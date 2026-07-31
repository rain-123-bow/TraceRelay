# TraceRelay Implementation Decision Record

## Status

- plan version: `1.0.0-draft.10`
- requirement snapshot: `tracerelay-req-b027-48e1910c4369`
- reasoning ledger: unavailable
- review status: `batch-007 FULL_PLAN PASS and user-confirmed; batch-008 FULL_PLAN FAIL C-001/R-003; batch-009 FULL_PLAN FAIL C-003/G-003; batch-010 unified-remediation review pending`
- implementation authorization:
  `SUSPENDED_PENDING_BATCH010_REVIEW_AND_USER_CONFIRMATION`
- user confirmation: pending with final plan

## Decisions

### IDR-001 — Runtime language and dependencies

- decision: CPython 3.13, standard library, narrow `ctypes` Win32 wrappers, and
  one wheel-bundled minimal `_winatomic` C extension; zero third-party runtime
  dependencies.
- requirement basis: TR-F-001..004, TR-NF-008..011, user-confirmed Python and
  no-agent decisions.
- rejected: pywin32/psutil runtime and a Rust/C product core.
- cost: Win32 FFI, native atomic ABI tests, and a pinned Windows build toolchain.
- failure prevented: mixed FFI semantics, non-atomic emulation, and a second
  business-logic truth boundary.

### IDR-002 — User-hosted foreground components

- decision: the external caller starts one transient coordinator. It creates
  service then monitor suspended and Job-bound, proves bootstrap/holders,
  publishes one result, and exits. Service and monitor remain separate
  foreground processes; no Windows SCM dependency exists in v1.
- requirement basis: TR-F-008, TR-F-024, TR-F-081 and confirmed caller
  ownership.
- rejected: TraceRelay starting client/upstream; mandatory SCM service.
- cost: caller hosts one startup command and two long-lived child processes.
- failure prevented: hidden process ownership and client lifecycle coupling.

### IDR-003 — Runtime-context installation authority

- decision: the operator selects three existing absolute roots before first
  start. Normally resolved final handles must prove pairwise
  distinct/non-nested writable local fixed-disk NTFS identities. One exact
  `TRII/1` beneath the runtime root and session-local objects establish
  authority for the current user plus logon session. Owner SID remains
  attribution and installation-identity input only.
- requirement basis: TR-F-007, TR-F-009, TR-F-066, TR-F-069, TR-F-076,
  TR-F-095.
- rejected: ProgramData/executable-relative authority, caller-named mutexes,
  host-global or hostile-user security claims.
- cost: final-handle root admission and exact decision tables.
- failure prevented: copied-executable, alternate-root, alias, final-target
  escape, or same-runtime-context singleton bypass.

### IDR-004 — Control and monitor IPC

- decision: local named pipes with default Windows access control,
  current-instance/logon-session association, held process identity, fresh
  incarnation challenges, replay state, and canonical binary frames.
- requirement basis: normative sections 8.1, 11.1, 11.2.
- rejected: loopback TCP control, custom DACL/security-product hardening, and
  caller-supplied identity.
- cost: custom framing and named-pipe FFI.
- failure prevented: accepting the wrong installation/incarnation/runtime
  context or a replayed request.

### IDR-005 — Canonical binary journal and durable witness

- decision: custom fixed-envelope, typed-field, append-only binary formats with
  SHA-256 chain, pre-witness digest, and exact 44-byte `TRFW/1`. The witness
  block starts zero, is filled once in ascending order after successful flush,
  then requires write return and exact readback. Offline positive authority
  requires a valid full witness; live external action additionally requires
  observed returns/readback.
  Authoritative files are create-new `GENERIC_READ|GENERIC_WRITE`, share zero,
  and use explicit offsets. Ordinary pre-witness records require one
  full-count completion; witness fill permits at most 44 positive-progress
  writes; `TRBH/1` permits positive chunks to exactly 4,096 bytes. All retain
  `OVERLAPPED`, event, buffer, and file through terminal completion.
- requirement basis: TR-F-038, TR-F-094 and normative sections 3, 7, 15.
- rejected: pickle, SQLite, JSON/base64 payload records, mutable database.
- cost: three independently authored codecs plus every-byte crash/witness
  classification.
