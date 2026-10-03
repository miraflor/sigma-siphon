from __future__ import annotations

import subprocess

CANONICAL_REQUIRED = {
    "src/sigma_siphon/data/areas.yml",
    "src/sigma_siphon/data/boundaries/areas.gpkg",
}

FORBIDDEN_TRACKED = {
    "config/areas.yml",
    "data/boundaries/areas.gpkg",
    "src/sigma_siphon/llm.py",
    "tests/test_llm_config.py",
    "CLASSIFICATION_REFERENCE.md",
    "GEOFABRIK_DISCOVERY_FIX.md",
    "GEOFABRIK_PATCH.md",
    "GEOFABRIK_REDIRECT_FIX.md",
    "KEY_CLEANUP.md",
    "OVERLAY_MANIFEST.md",
    "OVERTURE_SCHEMA_FIX.md",
    "PROGRESS_PATCH.md",
}


def main() -> None:
    proc = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True)
    tracked = {
        line.strip().replace("\\", "/")
        for line in proc.stdout.splitlines()
        if line.strip()
    }

    failures = []

    missing = sorted(CANONICAL_REQUIRED - tracked)
    if missing:
        failures.append("missing canonical packaged data: " + ", ".join(missing))

    forbidden = sorted(FORBIDDEN_TRACKED & tracked)
    if forbidden:
        failures.append("obsolete/redundant tracked files: " + ", ".join(forbidden))

    generated = sorted(
        path for path in tracked
        if path.split("/", 1)[0].startswith("output")
    )
    if generated:
        failures.append("generated output is tracked: " + ", ".join(generated))

    if failures:
        raise SystemExit("Repository hygiene check failed:\n- " + "\n- ".join(failures))

    print("repository hygiene: tracked tree is clean and canonical")


if __name__ == "__main__":
    main()
