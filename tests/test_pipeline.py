from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

import sigma_siphon.pipeline as pipeline


def _source(source: str, sid: str, name: str, category: str):
    frame = pd.DataFrame(
        {
            "source": [source],
            "source_id": [sid],
            "name": [name],
            "category": [category],
            "lon": [121.0],
            "lat": [14.5],
            "provenance": [source],
            "upstream_license": ["ODbL-1.0" if source == "osm" else "CDLA-Permissive-2.0"],
            "overture_providers": ["" if source == "osm" else "meta"],
        }
    )
    return gpd.GeoDataFrame(frame, geometry=[Point(121.0, 14.5)], crs="EPSG:4326")


def test_end_to_end_without_network(monkeypatch, tmp_path: Path):
    pbf_file = tmp_path / "philippines-latest.osm.pbf"
    pbf_file.touch()
    monkeypatch.setattr(
        pipeline,
        "ensure",
        lambda *args, **kwargs: pbf_file,
    )
    monkeypatch.setattr(
        pipeline,
        "load_prepared_area_osm",
        lambda *args, **kwargs: (
            _source("osm", "node/1", "Sample Bank", "amenity=bank"),
            "test-version",
            False,
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "fetch_overture",
        lambda *args, **kwargs: _source("overture", "ov-1", "Sample Bank", "bank"),
    )
    written: dict[str, gpd.GeoDataFrame] = {}

    def fake_to_parquet(self, path, index=False):
        written["frame"] = self.copy()
        Path(path).touch()

    monkeypatch.setattr(gpd.GeoDataFrame, "to_parquet", fake_to_parquet)

    target, report = pipeline.run_pipeline(
        "metro_manila",
        root=tmp_path,
        use_llm=False,
    )
    assert target.exists()
    assert (target.parent / "run.json").exists()
    assert (target.parent / "ATTRIBUTION.txt").exists()
    assert (target.parent / "DATABASE_LICENSE.txt").exists()
    result = written["frame"]
    assert len(result) == 1
    assert result.loc[0, "io80_code"] == "66"
    assert report["counts"]["matched_two_source"] == 1
    assert "ODbL-1.0" in result.loc[0, "source_licenses"]
    assert report["classification"]["io80_code_71_allowed"] is True
    assert report["licensing"]["database_license"] == "ODbL-1.0"
    assert report["licensing"]["software"] == "Proprietary"
    assert report["boundary"]["mode"] == "gpkg"
    assert len(str(report["boundary"]["geometry_sha256"])) == 64
    assert len(str(report["boundary"]["fingerprint"])) == 64
