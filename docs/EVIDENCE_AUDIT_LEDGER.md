# Evidence Audit Ledger

Phase 16 exposes an audit-style synthetic evidence trail, not compliance certification.

- `/audit-ledger` renders the timeline.
- `/audit-ledger.json` returns the catalog and representative ledger.
- `/cases/<case-id>/audit-ledger.json` returns one deterministic case ledger.

The ledger is synthetic-only and advisory-only. It records evidence routes and human meaning without real timestamps, external services, GPU dependencies, or autonomous operational actions. Deterministic rules remain authoritative.
