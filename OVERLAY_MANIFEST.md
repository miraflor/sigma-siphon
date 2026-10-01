# Sigma Siphon 0.1.4 overlay

Copy the contents of this overlay directly over the root of an untouched
`sigma-siphon` 0.1.3 checkout.

Files replaced:

- `DATA_SOURCES.md`
- `README.md`
- `.env.example`
- `pyproject.toml`
- `src/sigma_siphon/__init__.py`
- `src/sigma_siphon/cli.py`
- `src/sigma_siphon/llm.py`
- `src/sigma_siphon/pipeline.py`
- `src/sigma_siphon/sources/osm.py`
- `tests/test_osm.py`

Files added:

- `setup.ps1`
- `src/sigma_siphon/settings.py`
- `tests/test_llm_config.py`
- `tests/test_llm_required.py`

Main behavior changes:

- zero-config built-in Overpass endpoint for ordinary use;
- built-in OpenAI model and base URL;
- only the API key remains a secret;
- one-time beginner-friendly Windows setup script;
- setup creates a permanent `sigma-siphon` command, so Conda activation is not
  required during ordinary use;
- default runs are rules-only and require no API key;
- `--llm` explicitly enables the OpenAI fallback;
- explicit LLM runs fail early if the key is missing;
- `run.json` reports rule-vs-LLM classification counts;
- version bumped from 0.1.3 to 0.1.4.
