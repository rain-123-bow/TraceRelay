# TraceRelay v1 Normative Contracts

## 1. Status and precedence

This file is a normative part of `REQUIREMENT_DESIGN_DRAFT.md`.

The requirement set consists of:

1. `REQUIREMENT_DESIGN_DRAFT.md`;
2. this file;
3. `support-profile.windows-local-v1.json`;
4. `reason-exit-catalog.v1.json`;
5. `traceability-matrix.v1.json`.

If prose can be read in more than one way, the narrower evidence claim wins.
If two normative files conflict, this file wins over the main draft, and the
machine-readable support profile or reason catalog wins for values in its
declared field domain. Any unresolved conflict is a requirement defect and
blocks implementation.

## 2. Terms and evidence claim

| Term | Normative meaning |
|---|---|
| observed bytes | Bytes returned to TraceRelay by a supported source-side OS read operation. |
| OS-accepted bytes | The exact positive byte count returned by a supported destination-side OS write operation. This does not prove remote application receipt, consumption, or durable storage. |
| committed record | One complete canonical record whose pre-witness bytes validate and whose fixed trailer contains the exact complete `TRFW/1` post-flush witness defined in section 3.3. This offline status is determined only from self-contained observable bytes. |
| committed-record SHA-256 | SHA-256 of all bytes of one complete record including its exact valid `TRFW/1` witness. Every field described as a complete-record, previous-record, referenced-record, or emitted-record digest uses this value unless it explicitly says `pre_witness_record_digest`. |
| committed prefix | The longest contiguous sequence of valid committed records beginning at sequence zero. |
| partial tail | The first structurally unfinished or uncommitted suffix after a committed prefix. It includes a short record and a complete-length record whose `TRFW/1` witness is absent or a valid strict prefix. A complete-length malformed record or malformed witness is invalid rather than partial. |
| unknown write outcome | A `WRITE_ATTEMPT` was durably authorized, but no supported OS result was durably recorded before loss of execution continuity; the call may or may not have entered the OS. |
| authorized write attempt | A committed `WRITE_ATTEMPT` grants exactly one worker permission to enter one destination OS write call for the bound half-open range. It proves that the call could have entered the OS; it does not prove that it did. |
| clean session | A session satisfying every predicate in section 7.5. |
| incomplete session | A structurally valid session with a known non-clean condition. |
| invalid evidence | Input bytes violate a normative identity, framing, digest, sequence, range, or state invariant. |
| application payload | Bytes after a successful `ClientHello.v1` exchange. Authentication prelude and TraceRelay responses are control bytes, never application payload. |
| publication | A channel accepts an alarm according to section 9. This does not prove operator receipt. |
| supported runtime context | One current Windows user and one Windows logon session. v1 singleton and ACTIVE cardinality are enforced only inside this context. |
| installation | One committed `TRII/1` identity bound to one absolute installation runtime root and the supported runtime-context attribution recorded when it was created. |
| logical bundle identity | The immutable session, installation, schema, profile, and origin-directory facts committed when the bundle was created. It remains the verification identity after an exact directory copy. |
| IPC holder-proof point | The single kernel wait-criteria evaluation represented by exact `WaitForMultipleObjects(2, [service-process, monitor-process], FALSE, 0) == WAIT_TIMEOUT`, after bootstrap closure and exact process-identity and Job-membership revalidation. |
| acknowledged holder-proof snapshot | The byte-exact 28-handle inventory acknowledged by both children and proven by the IPC holder-proof point. It states holder ownership at that logical point only. |
| ready IPC manifest | A committed `TRIM/1` that durably records the acknowledged holder-proof snapshot. It does not assert that either child is live at manifest commit time or query time. |

TraceRelay claims only:

- which application-payload bytes it observed at each proxy source boundary;
- which byte ranges a local destination OS write call reported as accepted;
- which control, monitor, alarm, and lifecycle facts its components committed;
- whether the supplied evidence bundle satisfies the frozen verification
  predicates.

TraceRelay does not claim:

- remote application receipt, parsing, use, acknowledgement, or storage;
- absence of bypass traffic;
- correctness of client or upstream behavior;
- trusted wall-clock time;
- resistance to malicious local users or processes, the owner user, another
  user, Windows administrator, SYSTEM, kernel, filesystem, or storage hardware
  acting adversarially.

## 3. Supported failure model and durable commit

### 3.1 Supported failures

The v1 positive durability claim covers:

1. abrupt termination of the TraceRelay service process;
2. abrupt termination of the monitor, verifier, client, or upstream process;
3. returned Windows file, socket, pipe, capacity, or permission errors;
4. a TraceRelay worker that stops making declared progress;
5. orderly Windows shutdown and restart after the durable-commit operation
   returned success.

The v1 positive durability claim excludes:

1. sudden loss of electrical power;
2. Windows kernel crash, bugcheck, or kernel deadlock;
3. filesystem, storage-controller, firmware, or media corruption;
4. a device that falsely reports completed flushes;
5. malicious local-user/process, owner-user, administrator, or SYSTEM
   tampering;
6. whole-host destruction or replacement.

Excluded failures may produce `INCOMPLETE`, `INVALID`, `INPUT_ERROR`, or
`INTERNAL_ERROR`. They may never produce a relaxed `PASS`.

### 3.2 Evidence namespace durability

Before a session credential is issued, TraceRelay shall:

1. create a new canonical session directory beneath the configured evidence
   root using create-new semantics;
2. reject any pre-existing session target, path escape, unsupported final
   target, or final-handle identity mismatch;
3. create the immutable profile and identity files using create-new semantics;
4. create the service and monitor journals using create-new semantics;
5. flush each created authoritative file;
6. close and reopen the files by their canonical identity;
7. commit a `SESSION_CREATED` record containing the logical bundle identity,
   the original canonical directory path and Windows file identity as origin
   facts, and hashes of the frozen profile, reason catalog, and schema
   bindings.

Failure of any step prevents credential issuance and payload forwarding.
Recovery never reuses a partially created namespace for a new session.
After an exact copy, the copied directory's current path and Windows file
identity are not compared to the origin facts for `PASS`. The immutable
logical bundle identity, committed bytes, and digest bindings remain
authoritative. The verifier still rejects internal path escapes, unexpected
reparse objects inside the product-created bundle, and duplicate or
contradictory logical identities.

### 3.3 Record commit boundary

Every canonical record reserves trailer bytes `116..159` for one fixed
44-byte `TRFW/1` post-flush witness. The writer first constructs and writes the
complete pre-witness record with this block zero. The trailer digest at offset
84 is:

```text
pre_witness_record_digest =
  SHA-256(
    prefix ||
    body ||
    trailer with bytes 84..159 zero
  )
```

Each authoritative journal file is created with create-new semantics,
`GENERIC_READ | GENERIC_WRITE`, and share mode zero, then owned by exactly one
writer until close. Every record and witness write uses an explicit validated
file offset; current-file-position side effects are not authority. An
authoritative-journal overlapped operation uses an initially nonsignaled
auto-reset event and retains its `OVERLAPPED`, event, buffer, and file handle
until one terminal completion is observed. This event rule is limited to the
authoritative-journal primitive; `TRBH/1` uses the manual-reset operation events
defined in section 9.2.2. `CancelIoEx` requests cancellation but is not terminal
proof; the owner must obtain terminal completion with `GetOverlappedResultEx`
or terminate and observe the isolated owner process before releasing those
objects. No
out-of-band "final status" bytes may be appended; any status is another complete
canonical record.

Every ordinary pre-witness `WriteFile` must return the complete requested byte
count. A positive short return, zero progress, error, or deadline poisons that
record attempt; the writer does not retry the suffix, append another record, or
authorize an external action from that attempt. Only after the complete
pre-witness record has been written does the writer call `FlushFileBuffers` on
the authoritative file. Only after that call returns success may it issue the
witness write. The exact witness bytes are:

```text
offset 116, 4 bytes: ASCII "TRFW"
offset 120, 8 bytes: enclosing journal sequence as le_u64
offset 128, 32 bytes:
  SHA-256(
    ASCII "TRFW/1-FLUSH-RETURN" ||
    le_u64(enclosing journal sequence) ||
    pre_witness_record_digest[32]
  )
```

The writer seeks to the witness offset and writes the 44 bytes in ascending
order. It permits at most 44 positive-progress writes. A zero-progress return,
error, deadline, process loss, or short final result before all 44 bytes have
returned consumes that record attempt and authorizes no external action. The
writer never appends a later record until the current witness is closed.

The witness fill is the only legal in-place mutation of an authoritative
journal. It may change only the current record's still-zero witness bytes to
the exact expected prefix, once and in ascending order. The writer may not
rewrite, clear, repair, resume, or replace any witness byte or any earlier
record byte. In every other respect, authoritative journals remain append-only.

After all 44 witness bytes return successfully, the live writer reads back the
same range through the rooted authoritative handle and requires byte equality.
Only then is the live record committed and able to authorize forwarding,
destination calls, readiness, release, publication, or another externally
observable action. A readback failure is fail-closed.

Recovery and the offline verifier classify the stable 44-byte block without
using process memory, return values, logs, side files, or another acknowledgement
record:

| Witness state | Exact observable condition | Offline authority |
|---|---|---|
| `WITNESS_ABSENT` | all 44 bytes are zero | structurally valid uncommitted tail |
| `WITNESS_PARTIAL` | the block is not the full expected witness; for some `k` in `1..43`, bytes `0..k-1` equal the expected witness prefix and bytes `k..43` are zero | structurally valid uncommitted tail |
| `WITNESS_VALID` | all 44 bytes equal the expected witness | committed record when every other record validation succeeds |
| `WITNESS_INVALID` | any other byte pattern | invalid evidence |

`WITNESS_VALID` proves that the supported writer entered the witness write
after observing a successful durable-flush return. The witness write does not
recursively require a second flush-return acknowledgement. Under the supported
process-crash model, complete visible witness bytes are the offline authority
even if the process died before the witness `WriteFile` returned. This may
prove authorization without proving that a later external call executed. Power
loss, kernel failure, storage corruption, false flush acknowledgement and
owner/administrator mutation remain excluded by section 3.1.

After `WITNESS_VALID`, the committed-record SHA-256 is computed over the full
record including the witness. Digest chains and all fields described as the
SHA-256 or digest of a complete committed record use this full value. The
trailer field at offset 84 and the witness preimage alone use
`pre_witness_record_digest`; the two digests are distinct and never
interchangeable.

An ordinary buffered write, language-runtime flush, close request, queued
write, zero witness block, partial witness, in-memory flag, or mutable side
file is not a committed record.

Before every destination OS write call, the service shall durably commit one
`WRITE_ATTEMPT` containing:

1. a unique attempt ID;
2. parent `DATA_INTENT` sequence;
3. session, connection, and direction;
4. exact half-open attempted range;
5. the current known accepted-prefix end;
6. the worker-incarnation and one-use execution grant.

Only the bound worker may consume the grant, exactly once. No destination call
may be entered without the committed grant. A committed attempt without a
committed outcome means only that the exact range was authorized and may have
entered the OS; it is an unknown outcome. It does not assert that the syscall
executed or that any byte was remotely received. Such a range is never replayed
and always prevents `PASS`.

The journal is the sole authority for sequence and digest-chain state. A
mutable side file or in-memory counter cannot upgrade uncommitted bytes into a
committed record.

### 3.4 Recovery rule

Recovery scans without modifying historical files. It identifies:

- the longest valid committed prefix;
- any partial tail after that prefix, including a complete-length record with
  absent or partial `TRFW/1`;
- the last committed lifecycle, monitor, alarm-link, and byte-accounting
  facts;
- any attempted write whose outcome is absent.

A partial tail is retained. Recovery never truncates, repairs, appends, or
continues the old journal. A session without a committed clean terminal record
is not clean. A restarted service creates a new session and new credential.

### 3.5 Required durability tests

The Windows product gate shall include:

1. service process termination before, during, and after every record field,
   pre-witness trailer, durable flush boundary, witness byte, witness-write
   return, and witness readback;
2. termination before the `WRITE_ATTEMPT` commit, proving no destination call
   is permitted;
3. termination after `WRITE_ATTEMPT` commit but before call entry, which leaves
   the exact attempted range unknown;
4. termination while the call may be executing, which leaves that range
   unknown;
5. termination after a call returns but before its outcome commits, which
   leaves that range unknown;
6. termination after outcome commit, which preserves the exact known result;
7. orderly Windows restart after a committed record;
8. injected open, short-write, write, flush, close, capacity, and permission
   failures;
9. every-byte tail truncation fixtures;
10. the frozen crash oracle below:

| Crash window | Observable witness | Offline result | Live external action |
|---|---|---|---|
| complete pre-witness write; before or during flush | absent | uncommitted / non-PASS | forbidden |
| flush completed internally but return not observed | absent | uncommitted / non-PASS | forbidden |
| flush success returned; before first witness byte | absent | uncommitted / non-PASS | forbidden |
| after witness bytes `1..43` become visible | valid strict prefix | uncommitted / non-PASS | forbidden |
| exact full witness becomes visible | valid | committed if all other validation succeeds | still forbidden until the live write return and readback both succeed |
| live witness write return and readback succeed | valid | committed | permitted subject to the record-specific gate |

The first three rows are intentionally byte-identical and intentionally have
the same offline non-PASS result. A hidden flush-return difference never
changes offline classification.

Power-loss or kernel-crash tests may be exploratory only and cannot expand the
v1 positive claim.

## 4. `LOCAL_LOOPBACK_TCP_V1` transport contract

### 4.1 Endpoint scope

- Client-facing endpoint: TCP bound only to IPv4 loopback `127.0.0.1`.
- Upstream endpoint: TCP IPv4 loopback `127.0.0.1` plus an explicit port.
- A wildcard, non-loopback, hostname-resolved, remote, Unix, WSL, or tunneled
  endpoint is unsupported.
- Before claim, one session permits at most the profile authentication-attempt
  count of sequential accepted TCP attempt connections. At most one attempt may
  be in `AUTHENTICATING`; an additional simultaneous accept is rejected as
  busy and does not consume an attempt.
- Every accepted attempt receives a unique attempt-connection ID. Exactly one
  successful credential claim may create the session's application connection
  ID and exactly one upstream connection.
- A failed pre-claim attempt is closed before the session returns to
  `WAITING`. After claim, reconnection under the same session ID is prohibited.

### 4.2 Authentication framing

For each accepted pre-claim attempt, the client first sends exactly one ASCII
line:

`TRACERELAY/1 <session-id> <credential>\n`

Rules:

- total line length is at most the support-profile value;
- no `CR`, NUL, non-ASCII byte, extra field, or leading/trailing space is
  allowed;
- `session-id` is the canonical lowercase UUID text issued by control;
- `credential` is the issued base64url text without padding;
- the client shall wait for a TraceRelay response before sending application
  payload;
- bytes after the newline received before a success response cause rejection
  with `TR-TRANSPORT-EARLY-PAYLOAD`;
- the authentication line and TraceRelay response are not forwarded upstream
  and are not part of raw application-payload evidence.

Success response:

`OK TRACERELAY/1 <session-id> TR-TRANSPORT-ACTIVATED\n`

Failure response:

`ERR TRACERELAY/1 <stable-reason-id>\n`

The failure response is best-effort, contains no credential, and is followed
by connection close. A failure never connects upstream or forwards payload.
The success response acknowledges only session activation; TraceRelay emits no
application-payload acknowledgement.

### 4.3 Activation order

Before sending `OK`, the service shall, in order:

1. validate framing and credential;
2. atomically claim the credential and the runtime-context ACTIVE slot;
3. confirm evidence bundle readiness and a valid monitor lease;
4. connect exactly once to the registered loopback upstream;
5. commit `CONNECTION_ACTIVE` with client, upstream, and connection identities.

An invalid pre-claim hello follows the retry truth table in section 5.4. Any
failure after credential claim closes the session as incomplete. A claimed
credential is never returned to `ISSUED`.

### 4.4 Full-duplex behavior

- Each direction has an independent source offset beginning at zero.
- Byte value and direction order are preserved.
- The service may coalesce adjacent OS reads into one evidence intent up to the
  record limit; OS read chunking is not evidence semantics.
- No payload byte is written to a destination until the covering intent record
  is committed.
- A positive OS write return commits an accepted range outcome.
- A zero or error return commits a zero-progress failure when known.
- If execution continuity is lost after call entry but before a committed
  result, the outcome is unknown.
- A short write permits attempts only for the not-yet-accepted suffix. It does
  not replay accepted bytes.

### 4.5 EOF, half-close, error, and zero-byte behavior

- Source EOF is committed before propagating a send-side half-close to the
  opposite socket.
- After one direction reaches EOF, the opposite direction remains open until
  its own EOF, a failure, or the drain deadline.
- Reset, aborted connection, non-timeout socket error, monitor loss, journal
  failure, or deadline expiry stops new reads and new forwarding in both
  directions and closes incomplete.
- A zero-payload connection may close cleanly only after successful activation,
  both directional EOF events, complete empty accounting, continuous
  monitoring, and a committed clean terminal record.
- Idle time alone does not close an ACTIVE session before the maximum session
  duration. Polling and health checks remain bounded.

## 5. Identity, registration, session, and connection state

### 5.1 Identity rules

Application ID, registration ID, session ID, connection ID, service
incarnation ID, monitor incarnation ID, and upstream identity are separate
fields. No display name or opaque client metadata is identity authority.

The upstream identity is a service-generated ID bound to the registered
`127.0.0.1:port` tuple and the one resulting socket connection. It does not
claim operating-system process identity. Client identity at the data boundary
is the issued session, authenticated connection ID, and observed socket tuple;
it does not claim which Windows process owns the socket.

One registration creates exactly one session and one credential. Registration
and credential are not reusable.

### 5.2 Registration and credential states

An application identity is `ENABLED` or `DISABLED`. Only `ENABLED` may create
a registration. Disable is a current-instance local control mutation; it prevents new
registrations and revokes nonterminal registrations but does not alter
historical session evidence. Deletion is allowed only by section 12.

| Credential state | Entry | Allowed exit |
|---|---|---|
| `ISSUED` | Session namespace and `SESSION_CREATED` are committed; credential returned once. | `CLAIMED`, `EXPIRED`, or `REVOKED`. |
| `CLAIMED` | Valid hello atomically wins before expiry/revocation and reserves ACTIVE. | Permanent credential state; never reusable. Later session revoke/close changes the session, not this credential state. |
| `EXPIRED` | Monotonic activation deadline wins before claim. | Terminal. |
| `REVOKED` | Authorized revocation wins before claim. | Terminal. |

Session-token plaintext follows the functional lifecycle in section 11.3. No
credential state permits intentional plaintext persistence by TraceRelay.

### 5.3 Session states

| State | Meaning | Allowed next state |
|---|---|---|
| `CREATING` | New namespace and initial records are being created. | `WAITING`, `TERMINAL_INCOMPLETE`. |
| `WAITING` | Credential issued; no client connection claimed. | `AUTHENTICATING`, `TERMINAL_INCOMPLETE`. |
| `AUTHENTICATING` | One accepted attempt is under bounded hello validation. | `WAITING`, `CONNECTING_UPSTREAM`, `TERMINAL_INCOMPLETE`. |
| `CONNECTING_UPSTREAM` | Credential consumed; one bounded upstream connect is in progress. | `ACTIVE`, `TERMINAL_INCOMPLETE`. |
| `ACTIVE` | Activation record committed and success response sent. | `DRAINING`, `TERMINAL_INCOMPLETE`. |
| `DRAINING` | No new source reads; bounded known work is being resolved. | `TERMINAL_CLEAN`, `TERMINAL_INCOMPLETE`. |
| `TERMINAL_CLEAN` | All clean predicates and terminal record committed. | None. |
| `TERMINAL_INCOMPLETE` | A known non-clean terminal reason committed. | None. |
| `TERMINAL_UNKNOWN` | Recovery cannot prove a committed terminal record. This is a verifier/recovery observation, never a writer transition. | None. |

### 5.4 Automatic transitions

Operator-originated create, inspect, revoke, close, stop, alarm query,
deletion, and application disable operations require the authorized
control plane. v1 has no live configuration mutation command; roots and the
frozen profile are selected before service readiness. The service shall
perform these automatic transitions without a control command:

| Trigger | Required transition |
|---|---|
| activation expiry before claim | `WAITING -> TERMINAL_INCOMPLETE` |
| accepted TCP attempt | durably increment attempt count exactly once and `WAITING -> AUTHENTICATING` |
| simultaneous attempt while `AUTHENTICATING` | reject busy; do not increment attempt count; state unchanged |
| malformed hello, invalid credential, authentication timeout, or disconnect before a valid claim | close attempt; `AUTHENTICATING -> WAITING` if committed attempt count is below the limit, otherwise `AUTHENTICATING -> TERMINAL_INCOMPLETE` |
| valid credential on the final permitted attempt | claim wins if no higher-priority event is pending; the attempt limit does not independently terminate a valid claim |
| upstream connect failure | `CONNECTING_UPSTREAM -> TERMINAL_INCOMPLETE` |
| bilateral clean EOF with complete accounting | `ACTIVE -> DRAINING -> TERMINAL_CLEAN` |
| reset, disconnect error, or session deadline | current nonterminal state -> `TERMINAL_INCOMPLETE` |
| persistence failure | current nonterminal state -> stop forwarding -> `TERMINAL_INCOMPLETE` if terminal commit remains possible |
| monitor lease loss | current nonterminal state -> stop forwarding -> `TERMINAL_INCOMPLETE` |
| service stop | current nonterminal state -> `DRAINING`, then clean only if clean predicates were already achievable; otherwise incomplete |
| service crash/restart | recovery observes `TERMINAL_UNKNOWN` unless a terminal record was already committed |
| root/session/profile limit reached | stop reading before the limit, then incomplete |

Every committed terminal lifecycle uses this catalog mapping:

| Terminal cause | Stable lifecycle reason |
|---|---|
| full clean predicate | `TR-LIFECYCLE-CLEAN` |
| activation expiry | `TR-LIFECYCLE-ACTIVATION-EXPIRED` |
| failed final authentication attempt | `TR-LIFECYCLE-AUTH-ATTEMPT-LIMIT` |
| upstream connect failure | `TR-LIFECYCLE-UPSTREAM-CONNECT-FAILED` |
| transport reset/error | `TR-LIFECYCLE-TRANSPORT-ERROR` |
| maximum session duration | `TR-LIFECYCLE-SESSION-DEADLINE` |
| persistence failure | `TR-LIFECYCLE-PERSISTENCE-FAILED` |
| monitor lease or critical-progress failure | `TR-LIFECYCLE-MONITOR-LOST` |
| resource limit | `TR-LIFECYCLE-RESOURCE-LIMIT` |
| operator close | `TR-LIFECYCLE-OPERATOR-CLOSED` |
| revocation/application disable | `TR-LIFECYCLE-OPERATOR-REVOKED` |
| service stop before clean | `TR-LIFECYCLE-SERVICE-STOP` |

Operator mutation truth table:

| Command/event | `CREATING` | `WAITING` | `AUTHENTICATING` | `CONNECTING_UPSTREAM` | `ACTIVE` | `DRAINING` | terminal |
|---|---|---|---|---|---|---|---|
| `close` | not externally addressable before create response | revoke issued credential; commit incomplete terminal | close attempt; commit incomplete terminal | cancel or isolate connect worker; commit incomplete terminal | stop new reads and forwarding; drain only already-known work; commit incomplete terminal | force incomplete terminal | idempotent success with existing terminal reason |
| `revoke` / application disable | same as `close` when addressable | credential becomes `REVOKED`; incomplete terminal | close attempt; incomplete terminal | credential remains `CLAIMED`; incomplete terminal | credential remains `CLAIMED`; incomplete terminal | credential remains `CLAIMED`; incomplete terminal | idempotent status; historical evidence unchanged |
| graceful service stop | fail create and preserve any committed prefix | incomplete terminal | close attempt; incomplete terminal | cancel or isolate worker; incomplete terminal | enter bounded `DRAINING`; clean only if bilateral EOF and all clean predicates had already become true before stop won | finish within drain budget; otherwise incomplete | no state change |

Every row is serialized with the priority in section 5.5. A positive mutation
response is sent only after the resulting lifecycle fact commits.

### 5.5 Atomicity and race priority

The service serializes session lifecycle decisions under the runtime-context
ACTIVE authority. Priority from highest to lowest:

1. evidence-commit failure;
2. monitor lease loss or declared critical-path failure;
3. service forced stop;
4. transport reset/error or resource deadline;
5. authorized revocation/close;
6. maximum session duration;
7. bilateral clean EOF;
8. activation expiry;
9. the completed authentication decision for the current attempt.

Expiry and claim compare one monotonic timestamp inside the same atomic
decision. The boundary is exclusive: a claim decision at or after expiry
loses. Claim wins only before expiry and when no higher-priority event is
pending. Attempt-limit termination is evaluated only after an authentication
failure; it cannot defeat a valid final permitted attempt. Of concurrent
connections, the serialized accepted attempt is the only claim candidate;
busy rejects cannot claim. The evidence directory is created in `CREATING`,
before credential issuance. Every transition is committed before a
corresponding positive control result.

### 5.6 Monotonic deadline anchors

All lifecycle deadlines use one Windows monotonic counter and exclusive
deadlines: an event observed at `now >= deadline` is late.

| Deadline | Committed anchor |
|---|---|
| activation expiry | the monotonic timestamp in `CREDENTIAL_ISSUED`, committed before the credential response |
| authentication | `AUTH_ATTEMPT_STARTED`, committed when the attempt count is incremented after TCP accept |
| upstream connect | `CONNECTING_UPSTREAM`, committed after claim and before worker dispatch |
| maximum session duration | `CONNECTION_ACTIVE`, committed immediately before the `OK` response |
| drain | `DRAINING`, committed before new reads stop being acknowledged as accepted work |
| deletion completion | committed `DELETE_INTENT` |
| control response | receipt of the complete authenticated control request |

The timestamp, counter frequency, configured duration, and resulting deadline
are committed together. Restart never resumes a nonterminal deadline. Race
tests shall place each event one tick before, exactly at, and one tick after
the deadline.

## 6. Byte-range accounting

### 6.1 Range identity

Every payload fact is identified by:

`(session_id, connection_id, direction, start_offset, end_offset)`

Ranges are half-open: `[start_offset, end_offset)`. For each direction:

- the first observed range begins at zero;
- observed ranges are contiguous and non-overlapping;
- `end_offset > start_offset`;
- payload length equals `end_offset - start_offset`;
- range payload digest and raw bytes are committed together.

### 6.2 Intent and outcome

One committed `DATA_INTENT` contains one observed range and its raw bytes. Each
destination call first receives the durable `WRITE_ATTEMPT` grant defined in
section 3.3. A committed outcome binds exactly one committed attempt and
contains:

- attempt ID;
- parent intent sequence;
- attempted subrange;
- OS result category;
- exact OS-accepted count when known;
- accepted subrange when positive;
- error code when known.

Attempts for one direction are serialized. A new attempt cannot be granted
while the prior attempt lacks an outcome. An attempted byte cannot precede its
observation or be attempted after known acceptance.

### 6.3 Conservation rules

For direction `d`:

- `O_d` is the union of committed observed ranges;
- `T_d` is the ordered multiset of ranges in committed `WRITE_ATTEMPT` records;
- `A_d` is the union of known OS-accepted ranges;
- `U_d` is the union of attempted ranges with unknown outcomes.

The verifier shall establish:

1. `A_d subseteq O_d`, `U_d subseteq O_d`, and `A_d intersection U_d` is
   empty;
2. every element of `T_d` is a subset of exactly one committed intent in
   `O_d`;
3. every attempt has zero or one outcome; an attempt without an outcome
   contributes its entire range to `U_d`;
4. a known positive outcome with count `n` contributes exactly the attempted
   range's first `n` bytes to `A_d`; `0 < n <= attempted_length`;
5. a known zero-progress or error outcome contributes no bytes to `A_d` or
   `U_d`; a non-timeout transport error terminates incomplete;
