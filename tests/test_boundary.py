import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from sigma_siphon.areas import Area, BoundarySpec
from sigma_siphon.boundary import clip_points, load_boundary


def test_bbox_is_default_boundary():
    area = Area("x", "X", "test", (120.0, 14.0, 121.0, 15.0))
    boundary = load_boundary(area)
    frame = gpd.GeoDataFrame(
        pd.DataFrame({"name": ["in", "out"]}),
        geometry=[Point(120.5, 14.5), Point(122.0, 14.5)],
        crs="EPSG:4326",
    )
    clipped = clip_points(frame, boundary)
    assert clipped["name"].tolist() == ["in"]


def test_composite_boundary_unions_multiple_psgc_rows(tmp_path):
    gpkg = tmp_path / "areas.gpkg"
    frame = gpd.GeoDataFrame(
        {"psgc_code": ["0000000001", "0000000002"]},
        geometry=[box(120.0, 14.0, 120.5, 14.5), box(120.5, 14.0, 121.0, 14.5)],
        crs="EPSG:4326",
    )
    frame.to_file(gpkg, layer="areas", driver="GPKG")
    area = Area(
        "metro_test",
        "Metro Test",
        "composite",
        (120.0, 14.0, 121.0, 14.5),
        members=("0000000001", "0000000002"),
        boundary=BoundarySpec(
            gpkg=gpkg,
            layer="areas",
            field="psgc_code",
            value=("0000000001", "0000000002"),
        ),
    )
    geometry = load_boundary(area)
    assert geometry.bounds == (120.0, 14.0, 121.0, 14.5)
