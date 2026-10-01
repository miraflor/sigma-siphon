from pathlib import Path

import pytest

import sigma_siphon.pipeline as pipeline


def test_default_run_requires_llm_key_before_network(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SIGMA_LLM_API_KEY", raising=False)

    def unexpected_network(*args, **kwargs):
        raise AssertionError("network acquisition should not start before LLM preflight")

    monkeypatch.setattr(pipeline, "fetch_osm", unexpected_network)
    monkeypatch.setattr(pipeline, "fetch_overture", unexpected_network)

    with pytest.raises(RuntimeError, match="SIGMA_LLM_API_KEY"):
        pipeline.run_pipeline("metro_manila", root=tmp_path)
