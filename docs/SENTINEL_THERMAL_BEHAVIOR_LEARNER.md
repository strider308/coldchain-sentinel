# Sentinel Thermal Behavior Learner

Phase 35B exposes the offline STBL evidence through a stdlib-only runtime predictor.

## Runtime design

The live app reads three committed JSON artifacts. It calculates weighted centroid distance with the artifact feature weights, global standard deviations, fault prototypes, behavior mapping, and best rule-boost scale. The neural model is not executed by the app.

The runtime requires no GPU, PyTorch, notebook, external service, or real data. Missing or invalid artifacts produce an unavailable predictor state while deterministic fallback routes remain available.

## Evidence

- 171,000 total synthetic rows
- 38 synthetic fault prototypes
- 19 weighted features
- Neural synthetic fault accuracy: 95.51%
- Neural synthetic behavior accuracy: 99.52%
- Distilled synthetic fault accuracy: 77.25%
- Distilled synthetic behavior accuracy: 94.06%
- Method: `weighted-centroid-prototypes-plus-rule-boosts`

These values describe committed synthetic research evidence. They do not establish field performance or operational disposition.

## Routes

- `/behavior-predictor`
- `/behavior-predictor.json`
- `/behavior-predictor/model-card.json`
- `/behavior-predictor/training-artifact.json`
- `/behavior-predictor/distilled-rules.json`
- `/cases/{case-id}/behavior-prediction.json`

## Safety boundary

STBL is synthetic-only and advisory-only. Deterministic safety rules remain authoritative. Human review is required for operational interpretation, and no disposition or outbound message is executed.
