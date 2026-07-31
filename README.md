# TraceRelay

TraceRelay is a Windows-local evidence relay. A registered application starts
behind the relay, and the relay preserves traffic and lifecycle evidence for
later independent verification.

## Current implementation status

The runtime is not implemented yet. The former full-assurance design has been
retired because it exceeded the needs of the first usable version.

Current design:

- `docs/v1/REQUIREMENTS.md`
- `docs/v1/IMPLEMENTATION_PLAN.md`
- `docs/v1/DESIGN_REVIEW.md`

The repository baseline has been reset to the minimal v1 design. Runtime
implementation starts at milestone M1; no service, proxy, recorder, or CLI is
available yet.

## Supported target

- Windows 11 x64
- CPython 3.13
- PowerShell 7.x Core for repository gates
- no third-party runtime dependency

The first version supports one trusted local user and one loopback TCP session.
It is an evidence aid, not a hostile-user security or non-repudiation product.
