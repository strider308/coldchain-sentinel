# Final Route and Link Integrity Audit

- Base URL: `http://127.0.0.1:8092/`
- Completed UTC: `2026-07-11T12:59:59.060605+00:00`
- Crawl result: `PASS`
- Scope: bounded same-origin HTTP crawl plus static literal-route comparison.

## Summary

| Metric | Value |
| --- | --- |
| urlsRequested | 390 |
| htmlPagesCrawled | 106 |
| linkReferencesChecked | 1572 |
| uniqueInternalLinkTargets | 367 |
| brokenUrls | 0 |
| brokenLinkReferences | 0 |
| uncheckedLinkReferences | 0 |
| redirects | 0 |
| contentTypeIssues | 0 |
| fragmentIssues | 0 |
| duplicateLinkTargets | 206 |
| duplicateIds | 0 |
| externalLinksIgnored | 28 |
| manifestRoutes | 124 |
| staleRouteMapEntries | 0 |
| manifestRoutesMissingFromServer | 0 |
| serverRoutesNotRepresented | 39 |
| edgeStatusChecks | 30 |
| edgeStatusMismatches | 0 |
| blockingFindings | 0 |

## Broken or Unreachable URLs

None detected.

## Redirects

None detected.

## Content-Type Findings

None detected.

## Fragment Findings

None detected.

## Manifest Routes Missing from Literal Dispatch Inventory

None detected.

## Expected Error and Malformed-Path Checks

| Path | Expected | Actual | Content type | Pass |
| --- | --- | --- | --- | --- |
| /unknown | 404 | 404 | text/html | True |
| /unknown.json | 404 | 404 | application/json | True |
| /cases/unknown-case/behavior-prediction.json | 404 | 404 | application/json | True |
| /cases/unknown-case/inspection-plan.json | 404 | 404 | application/json | True |
| /fault-atlas/unknown-fault.json | 404 | 404 | application/json | True |
| /case-walkthroughs/unknown-case | 404 | 404 | text/html | True |
| /case-walkthroughs/unknown-case.json | 404 | 404 | application/json | True |
| /%2e%2e/ | 404 | 404 | text/html | True |
| /..%2f | 404 | 404 | text/html | True |
| /%3Cscript%3Ealert(1)%3C/script%3E | 404 | 404 | text/html | True |
| /a%0d%0aInjected-Header:test | 404 | 404 | text/html | True |
| //command-center | 404 | 404 | text/html | True |
| /COMMAND-CENTER | 404 | 404 | text/html | True |
| /command-center/ | 404 | 404 | text/html | True |
| /command-center?test=1 | 200 | 200 | text/html | True |
| /<9000 repeated characters> | 414 | 414 | text/html | True |
| /cases//blocked-unresolved-pallet | 404 | 404 | text/html | True |
| /cases/blocked-unresolved-pallet/review/ | 404 | 404 | text/html | True |
| /scenario-lab//door-open-warming.json | 404 | 404 | application/json | True |
| /cases//door-open-warming/fireworks-advisory.json | 404 | 404 | application/json | True |
| /case-walkthroughs//door-open-warming | 404 | 404 | text/html | True |
| /cases/unknown-case/risk-timeline.json | 404 | 404 | application/json | True |
| /cases/unknown-case/consensus-report.json | 404 | 404 | application/json | True |
| /cases/unknown-case/quality-events.json | 404 | 404 | application/json | True |
| /cases/unknown-case/raw-sensor-window.json | 404 | 404 | application/json | True |
| /cases/blocked-unresolved-pallet/sensor-window.json?offset=-1 | 400 | 400 | application/json | True |
| /cases/blocked-unresolved-pallet/sensor-window.json?limit=0 | 400 | 400 | application/json | True |
| /cases/blocked-unresolved-pallet/raw-sensor-window.json?offset=oops | 400 | 400 | application/json | True |
| /cases/blocked-unresolved-pallet/rejected-readings.json?limit=0 | 400 | 400 | application/json | True |
| /cases/unknown-case/root-cause-analysis.json | 404 | 404 | application/json | True |

## Literal Server Routes Not Represented by the Crawl or Manifests

- `/algorithm-console/prediction-table.json`
- `/algorithm-console/weaknesses.json`
- `/algorithm-insights.json`
- `/api/baseline`
- `/benchmark-refresh.json`
- `/beta-readiness`
- `/command-center-algorithm.json`
- `/command-center-strategy.json`
- `/data-pipeline.json`
- `/decision-simulator.json`
- `/demo-freeze.json`
- `/demo-navigation.json`
- `/demo-safe-mode.json`
- `/evaluation-matrix-v2.json`
- `/final-demo-checklist.json`
- `/index.html`
- `/integration-contract`
- `/integration-safety`
- `/judge-qna.json`
- `/live-qa-checklist.json`
- `/llm-advisory-eval.json`
- `/llm-advisory-eval/safety-cases.json`
- `/model-benchmark-v2.json`
- `/model-card`
- `/model-card.json`
- `/navigation-map.json`
- `/partner-api-contract/errors.json`
- `/partner-api-contract/sample-request.json`
- `/partner-api-contract/sample-response.json`
- `/policy-sandbox.json`
- `/policy-sandbox/mapping.json`
- `/policy-sandbox/sample-sop.md`
- `/review.json`
- `/screenshot-checklist.json`
- `/screenshot-worthy-dashboard.json`
- `/sensor-adapters.json`
- `/sensor-lab.json`
- `/submission-checklist.json`
- `/training-lab.json`

## Provider-safe crawl behavior

The crawler checked 13 provider-triggering links with HEAD. The final edge matrix contains 24 expected 404s, four expected 400s, one expected 414, and one expected 200; all 30 passed. Duplicate IDs are blocking findings, and none were found.

## Current live deployment check

The bounded crawl of the older Render deployment reached its 200-URL cap with six of 17 old-deployment edge mismatches. It remains **LIVE NO-GO** until the final commit is deployed and the generated validation script passes.

## Limitations

Dynamic dispatch is represented by literal `startswith` prefixes. Runtime-generated routes that have neither a literal route nor a literal prefix require manual review.
