# Source inputs

The raw inputs are immutable. Corrections and exclusions belong in the analysis scripts.
`MANIFIESTO.json` identifies all seven inputs with expected byte counts and SHA-256 hashes.

- `eurostat/lfsa_egai2d.csv`: original 28 August 2026 snapshot, included unchanged.
- `aioe/`: general, language-modeling and image-generation exposure workbooks.
- `onet/db_31_0_excel.zip`: O*NET 31.0 descriptors.
- `crosswalk/soc10_isco08.dta`: SOC 2010 to ISCO 08 correspondence.
- `crosswalk/2010_to_2019_SOC_Crosswalk.xlsx`: O*NET-SOC taxonomy correspondence.

Run from the repository root:

```sh
python 01_datos_fuente/01_scripts/descarga_fuentes.py
python 01_datos_fuente/01_scripts/descarga_fuentes.py --verify-only
```

Existing inputs are verified and never replaced. Downloads are checked before they are saved.
The manifest is not rewritten during replication. The historical Eurostat snapshot is required:
the live endpoint has revised observations. One byte-distinct O*NET crosswalk container is
explicitly accepted because every uncompressed XLSX member is identical to the original.

Three historical download timestamps are recorded. Four are unknown and marked null;
registration timestamps describe the later audit, not the original download.

No IMF proprietary index, Global Automation Atlas, WID or ILOSTAT input is used.
The complementarity index is reconstructed from O*NET descriptors.
See `../LICENSE-DATA.md` for attribution and limitations on reuse.
