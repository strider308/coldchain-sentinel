# Fireworks Advisory Explanation Layer

## Purpose

Phase 12 adds a product-facing Fireworks advisory explanation layer for ColdChain Sentinel. Fireworks is optional and used only to explain synthetic SERS review evidence for a human reviewer.

## Runtime Boundary

The app must continue to run when Fireworks is not configured. Missing API keys, HTTP errors, malformed output, unsafe output, or low-quality output must fall back to deterministic advisory text.

## Safety Controls

- Deterministic rules remain authoritative.
- SERS remains advisory-only.
- Fireworks cannot change risk bands or operational status.
- Fireworks cannot authorize operational decisions.
- Only compact synthetic context is sent.
- Unsafe or malformed output is rejected.
- No external service is required for the app to run.

## Routes

- `/fireworks-advisory`
- `/fireworks-advisory.json`
- `/fireworks-model-card`
- `/fireworks-model-card.json`
- `/cases/{caseId}/fireworks-advisory.json`

## Environment Variables

- `FIREWORKS_API_KEY`: optional. If absent, deterministic fallback is shown.
- `FIREWORKS_MODEL`: optional. If absent, the default router model is used.

Do not commit API keys, secrets, raw prompts containing private information, or model responses from real data.

## Claim Boundary

This phase does not claim regulated validation, real deployment validation, compliance signoff, operation-ready deployment, or any automated operational decisioning. The layer is synthetic-only and advisory-only.
