# ColdChain Sentinel Provider Addendums

Status: provider readiness and safety rules for the hackathon app.

## Fireworks AI Review Assistant

Status: optional, non-authoritative assistant.

- Credits received.
- API key must come only from `FIREWORKS_API_KEY`.
- Optional model override: `FIREWORKS_MODEL`.
- Default model: `accounts/fireworks/models/deepseek-v3p1`.
- Verification requires a real successful Fireworks API call.
- No Fireworks success is claimed until a successful call is observed locally or on Render.
- Fireworks may summarize and explain the deterministic review packet.
- Fireworks must not decide or alter `finalDisposition`, `reviewStatus`, `unresolvedPalletIds`, `autonomousActionsAllowed`, blocker logic, or source facts.
- Fireworks output is shown only as AI-assisted explanation.
- Missing key, timeout, rate limit, or invalid response must fall back to deterministic review.

## AMD

Status: pending/not configured.

- Credits/access not received.
- No AMD runtime, acceleration, or success claim is made.
- AMD must not be claimed unless a later authorized verification succeeds.

## Safety Rules

- Deterministic rules remain authoritative.
- Synthetic demo data only.
- Human review required.
- Final disposition remains blocked for the baseline case.
- No autonomous release, quarantine, discard, reroute, or customer notification.
- Do not commit provider responses, secrets, logs, scanner output, env files, caches, or build artifacts.