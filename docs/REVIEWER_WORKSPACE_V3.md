# Reviewer Workspace v3

Phase 17 provides a static, deterministic reviewer queue for the six synthetic cases. It requires no database, GPU, external service, or persistent state.

Routes:

- `/reviewer-workspace`
- `/reviewer-workspace.json`
- `/reviewer-workspace/{caseId}.json`

Each case workspace includes its review status, priority, evidence tabs, incomplete checklist, suggested notes, blocked actions, allowed reviewer actions, and links to the existing audit ledger, incident replay, human review workbench, SERS, and optional Fireworks advisory evidence.

The workspace is synthetic-only and advisory-only. Inspection, annotation, and status changes are static workflow labels only; nothing is persisted or executed. Deterministic rules remain authoritative.
