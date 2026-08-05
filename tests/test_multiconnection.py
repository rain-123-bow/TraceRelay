from __future__ import annotations

import hashlib
import socket
import threading
import time
from pathlib import Path
from typing import Callable

import pytest

from tracerelay.config import CONTROL_HOST, RuntimePaths
from tracerelay.journal import HASH_SIZE, JOURNAL_HEADER, Direction, JournalWriter, RecordType
from tracerelay.session import SessionManager, SessionState
from tracerelay.verify import VALID_COMPLETE, VALID_INCOMPLETE, verify_session


def test_journal_tracks_offsets_per_connection(tmp_path: Path) -> None:
    journal = JournalWriter(tmp_path / "journal.trr")

    first = journal.append_data(
        Direction.CLIENT_TO_UPSTREAM,
        b"first",
        connection_id=1,
    )
    second = journal.append_data(
        Direction.CLIENT_TO_UPSTREAM,
        b"second",
        connection_id=2,
    )
    journal.append_send_ok(first)
    journal.append_send_ok(second)
    journal.close()

    assert first.connection_id == 1
    assert second.connection_id == 2
    assert first.stream_offset == 0
    assert second.stream_offset == 0


@pytest.mark.parametrize("connection_id", [0, -1, True, 1.0, 2**64])
def test_journal_rejects_invalid_connection_ids(
    tmp_path: Path,
    connection_id: object,
) -> None:
    journal = JournalWriter(tmp_path / f"{connection_id!s}.trr")
    try:
        with pytest.raises(ValueError, match="connection_id"):
            journal.append_data(
                Direction.CLIENT_TO_UPSTREAM,
                b"payload",
                connection_id=connection_id,  # type: ignore[arg-type]
            )
    finally:
        journal.close()


def test_one_session_accepts_sequential_connections_until_explicit_close(
    tmp_path: Path,
) -> None:
    upstream = _MultiConnectionEcho(expected_connections=2)
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream.port)
    endpoint = (registration.proxy_host, registration.proxy_port)

    first_reply = _round_trip(endpoint, b"first-connection")
    _wait_for_state(manager, SessionState.WAITING)
    assert manager.status()["session_id"] == registration.session_id

    second_reply = _round_trip(endpoint, b"second-connection")
    _wait_for_state(manager, SessionState.WAITING)
    closed = manager.close(timeout=3.0)
    upstream.finish()

    assert first_reply == b"echo:first-connection"
    assert second_reply == b"echo:second-connection"
    assert closed["closed"] is True
    assert closed["state"] == SessionState.IDLE.value
    assert sorted(upstream.received) == [b"first-connection", b"second-connection"]
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_COMPLETE
    assert verification.observed_connection_count == 2
    assert verification.observed_bytes == {
        "client_to_upstream": len(b"first-connection") + len(b"second-connection"),
        "upstream_to_client": len(b"echo:first-connection")
        + len(b"echo:second-connection"),
    }
    assert _rebuild_connection_streams(
        registration.session_path / "journal.trr"
    ) == {
        (1, Direction.CLIENT_TO_UPSTREAM): b"first-connection",
        (1, Direction.UPSTREAM_TO_CLIENT): b"echo:first-connection",
        (2, Direction.CLIENT_TO_UPSTREAM): b"second-connection",
        (2, Direction.UPSTREAM_TO_CLIENT): b"echo:second-connection",
    }
    with _expect_connection_failure():
        socket.create_connection(endpoint, timeout=0.5)


def test_one_session_relays_two_overlapping_connections_without_stream_merging(
    tmp_path: Path,
) -> None:
    upstream = _MultiConnectionEcho(expected_connections=2, gate_until_all=True)
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream.port)
    endpoint = (registration.proxy_host, registration.proxy_port)
    payloads = [b"concurrent-alpha", b"concurrent-beta"]
    replies: dict[bytes, bytes] = {}
    errors: list[BaseException] = []
    start = threading.Barrier(3)

    def run_client(payload: bytes) -> None:
        try:
            start.wait()
            replies[payload] = _round_trip(endpoint, payload)
        except BaseException as error:
            errors.append(error)

    clients = [
        threading.Thread(target=run_client, args=(payload,), daemon=True)
        for payload in payloads
    ]
    for client in clients:
        client.start()
    start.wait()
    assert upstream.all_accepted.wait(3.0)
    _wait_for_state(manager, SessionState.RELAYING)
    for client in clients:
        client.join(timeout=5.0)

    assert all(not client.is_alive() for client in clients)
    assert errors == []
    assert replies == {payload: b"echo:" + payload for payload in payloads}
    _wait_for_state(manager, SessionState.WAITING)
    manager.close(timeout=3.0)
    upstream.finish()

    verification = verify_session(registration.session_path)
    assert verification.status == VALID_COMPLETE
    assert verification.observed_connection_count == 2


