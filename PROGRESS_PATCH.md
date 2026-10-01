# Progress-output patch

This patch changes visibility only. It does not change the pipeline algorithm,
matching thresholds, classification rules, data sources, or default LLM behavior.

A run now reports:

- resolved area;
- OSM cache/download status;
- each OSM tile and retry attempt;
- Overture stream/batch progress;
- clipping before/after counts;
- reconciliation counts;
- classification mode and counts;
- output-writing stage;
- total elapsed time.

Example:

```text
→ Resolving area: pasig
→ Area: City of Pasig (pasig)
→ [1/7] Acquiring OpenStreetMap POIs
→ OSM: downloading 1 tile(s)
→ OSM: tile 1/1 — request attempt 1/4 (the Overpass server may take a few minutes)
...
```
