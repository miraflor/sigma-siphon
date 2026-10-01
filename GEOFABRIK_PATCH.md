# Geofabrik OSM acquisition patch

Sigma Siphon no longer depends on a public Overpass query server for normal OSM
acquisition.

The pipeline is:

```text
Geofabrik Philippines PBF
        ↓
local Osmium extraction
        ↓
exact boundary clipping

Overture Places
        ↓
exact boundary clipping

OSM + Overture
        ↓
reconciliation
        ↓
IO80 tagging
        ↓
IO16 derivation
        ↓
output
```

The national PBF is cached once at:

```text
.sigma-cache/geofabrik/philippines-latest.osm.pbf
```

Each area also has its own OSM extraction cache. A normal rerun therefore does
not rescan the national PBF unless that PBF changed or `--refresh` is requested.

The default Geofabrik freshness threshold is 7 days. If the local extract is at
least that far behind the current Geofabrik file, Sigma Siphon asks whether to
refresh it before OSM/Overture reconciliation.

Force a national refresh:

```powershell
sigma-siphon run pasig --refresh-geofabrik
```

Change the prompt threshold:

```powershell
sigma-siphon run pasig --geofabrik-max-age-days 3
```

`--refresh` and `--refresh-geofabrik` are separate:

- `--refresh` rebuilds/refetches area-level data.
- `--refresh-geofabrik` downloads the national Philippines PBF again.

LLM behavior is unchanged:

```powershell
sigma-siphon run pasig
```

is deterministic/rules-only, while:

```powershell
sigma-siphon run pasig --llm
```

adds the optional LLM fallback.
