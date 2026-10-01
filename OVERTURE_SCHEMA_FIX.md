# Overture Places provenance/schema fix

This patch fixes a zero-row Overture ingestion failure caused by treating
`sources[].provider` as the decisive provenance field.

Current Overture Places rows may legitimately have:

```text
sources[0].dataset = meta
sources[0].provider = null
sources[0].license = null
```

The ingestion policy is now:

1. prefer `sources[].dataset`;
2. fall back to `sources[].provider`;
3. accept an explicit permitted SPDX license;
4. when the explicit license is null, infer the documented license only for
   current official Overture Places datasets;
5. reject unknown unlicensed future datasets instead of weakening the
   commercial-use guardrail.

Current documented fallbacks:

- Meta: CDLA-Permissive-2.0
- Microsoft: CDLA-Permissive-2.0
- PinMeTo: CDLA-Permissive-2.0
- Krick: CDLA-Permissive-2.0
- RenderSEO: CDLA-Permissive-2.0
- DAC: CDLA-Permissive-2.0
- BrightQuery: CDLA-Permissive-2.0
- Foursquare: Apache-2.0
- AllThePlaces: CC0-1.0

The patch also:

- understands the September 2026 `taxonomy`/`basic_category` schema;
- invalidates Overture caches created under the old normalization policy;
- refuses to cache a fresh zero-row Overture acquisition;
- prints raw/accepted/rejected counts and observed source datasets.
