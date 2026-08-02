from __future__ import annotations

import json
import random
import socket
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tracerelay import session as session_module
from tracerelay.config import (
    CONTROL_HOST,
    JOURNAL_LIMIT_BYTES,
    SESSION_ADMISSION_RESERVE_BYTES,
    RuntimePaths,
)
from tracerelay.journal import (
    JOURNAL_RECORD_OVERHEAD,
    DataReference,
    Direction,
    JournalLimitExceeded,
    JournalWriter,
)
from tracerelay.session import (
    SessionAdmissionError,
    SessionBusyError,
    SessionManager,
    SessionState,
)
from tracerelay.verify import VALID_COMPLETE, VALID_INCOMPLETE, verify_session


def test_random_binary_round_trip_creates_valid_complete_evidence(
    tmp_path: Path,
) -> None:
    generator = random.Random(42)
    request = generator.randbytes(96_123)
    response = generator.randbytes(83_777)
    upstream_port, received, upstream_errors, upstream_thread = _start_upstream(response)
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)

    with socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    ) as client:
        client.settimeout(5.0)
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        reply = _receive_all(client)

    upstream_thread.join(timeout=5.0)
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert received == [request]
    assert reply == response
    _wait_for_state(manager, SessionState.IDLE)

    result = verify_session(registration.session_path)
    assert result.status == VALID_COMPLETE
    assert result.observed_bytes == {
        "client_to_upstream": len(request),
        "upstream_to_client": len(response),
    }
    assert result.sent_success_bytes == result.observed_bytes
    assert all(value == 0 for value in result.sent_error_bytes.values())
    assert all(value == 0 for value in result.unknown_bytes.values())


def test_waiting_session_rejects_second_registration_and_closes_cleanly(
    tmp_path: Path,
) -> None:
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(9)

    with pytest.raises(SessionBusyError):
        manager.register(10)

    close_result = manager.close(timeout=2.0)

    assert close_result["closed"] is True
    assert manager.status()["state"] == SessionState.IDLE.value
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_COMPLETE
    assert verification.record_count == 0


def test_storage_admission_happens_before_a_session_directory_is_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal_limit = 1_024
    reserve = 16
    required = journal_limit + reserve
    free_bytes = required - 1
    monkeypatch.setattr(
        session_module.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=free_bytes),
    )
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    manager = SessionManager(
        paths,
        journal_limit_bytes=journal_limit,
        admission_reserve_bytes=reserve,
    )

    with pytest.raises(SessionAdmissionError, match="insufficient free space"):
        manager.register(9)

    assert manager.status() == {"state": SessionState.IDLE.value}
    assert list(paths.sessions.iterdir()) == []

    free_bytes = required
    registration = manager.register(9)
    metadata = json.loads(
        (registration.session_path / "session.json").read_text(encoding="utf-8")
    )
    assert metadata["limits"]["journal_limit_bytes"] == journal_limit
    assert metadata["limits"]["admission_required_free_bytes"] == required
    manager.close(timeout=2.0)
    assert verify_session(registration.session_path).status == VALID_COMPLETE


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"journal_limit_bytes": JOURNAL_LIMIT_BYTES + 1}, "journal_limit_bytes"),
        (
            {"admission_reserve_bytes": SESSION_ADMISSION_RESERVE_BYTES + 1},
            "admission_reserve_bytes",
        ),
    ],
)
def test_session_manager_rejects_limits_outside_the_v1_boundary(
    tmp_path: Path, options: dict[str, int], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SessionManager(RuntimePaths.from_root(tmp_path / message), **options)


def test_over_limit_data_is_not_forwarded_and_session_remains_incomplete(
    tmp_path: Path,
) -> None:
    payload = b"must-not-cross-the-quota-boundary"
    upstream_port, received, upstream_errors, upstream_thread = _start_upstream(b"")
    faults: list[BaseException] = []
    manager = SessionManager(
        RuntimePaths.from_root(tmp_path / "runtime"),
        on_fault=lambda _registration, error: faults.append(error),
        journal_limit_bytes=2 * JOURNAL_RECORD_OVERHEAD,
        admission_reserve_bytes=0,
    )
    registration = manager.register(upstream_port)

    with socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    ) as client:
        client.settimeout(5.0)
        client.sendall(payload)
        assert client.recv(1) == b""

    _wait_for_state(manager, SessionState.FAULT)
    upstream_thread.join(timeout=5.0)
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert received == [b""]
    assert len(faults) == 1
    assert isinstance(faults[0], JournalLimitExceeded)
    assert (registration.session_path / "journal.trr").stat().st_size == 0
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_INCOMPLETE
    assert verification.record_count == 0
    assert not (registration.session_path / "complete.json").exists()


