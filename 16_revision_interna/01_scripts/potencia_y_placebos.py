"""
Etapa 16b - Potencia de las tendencias previas y correccion por pruebas multiples.

(b) Para cada coeficiente previo de complementariedad y de exposicion se reportan
    intervalo de confianza y efecto minimo detectable. Un p>0,05 no dice nada por si
    solo: lo que acota la magnitud es el MDE.
(c) Los cinco placebos se contrastaban uno a uno. Con cinco contrastes, la probabilidad
    de que al menos uno resulte significativo al 5 % por azar es 1-0,95^5 = 22,6 %. Se
    aplica la correccion de Sidak y se situa la estimacion real en la distribucion de
    placebos.
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

ANO_BASE, ANO_TRAT = 2022, 2023
panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"],
                         errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]

# ------------------------------------------------- (b) potencia de las previas
d = prepara(panel, expo).dropna(subset=["cuota"]).copy()
anos = sorted(a for a in d.ano.unique() if a != ANO_BASE)
cols = []
for a in anos:
    d[f"A_{a}"] = d.aioe_z * (d.ano == a)
    d[f"T_{a}"] = d.theta_z * (d.ano == a)
    cols += [f"A_{a}", f"T_{a}"]

ids = np.column_stack([pd.factorize(d.geo + "_" + d.isco2)[0],
                       pd.factorize(d.geo + "_" + d.ano.astype(str))[0]])
alg = pyhdfe.create(ids, drop_singletons=False)
r = alg.residualize(d[["cuota"] + cols].to_numpy(dtype=float))
beta, se, _, G = ols_agrupado(r[:, 0], r[:, 1:], d.isco2.to_numpy(), int(alg.degrees))
gl = G - 1
tc = stats.t.ppf(0.975, gl)
mult = stats.t.ppf(0.975, gl) + stats.t.ppf(0.80, gl)

filas = []
for i, c in enumerate(cols):
    var, ano = c.split("_")
    if int(ano) >= ANO_TRAT:
        continue
    filas.append({
        "variable": "exposicion" if var == "A" else "complementariedad",
        "ano": int(ano),
        "coef": round(float(beta[i]), 6),
        "ic_bajo": round(float(beta[i] - tc * se[i]), 6),
        "ic_alto": round(float(beta[i] + tc * se[i]), 6),
        "mde": round(float(mult * se[i]), 6),
    })
prev = pd.DataFrame(filas)
prev.to_csv(SALIDA / "previas_ic_mde.csv", index=False)

th = prev[prev.variable == "complementariedad"]
ex = prev[prev.variable == "exposicion"]
resumen_b = {
    "complementariedad": {
        "max_abs_coef": round(float(th.coef.abs().max()), 6),
        "mde_mediano": round(float(th.mde.median()), 6),
        "mde_rango": [round(float(th.mde.min()), 6), round(float(th.mde.max()), 6)],
        "ic_mas_ancho": [round(float(th.ic_bajo.min()), 6), round(float(th.ic_alto.max()), 6)],
    },
    "exposicion": {
        "max_abs_coef": round(float(ex.coef.abs().max()), 6),
        "mde_mediano": round(float(ex.mde.median()), 6),
    },
}
resumen_b["lectura"] = (
    "El MDE mediano de las previas de complementariedad ("
    f"{resumen_b['complementariedad']['mde_mediano']}) es del mismo orden que el mayor "
    f"coeficiente previo de exposicion ({resumen_b['exposicion']['max_abs_coef']}): el diseno "
    "descartaria una tendencia previa de complementariedad tan grande como la de exposicion, "
    "pero no tendencias menores.")

# ------------------------------------------------- (c) placebos, pruebas multiples
pl = pd.read_csv(RAIZ.parent / "12_amenazas_validez" / "02_outputs" / "placebo_anos_falsos.csv")
res_c = {}
for dep in ("cuota", "log_empleo"):
    s = pl[pl.dependiente == dep]
    fal = s[s.tipo == "falso"].sort_values("corte")
    real = s[s.tipo == "real"].iloc[0]
    m = len(fal)
    sidak = 1 - (1 - 0.05) ** (1 / m)
    res_c[dep] = {
        "placebos": int(m),
        "umbral_sidak": round(float(sidak), 4),
        "p_minimo_placebo": round(float(fal.p.min()), 4),
        "placebos_significativos_sin_corregir": int((fal.p < 0.05).sum()),
        "placebos_significativos_con_sidak": int((fal.p < sidak).sum()),
        "prob_al_menos_uno_por_azar": round(float(1 - 0.95 ** m), 4),
        "real": [round(float(real.aioe_post), 6), round(float(real.p), 4)],
        "real_supera_a_todos_los_placebos": bool(real.aioe_post > fal.aioe_post.max()),
        "rango_placebos": [round(float(fal.aioe_post.min()), 6),
                           round(float(fal.aioe_post.max()), 6)],
        "p_por_rango": round((int((fal.aioe_post >= real.aioe_post).sum()) + 1) / (m + 1), 4),
    }

salida = {"previas": resumen_b, "placebos": res_c}
(SALIDA / "potencia_y_placebos.json").write_text(
    json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(salida, indent=2, ensure_ascii=False))
print("\n== coeficientes previos de complementariedad ==")
print(th[["ano", "coef", "ic_bajo", "ic_alto", "mde"]].to_string(index=False))
