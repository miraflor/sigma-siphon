from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

import sigma_siphon.pipeline as pipeline


def _source(source: str):
    frame = pd.DataFrame(
        {
            "source": [source],
            "source_id": [f"{source}/1"],
            "name": ["Sample Bank"],
            "category": ["amenity=bank"],
            "lon": [121.0],
            "lat": [14.5],
            "provenance": [source],
            "upstream_license": [
                "ODbL-1.0" if source == "osm" else "CDLA-Permissive-2.0"
            ],
            "overture_providers": [""],
        }
    )
    return gpd.GeoDataFrame(
        frame,
        geometry=[Point(121.0, 14.5)],
        crs="EPSG:4326",
    )


def test_explicit_llm_run_requires_key_before_network(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SIGMA_LLM_API_KEY", raising=False)

    def unexpected_network(*args, **kwargs):
        raise AssertionError("network acquisition should not start before LLM preflight")

    monkeypatch.setattr(pipeline, "ensure", unexpected_network)
    monkeypatch.setattr(pipeline, "load_prepared_area_osm", unexpected_network)
    monkeypatch.setattr(pipeline, "fetch_overture", unexpected_network)

    with pytest.raises(RuntimeError, match="SIGMA_LLM_API_KEY"):
        pipeline.run_pipeline("metro_manila", root=tmp_path, use_llm=True)


def test_default_run_does_not_require_llm_key(monkeypatch):
    monkeypatch.delenv("SIGMA_LLM_API_KEY", raising=False)
    assert pipeline.run_pipeline.__kwdefaults__["use_llm"] is False
