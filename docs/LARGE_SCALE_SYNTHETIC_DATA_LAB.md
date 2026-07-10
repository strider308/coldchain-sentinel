# Large-Scale Synthetic Data Lab

Phase 40 demonstrates the shapes and expected events of high-volume synthetic sensor streams without committing raw bulk data.

## Routes

- `/large-scale-data-lab` and `/large-scale-data-lab.json`
- `/large-scale-data-lab/profiles.json`
- `/large-scale-data-lab/throughput-summary.json`

The seven deterministic profiles include 10,000 and 100,000 readings, 171,000 STBL training windows, a one-million-reading simulation, multi-shipment and multi-zone streams, and a failure-heavy stream. Each profile exposes scale, sensor and shipment counts, expected quality events and fault families, a memory note, and an inspection route.

No large raw dataset is committed. The design notes describe bounded batches, partitioned consensus, aggregate counters, and the controls that future real ingestion would need. These profiles are synthetic design evidence, not measured deployment throughput.
