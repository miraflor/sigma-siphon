# Data licensing for commercial use

This document separates the software license from licenses that govern acquired data.

## Software

Sigma Siphon itself is proprietary, closed-source commercial software. Copyright in the original repository code and documentation is retained by the owner; no public software license is granted. The root `LICENSE` file is a proprietary all-rights-reserved notice.

This proprietary status does **not** replace or narrow licenses independently granted for third-party dependencies or acquired data. Those components remain subject to their own terms, summarized in `THIRD_PARTY_NOTICES.md` and below.

## OpenStreetMap

OpenStreetMap data are available under the Open Database License 1.0 (ODbL). Commercial use is permitted. Public use of a derivative database carries attribution and share-alike obligations.

Sigma Siphon performs cross-source reconciliation and emits canonical POI records. For commercial publication, the project therefore adopts the conservative position that a fused output containing OSM-derived records is distributed under **ODbL 1.0**. Every such run writes `DATABASE_LICENSE.txt` and OSM attribution.

Internal-only use can have a different ODbL analysis because the public-use conditions are not triggered in the same way. Users distributing data should review the current OSMF Produced Work / Derivative Database / Collective Database guidance for their specific product.

## Overture Maps Places

Overture Places uses provider-specific permissive licenses. Under Overture's current attribution table, retained providers in this project are covered by CDLA Permissive 2.0 or CC0 1.0. Provider names and license identifiers are preserved per output row when available.

Records from the provider intentionally excluded by this project's source policy are discarded during ingestion, before reconciliation or classification.

If a future Overture provider is not recognized by the audited provider table, its records are excluded at ingestion. The ingestion policy therefore fails closed rather than publishing data under an unaudited source license.

## Output fields

The final GeoParquet includes:

- `sources`: which acquisition sources contributed to the canonical POI;
- `source_licenses`: observed upstream license identifiers; and
- `overture_providers`: observed Overture provider identifiers.

`ATTRIBUTION.txt` and `DATABASE_LICENSE.txt` are generated for each run.

## PSIC and input-output reference material

The repository now packages the official PSIC Revision 5 detailed-structure workbook together with normalized PSIC hierarchy data and locally maintained PSIC-to-I-O reference tables so classification can be reproduced without downloading a taxonomy at runtime. Philippine government works and factual classification data can be subject to different legal rules depending on how they are reproduced or commercially exploited. The bundled files are included for classification reproducibility; downstream distributors should independently confirm any permissions or attribution requirements that apply to their mode of redistribution or commercial use.

The I-O reference layer contains PSIC-to-IO16/IO80/IO240 code relationships and associated descriptive metadata used by the classifier. It is not a copy of the full PSA input-output transaction workbook.

## Practical release rule

Before publicly distributing a commercial output:

1. preserve `ATTRIBUTION.txt` and `DATABASE_LICENSE.txt` alongside the database or in equivalent product documentation;
2. make the ODbL-covered derivative database available as required when ODbL applies;
3. preserve per-source provenance fields rather than stripping them; and
4. re-check current Overture provider terms if the Overture release or provider set changes.

This file is an engineering compliance posture, not a substitute for legal advice about a particular distribution model.
