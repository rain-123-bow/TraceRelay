# TraceRelay Implementation Plan Draft

## 1. Status

- author role: `MASTER_IMPLEMENTATION_PLAN_DESIGNER`
- status: `BATCH010_C003_G003_UNIFIED_REMEDIATION_DRAFT10_REVIEW_PENDING`
- plan version: `1.0.0-draft.10`
- created: `2026-07-29`
- amended: `2026-07-31`
- source repository: `C:\code\TraceRelay`
- implementation artifact root:
  `C:\code\recorder-artifacts\tracerelay-implementation-plan-v1`
- implementation authorization: `SUSPENDED_PENDING_BATCH010_REVIEW_AND_USER_CONFIRMATION`
- code modification in this phase: `FORBIDDEN`
- independent review:
  `batch-001 FAIL; batch-002 FAIL; batch-003 FAIL; batch-004 FAIL;
  batch-005-g001 scoped PASS; batch-006 FULL_PLAN FAIL P0=0/P1=1/P2=0;
  batch-007 FULL_PLAN PASS P0=0/P1=0/P2=0 and user-confirmed;
  batch-008 FULL_PLAN FAIL P0=0/P1=2/P2=0 with C-001 and R-003;
  batch-009 FULL_PLAN FAIL P0=0/P1=2/P2=0 with C-003 and G-003;
  batch-010 unified-remediation FULL_PLAN review pending`
- final-plan user confirmation: `PENDING`

This amendment designs the batch-027 rebase and closes both findings returned
by the complete batch-009 scan. It does not authorize further source
implementation, formal testing, commit, push, deployment, or publication into
the source repository. Batch-007 remains immutable historical authority for
the completed I00 checkpoint only. Its authorization cannot cover behavior or
assets changed by batch-027. Draft.8 rebase changes remain mapped in
`UNIFIED_REMEDIATION_BATCH_005.md`; draft.9 C-001/R-003 remediation is mapped
in `UNIFIED_REMEDIATION_BATCH_006.md`; the complete draft.10 C-003/G-003
remediation is mapped in `UNIFIED_REMEDIATION_BATCH_007.md`.

## 2. Binding inputs

### 2.1 Sole requirement authority

The sole requirement authority is:

`C:\code\recorder-artifacts\tracerelay-requirement-design-v1\REQUIREMENT_DESIGN_FINAL.md`

It binds immutable snapshot:

- snapshot ID: `tracerelay-req-b027-48e1910c4369`
- manifest SHA-256:
  `9f747ab101e7e1d20a9c0c6bc7c2b736921073c71058069fc534793fe73e260e`
- review result: `PASS`
- review report SHA-256:
  `a9b394a6ab07b2b799e71b79572d7d1d88689407d3601197b303d8d9b7a8cdd7`
- user confirmation:
  `C:\code\recorder-artifacts\tracerelay-requirement-design-v1\USER_CONFIRMATION.md`

The plan must not alter the requirement files, values, classifications,
failure model, deadlines, limits, or evidence claims.

### 2.2 Codebase baseline

- repository exists and has remote
  `git@github.com:rain-123-bow/TraceRelay.git`;
- branch is `main`;
- `HEAD` does not exist;
- repository state is `UNBORN_MAIN_NO_COMMIT`;
- the exact I00 checkpoint exists as 30 files;
- all 30 files match the retained I00 source snapshot;
- the package contains no Windows substrate, runtime, service, monitor,
  coordinator, verifier implementation, or I01 test implementation;
- five packaged requirement assets, `_build_identity.json`, contract tests,
  and the source inventory still bind batch-024 and are intentionally treated
  as stale historical I00 output;
- target environment is Windows 11 x64 with CPython 3.13;
- inspected workstation version is Windows `10.0.26200`;
- inspected Python version is CPython `3.13.13`.

There is no runtime implementation, migration, public API, or compatibility
obligation beyond the confirmed requirements. Before I01, one explicit
`TR-I00R` authority-rebase checkpoint must replace the five packaged
requirement assets with exact batch-027 bytes, update build identity, contract
tests, source inventory, packaged plan schemas, and phase ownership, and retain
the old I00 evidence as batch-024 history rather than relabel it as batch-027
PASS.

### 2.3 Reasoning ledger

No project reasoning ledger or Aegis project configuration exists. The plan
uses no ledger item and cannot claim consistency with project-local historical
decisions. Every decision used by implementation is recorded in
`IMPLEMENTATION_DECISION_RECORD.md`.

### 2.4 Normative implementation schemas

The confirmed requirement snapshot directly owns `TRII/1`, `TRIC/1`,
`TRIM/1`, `TRBH/1`, `TRAD/1`, `TRAO/1`, `TRAF/1`, `TRAR/1`, and `TRFW/1`,
including
every byte layout, variant/presence row, digest domain, timestamp-applicability
rule, state table, authority path, and capacity value. `TRAS/1`, `TRR1`, and
`TRBM/1` are plan-owned formats constrained by those requirement-owned
semantics. The plan imports requirement-owned bytes and rules by immutable
snapshot identity; it does not restate or override them.

These plan-owned files freeze only choices intentionally left to the
implementation plan:

- `schemas\wire-format.v1.json`;
- `schemas\record-registry.v1.json`;
- `schemas\control-registry.v1.json`;
- `schemas\worker-registry.v1.json`;
- `schemas\persistent-state.v1.json`;
- `schemas\report-schema.v1.json`;
- `schemas\golden-vectors.v1.json`.

`SCHEMA_HASHES.json` separates two authorities:

1. the runtime schema set contains the six shipped runtime schemas and is the
   only digest written into runtime records such as `TRBM/1`;
2. the review schema set contains those six files plus
   `schemas\golden-vectors.v1.json`; that golden authority separately binds
   the corpus, manifest, tools, and evidence.

`schemas\golden-vectors.v1.json` is excluded from the runtime schema-set
digest. This removes the impossible
`TRBM -> corpus -> golden -> schema-set -> TRBM` self-hash cycle without
removing any snapshot-integrity binding. The implementation copies the six
runtime-schema bytes unchanged into package assets.
The current frozen schema bindings are:

- `SCHEMA_HASHES.json`: SHA-256
  `f5da3799ae548e8214615ab54187a218811fa00a687e99ae233a0d75e5fa8ca8`;
- six-file runtime schema set: SHA-256
  `479f9667c3e0dfab4ce8bb43f1cd62ec17fdf3bbe63106daa088c6eee0d20dcb`;
- seven-file review schema set: SHA-256
  `2c412b4b08f6780fdd697775e4c578f0317977299b1dde052409a25431f84665`;
- `schemas\golden-vectors.v1.json`: SHA-256
  `fb89ba99208aa2868d0e86aa8bd166f16247a3a9691bd709282309a9774c2218`.

Writer, verifier, and oracle are authored independently from them. No
implementation phase may invent or reinterpret a field ID, command code,
record kind, state code, transition, encoded width, maximum, report field, or
golden byte. Any change requires a new frozen plan snapshot, full independent
review, and explicit user confirmation before code changes.

`schemas\golden-vectors.v1.json` additionally hash-binds:

- `fixtures\u001-corpus.v1.bin`: `17,699,707` bytes, SHA-256
  `aa0765075a76ee84f223382314ec7186cd873cbf6bc28e7ba007a5e2675d8ef0`;
- `fixtures\u001-corpus-manifest.v1.json`: `20,562,270` bytes, SHA-256
  `062c4ef789c88b72fdf2a2811538617e87217a628c46ecdb8b4a18ceb91b5a32`;
- the manifest closes 89 vectors, six fixture-file ranges, 195 byte
  mutations, three operation mutations, 23 transitions, four TRAF-target
  relations, ten TRAO-file-reference relations, one valid TRBM bundle,
  one complete ten-frame TRBH bootstrap sequence, one mapping-header
  publication/recovery relation,
  eleven deadline identities/33 boundary cases, six external deadline
  fixtures, thirteen semantic checkers, 141 semantic assertions, 195 semantic
  probes, and six mandatory mutation categories;
- the three operation mutations reject a second witness write, prior-byte
  rewrite, and declared TRBM expected-classification metadata tampering;
- machine closure is carried by
  `required_exclusive_deadline_ids`,
  `exclusive_deadline_boundary_cases`,
  `required_semantic_checker_ids`,
  `format_semantic_check_matrix`,
  `semantic_field_probe_mutations`, and
  `mandatory_mutation_categories`;
- `tools\generate_u001_fixtures.py`: deterministic plan-authoring provenance,
  `210,625` bytes, SHA-256
  `1bb5c35b38d5257a6f52683bbe3d7820507c0dc8063bd470c8e5ec52dfb8bfbc`;
- `tools\verify_u001_fixtures.ps1`: independent PowerShell semantic decoder
  with thirteen exact format checkers and one mutated-byte classifier,
  `141,266` bytes, SHA-256
  `15b14a9c9ff5b5926414ee4912896313985f27756295cee5c3e79a60203fced9`;
- all authoritative plan scripts require PowerShell 7.x Core and are invoked
  with `pwsh`; other PowerShell editions and major versions are out of scope;
- `U001_FIXTURE_VALIDATION_RESULT.txt`: current 13-checker independent
  semantic validation `PASS` under PowerShell 7.6.0, with deterministic
  generator reproduction `PASS`;
- `U001_MUTATION_VALIDATION_RESULT.txt`: all 17 negative gates rejected,
  including the seven historical exact-set deletions, corpus-byte tampering,
  declared expected-classification tampering, mandatory-category case drift,
  and every batch-027 relation/checker/order/handle-count drift;
- `tools\validate_batch027_mutation_gates.ps1`: independently executes 17
  negative gates covering the seven historical exact-set deletions, corpus,
  classification and category tampering, the two new semantic checkers,
  deletion of the TRBH sequence or mapping-header relation, TRBH global-order
  drift, mapping-publication order drift, holder-proof ready-handle drift, and
  a byte flip in a valid TRBH frame.

These bindings and counts are recomputed by draft.10 tooling before batch-010
freeze. Author-side PASS does not authorize implementation or substitute for
the batch-010 independent full-plan review.

The generator has no random, clock, environment, or implementation-selected
input. It is forbidden from production writer, verifier, oracle, or fixture
builder imports. The independent decoder does not invoke, import, translate,
or share codec functions with it. Every valid vector reaches exactly one of
`TRII/TRIC/TRIM/TRBH/TRFW/TRAD/TRAF/TRAO/TRAS/TRR1/TRAR/TRBM` or the
mapping-header state-machine checker; generic-only
acceptance is forbidden. Every mutated result enters the same exact semantic
classifier before its observed classification, checker ID, and assertion ID
are compared with frozen expectations. I02 must independently reproduce the
frozen bytes and classifications; it chooses no fixture ID, QPC, ordinal,
body, padding, mutation offset, expected result, or golden byte.

## 3. Design objective

Implement a Windows-local forensic relay in Python whose positive claim is
strictly limited to facts committed at its proxy boundary.

The design priority is:

1. prevent false positive evidence claims;
2. stop forwarding when evidence or monitoring becomes unreliable;
3. retain committed prefixes and explicit unknowns;
4. bound every process, wait, queue, file, report, and control response;
5. preserve independent failure detection and independent verification;
6. meet the frozen performance envelope without weakening 1–5.

Throughput and latency may be sacrificed. Evidence truth, failure isolation,
and reviewability may not be sacrificed.

## 4. Candidate comparison

| Candidate | Mechanism | Strength | Blocking defect | Decision |
|---|---|---|---|---|
| A | CPython 3.13, standard library, narrow `ctypes` Win32 layer, one minimal `_winatomic` CPython C extension, multiple isolated processes | Meets the Python decision; exposes exact Windows return codes, handles, file identity, durable flush, process identity, Job control, and the aligned acquire/release atomics required by batch-027 | More low-level code; Win32 declarations and the native atomic ABI require exhaustive x64 tests and a pinned Windows build toolchain | **Selected** |
| B | CPython plus `pywin32`/`psutil` runtime dependencies | Less wrapper code for some APIs | Still needs custom APIs for CNG, ETW, file identity, alarm slots, and exact handle inheritance; creates two FFI models and native-wheel dependency | Rejected |
| C | Python CLI with Rust/C native product core | Strong type and process primitives | Moves parsing, state, storage, or process policy across a second implementation truth boundary; that product core is not required by v1 | Rejected |
| D | One Python process with threads or `asyncio` | Smallest initial codebase | Cannot satisfy separate monitor failure domain; an uncancellable kernel call can block the only supervisor; writer/verifier separation is weak | Rejected |
| E | One process per application/session | Simple ownership model | Violates one local service model and exceeds the frozen worker bound for 64 waiting sessions | Rejected |

