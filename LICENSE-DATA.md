# Data sources and reuse terms

`LICENSE` applies to the authors' original code. It does not grant a blanket licence over
source data or mixed-source derived tables. Source-specific rights and attribution remain
applicable. CC BY 4.0 requires attribution; it is not a ShareAlike licence, and does not by
itself require every downstream result to use the same licence.

## Eurostat

Source: Eurostat, employment by occupation, table `lfsa_egai2d`, annual observations
2011–2025, ages 15–74, both sexes, thousands of persons. The original SDMX CSV downloaded
on 28 August 2026 is redistributed unchanged, with the original checksum in the manifest.
It contains published aggregate statistics, not confidential microdata.

[Eurostat's reuse policy](https://ec.europa.eu/eurostat/help/copyright-notice) permits reuse
with acknowledgment of the source. Derived panels apply the filters, exclusions and
transformations in stages 02–04. Eurostat has not endorsed these analyses.

## O*NET

This package uses information from the [O*NET 31.0 Database](https://www.onetcenter.org/database.html)
by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
O*NET® is a trademark of USDOL/ETA. The authors rescaled descriptors, constructed six
components of complementarity and aggregated occupations from SOC to ISCO. USDOL/ETA
has not approved, endorsed or tested these modifications.

The original descriptors are downloaded from O*NET, not redistributed. The taxonomy
crosswalk is retrieved separately from the [O*NET 2010–2019 crosswalk page](https://www.onetcenter.org/taxonomy/2019/walk.html).
See the [provider's licence notice](https://www.onetcenter.org/license_db.html) for its scope
and exceptions; do not assume every file on the provider's website has identical terms.

## AIOE and generative AI exposure indices

The workbooks are retrieved from [AIOE-Data/AIOE](https://github.com/AIOE-Data/AIOE)
at a fixed commit. They are not redistributed in this repository. The provider requests:

Felten, E., Raj, M., and Seamans, R. (2021). Occupational, industry, and geographic exposure
to artificial intelligence: A novel dataset and its potential uses. *Strategic Management
Journal*, 42(12), 2195–2217. https://doi.org/10.1002/smj.3286

The repository also provides language-modeling and image-generation indices. At the
29 September 2026 audit, no explicit licence for those datasets was found in the root
repository or its README. Public access and a citation request do not establish an open
redistribution licence. The package's MIT licence does not resolve this gap or relicense
AIOE-derived content. Reuse terms for mixed-source tables remain subject to clarification
with the relevant rights holders. This is an unresolved release consideration for Zenodo.

## SOC–ISCO correspondence

The `soc10_isco08.dta` file is retrieved from a pinned version of `eworx-org/iscoCrosswalks`.
The package's MIT notice is retained in `LICENSE-iscoCrosswalks.md`. The correspondence
originates from the Institute for Structural Research and the University of Warsaw;
see [the original source](https://ibs.org.pl/en/resources/occupation-classifications-crosswalks-from-onet-soc-to-isco/)
and the methodological publication https://doi.org/10.1111/ecot.12145.
The software package's licence should not be treated as independent proof of rights over
all third-party source material it bundles. The original crosswalk is downloaded, not redistributed.

## Excluded material

No proprietary IMF index or IMF paper is redistributed. Complementarity is independently
computed from O*NET descriptors using the cited methodology. The IMF Working Paper
2023/216 is retained as the methodological source; its presence is an explicit exception
to the project's preference for journal-only references, not a claim that it is a journal article.
