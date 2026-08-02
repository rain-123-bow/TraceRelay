from __future__ import annotations

import json
from pathlib import Path

import pytest

from tracerelay.config import (
    JOURNAL_LIMIT_BYTES,
    SESSION_ADMISSION_RESERVE_BYTES,
    RuntimePaths,
    atomic_write_json,
    new_session_id,
)


def test_runtime_paths_and_atomic_json(tmp_path: Path) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    paths.ensure()

    assert paths.sessions.is_dir()
    assert paths.alarms.is_dir()

    target = paths.root / "state.json"
    atomic_write_json(target, {"state": "IDLE", "number": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "number": 1,
        "state": "IDLE",
    }
    assert list(paths.root.glob(".state.json.*.tmp")) == []


def test_session_ids_include_utc_and_random_components() -> None:
    first = new_session_id()
    second = new_session_id()

    assert first != second
    timestamp, random_part = first.split("_", maxsplit=1)
    assert timestamp.endswith("Z")
    assert len(random_part) == 32
    int(random_part, 16)


def test_v1_storage_limits_match_the_frozen_requirements() -> None:
    assert JOURNAL_LIMIT_BYTES == 2 * 1024 * 1024 * 1024
    assert SESSION_ADMISSION_RESERVE_BYTES == 16 * 1024 * 1024


def test_atomic_json_rejects_nonstandard_numbers_without_publishing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "metadata.json"

    with pytest.raises(ValueError, match="Out of range float values"):
        atomic_write_json(target, {"invalid": float("nan")})

    assert not target.exists()
    assert list(tmp_path.glob(".metadata.json.*.tmp")) == []
