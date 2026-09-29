"""Etapa 10 - Heterogeneidad por region europea."""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
from robustez import prepara, ajusta, panel as panel_bruto  # noqa: E402

SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)
panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"], errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]
expuestas = set(expo[expo.aioe > expo.aioe.median()].isco2)

REGIONES = {
    "Nordicos": ["DK", "FI", "IS", "NO", "SE"],
    "Occidental": ["AT", "BE", "CH", "DE", "FR", "IE", "LU", "NL"],
    "Meridional": ["CY", "EL", "ES", "IT", "MT", "PT"],
    "Oriental y candidatos": ["BG", "CZ", "EE", "HR", "HU", "LT", "LV", "PL", "RO", "RS", "SI", "SK", "MK", "TR"],
}
cubiertos = {g for v in REGIONES.values() for g in v}
sin_region = sorted(set(panel.geo) - cubiertos)
assert not sin_region, f"paises sin region asignada: {sin_region}"

filas = []
for region, geos in REGIONES.items():
    p = panel[panel.geo.isin(geos) & panel.isco2.isin(expuestas)]
    d = prepara(p, expo)
    for dep in ("cuota", "log_empleo"):
        res, G, n = ajusta(d, dep)
        filas.append({
            "region": region, "paises": len(set(p.geo)), "dependiente": dep, "n": n,
            "expo_post": round(res["aioe_post"][0], 6), "p": round(res["aioe_post"][2], 4),
            "theta_post": round(res["theta_post"][0], 6), "theta_post_p": round(res["theta_post"][2], 4),
        })

t = pd.DataFrame(filas)
t.to_csv(SALIDA / "heterogeneidad_region.csv", index=False)
s = t[t.dependiente == "log_empleo"]
resumen = {
    "regiones": int(len(s)),
    "expo_post_positivo": int((s.expo_post > 0).sum()),
    "expo_post_significativo": int((s.p < 0.05).sum()),
    "rango": [round(float(s.expo_post.min()), 6), round(float(s.expo_post.max()), 6)],
    "theta_post_significativo": int((t.theta_post_p < 0.05).sum()),
}
(SALIDA / "heterogeneidad_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print(t.to_string(index=False))
print("\n" + json.dumps(resumen, indent=2, ensure_ascii=False))