Candidate A is selected because it is the smallest architecture that can meet
the confirmed process separation, current-runtime-context association,
durable-commit, uncancellable-call, independent-verifier, and shared-memory
atomic contracts simultaneously. `_winatomic` contains no parser, state
machine, allocation policy, storage policy, IPC policy, or business rule. It
only performs aligned 32/64-bit acquire loads, release stores, compare/exchange,
increment/decrement, and fences against already-mapped addresses. CPython and
`ctypes` cannot manufacture the requirement's hardware/compiler atomic
semantics, and the Windows DLLs inspected for this plan do not export the MSVC
Interlocked intrinsics. A native product core remains rejected; the bounded
atomic shim is a required substrate mechanism.

## 5. Architecture

### 5.1 Product entry points

The wheel exposes:

| Entry point | Responsibility |
|---|---|
| `tracerelay-start` | transient startup coordinator and sole normal startup entry |
| `tracerelay-monitor` | coordinator-launched long-lived monitor child; direct launch without exact bootstrap handles fails |
| `tracerelay-service` | coordinator-launched long-lived service child and control authority; direct launch without exact bootstrap handles fails |
| `tracerelayctl` | current-instance local control client; never prints a credential |
| `tracerelay-verify` | separate read-only bundle verifier |
| `tracerelay-reference-client` | supported client-conformance fixture |
| `tracerelay-certify` | Windows release-certification harness |

The external caller starts or confirms `tracerelay-start` before registering a
dependent application. The coordinator starts service then monitor, publishes
one bounded startup result, and exits only after operational readiness or
terminal startup failure. Service and monitor remain foreground processes
after coordinator exit. TraceRelay does not start, restart, pause, or terminate
a client or upstream.

### 5.2 Process topology

Startup boundary:

1. one transient startup coordinator;
2. one long-lived service child;
3. one long-lived monitor child.

Exactly eight prestarted worker processes:

1. monitor storage worker: post-`TRIM/1` committed-authority adoption and
   monitor journal;
2. monitor persistent-alarm worker;
3. monitor live-alarm worker;
4. service storage worker: catalog, namespaces, service journals, and audit;
5. transport worker;
6. service persistent-alarm worker;
7. service live-alarm worker;
8. maintenance worker: startup recovery, alarm query, inspect, bounded response
   serialization, and admitted deletion.

The eight-worker maximum excludes startup coordinator, service, and monitor
and includes every ordinary execution-boundary process they later create. No
per-session, per-connection, per-query, or per-deletion process exists. A
machine-readable worker registry counts process handles, roles, incarnation
IDs, start times, current operation, and termination state. Readiness fails if
the topology cannot fit inside the frozen limit.

The transient startup coordinator (`TRANSIENT_STARTUP_COORDINATOR`) performs
the requirement-owned startup protocol before any ordinary worker starts. It
is the sole execution owner of
every startup-authority `TRII/1`, `TRIC/1`, and `TRIM/1` path resolution,
create-new, explicit-offset exact-single write, flush, witness
positive-progress fill, readback, reopen, and final-handle identity operation.
It executes those operations directly through the frozen terminal-overlapped
startup primitives; no ordinary worker, mailbox, helper process, or hidden
queue participates. A deadline requests cancellation but never releases the
`OVERLAPPED`, event, buffer, or file handle before terminal completion. Any
non-positive or identity-mismatched result blocks the next allocation or
readiness gate.

The protocol is:

1. acquire the fixed current-user/logon-session initializer authority, resolve
   or create exact `TRII/1`, classify both deterministic IPC-authority paths,
   apply the complete 81-pair table, and commit exact `TRIC/1` in the
   table-selected file;
2. create one kill-on-last-handle startup Job;
3. create service first and monitor second with absolute
   `CreateProcessW.lpApplicationName`, `CREATE_SUSPENDED`,
   `EXTENDED_STARTUPINFO_PRESENT`, exact one-entry `JOB_LIST`, and exact
   two-entry `HANDLE_LIST`;
4. for each child create the command `CreatePipe` pair first and ACK pair
   second; inherit only command-read and ACK-write; clear inheritance on each
   retained endpoint and on both inherited endpoints at child entry;
5. resume both children once; complete service then monitor byte-exact
   `TRBH/1 IDENTITY_CHALLENGE/ACK`;
6. create mappings `0..3` and auto-reset initially-nonsignalled events `0..7`;
   duplicate the exact 12 object and two control handles into service, then
   monitor, with the requirement-owned masks, no inheritance, and options
   zero; complete service then monitor byte-exact
   `TRBH/1 FINAL_HANDLES_CHALLENGE/ACK`;
7. complete the entire service command-EOF, `BOOTSTRAP_CLOSED_ACK`, ACK-EOF
   sequence, then the entire monitor sequence; prove all eight steady
   bootstrap handles closed;
8. revalidate both held child identities and the exact two-member startup Job,
   then execute one `WaitForMultipleObjects(2,
   [service, monitor], FALSE, 0)`; only `WAIT_TIMEOUT` freezes the
   acknowledged 28-handle holder-proof snapshot;
9. after the proof point, drive exactly one matching `TRIM/1` write, flush,
   witness, and readback attempt to terminal outcome. Pre-proof child loss
   permits no `TRIM/1` byte. Post-proof child loss cannot cancel the attempt,
   returns `TR-START-FAILED`, permits no readiness, and retains a successfully
   committed manifest as later recovery authority;
10. after matching committed `TRIM/1`, service and monitor start and prove
    their ordinary workers, monitor issues the bound lease, service proves all
    readiness prerequisites, and only then may the coordinator report success
    and exit.

Every `TRBH/1` frame is exactly 4,096 bytes. Final frames carry the exact
3,328-byte pending `TRIM/1` inventory. The IPC-construction domain has 8 steady
bootstrap handles, a child-process-creation transient maximum of 14, a
PRE_READY maximum of 51, and a normal ready maximum of 28. The holder proof is
one logical snapshot; `TRIM/1` never asserts commit-time child liveness.

Each child receives exactly command-read and ACK-write as 16-lowercase-hex-digit
raw-handle arguments. `lpApplicationName` is the exact absolute executable
path; `bInheritHandles=TRUE`; standard handles are disabled; unrestricted
inheritance, pipe `DuplicateHandle`, post-create Job assignment, breakaway, and
retry after `CreateProcessW` are forbidden. The child rejects zero, invalid,
duplicate, malformed, or role-mismatched handles before role code. Parent
retained endpoints have inheritance cleared immediately. After creation the
parent proves Job membership, closes its child-end copies, resumes the primary
thread exactly once with return `1`, and closes the thread handle.

The four identity/final challenges are nonzero, mutually distinct 32-byte
Windows-CSPRNG values. `TRBH/1` binds kind, phase, child role, fixed counts,
planned IPC/child/coordinator/Job incarnations, challenge, PID, logon session,
held process-creation identity, exact profile/catalog hashes, installation,
boot, and `TRIC/1` digest. Bytes `320..3647` are the exact pending inventory;
bytes `3648..4095` are zero. Any post-ACK inventory-byte change prohibits
`TRIM/1`.

Ordinary workers start only after matching committed `TRIM/1`. They inherit
startup-Job membership from their owner process and cannot use
`CREATE_BREAKAWAY_FROM_JOB`. Each is created suspended with an exact
role-specific handle list, then the owner validates executable identity,
process creation identity, current logon-session ID, inherited-handle
manifest, and current Job membership before one resume. Worker bootstrap uses
a separate plan-owned mailbox protocol; it does not reuse `TRBH/1` and does
not add an alarm-IPC mapping/event/manifest holder. The four alarm-worker roles
that mutate `TRAS/1` slots are bounded in-process state machines in the service
or monitor holder; potentially blocking calls are delegated to the matching
ordinary execution-boundary process.

Each ordinary worker:

- has a fresh worker-incarnation ID;
- proves parent PID, held process-creation identity, current logon-session ID,
  and one-use bootstrap challenge;
- exposes bounded progress frames;
- owns only the handles required for its role;
- is waited by process handle, never PID alone.

Attribute-list creation failure, process-creation failure, membership mismatch,
parent death before resume, bootstrap timeout, or handle-manifest mismatch
fails readiness. No child can execute role code before Job membership and
handle proofs. Job close or `TerminateProcess` is only a kill request;
signalled process handle plus exclusive-resource reopen is the release proof.

If cancellation is requested, the coordinator still treats physical
completion as unknown until the worker process handle is signaled and every
exclusive resource can be reopened. Failure to prove release selects
`TR-INCOMPLETE-WORKER-TERMINATION-UNCONFIRMED` and blocks new sessions.

### 5.3 Responsibility boundaries

Service supervisor:

- owns the mutable installation, catalog, application, registration, session,
  deletion, and ACTIVE projections after bootstrap;
- serializes race priority;
- owns control dispatch and public-result selection;
- manages bounded buffers and worker grants;
- never performs a potentially unbounded filesystem or destination write.

Monitor coordinator:

- owns service process-handle observation;
- owns monitor incarnation and lease decisions;
- adopts already committed installation and IPC authority only after matching
  `TRIM/1`, delegating post-`TRIM/1` adoption and monitor-journal calls to its
  storage worker;
- independently publishes service-failure alarms;
- never depends on the service process for its alarm dispatch.

Transient startup coordinator:

- is the sole state and OS-call owner for the frozen `TRII/1`, `TRIC/1`, and
  `TRIM/1` startup-authority operations listed in section 5.2;
- performs no service, monitor, transport, alarm, session, query, deletion, or
  post-readiness storage work;
- retains each authoritative I/O resource until terminal completion and cannot
  cross the matching Job/child/IPC/readiness gate after failure.

Storage workers:

- own their declared authoritative append and namespace handles;
- begin only after matching committed `TRIM/1`; therefore they never create,
  write, flush, witness, read back, reopen, or decide `TRII/1`, `TRIC/1`, or
  `TRIM/1`;
- accept only typed, one-use append requests;
- return exact Windows status, committed sequence, byte position, and digest;
- never decide product state or public outcomes.

Transport worker:

- owns waiting loopback listeners and the one active socket pair;
- performs bounded hello parsing and reports candidate facts;
- enters a destination write only after receiving a committed one-use grant;
- returns the exact `send` count or Windows error;
- never selects lifecycle or verifier results.

Alarm workers:

- receive the same immutable alarm envelope independently;
- have separate fixed shared-memory in-place slot mappings, event handles,
  process handles, endpoints, storage handles, progress, and result paths;
- cannot wait on, reserve through, or call the other channel.

Verifier:

- imports no runtime writer, service, monitor, alarm, deletion, or control
  implementation module;
- opens one absolute bundle read-only with no-share-delete handles;
- streams within the 512 MiB memory bound;
- performs total classification without modifying evidence.

### 5.4 Operation-to-execution boundary

