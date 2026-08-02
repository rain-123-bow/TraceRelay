from __future__ import annotations

import json
import multiprocessing
import os
import socket
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

import pytest

from tracerelay import service as service_module
from tracerelay import session as session_module
from tracerelay import supervisor as supervisor_module
from tracerelay.config import (
    CONTROL_HOST,
    HEARTBEAT_TIMEOUT_SECONDS,
    RuntimePaths,
    latest_alarm_summary,
    write_alarm,
)
from tracerelay.control import ControlClient
from tracerelay.journal import Direction, JournalWriter
from tracerelay.session import SessionState
from tracerelay.verify import VALID_INCOMPLETE, verify_session


def test_alarm_json_and_public_summary(tmp_path: Path) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    error = RuntimeError("relay worker failed")

    record = write_alarm(
        paths,
        source="service",
        reason="session_fault",
        service_pid=41,
        supervisor_pid=42,
        session_id="session-123",
        error=error,
    )

    payload = json.loads(record.path.read_text(encoding="utf-8"))
    assert payload == {
        "format_version": 1,
        "incident_id": record.incident_id,
        "created_at_utc": payload["created_at_utc"],
        "source": "service",
        "reason": "session_fault",
        "service_pid": 41,
        "supervisor_pid": 42,
        "session_id": "session-123",
        "exception_type": "RuntimeError",
        "message": "relay worker failed",
    }
    assert payload["created_at_utc"].endswith("Z")
    assert record.path.stem == record.incident_id
    assert record.public_summary() == {
        "incident_id": record.incident_id,
        "reason": "session_fault",
        "alarm_path": str(record.path),
    }
    assert latest_alarm_summary(paths) == record.public_summary()
    assert set(record.public_summary()) == {
        "incident_id",
        "reason",
        "alarm_path",
    }


def test_alarm_uses_reason_when_exception_message_is_empty(tmp_path: Path) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")

    record = write_alarm(
        paths,
        source="service",
        reason="supervisor_pipe_closed",
        service_pid=51,
        supervisor_pid=52,
        session_id=None,
        error=EOFError(),
    )

    payload = json.loads(record.path.read_text(encoding="utf-8"))
    assert payload["exception_type"] == "EOFError"
    assert payload["message"] == "supervisor_pipe_closed"


def test_managed_service_exchanges_heartbeat_and_stops_without_alarm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_001
    run = _start_service_runtime(paths, supervisor_pid, monkeypatch)

    try:
        run.connection.send(
            {
                "type": "heartbeat",
                "supervisor_pid": supervisor_pid,
                "sent_monotonic": time.monotonic(),
            }
        )
        status = _receive_type(run.connection, "status")
        assert status == {
            "type": "status",
            "service_pid": os.getpid(),
            "state": "IDLE",
            "session_id": None,
        }

        run.instance.stop_requested.set()
        stop_request = _receive_type(run.connection, "stop_request")
        assert stop_request == {
            "type": "stop_request",
            "service_pid": os.getpid(),
            "session_id": None,
        }
        run.connection.send(
            {"type": "stop_ack", "supervisor_pid": supervisor_pid}
        )
        _join_thread(run.thread)
    finally:
        run.connection.close()
        run.thread.join(timeout=2.0)

    assert run.result == [0]
    assert list(paths.alarms.glob("*.json")) == []


def test_invalid_stop_request_does_not_set_stop_requested(tmp_path: Path) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    service = service_module.TraceRelayService(paths=paths, control_port=0)
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    client = ControlClient(CONTROL_HOST, service.control_port, timeout=2.0)

    try:
        response = client.request({"command": "stop", "unexpected": 1})
        status = client.request({"command": "status"})
    finally:
        service.shutdown()
        thread.join(timeout=2.0)

    assert response["ok"] is False
    assert "unexpected request field" in response["error"]
    assert "stopping" not in response
    assert not service.stop_requested.is_set()
    assert status["ok"] is True
    assert status["state"] == "IDLE"
    assert not thread.is_alive()


def test_managed_service_pipe_close_writes_alarm_and_returns_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_002
    run = _start_service_runtime(paths, supervisor_pid, monkeypatch)

    run.connection.send(
        {
            "type": "heartbeat",
            "supervisor_pid": supervisor_pid,
            "sent_monotonic": time.monotonic(),
        }
    )
    _receive_type(run.connection, "status")
    run.connection.close()
    _join_thread(run.thread)

    assert run.result == [1]
    alarm = _only_alarm(paths)
    assert alarm["source"] == "service"
    assert alarm["reason"] == "supervisor_pipe_closed"
    assert alarm["service_pid"] == os.getpid()
    assert alarm["supervisor_pid"] == supervisor_pid
    assert alarm["session_id"] is None
    assert alarm["exception_type"] == "EOFError"


