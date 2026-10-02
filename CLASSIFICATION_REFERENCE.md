# Built-in classification reference bundle

Sigma Siphon 0.2.2 introduces the reference-data foundation for the PSIC-first classifier.
This stage deliberately does **not** replace the existing runtime classifier yet. The purpose
is to make the reference material self-contained, validated, and ready for the classification
engine in the next stage.

## Bundled PSIC reference

The installed package contains:

- a normalized **PSIC Revision 5** hierarchy (`nodes.parquet`);
- the corresponding official PSIC Revision 5 workbook retained as a reference source;
- a Revision 5 -> PSIC 2019 bridge; and
- a PSIC 2019 -> PSA 2018 input-output concordance carrying IO16, IO80, and IO240 sets.

The package also contains the PSIC crosswalk/review CSVs needed by later classification work.
Those CSVs have been reduced to **OSM and Overture rows only**. No Foursquare, PSCC, or PCPC
reference rows are included in this classification bundle.

## Validation

Run:

```powershell
sigma-siphon classification-check
```

The command validates:

1. packaged-asset checksums and sizes;
2. the PSIC hierarchy and parent links;
3. the Revision 5 -> 2019 bridge against the loaded PSIC Revision 5 taxonomy;
4. the PSIC 2019 -> I-O concordance schema and code formats; and
5. that the bundled crosswalk/reference CSVs contain only OSM and Overture source rows.

The command requires the project's declared `pyarrow` dependency because the normalized PSIC
hierarchy is stored as Parquet.

## Overture source policy

The Overture ingestion policy now rejects a place when **any** source-lineage item belongs to
Foursquare. Mixed-lineage records are rejected as well. The Overture cache normalization
version was therefore incremented so an older cache cannot silently bypass the new policy.

## Stage boundary

At this checkpoint:

- the reference bundle is built in;
- it can be loaded and validated without external PSIC paths;
- Foursquare lineage is excluded at Overture ingestion; and
- the existing Sigma Siphon POI classifier remains unchanged.

The next stage will wire hierarchical PSIC retrieval, source semantics, evidence fusion, and
refinement to these built-in assets.
