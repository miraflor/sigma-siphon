from sigma_siphon.sources.cache import (
    cache_matches_bbox,
    write_cache_identity,
)


def test_cache_identity_requires_matching_bbox(tmp_path):
    cache = tmp_path / "source.parquet"
    cache.touch()
    bbox = (120.0, 14.0, 121.0, 15.0)

    assert not cache_matches_bbox(cache, bbox)

    write_cache_identity(cache, bbox)
    assert cache_matches_bbox(cache, bbox)
    assert not cache_matches_bbox(cache, (120.0, 14.0, 121.1, 15.0))


def test_malformed_cache_identity_fails_closed(tmp_path):
    cache = tmp_path / "source.parquet"
    cache.touch()
    metadata = cache.with_suffix(cache.suffix + ".meta.json")
    metadata.write_text("{not-json", encoding="utf-8")

    assert not cache_matches_bbox(cache, (120.0, 14.0, 121.0, 15.0))
