from sigma_siphon.sources.osm import _category, _has_poi


def test_named_shop_is_a_poi():
    assert _has_poi({"name": "Sample Shop", "shop": "convenience"})


def test_unnamed_shop_is_not_a_poi():
    assert not _has_poi({"shop": "convenience"})


def test_selected_railway_value_is_a_poi():
    assert _has_poi({"name": "Sample Station", "railway": "station"})


def test_unselected_railway_value_is_not_a_poi():
    assert not _has_poi({"name": "Sample Track", "railway": "rail"})


def test_category_preserves_classification_evidence():
    category = _category(
        {
            "amenity": "cafe",
            "cuisine": "coffee_shop",
            "brand": "Example Coffee",
        }
    )
    assert "amenity=cafe" in category
    assert "cuisine=coffee_shop" in category
    assert "brand=Example Coffee" in category
