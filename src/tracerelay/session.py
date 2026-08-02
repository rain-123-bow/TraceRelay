"""Single-session state machine and foreground TCP relay for TraceRelay v1."""

from __future__ import annotations

import errno
import select
import shutil
import socket
import threading
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable

from .config import (
    CLOSE_TIMEOUT_SECONDS,
    CONTROL_HOST,
    CONTROL_MESSAGE_LIMIT,
    FORMAT_VERSION,
    JOURNAL_LIMIT_BYTES,
    READ_CHUNK_SIZE,
    SESSION_ADMISSION_RESERVE_BYTES,
    UPSTREAM_CONNECT_TIMEOUT_SECONDS,
    RuntimePaths,
    atomic_write_json,
    new_session_id,
    utc_now_text,
)
from .journal import Direction, JournalWriter


class SessionState(StrEnum):
    IDLE = "IDLE"
    WAITING = "WAITING"
    CONNECTING = "CONNECTING"
    RELAYING = "RELAYING"
    FAULT = "FAULT"


class SessionError(RuntimeError):
    """Base class for expected session-control failures."""


class SessionBusyError(SessionError):
    pass


class SessionAdmissionError(SessionError):
    pass


class SessionCloseTimeout(SessionError):
    pass


@dataclass(frozen=True, slots=True)
class SessionRegistration:
    session_id: str
    proxy_host: str
    proxy_port: int
    upstream_host: str
    upstream_port: int
    session_path: Path

    def as_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "proxy_host": self.proxy_host,
            "proxy_port": self.proxy_port,
            "upstream_host": self.upstream_host,
            "upstream_port": self.upstream_port,
            "session_path": str(self.session_path),
        }


