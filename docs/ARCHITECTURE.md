# ColdChain Sentinel Architecture

ColdChain Sentinel is a stdlib Python app for a synthetic investor-grade cold-chain beta.

## Runtime Shape

- `src/serve_dashboard.py` owns HTTP routing and HTML/JSON rendering.
- `src/case_engine.py` owns deterministic case facts, rule trace, evidence, export, and audit packet generation.
- `src/sensor_engine.py` owns deterministic synthetic sensor generation, cleaning, consensus, SERS, prediction, and benchmark helpers.
- `src/ai_review_assistant.py` owns optional Fireworks calls, structured-output parsing, sanitization, and deterministic fallback.
- `fixtures/synthetic-cases.json` is the compact synthetic case source.

## Safety Boundary

Deterministic case facts are authoritative. Fireworks, SERS, and benchmark outputs are assistive only and cannot mutate final disposition, review status, blockers, pallet mapping, telemetry, trace facts, or `autonomousActionsAllowed`.

## Persistence Boundary

There is no database. Reviewer checklist and notes are browser `localStorage` only. Server routes generate deterministic responses from local synthetic fixtures and code.