6. `A_d` is a contiguous, non-overlapping prefix of `O_d`;
7. no element of `T_d` overlaps the accepted prefix known before that attempt;
8. after a short write, the next attempt, if any, begins at the first
   not-known-accepted offset and is confined to the prior suffix;
9. no attempt follows an unknown outcome, and an unknown range is never
   replayed.

`PASS` requires, for both directions:

- `U_d` is empty;
- `A_d = O_d`;
- both source EOF events are committed;
- all lifecycle and monitoring predicates in section 7.5 are true.

An unknown outcome poisons the affected session for `PASS`. TraceRelay does not
infer delivery from later traffic and does not replay the range.

Normative vectors:

| Case | Committed facts | Required accounting |
|---|---|---|
| empty stream | bilateral EOF; no intent or attempt | `O=A=U=empty`; eligible for clean if all other predicates hold |
| full success | intent `[0,4)`, attempt `[0,4)`, outcome `4` | `O=A=[0,4)`, `U=empty` |
| short write | intent `[0,4)`, attempt `[0,4)` outcome `2`, attempt `[2,4)` outcome `2` | `O=A=[0,4)`, `U=empty` |
| zero progress | intent `[0,4)`, attempt `[0,4)` outcome `0` | `O=[0,4)`, `A=U=empty`, session incomplete |
| unknown | intent `[0,4)`, attempt `[0,4)`, no outcome | `O=U=[0,4)`, `A=empty`, session incomplete and no replay |

## 7. Self-contained evidence bundle

### 7.1 Required files

One absolute session directory is the only verifier input. It contains:

1. immutable `bundle-manifest`;
2. the exact frozen `support-profile`;
3. the exact frozen `reason-exit-catalog`;
4. `service-journal`;
5. `monitor-journal`;
6. known-session `alarm-publication-observations`, manifest-bound as an
   explicit logical role even when physically encoded inside the service or
   monitor journal;
7. session-bound alarm linkage and channel outcomes;
8. version and compatibility bindings;
9. raw application payload inside committed service records.

Exact filenames and binary encoding are implementation-plan decisions, but the
roles, identities, hashes, and self-contained semantics above are mandatory.
The verifier shall not consult current service state, registry state, alarm
root, network state, caller-selected profile, or wall clock to determine its
result.

The bundle manifest distinguishes the logical bundle identity and immutable
origin-directory facts from the copied directory's current path and Windows
file identity. Exact copying is supported; relocation alone does not change
integrity or `PASS`.

### 7.2 Profile authority

The first committed service record and bundle manifest bind the exact bytes and
SHA-256 digest of the frozen support profile. The verifier uses only that
profile copy. A caller cannot select or override a profile.

### 7.3 Monitor and alarm binding

The monitor journal is written by the monitor directly into the session bundle
and binds:

- session, service-incarnation, and monitor-incarnation IDs;
- lease issue, renew, expiry, and closure events;
- heartbeat sequence and critical-progress observations;
- alarm IDs and channel-attempt outcomes;
- last observed service journal position and digest when available.

For a known-session alarm, the bundle's
`alarm-publication-observations` role is the offline verifier's only
publication authority. For a session-unknown alarm, the detector-owned alarm
journal is runtime recovery/query authority. Both use the exact `TRAO/1`
tagged-union record below; fields are required only by their variant, never by
an untagged "every observation" rule.

### 7.3.1 `TRAO/1` canonical observation serialization

Every `TRAO/1` record is:

```text
3936-byte fixed prefix
+ variant body
+ 160-byte fixed commit trailer
= 4096-byte fixed envelope + variant body
```

All integers are unsigned little-endian. IDs are the exact 16 CSPRNG bytes
generated by the product; no GUID text or mixed-endian conversion is allowed.
QPC timestamps are unsigned ticks at the record's QPC frequency. Digests are
32 raw SHA-256 bytes. Text is strict UTF-8 NFC without BOM or NUL. An absent
scalar, ID, digest, fixed block, or unused byte is all-zero and its presence
bit is zero. A present variable byte string has its exact length in the
prefix, occupies the beginning of its fixed block, and zero-fills the
remainder. Nonzero absent or padding bytes are invalid.

V1 committed-journal metadata applicability is closed. A committed journal
record is exactly a witnessed `TRII/1`, `TRIC/1`, `TRIM/1`, `TRAO/1`, or
`TRAR/1` record. `TRAD/1` is a dispatch command and `TRAF/1` is a referenced
file descriptor; neither is a committed journal record and neither inherits
the committed-journal metadata requirement.

Every committed journal record has its format-defined sequence, previous
record digest, magic plus variant as record kind, body length and body digest,
only its format-applicable version/profile bindings, and a `TRFW/1` commit
witness. QPC fields are required only by this table and their exact format
layout; a field marked `none` must remain zero under that layout:

| Format or variant | Required monotonic time field |
|---|---|
| `TRII/1 INSTALLATION_IDENTITY` | creation QPC at prefix offset 200 |
| `TRIC/1 CREATE_INTENT` | intent-created QPC at prefix offset 240 |
| `TRIM/1 READY` | manifest-created QPC at prefix offset 168 |
| every `TRAO/1` variant | `detected_at` at prefix offset 216, plus only the variant-applicable QPC fields in the closed presence table |
| `TRAR/1 INVENTORY_OPEN` | inventory-open QPC at recovery-block offset 296 and barrier-acquired QPC at offset 312 |
| `TRAR/1 SLOT_INVENTORY` | none |
| `TRAR/1 INVENTORY_SEAL` | inventory-seal QPC at recovery-block offset 320 |
| `TRAR/1 OBJECT_RELEASE_PROOF` | release-proof QPC at recovery-block offset 296 |
| `TRAR/1 UNPROVEN_RESOLUTION` | resolution QPC at recovery-block offset 320 |
| `TRAR/1 RECOVERY_COMPLETE` | recovery-complete QPC at recovery-block offset 352 |

The sole wall-clock-derived authoritative field in V1 is
`PROCESS_CREATION_IDENTITY_FILETIME`. Its source is exactly the
`lpCreationTime` output of one successful `GetProcessTimes` call on the exact
held process handle. Its canonical value is unsigned
`(uint64(dwHighDateTime) << 32) | dwLowDateTime`, serialized as little-endian
`u64`. Windows defines the value as 100-nanosecond intervals since
`1601-01-01T00:00:00Z`. TraceRelay treats it only as an opaque identity
discriminator paired with the PID; it does not convert, subtract, order or
display the value as time.

The exception is allowed only at `TRIM/1` process-record relative offset 16,
`TRAR/1` recovery-common-block offset 104 under that variant's availability
rules, and exact process-identity fields in host-certification evidence. A
required process identity rejects a failed `GetProcessTimes`, a zero value or
an exact mismatch. An unavailable `TRAR/1` identity uses the already-defined
all-zero field and may not claim identity equality. The value may be compared
for byte equality, paired with PID to reject PID reuse, hashed inside existing
canonical preimages, and used for ETW attribution. It must not determine
journal order, duration, deadline, liveness, QPC conversion, UTC observation,
or any time claim.

No other V1 authoritative field contains wall-clock or UTC data. No general
UTC source, presence bit or observation encoding exists. A writer must not put
wall-clock data in reserved bytes or reinterpret a QPC field as wall-clock
time. A query/display annotation may state its own query-time wall clock only
outside authoritative bytes, labeled `UNTRUSTED_QUERY_TIME`; it is excluded
from digests and cannot affect order, duration, validation or evidence claims.

Closed enum values are:

| Enum | Values |
|---|---|
| variant | `1 RETURNED_INLINE`, `2 RETURNED_FILE_REFERENCE`, `3 RETURNED_REJECTED`, `4 INITIAL_LATE_RETURN`, `5 TERMINAL_LATE_RETURN`, `6 TERMINAL_EMISSION_TIMEOUT_FROZEN`, `7 PREDISPATCH_FAILED_LIMIT`, `8 RECOVERY_UNPROVEN`, `9 ALARM_ENVELOPE_ADMISSION_LIMIT` |
| channel | `1 PERSISTENT`, `2 LIVE` |
| emission | `1 INITIAL`, `2 TERMINAL` |
| frozen result | `1 SUCCEEDED`, `2 FAILED`, `3 TIMEOUT_UNKNOWN`, `4 UNPROVEN` |
| validation | `0 NOT_APPLICABLE`, `1 VERIFIED`, `2 REJECTED`, `3 PENDING` |
| body mode | `0 NONE`, `1 INLINE`, `2 FILE_REFERENCE` |
| runtime slot state | `0 EMPTY`, `1 COMMAND_WRITING`, `2 COMMAND_READY`, `3 WORKER_EXECUTING`, `4 RESULT_WRITING`, `5 RESULT_READY`, `6 CONSUMER_VALIDATING`, `7 OBSERVATION_COMMITTING`, `8 REJECTION_COMMITTING`, `9 LATE_DIAGNOSTIC_COMMITTING`, `10 ACKED`, `11 POISONED` |
| endpoint/storage auxiliary | `0 NONE`, `1 PERSISTENT_STORAGE_RESULT`, `2 LIVE_ENDPOINT_RESULT`, `3 REJECTED_RESULT` |

Every other enum value is invalid. Unless a specific table assigns a flag,
all flag fields are zero and a nonzero value is invalid.

The frozen catalog reason ordinal is the zero-based position in the exact
concatenation `reasons`, then `lifecycle_reasons`, then `control_reasons`, each
in its serialized array order. It must resolve to the exact retained reason ID
under the bound catalog digest.

The 3936-byte prefix is:

| Offset | Bytes | Canonical field |
|---:|---:|---|
| 0 | 4 | ASCII `TRAO` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 2 | variant enum |
| 10 | 2 | presence bitmap |
| 12 | 4 | complete record byte length |
| 16 | 4 | variant body byte length |
| 20 | 4 | dispatch-block byte length |
| 24 | 4 | file-reference-block byte length |
| 28 | 4 | auxiliary-block byte length |
| 32 | 8 | enclosing journal sequence |
| 40 | 8 | QPC frequency |
| 48 | 16 | alarm ID |
| 64 | 16 | session ID; zero only for session-unknown |
| 80 | 16 | service incarnation |
| 96 | 16 | monitor incarnation |
| 112 | 16 | detector/writer incarnation |
| 128 | 16 | worker incarnation |
| 144 | 16 | mapping incarnation |
| 160 | 16 | operation ID |
| 176 | 16 | call/emission ID |
| 192 | 8 | slot index |
| 200 | 8 | slot epoch |
| 208 | 8 | alarm sequence |
| 216 | 8 | `detected_at` |
| 224 | 8 | `tuple_frozen_at` |
| 232 | 8 | coordinator decision timestamp |
| 240 | 8 | worker dispatch timestamp |
| 248 | 8 | `call_return_observed_at` |
| 256 | 8 | `result_validation_completed_at` |
| 264 | 8 | `reference_verified_at` |
| 272 | 8 | applicable exclusive deadline |
| 280 | 8 | timeout-decision timestamp |
| 288 | 2 | channel enum |
| 290 | 2 | initial/terminal emission enum |
| 292 | 2 | frozen result enum |
| 294 | 2 | validation enum |
| 296 | 4 | frozen catalog reason ordinal |
| 300 | 2 | body-mode enum |
| 302 | 2 | slot-state enum |
| 304 | 4 | slots in applicable mapping |
| 308 | 4 | exact `EMPTY` slot count |
| 312 | 4 | poisoned slot count |
| 316 | 4 | endpoint/storage auxiliary enum |
| 320 | 8 | NTFS volume serial |
| 328 | 16 | NTFS file identity |
| 344 | 16 | journal chain ID |
| 360 | 8 | referenced journal sequence |
| 368 | 8 | referenced record offset |
| 376 | 8 | referenced record length |
| 384 | 8 | returned durable position |
| 392 | 32 | referenced/emitted record digest |
| 424 | 32 | exact support-profile digest |
| 456 | 32 | exact reason-catalog digest |
| 488 | 24 | zero |
| 512 | 512 | exact dispatch bytes then zero padding |
| 1024 | 512 | exact `TRAF/1` file-reference bytes then zero padding |
| 1536 | 512 | endpoint/storage result block |
| 2048 | 512 | slot-census or recovery-inventory block |
| 2560 | 512 | reason/path/diagnostic block |
| 3072 | 768 | zero |
| 3840 | 32 | previous enclosing-journal record digest |
| 3872 | 32 | variant-body SHA-256 |
| 3904 | 32 | reserved; always zero |

The body immediately follows the prefix. The 160-byte trailer immediately
follows the body:

| Relative offset | Bytes | Canonical field |
|---:|---:|---|
| 0 | 4 | ASCII `TRCT` |
| 4 | 4 | complete record byte length |
| 8 | 4 | body byte length |
| 12 | 8 | enclosing journal sequence |
| 20 | 32 | SHA-256 of the 3936-byte prefix |
| 52 | 32 | SHA-256 of the body; SHA-256(empty) when length is zero |
| 84 | 32 | `pre_witness_record_digest`: SHA-256 of prefix, body, and this trailer with bytes 84..159 zero |
| 116 | 44 | `TRFW/1` post-flush witness; zero before flush and then exactly section 3.3 |

The prefix digest, body digest, pre-witness record digest, duplicated lengths,
sequence, and witness state must all match. No outer record wrapper is added;
this prefix/body/trailer is the complete section 3 canonical record. Golden
vectors freeze empty-body, maximum-body, every variant, one-byte mutation,
nonzero-padding, duplicate-length, digest/trailer cases, absent/partial/full/
malformed witness states, the exact witness preimage, prefix bytes
`3904..3935` equal to zero, trailer bytes `84..115` equal to
`pre_witness_record_digest`, and the fact that the full witnessed
committed-record SHA-256 occupies no field in its own record. That full hash is
computed only after `WITNESS_VALID` and is used by later chain/reference
fields.

Variant enums and presence rules are closed.

The structural fields outside the presence bitmap are always required: magic,
version, variant, bitmap, complete-record length, enclosing sequence, QPC frequency,
alarm/service/monitor/detector identities, alarm sequence, `detected_at`,
support-profile digest, reason-catalog digest, previous enclosing-record
digest, prefix digest, body digest, `pre_witness_record_digest`, duplicated
trailer lengths/sequence, witness state, and all required zero padding.
The 16 bitmap bits have these closed, nonoverlapping groups:

| Bit | Group | Exact fields |
|---:|---|---|
| 0 | `SESSION` | bytes 64–79 |
| 1 | `OPERATION` | bytes 160–175 |
| 2 | `WORKER_SLOT` | bytes 128–159, 192–207, 240–247 and 302–315 |
| 3 | `DISPATCH` | dispatch length at 20–23 and block 512–1023 |
| 4 | `CALL_ID` | bytes 176–191 |
| 5 | `RETURN_VALIDATION` | bytes 248–263 and validation enum 294–295 |
| 6 | `FILE_REFERENCE` | reference length at 24–27, reference time 264–271, bytes 320–383 and block 1024–1535 |
| 7 | `ENDPOINT_STORAGE` | auxiliary length at 28–31, enum 316–319 and block 1536–2047 when bit 11 is zero |
| 8 | `BODY` | body length at 16–19, body-mode enum 300–301 and following body bytes |
| 9 | `DEADLINE_TIMEOUT` | bytes 272–287 |
| 10 | `FROZEN_OUTCOME` | bytes 224–239, 288–293 and 296–299 |
| 11 | `PREDISPATCH_CENSUS` | bytes 1536–2559 interpreted as the exact 1024-byte slot census; bit 7 is zero |
| 12 | `RECOVERY_INVENTORY` | block 2048–2559 interpreted as the exact `TRAR/1` inventory binding |
| 13 | `RESULT_JOURNAL_IDENTITY` | bytes 384–423 |
| 14 | `DIAGNOSTIC` | block 2560–3071 |
| 15 | reserved | none; always zero |

A group is present only when its bit is one. A forbidden or absent group has
bit zero and every byte exclusively owned by that group zero; bytes shared by
bits 7, 11 or 12 are interpreted only by the one present mutually exclusive
group. The `BODY` group instead retains the structural SHA-256(empty) body
digest when absent. Bits 7, 11 and 12 are pairwise mutually exclusive where
their fixed blocks overlap. Bit 0 is one
exactly when the session ID is known; a
session-unknown record has bit zero and a zero session ID. Every variant below
requires bits 9 and 10 because deadline/frozen-outcome facts are part of its
authority; a non-timeout variant uses a zero timeout-decision timestamp. A
record without `RETURN_VALIDATION` has validation enum
`NOT_APPLICABLE(0)`. Channel and emission zero are allowed only for
`ALARM_ENVELOPE_ADMISSION_LIMIT`; every channel-attempt variant uses the closed
nonzero enums. A bitmap/field disagreement rejects the record.

The variant rows use the group names above and are exhaustive:

