from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from tracerelay.verify import INVALID, VALID_COMPLETE, VALID_INCOMPLETE, verify_session


HEADER = struct.Struct("<4sHBBQQQQQIi32s")
ZERO_HASH = bytes(32)
SESSION_ID = "20260801T000000.000000Z_12345678123446789abcdef012345678"


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
            "format_version": 1,
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

    assert HEADER.size == 88
    assert len(first) == 120 + len(b"\x00request\xff")
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
    assert result.problem == "send result does not match its DATA direction or offset"
    assert result.problem_offset == len(data)


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
    assert result.problem == "direction stream offset is not contiguous"
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
            "format_version": 1,
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
            "format_version": 1,
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
) -> tuple[bytes, bytes]:
    header = HEADER.pack(
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
            "format_version": 1,
            "session_id": SESSION_ID,
            "created_at_utc": "2026-08-01T00:00:00.000000Z",
            "proxy_host": "127.0.0.1",
            "proxy_port": 40_001,
            "upstream_host": "127.0.0.1",
            "upstream_port": 40_002,
            "limits": {
                "read_chunk_size": 65_536,
                "control_message_limit": 65_536,
                "upstream_connect_timeout_seconds": 10.0,
                "single_client": True,
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