| Operation family | Owner | Worker | Queue and priority | Deadline/failure rule |
|---|---|---|---|---|
| `TRII/1` resolve/create-new, exact-single write, flush, witness, readback/reopen, final identity | transient startup coordinator | direct frozen terminal-overlapped startup primitive; no ordinary worker or mailbox | one deterministic two-attempt decision before Job/child/IPC creation | deadline requests cancellation; resources remain retained through terminal completion; any non-positive/mismatch blocks allocation and readiness |
| `TRIC/1` resolve/create-new, exact-single write, flush, witness, readback/reopen, final identity | transient startup coordinator | direct frozen terminal-overlapped startup primitive; no ordinary worker or mailbox | one deterministic two-path/81-pair resolution before Job/child/IPC creation; at most one create-new action executes at a time; `a1` is created only in the two exact `CREATE_A1` cells | same terminal ownership; any non-positive/mismatch blocks allocation and readiness; exactly one committed attempt file is selected |
| `TRIM/1` exact-single write, flush, witness, readback/reopen, final identity | transient startup coordinator | direct frozen terminal-overlapped startup primitive; no ordinary worker or mailbox | exactly one append attempt to the selected committed `TRIC/1` file after holder proof; cannot be cancelled by post-proof child loss | terminal result is mandatory; failure blocks readiness while a successful commit remains recovery authority |
| `INSTALLATION_AUTHORITY_ADOPTION`, monitor session journal, and session-unknown observations | monitor coordinator | monitor storage | post-`TRIM/1` only; one in-flight; terminal/timeout observation before health append | no startup-authority record access; failure degrades alarm evidence and triggers fail-closed state |
| monitor persistent alarm | monitor coordinator | monitor persistent alarm | independent two-slot in-place mapping | full/worker/storage failure returns its channel outcome without waiting for live |
| monitor live alarm | monitor coordinator | monitor live alarm | independent 1,024-slot in-place mapping | full/worker/endpoint failure returns its channel outcome without waiting for persistent |
| catalog append, session namespace, service/session journal, deletion audit | service supervisor | service storage | one in-flight; terminal and already-reserved audit outcome before ordinary mutation | timeout poisons worker, stops forwarding, and blocks mutation until release proof |
| listener/auth/connect/read/write/half-close | service supervisor | transport | one in-flight command per active direction; no hidden backlog | deadline isolates worker; unknown call result is never replayed |
| service persistent alarm | service supervisor | service persistent alarm | independent two-slot in-place mapping | same independent-channel rule as monitor |
| service live alarm | service supervisor | service live alarm | independent 1,024-slot in-place mapping | same independent-channel rule as monitor |
| recovery scan, alarm query, inspect, large response encoding, deletion | service supervisor | maintenance | one in-flight, no general queue; recovery before readiness, admitted deletion before query/inspect | busy returns the exact non-positive catalog tuple; timeout poisons worker; deletion can become `DELETE_UNKNOWN` |

The long-lived service supervisor and monitor coordinator perform bounded
validation, state locking, timer decisions, slot reservation, and selector
evaluation only. They never call a potentially blocking filesystem, socket,
pipe-write, response-serialization, or deletion operation. The sole coordinator
exception is the transient startup coordinator, which directly performs only
the frozen bounded terminal-overlapped `TRII/1`, `TRIC/1`, and `TRIM/1`
operations above and retains their resources through terminal completion.
Ordinary workers have one command/result mailbox and no user-space backlog. A
busy worker rejects new work; no coordinator waits for queue space.
Alarm mappings are the only multi-entry queues. Each persistent mapping has
exactly `alarm_ipc_limits.persistent_slots_per_worker=2` slots. Each live
mapping has exactly `alarm_ipc_limits.live_slots_per_worker=1024` slots. A
result replaces its command in the same pinned slot; no result ring exists.

Every alarm IPC resource is frozen:

- mapping header: 32 bytes before slot zero;
- slot prefix: 256 schema bytes;
- inline payload: `alarm_ipc_limits.max_inline_payload_bytes=4,096`;
- slot total: `alarm_ipc_limits.slot_bytes=4,352` bytes;
- two persistent mappings:
  `2 × (32 + 2 × 4,352) = 17,472` bytes;
- two live mappings:
  `2 × (32 + 1,024 × 4,352) = 8,912,960` bytes;
- aggregate: 4 mappings, 8 events, 8,930,432 mapping bytes;
- ready manifest: 24 cross-process object-handle entries, 4 control-handle
  entries, and 28 total ready-handle entries;
- child-process-creation transient maximum: 14 handle entries;
- pre-ready creation maximum: 51 handle entries;
- current-runtime-context concurrent IPC-incarnation maximum: 1.

Each mapping header uses the exact requirement-owned aligned atomic fields:
`freeze_state@0`, zero reserved word at 4, `freeze_generation@8`,
`active_transition_count@16`, and `snapshot_sequence@24`. Slot `i` begins at
`32 + i * 4,352`. Normal mutation increments the active count, rejects any
nonzero generation or non-`RUNNING` state, acquires an even sequence as odd,
rechecks freeze ownership, performs at most one aligned slot-state
compare-exchange, publishes the next even sequence, then decrements the count.
Recovery first owns the deterministic nonzero generation, changes
`RUNNING -> FREEZE_REQUESTED`, waits for zero active transitions and an even
sequence, records the stable slot snapshot, then irreversibly changes to
`FROZEN`. Count/odd-sequence normalization is allowed only after every possible
mutator is proven `EXITED` or `IDENTITY_ABSENT`; slot state is never
synthesized or rolled back.

All terms above are owned by semantically matching `alarm_ipc_limits` keys;
`max_worker_processes` authorizes only process count. All mappings/events exist
before readiness. No alarm dispatch allocates a mapping, slot, queue, event, or
payload buffer. A full persistent mapping commits
`PREDISPATCH_FAILED_LIMIT/FAILED_LIMIT`; a full live mapping commits
`PREDISPATCH_FAILED_LIMIT/FAILED`. Both attempt the peer channel immediately.
Mappings contain slots only. The coordinator claims the lowest empty index;
each worker performs one bounded scan and processes ready slots by alarm
sequence then slot index. At most four persistent file references and 262,144
referenced-record bytes may remain pinned across all slots.

Within a shared storage worker, terminal/closure work already covered by a
committed reserve outranks catalog mutation and ordinary append. There is still
exactly one in-flight OS call; priority selects only the next command after the
current call returns. A timed-out call poisons that worker rather than allowing
later work to overtake an unknown resource owner.

### 5.5 Component flow

```text
external launcher
    | starts/observes
    +--> transient startup coordinator
            | exact TRII/TRIC/TRBH/TRIM bootstrap
            +--> service supervisor --> service storage worker
            |          |              +-> transport worker <-> client/upstream TCP
            |          |              +-> persistent alarm execution worker
            |          |              +-> live alarm execution worker
            |          |              +-> maintenance worker
            |          |
            |          +<-----------> monitor current-context local IPC
            |
            +--> monitor coordinator --> monitor storage worker
                       |              +-> persistent alarm execution worker
                       +--------------+-> live alarm execution worker

one copied session bundle --> independent verifier --> bounded report + exit
```

## 6. Windows substrate

### 6.1 FFI and atomic-shim policy

The runtime has no third-party runtime dependency. A narrow
`tracerelay.platform.windows` package wraps only required Win32 functions.
One compiled `tracerelay._winatomic` extension supplies only the batch-027
mapping-header atomic primitives.

Every `ctypes` declaration must:

- use `ctypes.WinDLL(..., use_last_error=True)`;
- declare `argtypes` and `restype`;
- use pointer-width-safe handle types;
- check every applicable return value before reading output;
- copy `GetLastError` immediately when the API contract makes it meaningful;
- convert no error into success;
- close every owned handle through one idempotent owner object;
- expose raw Windows status in internal evidence without leaking a session
  credential or application payload;
- assert required x64 structure size and alignment before the first call.

Each wrapper has a machine-readable applicability row:

- `APPLICABLE`: real Windows success plus every reachable returned-error,
  boundary, timeout, cancellation, and invalid-input/invalid-handle class;
- `N/A`: a class that the Win32 API cannot represent or the product cannot
  reach, with a documentation anchor and static proof;
- `SUBSTITUTE`: a deterministic harness supplies the otherwise unreachable
  kernel result and the release gate separately proves the real success path.

An unclassified row fails I01. This prevents the impossible blanket demand that
every API expose the same invalid-handle/error surface while retaining complete
coverage of every reachable result. No Win32 handle is represented by a bare
Python integer outside the FFI boundary.

`_winatomic` accepts only writable, aligned, in-range addresses owned by a live
mapped-view object. Each call accepts `(writable_contiguous_buffer, offset,
...)`, acquires one `Py_buffer`, validates `offset + width <= len` and actual
address alignment, performs one intrinsic, releases the view, and returns only
fixed-width integers/booleans. The GIL remains held; cross-process atomicity
comes from the aligned interlocked operation, not the GIL. The extension calls
no Python callback and allocates no product state.

Exact exported ABI:

| Function | Width | Contract |
|---|---:|---|
| `load_u32_acquire`, `load_u64_acquire` | 32/64 | acquire load |
| `store_u32_release`, `store_u64_release` | 32/64 | release store |
| `compare_exchange_u32_acq_rel`, `compare_exchange_u64_acq_rel` | 32/64 | return observed value and success |
| `increment_u64_acq_rel` | 64 | return post-increment value; overflow is fatal before mutation |
| `decrement_u64_release` | 64 | return post-decrement value; zero underflow is fatal before mutation |
| `full_fence` | n/a | compiler/CPU full fence for requirement-owned proof points |

MSVC full-fence Interlocked intrinsics are allowed to provide ordering stronger
than the required acquire/release semantics. Import freezes an ABI version,
CPython 3.13, Windows x64, unsigned widths, and extension self-test. An ABI,
alignment, range, architecture, overflow, or underflow mismatch blocks startup
before mapping use.

### 6.2 Required Windows APIs

The plan uses these API families:

- CNG: `BCryptGenRandom`, `BCryptOpenAlgorithmProvider` with
  `BCRYPT_ALG_HANDLE_HMAC_FLAG`, `BCryptCreateHash`, `BCryptHashData`,
  `BCryptFinishHash`, `BCryptDestroyHash`, and
  `BCryptCloseAlgorithmProvider`;
- files: `CreateFileW`, `ReadFile`, `WriteFile`, `FlushFileBuffers`,
  `GetOverlappedResultEx`, `CancelIoEx`,
  `GetFileInformationByHandleEx`, `GetFinalPathNameByHandleW`,
  `GetVolumeInformationW`, `GetDiskFreeSpaceExW`, and
  `GetDriveTypeW`;
- product-tree structure inspection: `FILE_FLAG_OPEN_REPARSE_POINT`,
  `FSCTL_GET_REPARSE_POINT`;
- current-context attribution: process/thread token APIs,
  `GetTokenInformation`, `ConvertSidToStringSidW`, and
  `ProcessIdToSessionId`;
- IPC: `CreateNamedPipeW`, `ConnectNamedPipe`, `GetNamedPipeClientProcessId`,
  `CreatePipe`, `SetHandleInformation`, `DuplicateHandle`,
  `ImpersonateNamedPipeClient`, and `RevertToSelf`;
- singleton/process: `CreateMutexExW`, `OpenMutexW`, `OpenProcess`,
  `GetProcessTimes`, `CreateProcessW`, `InitializeProcThreadAttributeList`,
  `UpdateProcThreadAttribute`, `DeleteProcThreadAttributeList`,
  `ResumeThread`, `WaitForSingleObject`, and `WaitForMultipleObjects`;
- containment: Job Object create/configure/terminate/query APIs,
  `PROC_THREAD_ATTRIBUTE_JOB_LIST`, and
  `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`;
- shared command transport: `CreateFileMappingW`, `MapViewOfFile`,
  `UnmapViewOfFile`, `CreateEventW`, `SetEvent`, `ResetEvent`,
  `NtQueryObject`, and `_winatomic` acquire/release transitions;
- timing: `QueryPerformanceCounter`, `QueryPerformanceFrequency`;
- certification: `GetSystemTimes`, `GetActiveProcessorCount`, ETW kernel
  `DiskIo` consumer APIs.

Official API behavior is an implementation input, not an expansion of the
product claim. `CancelIoEx` only requests cancellation. A retained
`OVERLAPPED`, event, buffer, and file handle remain owned until
`GetOverlappedResultEx` reports terminal completion or the isolated owner
process is observed terminated and exclusive resource release is proven.

### 6.3 Path and principal rules

The operator selects three existing absolute roots before first start:
evidence, alarm, and installation runtime. They are pairwise distinct and
non-nested. Each normally resolved final directory handle must prove writable
local fixed-disk NTFS, canonical final path, volume serial, file ID, and
required access. A path may traverse a reparse component. TraceRelay makes no
claim against a malicious concurrent path race. The product-created `_runtime`
tree rejects any unexpected reparse object as a structural conflict.

These three-root runtime-admission rules do not govern `tracerelay-verify`.
Verifier input has the separate read-only preflight contract in section 11.2.

First coordinator start:

1. derives the current user SID and current logon-session ID, acquires the
   session-local initializer authority, and validates the strict bootstrap
   object;
2. resolves the three final root handles, rejects nesting, aliasing,
   final-target escape/identity change, non-local/non-NTFS targets, or missing
   write access;
3. creates the deterministic installation-authority path under the runtime
   root and commits one exact `TRII/1` in one of its two create-new attempts;
