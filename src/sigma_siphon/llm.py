from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .industry import Industry


@dataclass(frozen=True, slots=True)
class LLMDecision:
    code: str
    confidence: float
    reason: str


def _signature(name: str, category: str) -> str:
    return hashlib.sha256(f"{name}\n{category}".encode("utf-8")).hexdigest()


class DecisionCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                signature TEXT NOT NULL,
                model_identity TEXT NOT NULL,
                code TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY(signature, model_identity)
            )
            """
        )
        self.connection.commit()

    def get(self, signature: str, model_identity: str) -> LLMDecision | None:
        row = self.connection.execute(
            "SELECT code, confidence, reason FROM decisions WHERE signature=? AND model_identity=?",
            (signature, model_identity),
        ).fetchone()
        return LLMDecision(str(row[0]), float(row[1]), str(row[2])) if row else None

    def put(self, signature: str, model_identity: str, decision: LLMDecision) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?)",
            (signature, model_identity, decision.code, decision.confidence, decision.reason),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


class LLMClassifier:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        cache_path: Path = Path(".sigma-cache/llm.sqlite"),
        batch_size: int = 25,
    ):
        kwargs: dict[str, object] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/")
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError("LLM support requires the openai package") from exc
        self.client = OpenAI(**kwargs)
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.cache = DecisionCache(cache_path)
        self.batch_size = max(1, batch_size)

    @classmethod
    def from_environment(cls, cache_path: Path) -> LLMClassifier | None:
        model = os.getenv("SIGMA_LLM_MODEL", "").strip()
        api_key = os.getenv("SIGMA_LLM_API_KEY", "").strip()
        if not model or not api_key:
            return None
        return cls(
            model=model,
            api_key=api_key,
            base_url=os.getenv("SIGMA_LLM_BASE_URL", "").strip() or None,
            cache_path=cache_path,
        )

    def close(self) -> None:
        self.cache.close()

    def _prompt(self, batch, catalog: dict[str, "Industry"]):
        industries = "\n".join(
            f"{x.io80_code}: {x.io80_label}" for x in catalog.values()
        )
        items = [
            {"key": str(pos), "name": name, "category": category}
            for pos, name, category in batch
        ]
        system = (
            "Classify Philippine points of interest by the establishment's primary economic "
            "activity into exactly one supplied 2018 input-output industry. Use the POI name "
            "and source category as evidence. Do not infer manufacturing merely because a "
            "retail establishment sells a manufactured product. Public/private distinctions "
            "for education and health should be made only when the evidence supports them. "
            "If evidence is weak, still select the most plausible available industry but lower "
            "confidence. Code 71 is valid when the evidence is genuinely about dwelling-ownership "
            "services; use code 70 for other real-estate services. Return JSON only."
        )
        user = (
            "Industries:\n" + industries + "\n\n"
            "Items:\n" + json.dumps(items, ensure_ascii=False) + "\n\n"
            "Return an object with key 'items'. Each item must contain: key, code, confidence "
            "(0 to 1), and a short evidence-based reason. Do not return any code outside the list."
        )
        return system, user

    @staticmethod
    def _json(text: str) -> dict:
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:].lstrip()
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("LLM did not return a JSON object")
        return json.loads(raw[start : end + 1])

    def _call(self, batch, catalog: dict[str, "Industry"]) -> dict[int, LLMDecision]:
        system, user = self._prompt(batch, catalog)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        payload = self._json(content)
        expected = {str(pos) for pos, _, _ in batch}
        decisions: dict[int, LLMDecision] = {}
        for item in payload.get("items", []):
            key = str(item.get("key", ""))
            code = str(item.get("code", "")).zfill(2)
            if key not in expected or code not in catalog:
                continue
            try:
                confidence = min(1.0, max(0.0, float(item.get("confidence", 0.0))))
            except (TypeError, ValueError):
                confidence = 0.0
            decisions[int(key)] = LLMDecision(
                code=code,
                confidence=confidence,
                reason=str(item.get("reason") or "LLM classification").strip()[:500],
            )
        return decisions

    @staticmethod
    def _policy_identity(catalog: dict[str, "Industry"]) -> str:
        payload = "\n".join(
            f"{x.io80_code}|{x.io80_label}|{x.io16_code}|{x.io16_label}"
            for x in catalog.values()
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"io80-direct-v2|catalog={digest}"

    def classify(self, pending, catalog: dict[str, "Industry"]) -> dict[int, LLMDecision]:
        decisions: dict[int, LLMDecision] = {}
        identity = f"{self.base_url}|{self.model}|{self._policy_identity(catalog)}"
        todo = []
        for pos, name, category in pending:
            sig = _signature(name, category)
            cached = self.cache.get(sig, identity)
            if cached is not None and cached.code in catalog:
                decisions[pos] = cached
            else:
                todo.append((pos, name, category, sig))

        for start in range(0, len(todo), self.batch_size):
            part = todo[start : start + self.batch_size]
            batch = [(pos, name, category) for pos, name, category, _ in part]
            fresh = self._call(batch, catalog)
            for pos, _, _, sig in part:
                decision = fresh.get(pos)
                if decision is None:
                    continue
                decisions[pos] = decision
                self.cache.put(sig, identity, decision)
        return decisions