| Variant | Required groups | Conditional groups | Forbidden groups |
|---|---|---|---|
| `RETURNED_INLINE` | `OPERATION`, `WORKER_SLOT`, `DISPATCH`, `CALL_ID`, `RETURN_VALIDATION`, `ENDPOINT_STORAGE`, `BODY`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `RESULT_JOURNAL_IDENTITY` | `SESSION` iff known | `FILE_REFERENCE`, `PREDISPATCH_CENSUS`, `RECOVERY_INVENTORY`, `DIAGNOSTIC` |
| `RETURNED_FILE_REFERENCE` | `OPERATION`, `WORKER_SLOT`, `DISPATCH`, `CALL_ID`, `RETURN_VALIDATION`, `FILE_REFERENCE`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `RESULT_JOURNAL_IDENTITY` | `SESSION` and `BODY` are both present for known-session; both are absent for session-unknown | `ENDPOINT_STORAGE`, `PREDISPATCH_CENSUS`, `RECOVERY_INVENTORY`, `DIAGNOSTIC` |
| `RETURNED_REJECTED` | `OPERATION`, `WORKER_SLOT`, `DISPATCH`, `CALL_ID`, `RETURN_VALIDATION`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `RESULT_JOURNAL_IDENTITY`, `DIAGNOSTIC` | `SESSION` iff known; exactly one of `BODY`, `FILE_REFERENCE`, or `ENDPOINT_STORAGE` identifies the rejected representation | `PREDISPATCH_CENSUS`, `RECOVERY_INVENTORY`; every positive-result flag |
| `INITIAL_LATE_RETURN` / `TERMINAL_LATE_RETURN` | `OPERATION`, `WORKER_SLOT`, `DISPATCH`, `CALL_ID`, `RETURN_VALIDATION`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `RESULT_JOURNAL_IDENTITY`, `DIAGNOSTIC` | `SESSION` iff known; inline uses `BODY`; a known-session file return uses `FILE_REFERENCE` plus `BODY`; a session-unknown file return uses `FILE_REFERENCE`; endpoint return uses `ENDPOINT_STORAGE` | `PREDISPATCH_CENSUS`, `RECOVERY_INVENTORY`; every success-upgrade flag |
| `TERMINAL_EMISSION_TIMEOUT_FROZEN` | `OPERATION`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `DIAGNOSTIC` | `SESSION` iff known; `WORKER_SLOT`, `DISPATCH`, and `CALL_ID` are all present iff worker dispatch occurred | `RETURN_VALIDATION`, `FILE_REFERENCE`, `ENDPOINT_STORAGE`, `BODY`, `PREDISPATCH_CENSUS`, `RECOVERY_INVENTORY`, `RESULT_JOURNAL_IDENTITY` |
| `PREDISPATCH_FAILED_LIMIT` | `OPERATION`, `DISPATCH`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `PREDISPATCH_CENSUS`, `DIAGNOSTIC` | `SESSION` iff known | `WORKER_SLOT`, `CALL_ID`, `RETURN_VALIDATION`, `FILE_REFERENCE`, `ENDPOINT_STORAGE`, `BODY`, `RECOVERY_INVENTORY`, `RESULT_JOURNAL_IDENTITY` |
| `RECOVERY_UNPROVEN` | `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `RECOVERY_INVENTORY`, `DIAGNOSTIC` | `SESSION` iff recoverable as known-session; `OPERATION` iff inventory proves it; `WORKER_SLOT` iff inventory proves the complete worker/slot tuple | `DISPATCH`, `CALL_ID`, `RETURN_VALIDATION`, `FILE_REFERENCE`, `ENDPOINT_STORAGE`, `BODY`, `PREDISPATCH_CENSUS`, `RESULT_JOURNAL_IDENTITY`; every returned-success flag |
| `ALARM_ENVELOPE_ADMISSION_LIMIT` | `SESSION`, `DEADLINE_TIMEOUT`, `FROZEN_OUTCOME`, `DIAGNOSTIC` | none | `OPERATION`, `WORKER_SLOT`, `DISPATCH`, `CALL_ID`, `RETURN_VALIDATION`, `FILE_REFERENCE`, `ENDPOINT_STORAGE`, `BODY`, `PREDISPATCH_CENSUS`, `RECOVERY_INVENTORY`, `RESULT_JOURNAL_IDENTITY` |

`PREDISPATCH_FAILED_LIMIT` sets coordinator-decision time to the timely
channel-outcome decision, sets the timeout-decision timestamp zero, embeds the
exact attempted `TRAD/1`, and records every canonical slot ordinal/state in the
census block. For an initial emission committed before the complete
publication tuple freezes, `tuple_frozen_at` is zero. For a terminal emission,
it equals the one already-frozen immutable publication tuple timestamp; the
later channel decision never replaces that anchor.
`ALARM_ENVELOPE_ADMISSION_LIMIT` is session-known, has channel/emission zero,
result `FAILED`, reason `TR-LIMIT-SESSION`, deadline
`detected_at + alarm_initial_attempt_admission_deadline_ms`, coordinator
decision strictly before that deadline, `tuple_frozen_at=0`, diagnostic kind
`LIMIT`, and no channel operation. It is global envelope rejection evidence,
not a persistent or live channel attempt. `RETURNED_REJECTED` and late-return
rows retain only the rejected/late representation needed for diagnosis; its
group can never be interpreted as positive authority. No conditional group is
implementation selected: session scope, observed IPC mode and whether a real
worker dispatch occurred determine it.

The endpoint/storage block at prefix bytes 1536–2047 is:

| Offset within block | Bytes | Field |
|---:|---:|---|
| 0 | 2 | auxiliary enum |
| 2 | 2 | raw-status domain enum |
| 4 | 4 | raw unsigned status code |
| 8 | 4 | flags; currently zero |
| 12 | 4 | returned-result byte length |
| 16 | 8 | accepted/committed byte length |
| 24 | 16 | endpoint or journal-segment identity |
| 40 | 32 | worker-result prefix SHA-256 |
| 72 | 32 | exact OS-call argument SHA-256 |
| 104 | 32 | complete returned-result SHA-256 |
| 136 | 376 | zero |

The prefix auxiliary length is exactly 136 when this group is present and zero
otherwise. The raw-status domain is `1 WIN32`, `2 WINSOCK`, or
`3 PRODUCT`; every other value is invalid.

The `PREDISPATCH_CENSUS` block at prefix bytes 1536–2559 is:

| Offset within block | Bytes | Field |
|---:|---:|---|
| 0 | 16 | target mapping incarnation |
| 16 | 16 | target worker-incarnation owner |
| 32 | 4 | canonical mapping ordinal |
| 36 | 4 | slot count |
| 40 | 8 | coordinator decision QPC |
| 48 | 8 | exclusive admission-deadline QPC |
| 56 | 2 | state encoding `2` = packed four-bit runtime-state enum |
| 58 | 2 | encoded-state byte length |
| 60 | 4 | `EMPTY` count |
| 64 | 4 | `COMMAND_WRITING` count |
| 68 | 4 | `COMMAND_READY` count |
| 72 | 4 | `WORKER_EXECUTING` count |
| 76 | 4 | `RESULT_WRITING` count |
| 80 | 4 | `RESULT_READY` count |
| 84 | 4 | `CONSUMER_VALIDATING` count |
| 88 | 4 | `OBSERVATION_COMMITTING` count |
| 92 | 4 | `REJECTION_COMMITTING` count |
| 96 | 4 | `LATE_DIAGNOSTIC_COMMITTING` count |
| 100 | 4 | `ACKED` count |
| 104 | 4 | `POISONED` count |
| 108 | 32 | SHA-256 of all slot epochs as consecutive little-endian uint64 values |
| 140 | 8 | stable mapping snapshot sequence |
| 148 | 12 | zero |
| 160 | 512 | packed slot-state vector then zero |
| 672 | 352 | zero |

The channel/emission in the attempted `TRAD/1` deterministically selects one
of the four role mappings, so a census never selects among eligible workers.
The owner and mapping identities name the inspected capacity but do not assert
worker dispatch. Slot `i` occupies one nibble: low nibble for even `i`, high
nibble for odd `i`. The encoded-state length is `ceil(slot_count/2)`, an unused
high nibble and all trailing bytes are zero, all twelve counts sum to
`slot_count`, and the state/epoch reads occur under one mapping snapshot
sequence whose before/after value must match. The supported slot counts are
exactly 2 or 1024. `FAILED_LIMIT` requires `EMPTY=0`. Any mismatch, unsupported
state, torn snapshot, or changed sequence invalidates the census and yields
`UNPROVEN`; it cannot be retried into a fabricated timely limit.

The `DIAGNOSTIC` block at prefix bytes 2560–3071 is:

| Offset within block | Bytes | Field |
|---:|---:|---|
| 0 | 2 | reason-ID UTF-8 length |
| 2 | 2 | rooted-relative-path UTF-8 length |
| 4 | 2 | diagnostic-detail UTF-8 length |
| 6 | 2 | diagnostic-kind enum |
| 8 | 4 | raw unsigned status code |
| 12 | 4 | flags; currently zero |
| 16 | 128 | reason-ID UTF-8 then zero |
| 144 | 128 | rooted-relative-path UTF-8 then zero |
| 272 | 128 | diagnostic-detail UTF-8 then zero |
| 400 | 32 | SHA-256 of the diagnostic source bytes or zero when not applicable |
| 432 | 80 | zero |

Each text length is at most 128 and must equal its exact valid prefix. A path
is empty unless the variant has an authoritative rooted relative path. The
diagnostic-kind values are `1 LIMIT`, `2 VALIDATION_REJECTION`,
`3 LATE_RETURN`, `4 TIMEOUT`, and `5 RECOVERY_UNPROVEN`; the corresponding
variant must use that exact value. The source digest is required only when raw
rejected or recovery-source bytes exist, otherwise it is zero. Unknown values
reject rather than becoming opaque extensions.

A known-session persistent `RETURNED_INLINE` or
`RETURNED_FILE_REFERENCE` copies the exact validated canonical persistent body,
up to 65536 bytes, into the bundle observation. A live returned observation
copies the exact accepted frame, up to 4096 bytes. A session-unknown persistent
`RETURNED_FILE_REFERENCE` has a zero-length body: runtime recovery already has
the immutable alarm-root record and requires the complete verified `TRAF/1`,
chain, identity, range, digest, and timely observation. It never treats path
text or the root record alone as success. Therefore:

```text
fixed envelope = 4096
known-session persistent maximum = 4096 + 65536 = 69632
known/session-unknown live maximum = 4096 + 4096 = 8192
session-unknown persistent/timeout/limit/recovery maximum = 4096
```

`RETURNED_INLINE` with channel `PERSISTENT` requires the `SESSION` group.
A session-unknown persistent result always uses verified
`RETURNED_FILE_REFERENCE`, even when its canonical record is 4096 bytes or
smaller. `RETURNED_INLINE` without `SESSION` is valid only for channel `LIVE`.

The serializer calculates the exact record before its first write. Body byte
69633, live-body byte 4097, any fixed-block overflow, or any noncanonical
presence/padding fails before write. No form may use a nested reference, split
record, omitted required field, null/absent ambiguity, or implementation-
selected encoding.

One admitted alarm has at most six primary observation roles: one initial role
per channel and two terminal roles per channel. A terminal primary role
contains exactly one timely result, pre-dispatch limit, timeout decision, or
recovery `UNPROVEN`; its second role is available only for one post-timeout
late result, rejection, or recovery resolution. These alternatives are
mutually exclusive. A seventh primary observation is rejected before write.

After a persistent record is durably committed in the alarm root, the detector
attempts `PERSISTENT_INITIAL_COMMITTED` or
`PERSISTENT_TERMINAL_COMMITTED` in this bundle role. The exact copied record
bytes plus chain/position facts are the self-contained verifier authority; the
offline verifier never reopens the alarm root. After a live call returns,
`LIVE_INITIAL_FRAME_ACCEPTED` or a terminal-diagnostic observation records the
local endpoint result. Only `LIVE_INITIAL_FRAME_ACCEPTED` may prove live
publication; terminal diagnostic acceptance is diagnostic only.

A returned channel result is not usable merely because its call returned.
Every returned result enters `RETURNED_UNVERIFIED` and becomes exactly one of
`VERIFIED` or `REJECTED` at `result_validation_completed_at`. For inline
results, validation covers framing, length, unused-zero bytes, digest, worker,
operation, incarnation, epoch, and canonical body. For `FILE_REFERENCE`,
validation additionally includes every section 9.2.1 reference and journal
range check; `reference_verified_at` equals
`result_validation_completed_at`. The returned-result observation is one
atomic semantic unit containing the call-return and validation facts plus the
exact body or zero-body alarm-root reference required by its `TRAO/1` variant.
No caller, recovery path, or verifier may treat `RETURNED_UNVERIFIED` as a
returned success.

An initial return observation is publication authority only when
both `call_return_observed_at` and `result_validation_completed_at` are
strictly before
`detected_at + alarm_initial_outcome_freeze_deadline_ms` and the frozen
publication tuple selects the same outcome. A validation rejection completed
strictly before the deadline is a returned `FAILED` result and poisons the
worker boundary. If validation remains pending at the deadline, the frozen
result is `TIMEOUT_UNKNOWN`. A return or validation completed at or after that
exclusive deadline is `INITIAL_PUBLICATION_LATE_RETURN`; it preserves return,
validation, reference, and alarm-root facts as diagnostic evidence but cannot
create, replace, erase, or upgrade initial publication success.
Runtime recovery likewise requires a matching timely detector observation;
an alarm-root record alone never overrides the frozen tuple.

If a terminal-emission call has no completely validated returned result at its
tuple-relative observation deadline, the coordinator freezes `TIMEOUT_UNKNOWN`
in memory and immediately attempts a `TERMINAL_EMISSION_TIMEOUT_FROZEN`
observation. The observation is allowed to commit without a call return or
while validation remains pending and is the sole durable authority for the
no-validated-result-by-deadline decision. A valid durable record remains truth
authority regardless of its unprovable physical commit-return time. The
`alarm_timeout_decision_commit_deadline_ms` bound is a runtime liveness and
release-certification obligation measured by an external harness; it is not an
offline-evidence predicate. The record proves only what the coordinator
observed by the deadline; it does not prove that the OS call never completed.

No bundle-observation commit gates or delays either channel. A crash after the
alarm-root durable commit or live endpoint acceptance but before the matching
bundle observation commits leaves that channel `UNPROVEN` to the offline
verifier. Absence proves neither failure nor success. Session-unknown
observations remain in the detector/publisher's own service- or
monitor-incarnation alarm journal and are not retroactively attached to an
unrelated session bundle. The record binds detector role, writer incarnation,
both last-known service/monitor incarnations, and alarm ID. Recovery and query
discover and validate both journal kinds under the configured alarm root.
Aggregate charging remains monitor-incarnation plus session-unknown plus
alarm-root bytes; aggregate ownership does not grant journal write authority.

Runtime recovery and offline verification are distinct evaluations. Runtime
recovery may read the configured alarm root, but an initial persistent success
requires both its canonical record and a matching timely detector return
observation consistent with the frozen tuple. Offline verification consumes
only the copied session bundle and requires the equivalent copied observation.
Neither evaluation imports the other's external input or result. Each emits
`TR-ALARM-PUBLISHED` only from its own declared authority and otherwise emits
`TR-ALARM-UNPROVEN`; the combined term `recovery/verifier` does not define one
shared input domain.

Service and monitor journals cross-reference the other journal's latest known
sequence and digest. A reference must name an existing committed prefix at or
before the referring observation; a future sequence, wrong digest,
non-monotonic reference, missing mandatory reference, or identity mismatch is
`INVALID`. A structurally valid lease expiry, renewal gap beyond the allowed
advance, or observation deadline miss is `INCOMPLETE`.

During `ACTIVE`, every accepted lease renewal records the service position
carried by that renewal. The monitor must commit its observation no later than
the profile cross-journal observation deadline after that service position was
reported. Every subsequent service health record records the latest monitor
renewal acknowledgement. It may lag by at most the same deadline. A lag inside
the deadline is valid; an exact boundary or later is incomplete. The clean
candidate and clean closure references below must match exactly and have zero
sequence ambiguity.

Absence of an alarm is acceptable for `PASS` only when the monitor journal
proves continuous valid monitoring through clean terminal and contains a
committed `NO_FAILURE_OBSERVED` closure. An alarm or monitoring gap prevents
`PASS`.

Clean close order is:

1. service commits `CLEAN_CANDIDATE` after bilateral EOF and complete range
   accounting;
2. monitor commits `NO_FAILURE_OBSERVED`, referencing that candidate and its
   last observed service position;
3. while the same lease remains valid, service commits `TERMINAL_CLEAN`,
   referencing the monitor closure.

Loss of execution continuity or lease between these steps prevents clean
terminal and `PASS`; recovery never synthesizes a missing step.

### 7.4 Crash windows

If a destination OS call may have executed but its outcome record is absent,
the range is unknown. If the service journal has no clean terminal, the
session is incomplete or terminal-unknown. If both alarm publication channels
fail, the next verifier or recovery run emits stable reason
`TR-ALARM-UNPROVEN`; it does not fabricate an earlier persistent alarm.

### 7.5 Clean predicate

`TERMINAL_CLEAN` and verifier `PASS` require all of:

1. valid bundle identity and supported version bindings;
2. valid complete service and monitor journal structures and digest chains;
3. no partial tail in any authoritative journal;
4. one valid activation and no identity/state contradiction;
5. both directions satisfy `A_d = O_d` and `U_d = empty`;
6. bilateral source EOF and required half-close outcomes are committed;
7. continuous valid monitor lease from activation through terminal;
8. no service, monitor, persistence, resource, alarm, or transport failure;
9. committed clean service terminal and matching monitor closure;
10. all evidence bytes remain within the frozen writer limits.

No single field or exit path may bypass this conjunction.

## 8. Monitor lifecycle and guarantee

### 8.1 Bootstrap and ownership

The caller that needs TraceRelay starts or confirms the TraceRelay startup
coordinator before registering a dependent application. The coordinator is a
transient TraceRelay process that establishes the monitor/service application
boundary and exits only after readiness or terminal startup failure. TraceRelay
starts neither the client nor upstream.

Bootstrap order:

1. the coordinator acquires the fixed runtime-context installation initializer
   lock, resolves or creates the canonical installation identity below the
   supplied installation runtime root, and binds that root to the
   runtime-context singleton authority;
2. after committed `TRII/1`, the coordinator commits `TRIC/1` before creating
   the startup job, either child process, or any alarm mapping/event;
3. the coordinator creates the service and then the monitor as suspended
   children already bound to one kill-on-close startup job at process creation;
   each child inherits exactly its command-read and acknowledgement-write
   private local overlapped named-pipe client endpoints, is resumed exactly
   once, immediately starts its identity read, and enters `PRE_READY`;
4. each child completes one byte-exact `TRBH/1 IDENTITY` challenge and
   acknowledgement that proves its role, PID plus
   `PROCESS_CREATION_IDENTITY_FILETIME`, logon-session ID, installation,
   incarnation challenge, and startup-job membership;
5. the coordinator allocates the four mappings and eight events, duplicates the
   exact 14 final handles into each child, and receives one byte-exact
   `TRBH/1 FINAL_HANDLES` acknowledgement from each holder after all local
   access-mask and operation probes pass;
6. the coordinator and both children execute the exact command-EOF,
   `BOOTSTRAP_CLOSED_ACK`, acknowledgement-EOF closure sequence. After all
   eight bootstrap endpoint entries and every transient bootstrap operation
   event are proven closed, the coordinator
   revalidates both exact process identities and the exact two-member startup
   Job, then executes one exact two-process zero-time wait. Only
   `WAIT_TIMEOUT` establishes the IPC holder-proof point and authorizes the one
   `TRIM/1` commit attempt. Loss before that point prohibits the attempt; loss
   ordered after that point cannot cancel the attempt, remains a child failure,
   and prohibits external readiness;
7. monitor adopts the fresh planned monitor-incarnation ID bound by
   `TRIC/1`/`TRBH/1`, opens the persistent alarm channel and journal, validates
   alarm IPC, and publishes monitor readiness;
8. service independently resolves the same installation identity and root,
   adopts the fresh planned service-incarnation ID bound by
   `TRIC/1`/`TRBH/1`, opens its own persistent alarm journal, and authenticates
   to the ready monitor;
9. monitor issues a lease bound to the installation and both incarnation IDs;
10. service validates control, evidence, profile, worker, alarm, and monitor
   prerequisites;
11. only then may service publish readiness and allow the coordinator to exit.

Bootstrap association requires current runtime-context local IPC, matching
installation identity, exact held process identity, matching logon-session ID,
fresh service/monitor/coordinator incarnation challenges, and the exact
`TRBH/1` protocol in section 9.2.2. Each response is phase-bound and cannot be
replayed across phases or process starts. The product uses the creator's normal
Windows token and default access control; no restricted token, custom
adversarial DACL, or malicious local-process isolation is required.

PID alone is never identity. PID plus the exact held process handle,
`PROCESS_CREATION_IDENTITY_FILETIME`, matching logon-session ID, and fresh
incarnation ID prevents accidental PID-reuse continuity.

### 8.2 Lease state

Lease states are `ABSENT`, `VALID`, `STALE`, and `CLOSED`. Renewals contain a
strictly increasing heartbeat sequence, critical-operation state, active
session ID if any, and last committed service-journal position. A renewal is
accepted only when:

1. authentication and both incarnation IDs match;
2. arrival is strictly before current lease expiry;
3. sequence advance is between `1` and the profile maximum, inclusive;
4. the service position is a valid committed prefix;
5. every declared critical-operation field is internally consistent.

A duplicate, regression, excessive advance, wrong incarnation, late, or
unauthenticated renewal is recorded as rejected and does not extend the lease.
An accepted advance greater than one records the skipped count; it preserves
continuous monitoring only because the prior lease never expired and the
advance stays inside the frozen bound.

An ACTIVE session cannot transfer to a replacement monitor. Monitor restart
closes the old session incomplete; a new lease permits only a new session.

Service restart invalidates every pre-restart credential. A pre-restart
nonterminal session is never resumed or appended; recovery observes its
committed prefix and terminal status, and a new registration is required.

### 8.3 Guaranteed detection set

Within the support-profile deadline, the monitor guarantees detection of:

- service process-handle signal or disappearance;
- heartbeat/lease stall;
- service-declared unhealthy state;
- lack of critical journal or forwarding progress while the service declares
  pending critical work;
- service-incarnation mismatch.

The service independently guarantees detection of monitor process loss and
lease expiry.

The monitor does not guarantee detection of:

- a responsive service that emits internally false facts;
- semantic corruption invisible to protocol invariants;
- malicious local-user/process, administrator, SYSTEM, kernel, or storage
  adversarial behavior;
- whole-host loss while no external observer exists.

These exclusions appear in verification assurance output.

### 8.4 Critical progress and normal backpressure

`pending critical work` is true only for work whose completion does not depend
on peer socket readiness:

- an entered authoritative journal or audit commit;
- a dispatched destination OS write call;
- an entered terminal, monitor-closure, or alarm commit;
- a control mutation whose durable intent has committed.

Each item has one critical-operation ID, kind, start timestamp, phase, and
monotonic progress counter. Entry commits the pending state. A phase completion
advances the counter and either advances phase or clears pending. No progress
for `critical_progress_stall_ms`, measured from the later of entry or last
advance, is a declared critical-path failure.

Bytes durably observed but waiting for destination socket writability are
`BACKPRESSURED`, not pending critical work. Backpressure remains healthy while
buffers stay within the profile, the lease renews, no destination call is
outstanding, and the maximum session deadline has not expired. It stops further
source reads; it does not create false progress. Once a destination call is
dispatched, the worker and critical-progress deadlines apply.

## 9. Alarm contracts

### 9.1 Channels

Evidence, alarm, and installation runtime roots are three distinct canonical
directories. No root is equal to, contains, or is contained by another. They
may share one NTFS volume, in which case volume failure is an explicit common
failure domain and section 14.2 groups their outstanding reservations.

Persistent channel:

- publisher-owned append-only journal under the configured alarm root, where
  section 3.3's one-time current-record witness fill is the sole allowed
  in-place mutation, with distinct create-new files for the service and monitor
  incarnations;
- publication succeeds only after a complete alarm record is durably committed
  under the section 3 failure model;
- service-evidence-journal failure does not disable the monitor's alarm writer,
  and monitor failure does not disable the service's alarm writer, by design;
- shared host, OS, or storage failure remains a declared common failure.

Live channel:

- current-instance local subscription endpoint bound to the exact service,
  monitor, process, and logon-session identities;
- bounded in-memory queue;
- one initial publication frame and one same-ID terminal diagnostic frame;
- live publication succeeds only when the endpoint accepts the complete
  initial publication frame;
- terminal diagnostic-frame acceptance is a separate delivery observation and
  never creates, erases, or upgrades live publication success;
- no subscriber, full queue, broken endpoint, or timeout is a failed attempt;
- live success does not prove subscriber processing or operator receipt.

### 9.2 Identity, ordering, and accounting

Detection first creates one immutable in-memory alarm envelope containing a
Windows-CSPRNG alarm ID, monitor-incarnation ID, next monotonic alarm sequence,
detected-at monotonic timestamp, failure class, reason ID, session linkage when
known, and both channel states. Creating this envelope is not a durable commit
claim and does not wait for alarm-root I/O.

The envelope's canonical dispatch record is at most
`alarm_ipc_limits.max_dispatch_record_bytes`. It is always carried inline.
Dispatch never depends on creating or reading an external payload file.

Consumers deduplicate by alarm ID and order within one monitor incarnation by
sequence. Cross-incarnation total ordering is not claimed. Both workers receive
the same immutable envelope before either can mutate channel state.

Before a known session becomes `ACTIVE`, session admission preallocates a
fixed closure partition for 32 future alarm envelopes. This one-time
preallocation is not owned by either alarm channel and cannot fail after the
session becomes active. Every envelope slot is permanently split into a
persistent-owned and live-owned subpartition:

```text
persistent observations/alarm = 3 * 69632 = 208896 bytes / 3 records
live observations/alarm = 3 * 8192 = 24576 bytes / 3 records
all observations/alarm = 233472 bytes / 6 records
maximum publication-root bytes/session = 32 * 2 * 65536 = 4194304
```

At most four known-session alarm envelopes are admitted concurrently and at
most 32 cumulatively. The fixed session closure partition is:

```text
alarm observation records = 32 * 6 = 192
alarm observation bytes = 32 * 233472 = 7471104
one global-admission-overflow record = 1 record / 4096 bytes
alarm partition = 193 records / 7475200 bytes
non-alarm closure remainder = 63 records / 26079232 bytes
total closure reserve = 256 records / 33554432 bytes
```

Global envelope admission checks only the already-preallocated alarm counters.
For the fifth concurrent or thirty-third cumulative alarm, it consumes the
dedicated overflow slot and commits exactly one 4096-byte
`ALARM_ENVELOPE_ADMISSION_LIMIT` `TRAO/1`. This rejection occurs before any
channel operation exists and is expressly outside the admitted-envelope rule
that each channel receives dispatch or pre-dispatch limit. It stops further
alarm admission for that session, saves recoverable state, and terminates the
application/session fail-closed. Commit failure leaves the global capacity
decision `UNPROVEN`, preserves existing evidence, and still terminates.

After global admission succeeds, drawing the two observation subpartitions is
an infallible counter transition over preallocated capacity. Persistent
admission separately reserves its two 65536-byte alarm-root publication
records; failure makes only the persistent channel `FAILED_LIMIT` or
`FAILED_IO`. Live admission has no alarm-root publication-record reservation
and proceeds from its live-owned observation subpartition. Observation commit
failure in either subpartition cannot consume, delay, cancel, or release the
peer subpartition. Crash recovery retains their ownership by alarm ID and
channel.

Before monitor readiness, the session-unknown alarm-root domain is likewise
split into 128 persistent-owned and live-owned subpartitions. One admitted
alarm draws them independently:

```text
persistent-owned
  = 2 * 65536 publication + 3 * 4096 zero-body observation
  = 143360 bytes / 5 records
live-owned = 3 * 8192 = 24576 bytes / 3 records
total = 167936 bytes / 8 records
```

A persistent observation always uses its 4096-byte envelope and verified
`TRAF/1`; a live observation may use an 8192-byte envelope-plus-frame record.
A partial primary record occupies no more than its own complete-record slot.
Recovery `UNPROVEN` records do not borrow either normal subpartition; section
9.2.2 gives them a separate host recovery reserve. Failure in one channel's
subpartition never waits for or cancels the peer channel.

Known and session-unknown channel reservations release unused alternatives
only after that channel has its terminal result and every owned observation
role is committed or permanently unprovable. A crash preserves committed
records and retained partial tails. A reservation with no committed or partial
record leaves no evidence claim and consumes no recovered quota.

Publication records charge the monitor-incarnation, known-session or session-
unknown count, alarm-root quota, and protected reserve. Known-session
observation records also charge session committed-record and logical-byte
domains. Session-unknown observation records charge monitor-incarnation,
session-unknown, alarm-root, and protected-reserve domains.

The profile admits at most 128 session-unknown alarms:

```text
records = 128 * 8 = 1024
bytes = 128 * 167936 = 21495808
```

Exact maxima are admitted; record 1025, alarm 129, or byte 21495809 fails
before write. Across those alarms, retained publication/observation partial
tails are bounded by:

```text
128 * (2*65536 + 3*4096 + 3*8192) = 21495808 bytes
```

The root has hard maxima of 12000 files and 16000 directory entries. Reserved
or partial roles are never reassigned to another alarm ID. The protected alarm
reserve cannot be consumed by deletion audit or ordinary diagnostics.

### 9.2.1 Bounded alarm IPC body transfer

The four alarm-worker roles use four preallocated in-place mappings: two
persistent roles with
`alarm_ipc_limits.persistent_slots_per_worker` slots each and two live roles
with `alarm_ipc_limits.live_slots_per_worker` slots each. One slot contains
exactly:

```text
alarm_ipc_limits.slot_prefix_bytes
+ alarm_ipc_limits.max_inline_payload_bytes
= alarm_ipc_limits.slot_bytes
```

Every mapping begins with one exact 32-byte little-endian control header:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | `freeze_state`: `1 RUNNING`, `2 FREEZE_REQUESTED`, `3 FROZEN`; every other value invalid |
| 4 | 4 | reserved; always zero |
| 8 | 8 | `freeze_generation`; zero only in ordinary `RUNNING`, otherwise the deterministic nonzero recovery generation |
| 16 | 8 | `active_transition_count` |
| 24 | 8 | `snapshot_sequence`; zero initially, even when stable, odd only while one slot transition owns the mapping |

The header is naturally aligned. Every field is accessed only with an aligned
32- or 64-bit acquire/release atomic operation. Torn, unaligned, overflowed, or
reserved-nonzero state is invalid. Slot zero starts at mapping offset 32; slot
`i` starts at `32 + i * slot_bytes`. Therefore one mapping has exactly:

```text
mapping_header_bytes + slot_count * slot_bytes
```

and the four mapping sizes are `8736`, `8736`, `4456480`, and `4456480`
bytes. Their aggregate is `8930432` bytes.

Normal slot transition protocol is closed:

1. atomically increment `active_transition_count`, rejecting overflow;
2. acquire-read `freeze_generation` and `freeze_state`; if generation is
   nonzero or state is not `RUNNING`, decrement the count and perform no slot
   mutation;
3. acquire the mapping sequence by compare-exchanging one even value `s` to
   `s+1`; while contended, recheck generation/state and abort as in step 2 if
   freeze has begun;
4. after owning the odd sequence, recheck generation/state. If freeze won,
   publish `s+2`, decrement the count, and perform no slot mutation;
5. perform at most one valid slot-state transition with one aligned atomic
   compare-exchange, then release-publish `s+2` and decrement the count.

Every decrement is paired with one successful increment, and the count cannot
underflow. A normal writer never changes the freeze fields. A recovery
coordinator first compare-exchanges generation `0` to its deterministic value;
an equal value resumes the same recovery and a different nonzero value blocks
as conflict. Generation ownership immediately prevents new slot transitions.
It then compare-exchanges `RUNNING` to `FREEZE_REQUESTED`; an already requested
or frozen state is valid only with the same generation.

Recovery waits for count zero and an even stable sequence. If, and only if,
every process that could mutate the mapping is proven `EXITED` or
`IDENTITY_ABSENT`, recovery may normalize crash-left volatile header state:
atomically set a nonzero active count to zero and advance an odd sequence by
one to the next even value. The slot state itself is never synthesized or
rolled back; its one atomic transition is observed wholly before or after the
crash. Normalization is forbidden while any mutator is `QUIESCED` but alive.
After the stable snapshot is recorded, recovery compare-exchanges
`FREEZE_REQUESTED` to irreversible `FROZEN`. No state returns to `RUNNING`.

There is one command-ready event and one result-ready event per mapping. One
ready IPC incarnation has exactly the mapping, event-object, cross-process
handle-entry, and aggregate mapping-byte values in `alarm_ipc_limits`; every
object exists before readiness and none grows after readiness. The
runtime-context concurrent IPC-incarnation maximum is one, including an old
incarnation whose worker or kernel object has outlived its coordinator.

Each slot has one owner and follows this closed lifecycle:

```text
EMPTY
-> COMMAND_WRITING
-> COMMAND_READY
-> WORKER_EXECUTING
-> RESULT_WRITING
-> RESULT_READY
-> CONSUMER_VALIDATING
-> OBSERVATION_COMMITTING | REJECTION_COMMITTING | LATE_DIAGNOSTIC_COMMITTING
-> ACKED
-> EMPTY
```

The coordinator claims `EMPTY`; the bound worker alone consumes the command
and publishes the result; the detector-owned consumer alone validates and
commits the returned-result, rejection, or late diagnostic observation; only
the coordinator publishes `ACKED` and returns the slot to `EMPTY`. Every
transition binds mapping incarnation, worker incarnation, slot index, epoch,
operation ID, alarm ID, and emission kind. The epoch advances only on the
`ACKED -> EMPTY` transition.

The twelve runtime states above are the only values stored in a slot and the
only values serialized by census or recovery. Each displayed lifecycle arrow
is one release/acquire atomic transition under the mapping snapshot sequence.
The three committing states enter only from `CONSUMER_VALIDATING` and exit only
to `ACKED` after the named durable record commits. On a bounded-call deadline,
owner loss or deterministic validation state from which normal progress cannot
continue, the current owner or recovery coordinator may atomically change any
non-`EMPTY`, non-`ACKED` state to `POISONED` after revoking its execution
grant. `POISONED` has no normal exit; only sealed `TRAR/1` recovery resolves
the old slot and the old mapping is then destroyed. An `ACKED` slot still
follows only `ACKED -> EMPTY`. No projection, collapsed state or invented
state is permitted in `PREDISPATCH_CENSUS` or `SLOT_INVENTORY`.

A slot remains pinned from command claim through `ACKED`. Result/reference
metadata may be copied only into the same operation's authoritative
observation; it may not be moved into an off-slot queue, backlog, cache, or
detached work item that outlives slot ownership. A `FILE_REFERENCE` counts
against both reference limits from `RESULT_READY` through `ACKED`, including
while validation, observation commit, rejection commit, timeout handling, or
late diagnostic commit is pending.

`ACKED` is permitted only after one of these durable outcomes:

1. complete validation plus the exact `TRAO/1` body/reference variant commits;
2. deterministic validation rejection observation commits;
3. a deadline timeout observation commits and the eventual late result or
   durable rejection diagnostic commits; or
4. a durable `TRAR/1` abandonment inventory binds the slot/reference before
   old authority is released, the owning process/worker and every old object
   are then proven gone, and a durable `RECOVERY_UNPROVEN` resolution cites
   that inventory.

A timeout decision alone does not release a still-running validation. If the
operation remains physically unresolved, the slot stays pinned and its worker
boundary is poisoned. New readiness remains false until release is proved.

After coordinator or worker crash, section 9.2.2 performs crash-safe two-phase
abandonment recovery. It durably inventories old authority before releasing
it, releases and proves every old object, then durably resolves every inventory
as `UNPROVEN`. No replacement alarm mapping, event, worker, or duplicated IPC
handle may be created before the sealed inventory, release proof, and all
resolutions are durable. If any phase cannot complete inside its fixed attempt
reserve, state is `RECOVERY_BLOCKED_OLD_IPC`: readiness remains false, new
registration/session admission fails closed, and automatic restart allocates
no new IPC set. Thus the host aggregate never exceeds four mappings, eight
events, 24 cross-process object-handle entries, four ready control-handle
entries, 28 ready handle entries, 54 bounded pre-ready creation handle entries,
8930432 committed mapping bytes, or one live IPC incarnation in any crash
window.

When no `EMPTY` persistent slot exists, the next persistent command fails
coordinator-owned pre-dispatch admission with `FAILED_LIMIT` immediately
before slot claim or result/reference creation. It does not wait, allocate
another queue, advance an epoch, or delay the live attempt. Thus the fifth
unresolved persistent reference and byte 262,145 are rejected while the first
four references remain pinned.

The pre-dispatch result uses only the `PREDISPATCH_FAILED_LIMIT` `TRAO/1`
presence row. Its in-memory atomic point is the coordinator decision timestamp:
if strictly before the admission deadline, the current-process result becomes
`FAILED` and no worker dispatch may occur for that emission. A subsequent
durable observation commit is the only recovery, query, or offline authority
for that decision; commit time does not replace the decision timestamp.

If the observation write fails, leaves a partial tail, or the process crashes
after decision but before complete commit, current-process memory is lost and
recovery/query/offline result is `UNPROVEN`, never reconstructed as either a
timely limit or a timeout. The product preserves the prefix and tail, declares
alarm evidence degraded, saves recoverable state, and terminates the affected
application/session fail-closed. A committed limit observation survives
restart and deterministically yields `FAILED`; a late commit retains that truth
but fails its separate runtime liveness check. The decision can never support
publication success. It is an admitted channel attempt, not a worker dispatch.

The canonical dispatch command is fixed-size `TRAD/1`:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII `TRAD` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 4 | total bytes `512` |
| 12 | 2 | channel enum |
| 14 | 2 | emission enum |
| 16 | 4 | flags |
| 20 | 16 | alarm ID |
| 36 | 16 | session ID or zero |
| 52 | 16 | service incarnation |
| 68 | 16 | monitor incarnation |
| 84 | 8 | alarm sequence |
| 92 | 8 | `detected_at` |
| 100 | 4 | reason-catalog ordinal |
| 104 | 4 | failure-class enum |
| 108 | 32 | support-profile digest |
| 140 | 32 | reason-catalog digest |
| 172 | 2 | reason-ID UTF-8 length |
| 174 | 128 | reason-ID UTF-8 then zero |
| 302 | 2 | opaque metadata length |
| 304 | 128 | opaque metadata then zero |
| 432 | 32 | SHA-256 of bytes 0–431 |
| 464 | 48 | zero |

Length overflow, invalid UTF-8, catalog ordinal/ID mismatch, digest mismatch, or
nonzero padding rejects before slot claim. `TRAD/1` is exactly 512 bytes; it is
not an implementation-selected at-most encoding.

`TRAD/1` flags are zero. Its failure-class enum is
`1 SERVICE_PROCESS_LOST`, `2 HEARTBEAT_LEASE_EXPIRED`,
`3 CRITICAL_PROGRESS_STALLED`, `4 WORKER_PROGRESS_STALLED`,
`5 DURABILITY_PATH_FAILED`, `6 CAPACITY_LIMIT`,
`7 IPC_RECOVERY_BLOCKED`, or `8 MONITOR_INTERNAL_FAILED`. The detector path
selects exactly one class before dispatch; the reason ID/ordinal remains the
more specific frozen cause. Opaque metadata is exact uninterpreted bytes, not
text, and cannot affect class, reason, admission, or public result.

The canonical file reference is fixed-size `TRAF/1`:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII `TRAF` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 4 | total bytes `512` |
| 12 | 2 | relative-path UTF-8 length |
| 14 | 2 | record-kind enum |
| 16 | 2 | serialization enum |
| 18 | 2 | flags |
| 20 | 8 | exact record offset |
| 28 | 8 | exact record length |
| 36 | 8 | committed durable position |
| 44 | 8 | journal sequence |
| 52 | 8 | slot epoch |
| 60 | 8 | NTFS volume serial |
| 68 | 16 | alarm ID |
| 84 | 16 | operation ID |
| 100 | 16 | writer incarnation |
| 116 | 16 | worker incarnation |
| 132 | 16 | mapping incarnation |
| 148 | 16 | NTFS file identity |
| 164 | 16 | journal chain ID |
| 180 | 32 | referenced record SHA-256 |
| 212 | 32 | referenced previous-record SHA-256 |
| 244 | 128 | alarm-rooted relative-path UTF-8 then zero |
| 372 | 32 | support-profile digest |
| 404 | 16 | journal-segment identity |
| 420 | 32 | referenced commit-trailer SHA-256 |
| 452 | 60 | zero |

The path length is at most 128 bytes and must equal the nonzero UTF-8 prefix.
The referenced record length is at most 65536. Wrong enum, identity, digest,
length, padding, or containment rejects before positive validation.
`TRAF/1` record kind is `1 ALARM_FIRST_ATTEMPT` or
`2 ALARM_CHANNELS_TERMINAL`; serialization is
`1 tracerelay-record-v1`; flags are zero. Every other value rejects.

Command and result representation is closed:

1. the dispatch record is exactly `max_dispatch_record_bytes=512` as `TRAD/1`
   and is always `INLINE`;
2. a live initial or terminal frame is at most
   `monitor_and_alarm_limits.max_live_alarm_frame_bytes` and is always
   `INLINE`;
3. a known-session persistent success whose complete canonical committed
   record is at most `max_inline_payload_bytes` may return those bytes inline;
4. a known-session larger persistent record, and every session-unknown
   persistent record regardless of size, returns `FILE_REFERENCE` to the
   already committed record range in the publisher-owned alarm journal; the
   referenced record remains bounded by both `max_external_payload_bytes` and
   `monitor_and_alarm_limits.max_alarm_record_bytes`;
5. a body outside its applicable maximum fails deterministically before
   partial publication, observation, or success classification.

No body is truncated, silently omitted, split across slots, or represented by
path text alone. A persistent file reference is exactly the 512-byte `TRAF/1`
above. Its relative path remains at the profile path depth and resolves only
beneath the configured alarm root without following reparse points. Callers
cannot choose the root or path.

The persistent worker publishes `FILE_REFERENCE` only after the complete
record and trailer have committed under section 3, and after it reopens the
journal range and verifies path containment, volume/file identity, chain,
sequence, offset, length, and digest. The consumer independently repeats all
checks before copying the exact bytes into a return observation. A wrong mode,
length, digest, identity, incarnation, epoch, format, path, range, or nonzero
unused inline byte poisons the worker boundary and cannot support a positive
alarm claim.

A file reference creates no second body file and no second authority. It points
to the canonical committed persistent alarm record already charged to the
record-count, alarm-root byte-quota, and protected-reserve domains. Reference
existence alone proves no timely return observation or frozen outcome. The
alarm journal is never deleted, truncated, or rewritten by IPC consumption or
recovery.

Only the four persistent slots may contain file references. Therefore:

```text
max_persistent_file_references_in_flight
= 2 * persistent_slots_per_worker
= 4

