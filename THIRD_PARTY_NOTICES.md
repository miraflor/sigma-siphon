# Third-party software license audit

Audit date: **2026-10-03**.

The project intentionally depends only on software whose reviewed licenses permit commercial use. No dependency is intentionally subject to a research-only, non-commercial, or source-data-use restriction.

## Declared dependencies

| Dependency | Role | Reviewed license | Commercial use |
|---|---|---|---|
| Hatchling | build backend | MIT | Yes |
| GeoPandas | geospatial frames/I/O | BSD-3-Clause | Yes |
| OpenAI Python | OpenAI-compatible client | Apache-2.0 | Yes |
| NumPy | numerical arrays for lexical retrieval | BSD-3-Clause | Yes |
| overturemaps | Overture data client | MIT | Yes |
| pandas | tabular processing | BSD-3-Clause | Yes |
| PyArrow | Parquet / Arrow | Apache-2.0 | Yes |
| PyYAML | configuration | MIT | Yes |
| RapidFuzz | name similarity | MIT | Yes |
| Requests | HTTP client | Apache-2.0 | Yes |
| scikit-learn | TF-IDF lexical retrieval | BSD-3-Clause | Yes |
| Rich | CLI rendering | MIT | Yes |
| Shapely | geometry | BSD-3-Clause | Yes |
| Typer | CLI | MIT | Yes |
| pytest | tests | MIT | Yes |
| Ruff | linting | MIT | Yes |

The audited build, runtime, and development dependency specifications are guarded by `tools/check_dependency_policy.py`; changing a package or its accepted version range requires an explicit re-audit.

## Important transitive/native components

Commercial use is also allowed by the principal transitive/native license families encountered in this stack, but distribution obligations differ:

- **NumPy** is principally BSD-3-Clause and may ship platform wheels containing components under BSD, LGPL, and GPL-with-GCC-runtime-exception terms. Those licenses permit commercial use; preserve the notices supplied with the wheel when redistributing it.
- **Shapely** uses **GEOS**, which is LGPL-2.1. Commercial proprietary applications may use LGPL libraries, but binary redistribution must respect LGPL requirements.
- GeoPandas commonly brings **pyogrio** and **pyproj/PROJ**, which use permissive MIT-style licensing.
- The OpenAI client brings HTTP/data-validation dependencies such as HTTPX-family, Pydantic and AnyIO, whose reviewed licenses are BSD-3-Clause or MIT-class permissive licenses.
- Requests brings `charset-normalizer`, `idna`, `urllib3` and `certifi`; these are commercially usable open-source components but their notices should be retained in a redistributed bundled environment.
- Overture's client brings components such as `orjson`, `tqdm`, `pyfiglet`, `colorama`, NumPy, PyArrow and Shapely. Some use MPL/LGPL-style terms; these permit commercial use but can impose file-level or binary-redistribution obligations.

## What this audit covers

This audit covers the Python software dependency stack, not external service contracts. In particular:

- an Overpass hosting provider may impose its own paid/commercial service terms;
- an LLM/API/model provider may impose separate commercial terms, acceptable-use rules, and data-processing terms; and
- source-data licenses are handled separately in `DATA_LICENSES.md`.

For a shipped executable, container, desktop bundle, or installer, generate a software bill of materials from the **actual locked environment** and carry the license/NOTICE files included by those installed distributions. Do not assume this Markdown summary replaces those notices.
