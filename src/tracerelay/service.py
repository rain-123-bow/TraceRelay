"""Foreground TraceRelay Service used by the M1 implementation milestone."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any

from .config import CONTROL_HOST, CONTROL_PORT, RuntimePaths
from .control import ControlServer
from .session import SessionError, SessionManager


class TraceRelayService:
    """Combine the local control endpoint with the single-session relay."""

    def __init__(
        self,
        *,
        paths: RuntimePaths | None = None,
        control_host: str = CONTROL_HOST,
        control_port: int = CONTROL_PORT,
    ) -> None:
        self.paths = paths or RuntimePaths.default()
        self.manager = SessionManager(self.paths)
        self.control = ControlServer(
            self.handle_request,
            host=control_host,
            port=control_port,
        )
        self._close_lock = threading.Lock()
        self._closed = False

    @property
    def control_host(self) -> str:
        return self.control.host

    @property
    def control_port(self) -> int:
        return self.control.port

    def serve_forever(self) -> None:
        self.control.serve_forever()

    def shutdown(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            self.control.close()
            self.manager.shutdown()

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        command = request.get("command")
        if not isinstance(command, str) or not command:
            return self._error(None, "command must be a non-empty string")

        try:
            if command == "status":
                _require_fields(request, {"command"})
                return self._success(command, self.manager.status())
            if command == "register":
                _require_fields(request, {"command", "upstream_port"})
                registration = self.manager.register(request.get("upstream_port"))
                payload = registration.as_dict()
                payload["state"] = self.manager.status()["state"]
                return self._success(command, payload)
            if command == "close":
                _require_fields(request, {"command"})
                return self._success(command, self.manager.close())
            return self._error(command, f"unsupported command: {command}")
        except (SessionError, OSError, ValueError) as error:
            return self._error(command, str(error))

    def _success(self, command: str, payload: dict[str, object]) -> dict[str, Any]:
        response: dict[str, Any] = {"ok": True, "command": command}
        response.update(payload)
        response.setdefault("state", self.manager.status()["state"])
        return response

    def _error(self, command: str | None, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "command": command,
            "state": self.manager.status()["state"],
            "error": message,
        }


def main() -> int:
    service: TraceRelayService | None = None
    try:
        service = TraceRelayService()
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "foreground",
                    "state": "IDLE",
                    "control_host": service.control_host,
                    "control_port": service.control_port,
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        service.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except OSError as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1
    finally:
        if service is not None:
            service.shutdown()


def _require_fields(request: dict[str, Any], allowed: set[str]) -> None:
    unknown = set(request) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unexpected request field(s): {names}")


if __name__ == "__main__":
    raise SystemExit(main())
