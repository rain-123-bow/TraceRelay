# TraceRelay v1 M3 validation

Date: 2026-08-02
Platform: Windows 11 x64
Branch: `m3-implementation`

## Environment

| Component | Observed version |
|---|---:|
| CPython | 3.13.14 |
| PowerShell Core | 7.6.4 |
| setuptools | 83.0.0 |
| pytest | 9.1.1 |

`python -m pip check` exited `0` with `No broken requirements found`.

## Automated results

| Command | Exit code | Result |
|---|---:|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | 0 | `98 passed in 55.92s` |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_windows_runtime.py tests/test_windows_wheel.py` | 0 | `8 passed in 47.61s` |
| `git diff --check` | 0 | no whitespace errors |
| TCP exclusive bind probe on `127.0.0.1:43190` | 0 | port free after tests |
| Windows process query | 0 | no TraceRelay Supervisor or Service remained |

## Wheel and CLI delivery smoke

`tests/test_windows_wheel.py` copies the source into a temporary directory,
builds with `--no-index --no-deps --no-build-isolation`, creates a clean venv,
and installs the wheel with `--no-index --no-deps`. It then runs the installed
`tracerelay.exe` outside the source tree.

| Installed command | Expected exit | Observed result |
|---|---:|---|
| `tracerelay start` | 0 | managed runtime started in `IDLE` |
| `tracerelay status` | 0 | managed runtime reported `IDLE` |
| `tracerelay register --upstream-port 9` | 0 | one session entered `WAITING` |
| `tracerelay close` | 0 | waiting session sealed and returned to `IDLE` |
| `tracerelay verify <session-directory>` | 0 | `VALID_COMPLETE` |
| `tracerelay stop` | 0 | Service and Supervisor stopped |
| `tracerelay status` after stop | 1 | expected `NOT_RUNNING` result |

No validation step requires internet access, a cloud service, a model, or
manual interaction.
