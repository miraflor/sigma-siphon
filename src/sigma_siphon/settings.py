"""Application defaults for ordinary Sigma Siphon deployments.

Normal users should not need to know provider endpoints or model names.
Environment variables remain available as deployment-time overrides.

Secrets are intentionally not stored here.
"""

DEFAULT_OSM_OVERPASS_URL = "https://overpass.private.coffee/api/interpreter"
DEFAULT_OSM_USER_AGENT = "SigmaSiphon/0.1.5"

DEFAULT_LLM_MODEL = "gpt-5.6-luna"
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
