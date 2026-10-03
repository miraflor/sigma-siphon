# PSIC-first classification

Sigma Siphon contains a self-contained PSIC Revision 5 classifier for canonical POI data. PSIC is the canonical economic-activity representation used by both the standalone `classify` command and the production `run` pipeline.

## Evidence

Reconciled POIs preserve source-specific semantics:

- `osm_name`
- `osm_category`
- `overture_name`
- `overture_category`

The classifier uses those fields independently before fusion. Legacy canonical files are still accepted when their source semantics can be recovered from `sources`, `name`, and `category`.

## Decision sequence

The default path is deterministic:

1. reviewed source crosswalk rules;
2. high-precision non-activity and uncodeable rules;
3. curated OSM/Overture PSIC branch semantics;
4. trusted PSIC floors;
5. word + character TF-IDF retrieval inside the permitted branch;
6. conservative descendant refinement;
7. independent-source fusion and sibling backoff.

Resolved deterministic rows are never sent to the model.

When `--llm` is enabled, only unresolved deterministic statuses eligible for adjudication (`CANDIDATES_ONLY`, `UNION`, ordinary `CONFLICT`, and `UNRESOLVED`) enter hierarchical traversal. Activity-versus-non-activity conflicts and suspect entity matches remain review cases rather than being overridden by the model.

The model may only select a candidate child shown by the classifier, `STOP_HERE`, or `INSUFFICIENT`. Traversal runs three differently framed passes by default and retains the deepest node supported by a majority. The cache key includes the taxonomy fingerprint, model endpoint/model identity, prompt fingerprint, evidence text, restrictions, and pass count.

## Model configuration

Stage 4 reuses Sigma Siphon's existing OpenAI-compatible environment variables:

```text
SIGMA_LLM_API_KEY
SIGMA_LLM_BASE_URL
SIGMA_LLM_MODEL
```

`SIGMA_LLM_BASE_URL` and `SIGMA_LLM_MODEL` are optional; their normal Sigma defaults apply. Any OpenAI-compatible endpoint can be used.

A conservative test run can cap model use:

```powershell
sigma-siphon classify .\output\pasig\pois.parquet `
  --llm `
  --llm-max-rows 100 `
  --progress-every 25
```

Without `--llm`, Stage 4 reproduces the deterministic PSIC path and performs no model calls.

## PSIC to I-O mapping

Unless `--no-io` is supplied, final PSIC codes are mapped through:

```text
PSIC Revision 5
      ↓
PSIC 2019 bridge
      ↓
PSA 2018 I-O concordance
      ↓
IO16 / IO80 / IO240 candidate sets
```

The deepest valid section/division/group bridge ancestor is used. Draft bridge rows remain explicitly `PROVISIONAL_*` unless an accepted coarser ancestor produces exactly the same I-O candidate sets.

Candidate sets are never silently collapsed. Singleton sets expose a map code directly. For IO80, the bundled audited same-name resolver can additionally resolve the 55/56 and 66/67 pairs when same-run singleton evidence is globally unanimous and has at least two distinct establishments; contradictory names force abstention.

## Hybrid I-O resolution

After PSIC-to-I-O mapping, the deterministic direct I-O rules run as an independent downstream expert. A direct code may confirm a PSIC-derived singleton, resolve an ambiguous PSIC-derived set only when it lies inside that set, or provide a fallback when no PSIC-derived I-O candidate set exists. Direct evidence never overrides a conflicting PSIC-derived candidate set. PSIC non-activity, uncodeable, suspect-entity, and activity/non-activity-conflict decisions block direct fallback. IO240 remains PSIC-derived because the direct expert targets IO80 and its IO16 roll-up.

## Main output fields

PSIC fields include:

- `psic_code`, `psic_level`, `psic_title`
- `psic_status`, `psic_method`
- `psic_candidate_codes`
- `psic_evidence_sources`, `psic_flags`
- `psic_retrieval_score`, `psic_rule`, `psic_query`
- `psic_traversal_agreement`, `psic_model`
- `psic_audit`

I-O fields include mapping provenance plus candidate, map-code, status, name, and confidence columns for IO16, IO80, and IO240. IO80 also records resolver method/support/score fields.

## Examples

Deterministic PSIC + I-O:

```powershell
sigma-siphon classify .\output\pasig\pois.parquet
```

Model-assisted unresolved PSIC + I-O:

```powershell
sigma-siphon classify .\output\pasig\pois.parquet --llm
```

PSIC only:

```powershell
sigma-siphon classify .\output\pasig\pois.parquet --no-io
```

The default output remains `<input>_psic.parquet` unless `--output` is supplied.
