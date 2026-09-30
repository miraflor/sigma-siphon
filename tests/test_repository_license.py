from pathlib import Path
import tomllib


def test_repository_is_proprietary():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == "LicenseRef-Proprietary"

    notice = (root / "LICENSE").read_text(encoding="utf-8")
    assert "PROPRIETARY SOFTWARE LICENSE NOTICE" in notice
    assert "All rights reserved" in notice
    assert "No license or other right" in notice
