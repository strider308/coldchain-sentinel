# ColdChain Sentinel — Planned Tool Adoption Matrix

This matrix prevents accidental dependency bloat.

## Adopt now

### CodeGraph / gortex

Adoption type: local-only developer tool.

Use for:
- repo indexing
- coding-agent context
- impact analysis
- route/module discovery

Do not:
- commit graph artifacts
- make it a production dependency
- expose it in the app
- use it as validation evidence

### Docker

Adoption type: validation/deploy packaging.

Use for:
- local build validation
- Render-compatible deployment confidence

### Gitleaks / TruffleHog

Adoption type: local secret scanning.

Use for:
- pre-push checks
- worktree and history hygiene

## Adopt only if needed before demo

### Instructor

Use for:
- strict Fireworks output schemas
- rejecting malformed AI analysis

Adopt only when:
- current deterministic fallback is insufficient
- schema validation is needed beyond current guards

### Langfuse

Use for:
- AI trace observability
- prompt/version audit

Adopt only when:
- setup is fast
- no secrets are exposed
- no sensitive data is logged

### Qdrant

Use for:
- SOP/product-policy retrieval
- explainable grounded review context

Adopt only when:
- there is actual policy content to retrieve
- retrieval output remains advisory

## Do not adopt before demo

### FastAPI + Pydantic

Use later for:
- /api/v1/cases
- /api/v1/readings
- /api/v1/cleaning-reports
- /api/v1/consensus-reports
- /api/v1/predictions
- /api/v1/audit-packets

Reason to defer:
- current stdlib app is stable
- rewrite risk is too high before demo

### DuckDB + Polars

Use later for:
- benchmark analytics
- Parquet/CSV exports
- larger synthetic training runs

Reason to defer:
- not needed for current working routes

### TimescaleDB

Use later for:
- real sensor readings
- hypertables
- retention policies
- customer workspaces

Reason to defer:
- needs ops/license/security review

### Redpanda / Redpanda Connect / Benthos / Bytewax

Use later for:
- streaming ingestion
- MQTT-like adapters
- windowed aggregation

Reason to defer:
- streaming should come after stable API/database design

### Great Expectations / dbt Core / Feast

Use later for:
- data quality suites
- feature definitions
- training/inference parity

Reason to defer:
- schemas and product loops are still evolving

## Permanent safety constraints

- Synthetic-only until real dataset/license/provenance review passes.
- No autonomous release/quarantine/discard/reroute/customer notification.
- Deterministic rules remain authoritative.
- SERS remains advisory only.
- Fireworks remains optional and safety-gated.
- AMD claims remain limited to verified synthetic benchmark evidence.