def test_second_client_and_same_session_reconnect_are_rejected(
    tmp_path: Path,
) -> None:
    payload = b"first-client-only"
    upstream_port, received, upstream_errors, upstream_thread = _start_upstream(b"")
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)
    endpoint = (registration.proxy_host, registration.proxy_port)
    first = socket.create_connection(endpoint, timeout=5.0)
    first.settimeout(5.0)
    try:
        _wait_for_state(manager, SessionState.RELAYING)
        with pytest.raises(SessionBusyError):
            manager.register(upstream_port)
        with pytest.raises(OSError):
            socket.create_connection(endpoint, timeout=1.0)
        assert [path.name for path in manager.paths.sessions.iterdir()] == [
            registration.session_id
        ]
        first.sendall(payload)
        first.shutdown(socket.SHUT_WR)
        assert _receive_all(first) == b""
    finally:
        first.close()

    _wait_for_state(manager, SessionState.IDLE)
    with pytest.raises(OSError):
        socket.create_connection(endpoint, timeout=1.0)
    upstream_thread.join(timeout=5.0)
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert received == [payload]
    assert verify_session(registration.session_path).status == VALID_COMPLETE


def test_restart_preserves_incomplete_evidence_and_uses_a_new_session(
    tmp_path: Path,
) -> None:
    paths = RuntimePaths.from_root(tmp_path / "runtime")
    first_manager = SessionManager(paths)
    first = first_manager.register(9)
    first_manager.abort("simulated process restart")
    first_snapshot = {
        path.name: path.read_bytes()
        for path in first.session_path.iterdir()
        if path.is_file()
    }

    second_manager = SessionManager(paths)
    second = second_manager.register(10)
    second_manager.close(timeout=2.0)

    assert first.session_id != second.session_id
    assert first_snapshot == {
        path.name: path.read_bytes()
        for path in first.session_path.iterdir()
        if path.is_file()
    }
    assert "complete.json" not in first_snapshot
    assert verify_session(first.session_path).status == VALID_INCOMPLETE
    assert verify_session(second.session_path).status == VALID_COMPLETE


def test_reverse_half_close_keeps_the_other_direction_relaying(
    tmp_path: Path,
) -> None:
    generator = random.Random(84)
    request = generator.randbytes(75_321)
    response = generator.randbytes(92_117)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    upstream_port = int(listener.getsockname()[1])
    received: list[bytes] = []
    errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(5.0)
                    connection.sendall(response)
                    connection.shutdown(socket.SHUT_WR)
                    received.append(_receive_all(connection))
        except BaseException as error:
            errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)

    with socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    ) as client:
        client.settimeout(5.0)
        reply = _receive_all(client)
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)

    upstream_thread.join(timeout=5.0)
    assert not upstream_thread.is_alive()
    assert errors == []
    assert reply == response
    assert received == [request]
    _wait_for_state(manager, SessionState.IDLE)

    result = verify_session(registration.session_path)
    assert result.status == VALID_COMPLETE
    assert result.observed_bytes == {
        "client_to_upstream": len(request),
        "upstream_to_client": len(response),
    }
    assert result.sent_success_bytes == result.observed_bytes


def test_active_close_disconnects_both_peers_and_seals_cleanly(
    tmp_path: Path,
) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    upstream_errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(5.0)
                    upstream_received.append(_receive_all(connection))
        except BaseException as error:
            upstream_errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)
    client = socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    )
    client.settimeout(5.0)
    _wait_for_state(manager, SessionState.RELAYING)

    with pytest.raises(OSError):
        socket.create_connection(
            (registration.proxy_host, registration.proxy_port), timeout=0.5
        )

    closed = manager.close(timeout=2.0)
    client_eof = client.recv(1)
    client.close()
    upstream_thread.join(timeout=5.0)

    assert closed["closed"] is True
    assert closed["state"] == SessionState.IDLE.value
    assert client_eof == b""
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert upstream_received == [b""]
    assert verify_session(registration.session_path).status == VALID_COMPLETE
    with pytest.raises(OSError):
        socket.create_connection(
            (registration.proxy_host, registration.proxy_port), timeout=0.5
        )


def test_close_allows_an_inflight_durable_block_to_finish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"durable-before-close" * 1024
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    upstream_errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(5.0)
                    upstream_received.append(_receive_all(connection))
        except BaseException as error:
            upstream_errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)
    client = socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    )
    client.settimeout(5.0)
    _wait_for_state(manager, SessionState.RELAYING)

    durable = threading.Event()
    release = threading.Event()
    original_append_data = JournalWriter.append_data

    def pause_after_durable_write(
        journal: JournalWriter, direction: Direction, data: bytes
    ) -> DataReference:
        reference = original_append_data(journal, direction, data)
        durable.set()
        if not release.wait(2.0):
            raise AssertionError("test did not release the durable DATA record")
        return reference

    monkeypatch.setattr(JournalWriter, "append_data", pause_after_durable_write)
    client.sendall(payload)
    assert durable.wait(2.0)

    close_results: list[dict[str, object]] = []
    close_errors: list[BaseException] = []

    def close_session() -> None:
        try:
            close_results.append(manager.close(timeout=2.0))
        except BaseException as error:
            close_errors.append(error)

    close_thread = threading.Thread(target=close_session, daemon=True)
    close_thread.start()
    time.sleep(0.05)
    assert close_thread.is_alive()
    release.set()
    close_thread.join(timeout=3.0)
    client_eof = client.recv(1)
    client.close()
    upstream_thread.join(timeout=5.0)

    assert not close_thread.is_alive()
    assert close_errors == []
    assert close_results[0]["closed"] is True
    assert close_results[0]["state"] == SessionState.IDLE.value
    assert client_eof == b""
    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert upstream_received == [payload]
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_COMPLETE
    assert verification.observed_bytes["client_to_upstream"] == len(payload)
    assert verification.sent_success_bytes["client_to_upstream"] == len(payload)


