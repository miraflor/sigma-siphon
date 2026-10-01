import json

from sigma_siphon.sources.overture import (
    OVERTURE_NORMALIZATION_VERSION,
    _policy_cache_matches,
)


def test_old_cache_without_policy_marker_is_invalid(tmp_path, monkeypatch):
    cache = tmp_path / "overture.parquet"
    cache.touch()

    # The separate Overture policy marker is mandatory even if the generic
    # bbox marker says the cache is otherwise current.
    monkeypatch.setattr(
        "sigma_siphon.sources.overture.cache_matches_bbox",
        lambda path, bbox: True,
    )
    assert not _policy_cache_matches(cache, (120.0, 14.0, 121.0, 15.0))


def test_current_policy_marker_is_accepted(tmp_path, monkeypatch):
    cache = tmp_path / "overture.parquet"
    cache.touch()
    bbox = (120.0, 14.0, 121.0, 15.0)

    monkeypatch.setattr(
        "sigma_siphon.sources.overture.cache_matches_bbox",
        lambda path, value: True,
    )

    marker = cache.with_suffix(cache.suffix + ".overture.json")
    marker.write_text(
        json.dumps(
            {
                "normalization_version": OVERTURE_NORMALIZATION_VERSION,
                "bbox": list(bbox),
                "raw_rows": 10,
                "accepted_rows": 8,
            }
        ),
        encoding="utf-8",
    )
    assert _policy_cache_matches(cache, bbox)
