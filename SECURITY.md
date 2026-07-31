# Security

TraceRelay is pre-release software and currently contains no runtime recorder.
Do not use it to capture production evidence.

The first version assumes one trusted local Windows user. It does not claim
resistance to same-user, administrator, SYSTEM, filesystem, or storage
tampering. Reasonable runtime input validation remains required.

Report a suspected security defect privately to the repository owner. Include
the affected version, reproduction conditions, observed impact, and the
smallest non-sensitive evidence needed to reproduce it. Do not include captured
payloads, credentials, keys, or personal data in a public issue.
