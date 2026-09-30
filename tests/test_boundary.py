import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from sigma_siphon.areas import Area
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
