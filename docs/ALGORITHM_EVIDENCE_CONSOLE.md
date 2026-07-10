# Algorithm Evidence Console

Phase 37 presents the committed STBL evidence as a judge-facing console. It reuses the Phase 35B predictor and Phase 36 inspection engine without duplicating inference logic.

## Evidence surfaces

- Offline training summary and synthetic metrics
- Weighted feature importance with inspection meaning
- Coverage of 38 project-defined synthetic fault families
- Predictions for 14 supported synthetic cases
- Weak fault classes and uncertainty patterns
- Explicit stdlib runtime and human-review boundary

The console exposes separate JSON routes for feature weights, error coverage, predictions, weaknesses, and runtime boundaries.

## Runtime boundary

Neural training happened offline. The live application loads committed JSON artifacts and uses distilled centroid rules. It does not load neural weights or require GPU, PyTorch, notebooks, databases, or external services.

The evidence is synthetic-only and advisory-only. It does not determine operational disposition, and deterministic safety rules remain authoritative.
