import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from sigma_siphon.industry import deterministic_code, load_catalog, tag_places
from sigma_siphon.llm import LLMDecision


def test_catalog_has_complete_io80_and_consistent_rollup():
    catalog = load_catalog()
    assert len(catalog) == 80
    assert catalog["01"].io16_code == "01"
    assert catalog["49"].io16_code == "04"
    assert catalog["72"].io16_code == "12"
    assert catalog["80"].io16_code == "16"
    assert catalog["71"].io16_code == "11"


def test_high_precision_rule():
    code, reason = deterministic_code("Sample Cafe", "amenity=cafe | cuisine=coffee_shop")
    assert code == "63"
    assert "food" in reason


def test_tag_places_derives_io16_from_io80():
    frame = gpd.GeoDataFrame(
        pd.DataFrame(
            {
                "poi_id": ["a"],
                "name": ["Sample Bank"],
                "category": ["amenity=bank"],
                "lon": [121.0],
                "lat": [14.5],
            }
        ),
        geometry=[Point(121.0, 14.5)],
        crs="EPSG:4326",
    )
    tagged = tag_places(frame)
    assert tagged.loc[0, "io80_code"] == "66"
    assert tagged.loc[0, "io16_code"] == "10"
    assert tagged.loc[0, "tag_method"] == "rule"


def test_llm_may_assign_io80_code_71():
    class FakeLLM:
        def classify(self, pending, catalog):
                    return {pending[0][0]: LLMDecision("71", 0.88, "dwelling ownership evidence")}

    frame = gpd.GeoDataFrame(
        pd.DataFrame(
            {
                "poi_id": ["dwelling"],
                "name": ["Sample Residential Condominium"],
                "category": ["residential condominium"],
                "lon": [121.0],
                "lat": [14.5],
            }
        ),
        geometry=[Point(121.0, 14.5)],
        crs="EPSG:4326",
    )
    tagged = tag_places(frame, llm=FakeLLM())
    assert tagged.loc[0, "io80_code"] == "71"
    assert tagged.loc[0, "io16_code"] == "11"
    assert tagged.loc[0, "tag_method"] == "llm"
