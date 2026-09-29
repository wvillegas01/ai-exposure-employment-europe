# Replication package

**Trend or Effect? Occupational Exposure to Artificial Intelligence and Relative Employment in Europe, 2011–2025**

This package contains the code and the derived tables behind every estimate reported in the
article, including the coefficients and standard errors that the text does not have room to
print in full.

## What is and is not included

Included: 23 analysis scripts, one source downloader, 50 derived CSV/JSON outputs,
12 figure files, the seven-source manifest, and the original Eurostat snapshot.
`reproduce.py` runs the analysis in dependency order.

The Eurostat snapshot (downloaded on 28 August 2026) is included unchanged because the live
API has since revised observations. Source: Eurostat, `lfsa_egai2d`; see `LICENSE-DATA.md`.
The remaining six inputs are downloaded from their providers and checked against recorded
SHA-256 hashes before being saved. Source files and the historical manifest are never
silently overwritten. Manuscript typesetting code is outside this package.

## How to reproduce

Use CPython 3.8.10 and a separate environment. On Windows:

```powershell
py -3.8 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe reproduce.py
```

On systems with Python 3.8 installed:

```sh
python3.8 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce.py
```

`reproduce.py` verifies/downloads the seven inputs, runs all 23 analysis scripts and stops
at the first error. It regenerates the packaged outputs, so use a fresh checkout for replication.
The bootstrap uses 9,999 draws and may take several minutes. Seeds and draw counts are unchanged.

```sh
python reproduce.py --list
python reproduce.py --offline
python -m unittest discover -s tests
```

`--list` prints the full dependency order without running. `--offline` requires all seven
inputs to be present and verified. Numerical stage labels are not execution order: exposure
aggregation needs the panel from stage 04, stage 05 needs indices from stage 09, and figures
need stage 16. Script paths are resolved relative to the package.

If a hash differs, stop and obtain the recorded input; do not replace the expected hash with
the new one. The O*NET crosswalk has one explicitly recorded equivalent XLSX container:
all uncompressed members were compared byte for byte with the original. This does not allow
arbitrary new versions. The Eurostat snapshot must be retained to reproduce the original analysis.

## Environment

Python 3.8.10 with `numpy` 1.24.3, `pandas` 2.0.3, `scipy` 1.10.1, `pyhdfe` 0.1.2,
`matplotlib` 3.7.5 and `openpyxl` 3.1.5. `requirements.txt` pins these and their installed
runtime dependencies. This historical environment is retained for replication.
See `REPRODUCIBILITY.md` for the validation scope and remaining limitations.

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
| AI occupational exposure indices, `github.com/AIOE-Data/AIOE` | Citation requested; no explicit data licence found; see `LICENSE-DATA.md` |
| O\*NET database 31.0 | Creative Commons Attribution 4.0 |
| SOC–ISCO crosswalk distributed by `iscoCrosswalks` | Package MIT; original crosswalk attribution retained |
| O*NET-SOC 2010–2019 crosswalk | Provider terms; retrieved from O*NET |

`01_datos_fuente/MANIFIESTO.json` records seven inputs with verified retrieval URLs, sizes
and SHA-256 hashes. Three original download timestamps survive; the four missing timestamps
are explicitly null. Audit registration dates are not presented as historical download dates.

## Note on comments

Code comments and some intermediate report filenames are in Spanish, the working language of the
research team. Variable names, outputs and this document are in English.

## Licence

The original code is released under MIT (`LICENSE`). This is not a blanket licence for
source data or mixed-source tables. `LICENSE-DATA.md` records source attributions,
applicable terms and the unresolved AIOE reuse terms. A public source is not itself a licence.

## Citation

See `CITATION.cff`. Until the article is published, cite it as a submitted manuscript; this file
will be updated with the DOI on acceptance.
