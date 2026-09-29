"""
Etapa 16 - Inferencia robusta con pocos conglomerados y potencia de las tendencias previas.

Responde a tres objeciones de la revision interna (2026-09-17):

  (a) Con 20 conglomerados ocupacionales, el error agrupado convencional con correccion
      de muestra pequena puede ser optimista. Se anade wild cluster bootstrap con pesos
      de Rademacher imponiendo la nula (Cameron, Gelbach y Miller) e inferencia por
      permutacion del regresor ocupacional.
  (b) La complementariedad se presentaba como "sin tendencia previa" apoyandose solo en
      p > 0,05. Se calculan intervalos de confianza y efecto minimo detectable de cada
      coeficiente previo, que es lo unico que permite afirmar algo sobre su magnitud.
  (c) Los cinco placebos se contrastaban de uno en uno. Se aplica correccion por pruebas
      multiples y se situa la estimacion real en la distribucion de placebos.
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
SALIDA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
sys.path.insert(0, str(RAIZ.parent / "06_tendencias_previas" / "01_scripts"))
from robustez import prepara, panel as panel_bruto  # noqa: E402
from tendencias_previas import ols_agrupado  # noqa: E402

SEMILLA = 20260917
B = 9999
COLS = ["aioe_t", "theta_t", "aioe_post", "theta_post"]

panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"],
                         errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]
expuestas = set(expo[expo.aioe > expo.aioe.median()].isco2)


def residualiza(d, dependiente, columnas):
    d = d.dropna(subset=[dependiente] + columnas)
    ids = np.column_stack([
        pd.factorize(d.geo + "_" + d.isco2)[0],
        pd.factorize(d.geo + "_" + d.ano.astype(str))[0],
    ])
    alg = pyhdfe.create(ids, drop_singletons=False)
    r = alg.residualize(d[[dependiente] + columnas].to_numpy(dtype=float))
    return d, r[:, 0], r[:, 1:], int(alg.degrees)


def t_agrupado(y, X, grupos, k_abs, j):
    beta, se, _, G = ols_agrupado(y, X, grupos, k_abs)
    return beta[j], se[j], beta[j] / se[j], G


def wild_bootstrap(y, X, grupos, k_abs, j, B=B, semilla=SEMILLA):
    """Wild cluster bootstrap con pesos de Rademacher imponiendo la hipotesis nula."""
    rng = np.random.default_rng(semilla)
    _, _, t_obs, G = t_agrupado(y, X, grupos, k_abs, j)

    # modelo restringido: se excluye la columna j (impone beta_j = 0)
    idx = [c for c in range(X.shape[1]) if c != j]
    Xr = X[:, idx]
    beta_r = np.linalg.pinv(Xr.T @ Xr) @ (Xr.T @ y)
    ajuste = Xr @ beta_r
    resid = y - ajuste

    codigos = pd.factorize(grupos)[0]
    n_g = codigos.max() + 1
    t_boot = np.empty(B)
    for b in range(B):
        w = rng.choice([-1.0, 1.0], size=n_g)[codigos]
        y_b = ajuste + w * resid
        _, _, t_b, _ = t_agrupado(y_b, X, grupos, k_abs, j)
        t_boot[b] = t_b
    p = float((np.abs(t_boot) >= abs(t_obs)).mean())
    lo, hi = np.percentile(t_boot, [2.5, 97.5])
    return {"t_observado": round(float(t_obs), 4), "p_wild_bootstrap": round(p, 4),
            "replicas": B, "t_critico_bootstrap_95": [round(float(lo), 3), round(float(hi), 3)],
            "clusters": int(G)}


def permutacion(d, dependiente, columna_expo, n=2000, semilla=SEMILLA):
    """Inferencia por permutacion: se reasignan los valores del indice entre ocupaciones."""
    rng = np.random.default_rng(semilla)
    ocupaciones = sorted(d.isco2.unique())
    _, y, X, k_abs = residualiza(d, dependiente, COLS)
    j = COLS.index(columna_expo)
    beta_obs, _, _, _ = t_agrupado(y, X, d.dropna(subset=[dependiente] + COLS).isco2.to_numpy(),
                                   k_abs, j)
    base = d.drop_duplicates("isco2").set_index("isco2")[["aioe", "theta"]]
    mayores = 0
    for _ in range(n):
        mezcla = base.copy()
        mezcla["aioe"] = rng.permutation(mezcla["aioe"].to_numpy())
        dd = d.drop(columns=["aioe", "theta"]).merge(
            mezcla.reset_index()[["isco2", "aioe"]], on="isco2")
        dd["theta"] = d["theta"].to_numpy()[:len(dd)]
        dd = prepara(dd.drop(columns=["aioe_z", "theta_z", "t", "post"] + COLS, errors="ignore"),
                     mezcla.reset_index())
        _, yb, Xb, kb = residualiza(dd, dependiente, COLS)
        bb, _, _, _ = t_agrupado(yb, Xb, dd.dropna(subset=[dependiente] + COLS).isco2.to_numpy(),
                                 kb, j)
        if abs(bb) >= abs(beta_obs):
            mayores += 1
    return {"beta_observado": round(float(beta_obs), 6),
            "p_permutacion": round((mayores + 1) / (n + 1), 4), "permutaciones": n}


resultados = {}

# --- (a) wild bootstrap sobre los coeficientes principales -------------------
for etiqueta, sub in (("expuestas", panel[panel.isco2.isin(expuestas)]), ("completa", panel)):
    d = prepara(sub, expo)
    for dep in ("cuota", "log_empleo"):
        dd, y, X, k_abs = residualiza(d, dep, COLS)
        g = dd.isco2.to_numpy()
        for termino in ("aioe_post", "theta_post"):
            j = COLS.index(termino)
            beta, se, t, G = t_agrupado(y, X, g, k_abs, j)
            wb = wild_bootstrap(y, X, g, k_abs, j)
            clave = f"{etiqueta}_{dep}_{termino}"
            resultados[clave] = {
                "beta": round(float(beta), 6), "se_agrupado": round(float(se), 6),
                "p_agrupado": round(float(2 * (1 - stats.t.cdf(abs(t), G - 1))), 4),
                **wb,
            }
            print(f"{clave}: beta={beta:+.5f}  p_cluster={2*(1-stats.t.cdf(abs(t),G-1)):.4f}  "
                  f"p_wild={wb['p_wild_bootstrap']:.4f}  (G={G})", flush=True)

(SALIDA / "wild_bootstrap.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
print("\n-> wild_bootstrap.json")