- failure prevented: semantic normalization, hidden transaction behavior,
  ambiguous tail/commit/cancellation boundaries, short-write continuation on
  authoritative records, and runtime-code execution on parse.

### IDR-006 — Process isolation

- decision: long-lived service and monitor coordinators never enter potentially
  unbounded file/destination calls; exactly eight ordinary workers execute
  those post-`TRIM/1` calls. The transient startup coordinator is the sole
  exception and directly executes only the frozen bounded terminal-overlapped
  `TRII/1`, `TRIC/1`, and `TRIM/1` create/write/flush/witness/readback/reopen/
  identity primitives. It retains every I/O resource until terminal completion
  and cannot cross the matching allocation/readiness gate after failure.
  Workers enter a kill-on-close Job at `CreateProcessW` time through
  `PROC_THREAD_ATTRIBUTE_JOB_LIST`, start suspended, receive an exact handle
  list, and resume only after membership/identity proof.
- requirement basis: TR-F-083, TR-F-084, normative 14.1.
- rejected: threads-only cancellation and monolithic asyncio.
- cost: worker protocol and process supervision.
- failure prevented: one stuck kernel call blocking fail-closed state.

### IDR-007 — Worker count and operation assignment

- decision: monitor storage, monitor persistent/live alarm, service storage,
  transport, service persistent/live alarm, and maintenance are the fixed eight
  workers; coordinators are not counted as workers. Maintenance handles
  recovery/query/inspect/serialization/deletion with one in-flight command.
  Monitor storage starts only after committed `TRIM/1`, adopts committed
  installation/IPC authority, and owns later monitor journals; it performs no
  startup-authority `TRII/1`, `TRIC/1`, or `TRIM/1` operation.
- requirement basis: profile `max_worker_processes=8`.
- rejected: one worker per waiting session.
- cost: one transport worker multiplexes waiting listeners.
- failure prevented: resource-bound violation at 64 waiting sessions.

### IDR-008 — Credential representation

- decision: direct `BCryptGenRandom` produces exactly 32 bytes, encoded once as
  43 base64url characters. A bounded volatile table retains only irreversible
  comparison material bound to session and service incarnation. Plaintext is
  returned once and is never intentionally persisted or logged. Ordinary
  buffers are released after the decision.
- requirement basis: TR-F-022, TR-NF-009, normative 11.3.
- rejected: immutable Python string/JSON path and plaintext persistence.
- cost: exact token parsing, lifecycle serialization, and restart invalidation.
- failure prevented: product-created credential copies in logs, terminal, or
  persistent state, replay, cross-session use, and old-incarnation reuse.

### IDR-009 — Alarm channel ownership

- decision: service and monitor each own separate persistent and live workers,
  endpoint, one preallocated in-place mapping, two events, and observations.
  `alarm_ipc_limits` owns every term: persistent mappings have two slots, live
  mappings 1,024 slots, each slot is 256+4,096=4,352 bytes after a 32-byte
  mapping header, and all four mappings total 8,930,432 bytes. One ready incarnation has 4 mappings,
  8 events, 24 object-handle entries, 4 control-handle entries, and 28 ready
  handles; bootstrap has 8 steady handles, process creation peaks at 14, and
  PRE_READY peaks at 51. A result replaces
  its command in the same pinned slot. Full/error/dead state in one channel
  returns immediately and cannot gate the peer.
- requirement basis: TR-F-051..057, normative 9.
- rejected: one shared broker or service-owned monitor alarm path.
- cost: duplicated workers/subscriptions.
- failure prevented: service failure removing monitor alarm dispatch.

### IDR-010 — Separated alarm reservations

- decision: one segmented append-only journal per detector incarnation; the
  durably committed `ALARM_FIRST_ATTEMPT` record is both the first publication
  record and reservation for exactly two 65,536-byte alarm-root publication
  records. It does not authorize IPC or observations. Known-session admission
  preallocates 193 records/7,475,200 bytes and draws independent
  3-record/208,896-byte persistent and 3-record/24,576-byte live
  subpartitions per admitted alarm. Session-unknown admission draws independent
  5-record/143,360-byte persistent and 3-record/24,576-byte live
  subpartitions. There are no per-alarm files.
