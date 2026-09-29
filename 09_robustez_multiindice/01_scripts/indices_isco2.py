"""
Etapa 09 (preparacion) - Todos los indices de exposicion agregados a ISCO-08 de 2 digitos.

Ademas del AIOE general se incorporan los dos indices especificos de IA GENERATIVA que
publican los mismos autores: Language Modeling y Image Generation. El de modelos de
lenguaje es el teoricamente correcto para nuestro tratamiento -lo que ocurre a finales de
2022 son los LLM, no la IA en general-, asi que su comportamiento es mas informativo que
el del indice general.

Indices generados por ocupacion ISCO-2:
  aioe        AIOE general (Felten, Raj y Seamans 2021), regla fraccional
  aioe_simple el mismo con media no ponderada
  lm_aioe     AIOE de modelos de lenguaje
  ig_aioe     AIOE de generacion de imagenes
  theta       complementariedad reconstruida (etapa 03B)
  c_aioe      exposicion ajustada por complementariedad, ecuacion (1) del FMI
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)


def soc_int(serie):
    return serie.astype(str).str.replace("-", "", regex=False).astype(int)


base = pd.read_excel(FUENTE / "aioe" / "AIOE_DataAppendix.xlsx", sheet_name="Appendix A")
base.columns = [str(c).strip() for c in base.columns]
base["soc10"] = soc_int(base["SOC Code"])
base = base[["soc10", "AIOE"]].rename(columns={"AIOE": "aioe"})

lm = pd.read_excel(FUENTE / "aioe" / "Language_Modeling_AIOE_and_AIIE.xlsx", sheet_name="LM AIOE")
lm["soc10"] = soc_int(lm["SOC Code"])
lm = lm[["soc10", "Language Modeling AIOE"]].rename(columns={"Language Modeling AIOE": "lm_aioe"})

ig = pd.read_excel(FUENTE / "aioe" / "Image_Generation_AIOE_and_AIIE.xlsx", sheet_name="IG AIOE")
ig["soc10"] = soc_int(ig["SOC Code"])
ig = ig[["soc10", "Image Generation AIOE"]].rename(columns={"Image Generation AIOE": "ig_aioe"})

theta = pd.read_csv(RAIZ.parent / "03_crosswalk_soc_isco" / "02_outputs" / "theta_por_soc6.csv")
theta["soc10"] = soc_int(theta.soc6)
theta = theta[["soc10", "theta"]]

cw = pd.read_stata(FUENTE / "crosswalk" / "soc10_isco08.dta")
cw["isco2"] = "OC" + (cw.isco08 // 100).astype(int).astype(str).str.zfill(2)

d = base.merge(lm, on="soc10").merge(ig, on="soc10").merge(theta, on="soc10").merge(cw, on="soc10")
d["c_aioe"] = d.aioe * (1 - (d.theta - d.theta.min()))
d["peso"] = 1.0 / d.groupby("soc10").soc10.transform("size")

indices = ["aioe", "lm_aioe", "ig_aioe", "theta", "c_aioe"]
g = d.groupby("isco2").apply(
    lambda x: pd.Series({c: (x[c] * x.peso).sum() / x.peso.sum() for c in indices})
).reset_index()
g["aioe_simple"] = d.groupby("isco2").aioe.mean().values
g["n_soc"] = d.groupby("isco2").soc10.nunique().values

g.round(5).to_csv(SALIDA / "indices_isco2.csv", index=False)
print(g.round(3).to_string(index=False))
print("\n== correlaciones entre índices ==")
print(g[indices + ["aioe_simple"]].corr(method="spearman").round(3).to_string())
