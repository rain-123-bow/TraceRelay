from __future__ import annotations

import json
import threading
from pathlib import Path

from tracerelay import cli
from tracerelay.config import CONTROL_HOST, RuntimePaths
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
        "state": "UNAVAILABLE",
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
