from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

from ..licensing import OSM_LICENSE
from ..settings import DEFAULT_OSM_OVERPASS_URL, DEFAULT_OSM_USER_AGENT
from ..text import clean_text, combine
from .cache import cache_matches_bbox, write_cache_identity

ProgressCallback = Callable[[str], None]

POI_KEYS = (
    "amenity",
    "shop",
    "office",
    "craft",
    "tourism",
    "leisure",
    "healthcare",
    "industrial",
    "man_made",
    "club",
    "emergency",
    "public_transport",
)

# Avoid turning named railway lines, tracks, runways, etc. into establishments.
VALUE_SELECTORS = {
    "aeroway": ("aerodrome", "terminal"),
    "railway": ("station", "halt", "tram_stop", "subway_entrance"),
}
CATEGORY_KEYS = (*POI_KEYS, *VALUE_SELECTORS)


def _emit(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _tiles(bbox: tuple[float, float, float, float], span: float = 0.18):
    west, south, east, north = bbox
    y = south
    while y < north:
        y2 = min(north, y + span)
        x = west
        while x < east:
            x2 = min(east, x + span)
            yield (x, y, x2, y2)
            x = x2
        y = y2


def _query(bbox: tuple[float, float, float, float]) -> str:
    west, south, east, north = bbox
    s = f"{south},{west},{north},{east}"
    selectors = [f'nwr["name"]["{key}"]({s});' for key in POI_KEYS]
    for key, values in VALUE_SELECTORS.items():
        pattern = "|".join(values)
        selectors.append(f'nwr["name"]["{key}"~"^({pattern})$"]({s});')
    return "[out:json][timeout:180];(\n" + "\n".join(selectors) + "\n);out center tags;"


def _commercial_endpoint() -> str:
    """Return the built-in Overpass endpoint unless deployment overrides it."""
    return (
        os.getenv("SIGMA_OSM_OVERPASS_URL", DEFAULT_OSM_OVERPASS_URL).strip()
        or DEFAULT_OSM_OVERPASS_URL
    )


def _user_agent() -> str:
    return (
        os.getenv("SIGMA_OSM_USER_AGENT", DEFAULT_OSM_USER_AGENT).strip()
        or DEFAULT_OSM_USER_AGENT
    )


def _download_tile(
    bbox: tuple[float, float, float, float],
    *,
    session: requests.Session,
    endpoint: str,
    user_agent: str,
    retries: int = 4,
    progress: ProgressCallback | None = None,
    tile_label: str = "tile",
) -> dict:
    query = _query(bbox)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        _emit(
            progress,
            f"OSM: {tile_label} — request attempt {attempt}/{retries} "
            "(the Overpass server may take a few minutes)",
        )
        try:
            response = session.post(
                endpoint,
                data={"data": query},
                timeout=(20, 240),
                headers={"User-Agent": user_agent},
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                delay = 2.0 * attempt
                _emit(
                    progress,
                    f"OSM: {tile_label} attempt {attempt} failed "
                    f"({type(exc).__name__}); retrying in {delay:.0f}s",
                )
                time.sleep(delay)
    raise RuntimeError(f"OSM request failed after {retries} attempts: {last_error}")


def _category(tags: dict[str, object]) -> str:
    parts = []
    for key in CATEGORY_KEYS:
        value = clean_text(tags.get(key))
        if value:
            parts.append(f"{key}={value}")
    for key in ("cuisine", "brand", "operator"):
        value = clean_text(tags.get(key))
        if value:
            parts.append(f"{key}={value}")
    return " | ".join(parts)


def fetch_osm(
    bbox: tuple[float, float, float, float],
    cache_file: Path,
    *,
    refresh: bool = False,
    progress: ProgressCallback | None = None,
) -> gpd.GeoDataFrame:
    """Fetch named OSM POIs using the built-in or overridden Overpass endpoint."""
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
            _emit(progress, f"OSM: using compatible cache — {len(cached):,} POIs")
            return cached

    endpoint = _commercial_endpoint()
    user_agent = _user_agent()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict[str, object]] = {}

    tiles = list(_tiles(bbox))
    _emit(progress, f"OSM: downloading {len(tiles)} tile(s)")

    with requests.Session() as session:
        for tile_number, tile in enumerate(tiles, start=1):
            label = f"tile {tile_number}/{len(tiles)}"
            payload = _download_tile(
                tile,
                session=session,
                endpoint=endpoint,
                user_agent=user_agent,
                progress=progress,
                tile_label=label,
            )
            elements = payload.get("elements", [])
            for element in elements:
                tags = element.get("tags") or {}
                name = combine(tags.get("name"), tags.get("name:en"))
                if not name:
                    continue
                lon = element.get("lon")
                lat = element.get("lat")
                center = element.get("center") or {}
                lon = lon if lon is not None else center.get("lon")
                lat = lat if lat is not None else center.get("lat")
                if lon is None or lat is None or not (
                    math.isfinite(float(lon)) and math.isfinite(float(lat))
                ):
                    continue
                source_id = f"{element.get('type', 'object')}/{element.get('id')}"
                rows[source_id] = {
                    "source": "osm",
                    "source_id": source_id,
                    "name": name,
                    "category": _category(tags),
                    "lon": float(lon),
                    "lat": float(lat),
                    "provenance": "OpenStreetMap contributors",
                    "upstream_license": OSM_LICENSE,
                    "overture_providers": "",
                }
            _emit(
                progress,
                f"OSM: {label} received {len(elements):,} objects; "
                f"{len(rows):,} accepted named POIs so far",
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
    ]
    frame = pd.DataFrame(rows.values())
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    gdf = gpd.GeoDataFrame(
        frame,
        geometry=[
            Point(xy)
            for xy in zip(frame.get("lon", []), frame.get("lat", []), strict=False)
        ],
        crs="EPSG:4326",
    )
    gdf.to_parquet(cache_file, index=False)
    write_cache_identity(cache_file, bbox)
    _emit(progress, f"OSM: complete — {len(gdf):,} POIs cached")
    return gdf