max_referenced_record_bytes_in_flight
= max_persistent_file_references_in_flight * max_external_payload_bytes
= 262144
```

Live publication never opens the persistent alarm journal and never waits for
a persistent file reference. File indirection therefore preserves the two
channels' dispatch and result independence. Recovery validates persistent
references only against the existing immutable journal prefix and never uses a
path or record alone to infer timely success.

A full monitor-incarnation or session-unknown aggregate, unavailable quota, or
reservation I/O failure makes the persistent attempt `FAILED_LIMIT` or
`FAILED_IO`; it never delays or cancels the live attempt. It also declares the
monitor degraded and blocks new session admission until a new ready monitor
incarnation establishes usable alarm capacity. Existing fail-closed handling
continues.

### 9.2.2 Crash-safe IPC abandonment recovery

The caller supplies one absolute installation runtime root before starting the
monitor. This root is the `installation root` used everywhere in v1 and is the
sole absolute parent of installation and IPC authority. Evidence and alarm
roots never substitute for it.

The product opens the caller-selected existing root with
`CreateFileW(OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS)` and holds a
no-share-delete handle through initialization. Normal Windows path resolution
may traverse a reparse component, but the opened final target must be a
writable local fixed-disk NTFS directory with an exact `FILE_ID_INFO`
containing the 64-bit volume serial plus 16 raw file-ID bytes. Required
operations must succeed under the creator's normal Windows token and default
access control; no custom DACL or adversarial ownership proof is required. The
canonical root-path bytes are strict UTF-8 NFC encoding, without BOM or NUL, of
`GetFinalPathNameByHandleW(FILE_NAME_NORMALIZED | VOLUME_NAME_GUID)` after
removing one trailing `\` except for a volume root. The path bytes, volume
serial and file ID must be byte-equal on every reopen. Caller spelling, current
directory, drive-letter mapping, display name and executable location are never
root identity.

The only legal installation-identity attempt paths, relative to that root, are:

```text
_runtime/installation-authority/identity-a0.trii
_runtime/installation-authority/identity-a1.trii
```

For every validated relative path in this contract, path depth is computed
after canonical separator normalization and strict component validation.
Leading, trailing or repeated separators, empty components, `.`, `..`,
alternate data streams and noncanonical components are invalid. The relative
root has depth zero. A directory-only relative path has one depth unit per
directory component. A relative file path has one depth unit per parent
directory component; the installation root and final file component are
excluded.

Each installation-attempt path is exactly 48 UTF-8 bytes and file-path depth
two. `_runtime` and
`installation-authority` are deterministic directories. Under the fixed
runtime-context initializer lock, an interrupted creation of either directory
is resumable only when every existing component has the expected directory
type, resolves inside the recorded final root identity, permits every required
operation, and the complete runtime-root enumeration contains only legal
names. An unexpected reparse object inside this product-created tree is a
structural conflict; no malicious concurrent path-race claim is made. Before a
complete valid `TRII/1`,
`ipc-authority`, any boot directory, any `.tria` file, or any IPC process,
job, mapping, event or handle is forbidden. Finding any such object is
`INSTALLATION_IDENTITY_CONFLICT`; startup returns `TR-START-FAILED`.

`TRII/1` is one zero-body, 4096-byte canonical record using the section 7.3.1
3936-byte prefix and 160-byte trailer rules. It has sequence zero, zero previous
digest, magic `TRII`, major/minor `1/0`, variant `1 INSTALLATION_IDENTITY`,
zero flags, and these exact nonzero prefix fields:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII `TRII` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 2 | variant `1 INSTALLATION_IDENTITY` |
| 10 | 2 | flags; zero |
| 12 | 4 | complete record bytes `4096` |
| 16 | 4 | body bytes `0` |
| 20 | 4 | installation-attempt ordinal `0..1` |
| 24 | 16 | installation ID |
| 40 | 32 | installation random seed |
| 72 | 4 | exact owner-SID byte length |
| 76 | 32 | SHA-256 of exact binary owner SID |
| 108 | 8 | runtime-root NTFS volume serial |
| 116 | 16 | runtime-root NTFS file ID |
| 132 | 4 | canonical runtime-root path byte length |
| 136 | 32 | SHA-256 of canonical runtime-root path bytes |
| 168 | 32 | SHA-256 of exact 48-byte attempt-relative-path bytes |
| 200 | 8 | creation QPC |
| 208 | 8 | QPC frequency |
| 216 | 3624 | zero |
| 3840 | 32 | previous record digest; zero |
| 3872 | 32 | SHA-256(empty) |
| 3904 | 32 | zero |

The 32-byte seed is obtained in one successful
`BCryptGenRandom(NULL, seed, 32, BCRYPT_USE_SYSTEM_PREFERRED_RNG)` call. The
owner SID bytes are the exact valid SID returned for the initializer token by
`GetTokenInformation(TokenUser)` and copied for `GetLengthSid` bytes; the
length is `8..68`. Each canonical absolute root path is at most 4096 strict
UTF-8 bytes. The SID is runtime-context attribution and deterministic identity
input, not a security boundary. All integers are unsigned little-endian. The
installation ID is exactly:

```text
SHA-256(
  ASCII "TRII/1-INSTALLATION-ID" ||
  random_seed[32] ||
  owner_sid_sha256[32] ||
  le_u64(runtime_root_volume_serial) ||
  runtime_root_file_id[16] ||
  runtime_root_path_sha256[32]
)[0:16]
```

A zero ID or a newly generated ID equal to an installation ID already
enumerated in the configured evidence or alarm roots is rejected before file
creation. The initializer may make at most two total RNG draws for one
installation initialization. Exhaustion or random-call failure consumes no
file attempt and returns `TR-START-FAILED`.

The initializer creates attempt zero with create-new semantics and the section
3 durable-commit primitive. Creation consumes the attempt even when zero bytes
are written. Each legal ordinary-file attempt has exactly one size/state:

| State | Exact condition |
|---|---|
| `ABSENT` | the deterministic path does not exist |
| `INCOMPLETE` | stable length is `0..4095` bytes |
| `COMPLETE_UNWITNESSED` | stable length is `4096`, every pre-witness `TRII/1` validation succeeds, and the witness is `WITNESS_ABSENT` or `WITNESS_PARTIAL` |
| `COMPLETE_VALID` | stable length is `4096`, every `TRII/1` validation succeeds, and the witness is `WITNESS_VALID` |
| `COMPLETE_INVALID` | stable length is `4096`, all higher-priority guards below pass, the bytes are readable, but at least one canonical record, field, trailer, digest, witness, identity or recomputation validation fails and the exact `COMPLETE_UNWITNESSED` condition does not apply |
| `OVERSIZE` | stable length is at least `4097` bytes |

Installation resolution uses this strict priority:

1. an unstable or unreadable file, wrong object type, unexpected reparse
   object inside the product-created tree, required-access failure, or
   root/path/final-file-identity failure is
   `INSTALLATION_IDENTITY_UNAVAILABLE`;
2. any unknown name, case/alias variant, alternate stream, a complete record
   whose stored attempt ordinal differs from its deterministic filename
   ordinal, or a valid identity inconsistent with the selected root/runtime
   context attribution is
   `INSTALLATION_IDENTITY_CONFLICT`;
3. only after both guards pass is each deterministic path assigned exactly one
   of the six states above and the complete 36-pair table applied.

The conflict guard overrides `COMPLETE_INVALID`; an ordinal mismatch can never
authorize attempt one. The decision table cells are the only legal next
actions:

| `a0` \ `a1` | `ABSENT` | `INCOMPLETE` | `COMPLETE_UNWITNESSED` | `COMPLETE_INVALID` | `COMPLETE_VALID` | `OVERSIZE` |
|---|---|---|---|---|---|---|
| `ABSENT` | `CREATE_A0` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `INCOMPLETE` | `CREATE_A1` | `EXHAUSTED` | `EXHAUSTED` | `EXHAUSTED` | `SELECT_A1` | `CONFLICT` |
| `COMPLETE_UNWITNESSED` | `CREATE_A1` | `EXHAUSTED` | `EXHAUSTED` | `EXHAUSTED` | `SELECT_A1` | `CONFLICT` |
| `COMPLETE_INVALID` | `CREATE_A1` | `EXHAUSTED` | `EXHAUSTED` | `EXHAUSTED` | `SELECT_A1` | `CONFLICT` |
| `COMPLETE_VALID` | `SELECT_A0` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `OVERSIZE` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |

`CREATE_A0` and `CREATE_A1` use create-new and consume the named attempt even
at zero bytes. `EXHAUSTED` is `INSTALLATION_IDENTITY_EXHAUSTED`; `CONFLICT` is
`INSTALLATION_IDENTITY_CONFLICT`. `SELECT_A0` or `SELECT_A1` is the sole valid
installation record. Every unavailable, exhausted or conflicting result
returns `TR-START-FAILED`, publishes no readiness and authorizes no IPC
allocation.

After commit, the initializer closes and reopens the selected file through the
rooted canonical path, revalidates root and file identity, reads exactly 4096
bytes, validates every field/trailer/digest, and recomputes the installation
ID. Monitor and service independently repeat the same read-only resolution.
The complete record digest, selected attempt ordinal, canonical root facts and
installation ID must all be byte-equal. The same valid root remains one
installation across processes, process restarts, executable copies and Windows
boots. Changing path, owner, volume/file ID or selected authority is not a new
identity; it is failed startup.

A fresh supported installation requires a newly created empty runtime root. It
never reuses, truncates or overwrites an old `TRII/1` or nonempty runtime tree.
Its new root identity and new CSPRNG seed produce a newly checked installation
ID; collision with any retained evidence/alarm installation ID fails closed
before path creation. Reusing a valid old runtime root is a
restart of the old installation, not reinstall. Deliberate deletion or
replacement outside this protocol is local tampering and outside the positive
claim.
No product operation automatically deletes installation authority.

The canonical Windows boot identity is the raw first 16 returned bytes,
interpreted only as an opaque identifier, from:

```text
NtQuerySystemInformation(
  SystemInformationClass = 90 SystemBootEnvironmentInformation,
  SystemInformation = one zero-initialized 32-byte buffer,
  SystemInformationLength = 32,
  ReturnLength
)
```

The supported profile requires NTSTATUS `STATUS_SUCCESS`, returned length
exactly `32`, and a nonzero 16-byte identifier. Three queries separated by at
least 10 ms must return byte-equal identifiers before startup or recovery may
use the value. The function/class is version-gated rather than assumed stable:
profile certification must prove the same identifier across processes and
process restarts in one Windows kernel boot epoch and a different identifier
after a real Windows restart. Hibernation/resume belongs to one boot epoch when
Windows returns the same identifier. Wall-clock, time-zone, QPC and uptime
values are never boot identity. Query failure, unsupported class, unexpected
length, zero value or unstable values are `BOOT_IDENTITY_UNAVAILABLE`; they
never authorize a new intent, `BOOT_EPOCH_ENDED`, object absence or readiness.

Only after the complete selected `TRII/1` is resolved may the initializer
create the deterministic `ipc-authority` parent. An empty exact parent after a
crash is resumable. An empty `bB[32]` boot directory consumes one retained-boot
directory entry and authorizes only intent-zero attempt-zero creation for the
matching current installation and boot identities; it authorizes no allocation
by itself. Unknown, mismatched, reparse or over-limit parents and empty boot
directories fail closed.

Each IPC incarnation has one logical two-record IPC-authority journal. Let:

```text
boot_path_id[16] =
  SHA-256(
    ASCII "TRIA/1-BOOT-PATH" ||
    installation_id[16] ||
    windows_boot_id[16]
  )[0:16]
```

Let `B` be its 32 lowercase hexadecimal ASCII characters in stored-byte order,
`II` the two lowercase hexadecimal characters of intent ordinal `0..63`, and
`A` the attempt ordinal `0` or `1`. The only legal relative attempt path is:

```text
_runtime/ipc-authority/bB[32]/iII[2]-aA.tria
```

It is exactly 68 UTF-8 bytes and file-path depth three under the global
parent-directory-component measure above. Every component is fixed ASCII;
separators are `/` in the canonical bytes and native `\` only when calling
Windows. Resolution rejects reparse points, alternate data streams, case
variants, aliases, extra files and path escape. The rooted path itself
attributes a zero-byte file to one installation, boot identity, intent ordinal
and attempt ordinal; no record prefix or mutable side file is needed.

Intent zero is the first intent in a boot. Intent `n+1` is legal only when
intent `n` has a complete valid `TRIC/1 -> TRIM/1` pair and the old ready IPC
has a complete matching `TRAR/1 RECOVERY_COMPLETE`.

After namespace, expected-object-type, required-access, root/final-file-
identity, path/boot/intent/attempt-ordinal and stable-read guards pass, each
deterministic IPC attempt has exactly one state:

| State | Exact condition |
|---|---|
| `ABSENT` | the deterministic path does not exist |
| `TRIC_INCOMPLETE` | stable length is `0..4095` |
| `TRIC_UNWITNESSED` | stable length is `4096`, the `TRIC/1` pre-witness bytes validate, and its witness is absent or partial |
| `TRIC_VALID_TRIM_INCOMPLETE` | stable length is `4096..8191`, bytes `0..4095` are one committed valid `TRIC/1`, and the remaining `TRIM/1` bytes are `0..4095` long |
| `COMPLETE_VALID` | stable length is `8192` and both `TRIC/1` and chained `TRIM/1` are committed and valid |
| `TRIC_INVALID` | stable length is `4096..8192`, bytes `0..4095` are not one committed valid `TRIC/1`, and the exact `TRIC_UNWITNESSED` condition does not apply |
| `TRIC_VALID_TRIM_UNWITNESSED` | stable length is `8192`, `TRIC/1` is committed and valid, the `TRIM/1` pre-witness bytes validate, and its witness is absent or partial |
| `TRIC_VALID_TRIM_INVALID` | stable length is `8192`, `TRIC/1` is committed and valid, and `TRIM/1` is invalid rather than unwitnessed |
| `OVERSIZE` | stable length is at least `8193` |

An unstable/unreadable file or failed object/root/security/file-identity guard
is `IPC_AUTHORITY_UNAVAILABLE`. An unknown name, case/alias/stream, path/boot/
intent/attempt-ordinal mismatch, or impossible valid identity is
`IPC_AUTHORITY_CONFLICT`. These guards run before the nine-state
classification. The conflict guard overrides every content state.

The complete 81-pair table freezes the sole next action:

| `a0` \ `a1` | `ABSENT` | `TRIC_INCOMPLETE` | `TRIC_UNWITNESSED` | `TRIC_VALID_TRIM_INCOMPLETE` | `COMPLETE_VALID` | `TRIC_INVALID` | `TRIC_VALID_TRIM_UNWITNESSED` | `TRIC_VALID_TRIM_INVALID` | `OVERSIZE` |
|---|---|---|---|---|---|---|---|---|---|
| `ABSENT` | `CREATE_A0` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `TRIC_INCOMPLETE` | `CREATE_A1` | `BLOCK_EXHAUSTED` | `BLOCK_EXHAUSTED` | `BLOCK_AUTHORITY` | `SELECT_A1` | `CONFLICT` | `BLOCK_AUTHORITY` | `BLOCK_AUTHORITY` | `CONFLICT` |
| `TRIC_UNWITNESSED` | `CREATE_A1` | `BLOCK_EXHAUSTED` | `BLOCK_EXHAUSTED` | `BLOCK_AUTHORITY` | `SELECT_A1` | `CONFLICT` | `BLOCK_AUTHORITY` | `BLOCK_AUTHORITY` | `CONFLICT` |
| `TRIC_VALID_TRIM_INCOMPLETE` | `BLOCK_AUTHORITY` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `COMPLETE_VALID` | `SELECT_A0` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `TRIC_INVALID` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `TRIC_VALID_TRIM_UNWITNESSED` | `BLOCK_AUTHORITY` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `TRIC_VALID_TRIM_INVALID` | `BLOCK_AUTHORITY` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |
| `OVERSIZE` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` | `CONFLICT` |

`CREATE_A0` and `CREATE_A1` use create-new and consume the path even at zero
bytes. `SELECT_A0` and `SELECT_A1` select the sole complete valid pair.
`BLOCK_EXHAUSTED` means both attempts were consumed before any committed valid
`TRIC/1`. `BLOCK_AUTHORITY` means one complete valid `TRIC/1` irrevocably owns
that intent but readiness is unproven; no other attempt or later same-boot
intent is legal. `CONFLICT` authorizes no mutation. Thus only an attempt-zero
`TRIC_INCOMPLETE` or `TRIC_UNWITNESSED` may authorize attempt one; a committed
4,096-byte valid `TRIC/1` never does.

At most 64 serial ready/recover/replacement intents exist per boot; the 65th
blocks before path creation. At most one IPC incarnation is allocated at a
time.

Before creating the first process, job, mapping, event or handle for an IPC
incarnation, the startup coordinator commits exactly one `TRIC/1`
`CREATE_INTENT` record in its selected create-new IPC-authority attempt file.
`TRIC/1` is sequence zero, has an all-zero previous digest, and is a zero-body
4096-byte canonical record using the same primitive, 3936-byte prefix,
160-byte trailer and durable-commit rules as `TRIM/1`, with magic `TRIC`. It
overrides all `TRAO/1` alarm semantics. Its exact nonzero prefix fields are:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII `TRIC` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 2 | variant `1 CREATE_INTENT` |
| 10 | 2 | flags; zero |
| 12 | 4 | complete record bytes `4096` |
| 16 | 4 | body bytes `0` |
| 20 | 4 | process records `2` |
| 24 | 4 | mapping records `4` |
| 28 | 4 | event records `8` |
| 32 | 8 | IPC-authority-journal sequence; exactly zero |
| 40 | 8 | QPC frequency |
| 48 | 16 | planned IPC incarnation |
| 64 | 16 | planned service incarnation |
| 80 | 16 | planned monitor incarnation |
| 96 | 16 | startup-coordinator incarnation |
| 112 | 16 | installation ID |
| 128 | 32 | exact support-profile SHA-256 |
| 160 | 32 | exact reason-catalog SHA-256 |
| 192 | 4 | Windows logon-session ID |
| 196 | 4 | total slots `2052` |
| 200 | 4 | cross-process object-handle records `24` |
| 204 | 4 | ready control-handle records `4` |
| 208 | 4 | maximum ready handle entries `28` |
| 212 | 4 | maximum creation handle entries `54` |
| 216 | 8 | committed mapping bytes `8930432` |
| 224 | 16 | canonical Windows boot identity |
| 240 | 8 | intent-created QPC |
| 248 | 4 | object namespace enum `1 LOCAL_RECORDED_SESSION` |
| 252 | 4 | unresolved pre-ready failure policy `1 REQUIRE_NEW_WINDOWS_BOOT` |
| 256 | 16 | startup job incarnation |
| 272 | 4 | intent ordinal `0..63` |
| 276 | 4 | journal-attempt ordinal `0..1` |
| 280 | 32 | planned object-name-set SHA-256 |
| 312 | 32 | planned geometry SHA-256 |
| 344 | 32 | SHA-256 of the exact 68 canonical relative-path bytes |
| 376 | 32 | complete committed `TRII/1` SHA-256 |
| 408 | 8 | installation-runtime-root NTFS volume serial |
| 416 | 16 | installation-runtime-root NTFS file ID |
| 432 | 32 | canonical installation-runtime-root path SHA-256 |
| 464 | 4 | selected installation-authority attempt ordinal `0..1` |
| 468 | 32 | SHA-256 of exact 48-byte installation-authority relative path |
| 500 | 3340 | zero |
| 3840 | 32 | previous IPC-authority-journal record SHA-256 |
| 3872 | 32 | SHA-256(empty) |
| 3904 | 32 | zero |

Mapping and event incarnation bytes are planned before allocation as the first
16 bytes of respectively `SHA-256(ASCII "TRIC/1-MAPPING" || planned_ipc_id ||
le_u32(ordinal))` and `SHA-256(ASCII "TRIC/1-EVENT" || planned_ipc_id ||
le_u32(ordinal))`. Using those identities, exact geometry and the exact name
construction below, the coordinator constructs the same four 128-byte mapping
records and eight 128-byte event records later stored by `TRIM/1`.
`planned_object_name_set_sha256` is exactly:

```text
SHA-256(
  ASCII "TRIM/1-OBJECT-NAME-SET" ||
  planned_mapping_records[512] ||
  planned_event_records[1024]
)
```

`planned_geometry_sha256` is:

```text
SHA-256(
  ASCII "TRIC/1-GEOMETRY" ||
  le_u32(2) || le_u32(4) || le_u32(8) ||
  le_u32(24) || le_u32(4) || le_u32(28) || le_u32(54) ||
  le_u32(2052) || le_u32(32) || le_u64(8930432)
)
```

The startup coordinator, service and monitor must run in the recorded Windows
logon session. The coordinator creates a Windows job with kill-on-last-handle
semantics and keeps the service non-ready while the monitor observes startup.

### 9.2.2.1 Exact bootstrap transport and process start

The coordinator creates the service first and the monitor second. For each
child it creates two private local one-way byte-mode named-pipe pairs: one
coordinator-to-child command pipe and one child-to-coordinator acknowledgement
pipe. It constructs the command pair before the acknowledgement pair and
finishes one pair, including connection and connect-event closure, before
starting the next. All four pairs are constructed serially.

Each pair has one independent 32-byte value returned by
`BCryptGenRandom(NULL, buffer, 32, BCRYPT_USE_SYSTEM_PREFERRED_RNG)`. Its pipe
name is:

```text
\\.\pipe\TraceRelay.TRBH.<64 lowercase nonce hex>.<service|monitor>.<command|ack>
```

An RNG failure, all-zero nonce, duplicate name inside the startup, existing
name, or creation collision is terminal startup failure. A failed name is not
retried. Names are never published, persisted, sent to a child, reused, or
accepted as authority.

For the command pair, the coordinator server endpoint is created by
`CreateNamedPipeW` with:

```text
dwOpenMode =
  PIPE_ACCESS_OUTBOUND |
  FILE_FLAG_OVERLAPPED |
  FILE_FLAG_FIRST_PIPE_INSTANCE
```

For the acknowledgement pair it instead uses `PIPE_ACCESS_INBOUND`; all other
server parameters are identical:

```text
dwPipeMode =
  PIPE_TYPE_BYTE |
  PIPE_READMODE_BYTE |
  PIPE_WAIT |
  PIPE_REJECT_REMOTE_CLIENTS
nMaxInstances = 1
nOutBufferSize = 4096
nInBufferSize = 4096
nDefaultTimeOut = 0
lpSecurityAttributes = NULL
```

The server endpoint is therefore non-inheritable. The coordinator opens the
matching client endpoint with `CreateFileW`, share mode zero, `OPEN_EXISTING`,
`FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED`, no template handle, and
`SECURITY_ATTRIBUTES { nLength=sizeof(SECURITY_ATTRIBUTES),
lpSecurityDescriptor=NULL, bInheritHandle=TRUE }`. The command client requests
exactly `GENERIC_READ`; the acknowledgement client requests exactly
`GENERIC_WRITE`.

After the client open, the coordinator calls `ConnectNamedPipe` with a
zero-initialized `OVERLAPPED` and a new unnamed, non-inheritable, initially
nonsignaled manual-reset event. A nonzero immediate return, terminal success
after `ERROR_IO_PENDING`, or `FALSE` plus `ERROR_PIPE_CONNECTED` is a connected
pair. Every other result is failure. A pending connect is completed through
`GetOverlappedResultEx`; deadline expiry requests cancellation only through
`CancelIoEx(server, &overlapped)`, after which the same operation must still
reach a terminal `GetOverlappedResultEx` result or its isolated owner process
must be terminated and observed. The `OVERLAPPED`, event, and server/client
endpoints remain owned until that terminal result. The connect event closes
before construction continues, so at most one connect event exists and no
connect event overlaps child I/O.

