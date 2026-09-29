# 01 — Datos fuente

Carpeta **inmutable**. Nada de lo que hay aquí se edita a mano. Las correcciones
(celdas corruptas, renombres de países, reglas de exclusión) van en la etapa 02 y
quedan registradas en el script de esa etapa, nunca aplicadas sobre el crudo.

`MANIFIESTO.json` guarda para cada archivo: URL, tamaño, SHA-256 y fecha de descarga.

## Contenido previsto

| Carpeta | Fuente | Estado |
|---|---|---|
| `eurostat/` | Eurostat `lfsa_egai2d` — empleo por ocupación ISCO-08 (2 díg.), 15-74 años, ambos sexos, miles de personas | verificado, pendiente de descarga |
| `aioe/` | AIOE — Felten, Raj y Seamans (2021), SOC 6 dígitos | verificado, pendiente de descarga |
| `onet/` | O*NET 31.0 — descriptores ocupacionales, CC BY 4.0 | verificado, pendiente de descarga |
| `atlas/` | *Global Automation Atlas* — país × ocupación | **bloqueado: licencia y años sin declarar** |
| `fmi/` | Índice de complementariedad del IMF WP 2023/216 | **descartado: no redistribuible** (ver D4) |

## Fuera de alcance, a propósito

- **WID.world** (882 MB): la desigualdad queda fuera del análisis principal (decisión D3).
- **ILOSTAT**: el servidor rechaza el acceso automatizado (403). Extensión opcional
  fuera de Europa; requiere descarga manual.
- **Índice de complementariedad del FMI**: se comparte solo por petición por correo a los
  autores y con licencia propia que **no permite redistribución**. Mismo caso que Freedom on
  the Net en el artículo 1. Se reconstruye desde O*NET (decisión D4).

## Reproducir

```
python 01_scripts/descarga_fuentes.py
```