4. validates canonical final identities, runtime-context attribution,
   evidence/alarm roots, and exact profile/catalog/schema/source/package
   identities;
5. resolves the complete six-state, 36-pair `TRII/1` table and commits exact
   sequence-zero `TRIC/1` before creating any Job, child, mapping, event,
   duplicated handle, or ordinary worker;
6. executes the exact coordinator protocol in section 5.2; readiness follows
   only committed `TRIM/1`, holder proof, current child liveness, ordinary
   worker proofs, and a valid monitor lease.

The first start command is:

`tracerelay-start --bootstrap-config <absolute-json-path>`

The strict bootstrap object contains evidence root, alarm root, installation
runtime root, and exact contract/profile identifiers. User SID and
logon-session ID are derived from the running process and cannot be supplied.
After `TRII/1` commits, its
installation identity, root identities, and digest are immutable startup
authority. The monitor never mutates application,
registration, session, deletion, or service catalog state. The service
validates and adopts the anchor, then owns all later mutable installation
projections. A later bootstrap file is either byte-equivalent
after strict canonical validation or start fails with `TR-START-FAILED`.
`tracerelay-service` accepts no root, user, product-name, or singleton-name
override.

Later starts use only the committed anchor. Caller-supplied identity, display
name, install path, executable path, or root cannot create a second authority.
Changing runtime context or roots is reinstall: all TraceRelay processes stop, a new
empty runtime root is selected, and old authority remains historical. No
running product merges, rewrites, repairs, or automatically removes it.

All three roots:

- are absolute operator-selected paths committed on first start;
- are pairwise distinct, non-nested, and non-aliasing by file identity;
- are local fixed-disk NTFS;
- permit normal Windows path resolution through reparse components;
- rely on default Windows access control;
- are held by canonical directory handles during runtime;
- are revalidated by final identity before readiness, admission, deletion, and
  recovery.

Singleton names and authority live in the current user/logon-session context.
At most one service and one ACTIVE session are claimed per supported runtime
context. Cross-user and cross-session exclusion is neither implemented nor
claimed. Owner SID remains an immutable `TRII/1` attribution and installation
identity input; it is not a hostile-user authorization boundary.

## 7. IPC and control

### 7.1 Named-pipe endpoints

Fixed endpoints:

- `\\.\pipe\TraceRelay.v1.monitor.control`;
- `\\.\pipe\TraceRelay.v1.service.control`;
- publisher-owned service and monitor live-alarm endpoints containing only
  committed installation/incarnation IDs, never caller names.

Each pipe:

- is local only;
- uses default Windows access control;
- has bounded instances and frame sizes from the support profile;
- associates the peer with the committed installation, current logon session,
  held peer process, creation identity, incarnation, challenge, and request
  replay state;
- binds `GetNamedPipeClientProcessId`, process creation time, and process
  handle where the contract requires process identity;
- uses a fresh per-connection challenge and one request ID;
- rejects absent, replayed, wrong-incarnation, extra-field, oversize, and
  deadline-late frames before dispatch.

No custom DACL, cross-user denial, or hostile-user security claim is part of
v1. A runtime-context mismatch remains a functional association failure and
selects the exact catalog result.

### 7.2 `TRCP/1` control frame

Control is a canonical binary protocol, not pickle and not credential-bearing
JSON.

Frame properties:

- fixed magic and major/minor version;
- unsigned little-endian fixed-width header;
- declared total length checked before allocation;
- frame kind and command code;
- request UUID and service/monitor incarnation UUID;
- one-use connection challenge;
- ordered typed fields with unique numeric field IDs;
- no unknown required field, duplicate field, trailing bytes, float, or
  implicit default;
- complete-frame SHA-256;
- maximum request and response bytes enforced before body read/write.

Typed fields are `U8`, `U16`, `U32`, `U64`, `BOOL`, `UUID16`, `BYTES`, and
strict UTF-8/ASCII identifier fields. No recursive object exists in v1.

The control CLI converts non-secret responses to stable JSON for stdout.
Registration credentials are never printed or intentionally persisted. A
registration call is available through the shipped Python control-client
context object or through a caller-created inherited anonymous pipe verified
as `FILE_TYPE_PIPE`. Console and disk sinks are rejected before registration
dispatch as `TR-CONTROL-INVALID-REQUEST`. The returned credential is one
43-byte base64url value backed by an ordinary bounded mutable buffer. The
buffer is released after the transfer decision; v1 makes no zeroization,
locked-memory, dump-resistance, or local-adversary secrecy claim.

### 7.3 Public-outcome selector

The exact embedded reason catalog is parsed by a dedicated closed grammar.
The implementation:

1. binds catalog bytes and hash;
2. validates construction invariants;
3. normalizes exactly nine facts;
4. performs the frozen eight-step selector;
5. immediately returns the first eligible rule;
6. emits one public reason.

The product evaluator, verifier catalog reader, and test oracle share no
parser, matcher, normalization, or selector function. The 30 patterns, 58
positive tuples, substitutions, overlaps, malformed facts, and dispatch
composition are regenerated from exact catalog bytes and compared.

## 8. Canonical evidence format

### 8.1 Fixed bundle layout

Each session directory is create-new and contains exactly five physical files:

```text
bundle.trm
support-profile.windows-local-v1.json
reason-exit-catalog.v1.json
service.trj
monitor.trj
```

Alarm-publication observations are exact requirement-owned `TRAO/1` records
inside `service.trj` or `monitor.trj`; linkage, exact copied persistent bodies,
and version bindings follow the closed `TRAO/1` variant/presence rules.
No mutable side file is authoritative. Extra file, alternate data stream,
reparse object, duplicate physical role, or unlisted directory entry is
invalid.

`bundle.trm` is an immutable canonical binary manifest. It binds:

- logical bundle, installation, session, schema, serialization, digest,
  transport, service-incarnation, and monitor-incarnation identities;
- origin canonical path and origin Windows volume/file IDs as advisory origin
  facts;
- four non-manifest physical-file entries: embedded profile, embedded catalog,
  service journal, and monitor journal;
- a seven-entry logical-role table covering six required roles: the four whole
  physical files, `TRAO/1` variants 1–9 selected from both journals, and alarm
  linkage selected as plan-owned kind 409 from `service.trj`;
- exact profile and catalog bytes, versions, and hashes;
- package/source identity.

The manifest itself is the fifth physical file. A logical-role selector names
one listed physical role and either the whole file or sorted inclusive
record-kind ranges. Exact duplicate selectors, overlapping ranges, a selector
for an unauthorized journal role, an unknown kind, or omission of any of the
six logical roles is invalid. Logical roles never imply additional physical
files.

Relocation changes no bound logical fact. Current path/file ID is checked only
for containment and duplicate identity, never compared to origin for PASS.

### 8.2 `tracerelay-record-v1`

Authoritative journals use one documented binary envelope:

1. immutable file prologue;
2. zero or more complete records;
3. optional retained partial tail.

Plan-owned non-fixed-format record envelope:

- `TRR1` magic;
- schema major/minor;
- total length and header length;
- role and record-kind numeric IDs;
- flags fixed to declared bits;
- sequence `u64`;
- only the record-kind-applicable QPC ticks and frequency `u64`; absent
  kind-inapplicable time slots are zero;
- no UTC, wall-clock observation, or universal observation-time field;
- payload length `u32`;
- previous-record SHA-256;
- payload SHA-256;
- canonical typed payload;
- record SHA-256 with domain separation;
- fixed `TRC1` trailer containing sequence, total length, and pre-witness
  digest;
- one exact 44-byte `TRFW/1` post-flush witness filled once after the
  pre-witness bytes flush.

All integers are unsigned little-endian. No float exists. Payload fields are
strictly increasing unique `u16` field IDs with explicit type and `u32`
length. Raw application payload is a direct `BYTES` field; it is never
base64-encoded or normalized. Each record kind has a frozen required/allowed
field table in a machine-readable schema.

Digest:

```text
SHA256(
  "TraceRelay.Record.v1\0"
  || complete canonical header excluding record_digest and trailer
  || canonical payload
)
```

The previous-record digest is inside the digested header. Sequence zero uses
32 zero bytes. The trailer repeats enough identity to reject a copied or
misplaced trailer.

The requirement-owned fixed formats are never wrapped in `TRR1`. `TRII/1`,
`TRIC/1`, `TRIM/1`, `TRAO/1`, and `TRAR/1` are complete records with their
own exact prefix/body/trailer/witness layouts. `TRAD/1` is always the exact
512-byte inline dispatch command. `TRAF/1` is always the exact 512-byte
persistent reference and is never itself journal authority. Numeric kinds
402–408 are withdrawn; `TRAO/1` magic plus variant 1–9 is the sole alarm
observation record-kind authority.

The only wall-clock-derived authoritative value is
`PROCESS_CREATION_IDENTITY_FILETIME`, obtained from `GetProcessTimes` on the
exact held process handle. It appears only in the exact `TRIM/1`, applicable
`TRAR/1`, and host-certification identity fields. It is an opaque PID-reuse
discriminator; ordering, duration, deadline, liveness, QPC conversion, UTC
observation, and display uses are forbidden.

### 8.3 Durable append

An append worker:

1. validates role, state-issued grant, next sequence, previous digest, record
   size, session/root reservation, and closure reserve;
2. serializes into a bounded mutable buffer;
3. opens the create-new authoritative file with
   `GENERIC_READ|GENERIC_WRITE`, share mode zero, and never treats current file
   position as authority;
4. writes the complete pre-witness record at one explicit validated offset
   through one ordinary exact-single-write operation with an initially
   nonsignalled auto-reset event;
5. retains `OVERLAPPED`, event, buffer, and file handle until
   `GetOverlappedResultEx` proves terminal completion; a positive short return,
   zero, error, or exclusive deadline terminally poisons the attempt, permits
   no suffix retry and no later record in that file;
6. calls `FlushFileBuffers` and requires its successful return;
7. fills the reserved `TRFW/1` block once in strictly ascending byte order
   using the separate witness positive-progress primitive, at most 44 positive
   writes, then performs exact readback;
8. computes the full-witness record digest only after valid readback and never
   rewrites a witness byte or any earlier byte;
9. returns sequence, byte position, pre-witness/full-witness digests, raw
   Windows status, and worker incarnation;
10. releases ordinary transient credential buffers without writing them to
    evidence, logs, or disk;
11. never truncates, repairs, resumes, replaces, or retries an uncertain
   record.

A crash or error leaves the bytes as a partial tail. No old session journal is
opened for append after restart.

There are three separate I/O primitives and no generic journal `write_all`:

1. ordinary authoritative pre-witness write: exactly one full-count completion;
2. witness fill: positive-progress loop bounded by 44 writes;
3. `TRBH/1` bootstrap pipe frame: positive chunks accumulated to exactly 4,096
   bytes; zero, error, early EOF, excess, or deadline is failure.

For all three, `CancelIoEx` is a cancellation request only. Resources remain
owned until terminal completion or isolated-process termination plus release
proof. Post-holder-proof peer loss cannot propagate a generic cancellation
token into the unique `TRIM/1` commit attempt.

Installation metadata and deletion audit use create-new chained segment files.
A new service incarnation may create a new segment referring to the last valid
committed prefix; it never appends behind a prior partial tail.

### 8.4 Writer/verifier/oracle separation

Three independent implementations consume the same written specification:

| Implementation | Location | Allowed imports |
|---|---|---|
| production writer | `src/tracerelay/runtime/journal/` | Windows substrate and writer schema constants |
| production verifier | `src/tracerelay/verifier/` | read-only Windows substrate and verifier-owned schema parser |
| test oracle | `tests/oracle/` | standard library only; no production package import |

They may consume exact machine-readable schema bytes. They may not share
serialization, digest, parser, state-transition, recovery, range-accounting,
selector, or classification functions. Static import/AST tests enforce this.

## 9. State and data-plane implementation

### 9.1 Installation and application state

The installation runtime root contains only the exact bounded installation and
IPC authority trees:

```text
TRII/1 installation-authority attempts
TRIC/1 + TRIM/1 IPC-authority attempts
```

Mutable catalog segments remain separately quota-bound authoritative evidence;
they are not charged to the runtime-root maxima. They durably record:

- application create/disable;
- registration/session allocation and lifecycle;
- credential lifecycle facts without plaintext, key, candidate, or comparison
  material;
