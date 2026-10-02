# Deterministic PSIC classification

Sigma Siphon contains a self-contained deterministic PSIC Revision 5 classifier for canonical POI data. It is intentionally separate from the main acquisition pipeline at this checkpoint so classification quality can be tested independently before replacing the existing production I-O tagging path.

## Evidence retained from acquisition

New reconciled records preserve source-specific semantic fields:

- `osm_name`
- `osm_category`
- `overture_name`
- `overture_category`

The canonical `name` and combined `category` remain for compatibility and display. The source-specific fields are the preferred classifier inputs because independent source evidence should not be flattened before fusion.

Older canonical files are still accepted. Single-source legacy rows can be reconstructed exactly from `sources`, `name`, and `category`. For older merged rows, Sigma Siphon separates OSM-like `key=value` category components from non-OSM category components when possible and marks the result with a legacy-recovery flag.

## Classification sequence

For each source independently:

1. reviewed crosswalk rules are checked first;
2. high-precision non-activity and uncodeable source categories are handled explicitly;
3. curated OSM/Overture category semantics produce a PSIC branch restriction;
4. selected source categories establish a conservative PSIC floor;
5. word and character TF-IDF retrieval searches within the allowed PSIC branch;
6. a strong, separated retrieval hit can refine below the floor;
7. otherwise the trusted floor is retained when available;
8. weak or ambiguous retrieval remains candidate-only.

Mapped OSM and Overture evidence is then fused in PSIC taxonomy space. Compatible nested evidence refines to the more specific admissible subtree. Independent immediate-sibling disagreement backs off by one level. Wider independent disagreement remains a conflict instead of being forced to a broad common ancestor. Activity versus non-activity disagreement between independent sources is also treated as a conflict.

## Retrieval thresholds

The defaults are:

- top candidates: `5`
- minimum score for automatic refinement: `0.45`
- minimum score margin over the second candidate: `0.12`

These can be changed for an explicit `classify` run:

```powershell
sigma-siphon classify .\output\pasig\pois.parquet `
  --top-n 5 `
  --min-score 0.45 `
  --min-margin 0.12
```

Changing these thresholds changes only semantic refinement. Source-policy decisions and trusted source floors remain conservative.

## Output columns

The classifier appends:

| Column | Meaning |
|---|---|
| `psic_code` | selected PSIC Revision 5 code, blank when unresolved |
| `psic_level` | PSIC hierarchy level of the selected code |
| `psic_title` | official bundled PSIC title |
| `psic_status` | resolution/fusion status |
| `psic_method` | deciding layer, such as fusion, trusted floor, or semantic refinement |
| `psic_candidate_codes` | retained lexical/fusion candidates |
| `psic_evidence_sources` | source systems contributing evidence |
| `psic_flags` | review and compatibility flags |
| `psic_retrieval_score` | strongest retained lexical retrieval score |
| `psic_rule` | source-semantic rule(s) used |
| `psic_query` | normalized retrieval query text |

## Deliberate limits at this checkpoint

The deterministic engine does **not** invoke an LLM. It also does not yet replace the normal `sigma-siphon run` I-O tagging path. The next integration stage can add candidate-bounded LLM resolution for unresolved PSIC cases and then map the resulting PSIC code through the bundled I-O concordance.
