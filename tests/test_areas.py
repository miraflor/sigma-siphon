from sigma_siphon.areas import load_areas


def test_packaged_area_scope_is_intentionally_small():
    areas = load_areas()
    assert len(areas) == 36
    assert sum(area.kind == "huc" for area in areas.values()) == 33
    assert sum(area.kind == "metro" for area in areas.values()) == 3
    assert {area.slug for area in areas.values() if area.kind == "metro"} == {
        "metro_manila",
        "metro_cebu",
        "metro_davao",
    }