- service/monitor incarnation bindings;
- asynchronous deletion operation state;
- installation readiness degradation;
- selected runtime-root, `TRII/1`, IPC-intent/manifest, and recovery bindings.

The exact entity fields, numeric state codes, transitions, race order, counters,
append authority, selector facts, tombstones, segment rollover, and recovery
order are frozen by `schemas\persistent-state.v1.json`. The exact persistent
record kinds and required/allowed field IDs are frozen by
`schemas\record-registry.v1.json`.

One atomic state-lock decision applies this exact descending priority:
evidence-commit failure; monitor lease/critical failure; forced service stop;
transport error/resource deadline; authorized revoke/close; maximum session
duration; bilateral clean EOF; activation expiry; completed authentication
decision. A valid claim is one result inside the last item. It is not a
separate priority. Expiry cannot run from `CREATING`; its anchor exists only
after `CREDENTIAL_ISSUED`.

Every durable transition schema entry names the pre/post state, one record and
writer, counter changes, race winner, reason, selector operation, and recovery
rule. Registration `EXPIRED`, `REVOKED`, and `CLAIMED` each have an explicit
`REGISTRATION_TERMINALIZED` commit to `TERMINAL`. Clean close is exactly:
service `CLEAN_CANDIDATE`; monitor `NO_FAILURE_OBSERVED`; service
`TERMINAL_CLEAN`, all under one continuously valid lease. A missing step is
never synthesized by recovery.

One lazy catalog segment is created per service incarnation. A segment begins
with a nonzero committed prologue and binds the preceding committed segment
digest. Clean rollover requires `CATALOG_SEGMENT_SEALED`; a partial tail is
retained, charged, and never reused. A crash after create-new but before
prologue commit leaves one zero-byte poison sentinel at the single expected
next path. That sentinel blocks further catalog mutation and prevents creation
of another candidate, bounding the orphan count at one until explicit operator
repair outside the running product.

The service rebuilds state only from valid committed prefixes. It applies
tombstones instead of erasing history. Contradiction, over-limit counters,
unexpected segment index, invalid seal/link, poison sentinel, or partial tail
in the current incarnation fails readiness. Recovery of an older partial tail
can create a new incarnation segment only after the old prefix is classified
read-only and all exclusive resources are proven released.

### 9.2 Credentials

Before readiness, the service allocates a bounded ordinary in-process
credential table with at most 64 entries. Each entry contains only irreversible
comparison material plus session, registration, service-incarnation, deadline,
and lifecycle facts. It contains no plaintext credential.

Credential issuance:

1. fill one 32-byte mutable raw buffer directly with `BCryptGenRandom` and
   `BCRYPT_USE_SYSTEM_PREFERRED_RNG`;
2. encode exactly 43 base64url ASCII bytes without padding;
3. derive and retain only fixed-length irreversible comparison material bound
   to the service incarnation and session;
4. commit only session/incarnation/deadline/lifecycle facts;
5. return the encoded buffer once through the protected control response;
6. release raw, encoded, and scratch buffers after the transfer decision.

Authentication validates exact length, encoding, session, incarnation, state,
exclusive deadline, replay, revocation, and claim status before comparing the
derived material. A terminal transition removes its comparison entry. Abrupt
or orderly service exit discards the table; restart creates a new service
incarnation and all earlier credentials fail. Plaintext is not intentionally
persisted or logged. Locked memory, forced zeroization timing,
constant-time/local-memory inspection guarantees, anti-dump behavior, and WER
hardening are outside the confirmed v1 claim.

### 9.3 Session creation

Before credential issuance:

1. under the installation state lock, admit one waiting-session counter and a
   `session_closure_reserve_bytes=33,554,432` logical reservation;
2. allocate IDs using Windows CSPRNG and commit
   `REGISTRATION_CREATE_INTENT` before filesystem creation;
3. create a unique session directory with create-new semantics;
4. create manifest, profile, catalog, and service journal;
5. ask the authenticated monitor to create and hold `monitor.trj`;
6. flush and reopen every file by identity;
7. verify role, canonical final path, volume/file identity, required access,
   and exact contract hashes;
8. commit `SESSION_CREATED`;
9. populate one comparison-material entry and commit `CREDENTIAL_ISSUED` with the
   monotonic deadline in the session journal;
10. commit `REGISTRATION_CREATED` in the installation catalog;
11. return endpoint and one-time credential.

Any failure closes the candidate namespace as incomplete or abandoned and
never reuses it. Catalog intent, created path, committed bytes, logical reserve,
and directory-entry count remain charged and recoverable.

Sixty-four waiting sessions reserve exactly 2 GiB of closure capacity, remain
inside the 32 GiB evidence-root quota, and hold no full-session reservation.
The 65th fails before creating a path.

The valid-credential decision is the exact ACTIVE admission point. While
holding the state lock and before session-journal claim copy, upstream connect,
`OK`, source read, or payload forwarding, the supervisor:

1. validates credential, expiry/revocation, current monitor lease, serialized
   race winner, and one available current-runtime-context ACTIVE slot;
2. atomically upgrades the winning waiting reservation to the 6 GiB session
   evidence reservation and proves the 5 GiB physical free-space reserve;
3. commits `CREDENTIAL_CLAIMED_ACTIVE_RESERVED` in the installation catalog.

That single catalog commit is the irreversible credential claim, ACTIVE-slot,
and capacity authority. Commit failure leaves no claim and permits no upstream
call. After commit, no rollback to `ISSUED` or `WAITING` exists. The supervisor
copies the claim into the session journal; copy, connect, or later failure
closes the session incomplete. Recovery releases the old logical ACTIVE
reservation only by a new `RECOVERY_ACTIVE_RESERVATION_RELEASED` catalog record
after the old bundle is classified read-only and worker/socket/file release is
proven.

### 9.4 Transport

The transport worker manages up to 64 WAITING loopback listeners and one
authenticated ACTIVE pair through bounded nonblocking readiness polling.

Waiting-session authoritative files are not kept open. The writer reopens one
requested journal by stored canonical path plus volume/file ID, validates its
role and committed prefix, performs one bounded append, and closes it.
Only active capture, current control mutation, alarm, installation segment,
and deletion audit handles remain open. Static accounting proves their maximum
is at most `max_open_authoritative_handles=64`.

Per attempt:

1. accept one loopback TCP connection;
2. commit attempt count and `AUTH_ATTEMPT_STARTED`;
3. read at most 512 authentication bytes by the exclusive deadline;
4. reject early payload, malformed framing, wrong identity, expiry, replay,
   revocation, or concurrent authentication before upstream connect;
5. send the candidate facts to the supervisor;
6. supervisor performs the catalog claim/ACTIVE/capacity commit described in
   section 9.3;
7. service storage worker commits the session-journal claim copy and
   `CONNECTING_UPSTREAM`;
8. worker connects exactly once to the registered `127.0.0.1:port`;
9. commit `CONNECTION_ACTIVE`;
10. only then send `OK`.

Payload path per direction:

1. one source read returns at most 65,536 bytes;
2. worker sends exact bytes and source offset to supervisor;
3. service journal worker commits `DATA_INTENT`;
4. no destination call begins until the commit result is validated;
5. when destination is writable, service journal worker commits one
   `WRITE_ATTEMPT`;
6. supervisor sends the exact one-use grant to the bound transport worker;
7. worker enters one destination `send`;
8. exact positive count, known zero/error, or absence of outcome is committed;
9. short-write continuation starts only at the first unaccepted suffix;
10. unknown outcome stops all forwarding and is never replayed.

At most one coalesced chunk per direction plus bounded protocol overhead is
live between commit points. Backpressure stops source reads before configured
direction or total memory bounds.

EOF is committed before half-close. One directional EOF does not close the
other direction. Clean close follows exact service candidate, monitor closure,
and service terminal order.

## 10. Monitor and alarm implementation

### 10.1 Bootstrap and lease

The transient coordinator is the only normal initializer. It performs section
5.2 exactly: `TRII/1`, then deterministic IPC `a0`/`a1` classification and
81-pair selection, then durable `TRIC/1` in the selected attempt file, then Job
and suspended service-first/monitor-second creation, two `CreatePipe` pairs per
child, identity `TRBH/1`, final-handle `TRBH/1`, bootstrap-close `TRBH/1`,
exact holder proof, and one terminal `TRIM/1` append to that selected file.
Neither child may publish
readiness before the manifest commits. Pre-proof child loss emits no manifest
byte. Post-proof child loss cannot cancel the manifest attempt, always blocks
external readiness, and preserves a successful manifest as recovery authority.

After committed `TRIM/1`, monitor opens its alarm journal and live endpoint,
starts and proves its ordinary workers, and becomes lease-capable. Service then
associates the monitor by current runtime context, held process handle,
creation identity, installation, challenge, and incarnation. Monitor issues a
lease. Service readiness requires current liveness of both children, a valid
lease, exact worker topology, and all frozen prerequisites.

Both sides hold the peer process handle. Lease messages bind:

- both incarnation IDs;
- strictly increasing sequence;
- expiry QPC anchor;
- service committed position;
- active session;
- critical-operation ID, phase, and progress;
- explicit healthy backpressure.

Every boundary uses QPC ticks and the frozen exclusive comparison.

### 10.2 Alarm reservation and journal

Each detector owns one segmented append-only persistent alarm chain per
incarnation:

```text
alarms\<detector-role>\<incarnation>.trj
```

The file is created lazily by the detector's persistent worker. A valid file
starts with the 288-byte `TRJF/1` prologue. Its nonzero bytes bind detector
role, chain, installation, service/monitor/writer incarnations, profile,
catalog, and schema. There is no per-alarm directory, manifest, slot file,
index, or diagnostic side file.

For each known-session alarm, session admission has already preallocated a
193-record/7,475,200-byte alarm-observation partition. Each admitted alarm
draws independent persistent-owned 3-record/208,896-byte and live-owned
3-record/24,576-byte subpartitions. At most four alarms are concurrent and 32
cumulative. The fifth/33rd consumes the one 4,096-byte overflow observation,
then terminates fail-closed.

For each persistent channel, the worker separately serializes alarm-root
publication capacity and append:

1. reconstruct committed record, monitor-incarnation, known-session or
   session-unknown, and alarm-root logical-byte counters;
2. prove that two records at `max_alarm_record_bytes=65,536` fit every
   inclusive aggregate and the protected alarm reserve;
3. append and witness one `ALARM_FIRST_ATTEMPT` record containing the immutable
   envelope and `reservation_records=2`,
   `reservation_bytes=131,072`;
4. report persistent initial success only after its complete `TRFW/1`,
   write-return, readback, and range validation;
5. later consume the same alarm ID's second reservation with exactly one
   `ALARM_CHANNELS_TERMINAL` record.

The two alarm-root publication records do not authorize IPC slots or
observation capacity. The committed first record is simultaneously the durable
publication reservation and first reserved record. No memory counter or
filesystem object before that commit claims capacity. A failed/partial first
or terminal append poisons the segment; its bytes remain charged and no slot,
sequence, or capacity is reused.

Before monitor readiness, the session-unknown domain preallocates 128
independent per-alarm partitions: persistent-owned 5 records/143,360 bytes and
live-owned 3 records/24,576 bytes, totaling 8 records/167,936 bytes per alarm
and 1,024 records/21,495,808 bytes per monitor incarnation.

A crash after create-new but before the prologue commit leaves exactly one
zero-byte poison sentinel at the unique expected incarnation path. Recovery
creates no alternative file or later incarnation segment while it exists.
Persistent readiness remains false until explicit operator repair outside the
running product, so repeated restarts cannot accumulate empty objects. Valid
segments consume at least one nonzero prologue and are therefore bounded by the
1 GiB alarm-root logical-byte quota. Record aggregates bound all alarm
reservations. Query enumerates only these segments within the profile limits
and reports committed prefixes/partial tails without repair.

### 10.3 Independent channel dispatch

Each publisher owns one persistent and one live in-place mapping. A slot has a
fixed 256-byte `TRAS/1` prefix plus a 4,096-byte inline payload. The coordinator
publishes a command, the bound worker replaces it with the result, and the
coordinator returns it to empty only after a durable outcome. The normal state
cycle is:

