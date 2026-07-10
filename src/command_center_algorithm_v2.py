from __future__ import annotations

import html
from typing import Any

from algorithm_console_v2 import get_algorithm_console_payload
from behavior_predictor_v2 import get_behavior_predictor_payload
from inspection_engine_v2 import BLOCKED_ACTIONS, get_inspection_plan


PHASE = "Phase 38 - Command Center Algorithm Integration"
PRIORITY_CASES = (
    "door-open-warming", "gateway-delay", "unresolved-mapping-risk",
    "single-sensor-spike", "mixed-quality-evidence", "multi-sensor-confirmed-warming",
)


def _inspection_cards() -> list[dict[str, Any]]:
    predictor = get_behavior_predictor_payload()
    predictions = {item["caseId"]: item for item in predictor.get("casePredictions", [])}
    cards = []
    for case_id in PRIORITY_CASES:
        prediction = predictions.get(case_id)
        if not prediction:
            continue
        plan = get_inspection_plan(case_id)
        cards.append({
            "caseId": case_id, "predictedFaultLabel": prediction["predictedFaultLabel"],
            "predictedBehaviorLabel": prediction["predictedBehaviorLabel"],
            "confidenceBand": prediction["confidenceBand"],
            "primaryInspectionTarget": plan["primaryInspectionTarget"],
            "whyInspect": plan["likelyRootCause"],
            "behaviorPredictionRoute": f"/cases/{case_id}/behavior-prediction.json",
            "inspectionPlanRoute": f"/cases/{case_id}/inspection-plan.json",
            "rootCauseRoute": f"/cases/{case_id}/root-cause-analysis.json",
        })
    return cards


def get_what_to_inspect_next_payload() -> dict[str, Any]:
    cards = [{
        "caseId": item["caseId"], "issueSummary": item["whyInspect"],
        "inspectFirst": item["primaryInspectionTarget"],
        "inspectWhy": "This target addresses the strongest synthetic evidence and its uncertainty.",
        "confidenceBand": item["confidenceBand"],
        "evidenceRoutes": {
            "behaviorPrediction": item["behaviorPredictionRoute"],
            "inspectionPlan": item["inspectionPlanRoute"], "rootCause": item["rootCauseRoute"],
        },
        "blockedOperationalActions": list(BLOCKED_ACTIONS),
    } for item in _inspection_cards()]
    return {"phase": PHASE, "syntheticOnly": True, "advisoryOnly": True, "priorityInspectionCards": cards}


def get_command_center_algorithm_payload() -> dict[str, Any]:
    console = get_algorithm_console_payload()
    metrics = {
        "trainingRows": console["trainingRows"],
        "neuralFaultAccuracy": console["neuralMetrics"].get("faultAccuracy"),
        "neuralBehaviorAccuracy": console["neuralMetrics"].get("behaviorAccuracy"),
        "distilledFaultAccuracy": console["distilledMetrics"].get("faultAccuracy"),
        "distilledBehaviorAccuracy": console["distilledMetrics"].get("behaviorAccuracy"),
        "supportedFaultCount": console["supportedFaultCount"],
        "featureWeightCount": console["featureWeightCount"],
    }
    return {
        "phase": PHASE, "status": "READY" if console["artifactAvailable"] else "ARTIFACT_UNAVAILABLE",
        "syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False,
        "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False,
        "runtimePyTorchRequired": False, "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False, "stblIntegrated": console["predictorIntegrated"],
        "inspectionEngineIntegrated": console["inspectionEngineIntegrated"],
        "algorithmConsoleIntegrated": True, "dashboardIntegrationOnly": True,
        "architectureChanged": False, "dependenciesAdded": False,
        "headlineMetrics": metrics,
        "topAlgorithmInsights": [
            {"title": "Synthetic training corpus", "metric": metrics["trainingRows"], "meaning": "Offline coverage used to train STBL.", "route": "/algorithm-console"},
            {"title": "Neural behavior accuracy", "metric": metrics["neuralBehaviorAccuracy"], "meaning": "Synthetic offline test metric.", "route": "/algorithm-console"},
            {"title": "Distilled behavior accuracy", "metric": metrics["distilledBehaviorAccuracy"], "meaning": "Transparent stdlib runtime metric.", "route": "/algorithm-console/runtime-boundary.json"},
            {"title": "Supported fault families", "metric": metrics["supportedFaultCount"], "meaning": "Project-defined synthetic fault universe.", "route": "/algorithm-console/error-coverage.json"},
            {"title": "Weighted features", "metric": metrics["featureWeightCount"], "meaning": "Inspectable inputs used by centroid distance.", "route": "/algorithm-console/feature-weights.json"},
        ],
        "whatToInspectNext": _inspection_cards(),
        "algorithmStory": [
            "Trained offline with GPU and Jupyter on synthetic evidence.",
            "Distilled into transparent stdlib rules.",
            "Predicts behavior and a likely synthetic fault family.",
            "Recommends human inspection targets.",
            "Does not take operational action.",
        ],
        "safetyBoundary": {
            "syntheticOnly": True, "advisoryOnly": True, "noRealData": True,
            "noGpuOrPyTorchRuntimeDependency": True,
            "deterministicRulesAuthoritative": True, "humanReviewRequired": True,
        },
        "routeMap": {
            "commandCenter": "/command-center", "commandCenterAlgorithm": "/command-center-algorithm",
            "algorithmInsights": "/algorithm-insights", "algorithmConsole": "/algorithm-console",
            "behaviorPredictor": "/behavior-predictor", "inspectionEngine": "/inspection-engine",
            "dashboardStrategy": "/dashboard-strategy", "demoFlow": "/demo-flow",
            "productionGapAnalysis": "/production-gap-analysis",
            "judgePack": "/judge-pack", "largeScaleDataLab": "/large-scale-data-lab",
            "faultAtlas": "/fault-atlas", "caseWalkthroughs": "/case-walkthroughs",
            "finalRouteManifest": "/final-route-manifest", "submissionReadiness": "/submission-readiness",
            "demoScriptFinal": "/demo-script-final", "visualPolish": "/visual-polish", "finalFreeze": "/final-freeze",
        },
    }


