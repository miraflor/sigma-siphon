from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd
from rapidfuzz.fuzz import ratio, token_sort_ratio
from shapely.geometry import Point

from .licensing import join_terms
from .text import clean_text, fold

EARTH_RADIUS_M = 6_371_008.8
GENERIC = {
    "market", "school", "hospital", "church", "store", "shop", "office",
    "restaurant", "pharmacy", "terminal",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    left: int
    right: int
    distance_m: float
    name_score: float
    strength: float


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    a1 = math.radians(lat1)
    a2 = math.radians(lat2)
    dlat = a2 - a1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def name_similarity(a: object, b: object) -> float:
    x, y = fold(a), fold(b)
    if not x or not y:
        return 0.0
    return max(ratio(x, y), token_sort_ratio(x, y)) / 100.0


def _accepted(distance_m: float, score: float, a: object, b: object) -> bool:
    left, right = fold(a), fold(b)
    if not left or not right or distance_m > 120.0:
        return False
    generic = left in GENERIC or right in GENERIC or len(left) <= 4 or len(right) <= 4
    if generic:
        return distance_m <= 15.0 and score >= 0.99
    if distance_m <= 20.0:
        return score >= 0.70
    if distance_m <= 50.0:
        return score >= 0.82
    if distance_m <= 90.0:
        return score >= 0.90
    return score >= 0.94


def _grid_key(lon: float, lat: float, cell_deg: float = 0.0012) -> tuple[int, int]:
    return (math.floor(lon / cell_deg), math.floor(lat / cell_deg))


def _candidate_pairs(osm: pd.DataFrame, overture: pd.DataFrame) -> list[Candidate]:
    grid: dict[tuple[int, int], list[int]] = {}
    for idx, row in overture.iterrows():
        grid.setdefault(_grid_key(float(row.lon), float(row.lat)), []).append(idx)

    candidates: list[Candidate] = []
    for li, left in osm.iterrows():
        gx, gy = _grid_key(float(left.lon), float(left.lat))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for ri in grid.get((gx + dx, gy + dy), ()):
                    right = overture.loc[ri]
                    distance = haversine_m(
                        float(left.lon), float(left.lat), float(right.lon), float(right.lat)
                    )
                    if distance > 120.0:
                        continue
                    score = name_similarity(left["name"], right["name"])
                    if not _accepted(distance, score, left["name"], right["name"]):
                        continue
                    strength = 0.82 * score + 0.18 * (1.0 - distance / 120.0)
                    candidates.append(Candidate(li, ri, distance, score, strength))
    return sorted(candidates, key=lambda c: (-c.strength, c.distance_m, c.left, c.right))


def _poi_id(source_ids: list[str]) -> str:
    value = "|".join(sorted(source_ids)).encode("utf-8")
    return "ss_" + hashlib.sha256(value).hexdigest()[:20]


def _pick_name(a: str, b: str) -> str:
    def quality(value: str) -> tuple[int, int, str]:
        key = fold(value)
        return (len(key.split()), len(key), key)
    return max((a, b), key=quality)


def _single(row: pd.Series) -> dict[str, object]:
    sid = str(row.source_id)
    return {
        "poi_id": _poi_id([f"{row.source}:{sid}"]),
        "name": str(row["name"]),
        "category": clean_text(row.get("category")),
        "lon": float(row.lon),
        "lat": float(row.lat),
        "source_count": 1,
        "sources": str(row.source),
        "osm_id": sid if row.source == "osm" else "",
        "overture_id": sid if row.source == "overture" else "",
        "aliases": [],
        "match_distance_m": None,
        "match_name_score": None,
        "source_licenses": join_terms([row.get("upstream_license")]),
        "overture_providers": join_terms([row.get("overture_providers")]),
    }


def reconcile(osm: gpd.GeoDataFrame, overture: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Resolve likely cross-source duplicates while preserving unmatched observations."""
    osm = osm.reset_index(drop=True)
    overture = overture.reset_index(drop=True)
    candidates = _candidate_pairs(osm, overture)
    used_left: set[int] = set()
    used_right: set[int] = set()
    rows: list[dict[str, object]] = []

    for candidate in candidates:
        if candidate.left in used_left or candidate.right in used_right:
            continue
        left = osm.loc[candidate.left]
        right = overture.loc[candidate.right]
        used_left.add(candidate.left)
        used_right.add(candidate.right)
        name = _pick_name(str(left["name"]), str(right["name"]))
        aliases = sorted({str(left["name"]), str(right["name"])} - {name})
        lon = (float(left.lon) + float(right.lon)) / 2.0
        lat = (float(left.lat) + float(right.lat)) / 2.0
        rows.append(
            {
                "poi_id": _poi_id([f"osm:{left.source_id}", f"overture:{right.source_id}"]),
                "name": name,
                "category": " | ".join(
                    dict.fromkeys(
                        x
                        for x in (
                            clean_text(left.get("category")),
                            clean_text(right.get("category")),
                        )
                        if x
                    )
                ),
                "lon": lon,
                "lat": lat,
                "source_count": 2,
                "sources": "osm|overture",
                "osm_id": str(left.source_id),
                "overture_id": str(right.source_id),
                "aliases": aliases,
                "match_distance_m": round(candidate.distance_m, 3),
                "match_name_score": round(candidate.name_score, 4),
                "source_licenses": join_terms([
                    left.get("upstream_license"), right.get("upstream_license")
                ]),
                "overture_providers": join_terms([
                    left.get("overture_providers"), right.get("overture_providers")
                ]),
            }
        )

    for idx, row in osm.iterrows():
        if idx not in used_left:
            rows.append(_single(row))
    for idx, row in overture.iterrows():
        if idx not in used_right:
            rows.append(_single(row))

    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=[
            "poi_id", "name", "category", "lon", "lat", "source_count", "sources",
            "osm_id", "overture_id", "aliases", "match_distance_m", "match_name_score",
            "source_licenses", "overture_providers",
        ])
    return gpd.GeoDataFrame(
        frame,
        geometry=[
            Point(xy)
            for xy in zip(frame.get("lon", []), frame.get("lat", []), strict=False)
        ],
        crs="EPSG:4326",
    )
