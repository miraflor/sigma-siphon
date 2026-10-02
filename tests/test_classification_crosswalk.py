from __future__ import annotations

from sigma_siphon.classification.crosswalk import CrosswalkIndex
from sigma_siphon.classification.engine import PsicClassifier
from sigma_siphon.classification.reference import PsicNode, PsicTaxonomy
from sigma_siphon.classification.types import MappingKind, MappingRule, SourceField


def _taxonomy() -> PsicTaxonomy:
    return PsicTaxonomy(
        [
            PsicNode("Q", "section", "Human Health Activities"),
            PsicNode("86", "division", "Human Health Activities", "Q"),
            PsicNode("862", "group", "Medical and dental practice activities", "86"),
            PsicNode("I", "section", "Accommodation and Food Service"),
            PsicNode("56", "division", "Food and beverage service activities", "I"),
            PsicNode("561", "group", "Restaurants and mobile food service activities", "56"),
        ]
    )


def test_compatible_name_rule_refines_category_rule():
    crosswalk = CrosswalkIndex(
        [
            MappingRule("overture", "health_care", MappingKind.SUBTREE, ("86",)),
            MappingRule(
                "overture",
                "Smile Dental",
                MappingKind.SUBTREE,
                ("862",),
                source_field=SourceField.NAME,
            ),
        ]
    )
    classifier = PsicClassifier(_taxonomy(), crosswalk)
    decision = classifier.classify_row(
        {
            "sources": "overture",
            "overture_name": "Smile Dental",
            "overture_category": "health_care",
        }
    )
    assert decision.code == "862"
    assert "CROSSWALK_NAME_RULE_OVERRODE_CATEGORY" not in decision.flags


def test_conflicting_specific_name_rule_overrides_broad_category_rule():
    crosswalk = CrosswalkIndex(
        [
            MappingRule("overture", "restaurant", MappingKind.SUBTREE, ("561",)),
            MappingRule(
                "overture",
                "Smile Dental",
                MappingKind.SUBTREE,
                ("862",),
                source_field=SourceField.NAME,
            ),
        ]
    )
    classifier = PsicClassifier(_taxonomy(), crosswalk)
    decision = classifier.classify_row(
        {
            "sources": "overture",
            "overture_name": "Smile Dental",
            "overture_category": "restaurant",
        }
    )
    assert decision.code == "862"
    assert "CROSSWALK_NAME_RULE_OVERRODE_CATEGORY" in decision.flags
