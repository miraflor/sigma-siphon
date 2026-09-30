from __future__ import annotations

import geopandas as gpd
from shapely.geometry import box
from shapely.ops import unary_union

from .areas import Area

WGS84 = "EPSG:4326"


def load_boundary(area: Area):
    """Return the configured clipping geometry in WGS84, or the area's bbox polygon."""
    if area.boundary is None:
        return box(*area.bbox)

    spec = area.boundary
    if not spec.gpkg.exists():
        raise FileNotFoundError(f"boundary GeoPackage does not exist: {spec.gpkg}")
    frame = gpd.read_file(spec.gpkg, layer=spec.layer)
    if frame.empty:
        raise ValueError(f"boundary layer is empty: {spec.gpkg}")
    if spec.field:
        if spec.field not in frame.columns:
            raise ValueError(f"boundary field {spec.field!r} not found in {spec.gpkg}")
        values = frame[spec.field].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

        wanted_values = spec.value if isinstance(spec.value, tuple) else (spec.value,)
        wanted_values = tuple(str(v).strip() for v in wanted_values if v is not None)
        mask = values.isin(wanted_values)
        for wanted in wanted_values:
            if wanted.isdigit():
                mask |= values.str.replace(r"^0+", "", regex=True) == wanted.lstrip("0")
        frame = frame.loc[mask]
        if frame.empty:
            raise ValueError(
                f"no boundary row where {spec.field} matches {spec.value!r} in {spec.gpkg}"
            )

        matched = set(
            frame[spec.field].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        )
        missing = [
            wanted
            for wanted in wanted_values
            if wanted not in matched
            and not (wanted.isdigit() and wanted.lstrip("0") in {v.lstrip("0") for v in matched})
        ]
        if missing:
            raise ValueError(
                f"boundary rows missing for {spec.field} values {missing!r} in {spec.gpkg}"
            )
    if frame.crs is None:
        raise ValueError(f"boundary layer has no CRS: {spec.gpkg}")
    frame = frame.to_crs(WGS84)
    geometry = unary_union(frame.geometry.dropna().tolist())
    if geometry.is_empty:
        raise ValueError(f"boundary geometry is empty: {spec.gpkg}")
    return geometry


def clip_points(frame: gpd.GeoDataFrame, geometry) -> gpd.GeoDataFrame:
    if frame.empty:
        return frame.copy()
    if frame.crs is None:
        frame = frame.set_crs(WGS84)
    elif str(frame.crs) != WGS84:
        frame = frame.to_crs(WGS84)
    mask = frame.geometry.intersects(geometry)
    return frame.loc[mask].reset_index(drop=True)
