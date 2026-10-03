# National OSM preparation cache

Sigma Siphon now scans the Philippines Geofabrik PBF once per Geofabrik version.

During that preparation pass it:

1. extracts all named nationwide OSM POI candidates;
2. loads all 1,642 city/municipality boundaries;
3. performs one nationwide spatial assignment;
4. writes one OSM cache for every city/municipality;
5. writes the three composite-area caches;
6. atomically marks the version complete only after all files are written.

The cache is versioned under:

```text
.sigma-cache/geofabrik/prepared/<YYMMDD>/
    national-pois.parquet
    national-pois-assigned.parquet
    manifest.json
    areas/
        pasig.parquet
        makati.parquet
        ...
```

A later:

```powershell
sigma-siphon run pasig
```

or:

```powershell
sigma-siphon run makati
```

does not rescan the Philippines PBF.

`--refresh` refreshes area-level Overture/downstream processing only.

`--refresh-geofabrik` downloads the new national PBF. A new Geofabrik version
then causes one new nationwide preparation pass and replaces the live prepared
version only after that pass completes successfully.
