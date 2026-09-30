from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from importlib import resources

import geopandas as gpd
import pandas as pd
import yaml

from .llm import LLMClassifier
from .text import combine, fold


@dataclass(frozen=True, slots=True)
class Industry:
    io80_code: str
    io80_label: str
    io16_code: str
    io16_label: str


@dataclass(frozen=True, slots=True)
class Rule:
    code: str
    any_terms: tuple[str, ...]
    all_terms: tuple[str, ...]
    reason: str


def load_catalog() -> dict[str, Industry]:
    text = (
        resources.files("sigma_siphon")
        .joinpath("data", "industries.csv")
        .read_text(encoding="utf-8")
    )
    out: dict[str, Industry] = {}
    for row in csv.DictReader(io.StringIO(text)):
        industry = Industry(
            io80_code=row["io80_code"],
            io80_label=row["io80_label"],
            io16_code=row["io16_code"],
            io16_label=row["io16_label"],
        )
        out[industry.io80_code] = industry
    return out


def load_rules() -> list[Rule]:
    text = resources.files("sigma_siphon").joinpath("data", "rules.yml").read_text(encoding="utf-8")
    payload = yaml.safe_load(text) or {}
    return [
        Rule(
            code=str(row["code"]).zfill(2),
            any_terms=tuple(fold(x) for x in row.get("any", []) if str(x).strip()),
            all_terms=tuple(fold(x) for x in row.get("all", []) if str(x).strip()),
            reason=str(row.get("reason") or "deterministic rule"),
        )
        for row in payload.get("rules", [])
    ]


def _rule_match(text: str, rule: Rule) -> bool:
    # fold() turns `key=value` into `key value`; substring matching remains stable.
    all_ok = all(term in text for term in rule.all_terms)
    any_ok = not rule.any_terms or any(term in text for term in rule.any_terms)
    return all_ok and any_ok


def deterministic_code(name: object, category: object, rules: list[Rule] | None = None):
    text = fold(combine(name, category))
    for rule in rules or load_rules():
        if _rule_match(text, rule):
            return rule.code, rule.reason
    return None


def _fill_industry_columns(row: dict[str, object], industry: Industry | None) -> None:
    if industry is None:
        row.update(
            io80_code="",
            io80_label="",
            io16_code="",
            io16_label="",
        )
        return
    row.update(
        io80_code=industry.io80_code,
        io80_label=industry.io80_label,
        io16_code=industry.io16_code,
        io16_label=industry.io16_label,
    )


def tag_places(
    frame: gpd.GeoDataFrame,
    *,
    llm: LLMClassifier | None = None,
) -> gpd.GeoDataFrame:
    """Tag canonical POIs. High-precision rules fire first; the LLM handles the rest."""
    if frame.empty:
        out = frame.copy()
        for column in (
            "io80_code", "io80_label", "io16_code", "io16_label", "tag_method",
            "tag_confidence", "tag_reason",
        ):
            out[column] = pd.Series(dtype="object")
        return out

    catalog = load_catalog()
    rules = load_rules()
    result = frame.copy()
    records: list[dict[str, object]] = []
    pending: list[tuple[int, str, str]] = []

    for pos, (_, source) in enumerate(result.iterrows()):
        record: dict[str, object] = {}
        decision = deterministic_code(source.get("name"), source.get("category"), rules)
        if decision:
            code, reason = decision
            industry = catalog[code]
            _fill_industry_columns(record, industry)
            record.update(tag_method="rule", tag_confidence=1.0, tag_reason=reason)
        else:
            _fill_industry_columns(record, None)
            record.update(tag_method="unresolved", tag_confidence=None, tag_reason="")
            pending.append((pos, str(source.get("name") or ""), str(source.get("category") or "")))
        records.append(record)

    if llm is not None and pending:
        decisions = llm.classify(pending, catalog)
        for pos, decision in decisions.items():
            record = records[pos]
            industry = catalog.get(decision.code)
            if industry is None:
                continue
            _fill_industry_columns(record, industry)
            record.update(
                tag_method="llm",
                tag_confidence=decision.confidence,
                tag_reason=decision.reason,
            )

    tagged = pd.DataFrame(records, index=result.index)
    for column in tagged.columns:
        result[column] = tagged[column]
    return result
