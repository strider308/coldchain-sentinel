# ColdChain Sentinel

A synthetic, containerized cold-chain demo that detects a deterministic temperature excursion, blocks unsafe final disposition, and produces a human review packet when pallet-zone mapping is incomplete.

## What It Does

ColdChain Sentinel loads a synthetic shipment fixture, applies deterministic cold-chain rules, shows a dashboard for the incident, and generates a human review packet. The baseline case includes a 45-minute high-temperature excursion, three mapped pallets, one unresolved pallet, and a blocked final disposition.

The beta app also includes a small static synthetic case workspace for reviewing multiple demo scenarios without uploads, databases, or real operational data.

The case workspace now includes a deterministic telemetry engine and rule trace so reviewers can see how synthetic readings become a review packet: telemetry, excursion detection, zone impact, pallet mapping, blockers, review status, and autonomous-action denial.

The beta now frames the product as a synthetic sensor intelligence platform: raw readings are normalized, cleaned, checked for redundancy, scored by an advisory Sentinel Excursion Risk Score, and benchmarked against simple synthetic baselines before any human-review packet is shown.

## Why It Matters

Cold-chain teams need a clear bridge from raw telemetry to review-ready evidence. This demo shows that consequential logistics decisions should expose missing evidence instead of hiding it behind an automated answer.

## Track Selected

Track 3 - Unicorn Track.

The demo is product/workflow oriented: it focuses on auditability, a clear market pain, a runnable app, containerization, and a safety-first review boundary.

## Demo Status

- Synthetic deterministic demo.
- Provider-disabled deterministic baseline.
- Optional Fireworks AI Review Assistant for non-authoritative reasoning/explanation.
- Human review required.
- Final disposition blocked.
- AMD is not used or claimed. Fireworks is optional, gated by deterministic validation and safety filters, and never controls disposition.

## Safety Boundaries

- Synthetic data only.
- Deterministic rules are authoritative.
- Final disposition blocked.
- Human review required.
- No autonomous release, quarantine, discard, reroute, or customer notification.
- Not a validated pharmaceutical, medical, or logistics compliance product.
- No production use or real-world compliance assurance is claimed.

## Baseline Case

- Synthetic shipment: `SYN-SHIP-2026-06-26-A`.
- Excursion window: `2026-06-26T10:30:00Z` to `2026-06-26T11:15:00Z`.
- Excursion duration: 45 minutes.
- Mapped pallets: `PAL-SYN-1001`, `PAL-SYN-1002`, `PAL-SYN-1003`.
- Unresolved pallet: `PAL-SYN-1004` because zone mapping is missing.
- Final disposition: `BLOCKED`.
- Human review: required.

## Synthetic Scenarios

- `blocked-unresolved-pallet` - temperature excursion with missing zone mapping for `PAL-SYN-1004`; blocked and human-review required.
- `excursion-fully-mapped` - temperature excursion with all pallets mapped; still human-review required and no autonomous action allowed.
- `no-excursion-control` - synthetic control with no excursion and no unresolved mapping; no real-world operational decision is made.

## Local Run Instructions

Run the local dashboard:

```powershell
python src/serve_dashboard.py
```

Open:

```text
http://127.0.0.1:8080/
```

Run the deterministic baseline self-check:

```powershell
python src/coldchain_baseline.py
```

Run the dashboard and review packet self-check:

```powershell
python src/serve_dashboard.py --check
```

## Docker Build And Run

Build the image:

```powershell
docker build -t coldchain-sentinel:local .
```

Run the container:

```powershell
docker run --rm -p 8080:8080 coldchain-sentinel:local
```

Open:

```text
http://127.0.0.1:8080/
```

## Docker Compose

Run with Compose:

```powershell
docker compose up --build
```

Compose serves the app at:

```text
http://127.0.0.1:18080/
```

## Routes