def test_pipe_close_exits_within_heartbeat_bound_when_session_worker_is_stuck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_005
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    listener.settimeout(3.0)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    blocked = threading.Event()
    release = threading.Event()

    def run_upstream() -> None:
        with listener:
            connection, _address = listener.accept()
            with connection:
                connection.settimeout(3.0)
                upstream_received.append(_receive_all(connection))

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    run = _start_service_runtime(paths, supervisor_pid, monkeypatch)
    client: socket.socket | None = None
    try:
        run.connection.send(
            {
                "type": "heartbeat",
                "supervisor_pid": supervisor_pid,
                "sent_monotonic": time.monotonic(),
            }
        )
        _receive_type(run.connection, "status")
        registration = run.instance.manager.register(upstream_port)
        client = socket.create_connection(
            (registration.proxy_host, registration.proxy_port), timeout=3.0
        )
        _wait_for_service_state(run.instance, SessionState.RELAYING)

        def block_journal_write(
            _writer: JournalWriter, _direction: Direction, _payload: bytes
        ) -> object:
            blocked.set()
            if not release.wait(HEARTBEAT_TIMEOUT_SECONDS):
                raise AssertionError("test did not release the stuck journal write")
            raise OSError("released stuck journal write")

        monkeypatch.setattr(JournalWriter, "append_data", block_journal_write)
        client.sendall(b"block-the-session-worker")
        assert blocked.wait(2.0)

        started = time.monotonic()
        run.connection.close()
        _join_thread(run.thread, timeout=HEARTBEAT_TIMEOUT_SECONDS)
        elapsed = time.monotonic() - started
        assert elapsed < HEARTBEAT_TIMEOUT_SECONDS
        client.settimeout(2.0)
        assert client.recv(1) == b""
    finally:
        release.set()
        if client is not None:
            client.close()
        run.connection.close()
        run.thread.join(timeout=2.0)
        upstream_thread.join(timeout=3.0)

    assert run.result == [1]
    assert not upstream_thread.is_alive()
    assert upstream_received == [b""]
    alarm = _only_alarm(paths)
    assert alarm["source"] == "service"
    assert alarm["reason"] == "supervisor_pipe_closed"
    assert alarm["session_id"] == registration.session_id


def test_managed_service_heartbeat_timeout_writes_alarm_and_returns_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_003
    monkeypatch.setattr(service_module, "HEARTBEAT_TIMEOUT_SECONDS", 0.15)
    run = _start_service_runtime(paths, supervisor_pid, monkeypatch)

    try:
        _join_thread(run.thread)
    finally:
        run.connection.close()

    assert run.result == [1]
    alarm = _only_alarm(paths)
    assert alarm["source"] == "service"
    assert alarm["reason"] == "supervisor_heartbeat_timeout"
    assert alarm["service_pid"] == os.getpid()
    assert alarm["supervisor_pid"] == supervisor_pid
    assert alarm["session_id"] is None
    assert alarm["exception_type"] == "TimeoutError"
    assert "no Supervisor heartbeat" in alarm["message"]


def test_managed_service_journal_fault_never_forwards_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_004
    payload = b"must-not-reach-upstream"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    listener.settimeout(3.0)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    upstream_errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(3.0)
                    upstream_received.append(_receive_all(connection))
        except BaseException as error:
            upstream_errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    run = _start_service_runtime(paths, supervisor_pid, monkeypatch)
    alarm_started = threading.Event()
    release_alarm = threading.Event()
    original_write_alarm = service_module.write_alarm
    client: socket.socket | None = None
    try:
        run.connection.send(
            {
                "type": "heartbeat",
                "supervisor_pid": supervisor_pid,
                "sent_monotonic": time.monotonic(),
            }
        )
        _receive_type(run.connection, "status")
        registration = run.instance.manager.register(upstream_port)
        client = socket.create_connection(
            (registration.proxy_host, registration.proxy_port), timeout=3.0
        )
        _wait_for_service_state(run.instance, SessionState.RELAYING)

        def fail_before_write(
            _writer: JournalWriter, _direction: Direction, _payload: bytes
        ) -> object:
            raise OSError("injected journal write failure")

        def pause_alarm(*args: object, **kwargs: object) -> object:
            alarm_started.set()
            if not release_alarm.wait(2.0):
                raise AssertionError("test did not release the alarm write")
            return original_write_alarm(*args, **kwargs)

        monkeypatch.setattr(JournalWriter, "append_data", fail_before_write)
        monkeypatch.setattr(service_module, "write_alarm", pause_alarm)
        client.sendall(payload)
        assert alarm_started.wait(2.0)
        assert run.instance.manager.status()["state"] == SessionState.FAULT.value
        client.settimeout(0.15)
        with pytest.raises(TimeoutError):
            client.recv(1)
        assert upstream_thread.is_alive()
        release_alarm.set()
        _join_thread(run.thread, timeout=3.0)
    finally:
        release_alarm.set()
        if client is not None:
            client.close()
        run.connection.close()
        run.thread.join(timeout=2.0)
        upstream_thread.join(timeout=3.0)

    assert run.result == [1]
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert upstream_received == [b""]
    alarm = _only_alarm(paths)
    assert alarm["source"] == "service"
    assert alarm["reason"] == "session_fault"
    assert alarm["service_pid"] == os.getpid()
    assert alarm["supervisor_pid"] == supervisor_pid
    assert alarm["session_id"] == registration.session_id
    assert alarm["exception_type"] == "OSError"
    assert "injected journal write failure" in alarm["message"]
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_INCOMPLETE
    assert verification.record_count == 0
    assert not (registration.session_path / "complete.json").exists()


