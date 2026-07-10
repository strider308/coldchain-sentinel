# Ops Readiness and Evidence Health

Phase 19 adds a static, synthetic-only view of demo evidence availability. It is evidence health only, not production monitoring.

The `/ops-readiness` page and `/ops-readiness.json` payload summarize locally built evidence from the GPU research artifact, optional Fireworks configuration, demo console, validation packet, integration sandbox, audit ledger, reviewer workspace, and scenario lab. `/evidence-health.json` serves the same payload.

Route rows describe expected static availability; the payload builder does not probe the app, open sockets, or contact external services. Fireworks remains optional, its fallback remains available, and neither GPU nor an external service is required to boot the app.

All evidence is synthetic and advisory. Deterministic rules remain authoritative, and any operational use requires human review.
