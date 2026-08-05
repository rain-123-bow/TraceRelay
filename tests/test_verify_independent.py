from __future__ import annotations

import hashlib
import json
import random
import socket
import struct
import threading
import time
from pathlib import Path

from tracerelay.config import RuntimePaths
from tracerelay.session import SessionManager, SessionState
from tracerelay.verify import INVALID, VALID_COMPLETE, VALID_INCOMPLETE, verify_session


HEADER = struct.Struct("<4sHBBQQQQQQIi32s")
LEGACY_HEADER = struct.Struct("<4sHBBQQQQQIi32s")
ZERO_HASH = bytes(32)
SESSION_ID = "20260801T000000.000000Z_12345678123446789abcdef012345678"


def test_independent_parser_rebuilds_real_relay_bytes_by_direction(
    tmp_path: Path,
) -> None:
    generator = random.Random(20260802)
    request = generator.randbytes(81_337)
    response = generator.randbytes(73_119)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
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
                    received.append(_receive_all(connection))
                    connection.sendall(response)
                    connection.shutdown(socket.SHUT_WR)
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
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        reply = _receive_all(client)

    upstream_thread.join(timeout=5.0)
    assert not upstream_thread.is_alive()
    assert errors == []
    assert received == [request]
    assert reply == response
    _wait_for_state(manager, SessionState.WAITING)
    manager.close(timeout=2.0)

    rebuilt = _independently_rebuild_streams(
        registration.session_path / "journal.trr"
    )
    assert rebuilt == {1: request, 2: response}


