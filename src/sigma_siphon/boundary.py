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
        wanted = str(spec.value).strip()
        values = frame[spec.field].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        exact = values == wanted
        if wanted.isdigit():
            exact |= values.str.replace(r"^0+", "", regex=True) == wanted.lstrip("0")
        frame = frame.loc[exact]
        if frame.empty:
            raise ValueError(
                f"no boundary row where {spec.field}={spec.value!r} in {spec.gpkg}"
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
