from __future__ import annotations

import tomllib
from pathlib import Path

# These exact declared ranges were license-reviewed on 2026-09-30. Changing a
# package *or its accepted version range* requires an intentional re-audit.
AUDITED_BUILD = ("hatchling>=1.25,<2",)
AUDITED_RUNTIME = (
    "geopandas>=1.0,<2",
    "openai>=1.50,<4",
    "osmium>=4.3,<5",
    "overturemaps>=1.0.2,<2",
    "pandas>=2.2,<4",
    "pyarrow>=16,<27",
    "PyYAML>=6,<7",
    "rapidfuzz>=3.9,<4",
    "requests>=2.32,<3",
    "rich>=13.7,<16",
    "shapely>=2.0,<3",
    "typer>=0.12,<1",
)
AUDITED_DEV = (
    "pytest>=8.2,<10",
    "ruff>=0.6,<1",
)
AUDITED_BACKEND = "hatchling.build"
AUDITED_PROJECT_LICENSE = "LicenseRef-Proprietary"


def _tuple(values: object) -> tuple[str, ...]:
    return tuple(str(value) for value in (values or ()))


def main() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    build = data.get("build-system", {})
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {})

    actual_build = _tuple(build.get("requires"))
    actual_runtime = _tuple(project.get("dependencies"))
    actual_dev = _tuple(optional.get("dev"))
    actual_backend = str(build.get("build-backend", ""))
    actual_project_license = str(project.get("license", ""))

    failures: list[str] = []
    if actual_project_license != AUDITED_PROJECT_LICENSE:
        failures.append(
            f"project license changed: expected {AUDITED_PROJECT_LICENSE!r}, "
            f"got {actual_project_license!r}"
        )
    if actual_backend != AUDITED_BACKEND:
        failures.append(
            f"build backend changed: expected {AUDITED_BACKEND!r}, got {actual_backend!r}"
        )
    if actual_build != AUDITED_BUILD:
        failures.append(
            f"build requirements changed: expected {AUDITED_BUILD!r}, got {actual_build!r}"
        )
    if actual_runtime != AUDITED_RUNTIME:
        failures.append(
            f"runtime requirements changed: expected {AUDITED_RUNTIME!r}, got {actual_runtime!r}"
        )
    if actual_dev != AUDITED_DEV:
        failures.append(
            f"dev requirements changed: expected {AUDITED_DEV!r}, got {actual_dev!r}"
        )

    if failures:
        detail = "\n- ".join(failures)
        raise SystemExit(
            "Dependency policy changed; re-audit software licensing before release:\n- " + detail
        )

    print("dependency policy: audited build/runtime/dev specifications unchanged")


if __name__ == "__main__":
    main()
