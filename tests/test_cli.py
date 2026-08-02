from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from tracerelay import cli
from tracerelay.config import (
    CONTROL_HOST,
    CONTROL_PROTOCOL_VERSION,
    PRODUCT_NAME,
    RuntimePaths,
)
from tracerelay.control import ControlClient
from tracerelay.service import TraceRelayService
from tracerelay.session import SessionManager
from tracerelay.verify import VALID_COMPLETE, verify_session


def test_status_cli_uses_control_service(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        cli,
        "ControlClient",
        lambda: ControlClient(CONTROL_HOST, service.control_port),
    )

    try:
        exit_code = cli.main(["status"])
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["state"] == "IDLE"


def test_verify_cli_reports_complete_session(tmp_path: Path, capsys: object) -> None:
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(9)
    manager.close(timeout=2.0)

    exit_code = cli.main(["verify", str(registration.session_path)])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "VALID_COMPLETE"


def test_verify_cli_returns_nonzero_for_invalid_directory(
    tmp_path: Path, capsys: object
) -> None:
    exit_code = cli.main(["verify", str(tmp_path / "missing")])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["status"] == "INVALID"


def test_status_cli_reports_unavailable_on_connection_failure(
    monkeypatch: object, capsys: object
) -> None:
    class UnavailableClient:
        def request(self, _request: dict[str, object]) -> dict[str, object]:
            raise ConnectionRefusedError("foreground Service is not running")

    monkeypatch.setattr(cli, "ControlClient", UnavailableClient)

    exit_code = cli.main(["status"])

    output = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert output == {
        "command": "status",
        "error": "foreground Service is not running",
        "ok": False,
        "state": "NOT_RUNNING",
    }


def test_register_and_close_cli_complete_a_waiting_session(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        cli,
        "ControlClient",
        lambda: ControlClient(CONTROL_HOST, service.control_port),
    )

    try:
        register_exit = cli.main(["register", "--upstream-port", "9"])
        registration = json.loads(capsys.readouterr().out)
        close_exit = cli.main(["close"])
        closed = json.loads(capsys.readouterr().out)
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert register_exit == 0
    assert registration["ok"] is True
    assert registration["state"] == "WAITING"
    assert close_exit == 0
    assert closed["ok"] is True
    assert closed["closed"] is True
    assert closed["state"] == "IDLE"
    assert verify_session(Path(registration["session_path"])).status == VALID_COMPLETE
    assert not thread.is_alive()


