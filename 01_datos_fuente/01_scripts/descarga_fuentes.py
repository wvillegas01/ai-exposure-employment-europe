"""
Etapa 01 - Descarga de datos fuente crudos e inmutables.

Nada de lo que este script escribe se edita despues a mano. Cualquier correccion
va en la etapa 02 (auditoria) o posteriores, nunca aqui.

Fuentes (decision D1: alcance Europa):
  1. Eurostat lfsa_egai2d - Empleo por ocupacion ISCO-08 a 2 digitos, 15-74 anos,
     ambos sexos, miles de personas. API SDMX publica, sin registro.
  2. AIOE - AI Occupational Exposure (Felten, Raj y Seamans 2021), SOC 6 digitos.
  3. O*NET 31.0 - base de descriptores ocupacionales, CC BY 4.0. Necesaria para
     RECONSTRUIR el indice de complementariedad: el del FMI no es redistribuible
     (decision D4).

NO se descarga WID.world: la desigualdad queda fuera del analisis principal (decision D3).
NO se descarga ILOSTAT: el servidor rechaza el acceso automatizado. Extension opcional,
descarga manual del usuario (decision D1).
"""
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"

FUENTES = [
    {
        "nombre": "eurostat_lfsa_egai2d",
        "destino": RAIZ / "eurostat" / "lfsa_egai2d.csv",
        "url": (
            "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
            "lfsa_egai2d/A..Y15-74.T.THS_PER.?format=SDMX-CSV"
        ),
        "nota": "Todas las ocupaciones, todos los paises, todos los anos disponibles.",
    },
    {
        "nombre": "aioe_data_appendix",
        "destino": RAIZ / "aioe" / "AIOE_DataAppendix.xlsx",
        "url": "https://raw.githubusercontent.com/AIOE-Data/AIOE/main/AIOE_DataAppendix.xlsx",
        "nota": "Apendices A-E. A = AIOE por ocupacion SOC 6 digitos.",
    },
    {
        "nombre": "onet_31_0",
        "destino": RAIZ / "onet" / "db_31_0_excel.zip",
        "url": "https://www.onetcenter.org/dl_files/database/db_31_0_excel.zip",
        "nota": "O*NET 31.0 completo, CC BY 4.0. Base del indice de complementariedad.",
    },
]


def descargar(fuente):
    destino = fuente["destino"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    peticion = urllib.request.Request(fuente["url"], headers={"User-Agent": UA})
    with urllib.request.urlopen(peticion, timeout=300) as respuesta:
        contenido = respuesta.read()
    destino.write_bytes(contenido)
    return {
        "nombre": fuente["nombre"],
        "url": fuente["url"],
        "archivo": str(destino.relative_to(RAIZ)),
        "bytes": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
        "descargado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nota": fuente["nota"],
    }


def main():
    registro = []
    for fuente in FUENTES:
        print("descargando", fuente["nombre"], "...", flush=True)
        try:
            entrada = descargar(fuente)
        except Exception as error:
            print("  FALLO:", error, file=sys.stderr)
            registro.append({"nombre": fuente["nombre"], "error": repr(error)})
            continue
        print("  ok  {bytes:,} bytes  sha256 {sha}".format(
            bytes=entrada["bytes"], sha=entrada["sha256"][:16]))
        registro.append(entrada)

    manifiesto = RAIZ / "MANIFIESTO.json"
    manifiesto.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
    print("manifiesto ->", manifiesto)

    if any("error" in entrada for entrada in registro):
        sys.exit(1)


if __name__ == "__main__":
    main()
