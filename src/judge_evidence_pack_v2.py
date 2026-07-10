from __future__ import annotations

import html
from typing import Any

from algorithm_console_v2 import get_algorithm_console_payload


PHASE = "Phase 39 - Final Judge Evidence Pack"

TOP_ROUTES = [
    ("Command Center", "/command-center", "Product home screen and safety posture."),
    ("Algorithm Console", "/algorithm-console", "Training, distillation, features, coverage, and weaknesses."),
    ("Algorithm Insights", "/command-center-algorithm", "Headline metrics and priority inspection targets."),
    ("Behavior Predictor", "/behavior-predictor", "Fourteen transparent distilled predictions."),
    ("Inspection Engine", "/inspection-engine", "Likely root causes and human inspection plans."),
    ("Case Walkthroughs", "/case-walkthroughs", "Six end-to-end narrative evidence paths."),
    ("Large-Scale Data Lab", "/large-scale-data-lab", "Deterministic high-volume data profiles."),
    ("Fault Atlas", "/fault-atlas", "Thirty-eight synthetic fault prototypes."),
    ("Demo Flow", "/demo-flow", "Guided presentation order."),
    ("Production Gap Analysis", "/production-gap-analysis", "Explicit limits and future work."),
    ("Final Validation", "/final-validation", "Committed local validation evidence."),
]


def get_demo_script_payload() -> dict[str, Any]:
    route_order = [route for _, route, _ in TOP_ROUTES[:8]] + ["/production-gap-analysis"]
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "pitches": {
            "60SecondPitch": "ColdChain Sentinel turns noisy synthetic sensor evidence into deterministic quality checks, consensus guardrails, advisory risk, transparent STBL behavior predictions, and human inspection targets.",
            "threeMinuteDemo": "Open the command center, show algorithm evidence, follow one case walkthrough, and close with the claims boundary.",
            "fiveMinuteDemo": "Add the large-scale profile and fault atlas before completing the case walkthrough and production gap review.",
        },
        "exactRouteOrder": route_order,
        "screenTalkTracks": [{"route": route, "whatToSay": proof} for _, route, proof in TOP_ROUTES],
        "safeLanguage": ["synthetic-only evidence", "advisory prediction", "project-defined fault universe", "transparent distilled runtime", "human inspection recommendation", "deterministic rules remain authoritative"],
        "phrasesToAvoid": ["production" + "-ready", "pharma" + " validated", "real-world" + " validated", "compliance" + " certified", "autonomous" + " release", "customer" + " notification"],
    }


def get_technical_proof_payload() -> dict[str, Any]:
    console = get_algorithm_console_payload()
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "architectureSummary": "Python standard-library HTTP server with deterministic payload modules and committed small JSON evidence artifacts.",
        "runtimeBoundary": {"stdlibOnly": True, "gpuRequired": False, "pyTorchRequired": False, "notebookRequired": False, "externalServiceRequired": False, "databaseRequired": False},
        "stblTrainingAndDistillation": {"trainingRows": console["trainingRows"], "faultPrototypeCount": console["faultPrototypeCount"], "featureWeightCount": console["featureWeightCount"], "distilledMethod": console["distilledMethod"], "neuralMetrics": console["neuralMetrics"], "distilledMetrics": console["distilledMetrics"]},
        "routeEvidence": [route for _, route, _ in TOP_ROUTES],
        "validationEvidence": ["focused phase tests", "compatibility phase tests", "script-style cold-chain validation", "dashboard self-check", "local HTTP smoke", "desktop and mobile browser smoke"],
        "dependencyBoundary": "No new dependency file or runtime package is required.",
        "externalCallsRequired": False,
    }


def get_claims_boundary_payload() -> dict[str, Any]:
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "whatWeClaim": ["The demo uses deterministic synthetic evidence.", "STBL offline synthetic metrics are surfaced from committed artifacts.", "The live app uses transparent distilled rules.", "Predictions route humans to inspection evidence.", "Runtime boot requires no GPU, PyTorch, notebook, database, or external service."],
        "whatWeDoNotClaim": ["External-world validation.", "Operational disposition authority.", "Regulated or compliance approval.", "Real customer integration.", "Exhaustive fault coverage."],
        "allowedDemoPhrasing": ["synthetic benchmark evidence", "advisory-only prediction", "human review required", "project-defined synthetic fault universe"],
        "bannedOverclaimPhrasing": ["production" + "-ready", "real-world" + " validated", "compliance" + " certified", "autonomous" + " quarantine", "autonomous" + " discard", "autonomous" + " reroute"],
        "safetyExplanation": "Deterministic rules remain authoritative. STBL explains likely synthetic behavior and inspection targets but cannot execute operational actions.",
    }


