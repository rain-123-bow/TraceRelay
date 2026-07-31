# TraceRelay Requirement Design Draft

## 1. Document Metadata

- Project name: TraceRelay
- Task name: Standalone forensic relay requirement design
- Author role: `MASTER_REQUIREMENT_DESIGNER`
- Draft version: `1.0.0-draft.27`
- Created: `2026-07-29`
- Project root: `C:\code\TraceRelay`
- Artifact path: `C:\code\recorder-artifacts\tracerelay-requirement-design-v1`
- Product platform: Windows local
- Reasoning ledger: unavailable; see `REASONING_LEDGER_STATUS.md`
- Reviewer status: batch 024 full scan passed and the user confirmed its frozen
  snapshot. Batch 026 closed all 112 historical findings and `TRR25-C-001`, but
  failed one fresh P1 holder-proof linearization finding after a full scan.
  Draft.27 is the unified remediation candidate; batch 027 review is pending.
- Normative status: non-final draft

English description:

> TraceRelay is a standalone, deterministic local proxy that turns application
> traffic into durable, verifiable evidence. It records registered
> bidirectional streams before forwarding, preserves committed data on
> failure, and provides independent monitoring and read-only verification
> without AI, agents, or semantic judgment.

## 2. User Goal

Build TraceRelay as a completely independent local application whose primary
purpose is evidence support.

An external launcher registers a client run before starting the client
application. The client routes its supported bidirectional traffic through the
returned TraceRelay endpoint. TraceRelay records what crosses its boundary,
forwards it without semantic interpretation, preserves committed evidence on
failure, and exposes independent monitoring and read-only verification.

TraceRelay must be useful as a general registration-and-proxy service. It must
not contain logic belonging to any specific client application.

## 3. Background and Context

### 3.1 First-principles reason

An actor that performs an action cannot be the sole controller of the evidence
used to establish what occurred. Self-produced logs can omit, reinterpret, or
lose events, and a later observer cannot distinguish "did not occur" from
"occurred but was not recorded."

TraceRelay separates behavior from evidence control. For supported traffic,
evidence is committed before forwarding. A client may choose what to do, but
it cannot unilaterally decide what TraceRelay recorded at the proxy boundary.

### 3.2 Product model

TraceRelay is one product with four responsibility-separated components:

| Component | Responsibility |
|---|---|
| Service | registration, session lifecycle, proxying, evidence writing, status |
| Monitor | separate-process service liveness observation and alarms |
| Verifier | read-only evidence validation |
| Control client | operator commands and machine-readable control-plane access |

The service and monitor are separate processes so service failure does not
remove the only failure detector.

### 3.3 Claim boundary

TraceRelay can establish facts only about data and control events it actually
observes. A positive destination fact means only that a local Windows write
operation returned an explicit accepted-byte count. It does not prove remote
application receipt, consumption, acknowledgement, or durable storage.

TraceRelay cannot prove the absence of client bypass traffic, upstream
internal behavior, client business correctness, trusted wall-clock time, or
resistance to local tampering. v1 supports one trusted, non-malicious operator
in one Windows user/logon-session runtime context. Same-user malicious
processes, other users, administrators, SYSTEM, kernel actors, and deliberate
ACL, path-race, process-memory, evidence, or installation tampering are outside
the positive product claim.

### 3.4 Normative requirement set

This draft incorporates these files as one requirement set:

1. `NORMATIVE_CONTRACTS.md`;
2. `support-profile.windows-local-v1.json`;
3. `reason-exit-catalog.v1.json`;
4. `traceability-matrix.v1.json`.

`NORMATIVE_CONTRACTS.md` freezes the failure model, transport behavior, state
machines, byte accounting, self-contained bundle, monitor and alarm protocol,
verifier classification, Windows runtime-context boundary, deletion transaction,
bounded execution, and historical compatibility. The JSON files freeze
numeric values and machine-facing classifications. Any unresolved
cross-document conflict blocks implementation.

### 3.5 Frozen v1 operational envelope

The exact machine-readable authority is
`support-profile.windows-local-v1.json`. Key values are:

| Property | v1 value |
|---|---|
| endpoint locality | IPv4 loopback `127.0.0.1` on both sides |
| ACTIVE sessions / client connections / upstream connections | `1 / 1 / 1` per supported runtime context |
| maximum session duration | 25 hours from committed ACTIVE |
| maximum raw payload | 1 GiB per direction; 2 GiB total |
| maximum session evidence | 6 GiB |
| evidence-root quota / minimum free reserve | 32 GiB / 5 GiB |
| alarm-root quota / protected alarm reserve / deletion-audit quota | 1 GiB / 128 MiB / 256 MiB |
| installation-runtime-root quota / maximum logical / product-reachable partial bytes | 67,117,056 / 67,117,056 / 17,305,600 bytes |
| installation authority | one valid 4,096-byte `TRII/1`; two create-new attempts; 8,192 logical bytes / 8,192 partial bytes maximum |
| installation decision model | 6 mutually exclusive states; 36 complete `a0/a1` pairs; namespace/ordinal conflict guards have priority |
| installation runtime root | 8,194 files / 67 directories / 8,261 recursive entries maximum |
| IPC authority product-reachable partial bound | 4,160 files / 17,301,504 bytes; 65 files / 270,336 bytes per retained boot |
| certification host floor | 4 logical CPUs, 16 GiB RAM, local SSD/NVMe, 40 GiB free, durable-flush p99 <= 50 ms |
| monitor heartbeat / lease expiry | 1 second / 5 seconds |
| `alarm_initial_attempt_admission_deadline_ms` | 5 seconds from `detected_at` |
| `alarm_initial_outcome_freeze_deadline_ms` | 10 seconds from `detected_at` |
| `alarm_terminal_attempt_admission_deadline_ms` | 1 second from `tuple_frozen_at` |
| `alarm_terminal_emission_observation_deadline_ms` | 5 seconds from `tuple_frozen_at` |
| `alarm_timeout_decision_commit_deadline_ms` | 1 second from `timeout_decision_at` |
| alarm IPC slot | 256-byte prefix + 4,096-byte inline payload = 4,352 bytes |
| alarm IPC mappings / events / object handles / ready handles / creation handles | `4 / 8 / 24 / 28 / 51` |
| startup bootstrap | `TRBH/1`; two anonymous pipe pairs/child; 4,096-byte frames carrying the exact 3,328-byte pending `TRIM/1` inventory; 8 steady bootstrap handles; 14 process-creation transient handles |
| aggregate alarm IPC mapping bytes | 8,930,432 bytes, including one 32-byte header per mapping |
| concurrent alarm IPC incarnations | 1; replacement allocation before old-object release proof is forbidden |
| alarm IPC persistent file reference | 65,536 bytes per referenced record; 4 concurrent references; 262,144 bytes total |
| alarm observation record | exact 4,096-byte `TRAO/1` envelope; 69,632-byte known-persistent maximum; 8,192-byte session-unknown/live maximum |
| known-session alarm reservation | preallocated partition: 3 persistent records/208,896 bytes plus 3 live records/24,576 bytes per admitted alarm; 4 in flight; 32 per session; one 4,096-byte global overflow record |
| session-unknown alarm reservation | persistent-owned 5 records/143,360 bytes plus live-owned 3 records/24,576 bytes; 8 records/167,936 bytes per alarm; 128 alarms/21,495,808 bytes per monitor incarnation |
| alarm IPC abandonment recovery | 4,108 records; two attempts each; 33,652,736-byte reserve; 8,216 total attempt files; reachable retained-partial maximum 4,109 files/16,830,464 bytes |
| live alarm frame | 4,096 bytes maximum; always inline |
| drain / stop response / asynchronous delete completion | 30 seconds / 45 seconds / 30 minutes |
| certified sustained aggregate payload | 1 MiB/s full duplex for 15 measured minutes after 60-second warm-up |
| certified burst | 16 MiB within 30 seconds |
| reference added latency | p95 <= 250 ms; p99 <= 1000 ms |
| soak | exact 24-hour payload workload plus a 10-minute clean-closure budget inside the 25-hour session ceiling |

These values are the normative proposal inside this draft. They are not
implementation-selected defaults. Like every other draft requirement, they
become the final downstream contract only when the user confirms the complete
final requirement set.

## 4. In Scope

1. A standalone installable Python product for Windows.
2. A local service with a machine-readable control plane.
3. Pre-launch client registration.
4. Per-run proxy sessions and credentials.
5. One active client session per supported current-user/logon-session runtime
   context at a time in v1.
6. The normative `LOCAL_LOOPBACK_TCP_V1` full-duplex byte-stream profile.
7. Exact bidirectional byte capture for traffic crossing the proxy.
8. Write-ahead evidence and explicit forwarding outcomes.
9. Append-only per-session evidence.
10. Independent read-only verification from one self-contained session bundle.
11. Separate-process service monitoring.
12. Persistent machine-readable alarms.
13. Local evidence retention and explicit deletion.
14. Recovery sufficient to verify old sessions and start new sessions.
15. Bounded resources, waits, reports, and failure behavior.

## 5. Out of Scope

