from sigma_siphon.settings import DEFAULT_OSM_OVERPASS_URL
from sigma_siphon.sources.osm import _commercial_endpoint, _query


def test_osm_has_zero_configuration_default(monkeypatch):
    monkeypatch.delenv("SIGMA_OSM_OVERPASS_URL", raising=False)
    assert _commercial_endpoint() == DEFAULT_OSM_OVERPASS_URL


def test_osm_endpoint_can_be_overridden(monkeypatch):
    monkeypatch.setenv(
        "SIGMA_OSM_OVERPASS_URL",
        "https://example.test/api/interpreter",
    )
    assert _commercial_endpoint() == "https://example.test/api/interpreter"


def test_osm_query_does_not_select_all_named_railways_or_aeroways():
    query = _query((120.0, 14.0, 121.0, 15.0))
    assert 'nwr["name"]["railway"](' not in query
    assert 'nwr["name"]["aeroway"](' not in query
    assert 'railway"~"^(station|halt|tram_stop|subway_entrance)$"' in query
    assert 'aeroway"~"^(aerodrome|terminal)$"' in query
