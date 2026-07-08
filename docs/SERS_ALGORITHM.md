# SERS Algorithm

SERS means Sentinel Excursion Risk Score. It is an advisory synthetic beta score from 0 to 100.

## Inputs

- Distance to threshold
- Rolling temperature slope
- Consecutive above-threshold windows
- Sensor agreement
- Dropout and outlier penalties
- Door-open events
- Humidity movement
- Unresolved pallet penalty
- Evidence completeness

## Outputs

- `riskScore`
- `riskBand`: `LOW`, `WATCH`, `REVIEW`, or `CRITICAL`
- `topContributingFactors`
- `confidenceLabel`
- `modelVersion`

SERS does not change `finalDisposition`, `reviewStatus`, blockers, pallet mappings, rule trace facts, or `autonomousActionsAllowed`.

See `docs/SERS_MODEL_CARD.md` and `/sers-model-card` for intended use, prohibited use, and limitations.