def test_start_reuses_a_valid_running_instance(
    monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    status = _managed_status(service_pid=101, supervisor_pid=202)

    class RunningClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 3.0

        def request(self, request: dict[str, object]) -> dict[str, object]:
            assert request == {"command": "status"}
            return status

    monkeypatch.setattr(cli, "ControlClient", RunningClient)
    monkeypatch.setattr(
        cli,
        "launch_detached_supervisor",
        lambda: pytest.fail("an existing instance must not launch another Supervisor"),
    )

    exit_code = cli.main(["start"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["started"] is False
    assert output["already_running"] is True
    assert output["service_pid"] == 101
    assert output["supervisor_pid"] == 202


def test_start_launches_only_after_connection_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    requests = 0
    launches = 0

    class StartingClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout in {3.0, 0.5}

        def request(self, request: dict[str, object]) -> dict[str, object]:
            nonlocal requests
            assert request == {"command": "status"}
            requests += 1
            if requests == 1:
                raise ConnectionRefusedError("not listening")
            return _managed_status(service_pid=303, supervisor_pid=404)

    def launch() -> int:
        nonlocal launches
        launches += 1
        return 999

    monkeypatch.setattr(cli, "ControlClient", StartingClient)
    monkeypatch.setattr(cli, "launch_detached_supervisor", launch)

    exit_code = cli.main(["start"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert requests == 2
    assert launches == 1
    assert output["started"] is True
    assert output["already_running"] is False
    assert output["service_pid"] == 303
    assert output["supervisor_pid"] == 404
    assert "launcher_supervisor_pid" not in output


def test_start_rejects_a_foreign_protocol_without_launching(
    monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    class ForeignClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 3.0

        def request(self, _request: dict[str, object]) -> dict[str, object]:
            return {"ok": True, "command": "status", "state": "IDLE"}

    monkeypatch.setattr(cli, "ControlClient", ForeignClient)
    monkeypatch.setattr(
        cli,
        "launch_detached_supervisor",
        lambda: pytest.fail("a foreign listener must not launch TraceRelay"),
    )

    exit_code = cli.main(["start"])

    output = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert output["ok"] is False
    assert "non-TraceRelay protocol" in output["error"]


def test_status_identity_requires_consistent_foreground_or_managed_pids() -> None:
    foreground = _managed_status(service_pid=303, supervisor_pid=404)
    foreground.update({"mode": "foreground", "supervisor_pid": None})
    assert cli._is_trace_relay_status(foreground) is True

    inconsistent_foreground = dict(foreground, supervisor_pid=404)
    inconsistent_managed = dict(foreground, mode="managed")
    assert cli._is_trace_relay_status(inconsistent_foreground) is False
    assert cli._is_trace_relay_status(inconsistent_managed) is False


def test_stop_waits_for_the_exact_response_process_ids(
    monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    class StoppingClient:
        def request(self, request: dict[str, object]) -> dict[str, object]:
            assert request == {"command": "stop"}
            return {
                "ok": True,
                "command": "stop",
                "state": "IDLE",
                "stopping": True,
                "service_pid": 505,
                "supervisor_pid": 606,
            }

    waited: list[tuple[tuple[int, ...], float]] = []
    monkeypatch.setattr(cli, "ControlClient", StoppingClient)
    monkeypatch.setattr(
        cli,
        "_wait_for_process_shutdown",
        lambda process_ids, timeout: waited.append((process_ids, timeout)) or True,
    )

    exit_code = cli.main(["stop"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["stopped"] is True
    assert waited == [((505, 606), cli.HEARTBEAT_TIMEOUT_SECONDS)]


def test_stop_rejects_malformed_process_identity(
    monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    class MalformedClient:
        def request(self, _request: dict[str, object]) -> dict[str, object]:
            return {
                "ok": True,
                "command": "stop",
                "state": "IDLE",
                "stopping": True,
                "service_pid": "505",
                "supervisor_pid": 606,
            }

    monkeypatch.setattr(cli, "ControlClient", MalformedClient)
    monkeypatch.setattr(
        cli,
        "_wait_for_process_shutdown",
        lambda *_args: pytest.fail("malformed PIDs must not be observed"),
    )

    exit_code = cli.main(["stop"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["stopped"] is False
    assert "invalid service_pid" in output["error"]


def test_process_shutdown_wait_handles_exit_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = iter([True, False, False])
    monkeypatch.setattr(cli, "_process_is_running", lambda _pid: next(checks))
    assert cli._wait_for_process_shutdown((701, 702), 1.0) is True

    monkeypatch.setattr(cli, "_process_is_running", lambda _pid: True)
    moments = iter([10.0, 11.0])
    monkeypatch.setattr(cli.time, "monotonic", lambda: next(moments))
    assert cli._wait_for_process_shutdown((701,), 1.0) is False


def test_windows_process_probe_recognizes_current_and_invalid_pid() -> None:
    assert cli._process_is_running(os.getpid()) is True
    assert cli._process_is_running(0xFFFFFFFF) is False


def _managed_status(
    *, service_pid: int, supervisor_pid: int
) -> dict[str, object]:
    return {
        "ok": True,
        "command": "status",
        "state": "IDLE",
        "mode": "managed",
        "product": PRODUCT_NAME,
        "protocol_version": CONTROL_PROTOCOL_VERSION,
        "service_pid": service_pid,
        "supervisor_pid": supervisor_pid,
    }
