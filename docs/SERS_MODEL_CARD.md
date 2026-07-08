# SERS Model Card v2

## Model

- Model name: Sentinel Excursion Risk Score
- Short name: SERS
- Version: `SERS-0.1-synthetic`
- Mode: deterministic synthetic beta only
- Horizon: 30 minutes

## Prediction Target

Advisory risk of near-future threshold breach or review escalation.

## Inputs

- Temperature distance to threshold
- Rolling temperature slope
- Rolling max/mean
- Humidity trend
- Door-open events
- Dropout, outlier, and duplicate counts
- Battery and signal quality
- Zone consensus score
- Unresolved pallet penalty
- Evidence completeness

## Outputs

- `riskScore`
- `riskBand`
- `confidenceLabel`
- `topContributingFactors`

## Intended Use

SERS helps reviewers prioritize inspection, understand why risk is rising, and add context to audit packets.

## Prohibited Use

SERS is not for autonomous release, quarantine, discard, reroute, or customer notification. It is not production validated or pharma/compliance certified.

## Limitations

SERS is trained and evaluated on synthetic data. Public or real data ingestion is deferred pending license/TOS/provenance review. Real sensor/vendor calibration is required before pilots.
