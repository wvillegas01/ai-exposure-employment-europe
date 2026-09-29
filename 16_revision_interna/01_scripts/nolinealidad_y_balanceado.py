"""
Etapa 16e - Contraste formal de no linealidad y sensibilidad de panel balanceado.

(a) Dividir por la mediana y comparar dos estimaciones NO demuestra no linealidad. Se
    estima un modelo unico con interaccion triple exposicion x post x mitad-alta y se
    contrasta la igualdad de pendientes entre mitades. Como alternativa se ajusta un
    spline lineal con nudo en la mediana, tambien interactuado con el periodo posterior.

(b) Las celdas sin valor publicado por Eurostat pueden alterar la composicion ocupacional
    a lo largo del tiempo. Se repite la estimacion sobre el panel balanceado, es decir
    sobre los pares ocupacion-pais observados en los quince anos.
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
from robustez import prepara, ajusta, panel as panel_bruto  # noqa: E402
from tendencias_previas import ols_agrupado  # noqa: E402

panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"],
                         errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]
mediana = float(expo.aioe.median())
altas = set(expo[expo.aioe > mediana].isco2)

salida = {}


def estima(d, dep, columnas, cluster="isco2"):
    d = d.dropna(subset=[dep] + columnas)
    ids = np.column_stack([pd.factorize(d.geo + "_" + d.isco2)[0],
                           pd.factorize(d.geo + "_" + d.ano.astype(str))[0]])
    alg = pyhdfe.create(ids, drop_singletons=False)
    r = alg.residualize(d[[dep] + columnas].to_numpy(dtype=float))
    beta, se, V, G = ols_agrupado(r[:, 0], r[:, 1:], d[cluster].to_numpy(), int(alg.degrees))
    return beta, se, V, G, len(d)


# --------------------------------------------- (a) interaccion triple
d = prepara(panel, expo).copy()
d["alta"] = d.isco2.isin(altas).astype(float)
d["A_t"] = d.aioe_z * d.t
d["T_t"] = d.theta_z * d.t
d["H_t"] = d.alta * d.t
d["A_p"] = d.aioe_z * d.post
d["T_p"] = d.theta_z * d.post
d["H_p"] = d.alta * d.post
d["AH_p"] = d.aioe_z * d.alta * d.post
d["AH_t"] = d.aioe_z * d.alta * d.t
cols = ["A_t", "T_t", "H_t", "AH_t", "A_p", "T_p", "H_p", "AH_p"]

inter = {}
for dep in ("cuota", "log_empleo"):
    beta, se, V, G, n = estima(d, dep, cols)
    i = cols.index("AH_p")
    t = beta[i] / se[i]
    p = float(2 * (1 - stats.t.cdf(abs(t), G - 1)))
    tc = stats.t.ppf(0.975, G - 1)
    inter[dep] = {
        "pendiente_mitad_baja": round(float(beta[cols.index("A_p")]), 6),
        "diferencia_alta_menos_baja": round(float(beta[i]), 6),
        "se": round(float(se[i]), 6),
        "ic95": [round(float(beta[i] - tc * se[i]), 6), round(float(beta[i] + tc * se[i]), 6)],
        "p_igualdad_de_pendientes": round(p, 4),
        "n": int(n), "clusters": int(G),
    }
    print(f"interacción triple, {dep}: diferencia={beta[i]:+.6f} se={se[i]:.6f} "
          f"p={p:.4f} (n={n}, G={G})")
salida["interaccion_triple"] = inter

# --------------------------------------------- (b) panel balanceado
conteo = panel.groupby(["geo", "isco2"]).ano.nunique()
completos = set(conteo[conteo == panel.ano.nunique()].index)
bal = panel[[(g, o) in completos for g, o in zip(panel.geo, panel.isco2)]]
print(f"\npanel balanceado: {len(bal)} de {len(panel)} filas "
      f"({100*len(bal)/len(panel):.1f} %), {bal.geo.nunique()} países, "
      f"{bal.isco2.nunique()} ocupaciones")

COLS = ["aioe_t", "theta_t", "aioe_post", "theta_post"]
balr = {}
for etiqueta, sel in (("expuestas", bal[bal.isco2.isin(altas)]), ("completa", bal)):
    dd = prepara(sel, expo)
    for dep in ("cuota", "log_empleo"):
        res, G, n = ajusta(dd, dep)
        c, s_, p_ = res["aioe_post"]
        ct, st, pt = res["theta_post"]
        balr[f"{etiqueta}_{dep}"] = {"beta_A": [round(c, 6), round(p_, 4)],
                                     "beta_theta": [round(ct, 6), round(pt, 4)],
                                     "n": int(n), "clusters": int(G)}
        print(f"  balanceado {etiqueta}/{dep}: beta_A={c:+.5f} (p={p_:.4f})  "
              f"beta_theta={ct:+.5f} (p={pt:.4f})  n={n}")
salida["panel_balanceado"] = balr
salida["panel_balanceado_cobertura"] = {
    "filas": int(len(bal)), "filas_totales": int(len(panel)),
    "porcentaje": round(100 * len(bal) / len(panel), 1)}

(SALIDA / "nolinealidad_y_balanceado.json").write_text(
    json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
