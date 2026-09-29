"""
Etapa 03B (validacion) - Contraste de la reconstruccion contra las afirmaciones
cualitativas que el FMI publica a 1 digito de ISCO (paper, seccion 2.4 y Figura 3):

  P1  Los directivos tienen MAYOR complementariedad que las ocupaciones de baja cualificacion.
  P2  El personal de apoyo administrativo (clerical, ISCO 4) tiene AIOE alto y el C-AIOE MAS ALTO de todos.
  P3  Directivos (1) y profesionales (2) bajan con el ajuste: alto AIOE pero bajo C-AIOE.
  P4  Los agricolas (6) quedan bajos en las DOS medidas.

Si estas cuatro se reproducen, la reconstruccion sirve para el analisis aunque los
niveles difieran por usar una version distinta de O*NET.
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
cw["isco1"] = (cw.isco08 // 1000).astype(int)

d = aioe.merge(theta[["soc10", "theta"]], on="soc10", how="inner").merge(cw, on="soc10")
theta_min = d.theta.min()
d["c_aioe"] = d.AIOE * (1 - (d.theta - theta_min))

d["peso"] = 1.0 / d.groupby("soc10").soc10.transform("size")
g = d.groupby("isco1").apply(
    lambda x: pd.Series({
        "AIOE": (x.AIOE * x.peso).sum() / x.peso.sum(),
        "theta": (x.theta * x.peso).sum() / x.peso.sum(),
        "C_AIOE": (x.c_aioe * x.peso).sum() / x.peso.sum(),
        "n_soc": x.soc10.nunique(),
    })
)
nombres = {1: "Directivos", 2: "Profesionales", 3: "Tecnicos", 4: "Apoyo administrativo",
           5: "Servicios y ventas", 6: "Agricolas", 7: "Oficios", 8: "Operadores", 9: "Elementales"}
g["grupo"] = [nombres.get(i, str(i)) for i in g.index]
g = g[["grupo", "AIOE", "theta", "C_AIOE", "n_soc"]]
print(g.round(3).to_string())

bajos = [7, 8, 9]
pruebas = {
    "P1_directivos_mas_complementarios_que_baja_cualificacion":
        bool(g.loc[1, "theta"] > g.loc[bajos, "theta"].max()),
    "P2_clerical_tiene_el_C_AIOE_mas_alto":
        bool(g.C_AIOE.idxmax() == 4),
    "P3_directivos_y_profesionales_bajan_con_el_ajuste":
        bool(g.loc[1, "AIOE"] > g.loc[1, "C_AIOE"] and g.loc[2, "AIOE"] > g.loc[2, "C_AIOE"]),
    "P4_agricolas_bajos_en_ambas":
        bool(g.loc[6, "AIOE"] < g.AIOE.median() and g.loc[6, "C_AIOE"] < g.C_AIOE.median()),
}
pruebas["superadas"] = f"{sum(pruebas.values())}/4"
print("\n" + json.dumps(pruebas, indent=2, ensure_ascii=False))
g.round(4).to_csv(SALIDA / "validacion_isco1.csv")
(SALIDA / "validacion_isco1.json").write_text(json.dumps(pruebas, indent=2, ensure_ascii=False), encoding="utf-8")