1. AI, model calls, agents, prompts, or semantic judgment.
2. Client-specific roles, nodes, workflows, policies, or verdicts.
3. Starting, pausing, resuming, terminating, or restarting clients.
4. Starting, terminating, or managing upstream services.
5. Client state saving or client task termination policy.
6. Proving client actions that did not cross the proxy.
7. Proving that no bypass channel exists.
8. Interpreting whether recorded content is correct, relevant, or malicious.
9. Post-launch attachment that claims complete evidence.
10. Multiple simultaneously active client sessions in v1.
11. Non-loopback or remote endpoint operation.
12. Linux or WSL product support.
13. Malicious local-user/process, cross-user, administrator, SYSTEM, kernel, or
    deliberate path/evidence tamper resistance.
14. External notarization, legal non-repudiation, or provider authority.
15. Cloud alerting, email, SMS, or operating-system toast notifications.
16. Automatic evidence deletion.
17. Sudden-power-loss, kernel-crash, corrupt-storage, or lying-flush positive
    durability claims.
18. Capabilities not required for current normal local use.
19. Security-product claims against malicious local users or processes.
20. Restricted-token sandboxes, custom adversarial DACL matrices, locked-memory
    guarantees, anti-dump guarantees, and malicious path-race resistance.

## 6. Functional Requirements

### 6.1 Product identity and trust boundary

| ID | Requirement | Verification |
|---|---|---|
| TR-F-001 | TraceRelay shall be independently installable and runnable without a client project source tree. | Install and start from a clean Windows environment. |
| TR-F-002 | The production package shall expose service, monitor, verifier, and control-client capabilities. | Inspect installed entry points and execute each capability. |
| TR-F-003 | No trusted execution path shall call an AI model or contain agent orchestration. | Static dependency/import scan and runtime network/model-call test. |
| TR-F-004 | Evidence capture shall not depend on parsing or understanding client business content. | Send unknown, malformed, and non-text bytes and compare exact output/evidence. |
| TR-F-005 | TraceRelay shall make claims only for a named proxy session and its observed boundary. | Validate every report contains session and scope identifiers. |
| TR-F-006 | Local evidence integrity shall not be reported as external authority or legal non-repudiation. | Validate report assurance fields and prohibited-claim tests. |

### 6.2 Service lifecycle

| ID | Requirement | Verification |
|---|---|---|
| TR-F-007 | One supported runtime context, defined as one current Windows user and logon session, shall have at most one active TraceRelay service regardless of installation runtime root, supplied name, service identity, or executable copy within that context. No cross-user or cross-session singleton claim is made. | Same-context cross-root, cross-identity, and copied-executable concurrent-start test. |
| TR-F-008 | Service lifetime shall be independent of client-session lifetime. | Start, run multiple serial sessions, and stop clients while the service remains healthy. |
| TR-F-009 | Service start shall publish readiness only after the fixed runtime-context authority, canonical `TRII/1` installation identity, exact installation-runtime-root binding, control, evidence, alarm, worker, frozen-profile, and valid-monitor-lease prerequisites are usable. | Installation identity create/restart/reinstall/conflict plus startup fault-injection matrix. |
| TR-F-010 | Service stop with no active session shall close cleanly and preserve all prior evidence. | Stop/restart and verifier test. |
| TR-F-011 | Service stop with an active session shall enter bounded drain; expiry shall close the session as incomplete. | Controlled slow-peer and timeout test. |
| TR-F-012 | Service restart shall never resume writing an earlier session journal. | Crash/restart and Windows file-identity test. |

### 6.3 Registration and session identity

| ID | Requirement | Verification |
|---|---|---|
| TR-F-013 | Operator-originated create, inspect, revoke, close, and delete mutations shall use the authorized local control plane; the service shall also perform the automatic lifecycle transitions enumerated in `NORMATIVE_CONTRACTS.md`. | Authority and automatic-transition matrix. |
| TR-F-014 | A launcher shall be able to register a client run before the client process starts. | End-to-end pre-launch registration test. |
| TR-F-015 | Registration shall produce an opaque application ID, registration ID, session ID, local proxy endpoint, and session credential. | Schema validation and uniqueness test. |
| TR-F-016 | Application identity, registration identity, session identity, connection identity, and upstream identity shall be distinct fields. | Schema and cross-field mutation tests. |
| TR-F-017 | v1 shall permit at most one ACTIVE session per supported runtime context at any instant, independent of installation path, process, or display identity within that context. | Same-context cross-root, cross-process, and cross-identity activation race test. |
| TR-F-018 | Multiple serial sessions shall use distinct evidence namespaces and credentials. | Repeated-session isolation test. |
| TR-F-019 | Unregistered, expired, revoked, replayed, or mismatched credentials shall be rejected before upstream connection or payload forwarding. | Negative credential matrix. |
| TR-F-020 | A session that did not observe traffic from its defined start shall not be relabeled as complete by later attachment. | Hot-attach rejection test. |
| TR-F-021 | Optional client metadata shall be opaque to all TraceRelay service decisions and excluded from identity authority. | Metadata mutation equivalence test. |
| TR-F-022 | A session token shall contain exactly 32 Windows-CSPRNG bytes, be returned once, never be intentionally persisted in plaintext by TraceRelay, bind one session and service incarnation, and become invalid after claim, revocation, expiry, or restart. It is a functional association and replay-prevention token, not a secrecy guarantee against local process inspection. | Source/length review, issuance, association, expiry, claim, revocation, replay, restart, and ordinary product-artifact scan. |

### 6.4 Proxy transport

| ID | Requirement | Verification |
|---|---|---|
| TR-F-023 | v1 shall implement the exact observable `LOCAL_LOOPBACK_TCP_V1` endpoint, sequential pre-claim attempt, hello, activation, authenticated connection-cardinality, EOF, half-close, error, timeout, zero-byte, and no-reconnect contract in `NORMATIVE_CONTRACTS.md`. | Normative transport and authentication truth-table conformance suite. |
| TR-F-024 | The registered upstream endpoint shall be supplied externally; TraceRelay shall connect but shall not start the upstream. | Process-tree and connection evidence. |
| TR-F-025 | TraceRelay shall preserve byte values and order within each direction. | Exhaustive byte corpus, randomized payloads, and hash comparison. |
| TR-F-026 | TraceRelay shall not apply text encoding, newline conversion, Unicode normalization, JSON normalization, or semantic filtering to proxied bytes. | Cross-platform byte fixtures on Windows. |
| TR-F-027 | Each direction shall have explicit source, destination, connection, EOF/half-close, error, and terminal lifecycle records bound to one connection ID. | Zero-byte, normal, and abnormal lifecycle tests. |
| TR-F-028 | Every observed byte range and its forwarding intent shall satisfy the supported failure model and durable-commit boundary before the first corresponding destination write. | Windows process-crash and orderly-restart crash-point tests. |
| TR-F-029 | Before every destination OS call, a durable one-use `WRITE_ATTEMPT` shall bind attempt ID, direction, connection, parent intent, and exact range; the later outcome shall record the exact known OS-accepted count, known zero progress/error, or remain absent as an explicitly possible-call unknown. | Five-boundary per-call crash matrix, short-write, zero-progress, and fault-injection suite. |
| TR-F-030 | Possible partial delivery shall never be automatically replayed. | Crash/restart and duplicate-detection test. |
| TR-F-031 | TraceRelay shall emit no application-payload success acknowledgement; transport `OK` acknowledges activation only, and reports shall never upgrade OS-accepted bytes into remote application receipt. | Wire-capture and prohibited-claim tests. |
| TR-F-032 | Proxy buffering and queues shall be bounded by `support-profile.windows-local-v1.json`. | Saturation and exact-boundary memory test. |
| TR-F-033 | Backpressure shall stop reading before any configured memory bound is exceeded. | Slow-consumer stress test. |
| TR-F-034 | Unsupported endpoint locality, hello framing, credential, connection cardinality, or transport property shall fail before application payload forwarding. | Profile preflight negative matrix. |

### 6.5 Evidence journal

| ID | Requirement | Verification |
|---|---|---|
| TR-F-035 | Every session shall create a new evidence directory; existing targets shall not be reused or overwritten. | Existing-path and race tests. |
| TR-F-036 | Evidence shall retain all proxy-observed bidirectional raw application bytes and TraceRelay control events for the session. | Stream reconstruction test. |
| TR-F-037 | Evidence shall be append-only during capture except for the current record's one-time ascending fill of its reserved zero `TRFW/1` block. No witness byte or earlier byte may be rewritten, cleared, repaired, resumed or replaced. | Write-offset, single-fill, second-write, prior-record mutation and crash instrumentation. |
| TR-F-038 | Each committed journal record shall carry its canonical monotonic sequence, previous-record digest, record kind, payload length and digest, version/profile/commit bindings, and exactly the format/variant-applicable QPC timestamps in `NORMATIVE_CONTRACTS.md`. `TRAD/1` and `TRAF/1` are not committed journal records. No universal record-observation or general-purpose UTC field exists in V1; the only wall-clock-derived authoritative field is the identity-only process-creation `FILETIME` exception in `TR-F-040`. | Per-format/variant golden vectors; required, forbidden and mutated timestamp/identity fields; restart tests. |
| TR-F-039 | Sequence, not wall clock, shall define journal order. | Clock rollback and jump tests. |
| TR-F-040 | V1 canonical evidence shall encode no wall-clock or UTC observation except the exact raw `GetProcessTimes.lpCreationTime` `FILETIME` allowed by `NORMATIVE_CONTRACTS.md` solely as an opaque process-identity discriminator. That value shall never support time order, duration, deadline, liveness, or time claims. A query/display may add query-time wall clock only outside authoritative bytes as `UNTRUSTED_QUERY_TIME`. | `FILETIME` source/encoding/failure/equality, PID-reuse, forbidden-use, reserved-zero, report-label, rollback and jump tests. |
| TR-F-041 | Only records with a valid self-contained `TRFW/1` post-flush witness may support positive offline evidence claims. Live external action additionally requires the witness write to return and exact readback to succeed. Hidden flush-return state, memory, mutable side files and recursive acknowledgement records have no offline authority. | Pre-flush, flush-pending, return-observed, every witness-byte, write-return, readback, byte-identical-history and mutation tests. |
| TR-F-042 | A persistence open, write, flush, or commit failure shall stop further forwarding for that session. | Filesystem fault injection. |
| TR-F-043 | After journal failure, committed bytes shall not be repaired, truncated, or rewritten as complete. | Poisoned-journal test. |
| TR-F-044 | Partial tails shall be retained and reported separately from committed records. A partial tail includes a short record and a complete-length record whose witness is absent or a valid strict prefix; malformed witnesses are invalid. | Crash-at-offset and absent/partial/full/malformed-witness matrix. |
| TR-F-045 | Evidence shall distinguish a clean terminal state, an incomplete terminal state, and absence of a provable terminal state. | Terminal-state truth table. |
| TR-F-046 | Raw evidence shall never be replaced by a redacted or human-readable derivative. | Export and file-identity test. |

