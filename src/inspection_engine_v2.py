from __future__ import annotations

import html
from typing import Any

from behavior_predictor_v2 import CASE_FEATURES, predict_case_behavior


PHASE = "Phase 36 - Root Cause and Inspection Recommendation Engine"
BLOCKED_ACTIONS = ["release", "quarantine", "discard", "reroute", "customer messaging"]

CASE_GUIDANCE = {
    "no-excursion-control": ("no confirmed fault / routine review", "low", "routine evidence review", ["stable evidence remains synthetic"]),
    "single-sensor-spike": ("isolated suspect sensor signal", "medium", "suspect sensor and neighboring sensors", ["single-sensor disagreement"]),
    "multi-sensor-confirmed-warming": ("sustained multi-sensor warming pattern", "high", "zone consensus sensors and thermal timeline", ["thermal interpretation requires human review"]),
    "unresolved-mapping-risk": ("unresolved pallet-zone identity mapping", "high", "pallet-zone identity mapping", ["location identity is unresolved"]),
    "door-open-warming": ("warming aligned with a door-open interval", "high", "door event timeline and affected zone", ["door context is synthetic"]),
    "dropout-weak-signal": ("weak signal with missing reading windows", "medium", "gateway signal timeline and missing readings", ["coverage is incomplete"]),
    "borderline-warming": ("warming close to the advisory threshold", "medium", "temperature slope and threshold proximity", ["threshold proximity increases uncertainty"]),
    "multi-zone-conflict": ("conflicting zone signals or mapping", "high", "zone disagreement and identity mapping", ["zone evidence conflicts"]),
    "sensor-drift-over-time": ("sensor calibration drift or offset", "medium", "sensor calibration trend and offset", ["drift can mimic a thermal trend"]),
    "gateway-delay": ("gateway ingestion delay", "medium", "gateway received timestamps and route segment", ["arrival time differs from event time"]),
    "battery-degradation": ("device battery degradation with evidence loss", "medium", "battery timeline and missing windows", ["device health reduces evidence completeness"]),
    "humidity-anomaly": ("humidity anomaly or condensation risk", "medium", "humidity sensor and condensation indicators", ["humidity does not establish a temperature breach"]),
    "late-arriving-data": ("late-arriving device evidence", "medium", "device and gateway timestamps", ["review window may be incomplete"]),
    "mixed-quality-evidence": ("mixed evidence quality", "high", "data quality evidence before thermal interpretation", ["strong and weak signals are combined"]),
}

TIMELINES = {
    "gateway-delay": "device event through gateway receipt window",
    "late-arriving-data": "device timestamp through review-window arrival",
    "door-open-warming": "30 minutes before and after the door event",
    "sensor-drift-over-time": "full synthetic calibration trend",
}


def _evidence_routes(case_id: str) -> dict[str, str]:
    routes = {
        "behaviorPrediction": f"/cases/{case_id}/behavior-prediction.json",
        "scenario": f"/scenario-library-v4/{case_id}.json",
        "evaluationRow": f"/cases/{case_id}/evaluation-row.json",
        "inspectionPlan": f"/cases/{case_id}/inspection-plan.json",
        "rootCauseAnalysis": f"/cases/{case_id}/root-cause-analysis.json",
    }
    if case_id in tuple(CASE_FEATURES)[:6]:
        routes.update({
            "reviewerWorkspace": f"/reviewer-workspace/{case_id}.json",
            "auditLedger": f"/cases/{case_id}/audit-ledger.json",
        })
    return routes


def get_inspection_plan(case_id: str) -> dict[str, Any]:
    if case_id not in CASE_GUIDANCE:
        raise KeyError(case_id)
    prediction = predict_case_behavior(case_id)
    root_cause, priority, primary, warnings = CASE_GUIDANCE[case_id]
    alternatives = [item["faultLabel"] for item in prediction.get("topAlternatives", [])]
    secondary = alternatives[:2] or ["neighboring synthetic evidence"]
    return {
        "phase": PHASE, "caseId": case_id, "syntheticOnly": True, "advisoryOnly": True,
        "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True,
        "stblPrediction": {
            "predictedBehaviorLabel": prediction.get("predictedBehaviorLabel"),
            "predictedFaultLabel": prediction.get("predictedFaultLabel"),
            "confidenceBand": prediction.get("confidenceBand"),
        },
        "likelyRootCause": root_cause,
        "rankedAlternateCauses": [
            {"cause": cause, "rank": rank, "source": "STBL distilled alternate"}
            for rank, cause in enumerate(alternatives, 1)
        ],
        "inspectionPriority": priority,
        "primaryInspectionTarget": primary,
        "secondaryInspectionTargets": secondary,
        "timelineWindowToInspect": TIMELINES.get(case_id, "synthetic evidence window and adjacent readings"),
        "dataQualityWarnings": warnings,
        "inspectionChecklist": [
            f"Confirm the case identity for {case_id}.",
            f"Inspect {primary}.",
            "Compare the primary evidence with neighboring synthetic evidence.",
            "Record missing, conflicting, or late evidence.",
            "Preserve deterministic findings for human review.",
        ],
        "humanReviewQuestions": [
            "Does the strongest evidence support the likely root cause?",
            "Which uncertainty could change the advisory interpretation?",
            "What additional synthetic evidence would resolve the conflict?",
            "Has the deterministic safety boundary been preserved?",
        ],
        "blockedOperationalActions": list(BLOCKED_ACTIONS),
        "evidenceRoutes": _evidence_routes(case_id),
        "safetyBoundary": {
            "syntheticOnly": True, "advisoryOnly": True, "humanReviewRequired": True,
            "notOperationalDisposition": True, "deterministicRulesAuthoritative": True,
        },
    }


