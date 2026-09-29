"""
Etapa 08 - Sustitucion frente a complementariedad. LA PRUEBA DECISIVA.

La etapa 06 dejo claro que el nivel agregado no sirve: las ocupaciones expuestas llevan
doce anos ganando peso de forma monotona y 2023 no quiebra esa recta. El unico contraste
que puede detectar algo es INTERNO al grupo expuesto: ocupaciones igual de expuestas pero
con distinta complementariedad comparten la misma tendencia secular, de modo que la
diferencia entre ellas la elimina por construccion.

PREMISA QUE HAY QUE VERIFICAR ANTES DE INTERPRETAR NADA: los coeficientes de theta por ano
tienen que ser PLANOS antes de 2023. Si theta tambien arrastra tendencia previa, este
diseno cae igual que el anterior y hay que decirlo.

Especificaciones:
  A) Estudio de eventos doble: theta x ano y AIOE x ano simultaneamente, base 2022.
     El coeficiente de interes es el de theta, condicionado a la exposicion.
  B) Parsimoniosa con tendencias lineales:
       y = a[o,c] + g[c,t] + L1*AIOE*t + L2*theta*t + B1*AIOE*post + B2*theta*post
     B2 es el estimando: a igualdad de exposicion, mayor complementariedad predice
     mejor evolucion tras 2022?
  C) Lo mismo restringido a las 20 ocupaciones expuestas (AIOE > mediana).

Errores agrupados por ocupacion (40 conglomerados; 20 en la especificacion C).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
PANEL = RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv"
EXPO = RAIZ.parent / "03_crosswalk_soc_isco" / "02_outputs" / "exposicion_theta_isco2.csv"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(RAIZ.parent / "06_tendencias_previas" / "01_scripts"))
from tendencias_previas import ols_agrupado  # noqa: E402

ANO_BASE = 2022
ANO_TRAT = 2023


def ajusta(d, columnas, dependiente, grupo_cluster="isco2"):
    d = d.dropna(subset=[dependiente] + columnas)
    ids = np.column_stack([
        pd.factorize(d.geo + "_" + d.isco2)[0],
        pd.factorize(d.geo + "_" + d.ano.astype(str))[0],
    ])
    alg = pyhdfe.create(ids, drop_singletons=False)
    r = alg.residualize(d[[dependiente] + columnas].to_numpy(dtype=float))
    beta, se, V, G = ols_agrupado(r[:, 0], r[:, 1:], d[grupo_cluster].to_numpy(), int(alg.degrees))
    gl = G - 1
    t = beta / se
    p = 2 * (1 - stats.t.cdf(np.abs(t), gl))
    return pd.DataFrame({"termino": columnas, "coef": beta, "se": se, "t": t, "p": p}), V, G, len(d)


panel = pd.read_csv(PANEL)
expo = pd.read_csv(EXPO)[["isco2c", "aioe", "theta", "c_aioe"]].rename(columns={"isco2c": "isco2"})
d = panel[panel.muestra_principal == 1].merge(expo, on="isco2", how="left")
assert d.theta.notna().all(), "hay ocupaciones sin theta"

# estandarizadas entre ocupaciones, para que los coeficientes sean comparables
ocup = d.drop_duplicates("isco2")
d["aioe_z"] = (d.aioe - ocup.aioe.mean()) / ocup.aioe.std()
d["theta_z"] = (d.theta - ocup.theta.mean()) / ocup.theta.std()
d["t"] = d.ano - ANO_BASE
d["post"] = (d.ano >= ANO_TRAT).astype(int)

resultados = {}

# ---------------------------------------------------- A) estudio de eventos doble
anos = sorted(a for a in d.ano.unique() if a != ANO_BASE)
cols_a = []
for a in anos:
    d[f"aioe_{a}"] = d.aioe_z * (d.ano == a)
    d[f"theta_{a}"] = d.theta_z * (d.ano == a)
    cols_a += [f"aioe_{a}", f"theta_{a}"]

tabla_a, V_a, G_a, n_a = ajusta(d, cols_a, "cuota")
tabla_a["ano"] = [int(c.split("_")[1]) for c in tabla_a.termino]
tabla_a["variable"] = [c.split("_")[0] for c in tabla_a.termino]
tabla_a["periodo"] = np.where(tabla_a.ano < ANO_TRAT, "previo", "posterior")
tabla_a.to_csv(SALIDA / "estudio_evento_doble.csv", index=False)

th = tabla_a[tabla_a.variable == "theta"]
th_prev = th[th.periodo == "previo"]
idx = [i for i, c in enumerate(cols_a) if c.startswith("theta_") and int(c.split("_")[1]) < ANO_TRAT]
R = np.zeros((len(idx), len(cols_a)))
for f, i in enumerate(idx):
    R[f, i] = 1.0
Rb = R @ tabla_a.coef.to_numpy()
F = float(Rb.T @ np.linalg.pinv(R @ V_a @ R.T) @ Rb / len(idx))
p_F = float(1 - stats.f.cdf(F, len(idx), G_a - 1))

resultados["A_evento_doble"] = {
    "n": int(n_a),
    "wald_previos_theta_F": round(F, 4),
    "wald_previos_theta_p": round(p_F, 4),
    "previos_theta_significativos": int((th_prev.p < 0.05).sum()),
    "previos_theta_totales": int(len(th_prev)),
    "posteriores_theta": {
        int(r.ano): [round(r.coef, 6), round(r.se, 6), round(r.p, 4)]
        for r in th[th.periodo == "posterior"].itertuples()
    },
}

# ---------------------------------------------------- B) y C) parsimoniosas
d["aioe_t"] = d.aioe_z * d.t
d["theta_t"] = d.theta_z * d.t
d["aioe_post"] = d.aioe_z * d.post
d["theta_post"] = d.theta_z * d.post
cols_b = ["aioe_t", "theta_t", "aioe_post", "theta_post"]

for etiqueta, datos in (("B_completa", d), ("C_solo_expuestas", d[d.aioe > ocup.aioe.median()])):
    for dep in ("cuota", "log_empleo"):
        tabla, V, G, n = ajusta(datos, cols_b, dep)
        clave = f"{etiqueta}_{dep}"
        resultados[clave] = {
            "n": int(n), "clusters": int(G),
            **{r.termino: [round(r.coef, 6), round(r.se, 6), round(r.p, 4)] for r in tabla.itertuples()},
        }
        tabla.to_csv(SALIDA / f"parsimoniosa_{clave}.csv", index=False)

(SALIDA / "sustitucion_complementariedad.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

print(json.dumps(resultados, indent=2, ensure_ascii=False, default=float))
print("\n== A) coeficientes de theta por año (condicionados a la exposición) ==")
print(th[["ano", "periodo", "coef", "se", "p"]].to_string(index=False, float_format=lambda v: f"{v:9.5f}"))
