from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from tracerelay.config import (
    FORMAT_VERSION,
    JOURNAL_LIMIT_BYTES,
    SESSION_ADMISSION_RESERVE_BYTES,
    atomic_write_json,
    utc_now_text,
)
from tracerelay.journal import (
    JOURNAL_HEADER,
    JOURNAL_RECORD_OVERHEAD,
    DataReference,
    Direction,
    JournalLimitExceeded,
    JournalSummary,
    JournalWriter,
)
from tracerelay.verify import (
    INVALID,
    VALID_COMPLETE,
    VALID_INCOMPLETE,
    verify_session,
)


def test_complete_journal_is_reconstructed_and_verified(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    first = journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"request")
    journal.append_send_ok(first)
    second = journal.append_data(Direction.UPSTREAM_TO_CLIENT, b"response")
    journal.append_send_ok(second)
    summary = journal.summary()
    journal.close()
    _write_completion(session_dir, summary)

    result = verify_session(session_dir)

    assert result.status == VALID_COMPLETE
    assert result.record_count == 4
    assert result.observed_bytes == {
        "client_to_upstream": 7,
        "upstream_to_client": 8,
    }
    assert result.sent_success_bytes == result.observed_bytes
    assert result.sent_error_bytes == {
        "client_to_upstream": 0,
        "upstream_to_client": 0,
    }
    assert result.unknown_bytes == result.sent_error_bytes
    assert result.final_hash == summary.final_hash


def test_missing_send_result_is_valid_incomplete(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"written-before-send")
    journal.close()

    result = verify_session(session_dir)

    assert result.status == VALID_INCOMPLETE
    assert result.record_count == 1
    assert "unknown" in (result.problem or "")
    assert result.unknown_bytes["client_to_upstream"] == len(b"written-before-send")


def test_journal_limit_reserves_the_terminal_record_before_accepting_data(
    tmp_path: Path,
) -> None:
    payload = b"at-the-boundary"
    exact_limit = (2 * JOURNAL_RECORD_OVERHEAD) + len(payload)
    journal_path = tmp_path / "journal.trr"
    journal = JournalWriter(journal_path, max_bytes=exact_limit)

    reference = journal.append_data(Direction.CLIENT_TO_UPSTREAM, payload)
    size_after_data = journal_path.stat().st_size
    with pytest.raises(JournalLimitExceeded, match="journal limit"):
        journal.append_data(Direction.UPSTREAM_TO_CLIENT, b"x")

    assert journal_path.stat().st_size == size_after_data
    journal.append_send_ok(reference)
    journal.close()
    assert journal_path.stat().st_size == exact_limit


def test_data_one_byte_over_limit_is_rejected_without_writing_a_partial_record(
    tmp_path: Path,
) -> None:
    payload = b"x"
    required = (2 * JOURNAL_RECORD_OVERHEAD) + len(payload)
    journal = JournalWriter(tmp_path / "journal.trr", max_bytes=required - 1)

    with pytest.raises(JournalLimitExceeded, match="journal limit"):
        journal.append_data(Direction.CLIENT_TO_UPSTREAM, payload)

    assert journal.path.stat().st_size == 0
    journal.close()


def test_concurrent_data_writes_cannot_oversubscribe_result_reservations(
    tmp_path: Path,
) -> None:
    payload = b"one-slot"
    exact_limit = (2 * JOURNAL_RECORD_OVERHEAD) + len(payload)
    journal = JournalWriter(tmp_path / "journal.trr", max_bytes=exact_limit)
    barrier = threading.Barrier(3)
    references: list[DataReference] = []
    errors: list[BaseException] = []

    def append(direction: Direction) -> None:
        barrier.wait()
        try:
            references.append(journal.append_data(direction, payload))
        except BaseException as error:
            errors.append(error)

    workers = [
        threading.Thread(target=append, args=(direction,), daemon=True)
        for direction in Direction
    ]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=2.0)

    assert all(not worker.is_alive() for worker in workers)
    assert len(references) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], JournalLimitExceeded)
    journal.append_send_ok(references[0])
    journal.close()
    assert journal.path.stat().st_size == exact_limit


@pytest.mark.parametrize(
    "invalid_limit", [True, 0, -1, 1.0, JOURNAL_LIMIT_BYTES + 1]
)
def test_journal_limit_requires_a_positive_integer(
    tmp_path: Path, invalid_limit: object
) -> None:
    with pytest.raises(ValueError, match="max_bytes"):
        JournalWriter(tmp_path / f"{invalid_limit!s}.trr", max_bytes=invalid_limit)  # type: ignore[arg-type]


def test_truncated_tail_preserves_valid_prefix(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal_path = session_dir / "journal.trr"
    journal = JournalWriter(journal_path)
    reference = journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"payload")
    journal.append_send_ok(reference)
    journal.close()
    data = journal_path.read_bytes()
    journal_path.write_bytes(data[:-7])

    result = verify_session(session_dir)

    assert result.status == VALID_INCOMPLETE
    assert result.record_count == 1
    assert result.problem_offset is not None
    assert result.problem_path == "journal.trr"
    assert "unknown" in (result.problem or "")


def test_middle_payload_tampering_is_invalid(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal_path = session_dir / "journal.trr"
    journal = JournalWriter(journal_path)
    reference = journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"payload")
    journal.append_send_ok(reference)
    journal.close()
    data = bytearray(journal_path.read_bytes())
    data[JOURNAL_HEADER.size] ^= 0x01
    journal_path.write_bytes(data)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem == "record hash mismatch"


