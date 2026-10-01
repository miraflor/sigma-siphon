# Resumable OSM preparation

Sigma Siphon 0.2.0 keeps durable checkpoints for Geofabrik preparation.

For a Geofabrik version such as `261001`, work is stored under:

```text
.sigma-cache/geofabrik/prepared/261001.incomplete/
    state.json
    national-pois.parquet
    boundaries.parquet
    assignments.parquet
    assignment-metrics.json
    national-pois-assigned.parquet
    areas/
        ...
```

A rerun reuses every valid checkpoint it finds.

## Resume guarantees

- Geofabrik `.osm.pbf` downloads retain a version-specific `.part` file.
- If the server supports HTTP Range, the download resumes from the partial byte count.
- If the server ignores Range, Sigma Siphon safely restarts that download.
- The libosmium nationwide scan restarts if interrupted mid-scan.
- Once `national-pois.parquet` exists and validates as Parquet, the national scan is not repeated.
- Boundary preparation is checkpointed.
- Nationwide POI-to-LGU assignment is checkpointed.
- Each LGU Parquet file is independently atomic and independently resumable.
- Composite caches are independently resumable.
- Final validation must pass before the `.incomplete` directory is promoted to the complete version.
- The previous complete prepared version remains live until the new version validates.
- If new-version preparation fails and a previous complete cache exists, an area run falls back to the previous complete cache and reports that fallback.

## Example after interruption

```text
→ OSM prepared cache: resumable preparation for Geofabrik 261001
→ OSM resume: nationwide POI extraction already complete — 285,421 rows
→ OSM resume: prepared LGU boundaries already complete — 1,642 rows
→ OSM resume: nationwide LGU assignment already complete — 283,997 assigned
→ OSM resume: 843/1,642 LGU caches already complete
→ OSM checkpoint: LGU caches 850/1,642
...
```

Only the currently running libosmium national scan lacks a safe mid-file resume point.
