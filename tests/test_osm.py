import pytest

from sigma_siphon.sources.osm import _commercial_endpoint, _query


def test_osm_requires_explicit_commercial_endpoint(monkeypatch):
    monkeypatch.delenv("SIGMA_OSM_OVERPASS_URL", raising=False)
    with pytest.raises(RuntimeError, match="SIGMA_OSM_OVERPASS_URL"):
        _commercial_endpoint()


def test_osm_query_does_not_select_all_named_railways_or_aeroways():
    query = _query((120.0, 14.0, 121.0, 15.0))
    assert 'nwr["name"]["railway"](' not in query
    assert 'nwr["name"]["aeroway"](' not in query
    assert 'railway"~"^(station|halt|tram_stop|subway_entrance)$"' in query
    assert 'aeroway"~"^(aerodrome|terminal)$"' in query
