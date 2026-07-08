# Consensus Engine

The consensus layer summarizes redundant synthetic sensors by zone.

## Inputs

- Neighboring synthetic sensors in the same zone
- Temporal persistence
- Reading agreement
- Outlier count
- Dropout count
- Signal and battery quality

## Outputs

- `sensorTrustScore`
- `zoneConsensusScore`
- `consensusLabel`

Labels include `CONSENSUS_STRONG`, `CONSENSUS_PARTIAL`, `CONSENSUS_WEAK`, and `SENSOR_CONFLICT_REVIEW_REQUIRED`.

Consensus is advisory context for reviewers. It does not authorize operational action.
