"""
Etapa 03B - Exposicion, complementariedad y C-AIOE agregados a ISCO-08 de 2 digitos.
Genera la variable que necesita la etapa 08 (sustitucion vs complementariedad).
"""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
SALIDA = RAIZ / "02_outputs"

theta = pd.read_csv(SALIDA / "theta_por_soc6.csv")
theta["soc10"] = theta.soc6.str.replace("-", "", regex=False).astype(int)

aioe = pd.read_excel(FUENTE / "aioe" / "AIOE_DataAppendix.xlsx", sheet_name="Appendix A")
aioe.columns = [str(c).strip() for c in aioe.columns]
aioe["soc10"] = aioe["SOC Code"].astype(str).str.replace("-", "", regex=False).astype(int)

cw = pd.read_stata(FUENTE / "crosswalk" / "soc10_isco08.dta")
cw["isco2"] = (cw.isco08 // 100).astype(int)
cw["isco1"] = (cw.isco08 // 1000).astype(int)

d = aioe.merge(theta[["soc10", "theta"]], on="soc10", how="inner").merge(cw, on="soc10")
d["c_aioe"] = d.AIOE * (1 - (d.theta - d.theta.min()))
d["peso"] = 1.0 / d.groupby("soc10").soc10.transform("size")


def agrega(datos, clave):
    return datos.groupby(clave).apply(lambda x: pd.Series({
        "aioe": (x.AIOE * x.peso).sum() / x.peso.sum(),
        "theta": (x.theta * x.peso).sum() / x.peso.sum(),
        "c_aioe": (x.c_aioe * x.peso).sum() / x.peso.sum(),
        "n_soc": x.soc10.nunique(),
    })).reset_index()


g = agrega(d, "isco2")
g["isco2c"] = "OC" + g.isco2.astype(int).astype(str).str.zfill(2)
g.round(4).to_csv(SALIDA / "exposicion_theta_isco2.csv", index=False)

panel = pd.read_csv(RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv")
del_panel = set(panel.isco2)
en_panel = g[g.isco2c.isin(del_panel)]
sin_theta = sorted(del_panel - set(g.isco2c))

alto = en_panel[en_panel.aioe > en_panel.aioe.median()]
resumen = {
    "soc_con_theta_y_aioe": int(d.soc10.nunique()),
    "ocupaciones_panel_con_theta": int(len(en_panel)),
    "sin_theta": sin_theta,
    "corr_aioe_theta": round(float(en_panel.aioe.corr(en_panel.theta)), 4),
    "expuestas_sobre_mediana": int(len(alto)),
    "theta_en_expuestas": {
        "min": round(float(alto.theta.min()), 4),
        "max": round(float(alto.theta.max()), 4),
        "rango": round(float(alto.theta.max() - alto.theta.min()), 4),
    },
    "menor_complementariedad": alto.nsmallest(4, "theta").isco2c.tolist(),
    "mayor_complementariedad": alto.nlargest(4, "theta").isco2c.tolist(),
}
(SALIDA / "exposicion_isco2_resumen.json").write_text(
    json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(resumen, indent=2, ensure_ascii=False))
print("\n== grupo expuesto ordenado por complementariedad ==")
print(alto.sort_values("theta")[["isco2c", "aioe", "theta", "c_aioe"]].round(3).to_string(index=False))
