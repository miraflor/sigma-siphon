from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import from_wkb

from ..licensing import overture_record_allowed, overture_terms
from ..text import clean_text, combine
from .cache import cache_matches_bbox, write_cache_identity

ProgressCallback = Callable[[str], None]


def _emit(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _primary_name(value: object) -> str:
    if isinstance(value, dict):
        primary = clean_text(value.get("primary"))
        common = value.get("common")
        if primary:
            return primary
        if isinstance(common, dict):
            for candidate in common.values():
                text = clean_text(candidate)
                if text:
                    return text
    return clean_text(value)


def _category(row: pd.Series) -> str:
    parts: list[str] = []
    for column in ("taxonomy", "categories"):
        value = row.get(column)
        if isinstance(value, dict):
            value = value.get("primary") or value.get("alternate")
        text = clean_text(value)
        if text:
            parts.append(text)
    basic = clean_text(row.get("basic_category"))
    if basic:
        parts.append(basic)
    return combine(*parts)


def _point_from_geometry(value: object):
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        geometry = from_wkb(bytes(value))
    else:
        geometry = value
    if geometry is None or geometry.is_empty:
        return None
    if geometry.geom_type == "Point":
        return geometry
    return geometry.representative_point()


def fetch_overture(
    bbox: tuple[float, float, float, float],
    cache_file: Path,
    *,
    refresh: bool = False,
    progress: ProgressCallback | None = None,
) -> gpd.GeoDataFrame:
    """Stream Overture Places for bbox and cache a normalized point layer."""
    required = {
        "source",
        "source_id",
        "name",
        "category",
        "lon",
        "lat",
        "upstream_license",
        "overture_providers",
    }
    if not refresh and cache_matches_bbox(cache_file, bbox):
        cached = gpd.read_parquet(cache_file)
        if required.issubset(cached.columns):
            _emit(progress, f"Overture: using compatible cache — {len(cached):,} POIs")
            return cached

    from overturemaps import record_batch_reader

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    _emit(
        progress,
        "Overture: opening Places stream "
        "(the first response may take a little while)",
    )
    reader = record_batch_reader("place", bbox=bbox, stac=True)
    records: list[dict[str, object]] = []
    batch_number = 0
    raw_total = 0

    if reader is not None:
        for batch_number, batch in enumerate(reader, start=1):
            table = batch.to_pandas()
            raw_total += len(table)
            before = len(records)
            for _, row in table.iterrows():
                status = clean_text(row.get("operating_status")).casefold()
                if status == "permanently_closed":
                    continue
                name = _primary_name(row.get("names"))
                if not name:
                    continue
                point = _point_from_geometry(row.get("geometry"))
                if point is None:
                    continue
                provenance = row.get("sources")
                providers, licenses = overture_terms(provenance)
                if not overture_record_allowed(providers):
                    continue
                source_id = clean_text(row.get("id"))
                if not source_id:
                    continue
                records.append(
                    {
                        "source": "overture",
                        "source_id": source_id,
                        "name": name,
                        "category": _category(row),
                        "lon": float(point.x),
                        "lat": float(point.y),
                        "provenance": clean_text(provenance),
                        "upstream_license": "|".join(licenses),
                        "overture_providers": "|".join(providers),
                        "geometry": point,
                    }
                )
            accepted = len(records) - before
            _emit(
                progress,
                f"Overture: batch {batch_number} — {len(table):,} rows read, "
                f"{accepted:,} accepted; {len(records):,} accepted total",
            )

    columns = [
        "source",
        "source_id",
        "name",
        "category",
        "lon",
        "lat",
        "provenance",
        "upstream_license",
        "overture_providers",
        "geometry",
    ]
    frame = pd.DataFrame(records)
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    gdf = gpd.GeoDataFrame(frame, geometry="geometry", crs="EPSG:4326")
    gdf.to_parquet(cache_file, index=False)
    write_cache_identity(cache_file, bbox)
    _emit(
        progress,
        f"Overture: complete — {raw_total:,} rows read across {batch_number} batch(es), "
        f"{len(gdf):,} POIs cached",
    )
    return gdf
