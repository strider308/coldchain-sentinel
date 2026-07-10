# Fault Universe Error Atlas

Phase 41 turns the 38 committed STBL synthetic fault prototypes and 19 weighted features into an inspectable atlas.

## Routes

- `/fault-atlas` and `/fault-atlas.json`
- `/fault-atlas/coverage.json`
- `/fault-atlas/{faultId}.json`

The atlas groups faults into thermal behavior, environmental exposure, handling events, sensor/device faults, network/gateway faults, data quality faults, identity/mapping faults, and mixed evidence. Each row summarizes the pattern, strongest prototype signals, first inspection target, common false positive, and linked evidence. Unknown fault identifiers return HTTP 404.

Coverage is limited to the project-defined synthetic fault universe. Detail payloads are advisory-only, preserve deterministic authority, and explicitly block release, quarantine, discard, reroute, and outbound messaging actions.