def test_explicit_close_disconnects_all_active_connections(tmp_path: Path) -> None:
    upstream = _MultiConnectionEcho(expected_connections=2, hold_open=True)
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream.port)
    endpoint = (registration.proxy_host, registration.proxy_port)
    clients = [socket.create_connection(endpoint, timeout=3.0) for _ in range(2)]
    for index, client in enumerate(clients):
        client.settimeout(3.0)
        client.sendall(f"client-{index}".encode())
    assert upstream.all_accepted.wait(3.0)
    assert upstream.all_payloads_observed.wait(3.0)
    _wait_for_state(manager, SessionState.RELAYING)

    closed = manager.close(timeout=3.0)
    disconnected = []
    for client in clients:
        try:
            disconnected.append(client.recv(1) == b"")
        except ConnectionResetError:
            disconnected.append(True)
        finally:
            client.close()
    upstream.release.set()
    upstream.finish()

    assert closed["closed"] is True
    assert disconnected == [True, True]
    verification = verify_session(registration.session_path)
    assert verification.status == VALID_COMPLETE
    assert verification.observed_connection_count == 2


def test_one_connection_eof_does_not_hide_another_active_connection(
    tmp_path: Path,
) -> None:
    upstream = _SelectiveEcho()
    manager = SessionManager(RuntimePaths.from_root(tmp_path / "runtime"))
    registration = manager.register(upstream.port)
    endpoint = (registration.proxy_host, registration.proxy_port)
    held = socket.create_connection(endpoint, timeout=3.0)
    held.settimeout(5.0)
    held.sendall(b"hold")
    assert upstream.hold_received.wait(3.0)

    assert _round_trip(endpoint, b"short") == b"echo:short"
    assert manager.status()["state"] == SessionState.RELAYING.value

    upstream.release_hold.set()
    assert _receive_all(held) == b"echo:hold"
    held.shutdown(socket.SHUT_WR)
    held.close()
    _wait_for_state(manager, SessionState.WAITING)
    manager.close(timeout=3.0)
    upstream.finish()

    assert verify_session(registration.session_path).status == VALID_COMPLETE


def test_journal_failure_in_one_connection_faults_the_whole_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream = _MultiConnectionEcho(expected_connections=2, hold_open=True)
    faults: list[BaseException] = []
    manager = SessionManager(
        RuntimePaths.from_root(tmp_path / "runtime"),
        on_fault=lambda _registration, error: faults.append(error),
    )
    registration = manager.register(upstream.port)
    endpoint = (registration.proxy_host, registration.proxy_port)
    healthy = socket.create_connection(endpoint, timeout=3.0)
    faulty = socket.create_connection(endpoint, timeout=3.0)
    healthy.settimeout(3.0)
    faulty.settimeout(3.0)
    assert upstream.all_accepted.wait(3.0)
    original_append_data = JournalWriter.append_data

    def fail_selected_payload(
        journal: JournalWriter,
        direction: Direction,
        payload: bytes,
        *,
        connection_id: int = 1,
    ) -> object:
        if payload == b"fault-this-connection":
            raise OSError("injected multi-connection journal failure")
        return original_append_data(
            journal,
            direction,
            payload,
            connection_id=connection_id,
        )

    monkeypatch.setattr(JournalWriter, "append_data", fail_selected_payload)
    healthy.sendall(b"healthy-connection")
    _wait_until(
        lambda: b"healthy-connection" in upstream.received,
        "healthy connection bytes to reach upstream",
    )
    faulty.sendall(b"fault-this-connection")
    _wait_for_state(manager, SessionState.FAULT)
    assert _is_disconnected(healthy)
    assert _is_disconnected(faulty)
    healthy.close()
    faulty.close()
    upstream.release.set()
    upstream.finish()

    assert len(faults) == 1
    assert isinstance(faults[0], OSError)
    assert not (registration.session_path / "complete.json").exists()
    assert verify_session(registration.session_path).status == VALID_INCOMPLETE


