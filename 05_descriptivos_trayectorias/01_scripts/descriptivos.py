"""Etapa 05 - Descriptivos y trayectorias."""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

panel = pd.read_csv(RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv")
panel = panel[panel.muestra_principal == 1]
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
d = panel.merge(ind[["isco2", "aioe", "lm_aioe", "theta", "c_aioe"]], on="isco2", how="left",
                suffixes=("_p", ""))

d["cuartil"] = pd.qcut(d.aioe.rank(method="dense"), 4, labels=["Q1 baja", "Q2", "Q3", "Q4 alta"])

# --- trayectoria del empleo por cuartil de exposicion, indice 2011 = 100 ---
tray = d.groupby(["cuartil", "ano"], observed=True).empleo_miles.sum().unstack(0)
tray_idx = (tray / tray.loc[2011] * 100).round(1)
tray_idx.to_csv(SALIDA / "trayectoria_por_cuartil.csv")

# --- tabla de ocupaciones ---
ocu = d.groupby("isco2").agg(
    aioe=("aioe", "first"), theta=("theta", "first"),
    cuota_media=("cuota", "mean"),
    empleo_2011=("empleo_miles", lambda s: s[d.loc[s.index, "ano"] == 2011].sum()),
    empleo_2022=("empleo_miles", lambda s: s[d.loc[s.index, "ano"] == 2022].sum()),
    empleo_2025=("empleo_miles", lambda s: s[d.loc[s.index, "ano"] == 2025].sum()),
).reset_index()
ocu["crec_2011_2022_pct"] = (ocu.empleo_2022 / ocu.empleo_2011 - 1) * 100
ocu["crec_2022_2025_pct"] = (ocu.empleo_2025 / ocu.empleo_2022 - 1) * 100
ocu.round(3).sort_values("aioe", ascending=False).to_csv(SALIDA / "tabla_ocupaciones.csv", index=False)

resumen = {
    "empleo_total_2011_miles": int(d[d.ano == 2011].empleo_miles.sum()),
    "empleo_total_2025_miles": int(d[d.ano == 2025].empleo_miles.sum()),
    "trayectoria_2025_indice_2011": tray_idx.loc[2025].round(1).to_dict(),
    "trayectoria_2022_indice_2011": tray_idx.loc[2022].round(1).to_dict(),
    "corr_aioe_crecimiento_previo": round(float(ocu.aioe.corr(ocu.crec_2011_2022_pct, method="spearman")), 3),
    "corr_aioe_crecimiento_posterior": round(float(ocu.aioe.corr(ocu.crec_2022_2025_pct, method="spearman")), 3),
    "corr_theta_crecimiento_posterior": round(float(ocu.theta.corr(ocu.crec_2022_2025_pct, method="spearman")), 3),
}
(SALIDA / "descriptivos.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print("== empleo por cuartil de exposición, índice 2011 = 100 ==")
print(tray_idx.to_string())
print("\n" + json.dumps(resumen, indent=2, ensure_ascii=False))
