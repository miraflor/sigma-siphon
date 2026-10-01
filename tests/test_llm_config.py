from sigma_siphon.llm import LLMClassifier
from sigma_siphon.settings import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL


def test_llm_is_not_configured_without_key(monkeypatch):
    monkeypatch.delenv("SIGMA_LLM_API_KEY", raising=False)
    assert LLMClassifier.is_configured() is False


def test_llm_is_configured_with_key(monkeypatch):
    monkeypatch.setenv("SIGMA_LLM_API_KEY", "test-key")
    assert LLMClassifier.is_configured() is True


def test_llm_uses_built_in_model_and_base_url(monkeypatch, tmp_path):
    monkeypatch.setenv("SIGMA_LLM_API_KEY", "test-key")
    monkeypatch.delenv("SIGMA_LLM_MODEL", raising=False)
    monkeypatch.delenv("SIGMA_LLM_BASE_URL", raising=False)

    classifier = LLMClassifier.from_environment(tmp_path / "llm.sqlite")
    assert classifier is not None
    try:
        assert classifier.model == DEFAULT_LLM_MODEL
        assert classifier.base_url == DEFAULT_LLM_BASE_URL
    finally:
        classifier.close()
