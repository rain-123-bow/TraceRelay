"""Runtime constants, paths, and durable JSON helpers for TraceRelay v1."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


FORMAT_VERSION = 1
CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 43_190
CONTROL_MESSAGE_LIMIT = 64 * 1024
READ_CHUNK_SIZE = 64 * 1024
UPSTREAM_CONNECT_TIMEOUT_SECONDS = 10.0
CLOSE_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    """Filesystem locations used by one TraceRelay installation."""

    root: Path
    sessions: Path
    alarms: Path

    @classmethod
    def from_root(cls, root: Path) -> RuntimePaths:
        resolved_root = Path(root).expanduser().resolve()
        return cls(
            root=resolved_root,
            sessions=resolved_root / "sessions",
            alarms=resolved_root / "alarms",
        )

    @classmethod
    def default(cls) -> RuntimePaths:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            root = Path(local_app_data) / "TraceRelay"
        else:
            root = Path.home() / "AppData" / "Local" / "TraceRelay"
        return cls.from_root(root)

    def ensure(self) -> None:
        self.sessions.mkdir(parents=True, exist_ok=True)
        self.alarms.mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    """Return a stable UTC timestamp suitable for JSON metadata."""

    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_session_id() -> str:
    """Create the required UTC-and-random session identifier."""

    created = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{created}_{uuid4().hex}"


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Durably write a small UTF-8 JSON object and atomically publish it."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
