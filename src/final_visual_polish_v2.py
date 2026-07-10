from __future__ import annotations

import html
from typing import Any

PHASE = "Phase 46 - Visual Polish and Screenshot Pass"
ROUTES = ["/command-center", "/algorithm-console", "/judge-pack", "/case-walkthroughs/door-open-warming", "/fault-atlas", "/large-scale-data-lab", "/submission-readiness", "/demo-script-final", "/final-route-manifest"]
PURPOSES = ["product overview", "algorithm evidence", "judge evidence hub", "end-to-end case", "fault coverage", "scale profile", "submission copy", "demo narration", "live QA manifest"]


def get_visual_polish_payload() -> dict[str, Any]:
    return {"phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True, "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False, "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True, "realWorldDataUsed": False, "polishOnly": True, "architectureChanged": False, "dependenciesAdded": False, "externalAssetsRequired": False, "externalCallsRequired": False, "screenshotReadyRoutes": list(ROUTES), "visualChecks": ["mobile overflow", "desktop overflow", "badge consistency", "button hierarchy", "focus states", "color consistency", "no external assets", "screenshot route order"], "routeMap": {"visualPolish": "/visual-polish", "screenshotChecklist": "/screenshot-checklist", "screenshotRouteMap": "/screenshot-route-map.json", "finalRouteManifest": "/final-route-manifest", "submissionReadiness": "/submission-readiness", "demoScriptFinal": "/demo-script-final", "demoFreeze": "/demo-freeze", "finalFreeze": "/final-freeze"}}


def get_screenshot_checklist_payload() -> dict[str, Any]:
    return {"phase": PHASE, "screenshotChecklist": ["use a clean browser window", "capture desktop at a consistent viewport", "capture mobile at 390 by 844", "verify no page overflow", "keep safety badges visible", "avoid transient browser UI", "confirm no external assets"], "recommendedCaptureOrder": list(ROUTES), "fileNamingSuggestions": [f"{index:02d}-{route.strip('/').replace('/', '-') or 'home'}.png" for index, route in enumerate(ROUTES, 1)], "whatEachScreenshotProves": dict(zip(ROUTES, PURPOSES)), "noGoVisualIssues": ["page-level horizontal overflow", "clipped heading", "unreadable copy", "missing safety boundary", "broken route button", "external asset request"]}


def get_screenshot_route_map_payload() -> dict[str, Any]:
    return {"phase": PHASE, "routes": [{"route": route, "screenshotPurpose": purpose, "priority": "primary" if index < 6 else "supporting", "expectedVisualElements": ["page title", "safety badges", "evidence content", "internal route links"]} for index, (route, purpose) in enumerate(zip(ROUTES, PURPOSES))]}


def render_visual_polish_html() -> str:
    payload = get_visual_polish_payload(); checklist = get_screenshot_checklist_payload()
    checks = "".join(f"<li>{html.escape(item)}</li>" for item in checklist["screenshotChecklist"])
    rows = "".join(f'<tr><td>{index}</td><td><a href="{html.escape(route)}">{html.escape(route)}</a></td><td>{html.escape(PURPOSES[index - 1])}</td></tr>' for index, route in enumerate(ROUTES, 1))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Visual Polish and Screenshot Pass</title><style>:root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 18px 56px}}h1{{font-size:3rem;line-height:1.05;letter-spacing:-.035em;text-wrap:balance}}p{{color:var(--muted);max-width:72ch}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.badges,.links{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 32px}}.badges span,.links a{{border:1px solid var(--line);border-radius:8px;padding:8px 11px}}.layout{{display:grid;grid-template-columns:.7fr 1.3fr;gap:28px}}.table{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;min-width:560px}}th,td{{padding:11px;text-align:left;border-bottom:1px solid var(--line)}}@media(max-width:650px){{main{{padding:18px 12px 44px}}h1{{font-size:2.25rem}}.layout{{grid-template-columns:1fr}}}}</style></head><body><main><h1>Visual Polish and Screenshot Pass</h1><p>A non-invasive capture checklist using the existing visual system and internal routes.</p><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Polish only</span><span>Architecture changed: false</span><span>External assets required: false</span></div><div class="links"><a href="/screenshot-checklist">Screenshot checklist</a><a href="/screenshot-route-map.json">Route map JSON</a><a href="/submission-readiness">Submission Readiness</a></div><div class="layout"><section><h2>Capture checks</h2><ol>{checks}</ol></section><section class="table"><h2>Capture order</h2><table><thead><tr><th>#</th><th>Route</th><th>Purpose</th></tr></thead><tbody>{rows}</tbody></table></section></div></main></body></html>'''
