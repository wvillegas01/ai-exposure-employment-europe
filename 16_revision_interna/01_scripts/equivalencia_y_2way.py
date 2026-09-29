"""
Etapa 16c - Pruebas de equivalencia y agrupamiento bidimensional.

Dos peticiones de la revision que quedaban sin ejecutar:

(a) PRUEBAS DE EQUIVALENCIA. Reportar el MDE no basta: la revision pide contrastar
    formalmente que las tendencias previas de complementariedad son equivalentes a cero
    dentro de un margen justificado. Se usa TOST (two one-sided tests) con margen
    delta = 0,00313, que es el mayor coeficiente previo de EXPOSICION. La justificacion
    sustantiva es directa: lo que hay que descartar es que la complementariedad arrastre
    una tendencia previa del tamano de la que invalida a la exposicion.

(b) AGRUPAMIENTO BIDIMENSIONAL. Antes se declaraba como no viable. Se implementa la
    varianza de dos vias de Cameron, Gelbach y Miller:
        V_2 = V_ocupacion + V_pais - V_interseccion
    con grados de libertad conservadores, min(G1, G2) - 1.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "02_outputs"
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
sys.path.insert(0, str(RAIZ.parent / "06_tendencias_previas" / "01_scripts"))
from robustez import prepara, panel as panel_bruto  # noqa: E402
from tendencias_previas import ols_agrupado  # noqa: E402

COLS = ["aioe_t", "theta_t", "aioe_post", "theta_post"]
ANO_BASE, ANO_TRAT = 2022, 2023
MARGEN = 0.003133  # mayor coeficiente previo de exposicion (etapa 16, previas_ic_mde.csv)

panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"],
                         errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]
expuestas = set(expo[expo.aioe > expo.aioe.median()].isco2)


def sandwich(X, e, grupos, XtX_inv):
    codigos = pd.factorize(grupos)[0]
    carne = np.zeros((X.shape[1], X.shape[1]))
    for g in range(codigos.max() + 1):
        m = codigos == g
        s = X[m].T @ e[m]
        carne += np.outer(s, s)
    return XtX_inv @ carne @ XtX_inv, codigos.max() + 1


def dos_vias(y, X, g1, g2, k_abs):
    """Varianza agrupada en dos dimensiones: V1 + V2 - V_interseccion."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta
    n, k = X.shape
    V1, G1 = sandwich(X, e, g1, XtX_inv)
    V2, G2 = sandwich(X, e, g2, XtX_inv)
    inter = pd.Series(g1).astype(str) + "_" + pd.Series(g2).astype(str)
    V12, G12 = sandwich(X, e, inter.to_numpy(), XtX_inv)
    G = min(G1, G2)
    correccion = (G / (G - 1)) * ((n - 1) / (n - k - k_abs))
    V = (V1 + V2 - V12) * correccion
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    return beta, se, G1, G2, G


def residualiza(d, dep, columnas):
    d = d.dropna(subset=[dep] + columnas)
    ids = np.column_stack([pd.factorize(d.geo + "_" + d.isco2)[0],
                           pd.factorize(d.geo + "_" + d.ano.astype(str))[0]])
    alg = pyhdfe.create(ids, drop_singletons=False)
    r = alg.residualize(d[[dep] + columnas].to_numpy(dtype=float))
    return d, r[:, 0], r[:, 1:], int(alg.degrees)


salida = {}

# ------------------------------------------------------------ (b) dos vias
dos = {}
for etiqueta, sub in (("expuestas", panel[panel.isco2.isin(expuestas)]), ("completa", panel)):
    d0 = prepara(sub, expo)
    for dep in ("cuota", "log_empleo"):
        dd, y, X, k_abs = residualiza(d0, dep, COLS)
        beta, se, G1, G2, G = dos_vias(y, X, dd.isco2.to_numpy(), dd.geo.to_numpy(), k_abs)
        for termino in ("aioe_post", "theta_post"):
            j = COLS.index(termino)
            t = beta[j] / se[j]
            p = float(2 * (1 - stats.t.cdf(abs(t), G - 1)))
            dos[f"{etiqueta}_{dep}_{termino}"] = {
                "beta": round(float(beta[j]), 6),
                "se_2vias": round(float(se[j]), 6),
                "p_2vias": round(p, 4),
                "G_ocupacion": int(G1), "G_pais": int(G2),
            }
            print(f"2vias {etiqueta}/{dep}/{termino}: beta={beta[j]:+.5f} "
                  f"se={se[j]:.5f} p={p:.4f} (G_oc={G1}, G_pa={G2})", flush=True)
salida["agrupamiento_bidimensional"] = dos

# ------------------------------------------------------ (a) equivalencia TOST
d = prepara(panel, expo).dropna(subset=["cuota"]).copy()
anos = sorted(a for a in d.ano.unique() if a != ANO_BASE)
cols = []
for a in anos:
    d[f"A_{a}"] = d.aioe_z * (d.ano == a)
    d[f"T_{a}"] = d.theta_z * (d.ano == a)
    cols += [f"A_{a}", f"T_{a}"]
dd, y, X, k_abs = residualiza(d, "cuota", cols)
beta, se, _, G = ols_agrupado(y, X, dd.isco2.to_numpy(), k_abs)
gl = G - 1

filas = []
for i, c in enumerate(cols):
    var, ano = c.split("_")
    if var != "T" or int(ano) >= ANO_TRAT:
        continue
    b, s = float(beta[i]), float(se[i])
    p_inf = 1 - stats.t.cdf((b + MARGEN) / s, gl)   # H0: b <= -margen
    p_sup = stats.t.cdf((b - MARGEN) / s, gl)       # H0: b >= +margen
    p_tost = float(max(p_inf, p_sup))
    filas.append({"ano": int(ano), "coef": round(b, 6), "se": round(s, 6),
                  "p_tost": round(p_tost, 5), "equivalente": bool(p_tost < 0.05)})
tost = pd.DataFrame(filas)
tost.to_csv(SALIDA / "equivalencia_tost.csv", index=False)
salida["equivalencia"] = {
    "margen": MARGEN,
    "justificacion": "mayor coeficiente previo de exposicion en la misma especificacion",
    "anos_contrastados": int(len(tost)),
    "equivalentes": int(tost.equivalente.sum()),
    "p_tost_maximo": round(float(tost.p_tost.max()), 5),
}
print("\n== TOST de las previas de complementariedad, margen "
      f"{MARGEN} ==")
print(tost.to_string(index=False))

(SALIDA / "equivalencia_y_2vias.json").write_text(
    json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
print("\n" + json.dumps(salida["equivalencia"], indent=2, ensure_ascii=False))
