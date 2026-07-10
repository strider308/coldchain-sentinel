from __future__ import annotations

import html
from typing import Any
from ui_design_system_v2 import unified_page

PHASE = "Phase 43 - Final Route Manifest and Live QA Sweep"
LIVE_COMMIT = "510e909e2330b887ced0ff7061a5b9f465472499"

ROUTE_GROUPS = {
    "command center and dashboard": ["/command-center", "/command-center.json", "/dashboard-strategy", "/dashboard-strategy.json"],
    "judge evidence": ["/judge-pack", "/judge-pack.json", "/judge-pack/demo-script.json", "/judge-pack/technical-proof.json", "/judge-pack/claims-boundary.json"],
    "algorithm and STBL": ["/algorithm-console", "/algorithm-console.json", "/behavior-predictor", "/behavior-predictor.json", "/command-center-algorithm"],
    "inspection and root cause": ["/inspection-engine", "/inspection-engine.json", "/cases/door-open-warming/inspection-plan.json", "/cases/door-open-warming/root-cause-analysis.json"],
    "case walkthroughs": ["/case-walkthroughs", "/case-walkthroughs.json", "/case-walkthroughs/door-open-warming", "/case-walkthroughs/door-open-warming.json"],
    "fault atlas": ["/fault-atlas", "/fault-atlas.json", "/fault-atlas/coverage.json", "/fault-atlas/door_open_warming.json"],
    "large-scale data": ["/large-scale-data-lab", "/large-scale-data-lab.json", "/large-scale-data-lab/profiles.json", "/large-scale-data-lab/throughput-summary.json"],
    "demo flow": ["/demo-flow", "/demo-flow.json", "/demo-navigation", "/demo-freeze"],
    "validation evidence": ["/final-validation", "/final-validation.json", "/route-reliability", "/route-reliability.json"],
    "integration and partner readiness": ["/partner-api-contract", "/partner-api-contract.json", "/integration-sandbox", "/integration-sandbox.json"],
    "ops and gap analysis": ["/ops-readiness", "/ops-readiness.json", "/production-gap-analysis", "/production-gap-analysis.json"],
    "freeze and submission": ["/final-route-manifest", "/submission-readiness", "/demo-script-final", "/visual-polish", "/final-freeze"],
}

EXPECTED_404 = [
    "/fault-atlas/unknown-fault.json", "/case-walkthroughs/unknown-case",
    "/case-walkthroughs/unknown-case.json", "/cases/unknown-case/behavior-prediction.json",
    "/cases/unknown-case/inspection-plan.json", "/cases/unknown-case/root-cause-analysis.json",
]