- requirement basis: TR-F-053, normative 9.2/9.3.
- rejected: memory-only quota reservation and reusable failed slots.
- cost: a poisoned partial tail ends that detector segment and can block
  readiness.
- failure prevented: semantic-domain reuse, peer-channel reserve theft,
  uncharged empty-object accumulation, slot reassignment, and unprovable
  capacity claims.

### IDR-011 — Verifier independence

- decision: writer, verifier, and test oracle share only written schemas/bytes;
  they share no critical implementation function.
- requirement basis: TR-F-067, TR-F-068.
- rejected: common codec/state library.
- cost: intentional duplication.
- failure prevented: one shared bug self-validating writer output.

### IDR-012 — Packaging

- decision: Windows x64 wheel containing Python code plus the minimal
  `_winatomic.pyd`, exact build/test/toolchain locks, byte-reproducible
  two-build gate, and clean installed-wheel test.
- requirement basis: TR-F-001, TR-NF-008, TR-AC-013.
- rejected: editable install as release evidence.
- cost: lock/wheelhouse, pinned MSVC/SDK identity, and deterministic native
  build tooling.
- failure prevented: source/package mismatch and unrepeatable dependency drift.

### IDR-013 — WAITING versus ACTIVE capacity

- decision: each WAITING namespace reserves 32 MiB closure capacity; the
  successful credential claim atomically upgrades only the winner to one
  current-runtime-context ACTIVE slot, 6 GiB logical session capacity, and the 5 GiB
  physical free-space reserve before upstream connect.
- requirement basis: profile 64 WAITING, one ACTIVE, 32 GiB root, normative
  active-session admission.
- rejected: 6 GiB reservation before every credential issuance.
- cost: separate waiting/active counters and a cross-journal claim copy.
- failure prevented: reducing the frozen WAITING limit from 64 to five.

### IDR-014 — Frozen implementation schemas

- decision: the batch-027 requirement snapshot directly owns the exact
  `TRII/TRIC/TRIM/TRBH/TRAD/TRAO/TRAF/TRAR/TRFW` formats and mapping-header
  protocol. Six runtime schema assets
  freeze the remaining plan-owned layouts, commands, record fields,
  persistent states, reports, and immutable references to requirement-owned
  formats before source implementation. `golden-vectors.v1.json` is a
  plan/review authority, not a runtime-schema member. `SCHEMA_HASHES.json`
  separately binds the six-file runtime schema set and seven-file review
  schema set. The golden authority binds the corpus, manifest, tools, and
  evidence. Runtime records use only the six-schema runtime digest, which
  excludes golden vectors and therefore cannot create a corpus self-hash
  cycle.
- requirement basis: TR-F-087, TR-F-094 and normative section 16.
- rejected: allowing I00/I02 executors to choose IDs or byte layouts.
- cost: later schema changes require plan amendment and repeat review.
- failure prevented: writer/verifier/oracle agreeing only on an
  implementation-selected defect.

### IDR-015 — Persistent catalog authority

- decision: the installation catalog is the single atomic authority for
  application/registration transitions, credential claim, ACTIVE slot, quota
  counters, deletion state, segment seals, and tombstones; session journals
  carry required copies but cannot roll back a committed catalog claim.
- requirement basis: normative sections 5, 12, 13, and 14.
- rejected: reconstructing state from directories, memory counters, or side
  files.
- cost: explicit intents, copies, recovery projections, and poison states.
- failure prevented: divergent post-state/reason selection after a crash or
  exact-limit race.

### IDR-016 — Phase dependency repair

- decision: I05 implements alarm transport foundations only; I06 supplies
  session activation; I07 is the first complete monitor/alarm/known-session
  composite gate; release certification moves to I12.
- requirement basis: TR-F-052, TR-F-090, TR-F-092.
- rejected: claiming monitor-kill and copied known-session authority before
  ACTIVE/session journals exist.
- cost: two-stage alarm implementation and thirteen original phases plus the
  I00R rebase checkpoint.
- failure prevented: a phase PASS based on absent prerequisites.

### IDR-017 — Physical files versus logical evidence roles