`EMPTY -> COMMAND_WRITING -> COMMAND_READY -> WORKER_EXECUTING ->
RESULT_WRITING -> RESULT_READY -> CONSUMER_VALIDATING ->
(OBSERVATION_COMMITTING | REJECTION_COMMITTING |
LATE_DIAGNOSTIC_COMMITTING) -> ACKED -> EMPTY`.

`POISONED` is the twelfth state. It has no normal exit. Slot index, `u64`
epoch, mapping/worker incarnations, operation, alarm, call, channel, and
emission remain bound throughout. The epoch advances only at `ACKED -> EMPTY`.

The persistent mapping has two slots: one for the initial emission and one for
the terminal emission, matching the two reserved persistent records. The live
mapping has 1,024 slots. Persistent and live mappings, indices, events,
workers, endpoints, and result paths share no mutable object.

Dispatch never calls `multiprocessing.Queue`, pipe `send`, blocking file I/O,
or a wait-for-space path. For each channel independently, the coordinator:

1. attempts one interlocked slot reservation;
2. if full, commits the exact `PREDISPATCH_FAILED_LIMIT` census observation
   for persistent `FAILED_LIMIT` or live `FAILED`, with no slot claim;
3. otherwise copies exact inline `TRAD/1`, retains its digest and deterministic
   reconstruction inputs, publishes `COMMAND_READY` with a release transition,
   and calls that channel's event;
4. records dispatch attempt QPC only after `SetEvent` returns success; a
   returned failure becomes `FAILED_IO`;
5. proceeds without waiting for worker pickup, storage, live acceptance,
   call return, or detector-journal observation.

On detection the coordinator creates the immutable alarm ID/sequence/envelope
and `detected_at`, then performs both independent dispatch attempts. It samples
the two independent result events with bounded `WaitForMultipleObjects`; it
never waits for either result before dispatching the other. A full/dead/error
channel cannot acquire, fill, signal, drain, time, or lock the peer mapping.

The coordinator owns all QPC timers. At
`detected_at + alarm_initial_outcome_freeze_deadline_ms` it freezes the exact
six-field initial tuple from results observed strictly before the deadline.
It then applies the same independent slot protocol to the persistent terminal
record and live terminal diagnostic within the one-second dispatch deadline.
No-return timeout decisions are made by the coordinator and committed within
their separate deadline.

Every returned call first enters `RETURNED_UNVERIFIED`. Inline framing/body
validation or complete `TRAF/1` path/identity/range/digest validation changes
it exactly once to `VERIFIED` or `REJECTED`. Initial success requires both call
return and validation strictly before the exclusive freeze deadline. At/after
the deadline is a late diagnostic; no validated result by the terminal
deadline is timeout authority. Known-session persistent bodies up to 4,096
bytes may be inline; larger bodies use `TRAF/1`. Session-unknown persistent
results always use a verified zero-body `FILE_REFERENCE`. Live bodies are at
most 4,096 bytes and inline.

Exact `TRAO/1` returned-result, rejection, timeout, pre-dispatch, and recovery
observations are commands to the detector's storage worker only after
dispatch/decision. Observation append failure makes the fact
unproven, degrades readiness, preserves committed prefixes, and fails the
affected session closed; it never gates either initial or terminal dispatch.
Late worker results remain diagnostics and cannot alter the frozen tuple.

Service and monitor expose separate live endpoints. A subscriber connects to
both if it needs complete live coverage. Service failure therefore does not
remove the monitor live path; monitor failure does not remove the service live
path.

If a required timeout-decision observation cannot commit, the detector marks
alarm evidence degraded, preserves committed prefixes, blocks new admission,
and fails the affected session closed without recursively requiring the failed
alarm path.

## 11. Recovery, verifier, and deletion

### 11.1 Recovery

Startup recovery:

- resolves `TRII/1` through the complete six-state/36-pair installation table
  before any IPC parent or allocation;
- derives the exact 68-byte deterministic `a0` and `a1` paths for the logical
  IPC intent, applies unavailable/conflict guards, classifies both paths into
  the exact nine states, and applies all 81 ordered `(a0,a1)` actions;
- executes at most one create-new action at a time: `CREATE_A0` only for
  `(ABSENT,ABSENT)`, and `CREATE_A1` only for
  `(TRIC_INCOMPLETE,ABSENT)` or `(TRIC_UNWITNESSED,ABSENT)`; no other `a0`
  state can create `a1`;
- selects at most one committed `TRIC/1` attempt file. The phrase “one
  deterministic attempt file” describes that selected file's sequence-zero
  `TRIC/1` followed by sequence-one `TRIM/1` chain, not the number of reserved
  paths or possible create-new actions;
- after holder proof appends exactly one `TRIM/1` attempt to that selected
  committed `TRIC/1` file; it never writes a manifest to the unselected path;
- if old ready IPC may remain, acquires the irreversible quiesce/freeze
  barrier and commits exact `TRAR/1`: inventory-open, 2,052 slot inventories,
  inventory seal, object-release proof, required uniquely ordered `UNPROVEN`
  resolutions, then recovery-complete;
- reserves 4,108 recovery records, two attempts each, 8,216 attempt files, and
  33,652,736 bytes; any incomplete proof becomes
  `RECOVERY_BLOCKED_OLD_IPC`;
- creates no replacement mapping, event, worker, or duplicated handle before
  complete recovery; old and replacement IPC incarnations never coexist;
- scans installation, alarm, and session committed prefixes read-only;
- never changes a historical session bundle;
- never continues a pre-restart session or credential;
- records new recovery facts only in a new installation/alarm segment;
- keeps target absence after uncertain deletion as `DELETE_UNKNOWN`;
- allows new sessions only after new monitor/service readiness.

Each mapping begins with the exact 32-byte aligned little-endian header:
`freeze_state@0`, zero reserved word at `4`,
`freeze_generation@8`, `active_transition_count@16`, and
`snapshot_sequence@24`. Slot `i` starts at `32 + i*4,352`.
`_winatomic` implements the requirement-owned acquire/release algorithm:
count increment, freeze read, even-to-odd sequence CAS, freeze recheck, one slot
CAS, next-even publish, and count decrement.

Recovery first claims generation `0 -> expected`, then
`RUNNING -> FREEZE_REQUESTED`. The same generation may resume; a different
generation is a structural conflict. Crash-left nonzero active count or odd
sequence may be normalized only after every mutator is `EXITED` or
`IDENTITY_ABSENT`; an alive `QUIESCED` mutator is insufficient. Stable snapshot
ends irreversibly at `FROZEN`, never `RUNNING`, and no slot state is synthesized
or rolled back. A crash before attempt-file creation reuses the already-derived
generation. Mapping sizes are exactly 8,736, 8,736, 4,456,480, and 4,456,480
bytes; aggregate 8,930,432.

### 11.2 Verifier pipeline

1. accept exactly one absolute self-contained evidence-session directory as the
   only input; runtime evidence/alarm/installation roots and current process
   state are never inputs;
2. inspect every component from the supplied path to the final target and
   reject any junction, symbolic link, mount point, or other reparse traversal
   with exact `INPUT_ERROR` before evidence evaluation;
3. open the final directory read-only with no share-delete and prove readable
   supported-filesystem identity, directory type, containment, canonical final
   path, and exact reopen identity from the final handle;
   write access is neither requested nor required;
4. reject access denial, unsupported filesystem/version, alternate streams,
   and every path/entry/file/byte/depth/time bound before authoritative
   evaluation;
5. open each declared role with read-only, no-share-delete handles and bind
   file IDs;
6. parse manifest/profile/catalog independently;
7. stream both journal prefixes and retain every partial tail fact;
8. validate framing, digest, sequence, identity, state, cross-journal, alarm,
   monitor, lifecycle, and version invariants;
9. prove `O_d/T_d/A_d/U_d` conservation without loading raw payload into
   unbounded memory;
10. evaluate the full clean conjunction;
11. compute all reason counts before detail truncation;
12. render deterministic canonical UTF-8 JSON within the four section budgets
    and return the catalog exit code.

`input.canonical_path` is an absolute Windows path. It is bounded by 32,767
UTF-16 code units, at most 131,068 UTF-8 bytes, and the confirmed mandatory
report-byte budget. The relative bundle-path profile key applies only to
manifest entries.

Issue details sort exactly by numeric priority; journal sequence with absent
last; direction client-to-upstream then upstream-to-client with absent last;
start offset with absent last; stable reason ID; canonical detail bytes.
Role, relative path, issue kind, and text live inside the final detail object
and cannot reorder the preceding normative keys.

All OS reads and failures are recorded. An internal failure after an observed
fact returns `INTERNAL_ERROR`, `evaluation_complete=false`, one primary
internal reason, and only cataloged `OBSERVED_*` reasons.

### 11.3 Deletion

`delete-inspect` returns exact type, ID, canonical path, file identity,
manifest digest, and a one-use in-memory nonce bound to current service
incarnation and exclusive expiry.

`delete-submit`:

1. validates current-instance association and exact final-path/file-identity
   binding;
2. reserves three audit records and alarm-root bytes;
3. commits `DELETE_INTENT`;
4. returns `ACCEPTED` plus operation ID;
5. dispatches the deletion operation to the isolated maintenance worker;
6. holds no-share-delete conflicts as failure;
7. commits succeeded, failed, or unknown;
8. never infers success from target absence.

No cancel exists. A deadline or unproven worker termination yields
`DELETE_UNKNOWN`. Only a new audit segment may contain the single allowed
recovery observation.

## 12. Source layout

```text
TraceRelay\
  pyproject.toml
  README.md
  SECURITY.md
  LICENSE
  docs\
    architecture.md
    evidence-claim.md
    operations-windows.md
    protocols\
      control-v1.md
      worker-v1.md
      journal-v1.md
      alarm-v1.md
  src\tracerelay\
    __init__.py
    _build_identity.json
    _winatomic.c
    assets\v1\
      support-profile.windows-local-v1.json
      reason-exit-catalog.v1.json
      traceability-matrix.v1.json
      schemas\...
    platform\windows\
      api\...
      handles.py
      runtime_context.py
      paths.py
      durability.py
      witness.py
      process.py
      clocks.py
      atomic.py
    protocol\
      bootstrap.py
      control.py
      worker.py
      outcome_selector.py
    runtime\
      coordinator.py
      service.py
      monitor.py
      installation.py
      installation_authority.py
      ipc_authority.py
      supervisor.py
      state\...
      journal\...
      alarm\...
      recovery\ipc_abandonment.py
      workers\...
    control\
      client.py
      cli.py
    verifier\
      cli.py
      framing.py
      digest.py
      state.py
      accounting.py
      catalog.py
      report.py
    entrypoints\
      start.py
      monitor.py
      service.py
      control.py
      verify.py
      reference_client.py
      certify.py
  tests\
    oracle\...
    unit\...
    contract\...
    integration\windows\...
    crash\windows\...
    mutation\...
    performance\windows\...
    soak\windows\...
  tools\
    release\...
    certification\
      etw_diskio.py
      host_gate.py
```

No production module imports `tests`. No verifier module imports
`tracerelay.runtime`. No runtime module imports `tracerelay.verifier`.
`_winatomic.c` imports no project header other than its generated ABI constants;
it exposes no requirement state, codec, path, handle, process, or storage
decision. ETW exists only under the external certification tool path and is
never imported by service, monitor, coordinator, readiness, or recovery.

Startup coordinator phase ownership is fixed:

| Artifact | First owner | Frozen scope | Later extension |
|---|---|---|---|
| `src/tracerelay/entrypoints/start.py` | TR-I03 | constructs the coordinator and enters the pre-IPC state machine; no Job, child, `TRIC/1`, `TRIM/1`, mapping, event, worker, lease, or readiness path | TR-I05 connects the existing post-`TRII_SELECTED` continuation |
| `src/tracerelay/runtime/coordinator.py` | TR-I03 | states `START -> ROOTS_ADMITTED -> TRII_SELECTED` or terminal failure; sole `TRII/1` call sites | TR-I05 adds IPC-intent resolution, recovery, Job/child/bootstrap, holder proof, `TRIM/1`, and readiness transitions |
| `src/tracerelay/runtime/installation_authority.py` | TR-I03 | exact `TRII/1` two-attempt resolver and frozen terminal-overlapped calls, invoked only by the coordinator | no I05 semantic change; I05 reruns its regression gate |
| `src/tracerelay/runtime/ipc_authority.py` | TR-I05 | exact two-path/81-pair `TRIC/1` resolver, selected-file chain, `TRIM/1`, and `TRAR/1` recovery | none before I05 |
| `src/tracerelay/protocol/bootstrap.py` and `src/tracerelay/platform/windows/process.py` | TR-I05 | `TRBH/1`, creation-time Job binding, child/handle/bootstrap protocol | none before I05 |

