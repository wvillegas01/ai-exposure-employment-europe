# Replication package

**Trend or Effect? Occupational Exposure to Artificial Intelligence and Relative Employment in Europe, 2011–2025**

This package contains the code and the derived tables behind every estimate reported in the
article, including the coefficients and standard errors that the text does not have room to
print in full.

## What is and is not included

Included: the analysis code (23 scripts), the 50 derived tables in CSV and JSON produced by
those scripts, the 12 figure files, and the registry of source files with their URLs, sizes and
SHA-256 checksums.

Not included: the source data themselves, about 56 MB. They are not redistributed because they
are already public and are better obtained from their own providers, which also guarantees that
a replication starts from the same bytes we used. `01_datos_fuente/01_scripts/descarga_fuentes.py`
downloads all of them and verifies each checksum against `01_datos_fuente/MANIFIESTO.json`.

Also not included: the code that typesets the manuscript and its bibliography. It reproduces the
document, not the results.

## How to reproduce

```
python 01_datos_fuente/01_scripts/descarga_fuentes.py
```

Then run each stage in numerical order; every script writes into the `02_outputs` folder of its
own stage and reads only from earlier stages, so the order is the dependency order:

```
python 02_auditoria_datos/01_scripts/auditoria_datos.py
python 03_crosswalk_soc_isco/01_scripts/crosswalk_aioe.py
...
python 16_revision_interna/01_scripts/inferencia_robusta.py
```

Scripts resolve their paths relative to their own location, so the package runs from wherever it
is unpacked.

## Environment

Python 3.8.10 with `numpy` 1.24.3, `pandas` 2.0.3, `scipy` 1.10.1, `pyhdfe` 0.1.2 for
fixed-effects absorption and `matplotlib` 3.7.5 for figures.

## Where each result comes from

| In the article | File |
| --- | --- |
| Table 1, employment by exposure quartile | `05_descriptivos_trayectorias/02_outputs/trayectoria_por_cuartil.csv` |
| Table 2, pre-cutoff coefficients with CI, MDE and TOST | `16_revision_interna/02_outputs/previas_ic_mde.csv`, `equivalencia_tost.csv` |
| Table 3, main estimates | `07_did_intensidad_continua/02_outputs/tabla_principal.csv` |
| Table 4, main specification and eleven variants | `11_robustez/02_outputs/robustez.csv`, `robustez_expuestas.csv` |
| Table 5, three inference schemes | `16_revision_interna/02_outputs/wild_bootstrap.json`, `equivalencia_y_2vias.json` |
| Table 6, placebo and actual cutoffs | `12_amenazas_validez/02_outputs/placebo_anos_falsos.csv`, `16_revision_interna/02_outputs/placebo_con_ic.csv` |
| Table 7, region-specific coefficients | `10_heterogeneidad/02_outputs/heterogeneidad_region.csv`, `16_revision_interna/02_outputs/regiones_conjunto.csv` |
| Supplementary Table 1, detailed variants | `16_revision_interna/02_outputs/robustez_detalle.csv` |
| Figure 2, event study | `13_figuras_resultados/03_reports/figures/fig2_tendencias_previas.*` |
| Figure 3, placebo cutoffs | `13_figuras_resultados/03_reports/figures/fig4_placebo.*` |
| Exposure indices aggregated to ISCO | `03_crosswalk_soc_isco/02_outputs/aioe_por_isco2.csv` |
| Reconstructed complementarity index | `03_crosswalk_soc_isco/02_outputs/theta_por_soc6.csv`, `validacion_theta.json` |
| Analytical panel | `04_construccion_panel/02_outputs/panel_analitico.csv` |

The coefficients and standard errors that Table 4 summarises as counts, and the full-sample
estimates that Supplementary Table 1 does not print, are in the four robustness CSV files listed
above.

## Source data and licences

| Source | Licence |
| --- | --- |
| Eurostat `lfsa_egai2d`, employment by occupation | Eurostat reuse policy |
| AI occupational exposure indices, `github.com/AIOE-Data/AIOE` | public repository |
| O\*NET database 31.0 | Creative Commons Attribution 4.0 |
| SOC–ISCO crosswalk, `iscoCrosswalks` | MIT |

`01_datos_fuente/MANIFIESTO.json` records, for every file, the URL it came from, its size in
bytes, its SHA-256 checksum and the UTC timestamp of the download.

## Note on comments

Code comments and some intermediate report filenames are in Spanish, the working language of the
research team. Variable names, outputs and this document are in English.

## Licence

The code is released under the MIT licence (`LICENSE`). The derived tables are **not** covered by
it: they inherit the terms of the sources they are built from, chiefly the Creative Commons
Attribution 4.0 licence of O\*NET. See `LICENSE-DATA.md` for the attribution that reuse requires.

## Citation

See `CITATION.cff`. Until the article is published, cite it as a submitted manuscript; this file
will be updated with the DOI on acceptance.
