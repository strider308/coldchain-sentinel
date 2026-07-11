# Final AI Provider Security Audit

Audit date: 2026-07-11
Audited baseline: `f97e58c1527c7b5f015ab2bec7930ff639ff9ad8` plus the final provider-hardening working tree
Scope: `src/fireworks_runtime_guard.py`, `src/ai_review_assistant.py`, `src/fireworks_advisory_v2.py`, and their HTTP route wiring

This report evaluates the optional Fireworks explanation layer. It is a source-based security hardening audit, not a certification. No paid provider request was made for this report.

## Executive result

The HTTP runtime is default-off for Fireworks calls and always has a deterministic fallback. The endpoint is fixed, the model is allowlisted, inputs are fixed synthetic summaries, tokens/time/response bytes/attempts are bounded, results are schema/content gated, HTML output is escaped, HEAD cannot spend credits, and provider output cannot modify deterministic risk or disposition. The main command center does not call Fireworks.

No Critical, High, or Medium provider finding was identified in source review. One Low residual remains only when live calls are deliberately enabled: rate/caching controls are process-local. Redirect destinations are not explicitly host-denied, but the Authorization header is now an unredirected header and cannot be copied by urllib to a redirect target.

## Runtime call paths

| Public surface | Provider behavior | Status |
|---|---|---|
| `/command-center` and `/command-center.json` | Builds deterministic/catalog summaries only; no guarded live provider function is called. | PASS |
| `/ai-review` and `/ai-review.json` | `build_runtime_ai_review()` invokes the common guard for GET; HEAD returns deterministic fallback. | PASS |
| `/cases/{id}/fireworks-advisory.json` | Exact three-segment route calls `get_runtime_case_fireworks_advisory_payload()` for GET; HEAD returns deterministic fallback. | PASS |
| App import/boot | Imports functions/constants only; no network request occurs. The base self-check explicitly renders with provider access disabled, and normal/read-only Docker boots passed without provider configuration. | PASS |

## Mandatory control checklist

| Requirement | Status | Evidence |
|---|---|---|
| App boots without Fireworks | PASS | Missing key and disabled live flag return deterministic fallback; local self-checks and the final container boots passed without provider configuration. |
| Explicit live enablement | PASS | `FIREWORKS_LIVE_ENABLED` must be one of `1/true/yes/on`; otherwise `guarded_provider_result()` stops before the call. |
| API key handling | PASS | Key is read from `FIREWORKS_API_KEY` only when a call is attempted and used only in the Authorization header. Responses expose configured/succeeded booleans, not key material. |
| Fixed endpoint | PASS | Both integrations use the fixed HTTPS Fireworks chat-completions URL; no route/query/environment value can replace it. |
| Allowlisted model | PASS | `ALLOWED_MODELS` contains only the declared default; `selected_model()` falls back if `FIREWORKS_MODEL` is not in that tuple. |
| Fixed/bounded prompt input | PASS | Prompts use compact fields from allowlisted synthetic cases. There is no arbitrary user prompt, URL, uploaded document, retrieval store, or tool result. |
| Bounded timeout | PASS | Reviewer brief: 12 seconds per attempt. Advisory: 45 seconds for its one attempt. |
| Bounded output tokens | PASS | Reviewer brief requests 350 tokens; advisory requests 700 tokens. |
| Bounded response bytes | PASS | `read_bounded_json()` reads at most 65,537 bytes and rejects anything over 65,536 bytes. |
| Bounded attempts | PASS | Runtime reviewer brief caps structured attempts at two; advisory makes one request; there is no recursive retry loop. |
| Schema validation | PASS | Exact required keys, strict string/list element types, item counts, text lengths, and quality checks are enforced before display. Values of the wrong provider type are rejected rather than coerced. |
| Unsafe-text rejection | PASS | A shared order-insensitive operational-language guard scans every structured and unstructured displayed field; malformed empty, repeated, fragment-like, or unsafe content falls back deterministically. |
| Safe output rendering | PASS | Provider-derived text is rendered through `html.escape`; raw/unstructured provider output is never returned for display. |
| Deterministic fallback | PASS | Both provider paths produce a deterministic brief/advisory for disabled, missing-key, cooldown, HTTP, timeout, size, parse, schema, and safety-gate failures. |
| Deterministic boundary | PASS | `build_ai_review()` snapshots/asserts the deterministic result; advisory snapshots/asserts context; returned provider content is in a separate explanation object and cannot authorize an action. |
| No operational tools | PASS | There is no shipment, quarantine, discard, reroute, notification, filesystem, shell, browser, or other action tool exposed to the model. |
| Cost-abuse controls | PASS | Default-off flag, a process-wide single-flight lock, 10-second cooldown, five-minute cache keyed by fixed synthetic input, bounded attempts, and fallback limit spend. |
| Error secrecy | PASS | Public error status contains HTTP status/reason or exception class only. Provider bodies and Authorization values are not returned or logged; Authorization is set with `add_unredirected_header()` so urllib does not forward it to a redirect target. |

