"""Read-only, byte-level verifier for TraceRelay v1 session evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from .config import (
    CONTROL_HOST,
    CONTROL_MESSAGE_LIMIT,
    FORMAT_VERSION,
    READ_CHUNK_SIZE,
    UPSTREAM_CONNECT_TIMEOUT_SECONDS,
)
from .journal import (
    HASH_SIZE,
    JOURNAL_HEADER,
    JOURNAL_MAGIC,
    ZERO_HASH,
    Direction,
    RecordType,
)


VALID_COMPLETE = "VALID_COMPLETE"
VALID_INCOMPLETE = "VALID_INCOMPLETE"
INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: str
    record_count: int
    observed_bytes: dict[str, int]
    sent_success_bytes: dict[str, int]
    final_hash: str
    sent_error_bytes: dict[str, int] = field(default_factory=dict)
    unknown_bytes: dict[str, int] = field(default_factory=dict)
    problem: str | None = None
    problem_offset: int | None = None
    problem_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "record_count": self.record_count,
            "observed_bytes": dict(self.observed_bytes),
            "sent_success_bytes": dict(self.sent_success_bytes),
            "sent_error_bytes": dict(self.sent_error_bytes),
            "unknown_bytes": dict(self.unknown_bytes),
            "final_hash": self.final_hash,
        }
        if self.problem is not None:
            result["problem"] = self.problem
        if self.problem_offset is not None:
            result["problem_offset"] = self.problem_offset
        if self.problem_path is not None:
            result["problem_path"] = self.problem_path
        return result


@dataclass(slots=True)
class _DataState:
    direction: Direction
    stream_offset: int
    length: int
    terminal: RecordType | None = None


def verify_session(session_directory: Path) -> VerificationResult:
    """Verify one session directory without modifying any evidence file."""

    session_dir = Path(session_directory)
    observed = {direction.label: 0 for direction in Direction}
    sent_success = {direction.label: 0 for direction in Direction}
    empty_hash = ZERO_HASH.hex()

    try:
        session = _read_json_object(session_dir / "session.json")
        _validate_session_metadata(session)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return VerificationResult(
            INVALID,
            0,
            observed,
            sent_success,
            empty_hash,
            sent_error_bytes={direction.label: 0 for direction in Direction},
            unknown_bytes={direction.label: 0 for direction in Direction},
            problem=f"invalid session.json: {error}",
            problem_path="session.json",
        )

    journal_path = session_dir / "journal.trr"
    try:
        stream = journal_path.open("rb")
    except OSError as error:
        return VerificationResult(
            INVALID,
            0,
            observed,
            sent_success,
            empty_hash,
            sent_error_bytes={direction.label: 0 for direction in Direction},
            unknown_bytes={direction.label: 0 for direction in Direction},
            problem=f"cannot open journal.trr: {error}",
            problem_path="journal.trr",
        )

    expected_sequence = 1
    previous_hash = ZERO_HASH
    records: dict[int, _DataState] = {}
    offset = 0
    tail_problem: str | None = None
    tail_offset: int | None = None

    with stream:
        while True:
            record_offset = offset
            header = stream.read(JOURNAL_HEADER.size)
            if not header:
                break
            if len(header) != JOURNAL_HEADER.size:
                tail_problem = "truncated record header"
                tail_offset = record_offset
                break
            offset += len(header)
            try:
                (
                    magic,
                    version,
                    record_type_value,
                    direction_value,
                    sequence,
                    _utc_ns,
                    _monotonic_ns,
                    related_sequence,
                    stream_offset,
                    payload_length,
                    result_code,
                    recorded_previous_hash,
                ) = JOURNAL_HEADER.unpack(header)
                record_type = RecordType(record_type_value)
                direction = Direction(direction_value)
            except (ValueError, TypeError) as error:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    f"invalid record header: {error}",
                    record_offset,
                    records=records,
                )

            if magic != JOURNAL_MAGIC or version != FORMAT_VERSION:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    "journal magic or version mismatch",
                    record_offset,
                    records=records,
                )
            if sequence != expected_sequence:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    "non-contiguous journal sequence",
                    record_offset,
                    records=records,
                )
            if recorded_previous_hash != previous_hash:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    "previous hash mismatch",
                    record_offset,
                    records=records,
                )
            if payload_length > READ_CHUNK_SIZE:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    "payload length exceeds v1 read block limit",
                    record_offset,
                    records=records,
                )

            payload = stream.read(payload_length)
            current_hash = stream.read(HASH_SIZE)
            offset += len(payload) + len(current_hash)
            if len(payload) != payload_length or len(current_hash) != HASH_SIZE:
                tail_problem = "truncated record payload or hash"
                tail_offset = record_offset
                break
            expected_hash = hashlib.sha256(header + payload).digest()
            if current_hash != expected_hash:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    "record hash mismatch",
                    record_offset,
                    records=records,
                )

            problem = _accept_record(
                record_type=record_type,
                direction=direction,
                sequence=sequence,
                related_sequence=related_sequence,
                stream_offset=stream_offset,
                payload=payload,
                result_code=result_code,
                records=records,
                observed=observed,
                sent_success=sent_success,
            )
            if problem is not None:
                return _invalid(
                    expected_sequence - 1,
                    observed,
                    sent_success,
                    previous_hash,
                    problem,
                    record_offset,
                    records=records,
                )

            previous_hash = current_hash
            expected_sequence += 1

    record_count = expected_sequence - 1
    sent_error, unknown = _terminal_byte_counts(records)
    complete_path = session_dir / "complete.json"
    if tail_problem is not None:
        if complete_path.exists():
            return _invalid(
                record_count,
                observed,
                sent_success,
                previous_hash,
                "complete.json exists for a truncated journal",
                tail_offset,
                records=records,
            )
        pending = sum(state.terminal is None for state in records.values())
        if pending:
            tail_problem = f"{tail_problem}; {pending} send result(s) are unknown"
        return VerificationResult(
            VALID_INCOMPLETE,
            record_count,
            observed,
            sent_success,
            previous_hash.hex(),
            sent_error_bytes=sent_error,
            unknown_bytes=unknown,
            problem=tail_problem,
            problem_offset=tail_offset,
            problem_path="journal.trr",
        )

    if not complete_path.exists():
        pending = sum(state.terminal is None for state in records.values())
        problem = "completion marker is absent"
        if pending:
            problem = f"completion marker is absent; {pending} send result(s) are unknown"
        return VerificationResult(
            VALID_INCOMPLETE,
            record_count,
            observed,
            sent_success,
            previous_hash.hex(),
            sent_error_bytes=sent_error,
            unknown_bytes=unknown,
            problem=problem,
            problem_path="complete.json",
        )

    try:
        complete = _read_json_object(complete_path)
        _validate_completion(
            complete=complete,
            session=session,
            record_count=record_count,
            final_hash=previous_hash.hex(),
            observed=observed,
            sent_success=sent_success,
            has_unknown=any(unknown.values()),
            has_send_error=any(sent_error.values()),
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _invalid(
            record_count,
            observed,
            sent_success,
            previous_hash,
            f"invalid complete.json: {error}",
            None,
            "complete.json",
            records=records,
        )

    return VerificationResult(
        VALID_COMPLETE,
        record_count,
        observed,
        sent_success,
        previous_hash.hex(),
        sent_error_bytes=sent_error,
        unknown_bytes=unknown,
    )


def _accept_record(
    *,
    record_type: RecordType,
    direction: Direction,
    sequence: int,
    related_sequence: int,
    stream_offset: int,
    payload: bytes,
    result_code: int,
    records: dict[int, _DataState],
    observed: dict[str, int],
    sent_success: dict[str, int],
) -> str | None:
    label = direction.label
    if record_type is RecordType.DATA:
        if not payload:
            return "DATA payload is empty"
        if related_sequence != 0 or result_code != 0:
            return "DATA contains result-only fields"
        if stream_offset != observed[label]:
            return "direction stream offset is not contiguous"
        observed[label] += len(payload)
        records[sequence] = _DataState(direction, stream_offset, len(payload))
        return None

    if payload:
        return "send result contains a payload"
    data = records.get(related_sequence)
    if data is None:
        return "send result references missing DATA"
    if data.terminal is not None:
        return "DATA has more than one terminal send result"
    if data.direction is not direction or data.stream_offset != stream_offset:
        return "send result does not match its DATA direction or offset"
    if record_type is RecordType.SEND_OK:
        if result_code != 0:
            return "SEND_OK has a non-zero result code"
        sent_success[label] += data.length
    elif result_code == 0:
        return "SEND_ERROR has a zero result code"
    data.terminal = record_type
    return None


def _read_json_object(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 64 * 1024:
        raise ValueError("metadata file exceeds 64 KiB")
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream, parse_constant=_reject_json_constant)
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value


def _validate_session_metadata(session: dict[str, Any]) -> None:
    if type(session.get("format_version")) is not int:
        raise ValueError("format_version must be an integer")
    if session["format_version"] != FORMAT_VERSION:
        raise ValueError("unsupported format_version")
    session_id = session.get("session_id")
    if not isinstance(session_id, str):
        raise ValueError("session_id must be a string")
    _validate_session_id(session_id)
    _validate_utc_text(session.get("created_at_utc"), "created_at_utc")
    for prefix in ("proxy", "upstream"):
        if session.get(f"{prefix}_host") != CONTROL_HOST:
            raise ValueError(f"{prefix}_host must be {CONTROL_HOST}")
        port = session.get(f"{prefix}_port")
        if type(port) is not int or not 1 <= port <= 65_535:
            raise ValueError(f"{prefix}_port is invalid")
    limits = session.get("limits")
    if not isinstance(limits, dict):
        raise ValueError("limits must be an object")
    if type(limits.get("read_chunk_size")) is not int or limits["read_chunk_size"] != READ_CHUNK_SIZE:
        raise ValueError("limits.read_chunk_size is invalid")
    if (
        type(limits.get("control_message_limit")) is not int
        or limits["control_message_limit"] != CONTROL_MESSAGE_LIMIT
    ):
        raise ValueError("limits.control_message_limit is invalid")
    upstream_timeout = limits.get("upstream_connect_timeout_seconds")
    if (
        isinstance(upstream_timeout, bool)
        or not isinstance(upstream_timeout, (int, float))
        or float(upstream_timeout) != UPSTREAM_CONNECT_TIMEOUT_SECONDS
    ):
        raise ValueError("limits.upstream_connect_timeout_seconds is invalid")
    if limits.get("single_client") is not True:
        raise ValueError("limits.single_client must be true")


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant is not allowed: {value}")


def _validate_completion(
    *,
    complete: dict[str, Any],
    session: dict[str, Any],
    record_count: int,
    final_hash: str,
    observed: dict[str, int],
    sent_success: dict[str, int],
    has_unknown: bool,
    has_send_error: bool,
) -> None:
    if type(complete.get("format_version")) is not int:
        raise ValueError("format_version must be an integer")
    if complete["format_version"] != FORMAT_VERSION:
        raise ValueError("unsupported format_version")
    if complete.get("session_id") != session["session_id"]:
        raise ValueError("session_id mismatch")
    if type(complete.get("final_sequence")) is not int:
        raise ValueError("final_sequence must be an integer")
    if complete["final_sequence"] != record_count:
        raise ValueError("final_sequence mismatch")
    if not isinstance(complete.get("final_hash"), str):
        raise ValueError("final_hash must be a string")
    if complete["final_hash"] != final_hash:
        raise ValueError("final_hash mismatch")
    _validate_counts(complete.get("observed_bytes"), observed, "observed_bytes")
    _validate_counts(
        complete.get("sent_success_bytes"), sent_success, "sent_success_bytes"
    )
    _validate_utc_text(complete.get("closed_at_utc"), "closed_at_utc")
    if not isinstance(complete.get("end_reason"), str) or not complete["end_reason"]:
        raise ValueError("end_reason is invalid")
    if has_unknown:
        raise ValueError("completion marker exists with unknown send results")
    if has_send_error:
        raise ValueError("completion marker exists after a failed send")


def _validate_counts(value: object, expected: dict[str, int], field: str) -> None:
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{field} has invalid direction keys")
    if any(type(count) is not int or count < 0 for count in value.values()):
        raise ValueError(f"{field} values must be non-negative integers")
    if value != expected:
        raise ValueError(f"{field} mismatch")


def _terminal_byte_counts(
    records: dict[int, _DataState],
) -> tuple[dict[str, int], dict[str, int]]:
    sent_error = {direction.label: 0 for direction in Direction}
    unknown = {direction.label: 0 for direction in Direction}
    for state in records.values():
        if state.terminal is RecordType.SEND_ERROR:
            sent_error[state.direction.label] += state.length
        elif state.terminal is None:
            unknown[state.direction.label] += state.length
    return sent_error, unknown


def _validate_session_id(value: str) -> None:
    try:
        timestamp, random_part = value.split("_", maxsplit=1)
        datetime.strptime(timestamp, "%Y%m%dT%H%M%S.%fZ")
        if len(random_part) != 32 or UUID(hex=random_part).hex != random_part.lower():
            raise ValueError
    except (ValueError, TypeError) as error:
        raise ValueError("session_id must contain a UTC timestamp and UUID") from error


def _validate_utc_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be a UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field} must be a UTC timestamp") from error


def _invalid(
    record_count: int,
    observed: dict[str, int],
    sent_success: dict[str, int],
    final_hash: bytes,
    problem: str,
    offset: int | None,
    problem_path: str = "journal.trr",
    *,
    records: dict[int, _DataState] | None = None,
) -> VerificationResult:
    sent_error, unknown = _terminal_byte_counts(records or {})
    return VerificationResult(
        INVALID,
        record_count,
        dict(observed),
        dict(sent_success),
        final_hash.hex(),
        sent_error_bytes=sent_error,
        unknown_bytes=unknown,
        problem=problem,
        problem_offset=offset,
        problem_path=problem_path,
    )