No bootstrap endpoint is duplicated with `DuplicateHandle`. Any partial pair
or later process-creation failure closes every created endpoint and terminally
settles every issued operation before cleanup continues. The named-pipe
instance disappears when its last endpoint closes.

The four logical bootstrap handles per child are exact:

| Child-local ordinal | Holder after creation handoff | Endpoint and permitted operation | Inheritable at `CreateProcessW` | In child `HANDLE_LIST` | Required close point |
|---:|---|---|---|---|---|
| 0 | coordinator | command server; `PIPE_ACCESS_OUTBOUND`; `WriteFile` only | no | no | after verified `FINAL_HANDLES_ACK`, before child observes command EOF |
| 1 | child | command client; requested `GENERIC_READ`; `ReadFile` only | yes, then cleared by child entry | yes | after command EOF, before `BOOTSTRAP_CLOSED_ACK` |
| 2 | child | acknowledgement client; requested `GENERIC_WRITE`; `WriteFile` only | yes, then cleared by child entry | yes | after `BOOTSTRAP_CLOSED_ACK` write reaches terminal success |
| 3 | coordinator | acknowledgement server; `PIPE_ACCESS_INBOUND`; `ReadFile` only | no | no | after acknowledgement EOF |

The access contract is the exact `CreateNamedPipeW` server direction and
`CreateFileW` client desired access above, not a queried
generic-to-specific `NtQueryObject.GrantedAccess` representation. Every
endpoint is opened with overlapped mode. A wrong-direction operation,
message-mode or remote-client substitution, instance count other than one,
duplicated endpoint, inheritance outside the two declared child endpoints,
non-overlapped call, or use after its close point is invalid.

For each child, `PROC_THREAD_ATTRIBUTE_JOB_LIST` contains exactly the one
startup-job handle and binds the job before the first child instruction.
`PROC_THREAD_ATTRIBUTE_HANDLE_LIST` contains exactly that child's command-read
and acknowledgement-write handles. `bInheritHandles` is `TRUE`,
`STARTF_USESTDHANDLES` is not set, and no standard handle is inherited.
The creation flags include exactly `CREATE_SUSPENDED` and
`EXTENDED_STARTUPINFO_PRESENT` among flags that affect this contract;
`CREATE_BREAKAWAY_FROM_JOB` is forbidden.
Unrestricted handle inheritance and post-create job assignment are forbidden.

`CreateProcessW.lpApplicationName` is the exact absolute selected child
executable path and is never `NULL`. Its fixed bootstrap arguments are:

```text
--trbh-role=service|monitor
--trbh-command-read=hhhhhhhhhhhhhhhh
--trbh-ack-write=hhhhhhhhhhhhhhhh
```

Each `h` is one lowercase hexadecimal digit encoding the unsigned 64-bit
inherited handle value with exactly 16 digits and no prefix. The role has one
value matching the selected executable role. No other argument conveys a
handle. The inherited handle's child value and access privileges must equal
the listed parent handle's value and privileges. On entry the child rejects
zero, `INVALID_HANDLE_VALUE`, duplicate values, malformed length/case, role
mismatch, or failure to clear inheritance before using either handle.

After successful `CreateProcessW`, and before resume, the coordinator:

1. proves through its returned process handle and startup-job handle that the
   exact child process is assigned to the job;
2. closes its duplicate copies of the child's command-read and
   acknowledgement-write handles;
3. calls `ResumeThread` exactly once on the returned primary-thread handle;
4. records success only when `ResumeThread` returns exactly `1`;
5. calls `CloseHandle` on the primary-thread handle immediately after that
   return, for both success and failure paths.

The child clears `HANDLE_FLAG_INHERIT` on both inherited endpoints before its
first pipe read. It then immediately issues the identity-frame read. After each
valid identity or final-handles acknowledgement reaches terminal write success,
it immediately issues the read for the next command frame or command EOF.
A failed membership proof, unexpected resume result, primary-thread close
failure, early child exit, pipe or operation-event failure, or deadline expiry
is terminal startup failure; no resume retry is permitted.

### 9.2.2.2 Byte-exact `TRBH/1` frames

Every bootstrap frame is exactly 4,096 bytes, little-endian, with this common
layout:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII `TRBH` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 2 | message kind: `1 IDENTITY_CHALLENGE`, `2 IDENTITY_ACK`, `3 FINAL_HANDLES_CHALLENGE`, `4 FINAL_HANDLES_ACK`, `5 BOOTSTRAP_CLOSED_ACK` |
| 10 | 2 | child role: `1 SERVICE`, `2 MONITOR` |
| 12 | 4 | frame bytes `4096` |
| 16 | 4 | result: `0 CHALLENGE`, `1 VERIFIED`, `2 BOOTSTRAP_CLOSED` |
| 20 | 4 | phase ordinal: `0 IDENTITY`, `1 FINAL_HANDLES`, `2 CLOSE` |
| 24 | 4 | process records: `0` or `2` |
| 28 | 4 | mapping records: `0` or `4` |
| 32 | 4 | event records: `0` or `8` |
| 36 | 4 | object-handle records: `0` or `24` |
| 40 | 4 | control-handle records: `0` or `4` |
| 44 | 4 | zero |
| 48 | 16 | planned IPC incarnation |
| 64 | 16 | planned child incarnation |
| 80 | 16 | startup-coordinator incarnation |
| 96 | 16 | startup-job incarnation |
| 112 | 32 | phase challenge generated by the Windows CSPRNG |
| 144 | 4 | exact child PID |
| 148 | 4 | Windows logon-session ID |
| 152 | 8 | exact child `PROCESS_CREATION_IDENTITY_FILETIME` |
| 160 | 32 | exact support-profile SHA-256 |
| 192 | 32 | exact reason-catalog SHA-256 |
| 224 | 32 | payload SHA-256 |
| 256 | 16 | canonical installation ID |
| 272 | 16 | canonical Windows boot identity |
| 288 | 32 | complete committed `TRIC/1` SHA-256 |
| 320 | 128 | exact pending-`TRIM/1` two-process table |
| 448 | 512 | exact pending-`TRIM/1` four-mapping table |
| 960 | 1024 | exact pending-`TRIM/1` eight-event table |
| 1984 | 1536 | exact pending-`TRIM/1` 24-object-handle table |
| 3520 | 128 | exact pending-`TRIM/1` four-control-handle table |
| 3648 | 448 | zero |

Every challenge is exactly 32 bytes returned by
`BCryptGenRandom(NULL, buffer, 32, BCRYPT_USE_SYSTEM_PREFERRED_RNG)`. Failure
or an all-zero value blocks startup.

An `IDENTITY_CHALLENGE` has result `CHALLENGE`, phase `IDENTITY`, zero handle
counts, zero bytes `320..4095`, and payload SHA-256 equal to
`SHA-256(empty)`. The child
validates its executable role, current PID, opaque process-creation identity,
logon session, planned incarnation, installation ID, boot identity,
support-profile hash, reason-catalog hash, complete `TRIC/1` digest, membership
in a job, and fresh challenge. Before sending the challenge, the coordinator
separately proves through its exact job and child-process handles that the child
is in that startup job; the later local job-handle probe binds the same job
incarnation. The `IDENTITY_ACK` is byte-equal to the challenge except for
message kind `IDENTITY_ACK` and result `VERIFIED`.

The coordinator sends no identity challenge until both children are resumed.
It completes the service identity challenge/ACK first and the monitor identity
challenge/ACK second; the two challenges have distinct fresh bytes. Only after
both acknowledgements validate may it create mappings or events. It creates
mapping ordinals `0..3`, event ordinals `0..7`, duplicates object handles to
service ordinals `0..11` then monitor ordinals `12..23`, and duplicates control
handles in `TRIM/1` ordinal order `0..3`.

A `FINAL_HANDLES_CHALLENGE` has result `CHALLENGE`, phase `FINAL_HANDLES`,
counts `2/4/8/24/4`, and a fresh challenge distinct from both identity
challenges and the other child's final challenge. Bytes `320..3647` are
byte-equal to pending `TRIM/1` bytes `512..3839`. The payload digest is exactly:

```text
SHA-256(
  ASCII "TRBH/1-FINAL-INVENTORY" ||
  le_u16(child_role) ||
  frame_bytes[320:3648]
)
```

Each child reconstructs and validates the complete process, mapping and event
tables and all table/digest relationships. The service then treats object
handle records `0..11` and control records `1,2` as its local raw handles; the
monitor treats object records `12..23` and control records `0,3` as its local
raw handles. Each performs every exact access-mask and operation probe defined
for its `TRIM/1` holder projection. It writes `FINAL_HANDLES_ACK` only when the
complete 3,328-byte inventory, payload digest, process identities, local
projection, phase and challenge are byte-equal and valid. The acknowledgement
is otherwise byte-equal to the challenge except for message kind
`FINAL_HANDLES_ACK` and result `VERIFIED`. Together the two ACKs cover every
ready handle. Every inventory byte later committed in `TRIM/1` must remain
byte-equal to acknowledged frame bytes `320..3647`; any post-ACK change blocks
commit. From its valid final ACK until matching committed `TRIM/1`, startup
failure, or process exit, each child retains its exact 12 object and two
control handles without close, replacement, reassignment, inheritance or
further duplication. This retention rule plus the later two-process
holder-proof point gives the snapshot its holder meaning; neither the final
ACK alone nor manifest commit time is a liveness assertion.
The coordinator completes the service final challenge/ACK first and the
monitor final challenge/ACK second.

Each command pipe carries exactly one identity challenge followed by one final
handle challenge, then EOF. Each acknowledgement pipe carries exactly one
identity ACK, one final-handle ACK, one close ACK, then EOF. Reads accumulate
only positive chunks until exactly 4,096 bytes; writes likewise advance only by
positive returned byte counts until exactly 4,096 bytes.

Every `TRBH/1` `read_all` or `write_all` call owns one zero-initialized
`OVERLAPPED`, its buffer, its endpoint, and one new unnamed, non-inheritable,
initially nonsignaled manual-reset event. A process has at most one active
`TRBH/1` call. Inside one call, the next positive chunk may reuse that event
only after the prior chunk has reached a terminal `GetOverlappedResultEx`
result and `ResetEvent` succeeds. The event, `OVERLAPPED`, buffer, or endpoint
must not be shared with another call, reused across calls, or closed before
terminal completion. The coordinator's serial protocol therefore owns at most
one I/O event while each child owns at most one; the global I/O-event maximum
is three.

For an expected EOF, the reader issues the next overlapped read and accepts
only a terminal zero-byte `ERROR_BROKEN_PIPE` after the complete declared frame
sequence. `ERROR_BROKEN_PIPE` before that point, immediate or terminal zero
progress during a frame, a read/write error, a frame outside this sequence,
nonzero reserved bytes, wrong role/phase/result/count, stale or duplicate
challenge, or any byte after the declared sequence is terminal startup
failure.

Every issued read or write obtains its terminal result from
`GetOverlappedResultEx`. Deadline expiry makes success impossible and calls
`CancelIoEx(endpoint, &overlapped)` only for that exact operation. A successful
cancel request and `ERROR_NOT_FOUND` race are both nonterminal; ownership
continues until matching terminal completion or observed termination of the
isolated owner process.

After both final-handle ACKs validate, the coordinator completes the entire
service close sequence and then the entire monitor close sequence. For one
sequence it closes that command-write handle; the child observes command EOF,
closes its command-read handle, writes one `BOOTSTRAP_CLOSED_ACK` derived from
its final-handle ACK by changing only message kind to
`BOOTSTRAP_CLOSED_ACK`, result to `BOOTSTRAP_CLOSED`, and phase to `CLOSE`,
then closes its acknowledgement-write handle. Each close must return success
before the next operation. The coordinator accepts the close ACK only after
its command-endpoint close returned success, then requires acknowledgement EOF
and closes its acknowledgement-read handle. This program order is the v1 proof
that all eight steady bootstrap endpoint entries and every transient connect or
I/O event entry are gone. None is serialized in `TRIM/1`.

### 9.2.2.3 Staged handle inventory and failure oracle

Final ready handles are duplicated non-inheritable only after both children
enter their `PRE_READY` watchdogs. All participants remain `PRE_READY` until
both identity ACKs, both final-handle ACKs, both close ACKs, both
acknowledgement EOFs, the IPC holder-proof point, and the complete `TRIM/1`
commit, unless they first take a required failure exit.

The exact all-process managed-handle maxima are:

| Checkpoint or phase maximum | Entries | Exact maximizing inventory |
|---|---:|---|
| service `CreateProcessW` returned, before duplicate child-end and primary-thread close | 9 | one coordinator job, four coordinator pipe endpoints, two inherited service pipe endpoints, one service-process handle, one primary-thread handle |
| monitor pair construction | 12 | six surviving service-stage endpoint/process/Job entries, one service pending-read event, four monitor endpoints, one serial connect event |
| monitor `CreateProcessW` returned, before duplicate child-end and primary-thread close | 15 | the prior 14 endpoint/process/thread/Job entries plus the service pending-read event |
| both children resumed and creation duplicates closed | 13 | one coordinator job, two coordinator-held child-process handles, four coordinator pipe endpoints, four child pipe endpoints, and two child pending-read events |
| both children resumed during an active coordinator exchange, before final allocation | 14 | the prior 13 entries plus one coordinator I/O event |
| all final mappings/events and handles allocated, no coordinator I/O event | 53 | 11 endpoint/process/Job base entries, two child pending-read events, 12 coordinator mapping/event handles, 24 duplicated child mapping/event handles, two child peer-process handles, and two child startup-job handles |
| all final mappings/events and handles allocated during an active coordinator exchange | 54 | the prior 53 entries plus one coordinator I/O event |
| both bootstrap transports and all operation events closed, before holder proof | 43 | 12 coordinator mapping/event handles, 24 child mapping/event handles, two coordinator child-process handles, two child peer-process handles, two child job handles, one coordinator job handle |
| IPC holder-proof point | 43 | the same live inventory; its 24 child object plus four child control handles form the acknowledged holder-proof snapshot |
| normal no-peer-loss path after `TRIM/1` commit and coordinator creation-handle close | 28 | 24 child object handles plus four child control handles |

This inventory is the IPC-construction handle domain. It counts every explicit
process, primary-thread, Job, mapping, event, peer-process, bootstrap-pipe and
bootstrap-operation-event handle created, inherited, returned or duplicated for
the IPC set across the three processes. The eight-entry bootstrap value counts
endpoints only; connect and I/O events are separate transient terms. Journal,
directory, installation-lock and other storage/control handles are governed by
their separate file, writer and control limits.
Current-process/thread pseudo-handles and interpreter/CRT internal handles are
also outside this domain.

Thus the child-process-creation transient maximum is exactly `15`, the
PRE_READY creation maximum is exactly `54`, and the ready maximum is exactly
`28`. The manifest always contains exactly 28 snapshot entries. On the normal
no-peer-loss path all 28 remain live after successful `TRIM/1` commit and the
coordinator closes its 15 creation-only final handles: 12 mapping/event
handles, two child-process handles, and one startup-job handle. After a
post-proof child loss, the live count may only decrease below 28; neither the
manifest nor this maximum claims a commit-time live count.

After both bootstrap transports close, the coordinator executes this one exact
proof program in order:

1. call `GetProcessTimes` on the held service-process handle and require the
   exact stored nonzero `PROCESS_CREATION_IDENTITY_FILETIME`;
2. repeat the same check for the held monitor-process handle;
3. call `QueryInformationJobObject` through the held startup-Job handle and
   require both exact process identities, no unknown member, and the previously
   frozen Job incarnation;
4. call `WaitForMultipleObjects` exactly once with `nCount=2`, handle array
   `[service-process handle, monitor-process handle]`, `bWaitAll=FALSE`, and
   `dwMilliseconds=0`.

Only exact return `WAIT_TIMEOUT` (`0x00000102`) succeeds. The kernel
wait-criteria evaluation represented by that return is the single IPC
holder-proof point. `WAIT_OBJECT_0` means service loss before proof;
`WAIT_OBJECT_0 + 1` means monitor loss before proof; `WAIT_FAILED`, every
abandoned value, or any other return means proof unavailable. These
non-success cases produce `PRE_READY_IPC_UNPROVEN`, prohibit every `TRIM/1`
byte, request cancellation of each outstanding exact bootstrap operation,
retain its resources through terminal completion or observed owner-process
termination, close coordinator pipe endpoints, terminate the startup Job, wait
for both held child process handles to become signalled, and close remaining
handles.

At the holder-proof point, both process identities, Job membership, the
children's retained local projections and acknowledged inventory become one
logical snapshot. No second liveness poll, wall-clock timestamp, QPC value or
implementation-selected observation may move this point. The snapshot has no
standalone durable authority: only a complete matching committed `TRIM/1`
asserts that this proof program succeeded.

Once the holder-proof point exists, the coordinator must drive exactly one
matching `TRIM/1` commit attempt to its terminal record-write, flush, witness
and readback result. A service or monitor signal ordered after the proof point
is latched as `POST_PROOF_SERVICE_FAILURE` or
`POST_PROOF_MONITOR_FAILURE`; it must not cancel, truncate or suppress that
manifest attempt. The child may still close its handles and exit. If the
manifest commits, it remains one valid durable acknowledged-snapshot authority;
the latched loss uses `fault_kind=START_PREREQUISITE_FAILURE`, selects public
reason `TR-START-FAILED`, prohibits monitor/service readiness, registration,
client start and a successful startup return, and requires the normal alarm
and later `TRAR/1` recovery path. If the manifest attempt is absent, partial,
unwitnessed, invalid, fails write/flush/readback, or the coordinator exits
before commit, no ready authority exists and the existing unresolved
pre-ready/same-boot block applies. A volatile proof point never repairs a
noncommitted manifest.

History A, where a child exits after the proof point but before manifest
commit, and History B, where the same child exits after manifest commit but
before any readiness publication, therefore have one external oracle: a valid
committed acknowledged-snapshot manifest if and only if the record commit
succeeds, `TR-START-FAILED`, no external readiness, and recovery required
before replacement. Loss after an actual readiness publication remains the
ordinary runtime monitor/service-failure path.

The mandatory holder-loss matrix crosses `SERVICE` and `MONITOR` with:

1. immediately before each identity check, Job query and
   `WaitForMultipleObjects` evaluation;
2. every `TRIM/1` pre-witness positive-prefix length `0..4096`;
3. flush pending and flush-success-returned;
4. every `TRFW/1` witness positive-prefix length `0..44`;
5. after the complete witness write and before, during and after exact
   readback;
6. after commit and before monitor readiness, service readiness and successful
   startup return.

With child loss as the only injected failure, every loss ordered before the
holder-proof point produces no `TRIM/1` byte and
`PRE_READY_IPC_UNPROVEN`. Every loss ordered after it must allow the one
manifest attempt to commit completely, retain the acknowledged-snapshot
authority, select `TR-START-FAILED`, prohibit external readiness and require
recovery. Independent coordinator or I/O failure at the same write, flush,
witness and readback boundaries retains the existing incomplete-manifest
oracle. Tests must prove those two failure dimensions are not conflated.

A child that observes an unexpected pipe close, peer loss, or coordinator
failure terminally settles or abandons only through observed process
termination every issued operation, closes all handles it owns, and exits.
Each surviving child otherwise waits only for the matching committed manifest
inside its startup deadline; missing, partial or invalid `TRIM/1` causes the
same fail-closed exit. Partial construction/allocation/duplication,
short/replayed/wrong-phase ACKs, wrong-direction or non-overlapped endpoints,
illegal connect results, early `ERROR_BROKEN_PIPE`, event sharing/reuse/leak,
and total PRE_READY handle count `55` or greater never permit holder proof or
`TRIM/1`.

Boundary vectors must cover endpoint entries `7/8/9`, process-creation entries
`14/15/16`, final-object structural entries `50/51/52`, actual PRE_READY peak
entries `53/54/55`, post-bootstrap entries `42/43/44`, ready entries
`27/28/29`, each pair/connect/read/write/allocation/duplication, both child
orders of failure, and every holder-proof return.
The service sequence and monitor sequence must each complete strictly before
its 15,000-ms startup deadline measured from that child's successful
`CreateProcessW` return; equality is late.

Before readiness, every live final handle is owned by exactly one of these
three watched processes; process exit closes that process's handles.
Before the holder-proof point, every surviving participant treats
coordinator/peer loss or allocation failure as `PRE_READY_IPC_UNPROVEN`: it
stops startup, closes its handles, terminates the Job/processes it owns,
attempts the external health alarm, and terminates. After the point, the exact
manifest-attempt and post-proof-loss rules above take precedence.
After matching committed `TRIM/1`, coordinator loss does not invalidate the
durable IPC manifest; the external caller receives no successful startup
return and must observe normal read-only readiness status before registering or
starting a client. Read-only status must never report operational readiness
when either exact child process is signalled. Peer loss remains a
monitor/service failure.

No process/object/handle allocation is permitted before a complete committed
and independently revalidated `TRII/1`, followed by a complete committed
`TRIC/1` that binds the exact selected identity record and runtime root. A
partial `TRII/1` or `TRIC/1` therefore authorizes zero allocation. There is at
most 64 serial intents per canonical Windows boot identity. A partial intent,
or a complete intent without a complete matching `TRIM/1`, permanently blocks
every later ordinal during that boot. A complete ready intent followed by a
complete matching `TRAR/1 RECOVERY_COMPLETE` permits exactly the next ordinal;
it does not require a new boot. This closes crash before/after authority-parent
creation, before allocation, after every allocation/duplication, at every
`TRIM/1` byte, before/after flush return, and repeated same-boot restart without
preventing proven post-ready replacement.

Every ready IPC incarnation first commits exactly one `TRIM/1` ready-IPC
manifest record as sequence one in the same selected attempt file. Its previous
digest is exactly SHA-256 of the complete committed `TRIC/1`; no intervening
record is legal. Readiness requires this exact pair and complete-record digest.
The pair creates no alarm-root file or `TRAR/1` attempt file.

`TRIM/1` is a durable statement that the exact acknowledged holder-proof
snapshot existed at the IPC holder-proof point. It is not a statement that all
28 serialized handles remained live when the pre-witness write, flush,
`TRFW/1` witness, readback, later query, or recovery occurred. A complete valid
pair is necessary for operational readiness but is not sufficient: current
child liveness, monitor lease and every later readiness predicate still apply.
A complete valid pair followed by post-proof/pre-readiness peer loss is
therefore a recoverable ready-intent authority with a failed startup outcome,
not an operationally ready service.

Installation authority and IPC authority form one closed runtime-root domain.
The installation subdomain is:

```text
installation attempts = 2
committed installation records = 1
attempt bytes = 4096
maximum installation logical bytes = 4096 + 4096 = 8192
maximum installation partial files = 2
maximum installation partial bytes = 2 * 4096 = 8192
```

The IPC subdomain is:

```text
intent ordinals per boot = 64
attempt files per intent = 2
records per complete intent = 2
maximum attempt-file bytes = 2 * 4096 = 8192
retained boot identities = 64
retained logical intent journals = 64 * 64 = 4096
retained complete records = 4096 * 2 = 8192
retained attempt files = 4096 * 2 = 8192
retained logical bytes = 8192 * 8192 = 67108864
maximum product-reachable partial files per retained boot
  = (64 - 1) * 1 + 2
  = 65
maximum product-reachable partial bytes per retained boot
  = 64 * 4096 + 8192
  = 270336
retained product-reachable partial files = 64 * 65 = 4160
retained product-reachable partial bytes = 64 * 270336 = 17301504
invalid-tree scan bytes cap = 67108864
directory entries below ipc-authority = 64 + 8192 = 8256
```

The product-reachable partial domain starts with a newly created empty runtime
root and includes only product create-new paths, canonical record bytes written
in order, supported process termination at any byte boundary, returned I/O
failure, successful durable commit, declared recovery and declared audited
deletion. It excludes external mutation, arbitrary invalid bytes, filesystem or
storage corruption, power loss, malicious local-user/process, owner-user,
administrator, or SYSTEM tampering and every other excluded failure. An
excluded or externally constructed invalid tree is still
enumerated under the file, entry, per-file, logical-byte and quota caps and
fails closed, but it is never a positive reachability witness.

For product-reachable counters, a partial tail includes a short record and a
complete-length record with absent or partial witness. A failed installation
attempt therefore has length `0..4096`. A prior ready/recovered IPC intent can
retain only one failed `TRIC_INCOMPLETE` or `TRIC_UNWITNESSED` attempt, at most
4,096 bytes, because its other attempt must be the complete valid journal that
permits a later intent. The final blocking intent can retain one 4,096-byte
failed attempt followed by one 8,192-byte
`TRIC_VALID_TRIM_UNWITNESSED` attempt. Thus one boot reaches:

```text
partial files = 63 prior failed a0 + final failed a0 + final a1 = 65
partial bytes = 63 * 4096 + 4096 + 8192 = 270336
```

Across 64 retained boots these are exactly 4,160 files and 17,301,504 bytes.
A complete-length invalid file consumes file and logical-byte scan limits but
is not a product-reachable partial witness. All complete, invalid, partial and
zero-byte attempts consume the applicable hard file, entry and logical limits.
Before any path creation, the authority verifier performs a no-reparse
enumeration of the complete fixed tree and rejects unknown names, files or
entries. A 65th retained boot identity, 65th intent in one boot, 8,193rd file,
67,108,865th byte or other max-plus-one condition blocks readiness before
allocation. No automatic deletion or overwrite occurs. An ended-boot authority
directory may be deleted only by an explicit owner-authorized, deletion-audited
operation that first proves its boot identity differs from the current one and
that no live/recoverable IPC, alarm record or report references the directory.
At least one complete deletion-audit record remains outside the deleted
directory. Thus retention duration is user-controlled while live storage is
hard-bounded. Zero-byte and partial attempts remain attributable by path and
are included in enumeration.

The complete installation runtime root has the exact recursive maxima:

```text
directories = _runtime + installation-authority + ipc-authority
            + 64 boot directories
            = 67
files = 2 installation attempts + 8192 IPC attempts = 8194
directory entries = 67 directories + 8194 files = 8261
maximum logical bytes = 8192 + 67108864 = 67117056
maximum product-reachable partial bytes with valid installation identity
  = 4096 + 17301504
  = 17305600
invalid-tree scan bytes cap = 67117056
reserved/quota bytes = 8192 + 67108864 = 67117056
maximum relative file-path bytes / parent-directory depth = 68 / 3
```

Two partial installation attempts authorize no IPC parent and therefore cannot
coexist with IPC partials. The reachable combined partial maximum uses one
4096-byte failed installation attempt plus one complete installation record and
the product-reachable IPC partial maximum. The separate 8192-byte
installation-partial bound still governs the no-valid-identity exhausted
state. A complete-invalid 4096-byte attempt zero may coexist with a
complete-valid attempt one and is why the maximum installation logical-byte
count is 8,192.

Directories and zero-byte files consume entry/file bounds even when they
consume zero logical bytes. Before every directory or file creation and before
every write, one no-reparse recursive enumeration checks installation, IPC and
combined root limits. The 8195th file, 68th directory, 8262nd entry,
67117057th logical byte, 17305601st product-reachable partial byte, or any
unknown entry blocks before mutation or allocation. An invalid-tree scan that
exceeds 67,117,056 bytes also blocks before further mutation or allocation and
never supports readiness below that cap. Maximum logical bytes and reserved
quota are both 67,117,056 because two complete-length installation attempts are
an admissible bounded resolver state when attempt zero is complete-invalid and
attempt one is complete-valid. This hard logical/quota domain is distinct from
the product-reachable partial-prefix domain. No root/path/ID change resets a
counter.

