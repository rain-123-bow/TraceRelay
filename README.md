# TraceRelay

TraceRelay is a Windows-local evidence relay. A registered application starts
behind the relay, and the relay preserves traffic and lifecycle evidence for
later independent verification.

## Current implementation status

`1.0.0.dev0` contains only the TR-I00 repository and immutable-contract
bootstrap. It does not yet expose a service, proxy, command-line interface, or
evidence recorder. Runtime behavior starts in later phases of the confirmed
implementation plan.

## Supported target

- Windows 11 x64
- CPython 3.13
- PowerShell 7.x Core for repository gates
- no third-party runtime dependency

The package includes byte-exact copies of the confirmed requirement assets and
the six runtime schemas. `tests/contract` independently checks their hashes,
schema-set identity, dependency boundary, source ownership, and import rules.