### 6.6 Monitoring and alarms

| ID | Requirement | Verification |
|---|---|---|
| TR-F-047 | Monitor shall execute in a process distinct from the service process and use a fresh monitor incarnation, installation lock, and monitor-owned alarm writer. Service and monitor shall remain `PRE_READY` through the exact `TRBH/1` identity, final-handle and bootstrap-close sequence, and every surviving participant shall remain `PRE_READY` through matching committed `TRIM/1`. After exact child identity and Job-membership revalidation, the single kernel wait evaluation represented by `WaitForMultipleObjects(2, [service, monitor], FALSE, 0) == WAIT_TIMEOUT` shall freeze the acknowledged 28-handle holder-proof snapshot. Matching `TRIM/1` shall durably record that logical snapshot and shall not claim commit-time child liveness. Child loss before the holder-proof point shall block `TRIM/1`; child loss after it shall not cancel the one required manifest-commit attempt, shall remain a monitor/service failure, and shall prohibit external readiness. | Process-tree, identity, exclusive-lock, byte-exact frame/kind/role/phase/count/padding/challenge/projection mutations, ACK/EOF order, every process/pipe/allocation/duplication crash boundary, `13/14/15`, `50/51/52`, holder-proof return mutations, replay, deadline, and no-early-readiness tests. Cross both child roles with loss before/after the holder-proof point and every `TRIM/1` pre-witness byte boundary, flush-pending/returned boundary, witness prefix `0..44`, readback boundary, commit boundary and pre-readiness boundary. |
| TR-F-048 | Monitor shall observe process handle plus incarnation, authenticated bounded-advance heartbeat/lease sequence, declared health, operation-scoped critical progress, explicit healthy backpressure, active session, and cross-journal committed positions. | Live monitor model, sequence/lag boundary, backpressure, critical-stall, and PID-reuse tests. |
| TR-F-049 | Service shall require a valid lease bound to current service and monitor incarnations before readiness and before session activation. | Missing, stale, replayed, and wrong-incarnation lease tests. |
| TR-F-050 | Service shall stop accepting and forwarding session data when the monitor lease expires. | Monitor-kill fault test. |
| TR-F-051 | Under the supported process-failure model, service failure shall not prevent the separate monitor from attempting and, when alarm storage remains usable, durably publishing a persistent alarm. | Service-kill and alarm-storage matrix. |
| TR-F-052 | Monitor failure shall cause service to publish monitoring failure and close any ACTIVE session as incomplete. | Monitor-kill test. |
| TR-F-053 | Alarm publication shall follow independent persistent-journal and current-instance live-subscription workers; once a global alarm envelope is admitted, neither channel admission may depend on the other channel's storage, reservation, queue, journal observation, or result. Every IPC creation intent shall use exact `TRIC/1`, every ready IPC manifest exact `TRIM/1`, every dispatch exact `TRAD/1`, every observation exact tagged-union `TRAO/1`, every persistent reference exact `TRAF/1`, and every IPC-abandonment recovery fact exact `TRAR/1`. `TRIC/1` and `TRIM/1` shall form the only sequence-zero/sequence-one pair in one deterministic path-bound authority attempt, bind one canonical 16-byte Windows boot identity, and record the exact acknowledged holder-proof snapshot and verified access masks for all 28 manifest handles without asserting commit-time process liveness. Known-session capacity is preallocated at session admission, then each admitted alarm draws an infallible persistent-owned 3-record/208,896-byte subpartition and live-owned 3-record/24,576-byte subpartition. Session-unknown admission independently reserves persistent-owned 5 records/143,360 bytes and live-owned 3 records/24,576 bytes. Session-unknown persistent results always use a verified zero-body `FILE_REFERENCE`; inline persistent results require a known session. Alarm IPC shall use the complete pinned-slot lifecycle and 32-byte mapping-header freeze protocol in `NORMATIVE_CONTRACTS.md`; no body may be truncated, silently omitted, split, replaced by an unverified path, or moved into an off-slot queue. | `TRIC/1`/`TRIM/1`/`TRAD/1`/`TRAO/1`/`TRAF/1`/`TRAR/1` golden vectors, holder-proof snapshot and commit-time-liveness rejection vectors, mapping-header geometry and atomic freeze/recovery vectors, every runtime slot state/edge, variant presence/absence, deterministic authority path/attempt/sequence/previous-digest, boot identity, access-mask/probe, creation/manifest table/digest mutation, preallocated-partition failure, per-channel reserve/write failure with peer success, 4,096/4,097, 65,535/65,536, 69,632/69,633, six/seven observations, known 4/5 and 32/33, unknown 167,936/167,937 and 128/129, unknown-persistent 4,096-byte inline rejection, slow validation, slot/epoch/ACK, exact-reference recovery, restart, ordering, deduplication, journal-failure, and backpressure matrix. |
| TR-F-054 | Guaranteed detection and its global alarm-envelope admission decision shall complete before the five-second detected-at boundary. For every admitted envelope, both independent initial channel-attempt admissions shall complete within the same boundary; each is exactly one worker dispatch or one coordinator-owned pre-dispatch `FAILED_LIMIT`. Initial outcomes freeze at ten seconds. After the one immutable tuple freezes, both terminal channel-attempt admissions shall complete within one second under the same closed alternatives, and terminal observations freeze at five seconds. A timeout-decision commit shall meet its one-second runtime liveness deadline, measured externally and excluded from offline truth classification. | Global admit/reject, EMPTY-slot 0/1/2, simultaneous pinned terminal operations, worker-dispatch versus pre-dispatch-limit, and one-tick-before/at/after every detected-at, immutable tuple-frozen-at, and externally observed timeout-decision-at deadline. |
| TR-F-055 | Alarm evidence shall separate persistent/live initial-publication outcomes, overall channel outcomes, the frozen alarm-publication tuple, persistent-terminal-record delivery, and live-terminal-diagnostic delivery. `PREDISPATCH_FAILED_LIMIT` shall use its exact `TRAO/1` presence row: attempted command, channel-decision time, deadline and slot census are required; worker/slot/epoch/dispatch-return/result-body fields are zero. Initial records committed before the complete publication tuple freezes carry zero `tuple_frozen_at`; terminal records carry the one immutable actual tuple freeze. The current process freezes the channel result `FAILED` at the timely decision; only its committed observation is recovery/query/offline authority. Commit failure, partial tail, or precommit crash becomes durable-input `UNPROVEN` and terminates fail-closed. Initial/terminal success still requires timely call return and complete validation. Inline and file-referenced bodies shall have identical authority after verified handoff; a path, reference, or root record alone proves no result. | Tagged-union golden/mutation vectors; initial zero-tuple/terminal exact-tuple anchors; decision-before/commit-before/during/after crash points; EMPTY 0/1/2; one-tick deadlines; query/restart/offline-copy; inline/reference differential; root-only, identity/digest/path, validation, timeout, late-return, and fail-closed tests. |
| TR-F-056 | Unknown alarm facts shall remain explicit unknowns and shall not be inferred as success. | Missing-observation mutation tests. |
| TR-F-057 | TraceRelay alarms shall describe infrastructure facts only and shall not direct client business recovery. | Schema allowlist and content tests. |

### 6.7 Verifier and reports

