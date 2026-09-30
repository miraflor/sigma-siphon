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
    value: str | int | float | tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class Area:
    slug: str
    name: str
    kind: str
    bbox: tuple[float, float, float, float]
    psgc_code: str | None = None
    province: str | None = None
    aliases: tuple[str, ...] = ()
    members: tuple[str, ...] = ()
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
    if value.get("value") is not None and value.get("values") is not None:
        raise ValueError("boundary cannot define both value and values")
    boundary_value: str | int | float | tuple[str, ...] | None
    if value.get("values") is not None:
        values = value["values"]
        if not isinstance(values, list) or not values:
            raise ValueError("boundary values must be a non-empty list")
        boundary_value = tuple(str(v).strip() for v in values if str(v).strip())
        if not boundary_value:
            raise ValueError("boundary values must contain at least one value")
    else:
        boundary_value = value.get("value")
    return BoundarySpec(
        gpkg=gpkg,
        layer=str(value["layer"]) if value.get("layer") else None,
        field=str(value["field"]) if value.get("field") else None,
        value=boundary_value,
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

        aliases_raw = raw.get("aliases") or []
        if not isinstance(aliases_raw, list):
            raise ValueError(f"{path}: aliases for {slug!r} must be a list")
        aliases = tuple(str(v).strip() for v in aliases_raw if str(v).strip())

        members_raw = raw.get("members") or []
        if not isinstance(members_raw, list):
            raise ValueError(f"{path}: members for {slug!r} must be a list")
        members = tuple(str(v).strip() for v in members_raw if str(v).strip())

        out[str(slug)] = Area(
            slug=str(slug),
            name=str(raw.get("name") or slug),
            kind=str(raw.get("kind") or "area"),
            bbox=(west, south, east, north),
            psgc_code=str(raw["psgc_code"]) if raw.get("psgc_code") is not None else None,
            province=str(raw["province"]) if raw.get("province") else None,
            aliases=aliases,
            members=members,
            boundary=_boundary(raw.get("boundary"), path.parent),
        )
    return out


def resolve_area(value: str, path: Path | None = None) -> Area:
    areas = load_areas(path)

    # Canonical slug wins immediately.
    if value in areas:
        return areas[value]

    query = value.casefold().strip()
    matches: list[Area] = []
    for area in areas.values():
        candidates = {area.slug.casefold(), area.name.casefold()}
        candidates.update(alias.casefold() for alias in area.aliases)
        if query in candidates:
            matches.append(area)

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        labels = ", ".join(
            f"{area.slug} ({area.name}, PSGC {area.psgc_code})" for area in matches
        )
        raise KeyError(f"ambiguous area {value!r}; matches: {labels}")

    raise KeyError(
        f"unknown area {value!r}; use `sigma-siphon areas --search <name>` "
        "to find a locality or pass its 10-digit PSGC code"
    )
