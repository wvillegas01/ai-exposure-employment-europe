"""
Etapa 09 - Robustez multiindice.

Se repite la especificacion principal cambiando el indice de exposicion. Interesa sobre
todo el de MODELOS DE LENGUAJE: si el tratamiento de finales de 2022 son los LLM, el
resultado deberia aparecer con mas nitidez con ese indice que con el general. Si apareciera
igual con el de generacion de imagenes, que es menos pertinente, seria mala senal.
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
from robustez import prepara, ajusta, panel as panel_bruto  # noqa: E402

panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"], errors="ignore")

SALIDA = RAIZ / "02_outputs"
ind = pd.read_csv(SALIDA / "indices_isco2.csv")

filas = []
for indice in ("aioe", "aioe_simple", "lm_aioe", "ig_aioe", "c_aioe"):
    expo = ind[["isco2", indice, "theta"]].copy()
    umbral = expo[indice].median()
    expuestas = set(expo[expo[indice] > umbral].isco2)
    for muestra, p in (("completa", panel), ("expuestas", panel[panel.isco2.isin(expuestas)])):
        d = prepara(p, expo, col_aioe=indice, col_theta="theta")
        for dep in ("cuota", "log_empleo"):
            res, G, n = ajusta(d, dep)
            filas.append({
                "indice": indice, "muestra": muestra, "dependiente": dep, "n": n, "clusters": G,
                "expo_post": round(res["aioe_post"][0], 6), "expo_post_p": round(res["aioe_post"][2], 4),
                "expo_t": round(res["aioe_t"][0], 6), "expo_t_p": round(res["aioe_t"][2], 4),
                "theta_post": round(res["theta_post"][0], 6), "theta_post_p": round(res["theta_post"][2], 4),
            })

t = pd.DataFrame(filas)
t.to_csv(SALIDA / "multiindice.csv", index=False)
resumen = {}
for muestra in ("completa", "expuestas"):
    for dep in ("cuota", "log_empleo"):
        s = t[(t.muestra == muestra) & (t.dependiente == dep)]
        resumen[f"{muestra}_{dep}"] = {
            "expo_post_significativo": f"{int((s.expo_post_p<0.05).sum())}/{len(s)}",
            "expo_post_positivo": f"{int((s.expo_post>0).sum())}/{len(s)}",
            "expo_t_significativo": f"{int((s.expo_t_p<0.05).sum())}/{len(s)}",
            "theta_post_significativo": f"{int((s.theta_post_p<0.05).sum())}/{len(s)}",
        }
(SALIDA / "multiindice_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print(t.to_string(index=False))
print("\n" + json.dumps(resumen, indent=2, ensure_ascii=False))
