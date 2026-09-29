"""
Etapa 03B - Reconstruccion del indice de complementariedad theta (Pizzinelli et al., IMF WP 2023/216).

El indice del FMI no es redistribuible (D4), asi que se reconstruye desde O*NET siguiendo
la metodologia del paper al pie de la letra. La reconstruccion es AUDITABLE: el paper
publica tres valores contra los que se contrasta, y si no cuadran hay que decirlo.

Metodologia (paper, seccion 2.3):
  11 contextos de trabajo de O*NET + job zone, agrupados en 6 componentes:
    1 Comunicacion       : Face-to-Face Discussions, Public Speaking
    2 Responsabilidad    : Work Outcomes and Results of Others, Health and Safety of Others
    3 Condiciones fisicas: Outdoors Exposed to Weather, Physical Proximity
    4 Criticidad         : Consequence of Error, Freedom to Make Decisions, Frequency of Decision Making
    5 Rutina             : Degree of Automation (INVERTIDO), Structured vs Unstructured Work
    6 Competencias       : Job Zone x 20
  Cada contexto se lleva a 0-100; cada componente es la media aritmetica de sus contextos;
  theta es la media aritmetica de los 6 componentes dividida por 100.

  C-AIOE = AIOE * [1 - (theta - theta_MIN)]        (ecuacion 1 del paper)

NOTA DE VERSION: el elemento 4.C.3.b.8 se llamaba "Structured versus Unstructured Work" y
en O*NET 31.0 figura como "Determine Tasks, Priorities and Goals". Es el mismo Element ID.
Se selecciona por ID, nunca por nombre, para que el script no se rompa entre versiones.

VALORES DE ORO publicados por el paper para validar:
  theta minimo  0.31  Hand Cutters and Trimmers      (SOC 2010  51-9031)
  theta maximo  0.78  Oral and Maxillofacial Surgeons (SOC 2010  29-1022)
  theta mediana 0.58
"""
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

COMPONENTES = {
    "comunicacion": ["4.C.1.a.2.l", "4.C.1.a.2.c"],
    "responsabilidad": ["4.C.1.c.2", "4.C.1.c.1"],
    "condiciones_fisicas": ["4.C.2.a.1.c", "4.C.2.a.3"],
    "criticidad": ["4.C.3.a.1", "4.C.3.a.4", "4.C.3.a.2.b"],
    "rutina": ["4.C.3.b.2", "4.C.3.b.8"],
}
INVERTIR = {"4.C.3.b.2"}  # Degree of Automation

ORO = {"theta_min": 0.31, "theta_max": 0.78, "theta_mediana": 0.58}

z = zipfile.ZipFile(FUENTE / "onet" / "db_31_0_excel.zip")
def leer(nombre):
    return pd.read_excel(io.BytesIO(z.read(f"db_31_0_excel/{nombre}.xlsx")))

wc = leer("Work Context")
wc = wc[(wc["Scale ID"] == "CX")].copy()          # escala Context 1-5
wc["valor_100"] = (wc["Data Value"] - 1) / 4 * 100
wc.loc[wc["Element ID"].isin(INVERTIR), "valor_100"] = (
    100 - wc.loc[wc["Element ID"].isin(INVERTIR), "valor_100"]
)

usados = [e for lista in COMPONENTES.values() for e in lista]
faltan = [e for e in usados if e not in set(wc["Element ID"])]
if faltan:
    raise SystemExit(f"elementos ausentes en O*NET: {faltan}")

ancho = wc[wc["Element ID"].isin(usados)].pivot_table(
    index="O*NET-SOC Code", columns="Element ID", values="valor_100"
)

for nombre, elementos in COMPONENTES.items():
    ancho[nombre] = ancho[elementos].mean(axis=1)

jz = leer("Job Zones").set_index("O*NET-SOC Code")["Job Zone"] * 20
ancho["competencias"] = jz

ancho = ancho.dropna(subset=list(COMPONENTES) + ["competencias"])
ancho["theta"] = ancho[list(COMPONENTES) + ["competencias"]].mean(axis=1) / 100

# --- O*NET-SOC 2019 (8 digitos) -> SOC 2010 (6 digitos) ---
# CRITICO: O*NET 31.0 viene en SOC 2019 y el AIOE esta en SOC 2010. Sin esta
# conversion el cruce descarta en silencio las ocupaciones que cambiaron de codigo
# entre ambas ediciones -entre ellas TODAS las informaticas (15-1132 -> 15-1252)-,
# que son justo las mas relevantes del analisis. El paper hace esta misma conversion.
ancho = ancho.reset_index()
puente = pd.read_excel(
    FUENTE / "crosswalk" / "2010_to_2019_SOC_Crosswalk.xlsx", skiprows=3
)
puente.columns = ["onet2010", "titulo2010", "onet2019", "titulo2019"]
puente["soc6_2010"] = puente.onet2010.astype(str).str[:7]
puente["soc6_2019"] = puente.onet2019.astype(str).str[:7]
puente = puente[["soc6_2019", "soc6_2010"]].drop_duplicates()

ancho["soc6_2019"] = ancho["O*NET-SOC Code"].str[:7]
convertido = ancho.merge(puente, on="soc6_2019", how="left")
# Si un codigo 2019 no aparece en el puente, es que no cambio: se conserva
convertido["soc6"] = convertido.soc6_2010.fillna(convertido.soc6_2019)
por_soc = convertido.groupby("soc6").theta.mean()

# ------------------------------------------------------- VALIDACION
def valor(soc):
    v = por_soc.get(soc)
    return None if v is None else round(float(v), 4)

validacion = {
    "n_ocupaciones_onet": int(len(ancho)),
    "n_soc6": int(len(por_soc)),
    "theta_min_obtenido": round(float(por_soc.min()), 4),
    "theta_min_ocupacion": por_soc.idxmin(),
    "theta_max_obtenido": round(float(por_soc.max()), 4),
    "theta_max_ocupacion": por_soc.idxmax(),
    "theta_mediana_obtenida": round(float(por_soc.median()), 4),
    "oro_publicado": ORO,
    "hand_cutters_51-9031": valor("51-9031"),
    "oral_maxillofacial_surgeons_29-1022": valor("29-1022"),
}
validacion["desvios"] = {
    "min": round(validacion["theta_min_obtenido"] - ORO["theta_min"], 4),
    "max": round(validacion["theta_max_obtenido"] - ORO["theta_max"], 4),
    "mediana": round(validacion["theta_mediana_obtenida"] - ORO["theta_mediana"], 4),
}

por_soc.rename("theta").to_csv(SALIDA / "theta_por_soc6.csv")
(SALIDA / "validacion_theta.json").write_text(
    json.dumps(validacion, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(validacion, indent=2, ensure_ascii=False))
