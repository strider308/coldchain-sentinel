# Root Cause and Inspection Recommendation Engine

Phase 36 combines STBL distilled predictions with existing synthetic scenario and evaluation routes. It answers three bounded questions:

1. What likely synthetic fault family best matches the evidence?
2. Which evidence supports or weakens that explanation?
3. What should a human inspect first?

## Outputs

Each supported case has an inspection plan and root-cause analysis. Plans include ranked alternatives, a primary target, timeline window, quality warnings, a checklist, reviewer questions, and blocked operational actions.

The engine is stateless. It uses no database, persistence layer, GPU, PyTorch, or external service.

## Routes

- `/inspection-engine`
- `/inspection-engine.json`
- `/cases/{case-id}/inspection-plan.json`
- `/cases/{case-id}/root-cause-analysis.json`

Fourteen expanded synthetic cases are supported. Unknown cases return HTTP 404.

## Safety boundary

The engine is synthetic-only and advisory-only. It does not determine operational disposition. Deterministic safety rules remain authoritative, and a human reviewer must interpret the evidence.
