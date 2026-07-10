# UI/UX and Performance Hardening Audit

## Problem summary

The deployed Command Center was visually dense and slow despite a modest HTML body. It assembled the legacy synthetic dashboard, injected three more panels, and displayed a large route inventory above the fold. The root route used an earlier light visual system while the later evidence routes used separate dark inline styles.

## Audit health score

| Dimension | Before | After | Finding |
| --- | ---: | ---: | --- |
| Accessibility | 2/4 | 3/4 | Shared focus styling, 44px actions, and a skip link now cover the hardened surfaces. |
| Performance | 1/4 | 3/4 | Command Center HTML no longer runs synthetic simulation or benchmark assembly. |
| Responsive design | 3/4 | 3/4 | Existing responsive layouts remain; shared shell adds a single-column collapse. |
| Theming | 2/4 | 3/4 | Shared tokens now apply to the core demo and submission pages. |
| Anti-patterns | 2/4 | 3/4 | The Command Center route dump and nested panel injection were removed. |
| Total | 10/20 | 15/20 | Significant hardening completed. |

## Root cause findings

- `render_command_center_with_amd()` called the legacy `render_command_center()`, which called `command_center_payload()`.
- Every request regenerated synthetic readings, cleaning, consensus, SERS, and benchmark data. Profiling recorded about 8.5 million function calls and 6.6 seconds in a direct cold render profile.
- The old Command Center had 93 links, 13 articles, and 16 headings. It acted as a route directory rather than a demo home.
- Core later pages repeated near-identical inline dark CSS with different widths, radii, breakpoints, and typography. The root route retained a separate early light layout.

## Route size and slow path findings

The body sizes were already small. Response time and visible density were the actual defects.

| Route | Before median | Before bytes | Before links | After median | After bytes | After links |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | 1.79 ms | 7,586 | 18 | 0.91 ms | 6,001 | 15 |
| `/command-center` | 3,615.95 ms | 16,058 | 93 | 0.94 ms | 7,609 | 22 |
| `/command-center.json` | 3,604.12 ms | 14,289 | 0 | 1.40 ms warm | 14,814 | 0 |
| `/dashboard-strategy` | 2.26 ms | 11,450 | 52 | 2.09 ms | 15,876 | 58 |
| `/algorithm-console` | 127.13 ms | 7,029 | 11 | 101.64 ms | 11,455 | 17 |
| `/command-center-algorithm` | 129.19 ms | 7,225 | 22 | 105.33 ms | 11,651 | 28 |
| `/judge-pack` | 64.87 ms | 5,623 | 21 | 74.91 ms | 10,049 | 27 |
| `/final-route-manifest` | 1.83 ms | 3,229 | 4 | 1.19 ms | 7,655 | 10 |
| `/submission-readiness` | 70.96 ms | 3,584 | 4 | 68.31 ms | 8,010 | 10 |
| `/demo-script-final` | 0.98 ms | 6,237 | 3 | 1.27 ms | 10,663 | 9 |
| `/final-freeze` | 0.93 ms | 2,476 | 8 | 0.92 ms | 6,902 | 14 |

Measurements used seven local HTTP requests and the median result. The first cold `/command-center.json` request remains about 3.17 seconds because it preserves the full legacy compatible payload; subsequent requests use a stdlib in-process cache. The interactive `/command-center` HTML path is independent of that calculation and is fast from the first request.

## Visual consistency and mobile findings

- Existing contrast was strong and no external fonts, scripts, or assets were used.
- The old Command Center was especially difficult on mobile because its large toolbar became a long stack of buttons.
- The shared shell establishes one dark palette, 12px surface radius, 1120px maximum content width, 44px target height, visible focus states, and one mobile collapse at 720px.
- Shared navigation is Home, Command Center, Start Demo, Evidence, and Submission. The legacy base handler remains untouched for backward compatibility.

## Simplification decisions and changes made

- Added `ui_design_system_v2.py` with tokens, shared CSS, page shell, metric cards, safety badges, route buttons, escaping, and a decorator for compatible dark-route styling.
- Rebuilt the AMD Command Center directly instead of injecting panels into legacy HTML.
- Kept four primary actions, four metrics, four inspection cards, one safety panel, and six evidence links. The full route map remains available in JSON.
- Added additive `coherent-fast-v1` fields to `/command-center.json` and a static payload cache.
- Routed `/` through the same shell while keeping review, sensor, and data links as secondary actions.
- Applied the shared shell to dashboard strategy, algorithm evidence, judge pack, submission, manifest, demo script, final freeze, and command-center algorithm pages.

## Remaining risks

- The first full legacy-compatible Command Center JSON request still computes the historical synthetic summary. It is cached after that request. Replace it with a versioned committed summary only if cold JSON latency becomes a real API requirement.
- Some detailed evidence pages intentionally retain their dense content and local CSS for compatibility. They now receive the common shell, but a whole-app visual rewrite is outside this hardening patch.
- The final user-facing judgement remains manual after Render deployment.

## Live validation instructions

1. Deploy the latest `main` commit manually on Render.
2. Open `/`, `/command-center`, `/algorithm-console`, `/judge-pack`, `/submission-readiness`, and `/final-freeze` on desktop and at 390 by 844.
3. Confirm that `/command-center` shows the four primary actions, four metrics, four inspection cards, concise safety panel, and compact evidence map.
4. Confirm `/command-center.json` reports `uiVersion` as `coherent-fast-v1`, `simplifiedDashboard` as true, and `performanceOptimized` as true.
5. Confirm no page-level horizontal overflow, no external assets, and no change to the synthetic-only advisory boundary.
