# End-to-End Case Walkthroughs

Phase 42 provides six narrative paths for judges: door-open warming, gateway delay, unresolved mapping risk, a single-sensor spike, multi-sensor confirmed warming, and mixed-quality evidence.

## Routes

- `/case-walkthroughs` and `/case-walkthroughs.json`
- `/case-walkthroughs/{caseId}` and `/case-walkthroughs/{caseId}.json`

Every walkthrough follows ten steps from raw synthetic signal through quality and consensus checks, SERS advisory context, STBL prediction, root-cause hypothesis, inspection priority, blocked actions, human review, and audit evidence. Existing behavior-predictor and inspection-engine logic supplies the prediction and plan summaries. Unknown identifiers return HTTP 404.

These are synthetic-only, advisory-only demonstration narratives. They do not change deterministic facts, recommend disposition, contact external parties, or make external validation claims.
