from __future__ import annotations

import json
import platform
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .areas import Area, resolve_area
from .boundary import boundary_identity, clip_points, load_boundary
from .industry import tag_places
from .llm import LLMClassifier
from .reconcile import reconcile
from .sources import ensure, fetch_overture, load_prepared_area_osm

ProgressCallback = Callable[[str], None]


def _say(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)


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
            "OpenStreetMap / Geofabrik",
            "Contains information from OpenStreetMap contributors, available under ODbL 1.0.",
            "Philippines extract obtained from Geofabrik GmbH.",
            "https://www.openstreetmap.org/copyright",
            "https://download.geofabrik.de/asia/philippines.html",
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
        "Geofabrik extract: https://download.geofabrik.de/asia/philippines.html\n"
        "ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/\n\n"
        "Individual Overture-origin source content retains its applicable upstream provider "
        "terms. See ATTRIBUTION.txt and the per-row source_licenses field.\n"
    )


def run_pipeline(
    area_slug: str,
    *,
    areas_file: Path | None = None,
    root: Path = Path("."),
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
    refresh_geofabrik: bool = False,
    clip: bool = True,
    use_llm: bool = False,
    progress: ProgressCallback | None = None,
) -> tuple[Path, dict[str, object]]:
    started = time.monotonic()
    root = root.resolve()

    _say(progress, f"Resolving area: {area_slug}")
    area = resolve_area(area_slug, areas_file)
    _say(progress, f"Area: {area.name} ({area.slug})")

    cache_base = (cache_dir or root / ".sigma-cache").resolve()
    cache_root = cache_base / area.slug
    out_root = (output_dir or root / "output").resolve() / area.slug
    cache_root.mkdir(parents=True, exist_ok=True)
    out_root.mkdir(parents=True, exist_ok=True)

    if use_llm and not LLMClassifier.is_configured():
        raise RuntimeError(
            "LLM classification is enabled, but SIGMA_LLM_API_KEY is not installed. "
            "Run setup-llm.ps1 from the repository to add an OpenAI API key, then open "
            "a new PowerShell window. Otherwise run the normal command without --llm."
        )

    _say(progress, "[1/8] Preparing Geofabrik Philippines OSM extract")
    pbf_file = ensure(
        cache_base,
        refresh=refresh_geofabrik,
        progress=progress,
    )

    _say(progress, "[2/8] Loading prepared all-LGU OSM cache")
    osm, osm_source_version, osm_fallback = load_prepared_area_osm(
        cache_base=cache_base,
        pbf_file=pbf_file,
        area_slug=area.slug,
        areas_file=areas_file,
        progress=progress,
    )

    _say(progress, "[3/8] Acquiring Overture Places")
    overture = fetch_overture(
        area.bbox,
        cache_root / "overture.parquet",
        refresh=refresh,
        progress=progress,
    )

    _say(progress, "[4/8] Loading exact administrative boundary")
    boundary = load_boundary(area)
    boundary_report = _boundary_report(area, boundary)

    if clip:
        _say(
            progress,
            f"[5/8] Verifying exact boundary clip "
            f"(OSM {len(osm):,}, Overture {len(overture):,})",
        )
        osm_before = len(osm)
        overture_before = len(overture)
        osm = clip_points(osm, boundary)
        overture = clip_points(overture, boundary)
        _say(
            progress,
            f"Boundary verification complete — OSM {osm_before:,}→{len(osm):,}, "
            f"Overture {overture_before:,}→{len(overture):,}",
        )
    else:
        _say(progress, "[5/8] Boundary clipping disabled")

    _say(progress, "[6/8] Reconciling OSM and Overture observations")
    canonical = reconcile(osm, overture, boundary=boundary if clip else None)
    matched_two_source = (
        int((canonical["source_count"] == 2).sum()) if len(canonical) else 0
    )
    _say(
        progress,
        f"Reconciliation complete — {len(canonical):,} canonical POIs, "
        f"{matched_two_source:,} matched across both sources",
    )

    if clip and len(canonical):
        inside = canonical.geometry.covered_by(boundary)
        if not bool(inside.all()):
            raise RuntimeError(
                "canonical output contains coordinates outside the configured boundary"
            )

    mode = "rules + LLM fallback" if use_llm else "deterministic rules only"
    _say(progress, f"[7/8] Classifying POIs — {mode}")
    classifier = LLMClassifier.from_environment(cache_root / "llm.sqlite") if use_llm else None
    try:
        tagged = tag_places(canonical, llm=classifier)
    finally:
        if classifier is not None:
            classifier.close()

    unresolved = int((tagged["io80_code"].fillna("") == "").sum()) if len(tagged) else 0
    method_counts = (
        tagged["tag_method"].fillna("").value_counts().to_dict()
        if len(tagged)
        else {}
    )
    _say(
        progress,
        f"Classification complete — {int(method_counts.get('rule', 0)):,} rules, "
        f"{int(method_counts.get('llm', 0)):,} LLM, {unresolved:,} unresolved",
    )

    _say(progress, "[8/8] Writing output files")
    target = out_root / "pois.parquet"
    tagged.to_parquet(target, index=False)

    source_licenses = _terms(tagged["source_licenses"]) if len(tagged) else []
    overture_providers = _terms(tagged["overture_providers"]) if len(tagged) else []
    (out_root / "ATTRIBUTION.txt").write_text(_attribution_text(tagged), encoding="utf-8")
    (out_root / "DATABASE_LICENSE.txt").write_text(
        _database_license_text(source_licenses), encoding="utf-8"
    )

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
        "sources": ["osm-geofabrik-prepared", "overture"],
        "counts": {
            "osm": len(osm),
            "overture": len(overture),
            "canonical": len(canonical),
            "matched_two_source": matched_two_source,
            "tagged": len(tagged) - unresolved,
            "unresolved": unresolved,
        },
        "classification": {
            "llm_enabled": classifier is not None,
            "llm_model": classifier.model if classifier is not None else None,
            "llm_base_url": classifier.base_url if classifier is not None else None,
            "tagged_by_rule": int(method_counts.get("rule", 0)),
            "tagged_by_llm": int(method_counts.get("llm", 0)),
            "unresolved": int(method_counts.get("unresolved", 0)),
            "deterministic_first": True,
            "io80_primary": True,
            "io16_derived_from_io80": True,
            "io80_code_71_allowed": True,
        },
        "osm_acquisition": {
            "provider": "Geofabrik",
            "preparation": (
                "resumable checkpoints; one national scan per Geofabrik version; "
                "all LGU caches"
            ),
            "pbf": str(pbf_file),
            "pbf_size_bytes": pbf_file.stat().st_size,
            "prepared_source_version": osm_source_version,
            "fallback_to_previous_complete_version": bool(osm_fallback),
            "geofabrik_refreshed_for_run": bool(refresh_geofabrik),
        },
        "licensing": {
            "software": "Proprietary",
            "database_license": (
                "ODbL-1.0" if "ODbL-1.0" in source_licenses else None
            ),
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
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _say(
        progress,
        f"Output complete — {target} ({report['elapsed_seconds']:.1f}s total)",
    )
    return target, report