def test_new_upstream_connect_failure_terminates_existing_healthy_connection(
    tmp_path: Path,
) -> None:
    upstream = _OneConnectionThenRefuse()
    faults: list[BaseException] = []
    manager = SessionManager(
        RuntimePaths.from_root(tmp_path / "runtime"),
        on_fault=lambda _registration, error: faults.append(error),
    )
    registration = manager.register(upstream.port)
    endpoint = (registration.proxy_host, registration.proxy_port)
    healthy = socket.create_connection(endpoint, timeout=3.0)
    healthy.settimeout(3.0)
    assert upstream.accepted.wait(3.0)
    healthy.sendall(b"healthy-before-second-connect")
    _wait_until(
        lambda: upstream.received == b"healthy-before-second-connect",
        "healthy bytes to reach the sole upstream connection",
    )
    failing = socket.create_connection(endpoint, timeout=3.0)
    failing.settimeout(3.0)

    _wait_for_state(manager, SessionState.FAULT)
    assert _is_disconnected(healthy)
    assert _is_disconnected(failing)
    healthy.close()
    failing.close()
    upstream.finish()

    assert len(faults) == 1
    assert isinstance(faults[0], OSError)
    assert not (registration.session_path / "complete.json").exists()
    assert verify_session(registration.session_path).status == VALID_INCOMPLETE


class _MultiConnectionEcho:
    def __init__(
        self,
        *,
        expected_connections: int,
        gate_until_all: bool = False,
        hold_open: bool = False,
    ) -> None:
        self.expected_connections = expected_connections
        self.gate_until_all = gate_until_all
        self.hold_open = hold_open
        self.received: list[bytes] = []
        self.errors: list[BaseException] = []
        self.all_accepted = threading.Event()
        self.all_payloads_observed = threading.Event()
        self.release = threading.Event()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind((CONTROL_HOST, 0))
        self._listener.listen(expected_connections)
        self._listener.settimeout(5.0)
        self.port = int(self._listener.getsockname()[1])
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        workers: list[threading.Thread] = []
        try:
            with self._listener:
                for _ in range(self.expected_connections):
                    connection, _address = self._listener.accept()
                    worker = threading.Thread(
                        target=self._serve_connection,
                        args=(connection,),
                        daemon=True,
                    )
                    workers.append(worker)
                    worker.start()
                self.all_accepted.set()
                for worker in workers:
                    worker.join(timeout=5.0)
                    if worker.is_alive():
                        raise AssertionError("upstream connection worker did not stop")
        except BaseException as error:
            self.errors.append(error)
            self.all_accepted.set()

    def _serve_connection(self, connection: socket.socket) -> None:
        try:
            with connection:
                connection.settimeout(5.0)
                payload = (
                    connection.recv(32 * 1024)
                    if self.hold_open
                    else _receive_all(connection)
                )
                with self._lock:
                    self.received.append(payload)
                    if len(self.received) == self.expected_connections:
                        self.all_payloads_observed.set()
                if self.gate_until_all and not self.all_accepted.wait(5.0):
                    raise AssertionError("upstream did not accept every connection")
                if self.hold_open and not self.release.wait(5.0):
                    raise AssertionError("test did not release held upstream connection")
                if not self.hold_open:
                    connection.sendall(b"echo:" + payload)
                    connection.shutdown(socket.SHUT_WR)
        except BaseException as error:
            self.errors.append(error)

    def finish(self) -> None:
        self._thread.join(timeout=6.0)
        assert not self._thread.is_alive()
        assert self.errors == []


class _OneConnectionThenRefuse:
    def __init__(self) -> None:
        self.received = b""
        self.errors: list[BaseException] = []
        self.accepted = threading.Event()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind((CONTROL_HOST, 0))
        self._listener.listen(1)
        self._listener.settimeout(5.0)
        self.port = int(self._listener.getsockname()[1])
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            connection, _address = self._listener.accept()
            self._listener.close()
            self.accepted.set()
            with connection:
                connection.settimeout(5.0)
                while True:
                    chunk = connection.recv(32 * 1024)
                    if not chunk:
                        break
                    self.received += chunk
        except BaseException as error:
            self.errors.append(error)
            self.accepted.set()

    def finish(self) -> None:
        self._thread.join(timeout=5.0)
        assert not self._thread.is_alive()
        assert self.errors == []


