from __future__ import annotations

import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .areas import Area, resolve_area
from .boundary import boundary_identity, clip_points, load_boundary
from .industry import tag_places
from .llm import LLMClassifier
from .reconcile import reconcile
from .sources import fetch_osm, fetch_overture


def _boundary_report(area: Area, geometry) -> dict[str, object]:
    return boundary_identity(area, geometry)


def _terms(series) -> list[str]:
    values: set[str] = set()
    for value in series.fillna(""):
        values.update(part.strip() for part in str(value).split("|") if part.strip())
    return sorted(values)


def _attribution_text(tagged) -> str:
    providers = set(_terms(tagged["overture_providers"])) if len(tagged) else set()
    return "\n".join(
        [
            "Sigma Siphon output source attribution",
            "",
            "OpenStreetMap",
            "Contains information from OpenStreetMap contributors, available under ODbL 1.0.",
            "https://www.openstreetmap.org/copyright",
            "",
            "Overture Maps Places",
            "Contains data obtained from Overture Maps Foundation Places.",
            "https://docs.overturemaps.org/attribution/",
            "",
            "Observed Overture providers: " + (", ".join(sorted(providers)) or "none recorded"),
            "",
            "Database note",
            (
                "When OSM-derived records are present, this fused POI database is "
                "distributed under ODbL 1.0 as a conservative compliance posture "
                "for a reconciled database."
            ),
            "",
            "Software",
            (
                "Sigma Siphon software is proprietary and all rights are reserved. "
                "Third-party software and source-data licensing are separate."
            ),
            "",
        ]
    )


def _database_license_text(source_licenses: list[str]) -> str:
    if "ODbL-1.0" not in source_licenses:
        return "No ODbL-covered source records were observed in this output.\n"
    return (
        "DATABASE LICENSE NOTICE\n\n"
        "This fused POI database is distributed under the Open Database License (ODbL) 1.0 "
        "as the project's conservative compliance posture for a reconciled database containing "
        "OpenStreetMap-derived records.\n\n"
        "OpenStreetMap attribution: © OpenStreetMap contributors.\n"
        "ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/\n\n"
        "Individual Overture-origin source content retains its applicable upstream provider terms. "
        "See ATTRIBUTION.txt and the per-row source_licenses field.\n"
    )


def run_pipeline(
    area_slug: str,
    *,
    areas_file: Path | None = None,
    root: Path = Path("."),
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
    clip: bool = True,
    use_llm: bool = True,
) -> tuple[Path, dict[str, object]]:
    started = time.monotonic()
    root = root.resolve()
    area = resolve_area(area_slug, areas_file)
    cache_root = (cache_dir or root / ".sigma-cache").resolve() / area.slug
    out_root = (output_dir or root / "output").resolve() / area.slug
    cache_root.mkdir(parents=True, exist_ok=True)
    out_root.mkdir(parents=True, exist_ok=True)

    osm = fetch_osm(area.bbox, cache_root / "osm.parquet", refresh=refresh)
    overture = fetch_overture(area.bbox, cache_root / "overture.parquet", refresh=refresh)

    boundary = load_boundary(area)
    boundary_report = _boundary_report(area, boundary)
    if clip:
        osm = clip_points(osm, boundary)
        overture = clip_points(overture, boundary)

    canonical = reconcile(osm, overture, boundary=boundary if clip else None)
    if clip and len(canonical):
        inside = canonical.geometry.covered_by(boundary)
        if not bool(inside.all()):
            raise RuntimeError(
                "canonical output contains coordinates outside the configured boundary"
            )

    classifier = LLMClassifier.from_environment(cache_root / "llm.sqlite") if use_llm else None
    try:
        tagged = tag_places(canonical, llm=classifier)
    finally:
        if classifier is not None:
            classifier.close()

    target = out_root / "pois.parquet"
    tagged.to_parquet(target, index=False)

    source_licenses = _terms(tagged["source_licenses"]) if len(tagged) else []
    overture_providers = _terms(tagged["overture_providers"]) if len(tagged) else []
    (out_root / "ATTRIBUTION.txt").write_text(_attribution_text(tagged), encoding="utf-8")
    (out_root / "DATABASE_LICENSE.txt").write_text(
        _database_license_text(source_licenses), encoding="utf-8"
    )

    unresolved = int((tagged["io80_code"].fillna("") == "").sum()) if len(tagged) else 0
    report: dict[str, object] = {
        "package": "sigma-siphon",
        "version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "area": {
            "slug": area.slug,
            "name": area.name,
            "kind": area.kind,
            "psgc_code": area.psgc_code,
            "bbox": list(area.bbox),
        },
        "boundary": boundary_report,
        "clip_enabled": bool(clip),
        "sources": ["osm", "overture"],
        "counts": {
            "osm": len(osm),
            "overture": len(overture),
            "canonical": len(canonical),
            "matched_two_source": (
                int((canonical["source_count"] == 2).sum()) if len(canonical) else 0
            ),
            "tagged": len(tagged) - unresolved,
            "unresolved": unresolved,
        },
        "classification": {
            "llm_enabled": classifier is not None,
            "llm_model": classifier.model if classifier is not None else None,
            "llm_base_url": classifier.base_url if classifier is not None else None,
            "deterministic_first": True,
            "io80_primary": True,
            "io16_derived_from_io80": True,
            "io80_code_71_allowed": True,
        },
        "licensing": {
            "software": "Proprietary",
            "database_license": "ODbL-1.0" if "ODbL-1.0" in source_licenses else None,
            "source_licenses_observed": source_licenses,
            "overture_providers_observed": overture_providers,
            "osm_public_distribution_note": (
                "The fused database is treated as ODbL-1.0 when OSM-derived records are present"
            ),
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output": str(target),
    }
    (out_root / "run.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return target, report
