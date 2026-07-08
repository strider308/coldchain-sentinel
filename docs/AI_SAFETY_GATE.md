# AI Safety Gate

Fireworks is optional and non-authoritative.

## Flow

1. Try structured JSON output.
2. Validate required reviewer-brief fields.
3. If structured output fails, sanitize/extract safe text.
4. If quality or safety filters fail, show deterministic fallback.

## Guardrails

Provider output cannot alter deterministic facts, rule traces, pallet mappings, blockers, review status, final disposition, or `autonomousActionsAllowed`.

Raw chain-of-thought and raw provider responses are not committed or displayed as trusted output.