`TRIM/1` is sequence one and a zero-body 4096-byte canonical record. It reuses
the `TRAO/1`
primitive encoding, 3936-byte prefix, 160-byte trailer, enclosing-journal
sequence/digest chain and durable-commit procedure, with magic `TRIM`. Prefix
variant is `1 READY`, flags at offset 10 are zero, complete length is 4096,
body length is zero, bytes 3840–3903 retain the enclosing-journal previous
digest and SHA-256(empty), and bytes 3904–3935 are zero. All other prefix bytes
are assigned exactly below. `TRIM/1` overrides the `TRAO/1` variant, presence
bitmap and prefix-field semantics; no `TRAO/1` alarm-field requirement applies
to those reassigned bytes.

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | ASCII `TRIM` |
| 4 | 2 | major `1` |
| 6 | 2 | minor `0` |
| 8 | 2 | variant `1 READY` |
| 10 | 2 | flags; zero |
| 12 | 4 | complete record bytes `4096` |
| 16 | 4 | body bytes `0` |
| 20 | 4 | process records `2` |
| 24 | 4 | mapping records `4` |
| 28 | 4 | event records `8` |
| 32 | 8 | IPC-authority-journal sequence; exactly one |
| 40 | 8 | QPC frequency |
| 48 | 16 | IPC incarnation |
| 64 | 16 | service incarnation |
| 80 | 16 | monitor incarnation |
| 96 | 32 | exact support-profile SHA-256 |
| 128 | 32 | exact reason-catalog SHA-256 |
| 160 | 8 | committed mapping bytes `8930432` |
| 168 | 8 | manifest-created QPC |
| 176 | 4 | handle records `24` |
| 180 | 4 | total slots `2052` |
| 184 | 4 | process-record bytes `64` |
| 188 | 4 | mapping-record bytes `128` |
| 192 | 4 | event-record bytes `128` |
| 196 | 4 | handle-record bytes `64` |
| 200 | 4 | name encoding `1 ASCII` |
| 204 | 4 | IPC-owned file-handle count `0` |
| 208 | 32 | old-object census SHA-256 |
| 240 | 32 | canonical object-name-set SHA-256 |
| 272 | 32 | process-table SHA-256 |
| 304 | 32 | handle-table SHA-256 |
| 336 | 4 | Windows logon-session ID |
| 340 | 4 | ready control-handle records `4` |
| 344 | 4 | total ready handle entries `28` |
| 348 | 4 | maximum creation handle entries `54` |
| 352 | 16 | startup-coordinator incarnation |
| 368 | 16 | startup job incarnation |
| 384 | 32 | complete committed `TRIC/1` SHA-256 |
| 416 | 16 | canonical Windows boot identity |
| 432 | 4 | intent ordinal; equals `TRIC/1` |
| 436 | 4 | journal-attempt ordinal; equals `TRIC/1` |
| 440 | 4 | job policy `1 STARTUP_FAIL_CLOSED` |
| 444 | 32 | canonical relative-path SHA-256; equals `TRIC/1` |
| 476 | 36 | zero |
| 512 | 128 | two process records |
| 640 | 512 | four mapping records |
| 1152 | 1024 | eight event records |
| 2176 | 1536 | 24 handle records |
| 3712 | 128 | four control-handle records |
| 3840 | 32 | complete committed `TRIC/1` SHA-256 |
| 3872 | 32 | SHA-256(empty) |
| 3904 | 32 | zero |

The complete `TRIM/1` chain is valid only when its matching `TRIC/1` contains
the currently selected complete `TRII/1` digest, attempt path/ordinal, canonical
installation ID, runtime-root volume/file identity and root-path digest.

The two 64-byte process records are ordered by ordinal `0 SERVICE`,
`1 MONITOR`:

| Relative offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | process ordinal |
| 4 | 4 | process-role enum equal to ordinal plus one |
| 8 | 4 | Windows process ID |
| 12 | 4 | flags; zero |
| 16 | 8 | `PROCESS_CREATION_IDENTITY_FILETIME` |
| 24 | 16 | process incarnation |
| 40 | 24 | zero; process/control handles are only in the control-handle table |

The four 128-byte mapping records are ordered by mapping ordinal and worker
role: persistent roles `0,1`, then live roles `2,3`:

| Relative offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | mapping ordinal |
| 4 | 4 | worker-role enum equal to ordinal plus one |
| 8 | 4 | slot count |
| 12 | 4 | slot bytes `4352` |
| 16 | 8 | mapping bytes, exactly 32 plus slot count times 4352 |
| 24 | 16 | mapping incarnation |
| 40 | 2 | object-name length `53` |
| 42 | 2 | name encoding `1 ASCII` |
| 44 | 80 | exact name bytes then zero padding |
| 124 | 4 | zero |

The eight 128-byte event records are ordered by mapping ordinal, then
`1 COMMAND_READY`, `2 RESULT_READY`:

| Relative offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | event ordinal `0..7` |
| 4 | 4 | owning mapping ordinal |
| 8 | 4 | event-kind enum |
| 12 | 4 | flags; zero |
| 16 | 16 | event incarnation |
| 32 | 2 | object-name length `53` |
| 34 | 2 | name encoding `1 ASCII` |
| 36 | 80 | exact name bytes then zero padding |
| 116 | 12 | zero |

Object names are unique ASCII and contain no NUL inside their declared length.
Let `H` be the 32 lowercase hexadecimal ASCII characters obtained by encoding
the 16 raw IPC-incarnation bytes in stored-byte order, two characters per byte.
Mapping ordinal `MM` and event ordinal `EE` are two lowercase hexadecimal
digits. The exact byte constructions are:

```text
ASCII "Local\TraceRelay-" || H[32] || ASCII "-M" || MM[2]
ASCII "Local\TraceRelay-" || H[32] || ASCII "-E" || EE[2]
```

They are respectively the mapping and event names. Each serialized name is
exactly 53 bytes; no terminator is included in the declared length.
`Local\` resolves only inside the recorded Windows logon session. Startup,
service, monitor and same-boot recovery must prove their current session ID
equals both `TRIC/1` and `TRIM/1` before creating, opening or probing a name.
A wrong-session `OBJECT_NAME_NOT_FOUND` is invalid and cannot prove release.
After a later Windows boot, the old local namespace is instead closed only by
the explicit boot-ended result defined below. Cross-session launch is rejected
before allocation. The runtime-context singleton uses its own session-local
authority and does not reinterpret object names from another session.

The 24 64-byte handle records are ordered by handle ordinal. Ordinals `0..11`
belong to process ordinal 0 and `12..23` to process ordinal 1. Within each
process, local object ordinals `0..3` are the four mappings and `4..11` are
events `0..7`; every process/object pair appears exactly once:

| Relative offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | handle ordinal |
| 4 | 4 | holder process ordinal |
| 8 | 4 | object kind `1 MAPPING` or `2 EVENT` |
| 12 | 4 | mapping/event ordinal |
| 16 | 8 | raw Windows handle value in the holder |
| 24 | 4 | granted-access mask |
| 28 | 4 | inherit flag; zero |
| 32 | 32 | SHA-256 of the exact referenced 128-byte object record |

The four 32-byte control-handle records are ordered exactly:

1. monitor-held handle to service process;
2. service-held handle to monitor process;
3. service-held startup-job handle;
4. monitor-held startup-job handle.

Their layout is:

| Relative offset | Bytes | Field |
|---:|---:|---|
| 0 | 4 | control-handle ordinal |
| 4 | 4 | holder process ordinal |
| 8 | 4 | kind `1 PEER_PROCESS` or `2 STARTUP_JOB` |
| 12 | 4 | target process ordinal; `0xffffffff` for the job |
| 16 | 8 | raw Windows handle value in the holder |
| 24 | 4 | granted-access mask |
| 28 | 4 | inherit flag; zero |

Raw handle identity is exactly `(holder_process_ordinal, raw_handle_value)`.
Duplicate keys inside one holder are invalid. The same raw value in different
holders is legal and does not identify the same handle. The two process-handle
records must target the opposite process; the two job-handle records bind the
one header job incarnation.

Every recorded granted-access mask is exact, not an implementation-selected
superset:

| Handle kind | Exact mask | Required rights |
|---|---:|---|
| mapping in either child | `0x00000006` | `FILE_MAP_READ \| FILE_MAP_WRITE` |
| event in either child | `0x00100002` | `SYNCHRONIZE \| EVENT_MODIFY_STATE` |
| peer process | `0x00101000` | `SYNCHRONIZE \| PROCESS_QUERY_LIMITED_INFORMATION` |
| startup job | `0x0010000c` | `SYNCHRONIZE \| JOB_OBJECT_QUERY \| JOB_OBJECT_TERMINATE` |

The coordinator creates every child handle with `DuplicateHandle`,
`dwDesiredAccess` equal to that row, `bInheritHandle=FALSE`, and
`dwOptions=0`; `DUPLICATE_SAME_ACCESS`, generic rights, all-access masks and
extra standard rights are forbidden. Before `TRIM/1` commit, each holder calls
`NtQueryObject(handle, ObjectBasicInformation=0, ...)` and requires
`STATUS_SUCCESS` plus `PUBLIC_OBJECT_BASIC_INFORMATION.GrantedAccess` byte-equal
to the recorded uint32. This query is version-gated at profile certification;
query failure blocks readiness.

The holder also completes kind/operation probes while still `PRE_READY`:

- every mapping maps and unmaps one read/write view using
  `FILE_MAP_READ | FILE_MAP_WRITE`;
- every event returns only `WAIT_OBJECT_0` or `WAIT_TIMEOUT` from a zero-time
  wait, then succeeds at `SetEvent`, `ResetEvent`, and a final zero-time
  nonsignalled wait;
- every peer-process handle returns `WAIT_TIMEOUT` while the peer is live and
  `GetProcessTimes.lpCreationTime` returns the exact stored
  `PROCESS_CREATION_IDENTITY_FILETIME`;
- every job handle returns `WAIT_TIMEOUT` while either child is live and
  `QueryInformationJobObject` proves both exact process identities are assigned.

The startup-job termination right is proven by exact successful duplication and
the exact queried granted mask; it is not destructively exercised against the
live startup job. All event probes finish nonsignalled before any command can be
admitted. A zero mask, missing bit, extra bit, wrong kind, source/target
mismatch, query mismatch or probe failure prevents `TRIM/1` commit.

`TRIM/1` component digests have these single byte-exact preimages:

```text
old_object_census_sha256 =
  SHA-256(TRIM_bytes[512:3840])

object_name_set_sha256 =
  SHA-256(ASCII "TRIM/1-OBJECT-NAME-SET" || TRIM_bytes[640:2176])

process_table_sha256 =
  SHA-256(ASCII "TRIM/1-PROCESS-TABLE" || TRIM_bytes[512:640])

handle_table_sha256 =
  SHA-256(ASCII "TRIM/1-HANDLE-TABLE" || TRIM_bytes[2176:3840])
```

Half-open ranges are literal. No length prefix, terminator, normalization,
reordering or omitted padding is added. The stored component digests must
match. `ready_ipc_manifest_sha256` is SHA-256 of the complete committed 4096
bytes, including the reused trailer. The `TRIC/1` digest, selected `TRII/1`
digest and path, canonical installation/root facts, planned IPC/process/
coordinator/job identities, Windows session, canonical boot identity, intent
ordinal, attempt ordinal, relative-path digest, geometry and planned names must
equal the matching intent. Duplicate IDs, names, same-holder/raw-handle keys,
process/object pairs or access-mask mismatches invalidate readiness.

Recovery uses `TRAR/1`, a zero-body 4096-byte canonical record. `TRAR/1` uses
the exact `TRAO/1` 3936-byte prefix and 160-byte trailer geometry,
integer/ID/digest rules, and digest algorithm, with magic `TRAR`. Its variant
block at bytes 2048–2559 is:

| Offset within block | Bytes | Field |
|---:|---:|---|
| 0 | 16 | recovery transaction ID |
| 16 | 16 | old IPC incarnation |
| 32 | 4 | variant enum |
| 36 | 4 | canonical slot ordinal |
| 40 | 4 | prior slot-state enum |
| 44 | 4 | availability enum |
| 48 | 16 | alarm ID |
| 64 | 16 | operation ID |
| 80 | 16 | worker incarnation |
| 96 | 8 | slot epoch |
| 104 | 8 | `PROCESS_CREATION_IDENTITY_FILETIME` |
| 112 | 32 | exact `TRAF/1` digest or zero |
| 144 | 32 | old-object census digest |
| 176 | 32 | preceding recovery-record digest |
| 208 | 32 | accumulated inventory digest |
| 240 | 272 | variant overlay defined below |

`TRAR/1` overrides the `TRAO/1` variant/presence table while retaining its
primitive encoding, length, padding and trailer rules. Its prefix presence
bitmap is exactly `0x1000` (`RECOVERY_INVENTORY`). The prefix alarm, session,
worker, mapping, operation, call, slot, dispatch, return, file-reference,
endpoint, body, deadline/outcome and diagnostic fields are zero. Prefix
sequence/QPC, service/monitor/detector identities, profile/catalog digests,
previous record digest, the recovery block, and trailer are required.
Variant-body length is zero and its digest is SHA-256(empty).

The `TRAR/1` variant enum is `1 INVENTORY_OPEN`, `2 SLOT_INVENTORY`,
`3 INVENTORY_SEAL`, `4 OBJECT_RELEASE_PROOF`, `5 UNPROVEN_RESOLUTION`, and
`6 RECOVERY_COMPLETE`; every other value is invalid. Availability is
`1 AVAILABLE` or `2 UNAVAILABLE`. Resolution reason is `1 NONEMPTY` or
`2 UNAVAILABLE`.

The recovery transaction ID is not random or restart-selected. It is the first
16 bytes of:

```text
SHA-256(
  ASCII "TRAR/1-TRANSACTION-ID" ||
  ready_ipc_manifest_sha256[32]
)
```

Every logical sequence has exactly two preassigned create-new attempt paths.
Let `D` be the 64 lowercase hex characters of the manifest digest and `S` the
16 lowercase hex characters of the uint64 logical sequence in big-endian text
order. The rooted relative filename is exactly
`trar-D-sS-a0.bin` or `trar-D-sS-a1.bin`. Creation of either path consumes that
attempt even when zero bytes are written. No side file, parsed prefix or
committed open is needed to attribute it. Existing attempt paths are never
deleted, reused or reassigned. Therefore a missing committed sequence-zero
open resumes only the remaining path for the same deterministic transaction;
after both paths exist without a committed open, state is
`RECOVERY_BLOCKED_OLD_IPC`. A new transaction ID cannot reset the count.

Prefix variant offset 8 and recovery-block variant offset 32 must contain the
same uint32 value; because the prefix field is two bytes, the high two bytes of
the block value are zero. A mismatch rejects the record. For
`INVENTORY_OPEN`, both the prefix previous-record digest and block preceding-
recovery digest are 32 zero bytes. Its initial accumulator is:

```text
SHA-256(
  ASCII "TRAR/1-INVENTORY-SEED" ||
  recovery_transaction_id[16] ||
  old_ipc_incarnation[16] ||
  ready_ipc_manifest_sha256[32]
)
```

`INVENTORY_OPEN` stores this value at block offset 208. Every later committed
record stores SHA-256 of the complete preceding `TRAR/1` bytes in both the
prefix previous-record field and block offset 176; the two copies must match.
The IPC-recovery journal is a new create-new authority domain.
`INVENTORY_OPEN` has enclosing sequence zero. Every later committed record
increments that sequence by exactly one; there is no sentinel or omitted
sequence-zero record.

Common recovery-block presence is closed:

| Common field | Open | Slot inventory | Seal | Release proof | Resolution | Complete |
|---|---|---|---|---|---|---|
| transaction ID, old IPC ID, duplicate variant | required | required | required | required | required | required |
| canonical slot ordinal | zero | required | zero | zero | copied from referenced slot | zero |
| slot state and availability | zero | required under rules below | zero | zero | copied from referenced slot | zero |
| alarm/operation/worker IDs, epoch, process creation, `TRAF/1` digest | zero | exact observed fields or zero when unavailable | zero | zero | exact referenced-slot fields or zero when unavailable | zero |
| old-object census digest | required | same required digest | same required digest | same required digest | same required digest | same required digest |
| preceding recovery-record digest | zero | required | required | required | required | required |
| accumulated inventory digest | exact seed | next accumulator | final accumulator | unchanged final accumulator | unchanged final accumulator | unchanged final accumulator |

The old-object census digest equals the verified `TRIM/1` field at offset 208.
The `INVENTORY_OPEN` ready-manifest digest binds the complete `TRIM/1` record.
All records in one transaction use the same census digest and manifest
identity.

The overlay at block bytes 240–511 is exact by variant.

`INVENTORY_OPEN`:

| Offset | Bytes | Field |
|---:|---:|---|
| 240 | 4 | expected slot records `2052` |
| 244 | 4 | expected mappings `4` |
| 248 | 4 | expected events `8` |
| 252 | 4 | expected handle entries `24` |
| 256 | 8 | expected committed mapping bytes `8930432` |
| 264 | 32 | ready-IPC manifest SHA-256 |
| 296 | 8 | inventory-open QPC |
| 304 | 8 | irreversible recovery-freeze generation |
| 312 | 8 | barrier-acquired QPC |
| 320 | 16 | recovery-coordinator incarnation |
| 336 | 4 | available-mapping bitmap; low four bits only |
| 340 | 4 | service quiescence enum |
| 344 | 4 | monitor quiescence enum |
| 348 | 4 | aggregate active-transition count; zero |
| 352 | 8 | mapping 0 frozen snapshot sequence or zero if unavailable |
| 360 | 8 | mapping 1 frozen snapshot sequence or zero if unavailable |
| 368 | 8 | mapping 2 frozen snapshot sequence or zero if unavailable |
| 376 | 8 | mapping 3 frozen snapshot sequence or zero if unavailable |
| 384 | 32 | recovery-barrier proof SHA-256 |
| 416 | 96 | zero |

Before open attempt zero, the recovery coordinator acquires one irreversible
recovery generation by deriving it and applying the exact section 9.2.1 header protocol to
every accessible mapping: generation `0 -> expected_generation`, then
`RUNNING -> FREEZE_REQUESTED`. An equal existing generation resumes; a
different generation conflicts. Every normal slot transition follows the
count/sequence/recheck protocol in section 9.2.1. Once generation ownership is
acquired, no new transition may mutate a slot. Each live service/monitor owner
either finishes its registered transition and commits `QUIESCED(1)`, or is
terminated and observed as `EXITED(2)` or `IDENTITY_ABSENT(3)`. Every other
enum is invalid.

The barrier is acquired only when all accessible mappings have active count
zero, their snapshot sequences are even and stable, and both process facts are
one of the three closed quiescence results. Crash-left nonzero count or odd
sequence may be normalized only under section 9.2.1 after every possible
mutator is `EXITED` or `IDENTITY_ABSENT`; an alive `QUIESCED` owner forbids
normalization. The coordinator then atomically sets each accessible mapping to
`FROZEN`; this state is irreversible for that IPC incarnation, including after
recovery-coordinator crash. An unavailable mapping has a zero bitmap bit and
zero sequence and is legal only when every process that could mutate it is
exited or identity-absent. No accessible but changing mapping may be relabeled unavailable.

The generation is restart-stable and nonzero:

```text
freeze_generation =
  1 + (
    le_u64(
      SHA-256(
        ASCII "TRAR/1-FREEZE-GENERATION" ||
        recovery_transaction_id[16] ||
        old_ipc_incarnation[16]
      )[0:8]
    )
    mod (2^64 - 1)
  )
```

Every mapping stores that exact value with `FREEZE_REQUESTED` and `FROZEN`.
A restart derives the same value and may continue an equal generation; any
other nonzero generation is a conflicting recovery and blocks progress. A
crash before attempt-file creation therefore consumes no record attempt and
must resume the same already-derived generation rather than create another.

The proof digest is:

```text
SHA-256(
  ASCII "TRAR/1-RECOVERY-BARRIER" ||
  recovery_transaction_id[16] ||
  old_ipc_incarnation[16] ||
  freeze_generation_le_u64 ||
  available_mapping_bitmap_le_u32 ||
  service_quiescence_le_u32 ||
  monitor_quiescence_le_u32 ||
  le_u32(0 active transitions) ||
  mapping_0_sequence_le_u64 || mapping_1_sequence_le_u64 ||
  mapping_2_sequence_le_u64 || mapping_3_sequence_le_u64
)
```

`INVENTORY_OPEN` may commit only after this barrier. Its committed bytes are
the durable recovery-ownership authority. Restart reuses the same generation,
coordinator-independent frozen mappings and deterministic transaction. It
never unfreezes old owners.

`SLOT_INVENTORY` uses an all-zero overlay. Its common block ordinal is in
`0..2051`. When availability is `AVAILABLE`, slot state is one of the twelve
closed states and every identity/reference field equals the inspected slot.
When availability is `UNAVAILABLE`, state and all unobserved identity/
reference fields are zero. The accumulated inventory digest is the SHA-256 of
the exact concatenation:

```text
preceding_accumulator[32] ||
canonical_ordinal_le_u32 ||
availability_le_u32 ||
state_le_u32 ||
common_block_bytes_48_through_143[96]
```

The first slot uses the open seed. Each next slot uses the prior slot's
accumulator. `INVENTORY_SEAL` stores the final slot accumulator unchanged;
release, resolution and complete records also carry that same sealed value at
block offset 208. No other variant updates it.

`INVENTORY_SEAL`:

| Offset | Bytes | Field |
|---:|---:|---|
| 240 | 48 | twelve uint32 state counts in runtime-slot-state enum order |
| 288 | 4 | available count |
| 292 | 4 | unavailable count |
| 296 | 4 | expected slot records `2052` |
| 300 | 4 | actual slot records `2052` |
| 304 | 8 | first inventory-record enclosing sequence |
| 312 | 8 | last inventory-record enclosing sequence |
| 320 | 8 | inventory-seal QPC |
| 328 | 184 | zero |

Available plus unavailable equals 2052. The twelve state counts sum to
available.
The first/last sequence range contains exactly 2052 contiguous
`SLOT_INVENTORY` records in canonical ordinal order. With open at sequence
zero, the first and last inventory sequences are exactly `1` and `2052`;
seal is `2053` and release proof is `2054`.

`OBJECT_RELEASE_PROOF`:

| Offset | Bytes | Field |
|---:|---:|---|
| 240 | 4 | old process count |
| 244 | 4 | proven-exited process count |
| 248 | 4 | mapping count |
| 252 | 4 | released mapping count |
| 256 | 4 | event count |
| 260 | 4 | released event count |
| 264 | 4 | file-handle count |
| 268 | 4 | released file-handle count |
| 272 | 4 | IPC handle-entry count |
| 276 | 4 | released IPC handle-entry count |
| 280 | 8 | committed mapping bytes |
| 288 | 8 | released mapping bytes |
| 296 | 8 | release-proof QPC |
| 304 | 32 | canonical object-name-set SHA-256 |
| 336 | 32 | process-handle evidence SHA-256 |
| 368 | 32 | post-release kernel-object census SHA-256 |
| 400 | 4 | process ordinal 0 exit-result enum |
| 404 | 4 | process ordinal 1 exit-result enum |
| 408 | 4 | named-object absence-result enum |
| 412 | 4 | handle-release-result enum |
| 416 | 4 | recovery Windows logon-session ID |
| 420 | 16 | recovery-observed canonical Windows boot identity |
| 436 | 76 | zero |

The exact paired values are processes `2/2`, mappings `4/4`, events `8/8`,
IPC-owned file handles `0/0`, IPC handle entries `28/28`, and mapping bytes
`8930432/8930432`.

Process exit result is:

1. `WAIT_OBJECT_0`: a peer-held or exact-identity reopened waitable handle
   returned the Windows signaled result;
2. `IDENTITY_ABSENT`: after a successful stable canonical boot-identity query
   equals the stored identity, two checks separated by at least the profile
   absence-recheck interval found no process with the exact PID and creation
   time; PID reuse with a different creation time is absence, while access
   denied or an unqueryable same-PID process is unknown and forbids the proof;
3. `BOOT_EPOCH_ENDED`: a successful stable canonical boot-identity query
   differs byte-for-byte from the stored `TRIM/1` boot identity.

Named-object absence is `1 OBJECT_NAME_NOT_FOUND_SAME_SESSION` only when the
recovery session equals the stored session and every exact reopen returns the
declared not-found result, or `2 LOCAL_NAMESPACE_ENDED_WITH_BOOT` only when the
stable canonical boot identity differs. A wrong-session same-boot probe is
invalid. A failed, unsupported, zero or unstable boot-identity query is unknown,
not a boot change. Handle release result is exactly
`1 ALL_RELEASED_OR_OWNER_EXITED`; it binds all 24 object handles plus four
control handles. v1 mappings are page-file backed, so the IPC-owned file-handle
counts are both zero. Any unknown or unequal fact forbids this variant.

The three release-proof digests are single-valued:

```text
canonical_object_name_set_sha256 =
  verified_TRIM_field_at_offset_240

process_handle_evidence_sha256 =
  SHA-256(
    ASCII "TRAR/1-PROCESS-EXIT" ||
    TRIM_process_record_0[64] || le_u32(process_0_exit_result) ||
    TRIM_process_record_1[64] || le_u32(process_1_exit_result) ||
    recovery_windows_session_id_le_u32 ||
    recovery_observed_windows_boot_id[16]
  )

post_release_kernel_object_census_sha256 =
  SHA-256(
    ASCII "TRAR/1-POST-RELEASE" ||
    for mapping ordinal 0..3:
      le_u32(1 MAPPING) || TRIM_mapping_record[128] ||
      le_u32(named_object_absence_result) ||
    for event ordinal 0..7:
      le_u32(2 EVENT) || TRIM_event_record[128] ||
      le_u32(named_object_absence_result) ||
    for handle ordinal 0..23:
      TRIM_handle_record[64] ||
      le_u32(handle_release_result) ||
    for control-handle ordinal 0..3:
      TRIM_control_handle_record[32] ||
      le_u32(handle_release_result) ||
    recovery_windows_session_id_le_u32 ||
    recovery_observed_windows_boot_id[16]
  )
```

The loops mean exact concatenation in the shown ascending order with no count,
length, delimiter or padding beyond the listed bytes. The fixed counts come
from the verified `TRIM/1` record. Duplicate, missing, reordered, unknown or
noncanonical entries invalidate the proof.

`UNPROVEN_RESOLUTION`:

| Offset | Bytes | Field |
|---:|---:|---|
| 240 | 4 | resolution-reason enum |
| 244 | 4 | source availability |
| 248 | 4 | source slot state or zero when unavailable |
| 252 | 4 | flags; zero |
| 256 | 32 | referenced `SLOT_INVENTORY` record SHA-256 |
| 288 | 32 | referenced `TRAF/1` SHA-256 or zero |
| 320 | 8 | resolution QPC |
| 328 | 184 | zero |

For every resolution:

```text
overlay.source_availability
  = common.availability
  = referenced_SLOT_INVENTORY.availability

overlay.source_slot_state
  = common.slot_state
  = referenced_SLOT_INVENTORY.slot_state

overlay.referenced_TRAF_digest
  = common.TRAF_digest
  = referenced_SLOT_INVENTORY.TRAF_digest
