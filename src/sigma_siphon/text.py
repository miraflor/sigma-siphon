from __future__ import annotations

import re
import unicodedata


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if text.casefold() in {"", "none", "null", "nan", "n/a", "na", "unknown"}:
        return ""
    return text


def fold(value: object) -> str:
    text = clean_text(value).casefold().replace("&", " and ")
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def combine(*values: object) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = clean_text(value)
        key = fold(text)
        if text and key and key not in seen:
            seen.add(key)
            out.append(text)
    return " | ".join(out)