- decision: a bundle contains five physical files. The manifest lists the four
  non-manifest files and separately binds seven selectors covering six logical
  roles. Alarm observations are exact `TRAO/1` variants 1–9 in either journal;
  session alarm linkage is plan-owned kind 409 in the service journal.
- requirement basis: normative 7.1/7.3 and TR-F-038/060/061/068.
- rejected: separate alarm-observation/linkage files and an ambiguous
  file-role table.
- cost: verifier validates a second manifest table.
- failure prevented: valid vectors creating seven physical files or omitting
  embedded logical roles.

### IDR-018 — Complete alarm-observation binding

- decision: exact requirement-owned `TRAD/1`, tagged-union `TRAO/1`, and
  `TRAF/1` freeze dispatch, returned-inline, returned-reference,
  returned-rejected, initial/terminal late, timeout, pre-dispatch limit,
  recovery-unproven, and envelope-limit truths. Every return moves from
  `RETURNED_UNVERIFIED` to exactly `VERIFIED` or `REJECTED`; success requires
  call return and validation strictly before its exclusive deadline. Numeric
  observation kinds 402–408 are withdrawn. Plan-owned kind 409 provides
  session linkage.
- requirement basis: normative 7.3/9.2/9.3.
- rejected: inferring publication from an alarm-root artifact or endpoint
  history.
- cost: larger typed records and more mutation vectors.
- failure prevented: offline success without a complete returned-call or
  no-return authority chain.

### IDR-019 — Exact lifecycle race and clean-close model

- decision: the persistent state schema uses the exact nine-level normative
  race order, expiry only after credential issue, explicit registration
  terminalization, and service-candidate/monitor-closure/service-terminal
  clean handshake under one lease.
- requirement basis: normative 5.2–5.6 and 7.3.
- rejected: a separate valid-claim priority and direct DRAINING-to-clean
  transition.
- cost: more transition records, crash states, and model-check vectors.
- failure prevented: a lower-priority event winning or recovery fabricating
  clean closure.

### IDR-020 — IPC creation and abandonment authority

- decision: startup resolves `TRII/1`, derives and classifies the exact IPC
  `a0`/`a1` paths, applies all 81 pair actions, and commits sequence-zero
  `TRIC/1` in the selected attempt file before any Job, child, mapping, event,
  or duplicated handle. Only `(TRIC_INCOMPLETE,ABSENT)` and
  `(TRIC_UNWITNESSED,ABSENT)` can create `a1`; at most one create-new action
  executes at a time. The coordinator
  creates/proves service then monitor through exact `TRBH/1`, closes all eight
  bootstrap handles, performs one exact two-process holder poll, and drives one
  sequence-one `TRIM/1` append attempt in the selected file. Pre-proof child
  loss emits no manifest byte;
  post-proof child loss cannot cancel the attempt and always blocks readiness.
  An old ready incarnation is replaced
  only after exact `TRAR/1` inventory, seal, release proof, uniquely ordered
  `UNPROVEN` resolutions, and recovery-complete. The fixed recovery reserve is
  4,108 records, two attempts each, 8,216 attempt files, and 33,652,736 bytes.
- requirement basis: TR-F-009, TR-F-053, TR-F-066, TR-F-086, TR-F-095.
- rejected: allocate-then-log, best-effort cleanup, and overlapping old/new IPC.
- cost: startup authority journals, 81-pair resolution, and two-phase recovery.
- failure prevented: missing evidence for pre-ready objects, PID reuse,
  unbounded restart leaks, and overlapping IPC authority.

### IDR-021 — Time and process identity

- decision: every format/variant carries only its exact applicable QPC fields.
  No universal observation or UTC field exists. The sole wall-clock-derived
  value is `PROCESS_CREATION_IDENTITY_FILETIME` from `GetProcessTimes` on the
  held handle, used only as an opaque PID-reuse identity discriminator in the
  exact allowed locations.
- requirement basis: TR-F-038, TR-F-040, TR-F-054.
- rejected: advisory UTC fields and process-creation time as ordering/duration.
- cost: per-format presence validation and held-handle identity tests.
- failure prevented: fabricated temporal claims and PID-reuse misattribution.

