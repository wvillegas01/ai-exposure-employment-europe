"""
Etapa 11b - El indicio lateral de la etapa 08 sometido a las mismas variantes.

En la muestra restringida a las 20 ocupaciones expuestas, aioe_post salio positivo y
significativo (+0,0419 en log empleo, p=0,0044). Antes de darle cualquier peso hay que
ver si sobrevive. Se repiten las variantes de la etapa 11 sobre esa submuestra.
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "01_scripts"))
from robustez import prepara, ajusta, expo, panel, SALIDA, VARIANTES_DEF  # noqa: E402

VARIANTES = VARIANTES_DEF()

umbral = expo.aioe.median()
expuestas = set(expo[expo.aioe > umbral].isco2)

filas = []
for nombre, cfg in VARIANTES.items():
    p = cfg["panel"][cfg["panel"].isco2.isin(expuestas)]
    d = prepara(p, cfg["expo"])
    for dep in ("cuota", "log_empleo"):
        res, G, n = ajusta(d, dep, cfg.get("cluster", "isco2"))
        filas.append({
            "variante": nombre, "dependiente": dep, "n": n, "clusters": G,
            "aioe_post": round(res["aioe_post"][0], 6),
            "p": round(res["aioe_post"][2], 4),
            "theta_post": round(res["theta_post"][0], 6),
            "theta_post_p": round(res["theta_post"][2], 4),
        })

t = pd.DataFrame(filas)
t.to_csv(SALIDA / "robustez_expuestas.csv", index=False)
resumen = {}
for dep in ("cuota", "log_empleo"):
    s = t[t.dependiente == dep]
    resumen[dep] = {
        "aioe_post_significativo_en": int((s.p < 0.05).sum()),
        "variantes": int(len(s)),
        "aioe_post_rango": [round(float(s.aioe_post.min()), 6), round(float(s.aioe_post.max()), 6)],
        "aioe_post_positivo_en": int((s.aioe_post > 0).sum()),
        "theta_post_significativo_en": int((s.theta_post_p < 0.05).sum()),
    }
(SALIDA / "robustez_expuestas_resumen.json").write_text(
    json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print(t.to_string(index=False))
print("\n" + json.dumps(resumen, indent=2, ensure_ascii=False))