def test_forged_completion_marker_is_invalid(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    reference = journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"payload")
    journal.append_send_ok(reference)
    summary = journal.summary()
    journal.close()
    _write_completion(session_dir, summary)
    complete_path = session_dir / "complete.json"
    complete = json.loads(complete_path.read_text(encoding="utf-8"))
    complete["final_hash"] = "00" * 32
    atomic_write_json(complete_path, complete)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert "final_hash mismatch" in (result.problem or "")


def test_completion_after_send_error_is_invalid(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    reference = journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"payload")
    journal.append_send_error(reference, 10054)
    summary = journal.summary()
    journal.close()
    _write_completion(session_dir, summary)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert "failed send" in (result.problem or "")
    assert result.sent_error_bytes["client_to_upstream"] == len(b"payload")


def test_completion_rejects_non_integer_number_types(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    summary = journal.summary()
    journal.close()
    _write_completion(session_dir, summary)
    complete_path = session_dir / "complete.json"
    complete = json.loads(complete_path.read_text(encoding="utf-8"))
    complete["final_sequence"] = 0.0
    atomic_write_json(complete_path, complete)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert "final_sequence must be an integer" in (result.problem or "")
    assert result.problem_path == "complete.json"


def test_session_metadata_requires_utc_uuid_and_effective_limits(tmp_path: Path) -> None:
    session_dir = _new_session(tmp_path)
    session_path = session_dir / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["session_id"] = "not-a-session-id"
    atomic_write_json(session_path, session)
    (session_dir / "journal.trr").write_bytes(b"")

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem_path == "session.json"
    assert "UTC timestamp and UUID" in (result.problem or "")


def test_verifier_rejects_a_journal_larger_than_its_declared_limit(
    tmp_path: Path,
) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    reference = journal.append_data(Direction.CLIENT_TO_UPSTREAM, b"payload")
    journal.append_send_ok(reference)
    journal.close()
    session_path = session_dir / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["limits"]["journal_limit_bytes"] = 1
    session["limits"]["admission_required_free_bytes"] = 1
    atomic_write_json(session_path, session)

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem_path == "journal.trr"
    assert "exceeds session limit" in (result.problem or "")


def test_verifier_rejects_admission_threshold_above_the_session_limit_reserve(
    tmp_path: Path,
) -> None:
    session_dir = _new_session(tmp_path)
    session_path = session_dir / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["limits"]["journal_limit_bytes"] = 1_024
    session["limits"]["admission_required_free_bytes"] = (
        1_024 + SESSION_ADMISSION_RESERVE_BYTES + 1
    )
    atomic_write_json(session_path, session)
    (session_dir / "journal.trr").write_bytes(b"")

    result = verify_session(session_dir)

    assert result.status == INVALID
    assert result.problem_path == "session.json"
    assert "admission_required_free_bytes" in (result.problem or "")


def test_concurrent_directions_keep_global_sequence_and_direction_offsets(
    tmp_path: Path,
) -> None:
    session_dir = _new_session(tmp_path)
    journal = JournalWriter(session_dir / "journal.trr")
    barrier = threading.Barrier(3)
    errors: list[BaseException] = []
    payloads = {
        Direction.CLIENT_TO_UPSTREAM: [bytes([index]) * (257 + index) for index in range(32)],
        Direction.UPSTREAM_TO_CLIENT: [
            bytes([255 - index]) * (193 + index) for index in range(32)
        ],
    }

    def write_direction(direction: Direction) -> None:
        try:
            barrier.wait()
            for payload in payloads[direction]:
                reference = journal.append_data(direction, payload)
                journal.append_send_ok(reference)
        except BaseException as error:
            errors.append(error)

    workers = [
        threading.Thread(target=write_direction, args=(direction,), daemon=True)
        for direction in Direction
    ]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=5.0)

    assert all(not worker.is_alive() for worker in workers)
    assert errors == []
    summary = journal.summary()
    journal.close()
    _write_completion(session_dir, summary)

    result = verify_session(session_dir)

    assert result.status == VALID_COMPLETE
    assert result.record_count == 128
    assert result.observed_bytes == {
        direction.label: sum(map(len, payloads[direction])) for direction in Direction
    }
    assert result.sent_success_bytes == result.observed_bytes


def _new_session(tmp_path: Path) -> Path:
    session_id = "20260801T000000.000000Z_00000000000000000000000000000000"
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    atomic_write_json(
        session_dir / "session.json",
        {
            "format_version": FORMAT_VERSION,
            "session_id": session_id,
            "created_at_utc": utc_now_text(),
            "proxy_host": "127.0.0.1",
            "proxy_port": 40_001,
            "upstream_host": "127.0.0.1",
            "upstream_port": 40_002,
            "limits": {
                "read_chunk_size": 65_536,
                "control_message_limit": 65_536,
                "journal_limit_bytes": JOURNAL_LIMIT_BYTES,
                "admission_required_free_bytes": (
                    JOURNAL_LIMIT_BYTES + SESSION_ADMISSION_RESERVE_BYTES
                ),
                "upstream_connect_timeout_seconds": 10.0,
                "single_client": False,
            },
        },
    )
    return session_dir


def _write_completion(session_dir: Path, summary: JournalSummary) -> None:
    atomic_write_json(
        session_dir / "complete.json",
        {
            "format_version": FORMAT_VERSION,
            "session_id": json.loads(
                (session_dir / "session.json").read_text(encoding="utf-8")
            )["session_id"],
            "closed_at_utc": utc_now_text(),
            "end_reason": "test",
            "final_sequence": summary.final_sequence,
            "final_hash": summary.final_hash,
            "observed_bytes": summary.observed_bytes,
            "sent_success_bytes": summary.sent_success_bytes,
        },
    )
