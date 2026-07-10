# Fireworks Multi-Case Advisory Coverage

Phase 18 exposes static coverage metadata at `/fireworks-coverage` and `/fireworks-coverage.json` for all six synthetic cases.

The coverage route reads `FIREWORKS_API_KEY` only to report whether a value is present, not whether it is valid, and reads `FIREWORKS_MODEL` to report the selected/default model. It never sends an external request. Each table link points to the existing single-case advisory route, where the safety gate and deterministic fallback apply.

Safety boundaries:

- Synthetic-only and advisory-only.
- Deterministic rules remain authoritative.
- Fireworks is optional; no key or external service is required to render coverage.
- No bulk external calls are made.
- Human review remains required; autonomous operational actions are disabled.

Run the focused check with:

```powershell
python -m pytest -p no:cacheprovider tests/test_fireworks_coverage_v2.py
```
