# Sigma Siphon 0.1.5 current-environment overlay

This overlay is designed for the current 0.1.4 `main` state.

Copy the contents directly over the repository root.

## Replaced

- `README.md`
- `setup.ps1`
- `.env.example`
- `pyproject.toml`
- `src/sigma_siphon/__init__.py`
- `src/sigma_siphon/settings.py`
- `src/sigma_siphon/pipeline.py`

## Added

- `setup-llm.ps1`

## Main changes

- Sigma Siphon installs into the Python environment that is already active.
- No dedicated Conda environment is created.
- Conda/Miniforge is never installed, reinstalled, updated, activated, or removed.
- No custom permanent launcher is created.
- The old Sigma Siphon launcher is removed by `setup.ps1` if it exists, so it
  cannot shadow the command installed in the active environment.
- The shortest install is `python -m pip install -e .`.
- Default runtime remains rules-only: `sigma-siphon run pasig`.
- OpenAI remains opt-in: `sigma-siphon run pasig --llm`.
- OpenAI credential setup is moved to a separate optional `setup-llm.ps1`.
- Version is bumped to 0.1.5.