- `/` - deterministic dashboard.
- `/command-center` - complete platform overview for judges and investors.
- `/command-center.json` - machine-readable command center summary.
- `/cases` - synthetic case workspace.
- `/sensor-lab` - high-volume synthetic sensor aggregation UI.
- `/sensor-lab.json` - machine-readable sensor lab summaries.
- `/data-pipeline` - raw-to-review data pipeline explanation.
- `/data-pipeline.json` - machine-readable pipeline stages.
- `/model-benchmark` - synthetic benchmark report for advisory model output.
- `/model-benchmark.json` - benchmark metrics against simple baselines.
- `/public-data-readiness` - public dataset readiness gate; no datasets are ingested yet.
- `/cases/blocked-unresolved-pallet` - case detail page.
- `/cases/blocked-unresolved-pallet/review` - reviewer workspace.
- `/cases/blocked-unresolved-pallet/sensor-summary.json` - deterministic synthetic sensor aggregation summary.
- `/cases/blocked-unresolved-pallet/sensor-window.json?offset=0&limit=100` - capped synthetic sensor reading window.
- `/cases/blocked-unresolved-pallet/cleaning-report.json` - deterministic cleaning, duplicate, dropout, outlier, and signal-quality report.
- `/cases/blocked-unresolved-pallet/prediction.json` - advisory SERS/model prediction report; deterministic facts remain unchanged.
- `/cases/blocked-unresolved-pallet/trace.json` - deterministic rule trace JSON.
- `/cases/blocked-unresolved-pallet/evidence.json` - case evidence timeline JSON.
- `/cases/blocked-unresolved-pallet/export.md` - markdown export packet.
- `/cases/blocked-unresolved-pallet/audit.md` - audit-style markdown packet; local browser notes are not included.
- `/cases/blocked-unresolved-pallet/audit.md?simulateResolved=true` - simulated audit packet for local review packet completion.
- `/review` - human review packet page.
- `/review.json` - deterministic review packet JSON.
- `/ai-review` - optional Fireworks-assisted reviewer brief with structured, sanitized, or deterministic fallback output.
- `/ai-review.json` - AI review assistant JSON with unchanged deterministic result.
- `/health` - provider-disabled health status.
- `/beta-readiness` - synthetic beta capability status page.
- `/system-status.json` - machine-readable beta safety/status flags.
- `/validation-evidence` - non-secret local validation evidence page.

`/ai-review` and `/ai-review.json` accept an optional `caseId` query parameter for the synthetic cases, for example `/ai-review?caseId=excursion-fully-mapped`.

## Recommended Demo Flow

Start at `/command-center` for the full platform summary. From there, open `/sensor-lab`, `/data-pipeline`, `/model-benchmark`, `/cases/blocked-unresolved-pallet/review`, and `/ai-review` to inspect each layer.

## Current Beta Capabilities

- Synthetic telemetry timeline with threshold labels.
- Large deterministic synthetic sensor stream aggregation, defaulting to 24 sensors over 48 hours at 5-minute intervals.
- Complete beta total: 41,472 generated synthetic readings across three cases.
- Cleaning pipeline for duplicate readings, impossible values, dropout, drift, outliers, low battery, and weak signal.
- Redundancy consensus scoring by zone.
- Advisory Sentinel Excursion Risk Score (`SERS-0.1-synthetic`).
- Synthetic training dataset and dependency-free benchmark against simple baselines.
- Deterministic rule trace that does not depend on Fireworks.
- Reviewer workspace with local-only checklist and notes.
- Evidence, trace, review packet, and audit packet exports.
- Safe unknown-case page listing available synthetic case IDs.
- Platform Command Center that connects sensor telemetry, cleaning, consensus, SERS, benchmarks, deterministic review packets, Fireworks safety gates, and readiness checks.

## Deterministic Rule Trace

Each synthetic case includes local synthetic temperature readings. The app derives threshold breaches, excursion windows, affected zones, pallet mapping state, blockers, review status, and `autonomousActionsAllowed: false` without Fireworks or any external dataset.

Trace items include `ruleId`, rule name, status, input summary, output summary, evidence IDs, and safety impact. Example rule IDs include `TEMP_THRESHOLD_CHECK`, `EXCURSION_WINDOW_CALCULATION`, `ZONE_IMPACT_IDENTIFICATION`, `PALLET_MAPPING_CHECK`, `HUMAN_REVIEW_GATE`, and `AUTONOMOUS_ACTION_DENY`.

## Synthetic Sensor Lab

