# ColdChain Sentinel Provider Addendums

Status: provider readiness and safety rules for the hackathon app.

## Fireworks AI Review Assistant

Status: optional, non-authoritative assistant.

- Credits received.
- API key must come only from `FIREWORKS_API_KEY`.
- Optional model override: `FIREWORKS_MODEL`.
- Default model: `accounts/fireworks/routers/kimi-k2p6-turbo`.
- Structured verification requires a real successful Fireworks API call with valid structured JSON.
- If structured output is unavailable, local deterministic sanitizer/extractor logic may show a bounded reviewer brief from provider text when it passes safety filters; otherwise deterministic fallback is shown.
- Fireworks may summarize and explain the deterministic review packet.
- Fireworks must not decide or alter `finalDisposition`, `reviewStatus`, `unresolvedPalletIds`, `autonomousActionsAllowed`, blocker logic, or source facts.
- Fireworks output is shown only as AI-assisted explanation.
- Fireworks must not approve, reject, release, quarantine, discard, reroute, notify customers, certify compliance, or make a production-ready decision.
- Missing key, timeout, rate limit, invalid response, low-quality text, or unsafe response must fall back to deterministic review.

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