### IDR-022 — Deterministic independent-vector authority

- decision: one hash-bound binary corpus and machine-readable index freeze
  every U-001 fixture field, byte range, digest, state, reference/identity relation,
  deadline case, mutation offset, expected checker/assertion, and expected
  classification before implementation. A deterministic Python authoring tool
  proves reproducibility. A separate PowerShell decoder validates bytes and
  semantics without invoking, translating, or sharing the generator. Every
  valid vector reaches exactly one exact format or mapping-header checker. Every
  mutated result enters the same exact classifier before observed output is
  compared with frozen expectations. Production writer, verifier, and oracle
  must independently reproduce the corpus and may not import either plan tool.
- current draft.10 author-side counts and hashes are populated only after
  deterministic regeneration, independent PowerShell verification, mutation
  gates, and batch-010 freeze. Historical draft.9 results remain in batch-009.
  All authoritative plan scripts require PowerShell 7.x Core; other
  PowerShell editions and major versions are out of scope.
- requirement basis: normative section 16, TR-F-087, and the existing
  no-invention/independent-generation gate.
- rejected: family-name tokens, I02-selected fixtures, shared fixture builders,
  generic-only semantic acceptance, declared-classification self-approval, and
  JSON-embedded corpus hex.
- cost: two plan-only validation tools and one frozen binary corpus in every
  review snapshot.
- failure prevented: three conforming implementations selecting different
  fixtures, or one shared defect manufacturing byte-identical PASS evidence.

### IDR-023 — U-001 relation and temporal closure

- decision: terminal alarm references are generated from actual committed
  TRR1 targets, not by changing a reference enum. `TRAF/1` kind `1` maps only
  to target kind `400`; kind `2` maps only to target kind `401`. A valid
  `TRBM/1` freezes the five physical files, four listed files, six logical
  roles, and seven selectors. Cross-format reference/identity relations are
  frozen in relation metadata and rejecting mutations. Exclusive alarm
  deadlines form one machine-declared closed matrix. The eleven deadline
  identities each have exactly `deadline-1`, `deadline`, and `deadline+1`,
  producing 33 cases. Applicable return and validation times are timely only
  when both are strictly before the deadline.
- requirement basis: batch-027 normative alarm-reference, result-validation,
  monotonic-exclusive-deadline, bundle-role, independent-vector, and
  no-invention requirements; batch-006 `U-001` complete published closure
  surface.
- rejected: enum-only terminal fixtures, invalid-only TRBM coverage,
  independently declared expected classifications, partial deadline sampling,
  and implementation-selected relation cases.
- cost: real first/terminal alarm-journal chains, a self-contained bundle
  fixture, relation/deadline matrices, and semantic mutations with dependent
  digests re-sealed.
- failure prevented: a false-positive terminal evidence reference, a missing
  bundle authority, and a verifier that passes invalid timelines or identities
  by checking only corpus hashes.

### IDR-024 — Trusted-user functional boundary

- decision: v1 supports one trusted, non-malicious operator in one current-user
  Windows logon-session runtime context. Default Windows access control and
  ordinary runtime validation are sufficient. No custom DACL, restricted
  token, locked memory, anti-dump, WER hardening, adversarial path-race,
  same-user/cross-user/cross-session security claim, or security-product gate
  exists.
- requirement basis: batch-027 platform profile, TR-F-007/009/017/022/069/070/
  073/076/095, TR-NF-009, TR-AC-007/011/014/021.
- rejected: retaining batch-024 hardening as implicit release criteria.
- cost: unsupported adversarial local contexts are reported as out of scope.
- failure prevented: spending implementation/test authority on an unconfirmed
  security product while obscuring functional correctness.

### IDR-025 — Minimal native atomic substrate

- decision: `_winatomic` exposes only aligned buffer+offset acquire loads,
  release stores, compare/exchange, bounded u64 increment/decrement, and full
  fence over mapped memory. It keeps the GIL, retains a `Py_buffer` for every
  operation, contains no product state, and uses MSVC full-fence Interlocked
  intrinsics as a permitted stronger ordering.
- requirement basis: batch-027 exact 32-byte mapping header and normal/recovery
  atomic protocol.
