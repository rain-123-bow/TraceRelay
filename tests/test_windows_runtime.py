from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

import pytest

from tracerelay.config import (
    CONTROL_HOST,
    CONTROL_PORT,
    CONTROL_PROTOCOL_VERSION,
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_TIMEOUT_SECONDS,
    PRODUCT_NAME,
)


pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="the detached M2 runtime is Windows-only"
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_PROCESS_EXIT_TIMEOUT = HEARTBEAT_TIMEOUT_SECONDS + 3.0
_FAILURE_EXIT_BOUND = HEARTBEAT_TIMEOUT_SECONDS + 0.5
_CLI_TIMEOUT = 20.0
_POLL_INTERVAL = 0.05
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class _CliResult:
    returncode: int
    payload: dict[str, Any]
    stdout: str
    stderr: str


class _RuntimeHarness:
    def __init__(self, local_app_data: Path) -> None:
        self.local_app_data = local_app_data
        self.local_app_data.mkdir(parents=True, exist_ok=False)
        self.runtime_root = self.local_app_data / PRODUCT_NAME
        self.sessions = self.runtime_root / "sessions"
        self.alarms = self.runtime_root / "alarms"
        self._owned_roles: dict[int, str] = {}
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "LOCALAPPDATA": str(self.local_app_data),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            }
        )
        source_path = str(_REPOSITORY_ROOT / "src")
        existing_python_path = self.environment.get("PYTHONPATH")
        self.environment["PYTHONPATH"] = (
            source_path
            if not existing_python_path
            else source_path + os.pathsep + existing_python_path
        )

    def cli(self, *arguments: object, timeout: float = _CLI_TIMEOUT) -> _CliResult:
        command = [
            sys.executable,
            "-m",
            "tracerelay",
            *(str(argument) for argument in arguments),
        ]
        completed = subprocess.run(
            command,
            cwd=_REPOSITORY_ROOT,
            env=self.environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        stdout = completed.stdout.decode("utf-8", errors="strict")
        stderr = completed.stderr.decode("utf-8", errors="strict")
        payloads: list[dict[str, Any]] = []
        non_json_lines: list[str] = []
        for stream in (stdout, stderr):
            for line in stream.splitlines():
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    non_json_lines.append(line)
                    continue
                if isinstance(value, dict):
                    payloads.append(value)
                else:
                    non_json_lines.append(line)
        if non_json_lines or len(payloads) != 1:
            raise AssertionError(
                "CLI did not emit exactly one JSON object: "
                f"command={command!r}, returncode={completed.returncode}, "
                f"stdout={stdout!r}, stderr={stderr!r}"
            )
        return _CliResult(completed.returncode, payloads[0], stdout, stderr)

    def remember_runtime(self, payload: dict[str, Any]) -> tuple[int, int]:
        assert payload.get("ok") is True
        assert payload.get("product") == PRODUCT_NAME
        assert payload.get("protocol_version") == CONTROL_PROTOCOL_VERSION
        assert payload.get("mode") == "managed"
        service_pid = payload.get("service_pid")
        supervisor_pid = payload.get("supervisor_pid")
        assert type(service_pid) is int and service_pid > 0
        assert type(supervisor_pid) is int and supervisor_pid > 0
        assert service_pid != supervisor_pid
        self._owned_roles[service_pid] = "service"
        self._owned_roles[supervisor_pid] = "supervisor"
        return service_pid, supervisor_pid

    def mark_exited(self, process_ids: tuple[int, ...]) -> None:
        for process_id in process_ids:
            assert not _process_is_running(process_id)
            self._owned_roles.pop(process_id, None)

    def alarm_records(self) -> list[dict[str, Any]]:
        if not self.alarms.exists():
            return []
        records: list[dict[str, Any]] = []
        for alarm_path in sorted(self.alarms.glob("*.json")):
            value = json.loads(alarm_path.read_text(encoding="utf-8"))
            assert isinstance(value, dict)
            _assert_alarm_schema(alarm_path, value)
            records.append(value)
        return records

    def cleanup(self) -> None:
        if self._owned_roles or not _control_port_is_free():
            self._discover_runtime_for_cleanup()

        ordered = sorted(
            self._owned_roles,
            key=lambda process_id: (
                self._owned_roles[process_id] != "service",
                process_id,
            ),
        )
        for process_id in ordered:
            if _process_is_running(process_id):
                _terminate_process(process_id)

        if ordered:
            _wait_until(
                lambda: all(not _process_is_running(pid) for pid in ordered),
                _PROCESS_EXIT_TIMEOUT,
                f"owned TraceRelay processes to exit: {ordered!r}",
            )
        _wait_until(
            _control_port_is_free,
            3.0,
            f"control port {CONTROL_PORT} to be released",
        )
        self._owned_roles.clear()

    def _discover_runtime_for_cleanup(self) -> None:
        if _control_port_is_free():
            return
        try:
            status = self.cli("status", timeout=5.0)
            if status.returncode == 0:
                self.remember_runtime(status.payload)
        except (AssertionError, OSError, subprocess.TimeoutExpired):
            return


@pytest.fixture
def runtime(tmp_path: Path) -> _RuntimeHarness:
    assert _control_port_is_free(), (
        f"TCP {CONTROL_PORT} is already occupied; refusing to disturb an "
        "unrelated process"
    )
    harness = _RuntimeHarness(tmp_path / "local-app-data")
    try:
        yield harness
    finally:
        harness.cleanup()


def test_detached_start_status_repeat_start_and_normal_stop(
    runtime: _RuntimeHarness,
) -> None:
    first, process_ids = _start_runtime(runtime)
    assert first.payload["started"] is True
    assert first.payload["already_running"] is False
    assert runtime.alarm_records() == []

    status = _status(runtime)
    assert runtime.remember_runtime(status.payload) == process_ids
    repeated = runtime.cli("start")
    assert repeated.returncode == 0
    assert repeated.payload["started"] is False
    assert repeated.payload["already_running"] is True
    assert runtime.remember_runtime(repeated.payload) == process_ids

    survival_deadline = time.monotonic() + HEARTBEAT_TIMEOUT_SECONDS + 0.75
    observations = 0
    while time.monotonic() < survival_deadline:
        remaining = survival_deadline - time.monotonic()
        time.sleep(min(0.75, max(0.0, remaining)))
        current = _status(runtime)
        assert runtime.remember_runtime(current.payload) == process_ids
        observations += 1
    assert observations >= 2

    stopped = _stop_runtime(runtime, process_ids)
    assert stopped.payload["closed"] is False
    assert stopped.payload["state"] == "IDLE"
    assert runtime.alarm_records() == []
    unavailable = runtime.cli("status")
    assert unavailable.returncode == 1
    assert unavailable.payload["state"] == "NOT_RUNNING"


def test_start_rejects_foreign_protocol_without_launching(
    runtime: _RuntimeHarness,
) -> None:
    with _ForeignControlServer() as foreign:
        result = runtime.cli("start")

        assert result.returncode == 1
        assert result.payload["ok"] is False
        assert result.payload["command"] == "start"
        assert "non-TraceRelay protocol" in result.payload["error"]
        assert "service_pid" not in result.payload
        assert "supervisor_pid" not in result.payload
        _wait_until(
            lambda: len(foreign.requests) == 1,
            2.0,
            "the foreign listener to receive the start probe",
        )
        assert foreign.errors == []
        assert not runtime._owned_roles
        assert runtime.alarm_records() == []

    _wait_until(
        _control_port_is_free,
        2.0,
        f"foreign listener to release TCP {CONTROL_PORT}",
    )
    _assert_control_port_stays_free(1.0)
    assert runtime.alarm_records() == []


def test_killed_service_is_alarmed_and_not_restarted(
    runtime: _RuntimeHarness,
) -> None:
    _started, process_ids = _start_runtime(runtime)
    service_pid, supervisor_pid = process_ids

    failure_started = time.monotonic()
    failure_deadline = failure_started + _FAILURE_EXIT_BOUND
    _terminate_process(service_pid)
    _wait_until(
        lambda: _has_alarm(
            runtime.alarm_records(),
            source="supervisor",
            reason="service_process_exited",
        ),
        _remaining(failure_deadline),
        "Supervisor abnormal-Service alarm",
    )
    _wait_until(
        lambda: all(not _process_is_running(pid) for pid in process_ids),
        _remaining(failure_deadline),
        "Supervisor to observe the killed Service and exit",
    )
    assert time.monotonic() - failure_started <= _FAILURE_EXIT_BOUND
    runtime.mark_exited(process_ids)
    alarms = runtime.alarm_records()

    assert len(alarms) == 1
    assert alarms[0]["source"] == "supervisor"
    assert alarms[0]["reason"] == "service_process_exited"
    assert alarms[0]["service_pid"] == service_pid
    assert alarms[0]["supervisor_pid"] == supervisor_pid
    assert alarms[0]["session_id"] is None
    _wait_until(
        _control_port_is_free,
        2.0,
        f"control port {CONTROL_PORT} after Service termination",
    )

    unavailable = runtime.cli("status")
    assert unavailable.returncode == 1
    assert unavailable.payload["state"] == "NOT_RUNNING"
    assert unavailable.payload["last_alarm"] == {
        "incident_id": alarms[0]["incident_id"],
        "reason": alarms[0]["reason"],
        "alarm_path": str(
            runtime.alarms / f"{alarms[0]['incident_id']}.json"
        ),
    }
    _assert_control_port_stays_free(HEARTBEAT_INTERVAL_SECONDS + 0.5)
    assert not _process_is_running(service_pid)
    assert not _process_is_running(supervisor_pid)
    assert runtime.alarm_records() == alarms


def test_killed_supervisor_aborts_active_session_and_service_alarms(
    runtime: _RuntimeHarness,
) -> None:
    payload = b"evidence-before-supervisor-loss"
    with _HoldingUpstream() as upstream:
        _started, process_ids = _start_runtime(runtime)
        service_pid, supervisor_pid = process_ids
        registration = _register(runtime, upstream.port)
        session_path = Path(registration["session_path"])
        client = socket.create_connection(
            (registration["proxy_host"], registration["proxy_port"]),
            timeout=3.0,
        )
        client.settimeout(0.2)
        try:
            assert upstream.accepted.wait(3.0)
            client.sendall(payload)
            _wait_until(
                lambda: upstream.received == payload,
                3.0,
                "client bytes to reach the upstream before Supervisor loss",
            )
            assert _status(runtime).payload["state"] == "RELAYING"

            failure_started = time.monotonic()
            failure_deadline = failure_started + _FAILURE_EXIT_BOUND
            _terminate_process(supervisor_pid)
            _wait_until(
                lambda: _has_alarm(runtime.alarm_records(), source="service"),
                _remaining(failure_deadline),
                "Service alarm after Supervisor termination",
            )
            _wait_until(
                lambda: all(not _process_is_running(pid) for pid in process_ids),
                _remaining(failure_deadline),
                "Service to abort and exit after Supervisor termination",
            )
            assert time.monotonic() - failure_started <= _FAILURE_EXIT_BOUND
            _wait_for_disconnect(client, 2.0)
            assert upstream.peer_closed.wait(2.0)
        finally:
            client.close()

    runtime.mark_exited(process_ids)
    alarms = runtime.alarm_records()
    assert len(alarms) == 1
    alarm = alarms[0]
    assert alarm["source"] == "service"
    assert alarm["reason"] in {
        "supervisor_pipe_closed",
        "supervisor_pipe_failed",
        "supervisor_heartbeat_timeout",
    }
    assert alarm["service_pid"] == service_pid
    assert alarm["supervisor_pid"] == supervisor_pid
    assert alarm["session_id"] == registration["session_id"]
    verification = runtime.cli("verify", session_path)
    assert verification.returncode == 0
    assert verification.payload["status"] == "VALID_INCOMPLETE"
    assert not (session_path / "complete.json").exists()
    _wait_until(
        _control_port_is_free,
        2.0,
        f"control port {CONTROL_PORT} after Supervisor termination",
    )


def test_upstream_connection_failure_alarms_and_preserves_incomplete_evidence(
    runtime: _RuntimeHarness,
) -> None:
    _started, process_ids = _start_runtime(runtime)
    service_pid, supervisor_pid = process_ids
    with _refusing_upstream_port() as unused_port:
        registration = _register(runtime, unused_port)
        session_path = Path(registration["session_path"])

        failure_started = time.monotonic()
        failure_deadline = failure_started + _FAILURE_EXIT_BOUND
        client = socket.create_connection(
            (registration["proxy_host"], registration["proxy_port"]),
            timeout=3.0,
        )
        client.settimeout(0.2)
        try:
            _wait_until(
                lambda: _has_alarm(
                    runtime.alarm_records(),
                    source="service",
                    reason="session_fault",
                ),
                _remaining(failure_deadline),
                "Service upstream-connect failure alarm",
            )
            _wait_for_disconnect(client, _remaining(failure_deadline))
        finally:
            client.close()

    _wait_until(
        lambda: all(not _process_is_running(pid) for pid in process_ids),
        _remaining(failure_deadline),
        "both processes to exit after upstream failure",
    )
    assert time.monotonic() - failure_started <= _FAILURE_EXIT_BOUND
    runtime.mark_exited(process_ids)
    alarms = runtime.alarm_records()
    service_alarms = [alarm for alarm in alarms if alarm["source"] == "service"]
    assert len(service_alarms) == 1
    assert service_alarms[0]["reason"] == "session_fault"
    assert service_alarms[0]["service_pid"] == service_pid
    assert service_alarms[0]["supervisor_pid"] == supervisor_pid
    assert service_alarms[0]["session_id"] == registration["session_id"]
    verification = runtime.cli("verify", session_path)
    assert verification.returncode == 0
    assert verification.payload["status"] == "VALID_INCOMPLETE"
    assert not (session_path / "complete.json").exists()
    _wait_until(
        _control_port_is_free,
        2.0,
        f"control port {CONTROL_PORT} after upstream failure",
    )


def test_normal_stop_during_bidirectional_traffic_completes_without_alarm(
    runtime: _RuntimeHarness,
) -> None:
    request = b"client-to-upstream-" * 128
    response = b"upstream-to-client-" * 96
    with _HoldingUpstream(response=response, respond_after=len(request)) as upstream:
        _started, process_ids = _start_runtime(runtime)
        registration = _register(runtime, upstream.port)
        session_path = Path(registration["session_path"])
        client = socket.create_connection(
            (registration["proxy_host"], registration["proxy_port"]),
            timeout=3.0,
        )
        client.settimeout(2.0)
        try:
            assert upstream.accepted.wait(3.0)
            client.sendall(request)
            assert _receive_exact(client, len(response), 3.0) == response
            _wait_until(
                lambda: upstream.received == request,
                3.0,
                "all client bytes to reach the upstream",
            )
            status = _status(runtime)
            assert status.payload["state"] == "RELAYING"
            assert runtime.remember_runtime(status.payload) == process_ids

            stopped = _stop_runtime(runtime, process_ids)
            assert stopped.payload["closed"] is True
            assert stopped.payload["session_id"] == registration["session_id"]
            _wait_for_disconnect(client, 2.0)
            assert upstream.peer_closed.wait(2.0)
        finally:
            client.close()

    verification = runtime.cli("verify", session_path)
    assert verification.returncode == 0
    assert verification.payload["status"] == "VALID_COMPLETE"
    assert verification.payload["observed_bytes"] == {
        "client_to_upstream": len(request),
        "upstream_to_client": len(response),
    }
    assert verification.payload["sent_success_bytes"] == {
        "client_to_upstream": len(request),
        "upstream_to_client": len(response),
    }
    assert runtime.alarm_records() == []


def test_restart_and_new_session_never_modify_old_evidence(
    runtime: _RuntimeHarness,
) -> None:
    _first_start, first_process_ids = _start_runtime(runtime)
    first_registration = _register(runtime, 9)
    first_path = Path(first_registration["session_path"])
    first_close = runtime.cli("close")
    assert first_close.returncode == 0
    assert first_close.payload["ok"] is True
    assert first_close.payload["closed"] is True
    first_verification = runtime.cli("verify", first_path)
    assert first_verification.payload["status"] == "VALID_COMPLETE"
    original_evidence = _snapshot_files(first_path)
    assert set(original_evidence) == {
        "complete.json",
        "journal.trr",
        "session.json",
    }
    _stop_runtime(runtime, first_process_ids)

    _second_start, second_process_ids = _start_runtime(runtime)
    second_registration = _register(runtime, 10)
    second_path = Path(second_registration["session_path"])
    assert second_registration["session_id"] != first_registration["session_id"]
    assert second_path != first_path
    assert _snapshot_files(first_path) == original_evidence

    second_close = runtime.cli("close")
    assert second_close.returncode == 0
    assert second_close.payload["closed"] is True
    _stop_runtime(runtime, second_process_ids)

    assert _snapshot_files(first_path) == original_evidence
    assert runtime.cli("verify", first_path).payload["status"] == "VALID_COMPLETE"
    assert runtime.cli("verify", second_path).payload["status"] == "VALID_COMPLETE"
    assert {path.name for path in runtime.sessions.iterdir() if path.is_dir()} == {
        first_registration["session_id"],
        second_registration["session_id"],
    }
    assert runtime.alarm_records() == []


def _start_runtime(
    runtime: _RuntimeHarness,
) -> tuple[_CliResult, tuple[int, int]]:
    assert _control_port_is_free()
    result = runtime.cli("start")
    assert result.returncode == 0
    assert result.payload["ok"] is True
    assert result.payload["command"] == "start"
    assert result.payload["state"] == "IDLE"
    process_ids = runtime.remember_runtime(result.payload)
    assert all(_process_is_running(process_id) for process_id in process_ids)
    return result, process_ids


def _status(runtime: _RuntimeHarness) -> _CliResult:
    result = runtime.cli("status")
    assert result.returncode == 0
    assert result.payload["ok"] is True
    assert result.payload["command"] == "status"
    return result


def _register(runtime: _RuntimeHarness, upstream_port: int) -> dict[str, Any]:
    result = runtime.cli("register", "--upstream-port", upstream_port)
    assert result.returncode == 0
    assert result.payload["ok"] is True
    assert result.payload["command"] == "register"
    assert result.payload["state"] == "WAITING"
    assert result.payload["proxy_host"] == CONTROL_HOST
    assert type(result.payload["proxy_port"]) is int
    assert result.payload["upstream_host"] == CONTROL_HOST
    assert result.payload["upstream_port"] == upstream_port
    return result.payload


def _stop_runtime(
    runtime: _RuntimeHarness, process_ids: tuple[int, int]
) -> _CliResult:
    result = runtime.cli("stop")
    assert result.returncode == 0
    assert result.payload["ok"] is True
    assert result.payload["command"] == "stop"
    assert result.payload["stopping"] is True
    assert result.payload["stopped"] is True
    assert (
        result.payload["service_pid"],
        result.payload["supervisor_pid"],
    ) == process_ids
    _wait_until(
        lambda: all(not _process_is_running(pid) for pid in process_ids),
        2.0,
        "normal stop to terminate both reported processes",
    )
    runtime.mark_exited(process_ids)
    _wait_until(
        _control_port_is_free,
        2.0,
        f"normal stop to release TCP {CONTROL_PORT}",
    )
    return result


def _assert_alarm_schema(path: Path, alarm: dict[str, Any]) -> None:
    assert set(alarm) == {
        "created_at_utc",
        "exception_type",
        "format_version",
        "incident_id",
        "message",
        "reason",
        "service_pid",
        "session_id",
        "source",
        "supervisor_pid",
    }
    assert alarm["format_version"] == 1
    assert alarm["incident_id"] == path.stem
    assert isinstance(alarm["created_at_utc"], str) and alarm["created_at_utc"]
    assert alarm["source"] in {"service", "supervisor"}
    assert isinstance(alarm["reason"], str) and alarm["reason"]
    assert isinstance(alarm["message"], str) and alarm["message"]
    exception_type = alarm["exception_type"]
    assert exception_type is None or (
        isinstance(exception_type, str) and exception_type
    )
    for field in ("service_pid", "supervisor_pid"):
        value = alarm[field]
        assert value is None or (type(value) is int and value > 0)
    session_id = alarm["session_id"]
    assert session_id is None or (isinstance(session_id, str) and session_id)


def _has_alarm(
    alarms: list[dict[str, Any]],
    *,
    source: str,
    reason: str | None = None,
) -> bool:
    return any(
        alarm.get("source") == source
        and (reason is None or alarm.get("reason") == reason)
        for alarm in alarms
    )


def _wait_until(
    predicate: Callable[[], _T], timeout: float, description: str
) -> _T:
    deadline = time.monotonic() + timeout
    last_value: object = None
    last_error: BaseException | None = None
    while True:
        try:
            value = predicate()
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            last_error = error
        else:
            last_value = value
            if value:
                return value
        if time.monotonic() >= deadline:
            detail = (
                f"last_error={last_error!r}"
                if last_error is not None
                else f"last_value={last_value!r}"
            )
            raise AssertionError(
                f"timed out after {timeout:g}s waiting for {description}; {detail}"
            )
        time.sleep(_POLL_INTERVAL)


def _remaining(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def _control_port_is_free() -> bool:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind((CONTROL_HOST, CONTROL_PORT))
        return True
    except OSError:
        return False
    finally:
        listener.close()


def _assert_control_port_stays_free(duration: float) -> None:
    deadline = time.monotonic() + duration
    observations = 0
    while time.monotonic() < deadline:
        assert _control_port_is_free()
        observations += 1
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    assert observations >= 2


def _windows_kernel32() -> Any:
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _process_is_running(process_id: int) -> bool:
    synchronize = 0x00100000
    wait_object_0 = 0x00000000
    wait_timeout = 0x00000102
    wait_failed = 0xFFFFFFFF
    error_access_denied = 5
    error_invalid_parameter = 87
    kernel32 = _windows_kernel32()
    open_process = kernel32.OpenProcess
    open_process.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    open_process.restype = ctypes.c_void_p
    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    wait_for_single_object.restype = ctypes.c_uint32
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (ctypes.c_void_p,)
    close_handle.restype = ctypes.c_int

    handle = open_process(synchronize, False, process_id)
    if not handle:
        error_code = ctypes.get_last_error()
        if error_code == error_invalid_parameter:
            return False
        if error_code == error_access_denied:
            return True
        raise ctypes.WinError(error_code)
    try:
        wait_result = wait_for_single_object(handle, 0)
        if wait_result == wait_timeout:
            return True
        if wait_result == wait_object_0:
            return False
        if wait_result == wait_failed:
            raise ctypes.WinError(ctypes.get_last_error())
        raise OSError(f"unexpected process wait result: {wait_result}")
    finally:
        close_handle(handle)


def _terminate_process(process_id: int) -> None:
    process_terminate = 0x0001
    synchronize = 0x00100000
    error_invalid_parameter = 87
    kernel32 = _windows_kernel32()
    open_process = kernel32.OpenProcess
    open_process.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    open_process.restype = ctypes.c_void_p
    terminate_process = kernel32.TerminateProcess
    terminate_process.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    terminate_process.restype = ctypes.c_int
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (ctypes.c_void_p,)
    close_handle.restype = ctypes.c_int

    handle = open_process(process_terminate | synchronize, False, process_id)
    if not handle:
        error_code = ctypes.get_last_error()
        if error_code == error_invalid_parameter:
            return
        raise ctypes.WinError(error_code)
    try:
        if not terminate_process(handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        close_handle(handle)


@contextmanager
def _refusing_upstream_port() -> Iterator[int]:
    reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            reservation.setsockopt(
                socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
            )
        reservation.bind((CONTROL_HOST, 0))
        yield int(reservation.getsockname()[1])
    finally:
        reservation.close()


def _receive_exact(connection: socket.socket, size: int, timeout: float) -> bytes:
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    received = 0
    while received < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(
                f"timed out receiving {size} bytes; received {received}"
            )
        connection.settimeout(min(0.2, remaining))
        try:
            chunk = connection.recv(size - received)
        except TimeoutError:
            continue
        if not chunk:
            raise AssertionError(
                f"connection closed after {received} of {size} expected bytes"
            )
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


def _wait_for_disconnect(connection: socket.socket, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError("connection did not close before the deadline")
        connection.settimeout(min(0.2, remaining))
        try:
            payload = connection.recv(1)
        except TimeoutError:
            continue
        except (ConnectionAbortedError, ConnectionResetError):
            return
        if payload == b"":
            return
        raise AssertionError(f"unexpected byte while waiting for EOF: {payload!r}")


def _snapshot_files(directory: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


class _ForeignControlServer:
    def __init__(self) -> None:
        self.requests: list[bytes] = []
        self.errors: list[BaseException] = []
        self._stop = threading.Event()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self._listener.setsockopt(
                socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
            )
        self._listener.bind((CONTROL_HOST, CONTROL_PORT))
        self._listener.listen(1)
        self._listener.settimeout(0.1)
        self._thread = threading.Thread(
            target=self._run,
            name="TraceRelay-test-foreign-control",
            daemon=True,
        )

    def __enter__(self) -> _ForeignControlServer:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        self._listener.close()
        self._thread.join(timeout=2.0)
        assert not self._thread.is_alive()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    connection, _address = self._listener.accept()
                except TimeoutError:
                    continue
                except OSError:
                    if self._stop.is_set():
                        return
                    raise
                with connection:
                    connection.settimeout(2.0)
                    request = bytearray()
                    while b"\n" not in request:
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        request.extend(chunk)
                    self.requests.append(bytes(request))
                    connection.sendall(
                        b'{"ok":true,"command":"status","state":"IDLE"}\n'
                    )
        except BaseException as error:
            if not self._stop.is_set():
                self.errors.append(error)


class _HoldingUpstream:
    def __init__(self, *, response: bytes = b"", respond_after: int = 0) -> None:
        self.response = response
        self.respond_after = respond_after
        self.accepted = threading.Event()
        self.response_sent = threading.Event()
        self.peer_closed = threading.Event()
        self.errors: list[BaseException] = []
        self._received = bytearray()
        self._received_lock = threading.Lock()
        self._stop = threading.Event()
        self._connection_lock = threading.Lock()
        self._connection: socket.socket | None = None
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self._listener.setsockopt(
                socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
            )
        self._listener.bind((CONTROL_HOST, 0))
        self.port = int(self._listener.getsockname()[1])
        self._listener.listen(1)
        self._listener.settimeout(0.1)
        self._thread = threading.Thread(
            target=self._run,
            name="TraceRelay-test-holding-upstream",
            daemon=True,
        )

    @property
    def received(self) -> bytes:
        with self._received_lock:
            return bytes(self._received)

    def __enter__(self) -> _HoldingUpstream:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        with self._connection_lock:
            connection = self._connection
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        self._listener.close()
        self._thread.join(timeout=2.0)
        assert not self._thread.is_alive()
        assert self.errors == []

    def _run(self) -> None:
        try:
            connection: socket.socket | None = None
            while connection is None and not self._stop.is_set():
                try:
                    connection, _address = self._listener.accept()
                except TimeoutError:
                    continue
                except OSError:
                    if self._stop.is_set():
                        return
                    raise
            if connection is None:
                return
            with self._connection_lock:
                self._connection = connection
            with connection:
                connection.settimeout(0.1)
                self.accepted.set()
                sent = not self.response
                while not self._stop.is_set():
                    try:
                        payload = connection.recv(32 * 1024)
                    except TimeoutError:
                        continue
                    if not payload:
                        self.peer_closed.set()
                        return
                    with self._received_lock:
                        self._received.extend(payload)
                        received_size = len(self._received)
                    if not sent and received_size >= self.respond_after:
                        connection.sendall(self.response)
                        sent = True
                        self.response_sent.set()
        except BaseException as error:
            if not self._stop.is_set():
                self.errors.append(error)
        finally:
            with self._connection_lock:
                self._connection = None