| ID | Requirement | Verification |
|---|---|---|
| TR-F-058 | Verifier shall be a separate read-only command whose only verification input is one absolute self-contained evidence-session directory. | Filesystem write-detection and external-state-independence test. |
| TR-F-059 | Verifier shall not repair, truncate, normalize, or append evidence. | Before/after directory digest comparison. |
| TR-F-060 | Verifier shall detect invalid framing, changed bytes, broken digest links, sequence duplicate/skip/reorder, absent/partial/malformed commit witness, partial tail, lifecycle mismatch, outcome mismatch, and missing terminal state. | Independent mutation corpus. |
| TR-F-061 | Verifier shall implement the total classification priority, combination truth table, ascending stable reason order, cataloged observed-reason behavior, sectioned byte-budget truncation rule, and numeric exits frozen by the normative contract and reason catalog. | Exhaustive classification, internal-failure-plus-observed-fact, deterministic truncation, and CLI exit tests. |
| TR-F-062 | PASS shall require the full conjunction in `NORMATIVE_CONTRACTS.md`: valid self-contained bundle and chains, valid witness on every authoritative record, complete byte-range accounting, no unknown outcome, continuous monitoring, bilateral EOF, matching clean closures, and no failure. | Full PASS predicate and witness-state truth table. |
| TR-F-063 | INCOMPLETE shall never be reported as PASS even when every committed record is internally valid. | Incomplete-prefix fixtures. |
| TR-F-064 | Verifier internal failure shall not be reported as evidence invalidity. | Verifier fault injection. |
| TR-F-065 | Verification output shall include evidence scope, assurance and exclusions, authority flag, evaluation-complete flag, committed count, final digest, byte-range accounting, terminal and monitoring state, alarm linkage, exact stable reason counts, section truncation state, and catalog exit inside the frozen report budgets. | Schema, deterministic-order, mandatory-field retention, section-boundary truncation, and CLI exit tests. |
| TR-F-066 | Verifier limits shall equal or exceed every legal writer output under identical recursive-bundle, aggregate-record, aggregate-tail, file-count, directory-entry, path, logical-byte, and inclusive-boundary domains; report, wall-time, memory, alarm IPC object, pinned-slot, reference, observation, per-session alarm, session-unknown, installation-authority, IPC-authority, installation-runtime-root, partial-tail, and two-phase recovery limits shall use exact profile values. Old and replacement IPC incarnations shall never coexist. Before any IPC-authority parent, attempt or allocation, one exact 4,096-byte `TRII/1` installation identity shall be committed in one of two deterministic create-new attempts below the exact absolute installation runtime root. Installation resolution shall apply unavailable and namespace/ordinal conflict guards before six mutually exclusive size states and one complete 36-pair `a0/a1` decision table. Before any allocation, IPC state shall commit one exact root-and-path-attributed sequence-zero `TRIC/1`; unresolved pre-ready failure permits no later same-boot intent, while a ready IPC followed by exact `TRAR/1 RECOVERY_COMPLETE` permits only the next of 64 serial intent ordinals. IPC resolution shall apply unavailable and namespace/ordinal conflict guards before nine mutually exclusive states and one complete 81-pair decision table; only `TRIC_INCOMPLETE` or `TRIC_UNWITNESSED` attempt zero may authorize attempt one. Before readiness it shall append only one matching sequence-one `TRIM/1`, whose previous digest is the complete `TRIC/1`. The records bind the same canonical 16-byte installation identity, version-gated canonical 16-byte Windows boot identity, exact runtime-root file identity, committed `TRII/1` digest, and exact 68-byte authority path. Installation authority permits two files, one committed record, 8,192 logical bytes and 8,192 partial bytes. IPC authority retains at most 64 boot identities, 4,096 intent journals, 8,192 files/records, 67,108,864 logical/invalid-tree scan bytes, 4,160 product-reachable partial files and 17,301,504 product-reachable partial bytes. The complete runtime root permits 8,194 files, 67 directories, 8,261 entries, 67,117,056 logical/invalid-tree scan bytes and 17,305,600 product-reachable partial bytes inside a 67,117,056-byte reserved quota. Product reachability starts from an empty product-created tree and includes only canonical create-new writes, supported crash/error prefixes and declared recovery/deletion transitions; external mutation, arbitrary invalid bytes, corruption, power loss and owner/administrator tampering cannot witness a positive maximum. Relative file-path depth is the number of parent-directory components: installation authority has depth two, IPC authority depth three. `TRIM/1` shall contain reconstructable census/name/process/object/control-handle digests and exact queried access masks `0x00000006`, `0x00100002`, `0x00101000`, and `0x0010000c`. Census and recovery serialize all twelve runtime slot states. Recovery uses a deterministic manifest-derived transaction and two filename-bound attempts per logical record, acquires an irreversible quiesce/freeze barrier, commits sequence-zero `TRAR/1` inventory-open, all 2,052 canonical slot records, inventory seal, byte-exact release proof, required uniquely ordered `UNPROVEN` resolutions, and recovery-complete before replacement allocation. Hard scan/quota caps, total attempt files and product-reachable retained partial tails are distinct domains. | Maximum failed bundle, 16-MiB tail, four/five refs, 262,144/262,145 bytes, `TRAO/1` max+1, known 4/5 and 32/33, unknown 128/129, all twelve slot states/edges, 1,024-byte census and 512-byte state vector, `TRII/1` absent/zero/1/4095/4096/4097-byte attempts, zero/1..43/full/malformed `TRFW/1`, six states, all 36 pairs, wrong stored/filename ordinal and guard-priority mutations, 4,096-byte invalid `a0` plus complete/partial `a1`, installation 8,192/8,193 bytes, attempt 0/1/exhausted/conflict, cross-process/restart/reinstall identity, owner/root/path/file-ID mutation, authority-parent crash, identity missing after IPC parent, installation path parent-depth 2 and IPC path parent-depth 3/4 mutations, IPC `TRIC_INCOMPLETE` 0/1/4095, `TRIC_UNWITNESSED` 4096 with zero/1..43 witness bytes, `TRIC_VALID_TRIM_INCOMPLETE` 4096/8191, `TRIC_VALID_TRIM_UNWITNESSED` 8192, complete witnessed 8192, malformed witness/invalid/oversize 8193, all nine states and 81 pairs, `TRIC/1` field partials 223/224/239/240/247/248/251/252/255/256/271/272/275/276/279/280/311/312/343/344/375/376/4095/4096, path alias and attempt 0/1, boot identity stable/changed/unknown, ready-recover-replace ordinals 0/63/64, empty boot directory, 64/65 retained boots, 4,096/4,097 journals, 8,192/8,193 IPC files, 67,108,864/67,108,865 IPC hard bytes, 65/66 product-reachable partial files per boot, 270,336/270,337 product-reachable partial bytes per boot, 4,160/4,161 retained product-reachable IPC partial files, 17,301,504/17,301,505 retained product-reachable IPC partial bytes, 8,194/8,195 runtime files, 67/68 runtime directories, 8,261/8,262 runtime entries, 67,117,056/67,117,057 runtime logical/scan bytes, 17,305,600/17,305,601 runtime product-reachable partial bytes, external-invalid-tree fail-closed fixtures, `TRIM/1` sequence/previous-digest/access-mask/table/order/same-value-different-holder/name/session/digest vectors, recovery sequence 0/1/2052/2053/2054, zero-byte deterministic attempt files, quiesce/read/seal races, dual-process exit/PID reuse/boot change, release/resolution duplicate/equality/reason/digest mutations, unavailable mapping, repeated restart, first/second attempt partial, 4,108/4,109 records, 33,652,736/33,652,737 reserved bytes, 8,216/8,217 total attempt files, 16,830,464/16,830,465 recovery partial bytes, 4,109/4,110 recovery partial files, 59,342,848/59,342,849 protected bytes, 42,520,576/42,520,577 combined partial bytes, 5,197/5,198 combined partial files, and containment tests. |
| TR-F-067 | Production writer and verifier shall not share the implementation functions that define canonical record serialization, record digest, state transition, or recovery truth. | Static dependency boundary test. |
| TR-F-068 | A third test-only oracle shall generate golden vectors and mutations independently of both writer and verifier. | Dependency and differential test. |

### 6.8 Storage, retention, and deletion

| ID | Requirement | Verification |
|---|---|---|
| TR-F-069 | Evidence, alarm, and installation runtime roots shall be three pairwise distinct absolute user-selected directories whose opened final targets are writable local fixed-disk NTFS directories, with no final root equal to, containing, or contained by another; the runtime root is the sole installation root and sole absolute parent of installation/IPC authority. | Three-root path, filesystem, relation, final file-identity, same/different-volume, access, and binding tests. |
| TR-F-070 | v1 shall reject remote, network, device, relative, alternate-stream, case/alias-conflicting, escaping, or final-target-identity-changing paths. A path containing a reparse component is supported only when the opened final target resolves to the required local fixed-disk NTFS domain and its recorded final identity remains exact; v1 makes no malicious path-race guarantee. | Windows three-root and child-path matrix using final-handle volume, file ID, filesystem, containment, access, and reopen identity. |
| TR-F-071 | Session evidence shall use a stable unique directory identity and shall remain isolated from all other sessions. | Collision and traversal tests. |
| TR-F-072 | v1 shall not automatically delete evidence or alarms. | Long-run retention test. |
| TR-F-073 | Deletion shall be limited to enumerated objects and require a current-instance local control request bound to exact type, ID, canonical final path, manifest digest, and one-use confirmation nonce; admitted audit capacity shall be reserved before target mutation. | CLI confirmation, target-binding, audit-full, reserve, runtime-race, and prohibited-object tests. |
| TR-F-074 | Deletion shall be a durable asynchronous operation: submit returns only accepted operation ID after committed intent; read-only status reports running/succeeded/failed/unknown; final success requires committed success; deadline/crash windows remain `DELETE_UNKNOWN`. | Every-crash-point, completion-deadline, recovery, status-query, and no-cancel transaction test. |
| TR-F-075 | Installation and service admission shall reserve the installation-runtime-root authority budget before authority creation; session admission shall reserve the profile session budget and free-space reserve; same-volume roots shall sum nonoverlapping reservations once per volume; session/root/alarm/runtime quota behavior shall fail closed and never delete prior evidence. | Per-root and grouped-volume disk-capacity, exact-quota, and no-double-count tests. |
| TR-F-076 | v1 shall bind control, monitor, service, roots, and process identities to the current supported Windows user/logon-session runtime context and shall validate the operations and handles required for normal use. Default Windows access control is accepted; no cross-user, same-user-process, administrator, or custom-DACL security guarantee is made. | Current-context identity, required-access, stale-handle/process, wrong-session, and assurance-boundary tests. |
| TR-F-077 | Raw payloads shall be documented as potentially secret-bearing. | Documentation inspection. |

