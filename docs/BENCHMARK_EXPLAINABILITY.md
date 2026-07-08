# Benchmark Explainability

The benchmark is synthetic-only.

## Scope

On deterministic synthetic benchmark data, SERS is compared against simple baselines.

## Compared Methods

- SERS/model
- Current-temperature threshold
- Rolling-average threshold

## Metrics

- Accuracy
- Precision
- Recall
- False positives
- False negatives
- Confusion matrix

## Strengths

SERS combines temperature, quality, consensus, door, and unresolved-pallet signals while keeping deterministic review facts unchanged.

## Known Failure Modes

- Synthetic labels may not match real vendor behavior.
- Low positive-label counts can make precision or recall uninformative.
- Sensor/vendor calibration is needed before pilots.

## Claims Boundary

No real-world superiority, production accuracy, pharma validation, or compliance certification is claimed.