def get_judge_evidence_pack_payload() -> dict[str, Any]:
    console = get_algorithm_console_payload()
    metrics = {
        "trainingRows": console["trainingRows"], "faultPrototypeCount": console["faultPrototypeCount"],
        "featureWeightCount": console["featureWeightCount"],
        "neuralFaultAccuracy": console["neuralMetrics"].get("faultAccuracy"),
        "neuralBehaviorAccuracy": console["neuralMetrics"].get("behaviorAccuracy"),
        "distilledFaultAccuracy": console["distilledMetrics"].get("faultAccuracy"),
        "distilledBehaviorAccuracy": console["distilledMetrics"].get("behaviorAccuracy"),
    }
    return {
        "phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True,
        "realWorldDataUsed": False, "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False,
        "deterministicRulesAuthoritative": True, "autonomousActionsAllowed": False,
        "databaseRequired": False, "persistenceEnabled": False,
        "dependenciesAdded": False, "externalCallsRequired": False,
        "projectSummary": "ColdChain Sentinel is a synthetic evidence and human-review demonstration spanning data quality, consensus, advisory risk, transparent behavior prediction, and inspection guidance.",
        "topJudgeRoutes": [{"title": title, "route": route, "evidence": proof} for title, route, proof in TOP_ROUTES],
        "headlineMetrics": metrics,
        "evidenceHighlights": ["synthetic sensor evidence", "data quality pipeline", "consensus guardrails", "SERS advisory risk", "STBL behavior prediction", "root cause inspection", "algorithm console", "command center integration", "partner/API readiness", "production gap honesty"],
        "limitations": ["synthetic-only", "no external-world validation", "no operational disposition", "no regulated or compliance claim", "no real customer integration"],
        "routeMap": {"judgePack": "/judge-pack", "demoScript": "/judge-pack/demo-script.json", "technicalProof": "/judge-pack/technical-proof.json", "claimsBoundary": "/judge-pack/claims-boundary.json", **{title.replace(" ", "").lower(): route for title, route, _ in TOP_ROUTES}},
    }


def render_judge_evidence_pack_html() -> str:
    payload = get_judge_evidence_pack_payload()
    metrics = payload["headlineMetrics"]
    metric_rows = "".join(f'<div><strong>{value * 100:.2f}%</strong><span>{html.escape(name)}</span></div>' if isinstance(value, float) else f'<div><strong>{value:,}</strong><span>{html.escape(name)}</span></div>' for name, value in metrics.items())
    routes = "".join(f'<a href="{html.escape(row["route"])}"><strong>{html.escape(row["title"])}</strong><span>{html.escape(row["evidence"])}</span></a>' for row in payload["topJudgeRoutes"])
    limits = "".join(f"<li>{html.escape(item)}</li>" for item in payload["limitations"])
    highlights = "".join(f"<li>{html.escape(item)}</li>" for item in payload["evidenceHighlights"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Final Judge Evidence Pack</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1180px,100%);margin:auto;padding:28px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}h1{{font-size:48px;line-height:1.05;letter-spacing:-.035em;text-wrap:balance;margin:0 0 14px}}h2{{font-size:24px;text-wrap:balance}}.intro{{max-width:72ch;color:var(--muted)}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 32px}}.badges span{{border:1px solid var(--line);border-radius:8px;padding:7px 10px}}.metrics{{display:flex;flex-wrap:wrap;border-block:1px solid var(--line);padding:18px 0;gap:24px}}.metrics div{{min-width:130px}}.metrics strong,.metrics span{{display:block}}.metrics strong{{color:var(--accent);font-size:25px}}section{{margin-top:40px}}.routes{{display:grid;grid-template-columns:1.2fr .8fr;gap:8px}}.routes a{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px;display:flex;flex-direction:column;min-height:110px}}.routes span{{color:var(--muted);margin-top:6px}}.proof{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.proof>div{{border-block:1px solid var(--line);padding:12px 0}}.proof li{{margin:6px 0}}.demo{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px}}.buttons{{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}}.buttons a{{border:1px solid var(--accent);border-radius:8px;padding:8px 11px}}@media(max-width:760px){{main{{padding:18px 12px 44px}}h1{{font-size:36px}}.routes,.proof{{grid-template-columns:1fr}}.metrics{{gap:15px}}}}
    </style></head><body><main><header><h1>Final Judge Evidence Pack</h1><p class="intro">One safe path through what was built, what evidence exists, what to click, and which claims remain intentionally outside scope.</p></header><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Stdlib runtime</span><span>GPU required: false</span><span>External service required: false</span><span>Deterministic rules authoritative</span></div><section class="metrics">{metric_rows}</section><section><h2>Top evidence routes</h2><div class="routes">{routes}</div></section><section class="proof"><div><h2>Evidence highlights</h2><ul>{highlights}</ul></div><div><h2>Claims boundary</h2><ul>{limits}</ul><a href="/judge-pack/claims-boundary.json">Open claims boundary JSON</a></div></section><section class="demo"><h2>Demo path</h2><p>Start at the command center, open algorithm evidence, follow one case walkthrough, and close with the production gap analysis.</p><div class="buttons"><a href="/judge-pack/demo-script.json">Demo script</a><a href="/judge-pack/technical-proof.json">Technical proof</a><a href="/command-center">Command Center</a><a href="/algorithm-console">Algorithm Console</a><a href="/behavior-predictor">Behavior Predictor</a><a href="/inspection-engine">Inspection Engine</a><a href="/case-walkthroughs">Case Walkthroughs</a><a href="/fault-atlas">Fault Atlas</a><a href="/large-scale-data-lab">Large-Scale Data Lab</a></div></section></main></body></html>'''