class _SelectiveEcho:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []
        self.hold_received = threading.Event()
        self.release_hold = threading.Event()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind((CONTROL_HOST, 0))
        self._listener.listen(2)
        self._listener.settimeout(5.0)
        self.port = int(self._listener.getsockname()[1])
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        workers: list[threading.Thread] = []
        try:
            with self._listener:
                for _ in range(2):
                    connection, _address = self._listener.accept()
                    worker = threading.Thread(
                        target=self._serve,
                        args=(connection,),
                        daemon=True,
                    )
                    workers.append(worker)
                    worker.start()
                for worker in workers:
                    worker.join(timeout=6.0)
                    if worker.is_alive():
                        raise AssertionError("selective upstream worker did not stop")
        except BaseException as error:
            self.errors.append(error)

    def _serve(self, connection: socket.socket) -> None:
        try:
            with connection:
                connection.settimeout(5.0)
                payload = connection.recv(32 * 1024)
                if payload == b"hold":
                    self.hold_received.set()
                    if not self.release_hold.wait(5.0):
                        raise AssertionError("test did not release held connection")
                else:
                    payload += _receive_all(connection)
                connection.sendall(b"echo:" + payload)
                connection.shutdown(socket.SHUT_WR)
                if payload == b"hold":
                    _receive_all(connection)
        except BaseException as error:
            self.errors.append(error)

    def finish(self) -> None:
        self._thread.join(timeout=7.0)
        assert not self._thread.is_alive()
        assert self.errors == []


class _expect_connection_failure:
    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        _traceback: object,
    ) -> bool:
        if exception_type is None:
            raise AssertionError("connection unexpectedly succeeded")
        return isinstance(exception, OSError)


def _round_trip(endpoint: tuple[str, int], payload: bytes) -> bytes:
    with socket.create_connection(endpoint, timeout=3.0) as client:
        client.settimeout(5.0)
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        return _receive_all(client)


def _receive_all(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = connection.recv(32 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _rebuild_connection_streams(
    path: Path,
) -> dict[tuple[int, Direction], bytes]:
    data = path.read_bytes()
    offset = 0
    expected_sequence = 1
    previous_hash = bytes(HASH_SIZE)
    streams: dict[tuple[int, Direction], bytearray] = {}
    while offset < len(data):
        header = data[offset : offset + JOURNAL_HEADER.size]
        assert len(header) == JOURNAL_HEADER.size
        offset += JOURNAL_HEADER.size
        (
            magic,
            version,
            record_type_value,
            direction_value,
            connection_id,
            sequence,
            _utc_ns,
            _monotonic_ns,
            _related_sequence,
            stream_offset,
            payload_length,
            _result_code,
            recorded_previous_hash,
        ) = JOURNAL_HEADER.unpack(header)
        payload = data[offset : offset + payload_length]
        offset += payload_length
        current_hash = data[offset : offset + HASH_SIZE]
        offset += HASH_SIZE
        assert magic == b"TRR1"
        assert version == 2
        assert sequence == expected_sequence
        assert recorded_previous_hash == previous_hash
        assert current_hash == hashlib.sha256(header + payload).digest()
        if RecordType(record_type_value) is RecordType.DATA:
            direction = Direction(direction_value)
            key = (connection_id, direction)
            stream = streams.setdefault(key, bytearray())
            assert stream_offset == len(stream)
            stream.extend(payload)
        previous_hash = current_hash
        expected_sequence += 1
    return {key: bytes(value) for key, value in streams.items()}


def _wait_for_state(
    manager: SessionManager,
    expected: SessionState,
    timeout: float = 5.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if manager.status()["state"] == expected.value:
            return
        time.sleep(0.01)
    raise AssertionError(f"session did not reach {expected.value}: {manager.status()}")


def _wait_until(
    predicate: Callable[[], bool],
    description: str,
    timeout: float = 5.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {description}")


def _is_disconnected(connection: socket.socket) -> bool:
    try:
        return connection.recv(1) == b""
    except (ConnectionResetError, ConnectionAbortedError):
        return True