## Cost-abuse analysis

`guarded_provider_result()` holds one process-wide lock through cache lookup and the provider call. Concurrent identical or different public requests therefore cannot create parallel provider calls in one process. A successful or deterministic provider result is cached for five minutes; uncached calls are separated by a ten-second cooldown. Cache keys are derived from allowlisted case IDs or deterministic compact packets, so anonymous users cannot generate an unbounded key space through prompt text.

| Abuse case | Status | Evidence / limit |
|---|---|---|
| Repeated requests with default deployment | PASS | No spend: live calls are disabled unless the server owner explicitly enables them. |
| Concurrent duplicate calls | PASS | Process-wide lock and cache provide single-flight behavior. |
| Anonymous varying prompts | NA | No prompt endpoint exists. |
| Anonymous varying models/URLs | PASS | Model and endpoint are not client-controlled. |
| Retry amplification | PASS | Two reviewer attempts only, each triggered by HTTP error; advisory has one attempt. |
| HEAD amplification | PASS | HEAD routes return fallback without calling the provider. |
| Multi-instance deployment | PARTIAL | Limits and cache are process-local. Each enabled instance has its own budget window. A shared quota store would be needed only if paid live traffic is enabled across multiple instances. |
| Stale result | PASS | Cache lifetime is five minutes and applies only to fixed synthetic evidence; deterministic facts remain authoritative. |
| Cache poisoning | PASS | Keys and values originate from fixed synthetic catalogs; values are deep-copied on storage/return. No client-supplied prompt or provider URL affects the key. |

## OWASP Top 10 for LLM and GenAI Applications 2025

Framework reference: [OWASP Top 10 for LLM and GenAI Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf).

| Category | Status | Evidence / rationale |
|---|---|---|
| LLM01 Prompt Injection | PASS | The public user cannot supply instructions. Provider prompts contain fixed instructions and allowlisted synthetic fields only; outputs are treated as untrusted data. |
| LLM02 Sensitive Information Disclosure | PASS | Prompts contain no key, environment dump, customer record, real shipment, patient, or owner data. The API key is transport authorization only. |
| LLM03 Supply Chain | PARTIAL | The model identifier and endpoint are fixed, and output is untrusted/gated. Provider/model provenance and upstream platform controls are external and not independently verified. |
| LLM04 Data and Model Poisoning | NA | The app does not train, fine-tune, retrieve, embed, or write model data at runtime. |
| LLM05 Improper Output Handling | PASS | Size, JSON shape, field count/type, text length, unsafe phrases, quality, and HTML escaping are enforced before display. |
| LLM06 Excessive Agency | PASS | The model has no tools and cannot modify deterministic outputs or initiate operational actions. |
| LLM07 System Prompt Leakage | NA | The system prompt is not a secret control and is already visible in this public source repository; no sensitive value is placed in it. |
| LLM08 Vector and Embedding Weaknesses | NA | No vector database, embeddings, or retrieval-augmented generation exists. |
| LLM09 Misinformation | PASS | Output is labeled optional/advisory, constrained to supplied evidence, subject to quality/safety gates, and separated from authoritative deterministic facts. Human review remains required. |
| LLM10 Unbounded Consumption | PASS | Default-off execution, finite cases, tokens, response bytes, timeouts, attempts, lock, cooldown, cache, and fallback bound consumption in one process. Multi-instance limits remain PARTIAL as noted above. |

## External API consumption

| Item | Status | Evidence / limitation |
|---|---|---|
| TLS endpoint | PASS | Fixed `https://api.fireworks.ai/...` URL. |
| User-controlled SSRF | PASS | No user-supplied URL or host reaches `urlopen`. |
| Response trust | PASS | Provider response is bounded, parsed as a JSON object, then schema/content validated. |
| Redirect destination policy | PASS | The request starts at the fixed provider HTTPS URL, and Authorization is an unredirected header that urllib does not copy to a redirect destination. A future explicit redirect-host denial would be additional hardening, not a credential-forwarding requirement. |
| Provider outage | PASS | Network/provider failure produces deterministic fallback rather than a boot failure or decision change. |

## Validation and remaining verification

- Final repository pytest completed **173/173 passed**, including the latest **16/16** final-focused group. Coverage proves default-off behavior even when a key is present, HEAD isolation, fixed-model fallback, two-attempt runtime cap, oversized and malformed-empty response rejection, redirect credential isolation, strict provider types, shared order-insensitive operational-language rejection, deterministic fallback, and an unchanged `autonomousActionsAllowed: false` boundary.
- The route crawler checked 13 provider-triggering links with HEAD, proving reachability without entering a paid-call path.
- The base self-check explicitly disables runtime provider access.
- Cooldown/cache behavior and multi-process quota coordination were reviewed in source; a paid concurrent-provider exercise was intentionally not run.
- `NOT VERIFIED`: the newly deployed Render environment keeps `FIREWORKS_LIVE_ENABLED` unset/false unless the owner deliberately accepts paid-call exposure.
- No paid live call is required for this audit.