def test_managed_service_quota_fault_alarms_exits_and_never_forwards_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tracerelay.journal import JOURNAL_RECORD_OVERHEAD, JournalLimitExceeded

    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_006
    payload = b"over-the-reduced-test-limit"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    listener.settimeout(3.0)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    upstream_errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(3.0)
                    upstream_received.append(_receive_all(connection))
        except BaseException as error:
            upstream_errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    run = _start_service_runtime(
        paths,
        supervisor_pid,
        monkeypatch,
        journal_limit_bytes=2 * JOURNAL_RECORD_OVERHEAD,
        admission_reserve_bytes=0,
    )
    registration = run.instance.manager.register(upstream_port)
    client = socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=3.0
    )
    try:
        _wait_for_service_state(run.instance, SessionState.RELAYING)
        client.sendall(payload)
        client.settimeout(3.0)
        assert client.recv(1) == b""
        _join_thread(run.thread, timeout=3.0)
    finally:
        client.close()
        run.connection.close()
        run.thread.join(timeout=2.0)
        upstream_thread.join(timeout=3.0)

    assert run.result == [1]
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert upstream_received == [b""]
    assert run.instance.manager.status()["state"] == SessionState.FAULT.value
    alarm = _only_alarm(paths)
    assert alarm["source"] == "service"
    assert alarm["reason"] == "session_fault"
    assert alarm["session_id"] == registration.session_id
    assert alarm["exception_type"] == JournalLimitExceeded.__name__
    assert "journal limit" in alarm["message"]
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_INCOMPLETE
    assert verification.record_count == 0
    assert not (registration.session_path / "complete.json").exists()


def test_admission_alarm_write_failure_faults_service_and_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    supervisor_pid = 71_007
    run = _start_service_runtime(paths, supervisor_pid, monkeypatch)
    monkeypatch.setattr(
        session_module.shutil,
        "disk_usage",
        lambda _path: type("Usage", (), {"free": 0})(),
    )

    def fail_alarm(*_args: object, **_kwargs: object) -> object:
        raise OSError("injected admission alarm failure")

    monkeypatch.setattr(service_module, "write_alarm", fail_alarm)
    try:
        response = run.instance.handle_request(
            {"command": "register", "upstream_port": 9}
        )
        _join_thread(run.thread, timeout=3.0)
    finally:
        run.connection.close()
        run.thread.join(timeout=2.0)

    assert response["ok"] is False
    assert response["state"] == SessionState.FAULT.value
    assert "last_alarm" not in response
    assert run.result == [1]
    assert list(paths.alarms.glob("*.json")) == []
    stderr = capsys.readouterr().err
    assert "alarm_write_failed" in stderr
    assert "injected admission alarm failure" in stderr


def test_supervisor_alarms_when_service_exits_abnormally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    process = _FakeProcess(pid=72_001, alive=False, exitcode=17)
    connection = _FakeConnection()
    _install_fake_context(monkeypatch, process, connection)

    exit_code = supervisor_module.run_supervisor(paths)

    assert exit_code == 1
    alarm = _only_alarm(paths)
    assert alarm["source"] == "supervisor"
    assert alarm["reason"] == "service_process_exited"
    assert alarm["service_pid"] == process.pid
    assert alarm["supervisor_pid"] == os.getpid()
    assert alarm["session_id"] is None
    assert alarm["exception_type"] == "ServiceProcessExit"
    assert "code 17" in alarm["message"]
    assert process.join_calls == [1.0]


