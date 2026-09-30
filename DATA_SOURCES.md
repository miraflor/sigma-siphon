# Data sources

Sigma Siphon directly acquires two POI sources.

## OpenStreetMap

Named establishment-relevant objects are requested from a user-configured Overpass endpoint and normalized to representative points. Broad railway/aeroway selectors are intentionally avoided; only establishment-like station, halt, terminal and aerodrome values are queried for those keys.

The data are licensed under ODbL 1.0. Commercial use is permitted subject to the ODbL conditions. The code does not default to volunteer public Overpass infrastructure; commercial deployments must configure an endpoint whose service terms permit the intended workload.

- OSM copyright and attribution: https://www.openstreetmap.org/copyright
- ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/

## Overture Maps Places

Places are streamed with the official Overture Python client for the requested bounding box. Provider provenance is parsed from each record and retained in the normalized layer. The pipeline records applicable provider-license identifiers and rejects records from unknown future providers rather than assuming a permissive license.

The provider intentionally outside this project's source policy is filtered out during acquisition. As a result, the normal retained Overture Places records are from providers covered by CDLA Permissive 2.0 or CC0 1.0 under the current Overture attribution table.

- Overture Places guide: https://docs.overturemaps.org/guides/places/
- Overture attribution and licensing: https://docs.overturemaps.org/attribution/


## Administrative boundaries and PSGC

Locality geometry is generated from the simplified geoBoundaries `gbOpen` Philippines ADM3 dataset and stored in `data/boundaries/areas.gpkg`. The boundary data are licensed CC BY 3.0 IGO.

Locality names and 10-digit aliases come from the Philippine Statistics Authority PSGC publication current at build time. The repository's boundary builder validates that the current catalog contains 149 cities and 1,493 municipalities before writing generated files.

A pinned 2023 PSGC-keyed low-resolution boundary snapshot is used only as a spatial crosswalk during the build to associate current geoBoundaries polygons with PSGC records, including duplicated locality names and later regional recodings. Output geometry remains geoBoundaries-derived.

- geoBoundaries: https://www.geoboundaries.org/
- PSGC: https://psa.gov.ph/classification/psgc/

### Composite metropolitan areas

Sigma Siphon keeps exactly three composite acquisition areas. They are unions of canonical PSGC localities rather than independent administrative records:

- **Metro Manila**: the 17 NCR LGUs (16 cities plus Pateros), following the PSA's NCR administrative composition.
- **Metro Cebu**: the 13-LGU Metro Cebu definition in the Central Visayas Regional Development Plan / Regional Spatial Development Framework.
- **Metro Davao**: the 15 LGUs within the jurisdiction of the Metropolitan Davao Development Authority under Republic Act No. 11708.

Membership is explicit and version-controlled in `scripts/build_areas.py`; the builder validates that every member PSGC exists before writing the generated catalog.

- PSA NCR: https://psa.gov.ph/classification/psgc/citimuni/1300000000
- Central Visayas RDP: https://pdp.neda.gov.ph/wp-content/uploads/2024/02/7-Central-Visayas-RDP-2017-2022.pdf
- Republic Act No. 11708: https://lawphil.net/statutes/repacts/ra2022/ra_11708_2022.html

## Input-output code catalog

Sigma Siphon carries an 80-code / 16-code mapping used as local classification metadata. The numeric structure corresponds to the Philippine 2018 benchmark input-output industry aggregation. The human-readable labels in this repository are independently worded descriptors rather than copied publication prose.

The code structure is treated as factual classification metadata. This repository does not package PSA spreadsheets, reports, or source workbooks.

Reference page: https://psa.gov.ph/statistics/supply-and-use-input-output