class SessionManager:
    """Own the sole waiting or running session allowed by v1."""

    def __init__(
        self,
        paths: RuntimePaths,
        *,
        on_fault: Callable[[SessionRegistration, BaseException], None] | None = None,
        journal_limit_bytes: int = JOURNAL_LIMIT_BYTES,
        admission_reserve_bytes: int = SESSION_ADMISSION_RESERVE_BYTES,
    ) -> None:
        if (
            type(journal_limit_bytes) is not int
            or not 1 <= journal_limit_bytes <= JOURNAL_LIMIT_BYTES
        ):
            raise ValueError(
                "journal_limit_bytes must be an integer between 1 and "
                f"{JOURNAL_LIMIT_BYTES}"
            )
        if (
            type(admission_reserve_bytes) is not int
            or not 0 <= admission_reserve_bytes <= SESSION_ADMISSION_RESERVE_BYTES
        ):
            raise ValueError(
                "admission_reserve_bytes must be an integer between 0 and "
                f"{SESSION_ADMISSION_RESERVE_BYTES}"
            )
        self.paths = paths
        self.paths.ensure()
        self._fault_callback = on_fault
        self._journal_limit_bytes = journal_limit_bytes
        self._admission_required_bytes = (
            journal_limit_bytes + admission_reserve_bytes
        )
        self._lock = threading.Lock()
        self._state = SessionState.IDLE
        self._active: _RelaySession | None = None
        self._last_session_id: str | None = None
        self._last_session_path: Path | None = None
        self._last_error: str | None = None
        self.faulted = threading.Event()

    def register(self, upstream_port: int) -> SessionRegistration:
        _validate_port(upstream_port)
        with self._lock:
            if self._state is not SessionState.IDLE or self._active is not None:
                raise SessionBusyError(f"cannot register while state is {self._state}")

            try:
                free_bytes = shutil.disk_usage(self.paths.sessions).free
            except OSError as error:
                raise SessionAdmissionError(
                    f"cannot determine available session storage: {error}"
                ) from error
            if free_bytes < self._admission_required_bytes:
                raise SessionAdmissionError(
                    "insufficient free space for a new session: "
                    f"{free_bytes} bytes available, "
                    f"{self._admission_required_bytes} bytes required"
                )

            session_id = new_session_id()
            session_path = self.paths.sessions / session_id
            session_path.mkdir(parents=False, exist_ok=False)
            listener: socket.socket | None = None
            journal: JournalWriter | None = None
            try:
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                listener.bind((CONTROL_HOST, 0))
                proxy_port = int(listener.getsockname()[1])
                metadata = {
                    "format_version": FORMAT_VERSION,
                    "session_id": session_id,
                    "created_at_utc": utc_now_text(),
                    "proxy_host": CONTROL_HOST,
                    "proxy_port": proxy_port,
                    "upstream_host": CONTROL_HOST,
                    "upstream_port": upstream_port,
                    "limits": {
                        "read_chunk_size": READ_CHUNK_SIZE,
                        "control_message_limit": CONTROL_MESSAGE_LIMIT,
                        "journal_limit_bytes": self._journal_limit_bytes,
                        "admission_required_free_bytes": self._admission_required_bytes,
                        "upstream_connect_timeout_seconds": UPSTREAM_CONNECT_TIMEOUT_SECONDS,
                        "single_client": True,
                    },
                }
                atomic_write_json(session_path / "session.json", metadata)
                journal = JournalWriter(
                    session_path / "journal.trr",
                    max_bytes=self._journal_limit_bytes,
                )
                listener.listen(1)
                registration = SessionRegistration(
                    session_id=session_id,
                    proxy_host=CONTROL_HOST,
                    proxy_port=proxy_port,
                    upstream_host=CONTROL_HOST,
                    upstream_port=upstream_port,
                    session_path=session_path,
                )
                relay = _RelaySession(
                    registration=registration,
                    listener=listener,
                    journal=journal,
                    on_state=self._on_state,
                    on_fault=self._on_fault,
                    on_finished=self._on_finished,
                )
                self._active = relay
                self._state = SessionState.WAITING
                self._last_error = None
                self.faulted.clear()
                relay.start()
                return registration
            except BaseException:
                if listener is not None:
                    _close_socket(listener)
                if journal is not None:
                    journal.close()
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            result: dict[str, object] = {"state": self._state.value}
            if self._active is not None:
                result.update(self._active.registration.as_dict())
            if self._last_session_id is not None:
                result["last_session_id"] = self._last_session_id
            if self._last_session_path is not None:
                result["last_session_path"] = str(self._last_session_path)
            if self._last_error is not None:
                result["last_error"] = self._last_error
            return result

    def close(self, timeout: float = CLOSE_TIMEOUT_SECONDS) -> dict[str, object]:
        with self._lock:
            relay = self._active
            state = self._state
        if relay is None:
            return {"closed": False, "state": state.value}

        relay.request_close()
        if not relay.done.wait(timeout):
            relay.force_abort()
            raise SessionCloseTimeout(f"session did not close within {timeout:g} seconds")
        result = self.status()
        if result["state"] == SessionState.FAULT.value:
            detail = result.get("last_error", "session ended incomplete")
            raise SessionError(f"session ended incomplete: {detail}")
        result["closed"] = True
        result["session_id"] = relay.registration.session_id
        return result

    def shutdown(self, timeout: float = CLOSE_TIMEOUT_SECONDS) -> None:
        with self._lock:
            relay = self._active
        if relay is None:
            return
        relay.request_close()
        if not relay.done.wait(timeout):
            relay.force_abort()

    def abort(self, reason: str, timeout: float = 2.0) -> None:
        """Force the active session incomplete after a process-level fault."""

        if not isinstance(reason, str) or not reason:
            raise ValueError("abort reason must be a non-empty string")
        with self._lock:
            relay = self._active
            if relay is None:
                self._state = SessionState.FAULT
                self._last_error = reason
                self.faulted.set()
                return
        relay.force_abort()
        if not relay.done.wait(timeout):
            with self._lock:
                if self._active is relay:
                    self._state = SessionState.FAULT
                    self._last_error = reason
                    self.faulted.set()

    def _on_state(self, relay: _RelaySession, state: SessionState) -> None:
        with self._lock:
            if self._active is relay:
                self._state = state

    def _on_fault(self, relay: _RelaySession, error: BaseException) -> None:
        with self._lock:
            if self._active is not relay:
                return
            self._state = SessionState.FAULT
            self._last_error = str(error)
        try:
            if self._fault_callback is not None:
                self._fault_callback(relay.registration, error)
        finally:
            with self._lock:
                if self._active is relay:
                    self.faulted.set()

    def _on_finished(
        self, relay: _RelaySession, completed: bool, error: BaseException | None
    ) -> None:
        with self._lock:
            if self._active is not relay:
                return
            self._last_session_id = relay.registration.session_id
            self._last_session_path = relay.registration.session_path
            self._active = None
            if completed:
                self._state = SessionState.IDLE
                self._last_error = None
                self.faulted.clear()
            else:
                self._state = SessionState.FAULT
                self._last_error = str(error) if error is not None else "session aborted"
                self.faulted.set()