def test_supervisor_acknowledges_normal_stop_without_alarm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    process = _FakeProcess(pid=72_002, alive=True, exitcode=None)
    connection = _FakeConnection()

    def respond_to_supervisor(message: object) -> None:
        if not isinstance(message, dict):
            return
        if message.get("type") == "heartbeat":
            connection.incoming.extend(
                [
                    {
                        "type": "status",
                        "service_pid": process.pid,
                        "state": "IDLE",
                        "session_id": None,
                    },
                    {
                        "type": "stop_request",
                        "service_pid": process.pid,
                        "session_id": "session-456",
                    },
                ]
            )
        elif message.get("type") == "stop_ack":
            process.alive = False
            process.exitcode = 0

    connection.on_send = respond_to_supervisor
    _install_fake_context(monkeypatch, process, connection)

    exit_code = supervisor_module.run_supervisor(paths)

    assert exit_code == 0
    assert [message["type"] for message in connection.sent] == [
        "heartbeat",
        "stop_ack",
    ]
    assert connection.sent[0]["supervisor_pid"] == os.getpid()
    assert connection.sent[1] == {
        "type": "stop_ack",
        "supervisor_pid": os.getpid(),
    }
    assert process.join_calls == [1.0]
    assert list(paths.alarms.glob("*.json")) == []


