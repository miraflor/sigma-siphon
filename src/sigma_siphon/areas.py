from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class BoundarySpec:
    gpkg: Path
    layer: str | None = None
    field: str | None = None
    value: str | int | float | None = None


@dataclass(frozen=True, slots=True)
class Area:
    slug: str
    name: str
    kind: str
    bbox: tuple[float, float, float, float]
    psgc_code: str | None = None
    boundary: BoundarySpec | None = None


def default_areas_path() -> Path:
    return Path(resources.files("sigma_siphon").joinpath("data", "areas.yml"))


def _boundary(value: Any, base: Path) -> BoundarySpec | None:
    if value in (None, ""):
        return None
    if not isinstance(value, dict) or not value.get("gpkg"):
        raise ValueError("boundary must be null or a mapping with a gpkg path")
    gpkg = Path(str(value["gpkg"]))
    if not gpkg.is_absolute():
        gpkg = (base / gpkg).resolve()
    return BoundarySpec(
        gpkg=gpkg,
        layer=str(value["layer"]) if value.get("layer") else None,
        field=str(value["field"]) if value.get("field") else None,
        value=value.get("value"),
    )


def load_areas(path: Path | None = None) -> dict[str, Area]:
    path = (path or default_areas_path()).resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_areas = payload.get("areas")
    if not isinstance(raw_areas, dict):
        raise ValueError(f"{path}: expected an 'areas' mapping")

    out: dict[str, Area] = {}
    for slug, raw in raw_areas.items():
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: area {slug!r} must be a mapping")
        bbox = raw.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"{path}: area {slug!r} needs bbox [west, south, east, north]")
        west, south, east, north = (float(v) for v in bbox)
        if not (west < east and south < north):
            raise ValueError(f"{path}: invalid bbox for {slug!r}")
        out[str(slug)] = Area(
            slug=str(slug),
            name=str(raw.get("name") or slug),
            kind=str(raw.get("kind") or "area"),
            bbox=(west, south, east, north),
            psgc_code=str(raw["psgc_code"]) if raw.get("psgc_code") is not None else None,
            boundary=_boundary(raw.get("boundary"), path.parent),
        )
    return out


def resolve_area(slug: str, path: Path | None = None) -> Area:
    areas = load_areas(path)
    try:
        return areas[slug]
    except KeyError as exc:
        choices = ", ".join(sorted(areas))
        raise KeyError(f"unknown area {slug!r}; choose one of: {choices}") from exc
