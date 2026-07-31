# TraceRelay design checkpoints

This directory stores versioned, reviewable design results inside the source
repository.

| Result | State | Entry point |
|---|---|---|
| Requirement design batch-028 | Independent review `PASS`; final user promotion pending | `requirements/batch-028/REQUIREMENT_DESIGN.md` |
| Implementation plan batch-010 | Historically user-confirmed against requirement batch-027; amendment required before implementation | `implementation-plan/batch-010/IMPLEMENTATION_PLAN.md` |

Read each directory's `STATUS.md` before using its contents. A copied document
does not change its authority state.

The requirement candidate and implementation plan deliberately remain separate:

- batch-028 closes `CPO-001` through private overlapped named pipes;
- batch-010 predates that change and does not yet contain the accepted
  `CPO-001`, `WA-001`, or `WA-002` resolutions;
- batch-011 must reconcile those decisions and pass its own frozen review and
  user-confirmation gates before implementation resumes.