def test_journal_write_failure_never_forwards_the_unflushed_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"must-not-be-forwarded"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    upstream_errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(5.0)
                    upstream_received.append(_receive_all(connection))
        except BaseException as error:
            upstream_errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)
    client = socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    )
    client.settimeout(5.0)
    _wait_for_state(manager, SessionState.RELAYING)

    def fail_before_durable_write(
        _journal: JournalWriter, _direction: Direction, _data: bytes
    ) -> DataReference:
        raise OSError("injected journal write failure")

    monkeypatch.setattr(JournalWriter, "append_data", fail_before_durable_write)
    client.sendall(payload)
    _wait_for_state(manager, SessionState.FAULT)
    client.close()
    upstream_thread.join(timeout=5.0)

    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert upstream_received == [b""]
    result = verify_session(registration.session_path)
    assert result.status == VALID_INCOMPLETE
    assert result.record_count == 0
    assert all(value == 0 for value in result.observed_bytes.values())
    assert not (registration.session_path / "complete.json").exists()


def test_result_write_failure_reports_forwarded_data_as_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"forwarded-before-result-failure" * 256
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    upstream_port = int(listener.getsockname()[1])
    upstream_received: list[bytes] = []
    upstream_errors: list[BaseException] = []

    def run_upstream() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(5.0)
                    upstream_received.append(_receive_all(connection))
        except BaseException as error:
            upstream_errors.append(error)

    upstream_thread = threading.Thread(target=run_upstream, daemon=True)
    upstream_thread.start()
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream_port)
    client = socket.create_connection(
        (registration.proxy_host, registration.proxy_port), timeout=5.0
    )
    client.settimeout(5.0)
    _wait_for_state(manager, SessionState.RELAYING)

    def fail_result_write(
        _journal: JournalWriter, _reference: DataReference
    ) -> None:
        raise OSError("injected SEND_OK write failure")

    monkeypatch.setattr(JournalWriter, "append_send_ok", fail_result_write)
    client.sendall(payload)
    client.shutdown(socket.SHUT_WR)
    _wait_for_state(manager, SessionState.FAULT)
    client.close()
    upstream_thread.join(timeout=5.0)

    assert not upstream_thread.is_alive()
    assert upstream_errors == []
    assert upstream_received == [payload]
    result = verify_session(registration.session_path)
    assert result.status == VALID_INCOMPLETE
    assert result.observed_bytes["client_to_upstream"] == len(payload)
    assert result.sent_success_bytes["client_to_upstream"] == 0
    assert result.unknown_bytes["client_to_upstream"] == len(payload)
    assert not (registration.session_path / "complete.json").exists()


def test_sequential_sessions_use_new_directories_and_never_rewrite_old_evidence(
    tmp_path: Path,
) -> None:
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    first = manager.register(9)
    manager.close(timeout=2.0)
    first_journal = (first.session_path / "journal.trr").read_bytes()
    first_complete = (first.session_path / "complete.json").read_bytes()

    second = manager.register(10)
    manager.close(timeout=2.0)

    assert first.session_id != second.session_id
    assert first.session_path != second.session_path
    assert first.session_path.is_dir()
    assert second.session_path.is_dir()
    assert (first.session_path / "journal.trr").read_bytes() == first_journal
    assert (first.session_path / "complete.json").read_bytes() == first_complete
    assert json.loads(
        (first.session_path / "session.json").read_text(encoding="utf-8")
    )["upstream_port"] == 9
    assert json.loads(
        (second.session_path / "session.json").read_text(encoding="utf-8")
    )["upstream_port"] == 10
    assert verify_session(first.session_path).status == VALID_COMPLETE
    assert verify_session(second.session_path).status == VALID_COMPLETE


def _start_upstream(
    response: bytes,
) -> tuple[int, list[bytes], list[BaseException], threading.Thread]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((CONTROL_HOST, 0))
    listener.listen(1)
    listener.settimeout(5.0)
    port = int(listener.getsockname()[1])
    received: list[bytes] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            with listener:
                connection, _address = listener.accept()
                with connection:
                    connection.settimeout(5.0)
                    received.append(_receive_all(connection))
                    connection.sendall(response)
                    connection.shutdown(socket.SHUT_WR)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run, name="TraceRelay-test-upstream", daemon=True)
    thread.start()
    return port, received, errors, thread


def _receive_all(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = connection.recv(32 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _wait_for_state(
    manager: SessionManager, expected: SessionState, timeout: float = 5.0
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if manager.status()["state"] == expected.value:
            return
        time.sleep(0.01)
    raise AssertionError(f"session did not reach {expected.value}: {manager.status()}")