The sensor lab generates high-volume synthetic readings deterministically from compact local case configuration. The default demo scale is 24 sensors, 4 zones, 48 hours, and 5-minute readings, producing 13,824 synthetic readings per case and 41,472 generated synthetic readings across the three-case beta without committing a generated dataset file.

Aggregation functions calculate readings per sensor and zone, min/max/average temperature, above-threshold counts, consecutive excursion windows, dropout counts, outlier counts, noisy/rejected counts, impacted zones, mapped pallets, unresolved pallets, and evidence IDs. Quality labels include `SENSOR_OK`, `SENSOR_READING_ABOVE_THRESHOLD`, `SENSOR_DROPOUT`, `SENSOR_DRIFT_POSSIBLE`, `SENSOR_OUTLIER_REJECTED`, and `SENSOR_WINDOW_ESCALATED`.

The app does not ask reviewers to inspect every reading. It compresses high-volume synthetic telemetry into deterministic evidence, rule traces, and human-review packets. Sensor routes return summaries or capped windows; `/cases/{caseId}/sensor-window.json` defaults to 100 readings and caps `limit` at 500.

`/sensor-lab.json` and `/system-status.json` expose non-secret readiness flags including `realDataUsed: false`, `autonomousActionsAllowed: false`, and `fireworksAuthoritative: false`. `/beta-readiness` shows the judge-facing readiness checklist, and `/validation-evidence` lists local validation evidence without claiming live deployment status before smoke testing.

## Sensor Intelligence Pipeline

Synthetic readings include temperature, humidity, battery percentage, signal strength, door-open state, reading sequence, ingestion delay, and evidence ID. The cleaning layer normalizes fields, rejects duplicate readings and impossible values, and flags dropout, drift, outliers, low battery, and weak signal.

Zone redundancy consensus compares neighboring synthetic sensors, temporal persistence, reading agreement, outliers, dropouts, and signal/battery quality. It emits `sensorTrustScore`, `zoneConsensusScore`, and labels such as `CONSENSUS_STRONG`, `CONSENSUS_PARTIAL`, `CONSENSUS_WEAK`, and `SENSOR_CONFLICT_REVIEW_REQUIRED`.

SERS combines threshold distance, rolling excursion duration, sensor agreement, dropout/outlier penalties, door-open events, humidity movement, unresolved pallet mapping, and evidence completeness into an advisory 0-100 risk score. SERS does not change `finalDisposition`, `reviewStatus`, blockers, pallet mappings, rule trace facts, or `autonomousActionsAllowed`.

## Synthetic Model Benchmark

The benchmark creates an in-memory synthetic training dataset from generated sensor windows. Features include rolling temperature, humidity, quality counts, consensus score, door-open count, and unresolved pallet count. The simple dependency-free classifier is benchmarked only on deterministic synthetic data against a current-temperature threshold baseline and a rolling-average threshold baseline.

Benchmark wording is intentionally bounded: any measured comparison is only against simple baselines on deterministic synthetic benchmark data. No real-world superiority, production readiness, medical validation, or compliance validation is claimed.

## Public Data Readiness

`/public-data-readiness` lists candidate public cold-chain, IoT anomaly, and time-series datasets as not ingested. External data remains gated until license/TOS, schema compatibility, and provenance are verified.

## Local Review Session

The reviewer workspace stores checklist state and synthetic reviewer notes in browser `localStorage` only, keyed by case and simulation state. Notes are not uploaded and are not included in server-generated JSON or markdown except for a placeholder explaining that local notes stay in the browser.

The packet completeness meter uses demo-only labels: `DEMO_PACKET_INCOMPLETE`, `DEMO_PACKET_REVIEWING`, and `DEMO_PACKET_READY_FOR_HUMAN_REVIEW_ARCHIVE`. These labels are not regulatory, compliance, or operational statuses.

## Fireworks Role

Fireworks is optional and non-authoritative. Its output is structured, sanitized, or rejected behind safety gates; deterministic case facts, rule traces, dispositions, pallet mappings, and `autonomousActionsAllowed` are not changed by AI output.

## Review Packet Instructions

1. Start the app locally or in Docker.
2. Open `/review` for the human-readable packet.
3. Open `/review.json` for the deterministic machine-readable packet.
4. Confirm the packet shows the blocked disposition, human review requirement, `PAL-SYN-1004` unresolved mapping, and prohibited autonomous actions.

