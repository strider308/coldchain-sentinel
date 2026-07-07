# ColdChain Sentinel

A synthetic, containerized cold-chain demo that detects a deterministic temperature excursion, blocks unsafe final disposition, and produces a human review packet when pallet-zone mapping is incomplete.

## What It Does

ColdChain Sentinel loads a synthetic shipment fixture, applies deterministic cold-chain rules, shows a dashboard for the incident, and generates a human review packet. The baseline case includes a 45-minute high-temperature excursion, three mapped pallets, one unresolved pallet, and a blocked final disposition.

## Why It Matters

Cold-chain teams need a clear bridge from raw telemetry to review-ready evidence. This demo shows that consequential logistics decisions should expose missing evidence instead of hiding it behind an automated answer.

## Track Selected

Track 3 - Unicorn Track.

The demo is product/workflow oriented: it focuses on auditability, a clear market pain, a runnable app, containerization, and a safety-first review boundary.

## Demo Status

- Synthetic deterministic demo.
- Provider-disabled baseline.
- Human review required.
- Final disposition blocked.
- AMD and Fireworks are not used in the baseline.

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

## Local Run Instructions

Run the local dashboard:

```powershell
python projects/coldchain/src/serve_dashboard.py
```

Open:

```text
http://127.0.0.1:8080/
```

Run the deterministic baseline self-check:

```powershell
python projects/coldchain/src/coldchain_baseline.py
```

Run the dashboard and review packet self-check:

```powershell
python projects/coldchain/src/serve_dashboard.py --check
```

## Docker Build And Run

Build the image:

```powershell
docker build -t coldchain-sentinel:local projects/coldchain
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
docker compose -f projects/coldchain/docker-compose.yml up --build
```

Compose serves the app at:

```text
http://127.0.0.1:18080/
```

## Routes

- `/` - deterministic dashboard.
- `/review` - human review packet page.
- `/review.json` - deterministic review packet JSON.
- `/health` - provider-disabled health status.

## Review Packet Instructions

1. Start the app locally or in Docker.
2. Open `/review` for the human-readable packet.
3. Open `/review.json` for the deterministic machine-readable packet.
4. Confirm the packet shows the blocked disposition, human review requirement, `PAL-SYN-1004` unresolved mapping, and prohibited autonomous actions.

The review packet is generated from the synthetic fixture and deterministic rule output. It is not an approval, release decision, quarantine decision, discard decision, reroute decision, or customer notification.

## Test And Validation Commands

Run the deterministic validation suite:

```powershell
python projects/coldchain/tests/test_coldchain_validation.py
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

No AMD or Fireworks credentials are required for the deterministic container demo.

## Public Repo And Deployment Status

- Public GitHub repository: not created yet.
- Deployment/demo app URL: not created yet.
- Planned approach: clean export or fresh public repo from an approved source tree.
- Do not publish the full private planning history.
- Run Gitleaks and TruffleHog before public repo and deployment work.
- Keep `.codegraph/`, scanner output, local logs, build/cache folders, secrets, and internal-only artifacts out of public artifacts.

## Provider Status

- Fireworks: credits received, but technical integration remains unverified.
- AMD: credits not received.
- No AMD success is claimed.
- No Fireworks success is claimed.
- Any future provider use requires a provider addendum covering credentials, access, runtime/model behavior, cost/rate limits, logging, privacy, failure modes, fallback behavior, and demo-safe wording.
- Providers must remain optional and non-authoritative; deterministic rules remain the source of truth.

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
