"""
Etapa 12 - Amenaza principal al hallazgo de la etapa 11b.

Dentro del grupo expuesto, aioe_post es positivo y significativo en 12 de 12 variantes.
La objecion obvia: la especificacion impone una tendencia LINEAL, y si la tendencia real
es convexa, cualquier corte tardio producira un "salto" positivo espurio.

PRUEBA: repetir la estimacion con anos de tratamiento FALSOS, usando solo datos previos
al tratamiento real (se truncan en el ano anterior al corte falso + 3, y nunca se incluye
2023 o posterior). Si los cortes falsos tambien dan positivo y significativo, el resultado
de 2023 no es un efecto sino la curvatura de la tendencia.
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
from robustez import prepara, ajusta, expo, panel  # noqa: E402

import robustez  # noqa: E402

SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

expuestas = set(expo[expo.aioe > expo.aioe.median()].isco2)
base = panel[panel.isco2.isin(expuestas)]

filas = []
for corte in (2016, 2017, 2018, 2019, 2020, 2023):
    # ventana simetrica al diseno real: 3 anos posteriores al corte, y nada del periodo real
    tope = corte + 2
    d = base[base.ano <= tope] if corte < 2023 else base
    robustez.ANO_BASE = corte - 1
    robustez.ANO_TRAT = corte
    dd = prepara(d, expo)
    dd["t"] = dd.ano - (corte - 1)
    dd["post"] = (dd.ano >= corte).astype(int)
    dd["aioe_t"] = dd.aioe_z * dd.t
    dd["theta_t"] = dd.theta_z * dd.t
    dd["aioe_post"] = dd.aioe_z * dd.post
    dd["theta_post"] = dd.theta_z * dd.post
    for dep in ("cuota", "log_empleo"):
        res, G, n = ajusta(dd, dep)
        filas.append({
            "corte": corte, "tipo": "real" if corte == 2023 else "falso",
            "dependiente": dep, "n": n, "anos": f"{int(dd.ano.min())}-{int(dd.ano.max())}",
            "aioe_post": round(res["aioe_post"][0], 6),
            "p": round(res["aioe_post"][2], 4),
        })

t = pd.DataFrame(filas)
t.to_csv(SALIDA / "placebo_anos_falsos.csv", index=False)
res = {}
for dep in ("cuota", "log_empleo"):
    s = t[t.dependiente == dep]
    fal = s[s.tipo == "falso"]
    res[dep] = {
        "falsos_significativos": int((fal.p < 0.05).sum()),
        "falsos_totales": int(len(fal)),
        "falsos_positivos": int((fal.aioe_post > 0).sum()),
        "real_2023": [float(s[s.tipo == "real"].aioe_post.iloc[0]), float(s[s.tipo == "real"].p.iloc[0])],
        "rango_falsos": [round(float(fal.aioe_post.min()), 6), round(float(fal.aioe_post.max()), 6)],
    }
(SALIDA / "placebo_resumen.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print(t.to_string(index=False))
print("\n" + json.dumps(res, indent=2, ensure_ascii=False))
