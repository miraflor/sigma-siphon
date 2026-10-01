from __future__ import annotations

import pandas as pd

from sigma_siphon.sources.osm_prepare import (
    _atomic_parquet,
    _load_state,
    _parquet_rows,
    _save_state,
    _stage,
)


def test_atomic_parquet_checkpoint(tmp_path):
    target = tmp_path / "checkpoint.parquet"
    _atomic_parquet(pd.DataFrame({"x": [1, 2, 3]}), target)
    assert _parquet_rows(target) == 3
    assert not target.with_suffix(target.suffix + ".tmp").exists()


def test_state_survives_restart(tmp_path):
    state = _load_state(tmp_path, "261001")
    _stage(state, "national_extraction")["status"] = "complete"
    _save_state(tmp_path, state)

    restored = _load_state(tmp_path, "261001")
    assert _stage(restored, "national_extraction")["status"] == "complete"