def test_independent_known_bytes_verify_as_complete(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    first, first_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"\x00request\xff",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    second, second_hash = _record(
        sequence=2,
        record_type=1,
        direction=2,
        related_sequence=0,
        stream_offset=0,
        payload=b"response",
        result_code=0,
        previous_hash=first_hash,
    )
    third, third_hash = _record(
        sequence=3,
        record_type=2,
        direction=1,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=second_hash,
    )
    fourth, final_hash = _record(
        sequence=4,
        record_type=2,
        direction=2,
        related_sequence=2,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=third_hash,
    )
    (session_dir / "journal.trr").write_bytes(first + second + third + fourth)
    _write_json(
        session_dir / "complete.json",
        {
            "format_version": 2,
            "session_id": SESSION_ID,
            "closed_at_utc": "2026-08-01T00:00:01.000000Z",
            "end_reason": "test",
            "final_sequence": 4,
            "final_hash": final_hash.hex(),
            "observed_bytes": {
                "client_to_upstream": len(b"\x00request\xff"),
                "upstream_to_client": len(b"response"),
            },
            "sent_success_bytes": {
                "client_to_upstream": len(b"\x00request\xff"),
                "upstream_to_client": len(b"response"),
            },
        },
    )

    result = verify_session(session_dir)

    assert HEADER.size == 96
    assert len(first) == 128 + len(b"\x00request\xff")
    assert result.status == VALID_COMPLETE
    assert result.record_count == 4
    assert result.final_hash == final_hash.hex()


def test_independent_semantic_error_hits_direction_check(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"payload",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    wrong_result, _result_hash = _record(
        sequence=2,
        record_type=2,
        direction=2,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=data_hash,
    )
    (session_dir / "journal.trr").write_bytes(data + wrong_result)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == (
        "send result does not match its DATA connection, direction, or offset"
    )
    assert result.problem_offset == len(data)


def test_send_result_cannot_change_its_data_connection_id(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"payload",
        result_code=0,
        previous_hash=ZERO_HASH,
        connection_id=1,
    )
    wrong_result, _final_hash = _record(
        sequence=2,
        record_type=2,
        direction=1,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=data_hash,
        connection_id=2,
    )
    (session_dir / "journal.trr").write_bytes(data + wrong_result)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == (
        "send result does not match its DATA connection, direction, or offset"
    )


def test_zero_connection_id_is_invalid(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, _data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"payload",
        result_code=0,
        previous_hash=ZERO_HASH,
        connection_id=0,
    )
    (session_dir / "journal.trr").write_bytes(data)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == "connection_id is invalid"


def test_legacy_v1_evidence_remains_verifiable(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    session = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
    session["format_version"] = 1
    session["limits"]["single_client"] = True
    _write_json(session_dir / "session.json", session)
    data, data_hash = _legacy_record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"legacy",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    send_ok, final_hash = _legacy_record(
        sequence=2,
        record_type=2,
        direction=1,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=data_hash,
    )
    (session_dir / "journal.trr").write_bytes(data + send_ok)
    _write_json(
        session_dir / "complete.json",
        {
            "format_version": 1,
            "session_id": SESSION_ID,
            "closed_at_utc": "2026-08-01T00:00:01.000000Z",
            "end_reason": "legacy-test",
            "final_sequence": 2,
            "final_hash": final_hash.hex(),
            "observed_bytes": {
                "client_to_upstream": len(b"legacy"),
                "upstream_to_client": 0,
            },
            "sent_success_bytes": {
                "client_to_upstream": len(b"legacy"),
                "upstream_to_client": 0,
            },
        },
    )

    result = verify_session(session_dir)

    assert result.status == VALID_COMPLETE
    assert result.observed_connection_count == 1
    assert result.final_hash == final_hash.hex()


def test_independent_data_without_result_reports_unknown_bytes(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, _data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"unknown",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    (session_dir / "journal.trr").write_bytes(data)

    result = verify_session(session_dir)

    assert result.status == VALID_INCOMPLETE
    assert result.unknown_bytes == {
        "client_to_upstream": len(b"unknown"),
        "upstream_to_client": 0,
    }


def test_independent_duplicate_send_result_is_invalid(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"payload",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    first_result, first_result_hash = _record(
        sequence=2,
        record_type=2,
        direction=1,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=data_hash,
    )
    duplicate_result, _duplicate_hash = _record(
        sequence=3,
        record_type=3,
        direction=1,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=10054,
        previous_hash=first_result_hash,
    )
    (session_dir / "journal.trr").write_bytes(
        data + first_result + duplicate_result
    )

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == "DATA has more than one terminal send result"
    assert result.problem_offset == len(data) + len(first_result)


def test_independent_noncontiguous_direction_offset_is_invalid(
    tmp_path: Path,
) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, _data_hash = _record(
        sequence=1,
        record_type=1,
        direction=2,
        related_sequence=0,
        stream_offset=1,
        payload=b"payload",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    (session_dir / "journal.trr").write_bytes(data)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == "connection direction stream offset is not contiguous"
    assert result.problem_offset == 0


def test_completion_marker_cannot_hide_an_unknown_send_result(
    tmp_path: Path,
) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"unknown",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    (session_dir / "journal.trr").write_bytes(data)
    _write_json(
        session_dir / "complete.json",
        {
            "format_version": 2,
            "session_id": SESSION_ID,
            "closed_at_utc": "2026-08-01T00:00:01.000000Z",
            "end_reason": "forged",
            "final_sequence": 1,
            "final_hash": data_hash.hex(),
            "observed_bytes": {
                "client_to_upstream": len(b"unknown"),
                "upstream_to_client": 0,
            },
            "sent_success_bytes": {
                "client_to_upstream": 0,
                "upstream_to_client": 0,
            },
        },
    )

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert "unknown send results" in (result.problem or "")
    assert result.unknown_bytes["client_to_upstream"] == len(b"unknown")


def test_completion_marker_with_a_truncated_tail_is_invalid(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    data, data_hash = _record(
        sequence=1,
        record_type=1,
        direction=1,
        related_sequence=0,
        stream_offset=0,
        payload=b"payload",
        result_code=0,
        previous_hash=ZERO_HASH,
    )
    result_record, final_hash = _record(
        sequence=2,
        record_type=2,
        direction=1,
        related_sequence=1,
        stream_offset=0,
        payload=b"",
        result_code=0,
        previous_hash=data_hash,
    )
    (session_dir / "journal.trr").write_bytes((data + result_record)[:-5])
    _write_json(
        session_dir / "complete.json",
        {
            "format_version": 2,
            "session_id": SESSION_ID,
            "closed_at_utc": "2026-08-01T00:00:01.000000Z",
            "end_reason": "forged",
            "final_sequence": 2,
            "final_hash": final_hash.hex(),
            "observed_bytes": {
                "client_to_upstream": len(b"payload"),
                "upstream_to_client": 0,
            },
            "sent_success_bytes": {
                "client_to_upstream": len(b"payload"),
                "upstream_to_client": 0,
            },
        },
    )

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == "complete.json exists for a truncated journal"
    assert result.problem_path == "journal.trr"


def test_session_metadata_rejects_nonstandard_json_numbers(tmp_path: Path) -> None:
    session_dir = _write_session_metadata(tmp_path)
    session_path = session_dir / "session.json"
    text = session_path.read_text(encoding="utf-8")
    session_path.write_text(
        text.replace("10.0", "NaN"),
        encoding="utf-8",
        newline="\n",
    )
    (session_dir / "journal.trr").write_bytes(b"")

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem_path == "session.json"
    assert "non-standard JSON constant" in (result.problem or "")


def _record(
    *,
    sequence: int,
    record_type: int,
    direction: int,
    related_sequence: int,
    stream_offset: int,
    payload: bytes,
    result_code: int,
    previous_hash: bytes,
    connection_id: int = 1,
) -> tuple[bytes, bytes]:
    header = HEADER.pack(
        b"TRR1",
        2,
        record_type,
        direction,
        connection_id,
        sequence,
        1_700_000_000_000_000_000 + sequence,
        10_000 + sequence,
        related_sequence,
        stream_offset,
        len(payload),
        result_code,
        previous_hash,
    )
    digest = hashlib.sha256(header + payload).digest()
    return header + payload + digest, digest


def _legacy_record(
    *,
    sequence: int,
    record_type: int,
    direction: int,
    related_sequence: int,
    stream_offset: int,
    payload: bytes,
    result_code: int,
    previous_hash: bytes,
) -> tuple[bytes, bytes]:
    header = LEGACY_HEADER.pack(
        b"TRR1",
        1,
        record_type,
        direction,
        sequence,
        1_700_000_000_000_000_000 + sequence,
        10_000 + sequence,
        related_sequence,
        stream_offset,
        len(payload),
        result_code,
        previous_hash,
    )
    digest = hashlib.sha256(header + payload).digest()
    return header + payload + digest, digest


def _write_session_metadata(tmp_path: Path) -> Path:
    session_dir = tmp_path / SESSION_ID
    session_dir.mkdir()
    _write_json(
        session_dir / "session.json",
        {
            "format_version": 2,
            "session_id": SESSION_ID,
            "created_at_utc": "2026-08-01T00:00:00.000000Z",
            "proxy_host": "127.0.0.1",
            "proxy_port": 40_001,
            "upstream_host": "127.0.0.1",
            "upstream_port": 40_002,
            "limits": {
                "read_chunk_size": 65_536,
                "control_message_limit": 65_536,
                "journal_limit_bytes": 2_147_483_648,
                "admission_required_free_bytes": 2_164_260_864,
                "upstream_connect_timeout_seconds": 10.0,
                "single_client": False,
            },
        },
    )
    return session_dir


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _independently_rebuild_streams(path: Path) -> dict[int, bytes]:
    data = path.read_bytes()
    offset = 0
    expected_sequence = 1
    previous_hash = bytes(32)
    streams = {1: bytearray(), 2: bytearray()}
    while offset < len(data):
        record_offset = offset
        header = data[offset : offset + HEADER.size]
        assert len(header) == HEADER.size
        offset += HEADER.size
        (
            magic,
            version,
            record_type,
            direction,
            connection_id,
            sequence,
            _utc_ns,
            _monotonic_ns,
            related_sequence,
            stream_offset,
            payload_length,
            result_code,
            recorded_previous_hash,
        ) = HEADER.unpack(header)
        payload = data[offset : offset + payload_length]
        offset += payload_length
        current_hash = data[offset : offset + 32]
        offset += 32

        assert magic == b"TRR1"
        assert version == 2
        assert connection_id == 1
        assert direction in streams
        assert sequence == expected_sequence
        assert recorded_previous_hash == previous_hash
        assert len(payload) == payload_length
        assert len(current_hash) == 32
        assert current_hash == hashlib.sha256(header + payload).digest()
        if record_type == 1:
            assert related_sequence == 0
            assert result_code == 0
            assert stream_offset == len(streams[direction])
            streams[direction].extend(payload)
        else:
            assert record_type in {2, 3}
            assert payload == b""
            assert related_sequence < sequence
        previous_hash = current_hash
        expected_sequence += 1
        assert offset > record_offset
    assert offset == len(data)
    return {direction: bytes(payload) for direction, payload in streams.items()}


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
