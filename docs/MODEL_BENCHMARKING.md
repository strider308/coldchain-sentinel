# Model Benchmarking

The benchmark uses generated synthetic windows only.

## Dataset

Rows are generated in memory from synthetic sensor windows. Features include rolling temperature, humidity, quality counts, consensus score, door-open count, and unresolved pallet count.

## Compared Methods

- Synthetic dependency-free classifier
- Current-temperature threshold baseline
- Rolling-average threshold baseline

## Claims Boundary

Benchmark wording is limited to deterministic synthetic benchmark data against simple baselines. No real-world superiority, production readiness, or compliance validation is claimed.
