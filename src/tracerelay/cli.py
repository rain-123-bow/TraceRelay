"""Command-line client for the TraceRelay M1 foreground Service."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .control import ControlClient, ControlProtocolError
from .verify import INVALID, verify_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracerelay")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="show foreground Service and session state")
    register = commands.add_parser("register", help="register one local upstream")
    register.add_argument("--upstream-port", required=True, type=int)
    commands.add_parser("close", help="close the waiting or active session")
    verify = commands.add_parser("verify", help="verify one session directory read-only")
    verify.add_argument("path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "verify":
        result = verify_session(arguments.path)
        _write_json(result.as_dict())
        return 1 if result.status == INVALID else 0

    request: dict[str, Any] = {"command": arguments.command}
    if arguments.command == "register":
        request["upstream_port"] = arguments.upstream_port
    try:
        response = ControlClient().request(request)
    except (ControlProtocolError, OSError, TimeoutError) as error:
        _write_json(
            {
                "ok": False,
                "command": arguments.command,
                "state": "UNAVAILABLE",
                "error": str(error),
            },
            stream=sys.stderr,
        )
        return 1
    _write_json(response)
    return 0 if response.get("ok") is True else 1


def _write_json(value: dict[str, Any], *, stream: Any | None = None) -> None:
    destination = sys.stdout if stream is None else stream
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), file=destination)