### 6.9 Recovery and control

| ID | Requirement | Verification |
|---|---|---|
| TR-F-078 | Recovery shall be read-only for historical sessions and shall report committed prefix, partial tail, missing outcomes, and terminal state without repair, truncation, or continuation. | Recovery write-detection and every-tail test. |
| TR-F-079 | A disconnected physical proxy connection shall not be resumed under the same session identity. | Reconnect test. |
| TR-F-080 | A recovered service may create a new session only after service and monitor readiness is re-established. | Restart readiness test. |
| TR-F-081 | Product entry points shall let an external caller start monitor and service processes; the running control plane shall cover readiness/status, application create/disable, registration plus session creation, inspect, revoke/close, graceful stop, alarm query/subscription, and delete inspect/submit/status; verification remains a separate read-only command. TraceRelay shall not start the client or upstream. | Process-owner and exhaustive CLI/API operation-set test. |
| TR-F-082 | Every public result shall use the one stable catalog reason selected by the catalog's exact eight-step first-match evaluator over closed required fact/token domains. Every predicate fact/literal shall be closed and live. Every SUCCESS/ACCEPTED/RUNNING/UNKNOWN rule shall match one complete rule-level nine-fact legal tuple pattern; values from separate patterns shall not mix. All 30 patterns shall deterministically expand to exactly 58 unique tuples in operation-array, ascending-numeric-rule, pattern-array, and fact/token mixed-radix order, with continuous ordinals, position-by-position metadata equality, product/oracle execution, and substitutions from every tuple. Input partition, mandatory final non-positive `otherwise`, immediate first return, normalization, and two-stage dispatch shall make the selector total and single-valued without translation to another proof language. | All construction invariants, exact catalog binding, ordered metadata reconstruction, deliberate order-mutation rejection, per-pattern/58-tuple coverage with missing/duplicate rejection, product-versus-independent-oracle agreement, substitutions, overlap, predicate mutation, exact alarm-query vectors, normalization, dispatch, deadline, reachability, and schema checks. |
| TR-F-083 | Every TraceRelay supervisor decision and control response shall meet its exact default or command-specific profile deadline and anchor; stop shall satisfy its component-budget inequality, asynchronous deletion shall separate response and completion deadlines, and uncancellable OS calls shall not block the supervisor state machine. | One-tick-before/at/after deadline, stop-budget, long-deletion, nonresponsive peer, and stuck-worker tests. |
| TR-F-084 | On an uncancellable-call deadline owned by transport activation, session close/revoke, application disable, or service stop, TraceRelay shall fail closed, alarm, return `TR-INCOMPLETE-WORKER-TERMINATION-UNCONFIRMED`, block new sessions until resource release is proven, and make no claim that the kernel call physically ended; asynchronous deletion uses its separate `DELETE_UNKNOWN` result. | Per-operation permanently blocking worker and catalog-membership tests. |

### 6.10 Normative closure requirements

| ID | Requirement | Verification |
|---|---|---|
| TR-F-085 | The five-file normative set named in section 3.4 shall be versioned, internally consistent, packaged together, and treated as one requirement source. | Cross-file reference and hash manifest test. |
| TR-F-086 | The v1 durability claim shall be limited to the supported failure model; every positive offline commit shall satisfy the namespace, pre-witness record, exact `TRFW/1` and recovery rules, while every live external action shall additionally satisfy flush return, witness-write return and readback rules in `NORMATIVE_CONTRACTS.md`. | Failure-model inspection, crash matrix and live/offline differential oracle. |
| TR-F-087 | Registration, credential, authentication attempt, session, application connection, write attempt, monitor lease, alarm, and deletion shall implement the complete states, transitions, atomic points, deadline anchors, and race priority in `NORMATIVE_CONTRACTS.md`. | Model-based state, final-attempt claim, operator-mutation, deadline, and concurrency tests. |
| TR-F-088 | Application-byte evidence semantics shall use direction, connection ID, monotonic stream offset, and half-open byte range, independent of OS read chunking. | Differential chunking and range-property tests. |
| TR-F-089 | For each direction, the verifier shall prove the exact `O_d/T_d/A_d/U_d` attempt/outcome conservation rules and normative vectors; unknown or replayed ranges prevent PASS. | Independent property oracle plus empty/full/short/zero/unknown vectors. |
| TR-F-090 | A session bundle shall include its exact support profile, reason catalog, service journal, monitor journal, known-session alarm-publication observations with exact persistent record copies, call-return timestamps, frozen-tuple binding, live acceptance facts, timeout decisions, alarm linkage, logical identity, origin facts, and version bindings so offline result computation uses no alarm root or mutable external state and exact copies remain verifiable. | Offline copied/relocated-directory verification, alarm-root-unavailable verification, timely/late/root-only observation crash windows, timeout decision, and origin-identity mutation tests. |
| TR-F-091 | Monitor bootstrap, incarnation, process-handle observation, authenticated lease acceptance, bounded sequence advance, cross-journal deadline, critical-operation progress, healthy backpressure, restart rule, guarantee set, and exclusions shall match the normative protocol. | Monitor state model, gap/lag/stall boundary, backpressure, and fault-injection suite. |
| TR-F-092 | Alarm publication shall define non-self-referential initial and terminal semantics, timely versus late return observations, durable timeout truth separated from externally measured commit liveness, self-contained known-session authority, detector-owned service/monitor journal authority for session-unknown alarms, independent aggregate charging, separate recovery/verifier inputs, crash-to-unproven behavior, forged-writer rejection, causal deadlines, backpressure, ordering, query, and deterministic `TR-ALARM-UNPROVEN`. | Dual-channel, timely/late/root-only, timeout pre/post/late commit, both detector roles with no session, writer crash/restart/forgery, offline-copy, and causal-deadline truth table. |
| TR-F-093 | Verifier classification shall be total and deterministic for every combination of preflight, internal, invalid, incomplete, and clean facts. | Exhaustive generated truth table. |
| TR-F-094 | Every session shall bind schema, canonical serialization, digest suite, writer identity, exact support-profile bytes/hash, exact reason-catalog bytes/hash/version, and transport profile; catalog version bytes shall never be reused, and current v1 verifier shall support all emitted `1.x` evidence. | Cross-version, catalog-byte mutation/reuse, and golden-vector suite. |
| TR-F-095 | Runtime-context service and ACTIVE authority shall not be bypassable inside that context by another installation runtime root, display identity, or executable copy. | Same-context cross-root/identity/copy race test. |
| TR-F-096 | Automatic service transitions shall be distinguished from operator-originated control authority and shall leave committed lifecycle reasons when persistence remains usable. | Automatic-transition matrix. |
| TR-F-097 | Writer, session, closure reserve, monitor, alarm page, deletion audit, root, verifier input/tree/time, report section, control, and performance bounds shall come from the same frozen profile and satisfy every declared unit, aggregate domain, reserve, and containment rule. | Static inequality, derived-budget, maximum-output, audit-full, alarm-page, and terminal-reserve tests. |
| TR-F-098 | The exact v1 operational envelope, host/volume certification procedure, and reproducible workload/statistical protocols shall be accepted as written or fail with a stable catalog reason; implementation may exceed targets but may not narrow input limits, relax workload, average away a one-second host-gate excursion, discard samples, or lengthen deadlines. | Three-run sustained/burst/latency protocol, GetSystemTimes/GetProcessTimes and ETW host gate, same-volume 4-GiB storage-floor benchmark, raw-sample retention, nearest-rank calculation, soak, and boundary tests. |
| TR-F-099 | The release shall ship a versioned machine-readable reason/exit catalog and a per-requirement bidirectional traceability matrix. | Schema, uniqueness, and coverage tests. |
| TR-F-100 | Both initial alarm publications being unavailable shall never be reported as success; terminal diagnostic acceptance shall not upgrade failure; recovery/verifier shall emit `TR-ALARM-UNPROVEN` when committed persistent or detector-journal facts cannot prove initial publication and the frozen terminal tuple. | Initial/terminal dual-channel loss and recovery test. |
| TR-F-101 | A clean terminal or PASS shall be produced only by the complete clean predicate, never by one terminal flag or success path. | Predicate mutation and branch-coverage test. |
| TR-F-102 | Above the certified throughput envelope, TraceRelay may apply backpressure or close incomplete but shall not weaken commit-before-forward, evidence accounting, or fail-closed behavior. | Over-envelope stress and invariant tests. |

## 7. Non-Functional Requirements

