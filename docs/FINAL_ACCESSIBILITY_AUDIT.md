# Final Accessibility Audit

## Scope and qualification

This is a **WCAG 2.2 AA-oriented audit**, not a formal conformance statement. The criteria reference the official [W3C WCAG 2.2 Recommendation](https://www.w3.org/TR/WCAG22/). The audit covers the 17 primary HTML routes listed in `tests/test_final_accessibility_design_v2.py` plus the custom 404.

Available deterministic checks passed:

- `python -m pytest -p no:cacheprovider tests/test_final_accessibility_design_v2.py` -> **3 passed**, including duplicate-attribute parser coverage.
- Final repository pytest completed **173/173 passed**; the latest final-focused run completed **16/16 passed** and the unaffected UI regression group remained **9/9 passed**.
- All 18 representative rendered pages have the shared shell and required structural markers.
- Chrome captured the 10 required routes at 1440x1000, 1024x768, 768x1024, 390x844, and 320x800: **50/50 checks passed**, with no horizontal overflow, duplicate IDs, empty hrefs, or H1/main-count failures.

Axe, Lighthouse, and Pa11y were not installed and were not added to the application. Browser keyboard traversal, screen-reader testing, and 200%/400% zoom remain explicitly limited below.

| Status | Count |
|---|---:|
| PASS | 16 |
| PARTIAL | 5 |
| FAIL | 0 |
| N/A | 2 |
| NOT VERIFIED | 4 |

## WCAG-oriented evidence matrix

| Check | Status | Evidence | Limitation / remediation |
|---|---|---|---|
| Page language | PASS | All 18 parsed outputs use `html lang="en"` | None found. |
| Unique meaningful title | PASS | Exactly one title per output; detailed walkthrough now uses `Door-Open Warming` | Browser tab inspection remains manual. |
| One logical H1 | PASS | Exactly one H1 per parsed output | None found in the representative set. |
| Deeper heading sequence | NOT VERIFIED | H1 count is deterministic; all H2/H3 transitions were not semantically audited | Inspect heading outline with browser accessibility tooling. |
| Landmarks | PARTIAL | Exactly one main; shared primary/action navigation is labeled | Not every legacy-compatible detail page uses header/footer landmarks consistently. |
| Skip link | PASS | `href="#main-content"` and unique `main-content` appear on all 18 outputs | Browser focus movement should still be exercised manually. |
| Keyboard-operable semantics | PARTIAL | Navigation and actions use native anchors/buttons; no custom widget framework was introduced | Full route-by-route keyboard traversal was not performed. |
| Logical focus order / traps | NOT VERIFIED | Source order is linear and no focus-loop script was found in the shared shell | Requires browser keyboard traversal. |
| Visible focus | PASS | 3px accent outline with 3px offset covers links, buttons, and summaries | Accent/background contrast is 9.50:1. |
| Focus not obscured | PARTIAL | Main has scroll margin; skip link becomes visible at the top | Sticky/viewport interactions require browser confirmation. |
| Meaningful/non-empty links | PASS | Deterministic parser rejects empty hrefs across all representative outputs | Link-purpose nuance still benefits from manual review. |
| Duplicate IDs and attributes | PASS | Duplicate-attribute-aware parsing rejects repeated attributes; duplicate IDs are a blocking crawler finding; parsed ID lists are unique on all 18 outputs | Shared helper's duplicate `main-content` insertion was fixed. |
| Button/link semantics | PASS | Navigation is represented by anchors/nav; no state-changing UI is presented as a link | No destructive controls are present. |
| Image alternatives | N/A | Representative pages do not load meaningful image assets | Re-evaluate if images are later added. |
| Color not used alone | NOT VERIFIED | Safety states include text labels, not color-only badges | A complete visual state inventory was not performed. |
| Text contrast | PASS | Ink/background 17.50:1; muted/background 9.62:1; muted/surface 8.81:1; accent/background 9.50:1 | These calculated combinations exceed the 4.5:1 normal-text target. |
| Non-text contrast | PARTIAL | Focus indicator is strong; muted borders measure 1.73:1-1.89:1 | Browser review must identify borders that are required to perceive controls; those boundaries would need 3:1. |
| Readable spacing and line length | PASS | Body line-height 1.5; paragraphs capped at 72ch; balanced/pretty wrapping | User stylesheet text-spacing overrides were not tested. |
| 320px reflow implementation | PASS | Ten required routes were captured at 320x800; all reported exact viewport width and zero horizontal overflow | This is representative browser evidence, not a claim about every possible route or user stylesheet. |
| 390x844 behavior | PASS | Ten required routes were captured at 390x844 with zero horizontal overflow and valid structural counts | Keyboard/touch target interaction remains a separate manual check. |
| 200% and 400% zoom | NOT VERIFIED | Fluid max width and wrapping reduce known overflow risks | No browser zoom session was recorded. |
| Target size | PARTIAL | Shared navigation/buttons have `min-height:44px` | Ordinary inline text links do not guarantee a 44x44 box; overlap must be checked visually. |
| Reduced motion | PASS | `prefers-reduced-motion:reduce` shortens animation/transition duration and disables smooth scrolling | No required interaction depends on motion. |
| Unexpected movement / autoplay | N/A | No autoplay media or shared page-load choreography is present | Re-evaluate if media is embedded in the app. |
| Error and status messaging | PASS | Shared HTML 404 has explanatory copy and recovery; JSON 404 remains typed JSON | Client-side live-region behavior is not applicable to these server-rendered errors. |
| JSON/text route separation | PASS | Focused protocol tests verify HTML and JSON content types; JSON is not wrapped in the HTML shell | Maintain `respond_json()` and `respond_text()` separation. |
| External asset dependence | PASS | Representative parser finds no `http://`, `https://`, or protocol-relative asset URLs | All audited surfaces remain self-contained. |

## Route coverage

The following rendered outputs passed the structural test: `/`, `/command-center`, `/dashboard-strategy`, `/algorithm-console`, `/behavior-predictor`, `/inspection-engine`, `/judge-pack`, `/case-walkthroughs`, `/case-walkthroughs/door-open-warming`, `/fault-atlas`, `/large-scale-data-lab`, `/final-route-manifest`, `/submission-readiness`, `/demo-script-final`, `/judge-qna`, `/visual-polish`, `/final-freeze`, and the custom 404.

## Fixes already implemented

- Shared skip-link, main landmark, language, title, H1, focus, responsive, and reduced-motion requirements now cover all representative routes.
- Six previously uncovered renderers now use `@unified_page`.
- `apply_design_system()` no longer creates duplicate `main-content` IDs and no longer duplicates an existing legacy navigation.
- Buttons were added to the visible-focus selector.
- Long unbroken content can wrap, reducing narrow-screen overflow risk.
- The detailed walkthrough has a route-specific title.
- The custom HTML 404 is coherent and includes a Command Center recovery path.

## Findings and next checks

No accessibility blocker was verified in the deterministic or required-viewport browser checks. The main residual risks are non-text boundary contrast and the absence of keyboard, zoom, and assistive-technology evidence. Before the submission UI is frozen, manually verify:

1. Tab order, skip-link destination, visible focus, and absence of keyboard traps.
2. Keyboard/touch target overlap and focus behavior on the narrow layouts already shown to reflow without horizontal scrolling.
3. 200% and 400% zoom-oriented behavior.
4. Heading outlines and accessible names with browser accessibility tooling.
5. Whether any low-contrast border is necessary to perceive a control; strengthen only those boundaries.

These limitations prevent a formal WCAG conformance claim.