- rejected: Python locks, GIL-based cross-process correctness, non-atomic
  `ctypes` reads/writes, undocumented DLL-symbol lookup, and a native product
  core.
- cost: CPython/Windows-x64-specific wheel and native ABI verification.
- failure prevented: torn fields, lost transitions, false stable snapshots, and
  recovery races.

### IDR-026 — Mapping-header recovery state machine

- decision: every mapping starts with the exact 32-byte header; slots begin at
  `32 + i*4352`; sizes are 8,736, 8,736, 4,456,480, 4,456,480; aggregate is
  8,930,432. Normal transitions follow the exact count/freeze/sequence/slot
  CAS protocol. Recovery claims one generation, freezes irreversibly, and may
  normalize crash-left count/odd sequence only after all mutators are exited or
  identity-absent.
- requirement basis: batch-027 normative mapping layout and TRAR recovery
  sections.
- rejected: slot offset zero, process-local locks, alive-QUIESCED normalization,
  state synthesis, and thaw to RUNNING.
- cost: native atomic ABI, cross-process model/stress tests, and larger mapping
  fixtures.
- failure prevented: an apparently stable recovery snapshot while a mutator can
  still change evidence state.

### IDR-027 — ETW certification separation

- decision: real kernel ETW DiskIo events exist only in the external Windows
  release-certification harness. They are not runtime, readiness, recovery, or
  session inputs. Missing, lost, unattributed, or ambiguous events make that
  certification not-passed. Synthetic events certify parser logic only.
- requirement basis: batch-027 normative external-certification boundary.
- rejected: production service ETW dependency and synthetic release evidence.
- cost: release certification requires a capable Windows host and retained raw
  events.
- failure prevented: runtime availability depending on a measurement facility
  and false performance certification.

### IDR-028 — Authority rebase checkpoint

- decision: historical I00/batch-024 remains immutable. `TR-I00R` replaces
  packaged authority and plan assets with batch-027/batch-010 bytes, updates
  identity/inventory/contract tests, proves package parity, and still contains
  no I01 runtime behavior.
- requirement basis: user-confirmed batch-027 and source baseline containing
  only completed I00.
- rejected: relabelling old evidence, editing historical snapshots, or starting
  I01 against stale assets.
- cost: one extra recoverable checkpoint.
- failure prevented: code built against requirements different from its
  packaged/self-reported authority.

### IDR-029 — Startup-authority I/O ownership

- decision: the transient startup coordinator is the only execution and OS-call
  owner for `TRII/1`, `TRIC/1`, and `TRIM/1` path resolution, deterministic
  create-new attempts, explicit-offset exact-single writes, flushes, witness
  positive-progress fills, readbacks/reopens, and final-handle identity checks.
  These calls use the frozen terminal-overlapped primitives directly, without
  an ordinary worker, mailbox, helper process, or hidden queue. I03 delivers
  its entrypoint/state shell and sole `TRII/1` call sites. I05 extends the same
  coordinator after `TRII_SELECTED`, resolves both IPC paths through the exact
  81-pair table, and completes selected `TRIC/1` before Job/child/IPC
  allocation; the sole `TRIM/1` append to that selected file begins only after
  holder proof. Post-proof child loss cannot cancel it.
- requirement basis: TR-F-009, TR-F-066, batch-027 normative bootstrap order,
  and batch-008 finding C-001.
- rejected: assigning pre-`TRIM/1` authority writes to `MONITOR_STORAGE`,
  starting an ordinary worker early, or adding a ninth worker/helper.
- cost: the transient coordinator retains authoritative I/O resources through
  terminal completion and needs the full real-Windows fault matrix.
- failure prevented: a causal startup cycle, silent topology expansion, or
  readiness after an unclassified authority-write result.

### IDR-030 — Verifier input preflight

- decision: verifier preflight is independent of runtime three-root admission.
  It accepts exactly one absolute, readable, supported-filesystem,
  self-contained session directory; write access is neither requested nor
  required. It opens final and role handles read-only with no share-delete,
  proves final-handle identity/containment/reopen, and rejects any path-to-final
  junction, symbolic link, mount point, or other reparse traversal with exact
  `INPUT_ERROR` before evidence evaluation. Runtime evidence/alarm/installation
  roots and current process state are never inputs.