| ID | Requirement | Verification |
|---|---|---|
| TR-NF-001 | Evidence truth and completeness shall take priority over throughput and latency. | Failure-policy and acceptance-gate inspection. |
| TR-NF-002 | TraceRelay shall never continue forwarding after it can no longer preserve the evidence contract. | Persistence and monitor fault tests. |
| TR-NF-003 | No resource shall grow without a declared hard bound. | Static configuration audit and stress test. |
| TR-NF-004 | The release shall publish and enforce `support-profile.windows-local-v1.json`; implementation may not substitute unconstrained values. | Profile schema, packaged-byte hash, and runtime-value validation. |
| TR-NF-005 | Behavior at every support-profile boundary shall be deterministic and fail closed. | Boundary-value tests. |
| TR-NF-006 | A failed session shall not modify historical evidence or prevent later read-only verification. | Failure isolation test. |
| TR-NF-007 | One failed session shall not prevent a new session after service recovery and readiness. | Recovery isolation test. |
| TR-NF-008 | Production packages shall be reproducibly attributable to exact source and version identifiers. | Clean build and package-manifest comparison. |
| TR-NF-009 | Runtime diagnostics shall not duplicate raw payloads or session-token plaintext outside authoritative evidence and the one issuance/authentication path. | Ordinary log, terminal, alarm, audit, and report scan. |
| TR-NF-010 | The first release shall be validated on Windows 11 x64, local NTFS, and CPython 3.13; other environments shall remain unsupported until separately certified. | Environment gate and clean-host validation. |
| TR-NF-011 | WSL and Linux results shall not satisfy the Windows product gate. | Release gate inspection. |
| TR-NF-012 | The product shall complete the exact 24-hour payload workload, bilateral EOF, monitor closure, terminal commit, and offline PASS inside the separate frozen closure budget and 25-hour session ceiling without unbounded growth, deadlock, silent evidence loss, or false PASS. | Frozen-profile Windows monotonic-anchor, exact-byte, closure-margin soak test. |

## 8. Inputs

### 8.1 Service inputs

- release support profile;
- service identity;
- absolute evidence root;
- absolute alarm root;
- absolute installation runtime root;
- local control-plane configuration;
- monitor identity and lease configuration.

### 8.2 Registration inputs

- application identity or request to create one;
- supported transport-profile identifier;
- upstream endpoint;
- optional opaque client metadata;
- evidence policy fixed to the v1 raw-retention contract.

Registration ID, session ID, connection ID, and credential are generated by
TraceRelay and cannot be supplied by the caller.

### 8.3 Data-plane inputs

- session credential;
- exact bidirectional client and upstream bytes;
- connection lifecycle events;
- operating-system I/O outcomes.

### 8.4 Verifier inputs

- exactly one absolute self-contained evidence-session directory.

The verifier shall reject caller attempts to select or override a support
profile. The authoritative profile is the exact session-bound copy.

## 9. Outputs

### 9.1 Registration output

- application ID;
- registration ID;
- session ID;
- proxy endpoint;
- session token delivered once through the current-instance local control
  response;
- support-profile ID;
- evidence-directory identity;
- activation expiry.

### 9.2 Runtime output

- payload bytes forwarded after prior committed intent;
- machine-readable session state;
- infrastructure failure result when applicable;
- append-only session journal with only the current record's one-time
  `TRFW/1` fill;
- append-only alarm records with the same sole witness-fill exception;
- durable long-operation ID and read-only operation state for deletion.

### 9.3 Verification output

- versioned machine-readable report;
- result class;
- stable reason IDs;
- evidence scope and assurance;
- committed-entry count and final digest;
- directional stream accounting;
- forwarding outcome accounting;
- terminal and monitoring states;
- partial-tail facts;
- bounded issue details;
- process exit consistent with result class.

## 10. File and Path Contracts

### 10.1 Project and requirement paths

- Source repository: `C:\code\TraceRelay`
- Requirement artifact path:
  `C:\code\recorder-artifacts\tracerelay-requirement-design-v1`
- Requirement artifacts shall remain outside the empty source repository until
  the user confirms the final document and separately authorizes repository
  publication.

### 10.2 Product evidence paths

- evidence root: operator-selected absolute local Windows directory;
- alarm root: operator-selected distinct absolute local Windows directory;
- installation runtime root: operator-selected third absolute local Windows
  directory and the sole installation root;
- the three roots are pairwise non-equal and non-containing;
- the three roots may occupy the same NTFS volume, but shared-volume failure is
  declared as a common failure domain rather than channel independence;
- installation identity attempts:
  `_runtime/installation-authority/identity-a0.trii` and
  `_runtime/installation-authority/identity-a1.trii`;
- IPC-authority attempts:
  `_runtime/ipc-authority/bB[32]/iII[2]-aA.tria`;
- session directory: create-new child bound to one session identity;
- exact `TRIC/1`, `TRIM/1`, `TRAD/1`, `TRAO/1`, `TRAF/1`, and `TRAR/1` binary encodings:
  requirement-level authority frozen by `NORMATIVE_CONTRACTS.md`;
- other product filenames and non-authoritative IPC/control framing:
  implementation-plan decisions constrained by mandatory roles, profile
  bindings, self-contained evidence, compatibility and verification behavior;
- temporary files: prohibited for authoritative evidence unless they are
  create-new, identity-bound, crash-accounted, and explicitly included in the
  evidence state machine.

## 11. External Dependencies

1. Supported Windows 11 x64 environment.
2. Local NTFS storage for the first validated profile.
3. Supported CPython 3.13 runtime.
4. An external launcher that starts the upstream and client processes.
5. A client integration that uses the registered proxy endpoint from its first
   supported byte.
6. At least the profile admission reservation plus the minimum free-space
   reserve on supported local NTFS storage.

TraceRelay does not require a specific client project, model provider,
workflow engine, or upstream application protocol above the supported
byte-stream profile.

## 12. Reasoning Ledger Dependencies

No project reasoning ledger exists. No reasoning-ledger item is used.

This absence does not block drafting because all product decisions used here
are explicitly included in this document. It does block any claim that the
draft has been checked against prior project-local decisions.

