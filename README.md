# Sigma Siphon

A compact Philippine POI pipeline that acquires OpenStreetMap and Overture Places data, clips it to a configured area, reconciles likely duplicate places, and tags the resulting POIs to the 2018 Philippine input-output industries at IO80 and IO16 resolution.

Sigma Siphon is designed as one pipeline with one normal command:

```text
area -> acquire -> clip -> reconcile -> IO80 classify -> derive IO16 -> GeoParquet
```

## Scope

The area catalog contains one canonical record for every Philippine city and municipality in the current PSGC, plus exactly three composite acquisition areas: Metro Manila, Metro Cebu, and Metro Davao. Each locality has one boundary geometry and one 10-digit PSGC code; the PSGC is accepted as an alias for the locality. Composite areas contain fixed member PSGC codes and dissolve those locality geometries at runtime; they are not additional PSGC localities.

Administrative clipping geometry is stored in one lightweight GeoPackage generated from the simplified geoBoundaries Philippines ADM3 layer. `config/areas.yml` is generated from the same boundary build so the YAML and GeoPackage stay synchronized.

## Data sources

Only two acquisition sources are used:

1. **OpenStreetMap**, queried through an explicitly configured Overpass endpoint.
2. **Overture Maps Places**, streamed through the official `overturemaps` Python package.

No third POI source, account, token, downloader, or dataset connector is present. Overture records from the provider intentionally excluded by this project are dropped during ingestion rather than propagated into the output.

## Commercial deployment

**Sigma Siphon itself is proprietary, closed-source commercial software.** Copyright is retained by the owner and no right to copy, modify, redistribute, sublicense, or sell the repository is granted except through a separate written agreement. The licenses of third-party dependencies and acquired data remain separate and continue to apply to those components.

For OSM acquisition, Sigma Siphon deliberately has **no volunteer public Overpass default**. Configure a self-hosted or paid endpoint whose service terms permit your commercial workload:

```powershell
$env:SIGMA_OSM_OVERPASS_URL="https://your-overpass.example/api/interpreter"
$env:SIGMA_OSM_USER_AGENT="SigmaSiphon/0.1.2 (+https://your-company.example/contact)"
```

The data licenses are separate from the software license. OSM data are ODbL 1.0. Because this pipeline reconciles OSM with another POI database into canonical records, an output containing OSM-derived records is conservatively distributed as an **ODbL 1.0 database**. Overture-origin content retains its applicable provider terms. Every run writes both `ATTRIBUTION.txt` and `DATABASE_LICENSE.txt`, and the final GeoParquet retains `source_licenses` and `overture_providers` columns.

See [DATA_LICENSES.md](DATA_LICENSES.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Install

```powershell
conda env create -f environment.yml
conda activate sigma-siphon
```

Or with an existing Python 3.11+ environment:

```powershell
python -m pip install -e .
```

## Configure the classifier

The classifier uses any OpenAI-compatible chat-completions endpoint:

```powershell
$env:SIGMA_LLM_MODEL="your-model"
$env:SIGMA_LLM_API_KEY="your-key"
$env:SIGMA_LLM_BASE_URL="https://your-compatible-endpoint/v1"  # optional for OpenAI
```

Credentials are read only from environment variables. `.env` is ignored by Git.

The model/provider service has its own commercial terms. The repository's software-license audit does not grant rights to a hosted model or API service.

## Run

Check configuration:

```powershell
sigma-siphon doctor
```

List areas:

```powershell
sigma-siphon areas
```

Run the full pipeline:

```powershell
sigma-siphon run quezon_city
# or a documented composite area
sigma-siphon run metro_manila
```

Refresh acquisition caches:

```powershell
sigma-siphon run 1381300000 --refresh
```

Disable LLM classification and retain only high-confidence deterministic tags:

```powershell
sigma-siphon run quezon_city --no-llm
```

## Boundaries

`data/boundaries/areas.gpkg` contains one polygon per city or municipality and is keyed by `psgc_code`. `config/areas.yml` contains 1,642 canonical locality entries plus the three composite areas. A locality's 10-digit PSGC is stored in `aliases` and resolves to the same area. Duplicate locality names receive province-qualified slugs where possible. Composite boundaries reuse the same GeoPackage rows and are unions of their fixed member PSGCs, so no duplicate metro geometry is stored.

Regenerate both files with `scripts/build_areas.py`. The build uses the current official PSGC workbook for names/codes and the simplified geoBoundaries Philippines ADM3 layer for output geometry. A PSGC-keyed historical boundary snapshot is used only as a spatial crosswalk to avoid ambiguous name matching.

Example generated entry:

```yaml
quezon_city:
  name: Quezon City
  kind: city
  psgc_code: "1381300000"
  aliases: ["1381300000"]
  bbox: [120.9, 14.5, 121.2, 14.8]
  boundary:
    gpkg: ../data/boundaries/areas.gpkg
    layer: areas
    field: psgc_code
    value: "1381300000"
```

## Output

A successful run writes:

```text
output/<area>/pois.parquet
output/<area>/run.json
output/<area>/ATTRIBUTION.txt
output/<area>/DATABASE_LICENSE.txt
```

`pois.parquet` contains canonical location and reconciliation fields, source IDs, source-license provenance, and:

- `io80_code`, `io80_label`;
- `io16_code`, `io16_label`;
- `tag_method`, `tag_confidence`, `tag_reason`.

IO80 is the primary classification. IO16 is derived deterministically from IO80 so the two resolutions cannot conflict.

## IO classification

The classifier is rules-first only where source evidence is unusually strong; otherwise the LLM does the classification work directly against the 80-sector catalog.

All 80 codes are valid classification outputs. **Code 71 is allowed.** It is described locally as `Dwelling-ownership services` and rolls up to IO16 code 11. The prompt distinguishes it from code 70, which covers other real-estate services.

The local labels are independently worded descriptors of the code structure rather than copied publication prose. Numeric code identities and rollups are retained for interoperability.

## Reconciliation

OSM and Overture observations are linked only when both geography and normalized names satisfy a distance-sensitive threshold. Very short and generic names are treated more strictly. Candidate matches are processed strongest-first, one observation per source, and the final row retains match distance and name score.

The final canonical coordinates for a two-source match are the midpoint of the two representative points. This is a reconciliation coordinate, not a surveyed location.

## Caching

Source caches live under `.sigma-cache/<area>/`. Cached source files are reused only when they contain the current normalized licensing/provenance schema; an older cache is automatically reacquired.
Overture ingestion is license-fail-closed: records from an excluded or unrecognized provider are not admitted until that provider is explicitly audited.

LLM decisions are cached by POI evidence **and** by model endpoint, model name, classification-policy version, and catalog fingerprint. Changing the catalog or classification policy therefore cannot silently reuse stale decisions.

## Dependency policy

The direct dependency set has been reviewed for commercial-use-compatible licenses. CI runs:

```powershell
python tools/check_dependency_policy.py
```

If an audited build, runtime, or development dependency specification changes—including its accepted version range—that check fails until the license audit is intentionally updated. This does not replace a release-time software bill of materials for a packaged binary; see `THIRD_PARTY_NOTICES.md`.

## Development

```powershell
python -m pip install -e ".[dev]"
python tools/check_dependency_policy.py
python -m pytest -q
ruff check .
```

The unit tests are network-free.