```

Reason is `UNAVAILABLE` if and only if availability is `UNAVAILABLE`; in that
case state, alarm/operation/worker identities, epoch, process creation and
`TRAF/1` digest are all zero in the common block, overlay and referenced
inventory. Reason is `NONEMPTY` if and only if availability is `AVAILABLE` and
runtime state is not `EMPTY`. An available `EMPTY` slot forbids a resolution.
Any duplicate-field mismatch, reason swap, wrong inventory-record digest,
extra resolution or omitted required resolution invalidates recovery.

`RECOVERY_COMPLETE`:

| Offset | Bytes | Field |
|---:|---:|---|
| 240 | 4 | expected inventory records `2052` |
| 244 | 4 | actual inventory records `2052` |
| 248 | 4 | required resolution count |
| 252 | 4 | actual resolution count |
| 256 | 32 | `OBJECT_RELEASE_PROOF` record SHA-256 |
| 288 | 32 | `INVENTORY_SEAL` record SHA-256 |
| 320 | 32 | canonical ordered resolution-set SHA-256 |
| 352 | 8 | recovery-complete QPC |
| 360 | 152 | zero |

Required and actual resolution counts must match. The resolution-set digest
covers exactly the sealed non-`EMPTY` available slots plus every unavailable
slot in canonical ordinal order. All variant-inapplicable common-block and
overlay bytes are zero.

The required ordinal set is computed from the sealed 2052-record inventory.
There is exactly one committed `UNPROVEN_RESOLUTION` for each required ordinal
and none for any other ordinal; duplicate or reordered resolutions are
invalid. Its exact digest is:

```text
SHA-256(
  ASCII "TRAR/1-RESOLUTION-SET" ||
  le_u32(required_resolution_count) ||
  for each required canonical ordinal in ascending order:
    le_u32(canonical_ordinal) ||
    SHA-256(complete_UNPROVEN_RESOLUTION_TRAR_record[4096])
)
```

For an empty required set, the preimage ends after the zero count. No implicit
set serializer, record field subset, delimiter, normalization or padding is
added.

On restart, recovery accepts only the longest fully committed prefix whose
transaction ID, old IPC ID, sequence, duplicate variant, previous digest and
accumulator all verify. A partial attempt is retained but is never an
accumulator or chain input. Recovery continues the same transaction at the
first missing logical record and its remaining prescribed attempt; it never
chooses a new seed. If no `INVENTORY_OPEN` committed, the deterministic
manifest-derived transaction and the create-new attempt paths still identify
which open attempt was consumed. Recovery may use only its remaining assigned
path; it never creates a new ID or resets an ordinal.

Variants are `INVENTORY_OPEN`, `SLOT_INVENTORY`,
`INVENTORY_SEAL`, `OBJECT_RELEASE_PROOF`, `UNPROVEN_RESOLUTION`, and
`RECOVERY_COMPLETE`. Every missing field is zero. `SLOT_INVENTORY` records
exactly one canonical ordinal in this order: persistent mapping 0, persistent
mapping 1, live mapping 0, live mapping 1; within each mapping, ascending slot
index. Even `EMPTY` and inaccessible slots receive a record. An inaccessible
slot uses `availability=UNAVAILABLE`, contains no invented alarm/operation/
worker/reference identity, and is conservatively unproven.

The two-phase protocol is:

1. acquire the irreversible quiesce/freeze barrier above;
2. commit `INVENTORY_OPEN` binding that barrier;
3. from the frozen mappings, commit exactly 2052 `SLOT_INVENTORY` records; if a
   mapping was already unavailable at the barrier, emit `UNAVAILABLE` for every
   canonical ordinal in that mapping;
4. commit `INVENTORY_SEAL` binding all 2052 records, counts by state and
   availability, and the accumulated digest;
5. only after the seal, wait for old processes to be gone and prove every old
   mapping, event, IPC handle entry, and committed mapping byte
   released; commit `OBJECT_RELEASE_PROOF`;
6. commit exactly one `UNPROVEN_RESOLUTION` for each non-`EMPTY` or
   `UNAVAILABLE` slot; an `EMPTY` slot needs no resolution but remains covered
   by the sealed inventory;
7. commit `RECOVERY_COMPLETE` binding the inventory seal, release proof,
   required-resolution count, actual-resolution count, and final digest;
8. only after `RECOVERY_COMPLETE` may exactly the next same-boot intent ordinal
   create one replacement IPC set; intent 64 requires a different canonical
   boot identity.

A crash before `INVENTORY_SEAL` releases no old object by product action. The
next recovery reuses no partial record; it starts the next create-new recovery
attempt while old authority remains. A crash during physical release is safe
because the sealed inventory is already durable. A crash after release but
before any resolution is safe because the next recovery reads the durable
inventory and repeats the object census before continuing. A crash after any
resolution resumes from the committed recovery chain. Thus no crash window
depends on an off-slot memory/cache after old authority disappears.

Each required `TRAR/1` record has two create-new attempts, each reserving 4096
bytes. An uncommitted attempt retains at most 4096 bytes, including a complete
pre-witness record with absent or partial witness, and consumes its attempt.
Attempt two may commit the complete record; if it also fails or becomes
partial, recovery enters `RECOVERY_BLOCKED_OLD_IPC`, retains every byte, emits
the external health alarm when possible, and performs no release not already
completed and no replacement allocation. It never borrows capacity or retries
unboundedly.

The exact worst-case recovery domain is:

```text
inventory records = 1 open + 2052 slots + 1 seal = 2054
resolution records = 2052
control records = 1 release proof + 1 recovery complete = 2
maximum committed records = 4108
reserved attempt files = 4108 * 2 = 8216
reserved attempt bytes = 4108 * 2 * 4096 = 33652736
reachable retained partial files
  = 4107 first-attempt partials + 2 final-record partials
  = 4109
reachable retained partial bytes = 4109 * 4096 = 16830464
successful-completion partial maximum = 4108 * 4096 = 16826368
```

The `8216` file and `33652736` byte values are conservative capacity reserved
before readiness, not claims that every reserved attempt can simultaneously be
partial. In the maximum failed execution, records 1 through 4107 each leave a
first-attempt partial and commit on attempt two; record 4108 leaves both
attempts partial and stops. That path has 4107 complete plus 4109 partial files,
8216 total. Any earlier second-attempt failure stops earlier.

This reserve is runtime-context-global, exists before readiness, is charged to the
monitor-incarnation, alarm-root quota, protected alarm reserve, 12000-file and
16000-directory-entry domains, and is not available to ordinary alarm,
deletion-audit, or diagnostic writes. Combined with 128 maximum
session-unknown alarm reservations and one maximum known-session publication
domain:

```text
protected bytes = 21495808 + 33652736 + 4194304 = 59342848
alarm-root partial-tail bytes
  = 21495808 + 16830464 + 4194304
  = 42520576
alarm-root partial-tail files = 1024 + 4109 + 64 = 5197
alarm-root total attempt files = 1024 + 8216 + 64 = 9304
```

All remain inside the profile's 134217728-byte protected reserve and root
file/directory bounds. Exact maxima succeed; the next record, attempt file, or
byte blocks readiness before allocation.

### 9.3 Independent channel state and deadlines

After global envelope admission, the coordinator independently admits one
persistent and one live initial channel attempt. Each admission becomes
exactly one worker dispatch or one coordinator-owned pre-dispatch
`FAILED_LIMIT`. Neither channel admission has a commit, reservation, queue, or
response precondition owned by the other channel.

| Path | Persistent worker | Live worker | Required result |
|---|---|---|---|
| known-session global envelope count is fifth concurrent or 33rd cumulative | no channel operation exists | no channel operation exists | one `ALARM_ENVELOPE_ADMISSION_LIMIT`; fail-closed; channel dispatch-or-limit rule is not entered |
| capacity and storage usable | reserve two slots; commit `ALARM_FIRST_ATTEMPT`; later commit `ALARM_CHANNELS_TERMINAL` | attempt bounded live frames | persistent and live outcomes remain independent |
| no EMPTY channel slot at attempt admission | coordinator records pre-dispatch `FAILED_LIMIT`; no worker dispatch is fabricated | peer channel still performs its own admission | the limited channel is `FAILED`; peer outcome remains independent |
| reservation or first-record write fails | `FAILED_LIMIT` or `FAILED_IO`; retain any partial/orphan evidence | still dispatch and attempt | live may succeed; no persistent success is claimed |
| persistent succeeds; initial live fails; terminal live diagnostic succeeds | persistent publication remains `SUCCEEDED` | live publication is `FAILED`; diagnostic delivery is `SUCCEEDED` | `TR-ALARM-PUBLISHED`; diagnostic acceptance never upgrades live publication |
| persistent fails; initial live succeeds | persistent publication is non-success | live publication is `SUCCEEDED` | runtime reports success; offline verifier accepts it only from a committed bundle `LIVE_INITIAL_FRAME_ACCEPTED` observation |
| persistent fails; initial live fails; terminal live diagnostic succeeds | no persistent success | live publication is `FAILED`; diagnostic delivery is `SUCCEEDED` | `TR-ALARM-PUBLICATION-FAILED`; no terminal-frame self-upgrade |
| both initial publications fail | no success | no success | `TR-ALARM-PUBLICATION-FAILED` when response remains possible |
| an initial worker lacks a completely validated returned result at initial-outcome freeze deadline | `TIMEOUT_UNKNOWN` | `TIMEOUT_UNKNOWN` | tuple freezes at the deadline; later return or validation cannot upgrade publication |
| initial call return or complete validation occurs at or after the exclusive freeze deadline | retain root record/result/reference as diagnostic | write `INITIAL_PUBLICATION_LATE_RETURN` | frozen initial result remains `TIMEOUT_UNKNOWN`; neither runtime recovery nor offline verification upgrades it |
| terminal call has no completely validated returned result at its tuple-relative observation deadline and timeout observation commits | call or validation may still be executing; slot remains pinned | coordinator records `TERMINAL_EMISSION_TIMEOUT_FROZEN` | terminal outcome is durably `TIMEOUT_UNKNOWN`; late return/validation is diagnostic only |
| crash or journal failure before timeout observation commit | physical call result unknown | no durable timeout authority | current-process memory is lost; runtime recovery and offline verifier return `UNKNOWN` / `TR-ALARM-UNPROVEN` for the terminal outcome |
| late return or validation after a committed timeout observation | returned result/validation is retained separately | timeout record remains unchanged | `TERMINAL_EMISSION_LATE_RETURN` is non-normative and cannot alter the frozen result |
| alarm-root persistent commit plus timely returned-result validation observation consistent with frozen tuple | runtime recovery uses root chain plus timely validated observation | bundle contains exact copied record bytes/chain/position plus timely validated observation | both evaluators may independently prove persistent publication from their own input |
| crash after alarm-root commit before timely returned-result validation observation commit | root exists but timely validated return is unproven | bundle has no persistent authority | runtime recovery and offline verifier report `TR-ALARM-UNPROVEN`; root alone cannot upgrade the tuple |
| restart after bundle live-success observation | persistent prefix optional | initial acceptance is a durable local API observation | offline verifier may prove live publication, but not subscriber processing |
| no root proof for recovery or no matching bundle observation for verifier | no authority in that evaluator's input | live history unknown | that evaluator emits `TR-ALARM-UNPROVEN` |

Each initial channel admission must complete before the exclusive
`alarm_initial_attempt_admission_deadline_ms` measured from the in-memory
`detected_at` timestamp. Completion is exactly one worker dispatch or one
coordinator-owned pre-dispatch `FAILED_LIMIT`; the latter is not relabeled as a
worker dispatch. Missing both alternatives at the boundary violates liveness,
leaves that channel `UNKNOWN_PENDING` until the outcome-freeze deadline, and
then freezes `TIMEOUT_UNKNOWN`. Failure or backpressure in one channel does not
wait for the other and does not delay session fail-closed behavior.

Before the exclusive
`detected_at + alarm_initial_outcome_freeze_deadline_ms`, each channel's
initial publication result may be `UNKNOWN_PENDING`. At that deadline, each
initial result becomes exactly one of:

- `SUCCEEDED`, only when the coordinator observed the returned committed
  persistent record position or accepted live initial-frame identity and
  completed all applicable result/reference validation strictly before the
  exclusive freeze deadline;
- `FAILED`, including limit, returned I/O error, no subscriber, full queue,
  broken endpoint, or result/reference validation rejected strictly before the
  deadline;
- `TIMEOUT_UNKNOWN`, when call completion or complete validation cannot be
  proved strictly before the deadline.

The coordinator then freezes one non-self-referential publication tuple:

- `persistent_initial_outcome`;
- `live_initial_outcome`;
- `overall_persistent_publication_outcome`, which is `SUCCEEDED` exactly when
  the persistent initial outcome is `SUCCEEDED`;
- `overall_live_publication_outcome`, which is `SUCCEEDED` exactly when the
  live initial outcome is `SUCCEEDED`;
- `alarm_publication_outcome`, which is `SUCCEEDED` exactly when either
  overall channel outcome is `SUCCEEDED`;
- the tuple-freeze monotonic timestamp and deadline classification.

The frozen tuple has priority over every later physical return, root record,
return observation, restart reconstruction, or copied-bundle artifact. A
call return or validation completed exactly at the exclusive deadline is late.
There is exactly one nonzero `tuple_frozen_at` for an alarm. An initial
observation committed before that instant writes zero in the tuple field and
binds its own channel-decision timestamp. An initial observation committed
afterward copies the exact immutable tuple timestamp. No initial decision,
late return, timeout, terminal decision, query, or recovery may create or
replace that timestamp. Every timely initial observation binds both return/
validation timestamps, validation outcome and exact body/reference; any
mismatch is invalid rather than a second candidate outcome.

When persistent reservation succeeds, slot one is `ALARM_FIRST_ATTEMPT` and
slot two is the same-ID `ALARM_CHANNELS_TERMINAL`. Slot two carries the frozen
publication tuple. If slot one cannot commit, persistent publication is not
successful. If slot one commits but slot two does not, initial persistent
success remains a fact but the final tuple is unproven.

After the tuple freezes, the persistent terminal-record commit and live
same-ID terminal diagnostic-frame send are independent terminal attempts. Each
terminal channel admission must complete before the exclusive
`tuple_frozen_at + alarm_terminal_attempt_admission_deadline_ms` as exactly one
worker dispatch or one coordinator-owned pre-dispatch `FAILED_LIMIT`. A limit
decision sets that terminal delivery outcome to `FAILED` and requires no
worker result; missing both alternatives remains `UNKNOWN_PENDING` until the
terminal observation deadline and then freezes `TIMEOUT_UNKNOWN`. This
deadline has a strictly positive profile value and is measured from the actual
tuple freeze, never from `detected_at`.

Their own results are respectively
`persistent_terminal_record_delivery_outcome` and
`live_terminal_frame_delivery_outcome`. Neither field is part of the frame or
record whose delivery it describes. A returned call is recorded by a
subsequent detector-journal return observation; a no-return-by-deadline result
is recorded by the coordinator-owned timeout-decision observation.
Consequently no terminal emission is self-referential. Until the exclusive
`tuple_frozen_at + alarm_terminal_emission_observation_deadline_ms`, a terminal
emission result may be `UNKNOWN_PENDING`; at that deadline it freezes to
`SUCCEEDED` or `FAILED` only when call return and complete validation were
observed strictly before the deadline, otherwise `TIMEOUT_UNKNOWN`.

For every returned channel call, the detector attempts a non-blocking return
observation after result validation completes. It binds the returned result,
`call_return_observed_at`, `result_validation_completed_at`, validation
outcome, exact deadline, and the fields in section 7.3. An initial result whose
return and validation both complete strictly before its freeze deadline uses
`PERSISTENT_INITIAL_COMMITTED` or `LIVE_INITIAL_FRAME_ACCEPTED`. A validation
rejection before the deadline uses a returned-failure observation. If either
timestamp is at or after the exclusive boundary, it uses
`INITIAL_PUBLICATION_LATE_RETURN` and is diagnostic only.

If a terminal call has no completely validated returned result at the
exclusive observation deadline, the coordinator first freezes
`TIMEOUT_UNKNOWN` in memory, records its exact monotonic
no-validated-result-by-deadline observation, and immediately dispatches an
isolated bounded journal commit for `TERMINAL_EMISSION_TIMEOUT_FROZEN`. The
timeout observation may commit without call return or while validation remains
pending. Its valid durable record is authority for the
no-validated-result-by-deadline fact; no record observes its own commit.

The commit is operationally required to return before the exclusive
`timeout_decision_at + alarm_timeout_decision_commit_deadline_ms`. An
independent release/runtime harness observes dispatch and durable-commit return
outside the record and retains raw monotonic measurements. A miss fails the
liveness requirement and forces degraded/fail-closed handling, but it does not
change the truth represented by a valid record that eventually committed.
Offline verification never claims that the physical commit met this liveness
deadline.

For a known session, return and timeout observations commit in the bundle's
`alarm-publication-observations` role. For a session-unknown alarm they commit
in the actual detector/publisher's own service- or monitor-incarnation alarm
journal under the alarm root. The writer may not append to the peer's journal.
Every session-unknown observation binds detector role, writer incarnation,
last-known service and monitor incarnations, alarm ID, and journal chain
identity. Recovery/query enumerate both journal kinds and reject a forged,
wrong-role, wrong-incarnation, or cross-journal writer. Monitor-incarnation and
session-unknown aggregate charging is independent of which authorized
detector-owned journal stores the observation. Within an offline bundle,
`PERSISTENT_INITIAL_COMMITTED` is authoritative for the exact copied
persistent record only when both its return and complete-validation timestamps
are timely and it agrees with the frozen tuple;
`LIVE_INITIAL_FRAME_ACCEPTED` has the same timely-return-and-validation
condition for local endpoint acceptance; a committed
`TERMINAL_EMISSION_TIMEOUT_FROZEN` is authoritative only for the terminal
no-validated-result-by-deadline decision. Initial/terminal late returns or
validations and
terminal-frame acceptance remain diagnostic.

If the timeout-decision commit fails or the process crashes before any valid
record commits, the current process may retain its frozen in-memory timeout
only until exit. Recovery and offline verification cannot invent that fact:
the terminal outcome is `UNKNOWN` and the result is `TR-ALARM-UNPROVEN`.
TraceRelay declares monitoring/alarm evidence degraded, blocks new admission,
preserves every committed prefix, saves recoverable state, and terminates the
affected application/session fail-closed. A commit that returns after its
liveness deadline triggers the same runtime degradation but remains durable
truth authority. Neither failure path recursively requires another alarm
through the failed path.

A call return or result validation completed after the terminal deadline is
written only as
`TERMINAL_EMISSION_LATE_RETURN`, with the same call/emission ID and returned
result, validation outcome, and exact body/reference facts. It is
non-normative diagnostic evidence. It cannot replace, erase, or upgrade a
committed timeout observation or an unproven crash window. Likewise, an
initial call return or validation completed at or after its freeze deadline is
written only as `INITIAL_PUBLICATION_LATE_RETURN`. If the process crashes after
alarm-root commit or endpoint acceptance but before complete validation or
before a matching timely return observation commits, runtime success may have
occurred but both recovery and offline verifier state are `UNKNOWN`; neither
infers success from the physical artifact alone.

There is no initial-publication `UNKNOWN_PENDING` state after
`alarm_initial_outcome_freeze_deadline_ms`; terminal-emission pending state has
its separate tuple-relative observation deadline above. If neither initial
publication attempt is `SUCCEEDED`, the runtime selects
`TR-ALARM-PUBLICATION-FAILED`. Runtime recovery selects
`TR-ALARM-UNPROVEN` whenever its alarm-root chain plus matching timely
returned-result validation observation cannot prove persistent initial
publication and its available runtime journal cannot prove timely validated
live initial publication, or when it cannot prove the frozen terminal tuple.
Offline verification independently selects `TR-ALARM-UNPROVEN` whenever the
self-contained bundle lacks a matching timely
`PERSISTENT_INITIAL_COMMITTED` exact-record observation or timely
`LIVE_INITIAL_FRAME_ACCEPTED` consistent with the frozen tuple, or lacks the
frozen terminal tuple and every required terminal return/timeout observation.
Neither evaluation infers live delivery, terminal diagnostic delivery,
subscriber processing, operator receipt, initial success from a late/root-only
artifact, or a timeout decision from elapsed wall time alone.

### 9.4 Query

Alarm query is read-only, paginated, bounded, ordered by incarnation and
sequence, and may report gaps. It never repairs or silently deduplicates source
records.

Pagination is byte-aware. A page contains at most the profile record count and
only the largest stable prefix whose complete canonical response, including
framing, remains within both `max_alarm_query_payload_bytes` and
`max_control_response_bytes`. One record that cannot fit is returned as a
stable oversize-record failure; it is never split or silently omitted. The
continuation token binds the last returned incarnation, sequence, alarm ID, and
query filter. Empty, final, and truncated pages have distinct stable outcomes.

## 10. Verifier total classification

### 10.1 Preflight

The verifier accepts exactly one absolute session directory. These failures
produce `INPUT_ERROR` before evidence evaluation:

- path absent, not a directory, non-absolute, unsupported filesystem, reparse
  traversal, or outside the supported size/profile envelope;
- access denied before any authoritative input is accepted;
- unsupported schema major, digest suite, or support-profile ID.

Preflight counts the whole directory tree before evidence evaluation. Total
logical bytes, file count, directory entries, path depth, normalized relative
path UTF-8 bytes, and wall time are each bounded by the frozen profile.
Allocated-size metadata is reported but does not replace logical-byte limits.
An input that exceeds a preflight bound is `INPUT_ERROR`; a bound exceeded
after authoritative evaluation begins is `INTERNAL_ERROR`.

An unreadable or malformed manifest that claims a supported schema is evidence
malformation and produces `INVALID`, not `INPUT_ERROR`.

### 10.2 Priority

After preflight, the total priority is:

1. `INTERNAL_ERROR` if verifier execution cannot complete due to its own
   exception, exhausted verifier resource, or a mid-read OS failure;
2. `INVALID` if complete evaluation finds any structural, identity, digest,
   sequence, range, state, or cross-journal invariant violation;
3. `INCOMPLETE` if structure is valid but any clean predicate is false,
   including partial tail, absent terminal, unknown outcome, monitor gap,
   alarm-unproven, or writer limit closure;
4. `PASS` only if every clean predicate is true.

If `INTERNAL_ERROR` occurs after a reliable evidence fact was found, the final
class remains `INTERNAL_ERROR`, `evaluation_complete=false`, and the report
retains the observed fact using an `OBSERVED_*` reason. The verifier never
upgrades to `INVALID`, `INCOMPLETE`, or `PASS` without total evaluation.

### 10.3 Combination truth table

| Conditions after preflight | Result |
|---|---|
| verifier cannot finish, with or without observed evidence issues | `INTERNAL_ERROR` |
| one or more invalid invariants, with or without incomplete conditions | `INVALID` |
| no invalid invariant; one or more incomplete conditions | `INCOMPLETE` |
| no invalid, incomplete, input, or internal condition | `PASS` |

Examples:

- invalid digest plus partial tail: `INVALID`;
- valid committed prefix plus partial tail: `INCOMPLETE`;
- unsupported major version: `INPUT_ERROR`;
- supported version with malformed version field: `INVALID`;
- permission loss during a scan: `INTERNAL_ERROR`;
- report-detail truncation: class unchanged.

### 10.4 Stable output

Reason ordering is:

1. ascending numeric catalog priority; lower numbers appear first;
2. earliest journal sequence, with absent sequence last;
3. direction order `CLIENT_TO_UPSTREAM`, then `UPSTREAM_TO_CLIENT`;
4. start offset ascending, with absent offset last;
5. stable reason ID.

For identical keys through stable reason ID, the canonical serialized detail
bytes break ties lexicographically. When final class is `INTERNAL_ERROR`,
`evaluation_complete=false`; one primary `TR-INTERNAL-*` reason is first, and
each reliable defect observed before failure is represented only by the
corresponding cataloged `TR-OBSERVED-*` reason. Observed reasons contribute to
counts but cannot change the final class.

The verifier computes total counts before truncation. The canonical UTF-8
machine report uses these non-overlapping byte budgets from the profile:

1. mandatory header and summary;
2. complete reason-count table;
3. bounded sequence lists;
4. bounded ordered issue details.

The four budgets sum to `max_report_bytes`. Mandatory fields, final class,
exit, identity, scope, evaluation-complete state, exact totals, terminal and
monitor summaries, assurance exclusions, and all distinct catalog reason
counts are never removed. The catalog cardinality must fit the reason-count
budget; otherwise release validation fails. Sequence entries and issue details
are added as complete canonical entries in their stable order until the next
entry would exceed that section or the global limit. No partial entry is
emitted. Any omission sets the corresponding truncation flag and
`details_truncated=true`; result class and total counts remain unchanged.

Exit codes are frozen in `reason-exit-catalog.v1.json`.

## 11. Windows runtime-context and session-token contract

### 11.1 Runtime-context boundary

One supported runtime context is one current Windows user and one Windows logon
session. One installation is one valid `TRII/1`, one exact final installation
runtime-root identity, and the user-SID/logon-session attribution observed at
initialization.

- control and monitor IPC use the local logon-session namespace and bind the
  exact installation, process identities, and fresh incarnation IDs;
- client data binds only to loopback and additionally requires the session
  token;
- evidence, alarm, and installation runtime roots need only grant the current
  process every operation required for normal use;
- packaged files and roots are checked for existence, expected type, final
  identity, supported storage, and required access, not a custom DACL matrix.

The recorded user SID and logon-session ID prevent accidental context mismatch;
they are not a hostile-user authorization boundary. v1 makes no guarantee
against same-user malicious processes, another user, administrators, SYSTEM,
kernel actors, deliberate ACL changes, memory inspection, or evidence/path
tampering.

### 11.2 Local control association

Mutating control commands require:

1. connection through current-logon-session local IPC;
2. exact installation and held peer-process identity;
3. a current service-incarnation challenge;
4. a request ID rejected on duplicate or cross-incarnation replay;
5. command-specific schema, state, bound, and target validation, including
   deletion confirmation where applicable.

Read-only status requires the same current-instance association. Control
responses never echo session tokens after initial issuance.

### 11.3 Session tokens

- exactly 32 random bytes from the Windows cryptographic random source;
- encoded as base64url without padding for `ClientHello.v1`;
- returned once through the local control response;
- plaintext exists only as required for issuance, local transport,
  authentication parsing, and comparison;
- TraceRelay does not intentionally persist plaintext to evidence, alarm,
  deletion audit, ordinary diagnostic log, terminal output, report, or a later
  control response;
- the service retains only non-reversible comparison material after issuance;
- validation compares the complete fixed-length derived value and rejects
  malformed length, encoding, session, incarnation, state, or deadline;
- ordinary temporary product buffers are released after the authentication
  decision; locked memory, deterministic overwrite timing, anti-dump behavior,
  pagefile exclusion, and Windows Error Reporting hardening are not claimed;
- bound to one session and one service incarnation;
- invalid after claim, revocation, expiry, or service restart.

The token prevents accidental association errors and replay within the defined
state machine. It is not a secrecy or authentication guarantee against a local
actor able to inspect, inject into, or modify the trusted user's processes.
Tests cover source, length, encoding, lifecycle, association, replay, restart,
and ordinary persistent artifacts. They do not scan arbitrary process memory
or require a launcher/client zeroization contract.

An external launcher or client remains outside TraceRelay ownership. It must
send the issued token exactly once before application payload, obey framing and
deadlines, and treat rejection as terminal for that connection. TraceRelay
makes no claim about erasing external-process memory.

Revocation wins according to section 5.5. Revoking an ACTIVE session triggers
fail-closed drain and incomplete terminal; it does not retroactively erase
evidence.

## 12. Explicit deletion

### 12.1 Objects

Allowed:

- one terminal session evidence directory;
- one unused, never-activated registration metadata object;
- one disabled application identity with no remaining registration or session
  reference;
- one complete IPC-authority boot directory whose canonical boot identity
  differs from the current stable boot identity and whose every ready IPC has
  complete release/recovery, with no alarm, report, session or live runtime
  reference.

Forbidden in v1:

- ACTIVE, DRAINING, or nonterminal session evidence;
- an evidence, alarm or installation runtime root as a whole;
- either installation-authority attempt;
- persistent alarm records;
- deletion-audit records;
- support-profile history or compatibility assets;
- any path outside the three canonical configured roots.

### 12.2 Authorization and binding

Deletion requires a current-instance local control request containing:

- exact target type and ID;
- canonical final path returned by inspect;
- current immutable target-manifest digest;
- a one-use confirmation nonce issued by inspect, bound to all preceding
  fields and expiring after the profile deadline.

Any mismatch rejects before mutation. A session verifier holds a no-share-
delete handle; deletion fails while a verifier or capture handle exists.
For an IPC-authority boot directory, inspect enumerates the exact fixed-name
product-created tree, rejects an unexpected internal reparse object or final
path escape, and binds every relative path, final identity, file length, and
SHA-256 into the target manifest. A zero-byte or partial attempt is included,
never silently omitted.

### 12.3 Transaction

The deletion audit is under the configured alarm root, outside every deletable
session directory, in a create-new identity bound to the installation and
runtime-context attribution. It counts against both the dedicated
deletion-audit quota and the alarm-root quota, but cannot consume the
alarm-required reserve.

States:

1. durably commit `DELETE_INTENT`;
2. revalidate identity, path, digest, terminal state, and exclusive access;
3. delete only the bound target;
4. durably commit `DELETE_SUCCEEDED` or `DELETE_FAILED`;
5. expose the durable operation state through read-only `delete-status`;
6. return final success only after `DELETE_SUCCEEDED` commits.

Deletion is an asynchronous control operation. `delete-submit` commits
`DELETE_INTENT` and returns `ACCEPTED` plus a durable operation ID inside the
ordinary control-response deadline. It is not deletion success. v1 provides no
cancel after intent commit; the bounded worker continues or recovery classifies
the operation. `delete-status` returns `ACCEPTED`, `RUNNING`, `SUCCEEDED`,
`FAILED`, or `UNKNOWN` without waiting for mutation completion.

The completion deadline is anchored at `DELETE_INTENT`. On deadline, the
supervisor stops dispatching new deletion work, isolates or terminates the
worker boundary, commits `DELETE_UNKNOWN` when possible, attempts an alarm, and
returns the stable unknown status. It does not infer whether a kernel-stuck
mutation physically ended.

Crash outcomes:

- before committed intent: no authorized deletion;
- after intent and before confirmed target mutation: `DELETE_UNKNOWN` until
  recovery inspects exact identity;
- after target removal and before outcome commit: remains `DELETE_UNKNOWN`,
  never inferred as success;
- after committed success: success is proven by the external audit;
- if audit storage is unavailable: deletion does not start.

After an initial `DELETE_UNKNOWN`, recovery may append at most one
`DELETE_RECOVERY_OBSERVATION` bound to the operation. It records exact target
identity facts and may prove failure when the unchanged target still exists;
target absence never upgrades unknown to success. Later recoveries read that
fact without appending. Recovery never recreates or repairs deleted evidence.

### 12.4 Audit capacity and admission

Every audit record is bounded by the profile record size. Total audit logical
bytes and committed records are inclusive hard maxima. Before
`DELETE_INTENT`, admission reserves three maximum audit records: one intent,
one terminal/unknown outcome, and one possible recovery observation. If that
reservation would exceed the dedicated audit quota, alarm-root quota, or
alarm-required reserve, `delete-submit` fails before target mutation with the
stable audit-full reason.

Audit full does not delete or rotate old audit records and does not invalidate
historical evidence. It disables new deletion submission and reports degraded
deletion readiness; capture readiness may remain true only while the separate
alarm reserve and all capture prerequisites remain satisfied. Recovery may use
only previously reserved outcome capacity for an admitted operation.

## 13. Runtime-context cardinality

Exactly one TraceRelay service instance and at most one ACTIVE session are
allowed inside one supported current-user/logon-session runtime context,
independent of installation runtime root, display name, supplied service
identity, or executable copy inside that context.

The runtime context has:

- one session-local singleton service authority whose name derives only from
  the fixed TraceRelay product identity, never caller or path input;
- one session-local singleton monitor authority;
- one serialized ACTIVE-slot authority owned by the singleton service;
- one current user/logon-session attribution, service incarnation, monitor
  incarnation, evidence-root binding, alarm-root binding, installation ID,
  selected `TRII/1` digest, and installation-runtime-root binding.

The singleton authority is OS-enforced inside the current Windows logon
session. A second process in that context can only observe `ALREADY_RUNNING`;
it cannot create another service or ACTIVE slot by changing a name, root, or
executable path. v1 makes no exclusivity or security claim across users or
logon sessions.

If runtime-context exclusivity is unavailable, ambiguous, or lost, readiness
and session activation fail closed. v1 does not rebind the running product to
another installation identity or root. A fresh installation requires a new
empty installation runtime root and does not merge, delete, or rewrite
historical evidence.

## 14. Bounded execution and resources

### 14.1 Uncancellable calls

Every potentially blocking OS operation runs in an execution boundary that
cannot block the supervisor state machine indefinitely. An operation that
cannot be cancelled is isolated in a worker process. On deadline:

1. supervisor stops new reads and forwarding;
2. session becomes incomplete;
3. monitor receives declared-unhealthy state;
4. supervisor abandons or terminates the worker boundary;
5. control returns a bounded failure result.

The product does not promise that a kernel-stuck call or worker process has
physically vanished by the deadline. It promises bounded supervisor decision,
fail-closed forwarding, alarm attempt, and an explicit
`TR-INCOMPLETE-WORKER-TERMINATION-UNCONFIRMED` state. New sessions remain
blocked until exclusive worker resources are proven released.

### 14.2 Unified limit rule

All writer, monitor, alarm, deletion-audit, session, root, verifier, report,
control, registration, application-identity, worker, handle, subscriber,
metadata, and diagnostic limits are in the frozen support profile.

Installation and IPC authority use the `storage_limits` and
`alarm_ipc_limits` domains. Their static closure is:

```text
TRII/1 installation identity = 3936 prefix + 160 trailer = 4096
installation attempts / committed records = 2 / 1
installation size states / decision pairs = 6 / 36
installation maximum logical / partial bytes = 8192 / 8192
runtime-root directories / files / entries = 67 / 8194 / 8261
runtime-root maximum logical / product-reachable partial bytes = 67117056 / 17305600
runtime-root invalid-tree scan bytes cap = 67117056
runtime-root reserved quota bytes = 67117056
runtime-root maximum relative file-path bytes / parent-directory depth = 68 / 3

