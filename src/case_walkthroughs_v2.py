from __future__ import annotations

import html
from typing import Any

from behavior_predictor_v2 import predict_case_behavior
from inspection_engine_v2 import BLOCKED_ACTIONS, get_inspection_plan


PHASE = "Phase 42 - End-to-End Case Walkthroughs"
WALKTHROUGHS = {
    "door-open-warming": ("Door-Open Warming", "A door event aligns with sustained warming across the affected synthetic zone.", "Connects environmental context, thermal evidence, and a direct inspection target."),
    "gateway-delay": ("Gateway Delay", "Device event time and gateway receipt time diverge, creating delayed evidence.", "Shows why timestamp reasoning must precede thermal interpretation."),
    "unresolved-mapping-risk": ("Unresolved Mapping Risk", "Thermal evidence exists, but pallet and zone identity remain uncertain.", "Demonstrates that mapping guardrails block overconfident conclusions."),
    "single-sensor-spike": ("Single-Sensor Spike", "One sensor spikes while neighboring synthetic sensors remain stable.", "Shows the false-spike guardrail and resistance to overreaction."),
    "multi-sensor-confirmed-warming": ("Multi-Sensor Confirmed Warming", "Several synthetic sensors agree on a sustained warming trend.", "Shows consensus evidence without allowing automated disposition."),
    "mixed-quality-evidence": ("Mixed-Quality Evidence", "Strong, weak, duplicate, and missing readings appear in one review window.", "Makes data-quality uncertainty visible before risk interpretation."),
}


def _audit_route(case_id: str) -> str:
    return f"/cases/{case_id}/audit-ledger.json" if case_id in ("door-open-warming", "unresolved-mapping-risk", "single-sensor-spike", "multi-sensor-confirmed-warming") else "/audit-ledger"


def get_case_walkthrough_payload(case_id: str) -> dict[str, Any]:
    if case_id not in WALKTHROUGHS:
        raise KeyError(case_id)
    title, storyline, why = WALKTHROUGHS[case_id]
    prediction = predict_case_behavior(case_id)
    plan = get_inspection_plan(case_id)
    routes = {
        "scenario": f"/scenario-library-v4/{case_id}.json",
        "behaviorPrediction": f"/cases/{case_id}/behavior-prediction.json",
        "inspectionPlan": f"/cases/{case_id}/inspection-plan.json",
        "rootCause": f"/cases/{case_id}/root-cause-analysis.json",
        "algorithmConsole": "/algorithm-console", "auditLedger": _audit_route(case_id),
        "decisionSimulator": f"/decision-simulator/{case_id}.json",
    }
    steps = [
        ("raw synthetic signal", "Open the scenario pattern and synthetic evidence.", routes["scenario"]),
        ("data quality check", "Identify missing, duplicate, weak, late, or conflicting readings.", f"/cases/{case_id}/expanded-evidence.json"),
        ("consensus guardrail", "Compare the suspect signal with neighboring sensors and zones.", f"/cases/{case_id}/evaluation-row.json"),
        ("SERS advisory risk", "Review the deterministic advisory risk context.", routes["decisionSimulator"]),
        ("STBL prediction", f'Review {prediction.get("predictedFaultLabel", "unavailable")} as an advisory synthetic match.', routes["behaviorPrediction"]),
        ("root cause hypothesis", f'Review the hypothesis: {plan["likelyRootCause"]}.', routes["rootCause"]),
        ("what to inspect first", f'Inspect {plan["primaryInspectionTarget"]}.', routes["inspectionPlan"]),
        ("blocked actions", "Confirm that operational actions and outbound messaging remain blocked.", routes["inspectionPlan"]),
        ("human review outcome", "Record uncertainty and a human review status without changing deterministic facts.", routes["decisionSimulator"]),
        ("audit evidence", "Follow the synthetic evidence trail and retained boundaries.", routes["auditLedger"]),
    ]
    return {
        "phase": PHASE, "caseId": case_id, "syntheticOnly": True, "advisoryOnly": True,
        "title": title, "storyline": storyline, "whyThisCaseMatters": why,
        "stepTimeline": [{"sequence": index, "title": step, "explanation": explanation, "route": route} for index, (step, explanation, route) in enumerate(steps, 1)],
        "stblPrediction": {key: prediction.get(key) for key in ("predictedBehaviorLabel", "predictedFaultLabel", "confidenceBand", "primaryInspectionTarget", "topAlternatives")},
        "inspectionPlan": {key: plan[key] for key in ("likelyRootCause", "inspectionPriority", "primaryInspectionTarget", "timelineWindowToInspect", "dataQualityWarnings", "humanReviewQuestions")},
        "evidenceRoutes": routes,
        "demoNarration": {
            "whatJudgeSees": f"A ten-step evidence path from {storyline.lower()} to a bounded human inspection plan.",
            "whatFounderSays": f"The system identifies a likely synthetic fault family and points a reviewer to {plan['primaryInspectionTarget']}.",
            "safeClaimBoundary": "This is deterministic synthetic advisory evidence. It does not determine operational disposition.",
        },
        "whatNotToDo": ["Do not treat a prediction as a disposition.", "Do not bypass deterministic guardrails.", "Do not execute blocked actions or outbound messaging."],
        "blockedOperationalActions": list(BLOCKED_ACTIONS),
        "safetyBoundary": {"syntheticOnly": True, "advisoryOnly": True, "humanReviewRequired": True, "deterministicRulesAuthoritative": True, "autonomousActionsAllowed": False},
    }


