# Cleaning Pipeline

The cleaning layer is deterministic and dependency-free.

## Steps

1. Normalize readings to the local schema.
2. Validate required values.
3. Reject duplicate readings.
4. Reject impossible temperature values.
5. Flag dropout, drift, outlier, low-battery, and weak-signal conditions.
6. Preserve accepted and rejected counts plus rejection reasons.

## Labels

- `CLEAN_ACCEPTED`
- `REJECTED_DUPLICATE`
- `REJECTED_IMPOSSIBLE_VALUE`
- `FLAGGED_DROPOUT`
- `FLAGGED_DRIFT`
- `FLAGGED_OUTLIER`
- `FLAGGED_LOW_BATTERY`
- `FLAGGED_WEAK_SIGNAL`

Cleaning reports do not alter deterministic review facts.
