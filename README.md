# TraceRelay

TraceRelay is a Windows-local evidence relay. A registered application starts
behind the relay, and the relay preserves traffic and lifecycle evidence for
later independent verification.

## Current implementation status

Milestone M2 is implemented. It provides the fault-closed local runtime:

- one loopback TCP session at a time;
- durable, hash-chained traffic evidence written before forwarding;
- independent read-only session verification;
- a detached Supervisor and managed Relay Service with bidirectional heartbeats;
- persistent alarms for process, monitoring, upstream, and journal failures;
- `start`, `status`, `register`, `close`, `stop`, and `verify` commands.

Start the detached runtime:

```powershell
tracerelay start
```

Use the CLI from any PowerShell terminal:

```powershell
tracerelay status
tracerelay register --upstream-port 9000
tracerelay close
tracerelay stop
tracerelay verify <session-directory>
```

`start` is idempotent for an already-running TraceRelay instance. `stop` closes
the current session before both managed processes exit. Fatal runtime failures
write independent JSON files under `%LOCALAPPDATA%\TraceRelay\alarms`; `status`
returns only the latest alarm's public summary.

The foreground Service entry point remains available for focused development:

```powershell
python -m tracerelay.service
```

Current design:

- `docs/v1/REQUIREMENTS.md`
- `docs/v1/IMPLEMENTATION_PLAN.md`
- `docs/v1/DESIGN_REVIEW.md`

The implementation intentionally stops at the M2 boundary described in the
plan. M3 quotas, free-space admission checks, wheel delivery, and cleanup are
not implemented yet.

## Supported target

- Windows 11 x64
- CPython 3.13
- PowerShell 7.x Core for repository gates
- no third-party runtime dependency

The first version supports one trusted local user and one loopback TCP session.
It is an evidence aid, not a hostile-user security or non-repudiation product.
