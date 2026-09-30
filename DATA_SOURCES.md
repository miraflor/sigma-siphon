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

## Input-output code catalog

Sigma Siphon carries an 80-code / 16-code mapping used as local classification metadata. The numeric structure corresponds to the Philippine 2018 benchmark input-output industry aggregation. The human-readable labels in this repository are independently worded descriptors rather than copied publication prose.

The code structure is treated as factual classification metadata. This repository does not package PSA spreadsheets, reports, or source workbooks.

Reference page: https://psa.gov.ph/statistics/supply-and-use-input-output