The review packet is generated from the synthetic fixture and deterministic rule output. It is not an operational decision, quarantine decision, discard decision, reroute decision, or customer notification.

## Test And Validation Commands

Run the deterministic validation suite:

```powershell
python tests/test_coldchain_validation.py
```

Run app self-checks:

```powershell
python src/coldchain_baseline.py
python src/ai_review_assistant.py
python src/serve_dashboard.py --check
```

Run JSON validation from the repo root:

```powershell
& ".\scripts\validation\validate-json.ps1"
```

Run whitespace validation:

```powershell
git diff --check
```

## Security Scan Commands

Run Gitleaks:

```powershell
gitleaks detect --source . --verbose --redact
```

Run TruffleHog filesystem scan:

```powershell
trufflehog filesystem . --no-update --fail
```

Do not commit scanner output, local logs, `.codegraph/`, secrets, build caches, or private-only artifacts.

## Container Validation Summary

Batch 5 validated the provider-disabled container path with:

- Docker build.
- Docker no-cache build.
- Docker run route smoke checks for `/`, `/review`, `/review.json`, and `/health`.
- Docker healthcheck healthy status.
- Docker Compose build/run health route check.

No AMD or Fireworks credentials are required for the deterministic container demo. Set `FIREWORKS_API_KEY` only when intentionally verifying the optional AI Review Assistant; `FIREWORKS_MODEL` is optional and defaults to `accounts/fireworks/routers/kimi-k2p6-turbo`.

## Public Repo And Deployment Status

- Public GitHub repository: https://github.com/strider308/coldchain-sentinel
- Deployment/demo app URL: https://coldchain-sentinel-35ex.onrender.com
- Planned approach: clean export or fresh public repo from an approved source tree.
- Do not publish the full private planning history.
- Run Gitleaks and TruffleHog before public repo and deployment work.
- Keep `.codegraph/`, scanner output, local logs, build/cache folders, secrets, and internal-only artifacts out of public artifacts.

## Live Demo

- Platform: Render.
- Public demo URL: https://coldchain-sentinel-35ex.onrender.com
- Public repository: https://github.com/strider308/coldchain-sentinel
- Status: live deterministic baseline. The Fireworks assistant is optional and must be smoke-tested after redeploy before any verification claim.

## Provider Status

- Fireworks: credits received; optional AI Review Assistant integration is non-authoritative. Structured output is verified when valid JSON matches the expected schema; otherwise the app shows sanitized provider text only when it passes local safety filters, or deterministic fallback.
- AMD: credits not received.
- No AMD success is claimed.
- Fireworks does not decide or alter final disposition.
- Deterministic rules remain authoritative when provider output is structured, sanitized, rejected, or unavailable.
- Any future provider use requires a provider addendum covering credentials, access, runtime/model behavior, cost/rate limits, logging, privacy, failure modes, fallback behavior, and demo-safe wording.
- Providers must remain optional and non-authoritative; deterministic rules remain the source of truth.

## Intentionally Not Included

- Real customer, patient, pharmaceutical, logistics, shipment, or sensor data.
- Authentication, database persistence, uploads, analytics, or background jobs.
- Operational approval, release, quarantine, discard, reroute, or customer-notification controls.
- AMD integration or AMD success claims.
- Production readiness, medical validation, pharmaceutical validation, or compliance certification.

## Submission Checklist

- [ ] Confirm dashboard/Discord deadline.
- [ ] Confirm final submission fields on lablab.ai.
- [ ] Create public GitHub repository from clean approved export.
- [ ] Add final README setup and usage instructions to public repo.
- [ ] Provide demo application URL/platform.
- [ ] Re-run container build and route smoke checks.
- [ ] Re-run Gitleaks and TruffleHog scans.
- [ ] Confirm no secrets, `.codegraph/`, scanner output, logs, or caches are included.
- [ ] Prepare cover image.
- [ ] Prepare slide presentation.
- [ ] Record video presentation.
- [ ] Fill title, short description, long description, and tags.
- [ ] Keep provider claims disabled unless addendum evidence exists.
- [ ] Keep safety wording visible in README, app, slides, and video.
