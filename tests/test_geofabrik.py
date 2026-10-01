from sigma_siphon.sources.geofabrik import _latest_from_philippines_page


def test_latest_dated_philippines_pbf_is_selected():
    html = """
    <a href="philippines-260928.osm.pbf">philippines-260928.osm.pbf</a>
    <a href="philippines-260929.osm.pbf">philippines-260929.osm.pbf</a>
    <a href="philippines-260929.osm.pbf.md5">checksum</a>
    """
    assert _latest_from_philippines_page(html) == "260929"
