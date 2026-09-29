"""
Etapa 03A - Agregacion del AIOE de SOC-2010 (6 digitos) a ISCO-08 (2 digitos).

El crosswalk (paquete iscoCrosswalks, MIT, que implementa la concordancia publicada
del Institute for Structural Research de Varsovia, doi:10.1111/ecot.12145) es
MUCHOS A MUCHOS y NO trae pesos: 839 SOC -> 436 ISCO de 4 digitos en 1.131 pares.

Sin pesos de empleo de EE.UU. (BLS bloquea el acceso automatizado) la agregacion
exige una regla explicita. Se calculan DOS y se comparan:

  regla_fraccional : cada SOC reparte su peso 1/k entre sus k destinos ISCO.
                     Es la regla que la propia concordancia asume.
  regla_simple     : media no ponderada de los SOC que caen en cada ISCO-2.

Si las dos ordenan igual las 43 ocupaciones, la eleccion de regla no manda en el
resultado y eso se declara. Si no, es una fragilidad que va al manuscrito.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

# --- AIOE: 774 ocupaciones SOC 6 digitos ---
aioe = pd.read_excel(FUENTE / "aioe" / "AIOE_DataAppendix.xlsx", sheet_name="Appendix A")
aioe.columns = [str(c).strip() for c in aioe.columns]
aioe["soc10"] = aioe["SOC Code"].astype(str).str.replace("-", "", regex=False).astype(int)

# --- crosswalk SOC-2010 -> ISCO-08 (4 digitos) ---
cw = pd.read_stata(FUENTE / "crosswalk" / "soc10_isco08.dta")
cw["isco2"] = (cw.isco08 // 100).astype(int)

union = aioe.merge(cw, on="soc10", how="left")
sin_destino = union[union.isco08.isna()]

emparejado = union[union.isco08.notna()].copy()
# regla fraccional: cada SOC reparte 1/k entre sus k destinos ISCO de 4 digitos
emparejado["peso"] = 1.0 / emparejado.groupby("soc10").soc10.transform("size")

fraccional = (
    emparejado.assign(num=lambda x: x.AIOE * x.peso)
    .groupby("isco2")
    .apply(lambda g: g.num.sum() / g.peso.sum())
    .rename("aioe_fraccional")
)
simple = emparejado.groupby("isco2").AIOE.mean().rename("aioe_simple")
n_soc = emparejado.groupby("isco2").soc10.nunique().rename("n_soc")

indice = pd.concat([fraccional, simple, n_soc], axis=1).reset_index()
indice["isco2"] = indice.isco2.astype(int)
indice["isco08_2d"] = "OC" + indice.isco2.astype(int).astype(str).str.zfill(2)

# --- contraste contra las 43 ocupaciones que hay en Eurostat ---
euro = pd.read_csv(FUENTE / "eurostat" / "lfsa_egai2d.csv")
codigos_euro = sorted(
    c for c in euro.isco08.unique()
    if isinstance(c, str) and c.startswith("OC") and len(c) == 4
    and c not in {f"OC{d}" for d in range(10)}
)
cubiertas = [c for c in codigos_euro if c in set(indice.isco08_2d)]
faltan = [c for c in codigos_euro if c not in set(indice.isco08_2d)]

rho = indice[["aioe_fraccional", "aioe_simple"]].corr(method="spearman").iloc[0, 1]
pearson = indice[["aioe_fraccional", "aioe_simple"]].corr().iloc[0, 1]

indice.sort_values("aioe_fraccional", ascending=False).to_csv(
    SALIDA / "aioe_por_isco2.csv", index=False
)

resumen = {
    "aioe_ocupaciones_soc": int(len(aioe)),
    "soc_sin_destino_isco": int(sin_destino.soc10.nunique()),
    "soc_sin_destino_ejemplos": sin_destino["Occupation Title"].head(8).tolist(),
    "pares_crosswalk": int(len(cw)),
    "isco2_generados": int(len(indice)),
    "ocupaciones_eurostat": len(codigos_euro),
    "cubiertas": len(cubiertas),
    "sin_cobertura": faltan,
    "spearman_fraccional_vs_simple": round(float(rho), 4),
    "pearson_fraccional_vs_simple": round(float(pearson), 4),
}
(SALIDA / "crosswalk_resumen.json").write_text(
    json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(resumen, indent=2, ensure_ascii=False))
print("\n== 8 ocupaciones mas expuestas ==")
print(indice.nlargest(8, "aioe_fraccional")[["isco08_2d", "aioe_fraccional", "aioe_simple", "n_soc"]].to_string(index=False))
print("\n== 8 menos expuestas ==")
print(indice.nsmallest(8, "aioe_fraccional")[["isco08_2d", "aioe_fraccional", "aioe_simple", "n_soc"]].to_string(index=False))
