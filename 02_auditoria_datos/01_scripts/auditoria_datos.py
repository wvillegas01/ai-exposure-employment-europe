"""
Etapa 02 - Auditoria de los datos fuente.

No corrige el crudo: lo describe, lo contrasta y deja constancia. Las reglas que
salgan de aqui se aplican en la etapa 04 (construccion del panel).

Pregunta critica de esta etapa: la ruptura de serie de 2021 (reglamento IESS),
que afecta a los 36 paises a la vez y cae dos anos antes del tratamiento,
DESPLAZA LAS CUOTAS DE OCUPACION DE FORMA DIFERENCIAL? Si solo reescala el nivel
del pais, los efectos fijos pais x ano la absorben y el diseno sobrevive. Si
reclasifica trabajadores entre ocupaciones, no la absorben y hay que tratarla.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

AGREGADOS_GEO = {"EU27_2020", "EA21"}
# Codigos ISCO de un digito y no-respuesta: no son grupos de 2 digitos
AGREGADOS_ISCO = {"TOTAL", "NRP"} | {f"OC{d}" for d in range(10)}

resultados = {}


def es_dos_digitos(codigo):
    return (
        isinstance(codigo, str)
        and codigo.startswith("OC")
        and len(codigo) == 4
        and codigo not in AGREGADOS_ISCO
    )


bruto = pd.read_csv(FUENTE / "eurostat" / "lfsa_egai2d.csv")
bruto["ruptura"] = bruto.OBS_FLAG.fillna("").str.contains("b")
bruto["baja_fiabilidad"] = bruto.OBS_FLAG.fillna("").str.contains("u")

resultados["crudo"] = {
    "filas": int(len(bruto)),
    "anos": [int(bruto.TIME_PERIOD.min()), int(bruto.TIME_PERIOD.max())],
    "geos": int(bruto.geo.nunique()),
    "codigos_isco": int(bruto.isco08.nunique()),
    "obs_value_nulos": int(bruto.OBS_VALUE.isna().sum()),
}

# --- muestra de trabajo: paises reales, ocupaciones de 2 digitos ---
panel = bruto[
    ~bruto.geo.isin(AGREGADOS_GEO)
    & bruto.isco08.apply(es_dos_digitos)
    & bruto.OBS_VALUE.notna()
].copy()

totales = bruto[
    ~bruto.geo.isin(AGREGADOS_GEO) & (bruto.isco08 == "TOTAL") & bruto.OBS_VALUE.notna()
][["geo", "TIME_PERIOD", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "total"})

panel = panel.merge(totales, on=["geo", "TIME_PERIOD"], how="left")
panel["cuota"] = panel.OBS_VALUE / panel.total

resultados["muestra"] = {
    "filas": int(len(panel)),
    "paises": int(panel.geo.nunique()),
    "ocupaciones": int(panel.isco08.nunique()),
    "anos": [int(panel.TIME_PERIOD.min()), int(panel.TIME_PERIOD.max())],
    "celdas_techo": int(panel.geo.nunique() * panel.isco08.nunique() * panel.TIME_PERIOD.nunique()),
    "baja_fiabilidad": int(panel.baja_fiabilidad.sum()),
}
resultados["muestra"]["completitud"] = round(
    len(panel) / resultados["muestra"]["celdas_techo"], 4
)

# --- rupturas por ano ---
rupturas = (
    bruto[bruto.ruptura].groupby("TIME_PERIOD").size().rename("obs_con_ruptura").reset_index()
)
rupturas["geos_afectados"] = [
    bruto[bruto.ruptura & (bruto.TIME_PERIOD == y)].geo.nunique() for y in rupturas.TIME_PERIOD
]
rupturas.to_csv(SALIDA / "rupturas_por_ano.csv", index=False)
resultados["rupturas"] = rupturas.set_index("TIME_PERIOD").to_dict("index")

# --- PRUEBA CENTRAL: la ruptura de 2021 mueve las cuotas diferencialmente? ---
# Para cada pais y ocupacion, cambio absoluto de la cuota respecto al ano anterior.
# Si 2021 solo reescala el nivel del pais, las CUOTAS no deberian moverse mas que
# en un ano normal, porque la cuota es invariante a un reescalado comun.
panel = panel.sort_values(["geo", "isco08", "TIME_PERIOD"])
panel["cuota_prev"] = panel.groupby(["geo", "isco08"]).cuota.shift(1)
panel["ano_prev"] = panel.groupby(["geo", "isco08"]).TIME_PERIOD.shift(1)
consecutivos = panel[panel.TIME_PERIOD - panel.ano_prev == 1].copy()
consecutivos["salto"] = (consecutivos.cuota - consecutivos.cuota_prev).abs()

por_ano = (
    consecutivos.groupby("TIME_PERIOD")
    .salto.agg(media="mean", mediana="median", p95=lambda s: s.quantile(0.95), n="size")
    .reset_index()
)
por_ano.to_csv(SALIDA / "salto_cuotas_por_ano.csv", index=False)

normales = por_ano[~por_ano.TIME_PERIOD.isin([2021])]
ratio_2021 = float(
    por_ano.loc[por_ano.TIME_PERIOD == 2021, "media"].iloc[0] / normales.media.median()
)
ratio_2020 = float(
    por_ano.loc[por_ano.TIME_PERIOD == 2020, "media"].iloc[0] / normales.media.median()
)
resultados["prueba_ruptura_2021"] = {
    "salto_medio_2021": round(float(por_ano.loc[por_ano.TIME_PERIOD == 2021, "media"].iloc[0]), 6),
    "salto_medio_mediano_otros_anos": round(float(normales.media.median()), 6),
    "ratio_2021": round(ratio_2021, 3),
    "ratio_2020_covid_referencia": round(ratio_2020, 3),
}

# --- AIOE ---
aioe = pd.read_excel(FUENTE / "aioe" / "AIOE_DataAppendix.xlsx", sheet_name="Appendix A")
aioe.columns = [str(c).strip() for c in aioe.columns]
resultados["aioe"] = {
    "filas": int(len(aioe)),
    "columnas": list(aioe.columns)[:6],
    "nulos": int(aioe.isna().sum().sum()),
}

(SALIDA / "auditoria_datos.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(resultados, indent=2, ensure_ascii=False))
print("\n== salto medio de cuotas por ano ==")
print(por_ano.to_string(index=False))