- requirement basis: TR-F-058, TR-F-059, TR-AC-003, normative section 10.1,
  and batch-008 finding R-003.
- rejected: requiring writable verifier input, inheriting runtime root reparse
  rules, or consulting live external state.
- cost: a separate read-only preflight path and direct/reparse/read-only copied
  bundle test matrix.
- failure prevented: rejecting valid read-only copied evidence or accepting a
  path form the frozen contract classifies as `INPUT_ERROR`.

### IDR-031 — Startup coordinator phase ownership

- decision: I03 first delivers `entrypoints/start.py`,
  `runtime/coordinator.py`, and `runtime/installation_authority.py`. Its
  coordinator scope ends at `TRII_SELECTED` or terminal failure and contains
  every `TRII/1` call site, but no IPC, Job, child, bootstrap, mapping, event,
  worker, lease, or readiness path. I05 extends the same entrypoint/coordinator
  after `TRII_SELECTED` and first delivers `ipc_authority.py`, bootstrap, and
  process orchestration. I05 preserves I03 evidence byte-for-byte and creates
  fresh current-source evidence after rerunning the complete I03 regression
  gate.
- requirement basis: executable phase ordering, batch-009 finding C-003, and
  the batch-027 startup order.
- rejected: requiring I03 to prove an I05-delivered coordinator, postponing all
  coordinator ownership to I05, or backfilling earlier evidence.
- cost: I03 exposes a deliberately bounded pre-IPC coordinator slice and I05
  reruns its regression matrix after extending shared source files.
- failure prevented: a dependency cycle, premature I03 PASS, stale evidence,
  or a later phase relabelling missing earlier artifacts.

### IDR-032 — IPC attempt selection cardinality

- decision: each logical IPC intent has exact deterministic `a0` and `a1`
  paths. Guards classify both paths before the complete 81-pair action table.
  Only `(TRIC_INCOMPLETE,ABSENT)` and `(TRIC_UNWITNESSED,ABSENT)` return
  `CREATE_A1`; at most one table-selected create-new action executes at a time.
  `SELECT_A0` or `SELECT_A1`, or a newly committed create action, identifies
  the sole selected `TRIC/1` file. After holder proof, exactly one `TRIM/1`
  append attempt targets that file. “One deterministic attempt file” means the
  selected two-record chain, not one reserved path or one lifetime create
  action.
- requirement basis: TR-F-066, normative IPC 81-pair table, and batch-009
  finding G-003.
- rejected: stopping after every failed `a0`, creating `a1` from any other
  `a0` state, concurrent create attempts, or writing `TRIM/1` to both paths.
- cost: exact table/static validation and a real-Windows two-path crash/action
  matrix.
- failure prevented: rejecting legal attempt-one recovery, violating path
  exhaustion authority, selecting two intents, or duplicating the manifest.

## Decisions requiring final user confirmation

The final plan confirmation accepts:

1. the transient-coordinator plus two no-SCM long-lived child model;
2. the three user-selected roots, current-runtime-context scope, and exact
   `TRII/1` installation authority;
3. zero third-party runtime dependencies plus the bundled minimal
   `_winatomic.pyd`;
4. the exact custom control/journal/state/report schemas and bound hashes;
5. the fixed eight-worker and Job-at-creation topology;
6. the 32 MiB WAITING versus 6 GiB ACTIVE reservation model;
7. the separated alarm reservations, batch-027 fixed formats, `TRBH/1`,
   deterministic IPC `a0`/`a1` 81-pair resolver, selected-file manifest chain,
   32-byte mapping header, pinned-slot protocol, and two-phase IPC recovery;
8. the exact deterministic golden/mutation corpus, relation graph and deadline matrix,
   and prohibition on shared generator/codec code;
9. the four Python build/test dependencies, Windows compiler/SDK build
   boundary, and exact lock evidence;
10. the `TR-I00R` rebase, I03/I05 startup-coordinator phase ownership, thirteen
    original implementation phases, and release gates;
11. the trusted-user functional boundary and external-only ETW certification.

Any later change requires a reviewed plan amendment.
