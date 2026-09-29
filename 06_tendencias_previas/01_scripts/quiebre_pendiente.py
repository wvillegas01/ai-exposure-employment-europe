"""
Etapa 06b - Contraste de QUIEBRE DE PENDIENTE en 2023.

El estudio de eventos muestra una tendencia previa monotona y significativa. La pregunta
que queda no es si hay un salto de nivel -sabemos que la serie viene subiendo- sino si
la IA generativa ACELERA o FRENA esa tendencia. Especificacion:

    y = a[o,c] + g[c,t] + b1*exp*t + b2*exp*1{post} + b3*exp*(t-2022)*1{post}

b2 = salto de nivel en 2023; b3 = cambio de pendiente despues. Si ambos son nulos, la
trayectoria posterior es la simple prolongacion de la previa y no hay efecto que estimar.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
PANEL = RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv"
SALIDA = RAIZ / "02_outputs"

import sys
sys.path.insert(0, str(RAIZ / "01_scripts"))
from tendencias_previas import ols_agrupado  # noqa: E402

panel = pd.read_csv(PANEL)
d = panel[panel.muestra_principal == 1].copy()
d["t"] = d.ano - 2022
d["exp_t"] = d.exposicion * d.t
d["exp_post"] = d.exposicion * (d.ano >= 2023)
d["exp_t_post"] = d.exposicion * d.t * (d.ano >= 2023)

resultados = {}
for dep in ("cuota", "log_empleo"):
    dd = d.dropna(subset=[dep])
    ids = np.column_stack([
        pd.factorize(dd.geo + "_" + dd.isco2)[0],
        pd.factorize(dd.geo + "_" + dd.ano.astype(str))[0],
    ])
    alg = pyhdfe.create(ids, drop_singletons=False)
    cols = ["exp_t", "exp_post", "exp_t_post"]
    r = alg.residualize(dd[[dep] + cols].to_numpy(dtype=float))
    beta, se, V, G = ols_agrupado(r[:, 0], r[:, 1:], dd.isco2.to_numpy(), int(alg.degrees))
    gl = G - 1
    t = beta / se
    p = 2 * (1 - stats.t.cdf(np.abs(t), gl))

    # Wald conjunto: b2 = b3 = 0  (ningun quiebre, ni de nivel ni de pendiente)
    R = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    Rb = R @ beta
    F = float(Rb.T @ np.linalg.pinv(R @ V @ R.T) @ Rb / 2)
    pF = float(1 - stats.f.cdf(F, 2, gl))

    resultados[dep] = {
        "pendiente_previa_b1": [round(float(beta[0]), 6), round(float(se[0]), 6), round(float(p[0]), 4)],
        "salto_nivel_b2": [round(float(beta[1]), 6), round(float(se[1]), 6), round(float(p[1]), 4)],
        "cambio_pendiente_b3": [round(float(beta[2]), 6), round(float(se[2]), 6), round(float(p[2]), 4)],
        "wald_sin_quiebre_F": round(F, 4),
        "wald_sin_quiebre_p": round(pF, 4),
    }
    print(f"\n===== {dep} =====  (coef, se, p)")
    for k, v in resultados[dep].items():
        print(f"  {k}: {v}")

(SALIDA / "quiebre_pendiente.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
