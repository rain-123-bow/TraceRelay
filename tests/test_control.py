from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from tracerelay.config import CONTROL_HOST, CONTROL_MESSAGE_LIMIT, RuntimePaths
from tracerelay.control import ControlClient
from tracerelay.service import TraceRelayService
from tracerelay.verify import VALID_COMPLETE, verify_session


def test_control_status_register_reject_second_and_close(tmp_path: Path) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    client = ControlClient(CONTROL_HOST, service.control_port)

    try:
        status = client.request({"command": "status"})
        assert status["ok"] is True
        assert status["state"] == "IDLE"

        registration = client.request({"command": "register", "upstream_port": 9})
        assert registration["ok"] is True
        assert registration["state"] == "WAITING"

        rejected = client.request({"command": "register", "upstream_port": 10})
        assert rejected["ok"] is False
        assert rejected["state"] == "WAITING"

        invalid = client.request(
            {"command": "status", "unexpected": "not accepted"}
        )
        assert invalid["ok"] is False

        closed = client.request({"command": "close"})
        assert closed["ok"] is True
        assert closed["closed"] is True
        assert closed["state"] == "IDLE"
        assert verify_session(Path(registration["session_path"])).status == VALID_COMPLETE
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert not thread.is_alive()


def test_control_rejects_invalid_upstream_port_type(tmp_path: Path) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )

    try:
        response = service.handle_request(
            {"command": "register", "upstream_port": "43123"}
        )
    finally:
        service.shutdown()

    assert response["ok"] is False
    assert response["state"] == "IDLE"


def test_control_rejects_message_over_64_kib(tmp_path: Path) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()

    try:
        with socket.create_connection(
            (CONTROL_HOST, service.control_port), timeout=2.0
        ) as connection:
            connection.sendall(b" " * CONTROL_MESSAGE_LIMIT + b"\n")
            response = json.loads(connection.makefile("r", encoding="utf-8").readline())
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert response["ok"] is False
    assert "exceeds 64 KiB" in response["error"]


def test_control_rejects_nonstandard_json_without_stopping_service(
    tmp_path: Path,
) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    client = ControlClient(CONTROL_HOST, service.control_port)

    try:
        with socket.create_connection(
            (CONTROL_HOST, service.control_port), timeout=2.0
        ) as connection:
            connection.sendall(b'{"command":NaN}\n')
            response = json.loads(connection.makefile("r", encoding="utf-8").readline())

        status = client.request({"command": "status"})
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert response["ok"] is False
    assert "non-standard JSON constant" in response["error"]
    assert status["ok"] is True
    assert status["state"] == "IDLE"
    assert not thread.is_alive()


def test_control_accepts_a_json_message_at_the_exact_size_limit(
    tmp_path: Path,
) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    client = ControlClient(CONTROL_HOST, service.control_port)
    prefix = b'{"command":"status","padding":"'
    suffix = b'"}\n'
    payload = prefix + b"x" * (CONTROL_MESSAGE_LIMIT - len(prefix) - len(suffix)) + suffix
    assert len(payload) == CONTROL_MESSAGE_LIMIT

    try:
        with socket.create_connection(
            (CONTROL_HOST, service.control_port), timeout=2.0
        ) as connection:
            connection.sendall(payload)
            response = json.loads(connection.makefile("r", encoding="utf-8").readline())
        status = client.request({"command": "status"})
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert response["ok"] is False
    assert "unexpected request field" in response["error"]
    assert "exceeds 64 KiB" not in response["error"]
    assert status["ok"] is True
    assert not thread.is_alive()


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        (b"\xff\n", "invalid UTF-8 JSON"),
        (b"[]\n", "must be a JSON object"),
        (b"\n", "control message is empty"),
        (b'{"command":"status"}\n{}\n', "only one control request"),
    ],
)
def test_malformed_control_input_does_not_stop_service(
    tmp_path: Path, payload: bytes, expected_error: str
) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    client = ControlClient(CONTROL_HOST, service.control_port)

    try:
        with socket.create_connection(
            (CONTROL_HOST, service.control_port), timeout=2.0
        ) as connection:
            connection.sendall(payload)
            response = json.loads(connection.makefile("r", encoding="utf-8").readline())
        status = client.request({"command": "status"})
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert response["ok"] is False
    assert expected_error in response["error"]
    assert status["ok"] is True
    assert status["state"] == "IDLE"
    assert not thread.is_alive()


def test_control_port_is_an_exclusive_single_instance_lock(tmp_path: Path) -> None:
    first = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "first"),
        control_port=0,
    )

    try:
        with pytest.raises(OSError):
            TraceRelayService(
                paths=RuntimePaths.from_root(tmp_path / "second"),
                control_port=first.control_port,
            )
    finally:
        first.shutdown()


def test_only_a_valid_stop_response_triggers_runtime_shutdown(
    tmp_path: Path,
) -> None:
    service = TraceRelayService(
        paths=RuntimePaths.from_root(tmp_path / "runtime"),
        control_port=0,
    )
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    client = ControlClient(CONTROL_HOST, service.control_port)

    try:
        rejected = client.request({"command": "stop", "unexpected": True})
        status = client.request({"command": "status"})
        assert rejected["ok"] is False
        assert rejected.get("stopping") is None
        assert service.stop_requested.is_set() is False
        assert status["ok"] is True

        accepted = client.request({"command": "stop"})
        deadline = time.monotonic() + 2.0
        while not service.stop_requested.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert accepted["ok"] is True
    assert accepted["stopping"] is True
    assert service.stop_requested.is_set() is True
    assert not thread.is_alive()
