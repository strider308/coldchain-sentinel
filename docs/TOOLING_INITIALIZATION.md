# ColdChain Sentinel — Tooling Initialization

Status: local-only tooling initialization.

## Rule

Tooling must not change product runtime behavior unless separately approved.

## CodeGraph / repo graph

Purpose:
- Local coding-agent navigation.
- Repository indexing.
- Safer implementation planning.
- Faster impact analysis.

Boundary:
- Local-only.
- Do not commit `.codegraph/`, `.gortex/`, `.repograph/`, or generated graph indexes.
- Do not expose graph output in the public app.
- Do not use graph output as product evidence.

## Required local tools now

| Tool | Purpose | Runtime dependency? | Commit artifacts? |
|---|---|---:|---:|
| Git | repo/version control | yes, developer only | no |
| Python | stdlib dashboard app | yes | no |
| Docker | container validation | yes, deployment build | no |
| Render CLI | optional deploy helper | no | no |
| CodeGraph / gortex | local repo graph/index | no | no |
| Gitleaks | secret scan | no | reports ignored |
| TruffleHog | secret scan | no | reports ignored |
| Playwright via npx | optional browser smoke | no | no |

## Planned but not installed into runtime today

| Tool/repo | Planned use | Adoption timing |
|---|---|---|
| Instructor | structured AI output validation | when AI output quality gates need stricter schemas |
| Langfuse | AI observability | only if quick and safe before demo; otherwise post-demo |
| LiteLLM | multi-provider routing | only if multiple model providers are active |
| Qdrant | policy/SOP retrieval | only if grounded retrieval becomes necessary |
| FastAPI + Pydantic | real API migration | post-demo architecture phase |
| DuckDB + Polars | local analytics / benchmark datasets | post-demo data phase |
| TimescaleDB | production time-series storage | post-demo, after license/ops review |
| Redpanda / Redpanda Connect / Benthos | streaming ingestion | after API/database architecture stabilizes |
| Bytewax | stream processing | later streaming experiments only |
| Great Expectations | data quality checks | after schemas stabilize |
| dbt Core | warehouse transforms | only after warehouse-style transforms exist |
| Feast | feature platform | only after real feature reuse exists |

## Current decision

For the current hackathon app:
- Keep runtime dependency surface small.
- Keep deterministic rules authoritative.
- Keep synthetic-only boundaries.
- Use local tools for safety, repo understanding, and validation.