def test_supervisor_heartbeat_timeout_alarms_and_terminates_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    process = _FakeProcess(pid=72_003, alive=True, exitcode=None)
    connection = _FakeConnection()
    _install_fake_context(monkeypatch, process, connection)
    monkeypatch.setattr(supervisor_module, "HEARTBEAT_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(supervisor_module, "PROCESS_POLL_INTERVAL_SECONDS", 0.01)

    exit_code = supervisor_module.run_supervisor(paths)

    assert exit_code == 1
    assert [message["type"] for message in connection.sent] == ["heartbeat"]
    alarm = _only_alarm(paths)
    assert alarm["source"] == "supervisor"
    assert alarm["reason"] == "service_heartbeat_timeout"
    assert alarm["service_pid"] == process.pid
    assert alarm["supervisor_pid"] == os.getpid()
    assert alarm["session_id"] is None
    assert alarm["exception_type"] == "ServiceHeartbeatTimeout"
    assert "no Service heartbeat response" in alarm["message"]
    assert process.terminate_calls == 1
    assert process.kill_calls == 0
    assert process.join_calls == [0.5, 2.0]
    assert not process.is_alive()


def test_supervisor_stop_timeout_alarms_and_kills_stuck_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    process = _FakeProcess(
        pid=72_004,
        alive=True,
        exitcode=None,
        terminate_stops=False,
    )
    connection = _FakeConnection(
        incoming=[
            {
                "type": "stop_request",
                "service_pid": process.pid,
                "session_id": "session-stuck",
            }
        ]
    )
    _install_fake_context(monkeypatch, process, connection)
    monkeypatch.setattr(supervisor_module, "HEARTBEAT_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(supervisor_module, "PROCESS_POLL_INTERVAL_SECONDS", 0.01)

    exit_code = supervisor_module.run_supervisor(paths)

    assert exit_code == 1
    assert connection.sent == [
        {"type": "stop_ack", "supervisor_pid": os.getpid()}
    ]
    alarm = _only_alarm(paths)
    assert alarm["source"] == "supervisor"
    assert alarm["reason"] == "service_stop_timeout"
    assert alarm["service_pid"] == process.pid
    assert alarm["supervisor_pid"] == os.getpid()
    assert alarm["session_id"] == "session-stuck"
    assert alarm["exception_type"] == "TimeoutError"
    assert "did not exit after stop acknowledgement" in alarm["message"]
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.join_calls == [2.0, 2.0]
    assert not process.is_alive()


class _ServiceRun:
    def __init__(
        self,
        *,
        connection: multiprocessing.connection.Connection,
        instance: service_module.TraceRelayService,
        thread: threading.Thread,
        result: list[int],
    ) -> None:
        self.connection = connection
        self.instance = instance
        self.thread = thread
        self.result = result


def _start_service_runtime(
    paths: RuntimePaths,
    supervisor_pid: int,
    monkeypatch: pytest.MonkeyPatch,
    **service_options: object,
) -> _ServiceRun:
    original_service = service_module.TraceRelayService
    ready = threading.Event()
    instances: list[service_module.TraceRelayService] = []
    result: list[int] = []

    def build_service(**kwargs: Any) -> service_module.TraceRelayService:
        instance = original_service(control_port=0, **service_options, **kwargs)
        instances.append(instance)
        ready.set()
        return instance

    monkeypatch.setattr(service_module, "TraceRelayService", build_service)
    supervisor_connection, service_connection = multiprocessing.Pipe(duplex=True)

    def target() -> None:
        try:
            result.append(
                service_module.run_service(
                    paths=paths,
                    connection=service_connection,
                    supervisor_pid=supervisor_pid,
                )
            )
        finally:
            service_connection.close()

    thread = threading.Thread(target=target, name="test-managed-service")
    thread.start()
    if not ready.wait(2.0):
        supervisor_connection.close()
        thread.join(timeout=2.0)
        pytest.fail("managed Service did not initialize before the deadline")
    return _ServiceRun(
        connection=supervisor_connection,
        instance=instances[0],
        thread=thread,
        result=result,
    )


def _receive_type(
    connection: multiprocessing.connection.Connection,
    expected_type: str,
    timeout: float = 2.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    received: list[object] = []
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if connection.poll(min(0.05, max(0.0, remaining))):
            message = connection.recv()
            received.append(message)
            if isinstance(message, dict) and message.get("type") == expected_type:
                return message
    pytest.fail(
        f"did not receive {expected_type!r} before deadline; received={received!r}"
    )


def _join_thread(thread: threading.Thread, timeout: float = 2.0) -> None:
    thread.join(timeout=timeout)
    assert not thread.is_alive(), "managed Service did not exit before the deadline"


def _wait_for_service_state(
    service: service_module.TraceRelayService,
    expected: SessionState,
    timeout: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service.manager.status()["state"] == expected.value:
            return
        time.sleep(0.01)
    pytest.fail(
        f"Service did not reach {expected.value} before the deadline: "
        f"{service.manager.status()}"
    )


def _receive_all(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = connection.recv(32 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _only_alarm(paths: RuntimePaths) -> dict[str, object]:
    alarm_paths = list(paths.alarms.glob("*.json"))
    assert len(alarm_paths) == 1
    value = json.loads(alarm_paths[0].read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


class _FakeConnection:
    def __init__(
        self,
        incoming: list[object] | None = None,
        on_send: Callable[[object], None] | None = None,
    ) -> None:
        self.incoming = deque(incoming or [])
        self.on_send = on_send
        self.sent: list[dict[str, object]] = []
        self.closed = False

    def send(self, message: dict[str, object]) -> None:
        self.sent.append(message)
        if self.on_send is not None:
            self.on_send(message)

    def poll(self, _timeout: float = 0.0) -> bool:
        return bool(self.incoming)

    def recv(self) -> object:
        return self.incoming.popleft()

    def close(self) -> None:
        self.closed = True


class _FakeProcess:
    def __init__(
        self,
        *,
        pid: int,
        alive: bool,
        exitcode: int | None,
        terminate_stops: bool = True,
        kill_stops: bool = True,
    ) -> None:
        self.pid = pid
        self.alive = alive
        self.exitcode = exitcode
        self.terminate_stops = terminate_stops
        self.kill_stops = kill_stops
        self.started = False
        self.join_calls: list[float | None] = []
        self.terminate_calls = 0
        self.kill_calls = 0

    def start(self) -> None:
        self.started = True

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout: float | None = None) -> None:
        self.join_calls.append(timeout)

    def terminate(self) -> None:
        self.terminate_calls += 1
        if self.terminate_stops:
            self.alive = False
            self.exitcode = -15

    def kill(self) -> None:
        self.kill_calls += 1
        if self.kill_stops:
            self.alive = False
            self.exitcode = -9


class _FakeContext:
    def __init__(
        self, process: _FakeProcess, supervisor_connection: _FakeConnection
    ) -> None:
        self.process = process
        self.supervisor_connection = supervisor_connection
        self.service_connection = _FakeConnection()

    def Pipe(self, *, duplex: bool) -> tuple[_FakeConnection, _FakeConnection]:
        assert duplex is True
        return self.supervisor_connection, self.service_connection

    def Process(self, **kwargs: object) -> _FakeProcess:
        assert kwargs["target"] is service_module.managed_service_main
        assert kwargs["name"] == "TraceRelay-Service"
        assert kwargs["daemon"] is False
        return self.process


def _install_fake_context(
    monkeypatch: pytest.MonkeyPatch,
    process: _FakeProcess,
    connection: _FakeConnection,
) -> None:
    context = _FakeContext(process, connection)

    def get_context(method: str) -> _FakeContext:
        assert method == "spawn"
        return context

    monkeypatch.setattr(
        supervisor_module.multiprocessing, "get_context", get_context
    )