def _safety() -> dict[str, bool]:
    return {"syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False, "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False, "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True, "databaseRequired": False, "persistenceEnabled": False, "dependenciesAdded": False, "externalCallsRequired": False}


def get_final_route_manifest_payload() -> dict[str, Any]:
    routes = [{"route": route, "expectedStatus": 200, "contentType": "application/json" if route.endswith(".json") else "text/html", "group": group, "whyItMatters": f"Confirms {group} evidence remains available."} for group, items in ROUTE_GROUPS.items() for route in items]
    return {"phase": PHASE, "status": "READY", **_safety(), "latestKnownLiveCommit": LIVE_COMMIT, "routeGroups": list(ROUTE_GROUPS), "requiredRoutes": routes, "expected404Routes": list(EXPECTED_404), "safetyFlagChecks": [{"route": route, "checks": ["syntheticOnly true", "advisoryOnly true", "runtimeGpuRequired false", "runtimeExternalServiceRequired false", "runtimePyTorchRequired false", "autonomousActionsAllowed false", "deterministicRulesAuthoritative true"]} for route in ("/final-route-manifest.json", "/submission-readiness.json", "/demo-script-final.json", "/visual-polish.json", "/final-freeze.json")], "ownerLiveValidationInstructions": ["Deploy latest main manually.", "Run the PowerShell live validation script.", "Review mobile layouts and claims boundary.", "Record owner signoff only after every check passes."], "routeMap": {"finalRouteManifest": "/final-route-manifest", "liveQaChecklist": "/live-qa-checklist", "liveValidationScript": "/live-validation-script.ps1", "submissionReadiness": "/submission-readiness", "finalFreeze": "/final-freeze"}}


def get_live_qa_checklist_payload() -> dict[str, Any]:
    sections = ["deploy latest main", "confirm route availability", "confirm JSON safety flags", "confirm expected 404 behavior", "confirm mobile layout", "confirm command-center links", "confirm no external assets", "confirm final freeze status", "confirm claims boundary"]
    return {"phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True, "checklistSections": [{"section": item, "ownerConfirmationRequired": True} for item in sections], "passCriteria": ["all required routes return expected status", "all core safety flags match", "mobile pages have no page overflow", "freeze remains an owner decision"], "noGoCriteria": ["required route failure", "safety flag mismatch", "unexpected external asset", "missing claims boundary", "freeze shown active before owner signoff"], "ownerSignoffRequired": True}


def get_live_validation_script() -> str:
    routes = "\n".join(f'  "{item}"' for item in [row for rows in ROUTE_GROUPS.values() for row in rows])
    missing = "\n".join(f'  "{item}"' for item in EXPECTED_404)
    return f'''$ErrorActionPreference = "Stop"
$base = "https://coldchain-sentinel-35ex.onrender.com"
$okRoutes = @(
{routes}
)
$notFoundRoutes = @(
{missing}
)
foreach ($route in $okRoutes) {{
  $response = Invoke-WebRequest -UseBasicParsing -Uri ($base + $route)
  if ($response.StatusCode -ne 200) {{ throw "$route returned $($response.StatusCode)" }}
}}
foreach ($route in $notFoundRoutes) {{
  try {{ Invoke-WebRequest -UseBasicParsing -Uri ($base + $route) -ErrorAction Stop | Out-Null; throw "$route did not return 404" }}
  catch {{ if ($_.Exception.Response.StatusCode.value__ -ne 404) {{ throw }} }}
}}
foreach ($route in @("/final-route-manifest.json", "/submission-readiness.json", "/demo-script-final.json", "/visual-polish.json", "/final-freeze.json")) {{
  $payload = Invoke-RestMethod -Uri ($base + $route)
  if (-not $payload.syntheticOnly -or -not $payload.advisoryOnly -or $payload.runtimeGpuRequired -or $payload.runtimeExternalServiceRequired -or $payload.runtimePyTorchRequired -or $payload.autonomousActionsAllowed -or -not $payload.deterministicRulesAuthoritative) {{ throw "Safety flag mismatch: $route" }}
}}
Write-Host "FINAL LIVE QA SWEEP PASSED"
'''


@unified_page
def render_final_route_manifest_html() -> str:
    payload = get_final_route_manifest_payload()
    groups = "".join(f'<section><h2>{html.escape(group)}</h2><p>{len(ROUTE_GROUPS[group])} required routes</p></section>' for group in payload["routeGroups"])
    checks = get_live_qa_checklist_payload()
    passed = "".join(f"<li>{html.escape(item)}</li>" for item in checks["passCriteria"])
    no_go = "".join(f"<li>{html.escape(item)}</li>" for item in checks["noGoCriteria"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Final Route Manifest and Live QA Sweep</title><style>:root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:28px 18px 56px}}h1{{font-size:3rem;line-height:1.05;letter-spacing:-.035em;text-wrap:balance}}h2{{font-size:1.2rem}}p{{color:var(--muted);max-width:72ch}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.badges,.links{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 32px}}.badges span,.links a{{border:1px solid var(--line);border-radius:8px;padding:8px 11px}}.groups{{border-top:1px solid var(--line)}}.groups section{{display:grid;grid-template-columns:1fr auto;align-items:center;gap:18px;padding:12px 2px;border-bottom:1px solid var(--line)}}.groups section h2,.groups section p{{margin:0}}.criteria{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:36px}}@media(max-width:650px){{main{{padding:18px 12px 44px}}h1{{font-size:2.25rem}}.criteria{{grid-template-columns:1fr}}.groups section{{grid-template-columns:1fr;gap:2px}}}}</style></head><body><main><h1>Final Route Manifest and Live QA Sweep</h1><p>Owner-run availability, safety, layout, and freeze checks for the final submission build.</p><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>{len(payload["requiredRoutes"])} required routes</span><span>Owner signoff required</span></div><div class="links"><a href="/live-qa-checklist">Live QA checklist</a><a href="/live-validation-script.ps1">PowerShell validation script</a><a href="/submission-readiness">Submission Readiness</a><a href="/final-freeze">Final Freeze</a></div><div class="groups">{groups}</div><div class="criteria"><section><h2>Pass criteria</h2><ul>{passed}</ul></section><section><h2>No-go criteria</h2><ul>{no_go}</ul></section></div></main></body></html>'''
