# TraceRelay

TraceRelay is a Windows-local evidence relay. A registered application starts
behind the relay, and the relay preserves traffic and lifecycle evidence for
later independent verification.

## Current implementation status

Milestone M1 is implemented. It provides the smallest foreground runtime:

- one loopback TCP session at a time;
- durable, hash-chained traffic evidence written before forwarding;
- independent read-only session verification;
- `status`, `register`, `close`, and `verify` commands.

Run the foreground Service in one PowerShell terminal:

```powershell
python -m tracerelay.service
```

Use the CLI from another terminal:

```powershell
tracerelay status
tracerelay register --upstream-port 9000
tracerelay close
tracerelay verify <session-directory>
```

Press `Ctrl+C` in the Service terminal to stop it. Detached process management,
`start` / `stop`, heartbeat monitoring, alarms, quotas, and delivery hardening
belong to later milestones and are not implemented. If the M1 foreground
Service enters `FAULT`, stop it with `Ctrl+C` and start a fresh process.

Current design:

- `docs/v1/REQUIREMENTS.md`
- `docs/v1/IMPLEMENTATION_PLAN.md`
- `docs/v1/DESIGN_REVIEW.md`

The implementation intentionally stops at the M1 boundary described in the
plan.

## Supported target

- Windows 11 x64
- CPython 3.13
- PowerShell 7.x Core for repository gates
- no third-party runtime dependency

The first version supports one trusted local user and one loopback TCP session.
It is an evidence aid, not a hostile-user security or non-repudiation product.