## 13. Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| TR-AC-001 | All `TR-F-*` and `TR-NF-*` requirements have executable tests or static verification evidence. |
| TR-AC-002 | Clean Windows installation exposes all four product capabilities. |
| TR-AC-003 | A registered loopback client completes one normal `LOCAL_LOOPBACK_TCP_V1` full-duplex session through one live loopback upstream, and offline verification of the copied bundle returns PASS. |
| TR-AC-004 | Reconstructed observed ranges match the test source bytes, and reconstructed OS-accepted ranges match injected/local OS write-return facts, byte-for-byte and offset-for-offset; no report claims remote application receipt. |
| TR-AC-005 | Every namespace, record byte, durable-flush, `TRFW/1` byte, witness-write return/readback, `WRITE_ATTEMPT` precommit, after-attempt-before-call, during-call, after-return-before-outcome, and after-outcome crash point under the supported failure model produces the exact PASS/non-PASS and live-action oracle. Byte-identical histories that differ only by hidden flush-return state have the same offline non-PASS result; no uncommitted record is upgraded. |
| TR-AC-006 | Every full, short, zero-progress, error, and no-outcome forwarding attempt produces the exact `O_d/T_d/A_d/U_d` accounting and no automatic replay. |
| TR-AC-007 | Every guaranteed service/monitor failure first receives a bounded global alarm-envelope admission decision. A rejected fifth-concurrent/33rd-cumulative known-session envelope commits one canonical `ALARM_ENVELOPE_ADMISSION_LIMIT` record and creates no channel attempt. Every admitted envelope then produces independent persistent/live initial attempt admissions; each is exactly one real worker dispatch or one coordinator-owned pre-dispatch `FAILED_LIMIT`, and peer-owned failure cannot block it. Pre-dispatch current-process truth, zero-before-complete initial `tuple_frozen_at`, immutable terminal tuple anchor, and durable authority follow the exact commit/crash rules. Initial success requires timely call return plus complete validation; late/root-only artifacts cannot upgrade it. Known-session and session-unknown channels obey separate reservation ownership. IPC startup first resolves one committed `TRII/1` under the sole absolute installation runtime root, then commits root-and-path-attributed sequence-zero `TRIC/1` before allocation and one sequence-one matching `TRIM/1` before readiness. After bootstrap closure, exact identity and Job revalidation followed by one two-process zero-time wait returning `WAIT_TIMEOUT` freezes the acknowledged holder-proof snapshot. `TRIM/1` durably records that snapshot and does not assert commit-time liveness. Pre-proof child loss prohibits `TRIM/1`; post-proof child loss cannot cancel the manifest attempt, selects `TR-START-FAILED`, prohibits external readiness, and leaves any successfully committed manifest as the recovery authority. An absent, partial, conflicting, exhausted, moved, or mismatched installation identity fails startup, and unresolved pre-ready uncertainty blocks the boot. A ready old IPC may be replaced in the same boot only after exact `TRAR/1 RECOVERY_COMPLETE` and only with the next bounded intent ordinal. Runtime recovery uses deterministic filename-bound attempts, stable installation and boot identities, exact ready-handle grants, freezes all old mutation before sequence-zero `TRAR/1`, seals the exact twelve-state inventory before release, and uses byte-exact release/resolution equality and digest rules before replacement. Offline verification uses only its bundle. Wrong-session absence, unknown installation/boot/process identity, root substitution, unknown-session persistent inline, truncation, missing bytes, path substitution, early reuse, old/new coexistence, access mismatch, and file-only inference are rejected. |
| TR-AC-008 | Verifier detects every mutation class listed in TR-F-060. |
| TR-AC-009 | Historical evidence directory bytes are unchanged by verification, recovery, service restart, and a failed later session. |
| TR-AC-010 | Unsupported paths, credentials, transport properties, platform profiles, and concurrent activation fail before payload forwarding. |
| TR-AC-011 | The packaged/runtime profile bytes equal the confirmed profile; all recursive-bundle containment, 16-MiB tail, 7,475,200-byte alarm/26,079,232-byte non-alarm closure partitions, audit/alarm reserves, pagination, report, control timing, single-concurrent-incarnation IPC object equations, persistent references, exact 4,096-byte `TRII/1`, `TRIC/1` and `TRIM/1`, `TRAD/1`/`TRAO/1`/`TRAF/1`/`TRAR/1` sizes, installation unavailable/conflict guard priority, six installation states/36 pairs, two installation attempts/one identity record/8,192 installation bytes/8,192 installation partial bytes, IPC unavailable/conflict guard priority, nine IPC states/81 pairs, 8,194 runtime files/67 directories/8,261 entries/67,117,056 logical and invalid-tree scan bytes/67,117,056 reserved bytes, 17,305,600 product-reachable partial bytes, installation/IPC parent-directory depths 2/3, two process/four mapping/eight event/24 object-handle/four control-handle manifest tables, exact `TRBH/1` two-pipe/two-validation-stage/close-ACK protocol, one exact two-process zero-time holder-proof wait, acknowledged-snapshot rather than commit-time-liveness manifest semantics, 4,096-byte frames carrying the exact 3,328-byte pending `TRIM/1` inventory, 8 steady bootstrap handles, 14 process-creation transient handles, 28 manifest and successful-ready handles and 51 maximum PRE_READY creation handle entries, exact four ready access masks, 16-byte installation and boot identities, 64 intents per boot, 64 retained boot identities, 4,096 authority journals, 8,192 authority records/files, 67,108,864 authority logical and invalid-tree scan bytes, 65/4,160 product-reachable authority partial files per boot/retained and 270,336/17,301,504 product-reachable authority partial bytes per boot/retained, twelve slot states, known-session 4/32 alarm bounds, session-unknown 167,936-byte reservation, 4,108-record two-attempt recovery reserve, 8,216 total attempt files, 16,830,464 recovery partial bytes/4,109 partial files, 59,342,848 protected bytes, 42,520,576 combined partial bytes, 5,197 combined partial files, and resource inequalities pass at inclusive/exclusive boundaries. |
| TR-AC-012 | The exact 24-hour payload workload starts and ends on its frozen monotonic anchors, produces exact per-direction bytes and 24 bursts, then reaches clean monitor/service closure and offline PASS inside the 10-minute closure and 25-hour session bounds. |
| TR-AC-013 | Package/source attribution and clean-environment install evidence are retained. |
| TR-AC-014 | Tests prove session-token source and length, one-time issuance, exact session/incarnation association, claim, expiry, revocation, replay rejection, restart invalidation, and absence from ordinary persistent product artifacts; no locked-memory, zeroization-deadline, anti-dump, or local-adversary secrecy claim is required. |
| TR-AC-015 | No production dependency path introduces AI, agent orchestration, or semantic record filtering. |
| TR-AC-016 | Independent requirement review has no unresolved blocking ambiguity, conflict, missing information, unverifiable item, or context dependency. |
| TR-AC-017 | User confirms the exact final requirement document as the sole downstream requirement source. |
| TR-AC-018 | Exhaustive verifier combinations, including internal failure after observed defects, return the exact class, ascending ordered catalog reasons, exact totals, deterministic section truncation state, and exit code. |
| TR-AC-019 | Every deletion admission, audit-full, async running, completion-deadline, and crash point returns or recovers to the exact accepted/running/succeeded/failed/unknown state without deleting a forbidden or mismatched target. |
| TR-AC-020 | Current v1 verifier validates every emitted `1.x` golden bundle and its exact embedded catalog/profile bindings, and deterministically rejects unsupported major versions without calling them corrupt. |
| TR-AC-021 | Current-user/logon-session runtime-context tests enforce exact process/session/handle association for normal operation, and assurance output explicitly excludes malicious local users, same-user processes, administrators, SYSTEM, and kernel actors. |
| TR-AC-022 | Machine-readable traceability has one or more tests for every requirement and no test with an unknown requirement ID. |

## 14. Failure Criteria

The release fails acceptance if any of the following occurs:

1. a destination write call lacks prior committed observation, intent, and
   exact one-use `WRITE_ATTEMPT`;
2. a possible partial delivery is automatically replayed;
3. raw bytes are normalized, filtered, or lost;
4. persistence or monitoring failure permits continued forwarding;
5. a corrupt, incomplete, uncertain, or unmonitored session receives PASS;
6. verifier modifies evidence;
7. service failure removes all available alarm paths without an explicit
   unproven-alarm result;
8. a new session reuses or overwrites an existing evidence namespace;
9. automatic cleanup removes evidence;
10. session-token plaintext is intentionally persisted outside its one
    issuance/authentication path, or raw payload leaks through ordinary logs;
11. an unsupported platform is presented as supported;
12. an out-of-scope external-authority claim is emitted;
13. any required test is skipped without converting the result to not-passed;
14. reviewer blocking findings or final user confirmation remain unresolved;
15. a local OS write return is represented as remote application receipt;
16. caller-selected current state, alarm root, or profile changes the result for
    the same self-contained evidence directory;
17. an implementation-selected limit, workload, sample rule, aggregate domain,
    or deadline narrows or lengthens the confirmed operational envelope;
18. an uncancellable worker blocks the supervisor decision or silently permits
    new forwarding;
19. deletion audit, report sections, alarm pages, bundle trees, or closure
    records can exceed an undeclared or unreserved resource bound;
20. an alarm IPC body is truncated, silently omitted, split across slots,
    accepted from a path without identity/range/digest verification, or causes
    live publication to depend on the persistent alarm journal.

## 15. Constraints and Prohibitions

1. Quality may trade speed; speed may not trade evidence quality.
2. No AI, model, agent, prompt, or semantic judgment inside TraceRelay.
3. No client-specific business logic in the product core.
4. No hidden fallback that bypasses evidence capture.
5. No post-hoc attachment claim.
6. No automatic replay after possible partial forwarding.
7. No automatic evidence deletion.
8. No repair of authoritative evidence.
9. No Linux product claim.
10. No external-authority or legal-proof claim.
11. No future capability may block v1 unless new evidence proves the current
    v1 goal cannot be achieved.
12. Reviewer findings must be evaluated against this frozen scope.

## 16. User Confirmed Decisions

1. Project name: TraceRelay.
2. Product is a completely independent application.
3. Product is a registration-based proxy service.
4. Product is implemented in Python.
5. Product contains only deterministic mechanisms; no intelligent agent.
6. Primary purpose is evidence support.
7. Evidence is committed before forwarding.
8. Complete raw bidirectional content is retained.
9. TraceRelay service must be monitored.
10. Failure triggers immediate alarm and preserves committed evidence.
11. Client-specific save-and-stop behavior belongs to client integration, not
    TraceRelay.
12. TraceRelay starts before a registered client run.
13. TraceRelay does not start or own clients or upstream services.
14. Hot attachment is prohibited.
15. One local service is sufficient.
16. Service lifetime is operator-controlled and longer than client runs.
17. v1 uses explicit local retention and no automatic deletion.
18. Capabilities not needed for current use are excluded from v1.
19. Windows is the only product platform.
20. The caller that needs TraceRelay is responsible for starting or confirming
    TraceRelay before launching the registered client.
21. v1 has one local TraceRelay service and one ACTIVE session at a time; app
    registration does not create one service per client application.
22. An alarm IPC body that does not fit the inline region shall be written
    completely to a TraceRelay-owned bounded file and represented by a verified
    file reference. Silent truncation is prohibited. The initial numeric
    profile uses a 4,096-byte inline body, a 65,536-byte persistent referenced
    record, four concurrent persistent references, and a 4,096-byte inline
    live frame.
23. The only intended user in v1 is one trusted, non-malicious operator.
24. Functional correctness and normal-use robustness take priority over
    security-product defenses; malicious local-user/process resistance is not
    a v1 acceptance obligation.
25. Reasonable runtime validation remains mandatory: schema and length bounds,
    state and deadline checks, final-handle path identity, process identity and
    liveness, handle/API results, resource limits, durability, recovery, and
    fail-closed handling whenever evidence certainty is lost.
26. The acknowledged IPC holder inventory uses one logical proof point after
    bootstrap closure. A later durable manifest records that proven snapshot,
    not commit-time child liveness. Post-proof child loss may trade operational
    availability for deterministic evidence but may not cancel the manifest
    commit attempt or permit external readiness.

## 17. Open Questions

No unresolved design question remains. The complete operational profile is
specified rather than delegated to implementation. The user still retains the
mandatory final accept/reject decision for the complete requirement set.

The post-bootstrap Windows control/monitor IPC primitive, selected executable
packaging, non-authoritative filenames and non-authoritative control framing
remain implementation-plan decisions. The seven named authoritative record
formats `TRII/1`, `TRIC/1`, `TRIM/1`, `TRAD/1`, `TRAO/1`, `TRAF/1`, and
`TRAR/1`, the `TRFW/1` witness encoding, the non-persistent `TRBH/1` startup
encoding and topology, observable behavior, failure model, transport
handshake, identities, states, byte accounting, durable boundary, profile
values, classifications and acceptance rules are frozen and cannot be changed
by the implementation plan.