mapping_header_bytes = 32
slot_bytes = 256 + 4096 = 4352
persistent slots = 2 workers * 2 slots
live slots = 2 workers * 1024 slots
aggregate_mapping_bytes
  = 2 * (32 + 2 * 4352) + 2 * (32 + 1024 * 4352)
  = 8930432
mapping_count = 4
event_object_count = 4 * 2 = 8
handle_entries = (4 mappings + 8 events) * 2 processes = 24
ready control-handle entries = 4
ready IPC handle entries = 24 + 4 = 28
maximum pre-ready creation handle entries
  = 12 coordinator mapping/event handles
  + 24 duplicated child mapping/event handles
  + 2 coordinator-held child-process handles
  + 2 child peer-process handles
  + 2 child startup-job handles
  + 1 coordinator startup-job handle
  + 8 steady bootstrap pipe-handle entries
  + 3 transient bootstrap I/O-event handle entries
  = 54
child-process-creation transient handle entries
  = 14 endpoint/process/thread/Job entries
  + 1 service pending-read event
  = 15
serial pair construction connect-event entries = 1
steady bootstrap pipe endpoint entries = 8
post-bootstrap holder-proof entries = 43
successful ready entries = 28
ipc_process_identity_count = 2
canonical boot identity query class/buffer/identity = 90 / 32 / 16
canonical boot identity stability reads/interval = 3 / 10 ms
TRIC/1 create intent = 3936 prefix + 160 trailer = 4096
IPC-authority intents per boot / attempts per intent = 64 / 2
IPC-authority complete records per intent / attempt bytes = 2 / 8192
IPC-authority retained boots / intent journals = 64 / 4096
IPC-authority records / attempt files = 8192 / 8192
IPC-authority attempt states / decision pairs = 9 / 81
IPC-authority maximum logical / invalid-tree scan bytes = 67108864 / 67108864
IPC-authority product-reachable partial files per boot / retained = 65 / 4160
IPC-authority product-reachable partial bytes per boot / retained = 270336 / 17301504
IPC-authority directory entries = 8256
TRIM/1 process table = 2 * 64 = 128
TRIM/1 mapping table = 4 * 128 = 512
TRIM/1 event table = 8 * 128 = 1024
TRIM/1 handle table = 24 * 64 = 1536
TRIM/1 control-handle table = 4 * 32 = 128
TRIM/1 inventory bytes = 128 + 512 + 1024 + 1536 + 128 = 3328
TRIM/1 record = 3936 prefix + 160 trailer = 4096
ready mapping/event masks = 0x00000006 / 0x00100002
ready peer-process/job masks = 0x00101000 / 0x0010000c
ready duplicate options / inheritance = 0 / false
ipc_owned_file_handle_count = 0
runtime slot states / packed bits = 12 / 4
predispatch census block / maximum vector = 1024 / 512
max_persistent_file_references_in_flight = 2 * 2 = 4
max_referenced_record_bytes_in_flight = 4 * 65536 = 262144
max_concurrent_ipc_incarnations = 1

TRAO/1 envelope = 3936 prefix + 160 trailer = 4096
maximum observation record = 4096 + 65536 = 69632
maximum session-unknown observation = 4096 + 4096 = 8192
session-unknown records reserved per alarm = 2 + 6 = 8
session-unknown bytes reserved per alarm
  = 2 * 65536 + 3 * 4096 + 3 * 8192
  = 167936
max session-unknown alarms per monitor incarnation
  = 1024 / 8
  = 128
max session-unknown alarm bytes per monitor incarnation
  = 128 * 167936
  = 21495808

known-session alarms per session/in flight = 32 / 4
known-session observation partition
  = 32 * (3*69632 + 3*8192) + 4096 overflow
  = 7475200 bytes / 193 records
non-alarm closure remainder = 26079232 bytes / 63 records

IPC recovery records = 2054 inventory + 2052 resolution + 2 control
  = 4108
IPC recovery reserve = 4108 * 2 * 4096 = 33652736
IPC recovery total attempt files = 8216
IPC recovery reachable partial-tail maximum
  = 4109 * 4096
  = 16830464 bytes / 4109 files

known-session alarm-root publication maximum = 32 * 2 * 65536 = 4194304
combined protected alarm-root bytes
  = 21495808 + 33652736 + 4194304
  = 59342848
combined reachable partial-tail allowance
  = 21495808 + 16830464 + 4194304
  = 42520576 bytes / 5197 partial files
combined total attempt-file allowance = 1024 + 8216 + 64 = 9304
```

The evidence, alarm and installation runtime roots have independent logical
quotas. Physical admission groups roots by the NTFS volume serial obtained from
their open handles. For each volume, TraceRelay sums every still-writable
root-domain reservation and every admitted session/operation reservation on
that volume, then adds `minimum_free_space_reserve_bytes` once. The same byte
cannot satisfy two reservations; the free-space reserve is not multiplied for
multiple roots on one volume. A different-volume root is evaluated in its own
group. Failure of any group blocks the creating operation before mutation.
Runtime-root admission reserves `runtime_root_reserved_quota_bytes` before the
first authority parent is created and retains that reservation while the
installation exists.

The mapping byte limit is committed shared memory. Referenced record bytes are
already-authoritative logical alarm-journal bytes, not an additional disk
allocation. A reference remains charged while its owning slot is pinned through
validation, observation/rejection/late-diagnostic commit, and ACK. Exact-
boundary admission succeeds; the next slot, unresolved reference, referenced
body byte, path byte, mapping byte, event object, or handle entry fails before
allocation or publication.

Old and replacement IPC incarnations are never allocated concurrently. Before
replacement allocation, the sealed `TRAR/1` inventory must exist, the old
processes, mappings, events, file handles, duplicated handles, and committed
mapping bytes must be proven released, every required resolution must be
durable, and `RECOVERY_COMPLETE` must commit. A failed proof or exhausted
two-attempt record blocks readiness and admits zero replacement objects.

Unless a field says otherwise, `bytes` means logical serialized file bytes,
not NTFS allocated size, and each maximum is inclusive. An operation whose
next complete record or response would make the aggregate exceed the maximum
is rejected before that record or response is started.

Session writer domains:

- `max_evidence_bytes_per_session` is the recursive aggregate of every logical
  file byte in the session directory: bundle manifest, embedded profile,
  embedded reason catalog, immutable bindings, service journal, monitor
  journal, alarm-publication observations including copied canonical
  persistent records, session alarm linkage, raw payload, committed framing,
  and every authoritative partial tail;
- `max_committed_records_per_session` is the aggregate count across all
  authoritative files inside the session directory;
- `max_partial_tail_bytes` is the aggregate uncommitted tail across all
  authoritative files, while `max_partial_tail_bytes_per_file` bounds each one;
- `max_authoritative_record_bytes` is per complete canonical record;
- session file-count, directory-entry, path-depth, and relative-path-byte
  bounds apply to the whole recursive bundle.

The verifier fields use the same domains. Therefore:

```text
verifier.max_input_bytes >= writer.max_evidence_bytes_per_session
verifier.max_committed_records >= writer.max_committed_records_per_session
verifier.max_partial_tail_bytes >= writer.max_partial_tail_bytes
verifier.max_input_files >= writer.max_session_bundle_files
verifier.max_directory_entries >= writer.max_session_directory_entries
verifier.max_path_depth >= writer.max_session_path_depth
verifier.max_relative_path_utf8_bytes >= writer.max_relative_path_utf8_bytes
```

The maximum legal failed bundle includes all immutable files, both journals,
alarm-publication observations, alarm linkage, the maximum aggregate committed
records, and the maximum aggregate tails; it remains inside all verifier
bounds. Allocated NTFS size is
reported diagnostically and governed by root free-space/quota admission, not
used to reinterpret logical evidence limits.

- active-session admission reserves the maximum session evidence budget and
  minimum free-space reserve;
- installation initialization reserves the complete runtime-root authority
  budget before parent-directory or attempt-file creation;
- same-volume evidence, alarm and runtime reservations are summed once by
  volume identity and are never double-counted or borrowed across domains;
- source reads and ordinary records stop before consuming the session closure
  byte or record reserve; only terminal, monitor-closure, alarm-link, and
  already-authorized outcome records may consume that reserve;
- release validation proves the reserve covers the maximum canonical closure
  sequence;
- approaching a session limit stops source reads before the limit, commits an
  incomplete reason when possible, and never forwards uncommitted bytes;
- approaching root quota rejects a new session;
- evidence and alarms are never auto-deleted;
- alarm IPC file references never create or delete a second body file; the
  referenced authoritative alarm journal remains subject to the existing
  no-automatic-deletion rule;
- a full alarm root makes readiness false or closes an active session
  incomplete; it never silently drops a required persistent alarm;
- ordinary diagnostic logs may rotate inside their declared bound because they
  are not authoritative evidence; evidence, alarm, and deletion-audit records
  do not rotate;
- an implementation resource not represented by a profile limit is unsupported
  until a user-confirmed profile revision adds a hard bound;
- profile boundary behavior is deterministic and testable.

### 14.3 Operational envelope

The complete v1 proposal is frozen in
`support-profile.windows-local-v1.json`. It is normative within this draft:
the implementation may perform better but may not narrow accepted values or
lengthen deadlines. User acceptance of the final requirement document remains
the separate final gate required for every draft; it is not an implementation
choice or an unresolved internal value.

Command-specific deadlines override the default control-request deadline only
for the named command. `control_deadlines_ms.stop_command_response` includes:

```text
drain_ms
+ terminal_commit_ms
+ alarm_initial_attempt_admission_deadline_ms
+ control_response_serialization_ms
```

and is at least that sum. `delete-submit` returns durable acceptance inside the
ordinary control deadline; `control_deadlines_ms.delete_completion` applies
asynchronously.

### 14.4 Reproducible performance protocol

Certification uses the reference host floor in the profile, AC power, no
debugger, release package, local loopback endpoints, and one ACTIVE session.
The exact host procedure is
`minimum_operational_envelope.host_certification_procedure`; the exact
same-volume storage-floor procedure is
`minimum_operational_envelope.storage_floor_benchmark`.

ETW collection in this section belongs only to the external release-
certification harness. It is not a production runtime mode, readiness
prerequisite, or reason to terminate an otherwise supported TraceRelay
session. Missing privilege, unavailable ETW, loss, or ambiguity makes that
certification run not-passed. Synthetic or simulated ETW events may test harness
parsing but cannot satisfy release certification.

Before every repetition, the harness:

1. freezes the in-scope process manifest by PID plus exact
   `PROCESS_CREATION_IDENTITY_FILETIME` and holds process handles through
   closure;
2. records one-second CPU samples using `GetSystemTimes`, `GetProcessTimes`,
   `GetActiveProcessorCount(ALL_PROCESSOR_GROUPS)`, and
   `QueryPerformanceCounter`;
3. records target-volume write bytes using Windows kernel ETW `DiskIo`
   `WriteTransfer` events; unknown or unattributed writes count as background;
4. runs the 60-second pre-run gate with no discarded interval;
5. runs the create-new, same-volume, 512 MiB warm-up plus 4 GiB measured,
   1 MiB aligned, queue-depth-one, `FILE_FLAG_NO_BUFFERING` storage benchmark;
6. calls `FlushFileBuffers` every 64 MiB, retains at least 64 samples, and uses
   nearest-rank p99 without interpolation or outlier removal.

Background CPU is host busy capacity minus the frozen in-scope process-time
equivalent, clamped only at zero. Background storage is every target-volume
write byte not attributed to an in-scope process identity. The gate remains
active from its pre-run interval through workload warm-up, measured workload,
and clean closure. Every complete one-second interval must satisfy both
profile maxima; no averaging across intervals is permitted. The storage floor
must satisfy both measured sequential throughput and durable-flush p99.

Raw counter samples, ETW events and aggregates, process/parent identities,
counter frequency, volume identity, OS build, power state, benchmark return
codes, and benchmark timestamps are retained. Missing data, a lost ETW event,
PID ambiguity, a gate excursion, wrong target volume/flags, insufficient
samples, or either storage-floor miss returns the stable
`TR-PERFORMANCE-HOST-GATE-FAILED` certification reason. No workload result is
accepted from an inadmissible host interval.

Both the sustained/burst protocol and the added-latency protocol run the
profile `performance_repetitions` times. Every repetition must pass.

Sustained throughput:

1. 60-second warm-up;
2. 900 measured seconds;
3. both directions active concurrently;
4. each direction offers one 4096-byte write exactly 128 times per second,
   producing 1 MiB/s aggregate;
5. each non-overlapping 10-second measured window must contain at least
   10 MiB of destination-harness received payload, and exact full payload and
   evidence reconstruction must succeed;
6. at measured second 300, each direction additionally offers 8 MiB in
   65536-byte writes; all 16 MiB must arrive within 30 seconds without weakening
   evidence or bounds.

Added latency is a separate workload:

1. one direct loopback baseline immediately precedes each relay run;
2. baseline and relay use the same processes, payload, affinity policy, and
   60-second warm-up;
3. for 600 measured seconds, each direction sends one 4096-byte framed test
   message 10 times per second concurrently;
4. the harness timestamps immediately before source write and immediately
   after exact receiver read using the same monotonic clock;
5. each direction therefore has at least 6000 samples per run;
6. percentile `p` is nearest-rank `sorted[ceil(p*n)-1]`, with no interpolation
   or outlier removal;
7. added percentile is
   `max(0, relay_percentile - direct_baseline_percentile)`;
8. p95 and p99 thresholds must pass independently for both directions in all
   three runs.

Any workload, environment, sample-count, window, or correctness violation
makes certification not-passed; a rerun does not erase retained failed
evidence.

### 14.5 Reproducible 24-hour soak

The session-duration anchor is committed `CONNECTION_ACTIVE`. The first steady
write occurs no later than the profile start-delay bound. The workload clock
starts at that first write and runs for exactly 86,400,000 monotonic
milliseconds, excluding final EOF and closure.

Each second, both directions concurrently send one 4096-byte write. Exactly 24
bursts occur at workload offsets `0, 3600, ..., 82800` seconds; each burst is
16 MiB total, split equally between directions, in 65536-byte writes, and must
complete within 30 seconds. The last steady write is scheduled strictly before
the 24-hour endpoint. After it completes, both peers issue EOF and the service,
monitor, and verifier complete clean closure inside the profile closure
deadline.

The maximum session duration is strictly greater than:

```text
soak_start_delay_ms
+ 86,400,000
+ soak_closure_deadline_ms
```

Equality loses to the session deadline. The workload has no injected fault;
fault soak remains a separate matrix. PASS requires exact per-direction byte
counts, clean terminal, matching monitor closure, bounded resources, and
offline verifier `PASS`.

## 15. Version and historical verification

Each session binds:

- journal schema major/minor;
- canonical serialization ID;
- digest suite and digest length;
- writer product version and source/package identity;
- exact support-profile bytes and SHA-256 digest;
- exact reason-catalog bytes, SHA-256 digest, and version;
- transport-profile version;
- service and monitor incarnation IDs.

The current v1 verifier shall verify every TraceRelay-produced `1.x` evidence
version. New minor versions are backward-readable. An incompatible major
version requires a new user-confirmed requirement and verifier. A verifier
encountering an unknown major version returns `INPUT_ERROR` with
`TR-INPUT-UNSUPPORTED-VERSION`; it never labels the evidence corrupt solely
because support is absent.

A reason-catalog version is immutable: different bytes may never reuse a
catalog version. The verifier validates the embedded catalog digest and
version against its supported compatibility asset before using catalog
priority, class, or meaning. A digest mismatch is evidence invalidity; an
unknown catalog major is unsupported input.

Before any future release can stop verifying a previously emitted version, it
must retain, outside deletable session directories:

1. the normative schema and canonical serialization specification;
2. digest and state-machine specifications;
3. independent golden vectors and mutation vectors;
4. a reproducibly attributable compatible verifier package.

The authority for one verification is the self-contained bundle plus the
verifier's supported compatibility assets, never a caller-selected profile.

## 16. Required machine-readable contracts

The release shall ship and validate:

1. support profile with all numeric limits and deadlines;
2. reason and exit-code catalog;
3. requirement-to-test traceability matrix;
4. schemas for bootstrap, control, journal, monitor, alarm, bundle manifest,
   profile, and verification report;
5. independent golden and mutation vectors.

Every requirement ID maps to at least one test or static inspection. Every
test maps back to at least one requirement. Missing mappings block the release.

The reason catalog also ships one exhaustive public-outcome trigger function.
Every public entry point, event, and release-certification result names the
complete allowed reason-ID set and an ordered rule for every allowed ID,
including start, readiness/status, application create/disable, registration
create, session inspect/revoke/close, graceful stop, alarm query/subscription,
alarm publication attempt, delete inspect/submit/status, transport hello,
performance certification, and control dispatch. Each reason freezes:

- success, accepted, running, failure, unknown, or terminal outcome class;
- domain and trigger predicate;
- numeric priority and ordering direction;
- introduced version and deprecation state.

A public result selector receives authorization result, validated request
shape, serialized pre-state, section 5.5 race winner, deadline/limit/fault
facts, operation-specific discriminator, and committed post-state. The catalog
itself is the machine-readable authority for:

- the predicate grammar;
- every required fact and its neutral token;
- every closed fact/token domain;
- absence and out-of-domain behavior;
- the complete operation set;
- result visibility;
- dispatch composition;
- each operation's normalization-failure reason.

Every fact is required; there are no optional facts in v1. The full Cartesian
product of the closed domains is an accepted selector input domain. A
state-inconsistent or contradictory tuple is therefore not delegated to a
future schema: it deterministically reaches a non-success rule. An absent fact
or token outside the catalog domain bypasses rule evaluation and selects the
operation's frozen normalization-failure reason. An unrecognized operation
selects `TR-CONTROL-UNSUPPORTED-COMMAND`.

For one operation, raw rules are evaluated by ascending `rule_order`. Every
`SUCCESS`, `ACCEPTED`, `RUNNING`, or `UNKNOWN` rule also carries one or more
complete nine-fact `positive_tuple_patterns`. One pattern contains every fact
key and a non-empty allowed-token array for that key. A vector matches only if
all nine values belong to the same pattern; values from separate patterns may
not be mixed. The patterns therefore freeze legal pre/post transitions,
operation discriminators, authorization/request state, race state, and neutral
values for every irrelevant fact.

A positive rule is eligible only when its raw predicate and one complete
pattern both match. A non-positive rule is eligible when its raw predicate
matches. The effective predicate of rule `n` is its eligible predicate and the
negation of every earlier eligible predicate. Effective predicates are
therefore mutually exclusive. The last rule is mandatory `otherwise`, making
the function exhaustive, and its reason must be non-success. No positive ID
may be selected by normalization failure or `otherwise`. A closed-domain
foreign discriminator, illegal pre/post pair, contradictory race, or
non-neutral irrelevant fact cannot match a positive pattern and therefore
reaches a non-success reason.

Every allowed reason ID appears in exactly one rule for that operation and
names a reachable fixture. A reason outside the catalog, outside the
operation's allowed set, absent from its rules, or selected by zero or multiple
effective predicates is schema-invalid.

Release validation applies the catalog `conformance_contract` directly; it
does not translate the selector into CNF or claim solver correspondence. The
layered grammar freezes conjunction precedence over disjunction. The eight-step
normative algorithm partitions unknown-operation, malformed fact-object,
out-of-domain, bounded-internal-failure, and closed-domain inputs, then performs
one ascending first-match traversal with immediate return. The mandatory final
non-positive `otherwise` gives totality; immediate first return gives
uniqueness; mandatory complete positive patterns prevent a positive result
outside its declared operation-valid tuples. These are selector construction
invariants, not conclusions delegated to a second representation.

The product evaluator and an independently authored oracle share no parser,
predicate evaluator, pattern matcher, selector loop, or normalization module.
Both bind exact catalog bytes/hash and must agree on the generated conformance
corpus. Every positive pattern is expanded into its complete Cartesian tuple
set in the catalog's frozen operation/rule/pattern/fact/token order. The
current exact baseline is 30 patterns and 58 unique legal tuples. Both
evaluators run every tuple, then every one-fact substitution of every expanded
tuple. The corpus also covers every fixture, pairwise raw-predicate overlap,
missing/duplicate/extra/out-of-domain fact, bounded internal failure, unknown
operation, dispatch composition, enumerated state/race/fault/limit/
discriminator, predicate-schema mutation, exact alarm-query
`QUERY_FILTER`/`QUERY_PAGE`/`CONTROL_RESPONSE_BYTES` limit vector, and deadline
boundary.

Every predicate fact identifier must be one required fact and every literal
must be in that fact's closed domain. Each clause and literal must have a
closed-domain reachability witness and a same-fact mutation witness; unknown
facts, out-of-domain literals, and syntactically valid but unreachable/dead
literals fail certification. Release validation independently reconstructs
the expansion, per-pattern counts, exact total, canonical corpus bytes, and
coverage set; a missing or duplicate tuple fails rather than being silently
deduplicated. Retained evidence includes both executable identities/hashes,
exact corpus bytes/hash/count, frozen expansion order, every per-pattern
count, independently recomputed coverage, per-case inputs/results,
construction-invariant results, raw exits/output, and failures. Missing
coverage, disagreement, timeout, or resource exhaustion fails certification.
Generic prose cannot replace a stable reason.

`control_dispatch` is a two-stage composition contract. A dispatch failure is
the request's one final public reason and no command selector runs.
`TR-CONTROL-DISPATCHED` is an internal committed event, never the API's final
response. After that event, exactly one command-specific `PUBLIC_RESPONSE`
reason is returned. Alarm publication is an internal event. Performance
certification is a release-certification result. Every other matrix operation
is a public response.

Authentication rules distinguish a non-final invalid attempt
(`TR-TRANSPORT-AUTH-FAILED`) from an invalid final permitted attempt
(`TR-TRANSPORT-AUTH-ATTEMPT-LIMIT`). Application disable is idempotent:
already-disabled selects `TR-CONTROL-APPLICATION-DISABLED`; v1 has no
application-enable command. Alarm query selects one of empty, final, or
truncated page reasons. `TR-INCOMPLETE-WORKER-TERMINATION-UNCONFIRMED` is
allowed only for transport activation, session close/revoke, application
disable, and service stop, the operations whose bounded worker isolation can
produce that fact. Deletion uses its separate `DELETE_UNKNOWN` contract.
Any missing, contradictory, out-of-domain, or product-owned bounded transport
failure selects `TR-TRANSPORT-INTERNAL`; it cannot fall through to
`TR-TRANSPORT-ACTIVATED`.
