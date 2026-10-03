from sigma_siphon.industry import deterministic_code, load_catalog


def test_catalog_has_complete_io80_and_consistent_rollup():
    catalog = load_catalog()
    assert len(catalog) == 80
    assert catalog["01"].io16_code == "01"
    assert catalog["49"].io16_code == "04"
    assert catalog["72"].io16_code == "12"
    assert catalog["80"].io16_code == "16"
    assert catalog["71"].io16_code == "11"


def test_high_precision_rule():
    code, reason = deterministic_code(
        "Sample Cafe",
        "amenity=cafe | cuisine=coffee_shop",
    )
    assert code == "63"
    assert "food" in reason