def get_case_walkthroughs_payload() -> dict[str, Any]:
    rows = []
    for case_id, (title, storyline, why) in WALKTHROUGHS.items():
        plan = get_inspection_plan(case_id)
        rows.append({"caseId": case_id, "title": title, "storyline": storyline, "whyThisCaseMatters": why, "primaryInspectionTarget": plan["primaryInspectionTarget"], "route": f"/case-walkthroughs/{case_id}"})
    return {
        "phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True,
        "realWorldDataUsed": False, "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False,
        "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True,
        "dependenciesAdded": False, "externalCallsRequired": False,
        "supportedWalkthroughCount": len(rows), "walkthroughs": rows,
        "routeMap": {"caseWalkthroughs": "/case-walkthroughs", "algorithmConsole": "/algorithm-console", "behaviorPredictor": "/behavior-predictor", "inspectionEngine": "/inspection-engine", "faultAtlas": "/fault-atlas", "judgePack": "/judge-pack"},
    }


def render_case_walkthroughs_html(case_id: str | None = None) -> str:
    if case_id is None:
        payload = get_case_walkthroughs_payload()
        cards = "".join(f'<article><h2>{html.escape(row["title"])}</h2><p>{html.escape(row["storyline"])}</p><strong>Inspect first: {html.escape(row["primaryInspectionTarget"])}</strong><a href="{html.escape(row["route"])}">Open walkthrough</a></article>' for row in payload["walkthroughs"])
        content = f'<header><h1>End-to-End Case Walkthroughs</h1><p class="intro">Six narrative paths connect raw synthetic signals, guardrails, STBL predictions, inspection guidance, and audit evidence.</p></header><section class="catalog">{cards}</section>'
    else:
        payload = get_case_walkthrough_payload(case_id)
        steps = "".join(f'<li><span>{step["sequence"]}</span><div><h2>{html.escape(step["title"])}</h2><p>{html.escape(step["explanation"])}</p><a href="{html.escape(step["route"])}">Evidence route</a></div></li>' for step in payload["stepTimeline"])
        routes = "".join(f'<a href="{html.escape(route)}">{html.escape(name)}</a>' for name, route in payload["evidenceRoutes"].items())
        content = f'<header><p><a href="/case-walkthroughs">All walkthroughs</a></p><h1>{html.escape(payload["title"])}</h1><p class="intro">{html.escape(payload["storyline"])}</p></header><section class="summary"><div><h2>STBL prediction</h2><p>{html.escape(str(payload["stblPrediction"]["predictedFaultLabel"]))} / {html.escape(str(payload["stblPrediction"]["confidenceBand"]))}</p></div><div><h2>Inspection plan</h2><p>{html.escape(payload["inspectionPlan"]["likelyRootCause"])}</p></div><div><h2>Inspect first</h2><p>{html.escape(payload["inspectionPlan"]["primaryInspectionTarget"])}</p></div></section><section><h2>Evidence timeline</h2><ol class="timeline">{steps}</ol></section><section class="narration"><h2>Demo narration</h2><p><strong>Judge sees:</strong> {html.escape(payload["demoNarration"]["whatJudgeSees"])}</p><p><strong>Founder says:</strong> {html.escape(payload["demoNarration"]["whatFounderSays"])}</p><p>{html.escape(payload["demoNarration"]["safeClaimBoundary"])}</p></section><nav class="evidence">{routes}</nav>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>End-to-End Case Walkthroughs</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1120px,100%);margin:auto;padding:28px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}h1{{font-size:46px;line-height:1.05;letter-spacing:-.035em;text-wrap:balance;margin:0 0 14px}}h2{{font-size:20px;text-wrap:balance}}.intro{{max-width:72ch;color:var(--muted)}}.catalog{{display:grid;grid-template-columns:1.15fr .85fr;gap:10px;margin-top:34px}}.catalog article{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:20px;display:flex;flex-direction:column;min-height:220px}}.catalog article:nth-child(3n){{grid-column:1/-1;min-height:170px}}.catalog p{{color:var(--muted)}}.catalog a{{margin-top:auto}}.summary{{display:flex;flex-wrap:wrap;gap:10px;margin:30px 0}}.summary>div{{flex:1 1 250px;border-block:1px solid var(--line);padding:16px 0}}.summary p{{color:var(--muted)}}.timeline{{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}}.timeline li{{display:grid;grid-template-columns:46px 1fr;gap:14px;padding:16px 0;border-bottom:1px solid var(--line)}}.timeline li>span{{color:var(--accent);font-weight:800;font-size:21px}}.timeline h2,.timeline p{{margin:0 0 6px}}.timeline p{{color:var(--muted)}}.narration{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px;margin-top:34px}}.evidence{{display:flex;flex-wrap:wrap;gap:8px;margin-top:28px}}.evidence a{{border:1px solid var(--line);border-radius:8px;padding:7px 10px}}@media(max-width:760px){{main{{padding:18px 12px 44px}}h1{{font-size:36px}}.catalog{{grid-template-columns:1fr}}.catalog article:nth-child(3n){{grid-column:auto}}.timeline li{{grid-template-columns:34px 1fr}}}}
    </style></head><body><main>{content}<nav class="evidence"><a href="/algorithm-console">Algorithm Console</a><a href="/behavior-predictor">Behavior Predictor</a><a href="/inspection-engine">Inspection Engine</a><a href="/fault-atlas">Fault Atlas</a><a href="/judge-pack">Judge Pack</a></nav><section class="narration"><h2>Safety boundary</h2><p>Synthetic-only. Advisory-only. Deterministic rules remain authoritative. Human review is required and no operational action is executed.</p></section></main></body></html>'''