def get_algorithm_insights_payload() -> dict[str, Any]:
    return get_command_center_algorithm_payload()


def render_command_center_algorithm_html() -> str:
    payload = get_command_center_algorithm_payload()
    metrics = payload["headlineMetrics"]
    insights = "".join(f'<a href="{html.escape(item["route"])}"><strong>{html.escape(str(item["metric"]))}</strong><span>{html.escape(item["title"])}</span><small>{html.escape(item["meaning"])}</small></a>' for item in payload["topAlgorithmInsights"])
    inspections = "".join(f'<article><p>{html.escape(item["confidenceBand"])}</p><h2>{html.escape(item["caseId"])}</h2><strong>{html.escape(item["predictedFaultLabel"])}</strong><small>Likely cause: {html.escape(item["whyInspect"])}</small><span>Inspect: {html.escape(item["primaryInspectionTarget"])}</span><a href="{html.escape(item["inspectionPlanRoute"])}">Inspection plan</a><a href="{html.escape(item["rootCauseRoute"])}">Root cause</a></article>' for item in payload["whatToInspectNext"])
    story = "".join(f"<li>{html.escape(item)}</li>" for item in payload["algorithmStory"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Command Center Algorithm Insights</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--surface2:#122722;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1180px,100%);margin:auto;padding:24px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.hero{{border-left:6px solid var(--accent);border-radius:var(--radius);background:var(--surface);padding:clamp(24px,5vw,50px)}}h1{{font-size:clamp(40px,6vw,68px);line-height:1;letter-spacing:-.045em;max-width:850px;margin:0 0 18px}}.hero p{{color:var(--muted);max-width:60ch}}.metrics{{display:grid;grid-template-columns:repeat(5,1fr);margin:16px 0 42px;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}.metrics div{{padding:16px;border-right:1px solid var(--line)}}.metrics div:last-child{{border:0}}.metrics strong,.metrics span{{display:block}}.metrics strong{{font-size:25px;color:var(--accent)}}section{{margin-top:44px}}section>p{{color:var(--muted);max-width:64ch}}.insights{{display:grid;grid-template-columns:1.2fr .8fr;gap:10px}}.insights a{{display:flex;flex-direction:column;background:var(--surface);padding:18px;min-height:145px;border-top:3px solid var(--accent)}}.insights strong{{font-size:27px}}.insights small{{color:var(--muted);margin-top:auto}}.inspect{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}.inspect article{{background:var(--surface);padding:18px;display:flex;flex-direction:column;min-height:210px}}.inspect article>p{{color:var(--accent);text-transform:uppercase;font-weight:750;margin:0}}.inspect article>span{{color:var(--muted);margin:8px 0 16px}}.inspect article>a{{margin-top:5px}}.story-boundary{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.story-boundary>div{{background:var(--surface2);border-radius:var(--radius);padding:24px}}.routes{{display:flex;flex-wrap:wrap;gap:8px;margin-top:38px}}.routes a{{border:1px solid var(--line);border-radius:8px;padding:9px 12px}}@media(max-width:760px){{main{{padding:14px 12px 44px}}.metrics,.insights,.inspect,.story-boundary{{grid-template-columns:1fr}}.metrics div{{border:0;border-bottom:1px solid var(--line)}}h1{{font-size:42px}}}}
    </style></head><body><main><section class="hero"><h1>What is wrong? What should we inspect?</h1><p>STBL evidence connects likely synthetic faults to transparent human inspection targets.</p></section><div class="metrics"><div><strong>{metrics["trainingRows"]:,}</strong><span>synthetic rows</span></div><div><strong>{float(metrics["neuralFaultAccuracy"] or 0)*100:.2f}%</strong><span>neural fault</span></div><div><strong>{float(metrics["neuralBehaviorAccuracy"] or 0)*100:.2f}%</strong><span>neural behavior</span></div><div><strong>{float(metrics["distilledFaultAccuracy"] or 0)*100:.2f}%</strong><span>distilled fault</span></div><div><strong>{float(metrics["distilledBehaviorAccuracy"] or 0)*100:.2f}%</strong><span>distilled behavior</span></div></div>
    <section><h2>STBL algorithm insights</h2><p>Offline performance, transparent runtime evidence, and bounded coverage in one view.</p><div class="insights">{insights}</div></section>
    <section><h2>What to inspect next</h2><p>Representative cases rank the first human evidence target without taking operational action.</p><div class="inspect">{inspections}</div></section>
    <section class="story-boundary"><div><h2>Algorithm story</h2><ol>{story}</ol></div><div><h2>Safety boundary</h2><p>Synthetic-only. Advisory-only. No real data or runtime GPU, PyTorch, notebook, or external service. Deterministic rules remain authoritative and human review is required.</p></div></section>
    <nav class="routes"><a href="/algorithm-console">Algorithm Console</a><a href="/behavior-predictor">Behavior Predictor</a><a href="/inspection-engine">Inspection Engine</a><a href="/demo-flow">Demo Flow</a><a href="/production-gap-analysis">Production Gap Analysis</a></nav></main></body></html>'''
