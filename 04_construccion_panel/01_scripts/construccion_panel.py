"""
Etapa 04 - Construccion del panel analitico.

Aplica las reglas que salieron de las etapas 02 y 03. No descubre nada nuevo:
ejecuta decisiones ya tomadas y las verifica con aserciones duras. Si alguna
falla, el script para: es preferible a construir un panel silenciosamente roto.

Reglas aplicadas:
  - Fuera agregados geograficos (EU27_2020, EA21) y codigos ISCO que no sean de 2 digitos.
  - Fuera fuerzas armadas OC01-OC03 (D5): la SOC/AIOE no las cubre.
  - Muestra principal: se MARCA, no se borra. Excluidos UK (serie hasta 2019) y ME
    (hasta 2020) por no tener periodo posterior, y BA (desde 2021) por periodo
    previo insuficiente.
  - Denominador de las cuotas: suma de las 40 ocupaciones retenidas en cada pais-ano,
    de modo que las cuotas sumen 1 dentro de la muestra de analisis.
  - Tratamiento: Post = ano >= 2023 (IA generativa, finales de 2022).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
CROSSWALK = RAIZ.parent / "03_crosswalk_soc_isco" / "02_outputs" / "aioe_por_isco2.csv"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

AGREGADOS_GEO = {"EU27_2020", "EA21"}
FUERZAS_ARMADAS = {"OC01", "OC02", "OC03"}
SIN_POSTERIOR = {"UK", "ME"}      # series que terminan antes de 2023
SIN_PREVIO = {"BA"}               # serie que empieza en 2021
ANO_TRATAMIENTO = 2023
ANO_RUPTURA = 2021

# ------------------------------------------------------------------ carga
bruto = pd.read_csv(FUENTE / "eurostat" / "lfsa_egai2d.csv")
bruto = bruto[~bruto.geo.isin(AGREGADOS_GEO) & bruto.OBS_VALUE.notna()].copy()

es_2d = bruto.isco08.str.match(r"^OC\d\d$", na=False)
panel = bruto[es_2d & ~bruto.isco08.isin(FUERZAS_ARMADAS)].copy()

panel = panel.rename(columns={"TIME_PERIOD": "ano", "OBS_VALUE": "empleo_miles", "isco08": "isco2"})
panel["baja_fiabilidad"] = panel.OBS_FLAG.fillna("").str.contains("u")
panel["ruptura"] = panel.OBS_FLAG.fillna("").str.contains("b")
panel = panel[["geo", "isco2", "ano", "empleo_miles", "baja_fiabilidad", "ruptura"]]

# ------------------------------------------------- cuotas y variable dependiente
total = panel.groupby(["geo", "ano"]).empleo_miles.sum().rename("empleo_total")
panel = panel.merge(total, on=["geo", "ano"])
panel["cuota"] = panel.empleo_miles / panel.empleo_total
panel["log_empleo"] = np.log(panel.empleo_miles.where(panel.empleo_miles > 0))

# --------------------------------------------------------------- exposicion
aioe = pd.read_csv(CROSSWALK).drop(columns=["isco2"]).rename(columns={"isco08_2d": "isco2"})
panel = panel.merge(
    aioe[["isco2", "aioe_fraccional", "aioe_simple", "n_soc"]], on="isco2", how="left"
)
panel["exposicion"] = panel.aioe_fraccional

# ------------------------------------------------------------------ diseno
panel["post"] = (panel.ano >= ANO_TRATAMIENTO).astype(int)
panel["tratamiento"] = panel.exposicion * panel.post
panel["ano_ruptura"] = (panel.ano == ANO_RUPTURA).astype(int)
panel["oc95"] = (panel.isco2 == "OC95").astype(int)

cobertura = panel.groupby("geo").ano.agg(["min", "max", "nunique"])
excluidos = SIN_POSTERIOR | SIN_PREVIO
panel["muestra_principal"] = (~panel.geo.isin(excluidos)).astype(int)

panel = panel.sort_values(["geo", "isco2", "ano"]).reset_index(drop=True)

# ------------------------------------------------------------- ASERCIONES
fallos = []

if panel.duplicated(["geo", "isco2", "ano"]).any():
    fallos.append("hay filas duplicadas por geo x isco2 x ano")

if not FUERZAS_ARMADAS.isdisjoint(set(panel.isco2)):
    fallos.append("las fuerzas armadas siguen en el panel")

n_ocupaciones = panel.isco2.nunique()
if n_ocupaciones != 40:
    fallos.append(f"se esperaban 40 ocupaciones, hay {n_ocupaciones}")

if panel.exposicion.isna().any():
    huerfanas = sorted(panel[panel.exposicion.isna()].isco2.unique())
    fallos.append(f"ocupaciones sin AIOE: {huerfanas}")

suma = panel.groupby(["geo", "ano"]).cuota.sum()
if not np.allclose(suma, 1.0, atol=1e-9):
    fallos.append(f"las cuotas no suman 1 (min {suma.min():.6f}, max {suma.max():.6f})")

principal = panel[panel.muestra_principal == 1]
previos = principal[principal.post == 0].groupby("geo").ano.nunique()
posteriores = principal[principal.post == 1].groupby("geo").ano.nunique()
if previos.min() < 10:
    fallos.append(f"algun pais principal tiene menos de 10 anos previos (min {previos.min()})")
if posteriores.min() < 3:
    fallos.append(f"algun pais principal tiene menos de 3 anos posteriores (min {posteriores.min()})")

if not (panel.oc95.sum() > 0):
    fallos.append("OC95 deberia estar presente y marcado, no eliminado")

if fallos:
    for f in fallos:
        print("ASERCION FALLIDA:", f)
    raise SystemExit(1)

# ------------------------------------------------------------------ salidas
panel.to_csv(SALIDA / "panel_analitico.csv", index=False)

resumen = {
    "filas": int(len(panel)),
    "columnas": int(panel.shape[1]),
    "paises_totales": int(panel.geo.nunique()),
    "paises_muestra_principal": int(principal.geo.nunique()),
    "excluidos": {
        "sin_periodo_posterior": sorted(SIN_POSTERIOR),
        "sin_periodo_previo": sorted(SIN_PREVIO),
    },
    "ocupaciones": int(n_ocupaciones),
    "anos": [int(panel.ano.min()), int(panel.ano.max())],
    "ano_tratamiento": ANO_TRATAMIENTO,
    "muestra_principal_filas": int(len(principal)),
    "muestra_principal_techo": int(principal.geo.nunique() * 40 * 15),
    "celdas_baja_fiabilidad": int(panel.baja_fiabilidad.sum()),
    "anos_previos_min": int(previos.min()),
    "anos_posteriores_min": int(posteriores.min()),
    "aserciones": "7/7 superadas",
}
resumen["muestra_principal_completitud"] = round(
    resumen["muestra_principal_filas"] / resumen["muestra_principal_techo"], 4
)
(SALIDA / "panel_resumen.json").write_text(
    json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
)
cobertura.to_csv(SALIDA / "cobertura_por_pais.csv")

print(json.dumps(resumen, indent=2, ensure_ascii=False))
