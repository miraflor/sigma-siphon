import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from sigma_siphon.reconcile import reconcile


def layer(source, rows):
    frame = pd.DataFrame(rows)
    frame["source"] = source
    frame["upstream_license"] = "ODbL-1.0" if source == "osm" else "CDLA-Permissive-2.0"
    frame["overture_providers"] = "" if source == "osm" else "meta"
    return gpd.GeoDataFrame(
        frame,
        geometry=[Point(xy) for xy in zip(frame.lon, frame.lat, strict=True)],
        crs="EPSG:4326",
    )


def test_near_same_name_is_reconciled():
    a = layer(
        "osm",
        [{"source_id": "node/1", "name": "Alpha Coffee", "category": "amenity=cafe", "lon": 121.0, "lat": 14.5}],
    )
    b = layer(
        "overture",
        [{"source_id": "ov-1", "name": "Alpha Coffee", "category": "coffee shop", "lon": 121.00005, "lat": 14.5}],
    )
    out = reconcile(a, b)
    assert len(out) == 1
    assert out.loc[0, "source_count"] == 2
    assert out.loc[0, "osm_id"] == "node/1"
    assert out.loc[0, "overture_id"] == "ov-1"
    assert out.loc[0, "source_licenses"] == "CDLA-Permissive-2.0|ODbL-1.0"
    assert out.loc[0, "overture_providers"] == "meta"


def test_distant_observations_stay_separate():
    a = layer(
        "osm",
        [{"source_id": "node/1", "name": "Alpha Coffee", "category": "amenity=cafe", "lon": 121.0, "lat": 14.5}],
    )
    b = layer(
        "overture",
        [{"source_id": "ov-1", "name": "Alpha Coffee", "category": "coffee shop", "lon": 121.01, "lat": 14.5}],
    )
    out = reconcile(a, b)
    assert len(out) == 2
    assert set(out["source_count"]) == {1}