TR-I03 evidence is immutable after its gate. TR-I05 may extend the named
coordinator and entrypoint source files, but it never backfills or relabels
TR-I03 evidence. Its own checkpoint reruns the complete TR-I03 regression
matrix against the changed source and records new current-code evidence before
claiming I05 PASS.

## 13. Dependencies and packaging

Runtime dependencies: none outside CPython 3.13, the wheel-bundled
`_winatomic.pyd`, and Windows 11 APIs. The extension has no separately installed
runtime and uses the CPython extension boundary only for argument/result
marshalling.

Build/test dependencies proposed for the first lock:

| Dependency | Version | Scope |
|---|---:|---|
| `setuptools` | `83.0.0` | PEP 517 build backend |
| `build` | `1.5.0` | isolated wheel/sdist build |
| `pytest` | `9.1.1` | test runner |
| `hypothesis` | `6.163.0` | bounded property/state-machine generation |
| MSVC x64 C compiler | CPython-3.13-compatible toolset selected by the frozen build image | build `_winatomic.pyd`; no runtime role |
| Windows SDK | `10.0.26100.0` | compile/link headers and import libraries |

All direct and transitive build/test artifacts and the concrete compiler
installation used for release are pinned by exact version, filename or
installation identity, SHA-256 where an artifact exists, Python tag, platform
tag, compiler command line, and environment capture in lock evidence. The
inspected workstation currently provides Visual Studio Community
`18.8.0+12009.203` and Windows SDK `10.0.26100.0`; this is environment evidence,
not a product-format value. A release uses one frozen compatible toolchain and
records it before build. No unpinned network resolution occurs in release
certification. Changing a runtime dependency or the `_winatomic` ABI requires a
reviewed plan amendment.

The release build:

- uses one committed source tree and clean worktree;
- embeds source commit, package version, contract hashes, Python version, and
  build-tool lock hash;
- sets deterministic archive timestamps and ordering;
- builds twice in independent clean directories;
- requires byte-identical wheels;
- installs the wheel into a clean CPython 3.13 virtual environment;
- runs the package and full Windows gates from the installed wheel;
- retains wheel/sdist hashes, build logs, inputs, exits, and environment.

## 14. Implementation phases

No phase starts until the final implementation plan is reviewer-PASS and
explicitly confirmed by the user. Each phase is one recoverable checkpoint.
`PHASE_DEPENDENCY_DAG.json` SHA-256 is
`1e3ba36f4dffe726708a7a21a97262e548868b5c6fa3872eeb799c6f5bbbc5f7`;
it is the machine-readable authority for prerequisites and the first phase
allowed to claim each composite gate.

### TR-I00 — Repository and contract bootstrap

Deliver:

- project skeleton and package metadata;
- exact confirmed profile, catalog, and traceability bytes;
- exact plan-confirmed machine-readable schemas, schema-hash manifest, phase
  DAG, and format specifications;
- dependency locks and offline wheelhouse manifest;
- static import-boundary and no-AI checks.

Gate:

- source assets hash to the confirmed requirement snapshot;
- packaged schema bytes hash to `SCHEMA_HASHES.json`;
- package build and clean install succeed;
- no runtime dependency exists;
- no implementation invents a field, command, record, state, or vector.

`TR-I00` is complete only for historical batch-024. It is not relabelled as a
batch-027 PASS.

### TR-I00R — Batch-027 authority rebase

Deliver:

- replace the five packaged requirement assets with byte-exact batch-027
  authority;
- replace packaged plan schemas, `SCHEMA_HASHES.json`, and phase DAG with the
  reviewer-PASS/user-confirmed batch-010 bytes;
- update `_build_identity.json`, source inventory, contract tests, dependency
  lock/wheelhouse metadata, and package-data expectations without adding
  runtime behavior;
- retain the I00/batch-024 snapshot and evidence as immutable history.

Gate:

- all 30 pre-rebase files first match the retained I00 snapshot;
- every replaced asset matches its batch-027 or batch-010 authority hash;
- source inventory covers every file exactly once and binds the new authority;
- contract tests, package build, clean install, and installed-wheel asset tests
  pass on Windows under CPython 3.13 and PowerShell 7.x Core;
- repository still contains no I01 runtime implementation;
- a frozen I00R source snapshot and independent evidence exist before I01.

### TR-I01 — Windows substrate

Deliver:

- handle ownership;
- clocks;
- CNG;
- current user/logon-session attribution;
- session-local named mutex;
- named pipe;
- file identity/path/NTFS checks;
- three non-interchangeable overlapped I/O primitives: ordinary exact-single
  journal write, witness positive-progress fill, and `TRBH/1` read/write-all;
- `TRFW/1` one-time witness fill/readback primitive and pre/full-witness
  digests;
- held-handle `PROCESS_CREATION_IDENTITY_FILETIME` identity primitive with all
  time uses prohibited;
- creation-time Job/process/pipe/HANDLE_LIST construction;
- `_winatomic` aligned 32/64-bit acquire/release ABI;
- shared-memory header, in-place slots/events, terminal overlapped-completion
  ownership, and cancellation APIs.

Gate:

- the wrapper applicability matrix closes every API row as
  `APPLICABLE`, `N/A`, or `SUBSTITUTE`; every reachable real-Windows
  success/error/boundary/invalid-input/invalid-handle class is tested;
- x64 ABI assertions pass;
- termination at every create/job/resume/bootstrap boundary proves no
  uncontained role execution;
- injected Job/pipe/mapping/overlapped/atomic failures fail closed;
- cross-process atomic stress proves no torn 32/64-bit value, lost transition,
  sequence regression, or invalid recovery normalization;
- positive-short/zero/error/deadline/cancel races prove terminal ownership and
  exact poison behavior for each of the three I/O primitives;
- handle leak baseline returns to zero;
- normally resolved reparse paths, final-target escape/identity changes,
  unexpected product-tree reparse objects, and wrong runtime-context
  associations produce the exact supported outcomes.

### TR-I02 — Canonical formats and independent oracle

Deliver:

- manifest/journal/alarm/control/worker schemas;
- byte-exact `TRII/1`, `TRIC/1`, `TRIM/1`, `TRBH/1`, `TRAD/1`, `TRAO/1`,
  `TRAF/1`, `TRAR/1`, and `TRFW/1` codecs imported from batch-027;
- byte-exact plan-owned `TRAS/1`, `TRR1`, and `TRBM/1` codecs;
- production writer;
- independent verifier with exact checkers for every frozen format;
- one mutated-byte classifier that executes the same exact checker path used
  for valid bytes;
- third oracle;
- reproduction and execution of the already-frozen golden and mutation
  corpus; I02 creates no normative fixture choice.

Gate:

- byte-identical agreement on valid vectors;
- every machine-declared vector, fixture-file range, byte mutation, operation
  mutation, cross-vector relation, deadline case, and transition reproduces its
  frozen hash and classification;
- all nine `TRAO/1` variants, 35 conditional-presence cases, twelve `TRAS/1`
  states, 22 legal transitions, one forbidden transition, 43 partial witness
  prefixes, and the complete 4,108-record `TRAR/1` chain remain covered;
- every valid vector reaches exactly one of
  `TRII/TRIC/TRIM/TRBH/TRFW/TRAD/TRAF/TRAO/TRAS/TRR1/TRAR/TRBM` or the
  mapping-header state-machine checker; a generic-only
  fallback fails the gate;
- each `TRAF/1` kind `1` resolves to an actual kind-400 target and each kind
  `2` resolves to an actual kind-401 target, with exact range, identity,
  sequence, previous-digest, full-record-digest, and trailer-digest equality;
- the valid TRBM vector yields exactly five physical files, four listed
  non-manifest files, six logical roles, and seven exact selectors;
- every mutation result is independently classified from its bytes; a declared
  expected classification is never an input to the classifier;
- all eleven exclusive deadline identities have exact before/at/after rows:
  33 cases at `deadline-1/deadline/deadline+1`; every frozen reference and
  identity relation is executed;
- mutations of logical selectors, alarm call/worker/subscription/result/copy
  bindings, initial channel states, report direction/offset/order, and
  1,024/1,025-byte relative versus long legal absolute paths fail with the
  exact catalog result;
- all every-byte truncations classify correctly;
- import-boundary scan proves no shared critical function;
- crash points never fabricate a committed record;
- every per-format/variant QPC presence mutation and every forbidden wall-clock
  field fails; pre-witness/partial/full/malformed witness cases classify
  exactly.

### TR-I03 — Installation authority and persistent catalog

Deliver:

- three-root admission and immutable `TRII/1` installation authority;
- minimal `tracerelay-start` entrypoint and transient startup-coordinator state
  shell through `START -> ROOTS_ADMITTED -> TRII_SELECTED` or terminal failure;
- coordinator-owned `TRII/1`-only OS-call path; no `TRIC/1`, `TRIM/1`, Job,
  child, bootstrap, mapping, event, worker, lease, or readiness path;
- current-runtime-context singleton objects;
- catalog segment recovery;
- app identity;
- root admission and quotas.

Gate:

- copied executable/cross-root races inside one runtime context produce one
  authority; a different user/logon session is outside the singleton claim;
- restart reconstructs exact state;
- no tail is repaired or appended;
- six-state/36-pair authority resolution and 8,192/8,193-byte boundaries pass;
- profile/hash/root/identity mismatch blocks readiness before IPC allocation.
- machine-readable phase ownership assigns `entrypoints/start.py`,
  `runtime/coordinator.py`, and `runtime/installation_authority.py` to I03 with
  exact pre-IPC scope, tests, and evidence; every I03 gate consumes only
  I00R..I03 artifacts;
- static ownership proof assigns every `TRII/1` create, exact write, flush,
  witness, readback/reopen, and final-identity call exactly once to the transient
  startup coordinator and to no ordinary worker;
- real-Windows create/short/zero/error/deadline/cancel/flush/witness/readback
  fault matrices prove terminal completion/resource ownership and no
  post-failure Job/child/IPC allocation.

### TR-I04 — Control protocol and outcome selector

Deliver:

- current-instance-associated local pipes with default Windows access control;
- TRCP frames;
- request challenge/replay protection;
- control client;
- exact public outcome evaluator.

Gate:

- 58 tuples and all mandated corpus families agree with the independent oracle;
- malformed/oversize/deadline inputs select exact reasons;
- one request produces one final public reason;
- registration credential never reaches console, log, or persistent file.

### TR-I05 — Monitor, lease, and alarm transport foundations

Deliver:

- monitor lifecycle;
- extension of the I03 transient startup coordinator after `TRII_SELECTED`,
  without backfilling or relabelling I03 evidence, plus exact creation-time Job
  binding;
- exact `TRBH/1` identity/final/close state machine;
- current-instance-associated incarnation handshake;
- heartbeat/critical progress;
- four prestarted alarm workers;
- independent profile-derived in-place alarm mappings;
- exact `TRIC/1` intent and `TRIM/1` ready-manifest chain;
- exact deterministic IPC `a0`/`a1` path derivation, nine-state classifier,
  complete 81-pair action table, and selected-attempt-file rule;
- transient-coordinator-owned bounded terminal-overlapped `TRIC/1` and
  `TRIM/1` authority operations with no ordinary-worker dependency;
- startup-only `TRAR/1` IPC-abandonment recovery and replacement barrier;
- segmented alarm journal plus first-record reservation;
- QPC freeze/terminal timers;
- session-unknown observation path;
- query/subscription framing.

Gate:

- monitor/service bootstrap and lease-state model pass without a session;
- machine-readable phase ownership proves I05 adds only its declared
  coordinator continuation and IPC/bootstrap artifacts; its fresh checkpoint
  reruns the complete I03 regression matrix against current source and leaves
  the historical I03 evidence unchanged;
- static validation proves exact `a0`/`a1` paths, all 81 table actions,
  exactly two `CREATE_A1` cells, at most one create-new action at a time, and one
  selected committed `TRIC/1` file with one later `TRIM/1` append;