Normative authority is partitioned: this draft owns scope, behavior and
acceptance; `NORMATIVE_CONTRACTS.md` owns field-level state and byte schemas;
the support profile owns numeric limits; the reason catalog owns reason/result
selection; the traceability matrix mirrors requirements and test obligations.
No lower-level file may weaken a higher-level obligation. A direct conflict
between authorities invalidates the requirement set and blocks implementation;
an implementation may not choose the favorable side.

One approval gate remains: the user must confirm the exact final requirement
set, including the complete operational-envelope values. Until then this is a
non-final draft, not implementation authorization.

## 18. Reviewer Status

- reviewer role: `MASTER_REVIEWER`
- active reviewer handle: `/root/tracerelay_requirement_change_reviewer`
- batch 001 verdict: `FAIL` (`P0=3`, `P1=14`, `P2=3`)
- batch 001 report: `reviews/batch-001/REVIEW_RESULT.md`
- batch 001 disposition: all 20 findings accepted into one unified remediation
- batch 002 first full scan: `FAIL` (`P0=0`, `P1=9`, `P2=2`);
  `reviews/batch-002/REVIEW_RESULT.md`
- batch 002 second independent full scan: `FAIL` (`P0=1`, `P1=8`, `P2=2`);
  `reviews/batch-002-independent-002/REVIEW_RESULT.md`
- batch 002 disposition: all findings from both completed scans aggregated
  before one draft.3 remediation; no per-finding edit cycle used
- batch 003 full scan: `FAIL` (`P0=0`, `P1=4`, `P2=0`);
  `reviews/batch-003/REVIEW_RESULT.md`
- batch 003 disposition: all four findings aggregated before one draft.4
  remediation; no per-finding edit cycle used
- batch 004 full scan: `FAIL` (`P0=0`, `P1=2`, `P2=1`);
  `reviews/batch-004/REVIEW_RESULT.md`
- batch 004 disposition: all three findings aggregated before one draft.5
  remediation; no per-finding edit cycle used
- batch 005 full scan: `FAIL` (`P0=0`, `P1=3`, `P2=2`);
  `reviews/batch-005/REVIEW_RESULT.md`
- batch 005 disposition: all five findings aggregated before one draft.6
  remediation; no per-finding edit cycle used
- batch 006 full scan: `FAIL` (`P0=0`, `P1=3`, `P2=0`);
  `reviews/batch-006/REVIEW_RESULT.md`
- batch 006 disposition: all three findings aggregated before one draft.7
  remediation; no per-finding edit cycle used
- batch 007 full scan: `FAIL` (`P0=0`, `P1=3`, `P2=1`);
  `reviews/batch-007/REVIEW_RESULT.md`
- batch 007 disposition: all four findings aggregated before one draft.8
  remediation; no per-finding edit cycle used
- batch 008 full scan: `FAIL` (`P0=0`, `P1=4`, `P2=0`);
  `reviews/batch-008/REVIEW_RESULT.md`
- batch 008 disposition: all four findings aggregated before one draft.9
  remediation; no per-finding edit cycle used
- batch 009 full scan: `PASS` (`P0=0`, `P1=0`, `P2=0`);
  `reviews/batch-009/REVIEW_RESULT.md`
- batch 009 user confirmation: recorded in `USER_CONFIRMATION.md`
- batch 010 snapshot: `tracerelay-req-b010-cd10afecb2f4`
- batch 010 full scan: `FAIL` (`P0=0`, `P1=2`, `P2=1`);
  `reviews/batch-010/REVIEW_RESULT.md`
- batch 010 disposition: all three findings aggregated before one draft.11
  remediation; no per-finding edit cycle used
- batch 011 snapshot: `tracerelay-req-b011-15dad45740a6`
- batch 011 full scan: `FAIL` (`P0=0`, `P1=3`, `P2=0`);
  `reviews/batch-011/REVIEW_RESULT.md`
- batch 011 disposition: all three findings aggregated before one draft.12
  remediation; no per-finding edit cycle used
- batch 012 snapshot: `tracerelay-req-b012-bb3ba8e81c04`
- batch 012 full scan: `FAIL` (`P0=0`, `P1=5`, `P2=0`);
  `reviews/batch-012/REVIEW_RESULT.md`
- batch 012 disposition: all five findings aggregated before one draft.13
  remediation; no per-finding edit cycle used
- batch 013 snapshot: `tracerelay-req-b013-92c4b441d5bc`
- batch 013 full scan: `FAIL` (`P0=0`, `P1=7`, `P2=1`);
  `reviews/batch-013/REVIEW_RESULT.md`
- batch 013 disposition: all eight findings aggregated before one draft.14
  remediation; no per-finding edit cycle used
- batch 014 snapshot: `tracerelay-req-b014-a1f788a22176`
- batch 014 full scan: `FAIL` (`P0=0`, `P1=2`, `P2=0`);
  `reviews/batch-014/REVIEW_RESULT.md`
- batch 014 disposition: both findings aggregated before one draft.15
  remediation; no per-finding edit cycle used
- batch 015 snapshot: `tracerelay-req-b015-c4e86aa319a6`
- batch 015 full scan: `FAIL` (`P0=0`, `P1=8`, `P2=0`);
  `reviews/batch-015/REVIEW_RESULT.md`
- batch 015 disposition: all eight findings aggregated before one draft.16
  remediation; no per-finding edit cycle used
- batch 016 snapshot: `tracerelay-req-b016-9aa91183bcbb`
- batch 016 full scan: `FAIL` (`P0=0`, `P1=5`, `P2=0`);
  `reviews/batch-016/REVIEW_RESULT.md`
- batch 016 disposition: all five findings aggregated before one draft.17
  remediation; no per-finding edit cycle used
- batch 017 snapshot: `tracerelay-req-b017-519450bea31c`
- batch 017 full scan: `FAIL` (`P0=0`, `P1=1`, `P2=0`);
  `reviews/batch-017/REVIEW_RESULT.md`
- batch 017 disposition: the one complete finding was retained before one
  draft.18 remediation; no per-finding edit cycle used
- batch 018 snapshot: `tracerelay-req-b018-092a295ce678`
- batch 018 full scan: `FAIL` (`P0=0`, `P1=3`, `P2=0`);
  `reviews/batch-018/REVIEW_RESULT.md`
- batch 018 disposition: all three findings were aggregated before one
  draft.19 remediation; no per-finding edit cycle used
- batch 019 snapshot: `tracerelay-req-b019-6bbc69a5928f`
- batch 019 full scan: `FAIL` (`P0=0`, `P1=3`, `P2=0`);
  `reviews/batch-019/REVIEW_RESULT.md`
- batch 019 disposition: all three findings were aggregated before one
  draft.20 remediation; no per-finding edit cycle used
- batch 020 snapshot: `tracerelay-req-b020-fa3fada8f5cc`
- batch 020 full scan: `FAIL` (`P0=1`, `P1=0`, `P2=0`);
  `reviews/batch-020/REVIEW_RESULT.md`
- batch 020 disposition: the complete finding was retained before one draft.21
  remediation; no per-finding edit cycle used
- batch 021 snapshot: `tracerelay-req-b021-9ea4a0738ea4`
- batch 021 full scan: `FAIL` (`P0=0`, `P1=1`, `P2=1`);
  `reviews/batch-021/REVIEW_RESULT.md`
- batch 021 disposition: both findings were aggregated before one draft.22
  remediation; no per-finding edit cycle used
- batch 022 snapshot: `tracerelay-req-b022-c3ab99a283ea`
- batch 022 full scan: `FAIL` (`P0=0`, `P1=1`, `P2=0`);
  `reviews/batch-022/REVIEW_RESULT.md`
- batch 022 disposition: the complete finding was retained before one draft.23
  remediation; no per-finding edit cycle used
- batch 023 snapshot: `tracerelay-req-b023-1f81881219a6`
- batch 023 full scan: `FAIL` (`P0=0`, `P1=1`, `P2=0`);
  `reviews/batch-023/REVIEW_RESULT.md`
- batch 023 disposition: the complete finding was retained before one draft.24
  remediation; no per-finding edit cycle used
- batch 024 full scan: `PASS` (`P0=0`, `P1=0`, `P2=0`);
  `reviews/batch-024/REVIEW_RESULT.md`
- batch 024 disposition: the user confirmed snapshot
  `tracerelay-req-b024-fc46d805d0be`; it remains immutable historical authority
  until this change passes review and receives a separate user confirmation
- batch 025 snapshot: `tracerelay-req-b025-dce914052bd2`
- batch 025 full scan: `FAIL` (`P0=0`, `P1=1`, `P2=0`);
  `reviews/batch-025/REVIEW_RESULT.md`
- batch 025 disposition: `TRR25-C-001` accepted into one draft.26 remediation;
  no per-finding edit/review cycle used
- batch 026 snapshot: `tracerelay-req-b026-e2fd35fe55ba`
- batch 026 full scan: `FAIL` (`P0=0`, `P1=1`, `P2=0`);
  `reviews/batch-026/REVIEW_RESULT.md`
- batch 026 historical closure: `112/112 CLOSED`; `TRR25-C-001` closed
- batch 026 disposition: `TRR26-C-001` accepted into one draft.27 remediation;
  no per-finding edit/review cycle used
- batch 027 status: this draft.27 is the review candidate; its identity is
  supplied only by the enclosing immutable `SNAPSHOT_MANIFEST.json`
- review basis: frozen requirement-set snapshots only
- required review mode: independent first-principles full-document scan
- incremental single-finding review: prohibited
- source modification during review batch: prohibited
- result location: independent Markdown file under `reviews/<batch>/`
