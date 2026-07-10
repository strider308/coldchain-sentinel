from __future__ import annotations

import html
from typing import Any

from algorithm_console_v2 import get_algorithm_console_payload

PHASE = "Phase 44 - Submission Readiness Pack"
LIVE_URL = "https://coldchain-sentinel-35ex.onrender.com"
REPO_URL = "https://github.com/strider308/coldchain-sentinel"
LIVE_COMMIT = "510e909e2330b887ced0ff7061a5b9f465472499"


def _copy() -> dict[str, Any]:
    one = "ColdChain Sentinel turns noisy synthetic cold-chain sensor evidence into bounded advisory risk, transparent behavior predictions, and human inspection guidance."
    short = "A stdlib-only demonstration that combines deterministic data-quality and consensus guardrails with SERS advisory risk, offline-trained STBL behavior prediction, and auditable human inspection paths."
    long = short + " It exposes synthetic evidence, limitations, algorithm metrics, root-cause hypotheses, and six end-to-end cases without requiring GPU, PyTorch, notebooks, databases, or external services at runtime. Deterministic safety rules remain authoritative."
    return {"oneLineDescription": one, "shortDescription": short, "longDescription": long, "technicalSummary": "Python standard-library HTTP runtime backed by committed small evidence artifacts and transparent weighted-centroid prototype rules.", "aiUsageDisclosure": "GPU and Jupyter supported offline synthetic STBL research. The live runtime uses transparent distilled rules. Fireworks remains optional explanation support.", "safetyDisclosure": "Synthetic-only and advisory-only. Human review is required and deterministic rules remain authoritative.", "limitationsDisclosure": "No external-world validation, customer integration, regulated approval, operational disposition, or measured deployment throughput is claimed.", "judgePitchBullets": ["Evidence first, not dashboard theater", "Transparent runtime behavior", "Human inspection paths", "Honest deployment gap"], "demoVideoScriptShort": "Open the command center, show algorithm evidence, follow door-open warming, then close on the claims boundary.", "demoVideoScriptLong": "Show the command center, algorithm metrics, one end-to-end case, the 38-fault atlas, judge pack, and owner submission checklist."}


def get_submission_readiness_payload() -> dict[str, Any]:
    console = get_algorithm_console_payload()
    copy = _copy()
    return {"phase": PHASE, "status": "READY_FOR_OWNER_SUBMISSION", "syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False, "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False, "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True, "dependenciesAdded": False, "externalCallsRequired": False, "ownerSubmissionRequired": True, "submissionNotAutomated": True, "liveDemoUrl": LIVE_URL, "repositoryUrl": REPO_URL, "latestKnownLiveCommit": LIVE_COMMIT, "projectName": "ColdChain Sentinel", "oneLineDescription": copy["oneLineDescription"], "shortDescription": copy["shortDescription"], "longDescription": copy["longDescription"], "technicalDifferentiators": ["synthetic cold-chain evidence pipeline", "data quality and consensus guardrails", "SERS advisory risk", "STBL offline GPU/Jupyter training", "transparent stdlib runtime distillation", "root-cause inspection guidance", "algorithm evidence console", "judge evidence pack"], "headlineMetrics": {"trainingRows": console["trainingRows"], "faultCount": console["faultPrototypeCount"], "featureCount": console["featureWeightCount"], "neuralFaultAccuracy": console["neuralMetrics"]["faultAccuracy"], "neuralBehaviorAccuracy": console["neuralMetrics"]["behaviorAccuracy"], "distilledFaultAccuracy": console["distilledMetrics"]["faultAccuracy"], "distilledBehaviorAccuracy": console["distilledMetrics"]["behaviorAccuracy"]}, "screenshotsToCapture": ["/command-center", "/algorithm-console", "/judge-pack", "/case-walkthroughs/door-open-warming", "/fault-atlas", "/submission-readiness"], "videoDemoRouteOrder": ["/command-center", "/algorithm-console", "/case-walkthroughs/door-open-warming", "/fault-atlas", "/judge-pack", "/submission-readiness"], "claimsBoundarySummary": copy["safetyDisclosure"], "knownLimitations": copy["limitationsDisclosure"], "routeMap": {"submissionReadiness": "/submission-readiness", "submissionChecklist": "/submission-checklist", "submissionCopy": "/submission-copy.json", "finalRouteManifest": "/final-route-manifest", "demoScriptFinal": "/demo-script-final", "visualPolish": "/visual-polish", "finalFreeze": "/final-freeze"}}


def get_submission_checklist_payload() -> dict[str, Any]:
    return {"phase": PHASE, "ownerChecklist": ["deploy latest main", "run final live QA script", "capture screenshots", "record demo video", "verify GitHub repo visibility if needed", "copy short and long descriptions", "disclose synthetic-only advisory boundary", "submit URL and repository"], "goCriteria": ["live QA passes", "screenshots and video captured", "claims boundary disclosed", "owner signs off"], "noGoCriteria": ["route or safety check fails", "submission copy missing", "demo overclaims evidence", "deployed commit is not confirmed"], "ownerSignoffRequired": True}


def get_submission_copy_payload() -> dict[str, Any]:
    return _copy()


def render_submission_readiness_html() -> str:
    payload = get_submission_readiness_payload(); checklist = get_submission_checklist_payload()
    blocks = "".join(f'<section><h2>{html.escape(label)}</h2><p>{html.escape(payload[key])}</p></section>' for label, key in (("One-line description", "oneLineDescription"), ("Short description", "shortDescription"), ("Long description", "longDescription")))
    shots = "".join(f"<li><code>{html.escape(route)}</code></li>" for route in payload["screenshotsToCapture"])
    steps = "".join(f"<li>{html.escape(item)}</li>" for item in checklist["ownerChecklist"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Submission Readiness Pack</title><style>:root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 18px 56px}}h1{{font-size:3rem;line-height:1.05;letter-spacing:-.035em;text-wrap:balance}}p{{color:var(--muted);max-width:72ch;text-wrap:pretty}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.badges,.links{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 32px}}.badges span,.links a{{border:1px solid var(--line);border-radius:8px;padding:8px 11px}}.copy section{{border-block:1px solid var(--line);padding:14px 0}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:34px}}code{{overflow-wrap:anywhere;color:var(--accent)}}@media(max-width:650px){{main{{padding:18px 12px 44px}}h1{{font-size:2.25rem}}.split{{grid-template-columns:1fr}}}}</style></head><body><main><h1>Submission Readiness Pack</h1><p>Copy, routes, screenshots, and owner checks for the final submission form.</p><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Owner submission required</span><span>Submission not automated</span></div><div class="links"><a href="/submission-copy.json">Submission copy JSON</a><a href="/submission-checklist">Checklist</a><a href="/demo-script-final">Demo Script</a><a href="/final-freeze">Final Freeze</a></div><div class="copy">{blocks}</div><div class="split"><section><h2>Screenshot list</h2><ol>{shots}</ol></section><section><h2>Owner checklist</h2><ol>{steps}</ol></section></div><section><h2>Claims boundary</h2><p>{html.escape(payload["claimsBoundarySummary"])}</p><p>{html.escape(payload["knownLimitations"])}</p></section></main></body></html>'''