- real-Windows crash/action tests prove `a0` partial and unwitnessed states
  create `a1`; the other seven `a0` states do not; exhaustion, conflict,
  selected path, 8,192/8,193 bytes, no-pre-allocation, and duplicate-manifest
  cases receive their exact frozen result;
- static resource validation recomputes 4 mappings, 8 events, exact mapping
  sizes `8,736/8,736/4,456,480/4,456,480`, aggregate `8,930,432`,
  24 object-handle entries, 4 control-handle entries, 28 ready handles,
  8 steady bootstrap handles, 14 child-create transient handles, and 51
  PRE_READY handles from confirmed profile domains;
- every holder-proof boundary executes the single required poll; pre-proof
  child loss emits no `TRIM/1`, while post-proof loss cannot cancel its sole
  attempt and can never publish readiness;
- static OS-call ownership maps every `TRIC/1`/`TRIM/1` create, exact write,
  flush, witness, readback/reopen, and identity call to the transient startup
  coordinator exactly once; the ordinary-worker graph has no pre-`TRIM/1`
  dependency and topology remains exact `8/14/51/43/28`;
- real-Windows fault injection at every startup-authority boundary proves
  terminal completion/resource-release classification and prohibits crossing
  the corresponding allocation/readiness gate;
- independently fill both persistent two-slot mappings and both live
  1,024-slot mappings; every full/stalled result path returns its channel
  failure without dynamic allocation or peer delay;
- every deadline one tick before/at/after;
- full/dead/faulted one-channel mappings never delay the peer dispatch;
- persistent/live faults remain independent;
- late/root-only facts never upgrade outcomes;
- session-unknown journals validate both detector roles;
- this phase does **not** claim complete TR-F-047..057, TR-F-052, TR-F-090, an
  ACTIVE-session monitor-kill result, known-session copied authority, or
  cross-journal clean closure.

### TR-I06 — Session namespace, credential, and lifecycle

Deliver:

- namespace transaction;
- bounded volatile credential-comparison lifecycle;
- 64-WAITING lightweight reservation and atomic one-ACTIVE upgrade;
- WAITING/authentication/ACTIVE states;
- race-priority serializer;
- session closure reserve;
- minimal loopback activation through committed `CONNECTION_ACTIVE`, with
  application payload forwarding still disabled;
- service and monitor session-journal integration.

Gate:

- all states/transitions/races match the contract;
- model-check every simultaneous event pair one tick before/at/after each
  deadline against the exact nine-level race order;
- crash after every credential issue/expiry, claim, registration
  terminalization, `CLEAN_CANDIDATE`, `NO_FAILURE_OBSERVED`, and
  `TERMINAL_CLEAN` boundary recovers one exact state/reason;
- 64 WAITING succeed within root quota, 65th fails before object creation, and
  an activation race produces exactly one durable winner;
- no upstream call or payload forwarding precedes catalog ACTIVE reservation
  and session-journal claim copy;
- plaintext is returned once, never intentionally persisted/logged, and all
  old credentials fail after restart;
- restart invalidates credentials and never resumes old journals;
- all namespace crash points retain a non-reused result.

### TR-I07 — Integrated monitoring and alarm authority

Deliver:

- known-session alarm-publication observations;
- exact `TRAO/1` variants, `TRAD/1` dispatch binding, `TRAF/1` validation,
  persistent-record copy/linkage, and return-validation state machine;
- ACTIVE-session lease-loss/service-failure handling;
- service/monitor cross-journal close protocol;
- alarm-specific offline evaluator independent of runtime recovery;
- integrated alarm query/subscription.

Gate:

- real ACTIVE-session service-kill and monitor-kill matrices;
- monitor failure closes the ACTIVE session incomplete;
- known-session and session-unknown truth tables cover every timely, at,
  after, root-only, timeout, precommit-crash, and late-commit window;
- 4/5 concurrent, 32/33 cumulative, 128/129 session-unknown, 4,096/4,097
  inline, 65,536/65,537 referenced, 69,632/69,633 observation, and
  six/seven-observation boundaries pass;
- copied bundle proves only its copied observation authority without reopening
  alarm root;
- cross-journal clean closure and `TR-ALARM-UNPROVEN` mutations pass;
- this is the first phase allowed to claim the composite TR-F-047..057,
  TR-F-090, and TR-F-092 alarm/monitor gates.

### TR-I08 — Full-duplex transport

Deliver:

- loopback listeners;
- exact hello;
- one upstream connect;
- commit-before-forward;
- range accounting;
- EOF/half-close/backpressure;
- worker fail-closed behavior.

Gate:

- exhaustive byte corpus and randomized binary streams match;
- full/short/zero/error/unknown vectors pass;
- five-boundary write crash matrix passes;
- no unknown range is replayed;
- over-envelope load weakens no invariant.

### TR-I09 — Recovery and verifier

Deliver:

- read-only session recovery plus complete `TRAR/1` two-phase IPC recovery;
- full verifier state/accounting;
- stable report budgets;
- version compatibility assets.

Gate:

- exhaustive classification and mutation corpus;
- a direct absolute bundle path verifies without alarm root, runtime root, or
  current process state;
- a copied bundle that is readable but not writable can PASS; before/after
  directory digest, metadata-write monitoring, and access logs prove zero
  verifier writes;
- the same valid bundle addressed through any junction, symbolic link, mount
  point, or other reparse traversal returns exact `INPUT_ERROR` before evidence
  evaluation;
- direct-path access-denied, unsupported-filesystem, bound max/max+1, and
  mid-read-failure vectors produce their frozen classifications;
- maximum legal failed bundle remains inside all verifier bounds;
- old and replacement IPC incarnations never coexist at any crash point;
- current verifier reads every produced `1.x` vector.

### TR-I10 — Deletion

Deliver:

- inspect binding/nonce;
- audit reservations and segments;
- asynchronous worker/status;
- recovery observation.

Gate:

- every crash point and deadline;
- audit-full prevents mutation;
- verifier/capture handles block delete;
- target absence never upgrades unknown;
- forbidden objects cannot be deleted.

### TR-I11 — Packaging and functional assurance

Deliver:

- final CLI/docs;
- reproducible package identity;
- strict logs;
- bundled `_winatomic.pyd` ABI/toolchain identity;
- clean-host installer flow;
- release artifact manifest.

Gate:

- two clean builds are byte-identical;
- installed-wheel tests pass;
- static/runtime scans find no AI/model/agent path;
- credential/payload persistence and log scans pass;
- unsupported environments fail without a support claim.

### TR-I12 — Windows release certification

Deliver:

- all 136 traceability tests;
- current-runtime-context association, crash, holder-loss, short-I/O, and
  mapping-recovery matrices;
- three performance repetitions;
- exact 24-hour soak and closure;
- retained raw evidence.

Gate:

- no skipped requirement is called passed;
- host and storage gate pass every interval;
- ETW evidence comes only from the external certification harness; missing,
  lost, unattributed, or ambiguous real events make certification not-passed
  but never alter runtime readiness or session outcome;
- synthetic ETW exercises only parser logic and cannot certify release;
- all three performance repetitions pass;
- 24-hour exact bytes, closure, and offline PASS succeed;
- final independent code/test/evidence reviews pass.

## 15. Test and evidence strategy

Implementation and test authorship remain separate in the later Aegis flow.
Execution and result-evidence review remain separate.

Every test run retains:

- source commit and clean/dirty state;
- installed wheel and SHA-256;
- exact profile/catalog/schema hashes;
- OS build, Python, volume, current user SID, logon-session ID, and held process
  manifest;
- fixture/corpus hash;
- command/harness identity;
- raw exit, stdout, stderr, Windows status, and timeout;
- expected/actual machine comparison;
- failed evidence without deletion or replacement.

Test families:

1. pure unit tests for codecs, state predicates, bounds, and selectors;
2. model/state tests for lifecycle/race/deadline spaces;
3. independent differential tests across writer/verifier/oracle;
4. real NTFS and named-pipe integration;
5. process termination at every commit/write boundary;
6. socket fault/short-write/half-close/unknown tests;
7. normal-reparse/final-handle/path/current-context association tests;
8. startup `TRBH/1`, exact holder-proof, post-proof loss, Job/handle-ledger,
   mapping atomic/recovery, and three-way short-I/O/cancellation tests;
9. verifier mutation and resource-limit tests;
10. packaging/reproducibility/persistence-log scans;
11. external real-ETW Windows performance certification and 24-hour soak.

Test-only fault injection is explicit and cannot be enabled by a production
entry point. Every injected call has a stable point ID and retained trace.

## 16. Quality gates and stop rules

An implementation phase cannot pass if:

- a normative requirement lacks a test/static oracle;
- a failure or timeout is skipped, retried away, or averaged away;
- test and implementation share the truth function under test;
- a Windows result is inferred rather than observed;
- a worker cancellation is treated as physical completion;
- a journal tail is repaired or discarded;
- a limit/deadline differs from embedded profile bytes;
- any credential/raw payload appears outside allowed evidence and transient
  buffers;
- a current diff is reviewed against a stale plan/code snapshot without
  preserving the stale result;
- the source worktree changes while a frozen review batch is running.

## 17. Rollback and recovery

Before every implementation phase:

- record branch, HEAD, status, diff, contract hashes, and test baseline;
- create a phase artifact directory;
- keep unrelated user changes untouched.

On phase failure:

- stop before the next phase;
- retain raw failing evidence;
- leave historical evidence files unchanged;
- record incomplete work and exact resume command in `CONTINUATION.md`;
- do not reset, delete, commit, or push without user authority.

No database migration exists in v1. On-disk format changes require a new
schema minor/major decision and compatibility review before code changes.

## 18. Requirement-to-phase ownership

| Requirement group | Primary phase | Independent release gate |
|---|---|---|
| TR-F-001..006 | I00, I11 | I12 |
| TR-F-007..012 | I03, I06, I07, I11 | I12 |
| TR-F-013..022 | I04, I06 | I12 |
| TR-F-023..034 | I06, I08 | I12 |
| TR-F-035..046 | I02, I06, I08, I09 | I12 |
| TR-F-047..057 | I05 foundation, I06 prerequisite, I07 composite gate | I12 |
| TR-F-058..068 | I02, I07, I09 | I12 |
| TR-F-069..077 | I01, I03, I10 | I12 |
| TR-F-078..084 | I04, I09, I10 | I12 |
| TR-F-085..102 | I00..I11 | I12 |
| TR-NF-001..012 | all applicable phases | I12 |
| TR-AC-001..022 | all applicable phases | I12 |

The shipped traceability matrix remains the row-level authority. This table
only assigns implementation ownership.

## 19. External source anchors

Implementation must verify the current Windows/Python documentation again at
the start of the affected phase. Initial plan anchors:

- named-pipe client process identity:
  https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeclientprocessid
- kernel-object namespaces:
  https://learn.microsoft.com/en-us/windows/win32/termserv/kernel-object-namespaces
- `CreateFileW` create-new, share, reparse, and write-through rules:
  https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
- `FlushFileBuffers`:
  https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers
- `CancelIoEx` uncertainty:
  https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex
- `GetOverlappedResultEx` terminal completion:
  https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getoverlappedresultex
- anonymous pipe construction:
  https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createpipe
- Windows Job Objects:
  https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- process creation attribute list and Job-at-creation:
  https://learn.microsoft.com/en-us/windows/win32/procthread/attribute-list
- `UpdateProcThreadAttribute`:
  https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute
- CNG random generation:
  https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptgenrandom
- CNG HMAC hash creation:
  https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptcreatehash
- aligned interlocked compare/exchange:
  https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-interlockedcompareexchange64
- MSVC interlocked intrinsics:
  https://learn.microsoft.com/en-us/cpp/intrinsics/interlockedcompareexchange-intrinsic-functions
- Python 3.13 multiprocessing:
  https://docs.python.org/3.13/library/multiprocessing.html

## 20. Open decisions and gates

No product-behavior choice is intentionally left to the implementer.

Remaining gates:

1. independent reviewer full-snapshot review;
2. unified remediation of all findings if review fails;
3. new frozen review snapshot after any remediation;
4. reviewer PASS;
5. explicit user confirmation of the exact final implementation plan;
6. separate user authorization before source implementation begins.

Until gates 1–5 pass, `IMPLEMENTATION_PLAN_FINAL.md` remains only the explicit
suspension wrapper for historical batch-007 authority; it must not identify
batch-010 as final or authorize `TR-I00R`.
