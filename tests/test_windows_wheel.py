from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
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
    upstream: _TwoConnectionEcho | None = None
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

        upstream = _TwoConnectionEcho()
        _register_result, registration = _cli(
            executable,
            "register",
            "--upstream-port",
            str(upstream.port),
            cwd=outside_source,
            environment=environment,
        )
        assert registration["state"] == "WAITING"
        session_path = Path(registration["session_path"])
        endpoint = (registration["proxy_host"], registration["proxy_port"])
        assert _round_trip(endpoint, b"installed-first") == b"echo:installed-first"
        assert _round_trip(endpoint, b"installed-second") == b"echo:installed-second"
        upstream.finish()

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
        assert verification["record_count"] >= 8
        assert verification["observed_connection_count"] == 2

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
        if upstream is not None:
            upstream.close()
        if started and not stopped and executable.exists():
            _run(
                [str(executable), "stop"],
                cwd=outside_source,
                environment=environment,
                timeout=15.0,
            )


class _TwoConnectionEcho:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []
        self.received: list[bytes] = []
        self._stop = threading.Event()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(2)
        self._listener.settimeout(0.2)
        self.port = int(self._listener.getsockname()[1])
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            with self._listener:
                while len(self.received) < 2 and not self._stop.is_set():
                    try:
                        connection, _address = self._listener.accept()
                    except TimeoutError:
                        continue
                    with connection:
                        connection.settimeout(5.0)
                        payload = _receive_all(connection)
                        self.received.append(payload)
                        connection.sendall(b"echo:" + payload)
                        connection.shutdown(socket.SHUT_WR)
        except OSError as error:
            if not self._stop.is_set():
                self.errors.append(error)
        except BaseException as error:
            self.errors.append(error)

    def finish(self) -> None:
        self._thread.join(timeout=6.0)
        assert not self._thread.is_alive()
        assert self.errors == []
        assert self.received == [b"installed-first", b"installed-second"]

    def close(self) -> None:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass
        self._thread.join(timeout=2.0)


def _round_trip(endpoint: tuple[str, int], payload: bytes) -> bytes:
    with socket.create_connection(endpoint, timeout=3.0) as connection:
        connection.settimeout(5.0)
        connection.sendall(payload)
        connection.shutdown(socket.SHUT_WR)
        return _receive_all(connection)


def _receive_all(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = connection.recv(32 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


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