class _RelaySession:
    def __init__(
        self,
        *,
        registration: SessionRegistration,
        listener: socket.socket,
        journal: JournalWriter,
        on_state: Callable[[_RelaySession, SessionState], None],
        on_fault: Callable[[_RelaySession, BaseException], None],
        on_finished: Callable[[_RelaySession, bool, BaseException | None], None],
    ) -> None:
        self.registration = registration
        self.done = threading.Event()
        self._listener = listener
        self._journal = journal
        self._on_state = on_state
        self._on_fault = on_fault
        self._on_finished = on_finished
        self._stop = threading.Event()
        self._close_requested = threading.Event()
        self._forced = threading.Event()
        self._socket_lock = threading.Lock()
        self._failure_lock = threading.Lock()
        self._failure: BaseException | None = None
        self._fault_notified = False
        self._client: socket.socket | None = None
        self._upstream: socket.socket | None = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"TraceRelay-{registration.session_id}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def request_close(self) -> None:
        self._close_requested.set()
        self._stop.set()
        _close_socket(self._listener)

    def force_abort(self) -> None:
        self._forced.set()
        self.request_close()
        self._shutdown_connections()

    def _run(self) -> None:
        completed = False
        failure: BaseException | None = None
        try:
            client = self._accept_client()
            if client is None:
                if self._forced.is_set():
                    raise SessionError("session was forcibly aborted while waiting")
                self._seal("close_requested_waiting")
                completed = True
                return

            self._on_state(self, SessionState.CONNECTING)
            if self._close_requested.is_set():
                self._seal("close_requested_connecting")
                completed = True
                return

            try:
                upstream = socket.create_connection(
                    (self.registration.upstream_host, self.registration.upstream_port),
                    timeout=UPSTREAM_CONNECT_TIMEOUT_SECONDS,
                )
            except OSError:
                if self._close_requested.is_set() and not self._forced.is_set():
                    self._seal("close_requested_connecting")
                    completed = True
                    return
                raise
            upstream.settimeout(None)
            with self._socket_lock:
                self._upstream = upstream
            if self._close_requested.is_set():
                self._shutdown_connections()

            self._on_state(self, SessionState.RELAYING)
            workers = [
                threading.Thread(
                    target=self._relay,
                    args=(client, upstream, Direction.CLIENT_TO_UPSTREAM),
                    name="TraceRelay-client-to-upstream",
                    daemon=True,
                ),
                threading.Thread(
                    target=self._relay,
                    args=(upstream, client, Direction.UPSTREAM_TO_CLIENT),
                    name="TraceRelay-upstream-to-client",
                    daemon=True,
                ),
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()

            with self._failure_lock:
                failure = self._failure
            if failure is not None:
                raise failure
            if self._forced.is_set():
                raise SessionError("session was forcibly aborted")
            reason = "close_requested" if self._close_requested.is_set() else "peer_eof"
            self._seal(reason)
            completed = True
        except BaseException as error:
            failure = error
            if self._forced.is_set():
                self._on_state(self, SessionState.FAULT)
            else:
                self._notify_failure(error)
        finally:
            _close_socket(self._listener)
            try:
                self._journal.close()
            except OSError as error:
                if failure is None:
                    failure = error
                    completed = False
                    if not self._forced.is_set():
                        self._notify_failure(error)
            self._shutdown_connections()
            self._close_connections()
            self._on_finished(self, completed, failure)
            self.done.set()

    def _accept_client(self) -> socket.socket | None:
        self._listener.settimeout(0.25)
        while not self._stop.is_set():
            try:
                client, _address = self._listener.accept()
            except TimeoutError:
                continue
            except OSError:
                if self._stop.is_set():
                    return None
                raise
            _close_socket(self._listener)
            client.settimeout(None)
            with self._socket_lock:
                self._client = client
            return client
        return None

    def _relay(
        self, source: socket.socket, destination: socket.socket, direction: Direction
    ) -> None:
        while not self._stop.is_set():
            try:
                readable, _writable, _exceptional = select.select(
                    [source], [], [], 0.25
                )
            except (OSError, ValueError) as error:
                if self._stop.is_set():
                    return
                self._record_failure(error)
                return
            if not readable or self._stop.is_set():
                continue
            try:
                payload = source.recv(READ_CHUNK_SIZE)
            except OSError as error:
                if self._stop.is_set():
                    return
                self._record_failure(error)
                return
            if not payload:
                _shutdown_socket(destination, socket.SHUT_WR)
                return

            try:
                reference = self._journal.append_data(direction, payload)
            except BaseException as error:
                self._record_failure(error)
                return

            try:
                destination.sendall(payload)
            except OSError as error:
                try:
                    self._journal.append_send_error(reference, _error_code(error))
                except BaseException as journal_error:
                    self._record_failure(journal_error)
                    return
                self._record_failure(error)
                return

            try:
                self._journal.append_send_ok(reference)
            except BaseException as error:
                self._record_failure(error)
                return

    def _record_failure(self, error: BaseException) -> None:
        first_failure = False
        with self._failure_lock:
            if self._failure is None:
                self._failure = error
                first_failure = True
        self._stop.set()
        if not first_failure or self._forced.is_set():
            return
        self._notify_failure(error)
        self._shutdown_connections()

    def _notify_failure(self, error: BaseException) -> None:
        with self._failure_lock:
            if self._fault_notified:
                return
            self._fault_notified = True
        self._on_fault(self, error)

    def _shutdown_connections(self) -> None:
        with self._socket_lock:
            sockets = (self._client, self._upstream)
        for connection in sockets:
            if connection is not None:
                _shutdown_socket(connection, socket.SHUT_RDWR)

    def _close_connections(self) -> None:
        with self._socket_lock:
            sockets = (self._client, self._upstream)
            self._client = None
            self._upstream = None
        for connection in sockets:
            if connection is not None:
                _close_socket(connection)

    def _seal(self, reason: str) -> None:
        summary = self._journal.summary()
        if summary.pending_results:
            raise SessionError("cannot seal a journal with unknown send results")
        self._journal.close()
        complete_path = self.registration.session_path / "complete.json"
        if complete_path.exists():
            raise SessionError("complete.json already exists")
        atomic_write_json(
            complete_path,
            {
                "format_version": FORMAT_VERSION,
                "session_id": self.registration.session_id,
                "closed_at_utc": utc_now_text(),
                "end_reason": reason,
                "final_sequence": summary.final_sequence,
                "final_hash": summary.final_hash,
                "observed_bytes": summary.observed_bytes,
                "sent_success_bytes": summary.sent_success_bytes,
            },
        )


def _validate_port(port: int) -> None:
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65_535:
        raise ValueError("upstream_port must be an integer between 1 and 65535")


def _error_code(error: OSError) -> int:
    code = error.errno
    if code is None or code == 0:
        return -1
    if -(2**31) <= code < 2**31:
        return code
    return errno.EIO


def _shutdown_socket(connection: socket.socket, how: int) -> None:
    try:
        connection.shutdown(how)
    except OSError:
        pass


def _close_socket(connection: socket.socket) -> None:
    try:
        connection.close()
    except OSError:
        pass
