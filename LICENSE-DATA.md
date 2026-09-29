# Licence of the derived data

The MIT licence in `LICENSE` covers the **code** in this repository. It does not cover the
derived tables in the `02_outputs` folders, which are governed by the terms of the sources they
are built from.

The occupational descriptors come from **O\*NET database 31.0**, released by the U.S. Department
of Labor, Employment and Training Administration under the
[Creative Commons Attribution 4.0 International licence](https://creativecommons.org/licenses/by/4.0/).
Any table in this repository that derives from those descriptors — in particular the
reconstructed complementarity index in `03_crosswalk_soc_isco/02_outputs/theta_por_soc6.csv` and
everything computed from it — is therefore distributed under **CC BY 4.0** and must carry the
same attribution when reused:

> This product uses data from O\*NET, a trademark of the U.S. Department of Labor, Employment and
> Training Administration. O\*NET data are published under a Creative Commons Attribution 4.0
> International licence. The data have been modified: descriptors were rescaled and aggregated
> into a six-component complementarity index and mapped from SOC to ISCO-08.

The other sources carry their own terms: Eurostat data follow the Eurostat reuse policy, the
SOC–ISCO crosswalk from the `iscoCrosswalks` package is MIT licensed, and the AI occupational
exposure indices come from the public repository at https://github.com/AIOE-Data/AIOE.

No source file is redistributed here. `01_datos_fuente/MANIFIESTO.json` records the URL, size,
SHA-256 checksum and download timestamp of each one, and
`01_datos_fuente/01_scripts/descarga_fuentes.py` retrieves them from their original providers.
