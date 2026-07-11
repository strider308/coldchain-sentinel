# Final Debug and Performance Audit

## Executive result

**PASS for the performed local HTTP profile**, with one documented cold-path limitation. The 17-route profiler completed 20 warm samples per route and a 10-worker/50-request mixed-route smoke with zero errors. The Command Center meets the stated local targets. Browser Core Web Vitals, live Render timings, allocation tracing, and a long memory soak were not measured.

Evidence: `submission-work/final-audit/performance-audit-local.json` and `performance-audit-local.md`, generated against `http://127.0.0.1:8092` on 2026-07-11. The workspace evidence is intentionally excluded from the commit.

## Classification summary

| Class | Status | Evidence / decision |
|---|---|---|
| 17 primary route HTTP profile | PASS | All cold and 340 warm requests returned 200 with expected content types. |
| Command Center target | PASS | 45.675ms warm median, 61.257ms p95, 7,921 bytes. |
| Command Center JSON warm target | PASS | 46.791ms warm median, 62.316ms p95. |
| Command Center JSON cold path | PARTIAL | Clean-process first request was 3,496.965ms because the legacy-compatible synthetic summary is assembled once. |
| Response-size target | PASS | Command Center is 7,921 bytes, below 120KB; largest profiled HTML body was 17,686 bytes. |
| Route-density target | PASS | Command Center has 22 links, not the former 93-link route dump. |
| Bounded concurrency | PASS | 10 workers, 50 requests, 0 errors, all status 200; median 430.565ms, p95 755.082ms. |
| Static-route provider/GPU isolation | PASS | Static route sources do not import Torch; optional provider traffic is disabled by default and guarded separately. |
| Cache behavior | PASS | Static synthetic Command Center payload uses `lru_cache(maxsize=1)` and returns a defensive deep copy. |
| Cache headers | PARTIAL | Most detailed routes return `no-store`; root and Command Center responses have no cache directive. |
| Gzip | N/A | Profiler requested gzip; server did not compress. Bodies are 7-18KB, so no compression code was added without measured need. |
| cProfile/tracemalloc | NOT VERIFIED | Final HTTP profiler records timings/counts but not allocation or function-call profiles. |
| Client Core Web Vitals | NOT VERIFIED | No Lighthouse/browser performance run is available for this working tree. |
| Live Render performance | NOT VERIFIED | Must be measured after owner deployment; hosting cold start must remain separate from application compute. |
| Memory growth / long soak | NOT VERIFIED | The bounded concurrency check found no request errors but was not a memory soak. |

## Final local route measurements

| Route | Status | Bytes | Cold ms | Warm median ms | Warm p95 ms | Links |
|---|---:|---:|---:|---:|---:|---:|
| `/` | 200 | 6,313 | 47.697 | 45.644 | 65.469 | 15 |
| `/command-center` | 200 | 7,921 | 46.519 | 45.675 | 61.257 | 22 |
| `/command-center.json` | 200 | 14,814 | 3,496.965 | 46.791 | 62.316 | 0 |
| `/dashboard-strategy` | 200 | 16,170 | 56.264 | 48.227 | 64.893 | 58 |
| `/algorithm-console` | 200 | 11,749 | 155.678 | 153.512 | 175.474 | 17 |
| `/behavior-predictor` | 200 | 13,355 | 114.465 | 84.949 | 108.924 | 38 |
| `/inspection-engine` | 200 | 12,463 | 95.152 | 77.168 | 95.115 | 35 |
| `/judge-pack` | 200 | 10,343 | 108.438 | 112.151 | 139.957 | 27 |
| `/case-walkthroughs` | 200 | 9,166 | 67.757 | 65.407 | 86.938 | 17 |
| `/case-walkthroughs/door-open-warming` | 200 | 10,868 | 49.115 | 62.708 | 77.077 | 29 |
| `/fault-atlas` | 200 | 17,686 | 194.971 | 181.528 | 207.564 | 48 |
| `/large-scale-data-lab` | 200 | 10,994 | 33.676 | 46.542 | 61.860 | 17 |
| `/final-route-manifest` | 200 | 7,949 | 64.662 | 47.245 | 60.916 | 10 |
| `/submission-readiness` | 200 | 8,304 | 133.703 | 114.622 | 130.794 | 10 |
| `/demo-script-final` | 200 | 10,957 | 42.931 | 49.870 | 72.083 | 9 |
| `/judge-qna` | 200 | 10,957 | 47.343 | 54.783 | 62.356 | 9 |
| `/final-freeze` | 200 | 7,196 | 46.351 | 45.827 | 60.340 | 14 |

The slowest measured warm p95 values were `/fault-atlas` at 207.564ms and `/algorithm-console` at 175.474ms. No route failed the audit, and no evidence justified adding compression, a new cache layer, or a dependency.

## Before and final comparison

The earlier hardening report used seven local requests; the final profiler uses 20 warm samples, so values are directionally comparable but are not a controlled hardware benchmark.

| Route | Earlier median | Earlier bytes / links | Final result |
|---|---:|---|---|
| `/command-center` | 3,615.95ms | 16,058 / 93 | 45.675ms warm median; 7,921 bytes / 22 links |
| `/command-center.json` | 3,604.12ms | 14,289 / 0 | 3,496.965ms cold; 46.791ms warm median; 14,814 bytes |

The root cause was repeated legacy synthetic simulation and benchmark assembly on the interactive Command Center path. The current HTML renderer is independent of that work. The legacy-compatible JSON payload computes once and is cached.

## Debug and resource findings

- The server uses `ThreadingHTTPServer`; the bounded concurrency run returned 50/50 successful responses.
- `_cached_command_center_with_amd_json()` uses a one-entry stdlib cache; `command_center_with_amd_json()` deep-copies the cached payload so callers cannot mutate it.
- No `import torch` or `from torch` statement was found under `src/`.
- Static app boot does not require a provider, GPU, PyTorch, or an external asset.
- Optional provider calls use explicit timeouts, response-size bounds, an allowlisted model, an opt-in environment flag, a process lock, a five-minute cache, and a ten-second cooldown.
- Final validation passed: full 173/173, focused 16/16, compatibility 155/155, standalone, compileall, and both dashboard self-checks.
- No gzip or new caching abstraction was added because the measured response bodies are small and the primary latency target already passes.

## Remaining performance risks

1. `/command-center.json` retains a roughly 3.50-second first-request computation for historical payload compatibility. It is warm-fast and does not block the interactive HTML route. Replace it with a committed versioned summary only if cold JSON becomes a measured requirement.
2. The Fault Atlas is the slowest warm route in the final profile. Its 207.564ms p95 is observed, not evidence of a failure; re-profile before optimizing.
3. Browser rendering, LCP/INP/CLS, live Render cold start, memory growth, and detailed allocations remain unverified.

## Reproduction

Start the app locally, then run:

```powershell
python scripts/final_performance_audit.py --base-url http://127.0.0.1:8092 --warm-samples 20 --json-output submission-work/final-audit/performance-audit-local.json --markdown-output submission-work/final-audit/performance-audit-local.md
```

Do not interpret a future Render wake-up delay as application compute without separate warmed measurements.
