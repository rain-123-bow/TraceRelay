from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="TraceRelay v1 only supports Windows")
def test_wheel_installs_offline_and_all_cli_commands_smoke(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment.pop("PYTHONPATH", None)
    source_tree = tmp_path / "source"
    shutil.copytree(
        REPOSITORY_ROOT,
        source_tree,
        ignore=shutil.ignore_patterns(
            ".git",
            ".pytest_cache",
            ".venv",
            "*.egg-info",
            "__pycache__",
            "build",
            "dist",
        ),
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    build = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheelhouse),
            str(source_tree),
        ],
        cwd=tmp_path,
        environment=environment,
    )
    _require_exit(build, 0)
    wheels = list(wheelhouse.glob("tracerelay-1.0.0.dev0-*.whl"))
    assert len(wheels) == 1

    virtual_environment = tmp_path / "installed"
    create_environment = _run(
        [sys.executable, "-m", "venv", str(virtual_environment)],
        cwd=tmp_path,
        environment=environment,
    )
    _require_exit(create_environment, 0)
    installed_python = virtual_environment / "Scripts" / "python.exe"
    install = _run(
        [
            str(installed_python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            str(wheels[0]),
        ],
        cwd=tmp_path,
        environment=environment,
    )
    _require_exit(install, 0)

    outside_source = tmp_path / "outside-source"
    outside_source.mkdir()
    environment["LOCALAPPDATA"] = str(tmp_path / "local-app-data")
    executable = virtual_environment / "Scripts" / "tracerelay.exe"
    started = False
    stopped = False
    try:
        _start_result, start = _cli(
            executable, "start", cwd=outside_source, environment=environment
        )
        started = True
        assert start["started"] is True
        assert start["already_running"] is False
        assert start["state"] == "IDLE"

        _status_result, status = _cli(
            executable, "status", cwd=outside_source, environment=environment
        )
        assert status["state"] == "IDLE"
        assert status["mode"] == "managed"

        _register_result, registration = _cli(
            executable,
            "register",
            "--upstream-port",
            "9",
            cwd=outside_source,
            environment=environment,
        )
        assert registration["state"] == "WAITING"
        session_path = Path(registration["session_path"])

        _close_result, close = _cli(
            executable, "close", cwd=outside_source, environment=environment
        )
        assert close["closed"] is True
        assert close["state"] == "IDLE"

        _verify_result, verification = _cli(
            executable,
            "verify",
            str(session_path),
            cwd=outside_source,
            environment=environment,
        )
        assert verification["status"] == "VALID_COMPLETE"
        assert verification["record_count"] == 0

        _stop_result, stop = _cli(
            executable, "stop", cwd=outside_source, environment=environment
        )
        stopped = True
        assert stop["stopped"] is True
        assert stop["state"] == "IDLE"

        unavailable_result, unavailable = _cli(
            executable,
            "status",
            cwd=outside_source,
            environment=environment,
            expected_exit=1,
        )
        assert unavailable_result.stdout == ""
        assert unavailable["state"] == "NOT_RUNNING"
    finally:
        if started and not stopped and executable.exists():
            _run(
                [str(executable), "stop"],
                cwd=outside_source,
                environment=environment,
                timeout=15.0,
            )


def _cli(
    executable: Path,
    *arguments: str,
    cwd: Path,
    environment: dict[str, str],
    expected_exit: int = 0,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = _run(
        [str(executable), *arguments],
        cwd=cwd,
        environment=environment,
        timeout=30.0,
    )
    _require_exit(result, expected_exit)
    output = result.stdout.strip() or result.stderr.strip()
    value = json.loads(output)
    assert isinstance(value, dict)
    if "ok" in value:
        assert value["ok"] is (expected_exit == 0)
    return result, value


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: float = 60.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=timeout,
        check=False,
    )


def _require_exit(result: subprocess.CompletedProcess[str], expected: int) -> None:
    assert result.returncode == expected, (
        f"command returned {result.returncode}, expected {expected}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