def get_root_cause_analysis(case_id: str) -> dict[str, Any]:
    plan = get_inspection_plan(case_id)
    prediction = predict_case_behavior(case_id)
    summary = prediction.get("featureVectorSummary", {})
    evidence_for = [f"{name}={value}" for name, value in list(summary.items())[:4]]
    evidence_against = [
        "The evidence is synthetic and cannot establish field conditions.",
        "Distilled centroid accuracy is lower than the offline neural benchmark.",
    ]
    return {
        "phase": PHASE, "caseId": case_id, "syntheticOnly": True, "advisoryOnly": True,
        "likelyRootCause": plan["likelyRootCause"],
        "confidenceBand": prediction.get("confidenceBand", "unavailable"),
        "evidenceFor": evidence_for,
        "evidenceAgainst": evidence_against,
        "uncertaintyDrivers": plan["dataQualityWarnings"] + ["human interpretation remains required"],
        "topAlternatives": prediction.get("topAlternatives", []),
        "whyThisMatters": "The likely cause narrows human inspection without making an operational decision.",
        "whatToInspectFirst": plan["primaryInspectionTarget"],
        "whatNotToDo": "Do not execute release, quarantine, discard, reroute, or outbound messaging from this advisory.",
        "deterministicBoundary": "Deterministic safety rules remain authoritative.",
        "humanReviewRequired": True,
    }


def get_inspection_engine_payload() -> dict[str, Any]:
    plans = [get_inspection_plan(case_id) for case_id in CASE_GUIDANCE]
    return {
        "phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True,
        "realWorldDataUsed": False, "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False,
        "deterministicRulesAuthoritative": True, "autonomousActionsAllowed": False,
        "databaseRequired": False, "persistenceEnabled": False, "stblIntegrated": True,
        "supportedCaseCount": len(plans), "inspectionPlans": plans,
        "inspectionOutputs": [
            "likely root cause", "ranked alternate causes", "evidence supporting each cause",
            "evidence against each cause", "confidence band", "first sensor/zone/pallet/gateway to inspect",
            "timeline window to inspect", "data quality warnings", "human review questions",
            "blocked operational actions",
        ],
        "routeMap": {
            "inspectionEngine": "/inspection-engine", "behaviorPredictor": "/behavior-predictor",
            "decisionSimulator": "/decision-simulator", "reviewerWorkspace": "/reviewer-workspace",
            "auditLedger": "/audit-ledger", "evaluationMatrixV2": "/evaluation-matrix-v2",
            "scenarioLibraryV4": "/scenario-library-v4", "productionGapAnalysis": "/production-gap-analysis",
        },
    }


def render_inspection_engine_html() -> str:
    payload = get_inspection_engine_payload()
    cards = "".join(
        f'<article><p class="priority">{html.escape(plan["inspectionPriority"])}</p><h2>{html.escape(plan["caseId"])}</h2>'
        f'<p><strong>Likely root cause:</strong> {html.escape(plan["likelyRootCause"])}</p>'
        f'<p><strong>Inspect first:</strong> {html.escape(plan["primaryInspectionTarget"])}</p>'
        f'<a href="/cases/{html.escape(plan["caseId"])}/inspection-plan.json">Inspection plan</a> '
        f'<a href="/cases/{html.escape(plan["caseId"])}/root-cause-analysis.json">Root cause JSON</a></article>'
        for plan in payload["inspectionPlans"]
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Root Cause and Inspection Engine</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1160px,100%);margin:auto;padding:24px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.hero{{border-left:6px solid var(--accent);padding:clamp(24px,5vw,52px);background:var(--surface);border-radius:var(--radius)}}h1{{font-size:clamp(38px,6vw,66px);line-height:1;letter-spacing:-.04em;max-width:850px;margin:0 0 18px}}.hero p{{color:var(--muted);max-width:65ch}}.badges{{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0 40px}}.badges span{{border:1px solid var(--line);border-radius:8px;padding:6px 9px;color:var(--muted);font-size:13px}}.grid{{display:grid;grid-template-columns:1.2fr .8fr;gap:10px}}article{{background:var(--surface);border-top:3px solid var(--accent);padding:18px;min-height:220px}}article:nth-child(3n){{grid-column:1/-1;min-height:170px}}article h2{{text-transform:capitalize;margin:8px 0}}.priority{{color:var(--accent);font-weight:750;text-transform:uppercase}}section>p{{color:var(--muted);max-width:70ch}}@media(max-width:760px){{main{{padding:14px 12px 44px}}.grid{{grid-template-columns:1fr}}article:nth-child(3n){{grid-column:auto}}h1{{font-size:42px}}}}
    </style></head><body><main><section class="hero"><h1>What is wrong? What should a human inspect?</h1><p>STBL predictions and deterministic evidence narrow the first inspection target without making an operational decision.</p><a href="/behavior-predictor">Open behavior predictor</a></section><div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>No autonomous operations</span><span>Human review required</span><span>Deterministic rules authoritative</span></div><section><h2>Inspection recommendations</h2><p>Each case shows a likely root cause, confidence context, and the first evidence target for a human reviewer.</p><div class="grid">{cards}</div></section></main></body></html>'''


get_inspection_plan_payload = get_inspection_plan
get_root_cause_analysis_payload = get_root_cause_analysis
