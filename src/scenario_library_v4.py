"""Expanded synthetic scenario catalog backed by the Phase 21 artifact."""

from __future__ import annotations

import html
from typing import Any

from expanded_benchmark_v2 import ARTIFACT_PATH, load_expanded_benchmark_artifact

PHASE = "Phase 22 - Expanded Scenario Library v4"

CASE_DETAILS = {
    "no-excursion-control": ("No-Excursion Control", "stable control readings", "accept stable, complete evidence", "confirm stable multi-sensor agreement"),
    "single-sensor-spike": ("Single-Sensor Spike", "one isolated sensor spike", "preserve the outlier and flag conflicting evidence", "avoid treating an isolated spike as zone consensus"),
    "multi-sensor-confirmed-warming": ("Multi-Sensor Confirmed Warming", "sustained warming across sensors", "accept consistent readings for review", "recognize multi-sensor agreement"),
    "unresolved-mapping-risk": ("Unresolved Mapping Risk", "readings with unresolved location mapping", "surface the mapping gap", "withhold location consensus until mapping is resolved"),
    "door-open-warming": ("Door-Open Warming", "warming aligned with a door-open interval", "retain temperature and door context", "compare warming across neighboring sensors"),
    "dropout-weak-signal": ("Dropout and Weak Signal", "intermittent readings and weak signal", "lower confidence and expose missing evidence", "limit consensus when coverage is sparse"),
    "borderline-warming": ("Borderline Warming", "persistent near-threshold warming", "retain borderline evidence for review", "evaluate persistence without overstating agreement"),
    "multi-zone-conflict": ("Multi-Zone Conflict", "zones showing conflicting trends", "preserve each zone's evidence", "surface disagreement instead of merging it"),
    "sensor-drift-over-time": ("Sensor Drift Over Time", "gradual sensor drift", "flag temporal drift for inspection", "compare the drifting sensor with stable neighbors"),
    "gateway-delay": ("Gateway Delay", "delayed gateway delivery", "distinguish event time from arrival time", "avoid inferring simultaneity from delayed arrivals"),
    "battery-degradation": ("Battery Degradation", "declining battery and signal quality", "expose device-health degradation", "reduce confidence when coverage becomes unreliable"),
    "humidity-anomaly": ("Humidity Anomaly", "humidity anomaly without assumed temperature breach", "retain humidity as contextual evidence", "keep humidity and temperature consensus distinct"),
    "late-arriving-data": ("Late-Arriving Data", "readings arriving after the review window", "mark evidence as late and preserve timestamps", "recompute review context without silent replacement"),
    "mixed-quality-evidence": ("Mixed-Quality Evidence", "combined strong, weak, and missing signals", "label quality differences explicitly", "weight agreement by evidence quality"),
}

SAFETY_BOUNDARIES = {
    "syntheticOnly": True,
    "advisoryOnly": True,
    "deterministicRulesAuthoritative": True,
    "autonomousActionsAllowed": False,
    "humanReviewRequiredForOperationalUse": True,
    "evidenceScope": "synthetic benchmark/demo evidence only",
}
REVIEW_WORKSPACE_CASE_IDS = {
    "no-excursion-control", "single-sensor-spike", "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk", "door-open-warming", "dropout-weak-signal",
}


def _case_from_coverage(row: dict[str, Any]) -> dict[str, Any]:
    family = str(row["scenario"])
    case_id = family.replace("_", "-")
    title, pattern, quality, consensus = CASE_DETAILS[case_id]
    positive = float(row.get("positiveRate", 0)) > 0
    route_links = {
        "scenario": f"/scenario-library-v4/{case_id}.json",
        "expandedEvidence": f"/cases/{case_id}/expanded-evidence.json",
        "benchmark": "/expanded-benchmark",
    }
    if case_id in REVIEW_WORKSPACE_CASE_IDS:
        route_links["reviewerWorkspace"] = f"/reviewer-workspace/{case_id}.json"
    return {
        "caseId": case_id,
        "title": title,
        "scenarioFamily": family,
        "syntheticPattern": pattern,
        "expectedDataQualityBehavior": quality,
        "expectedConsensusBehavior": consensus,
        "expectedSersBehavior": "surface an advisory risk signal for human review" if positive else "retain a low-concern advisory posture while preserving evidence gaps",
        "expectedHumanReviewBehavior": "inspect the synthetic evidence and record review context; no operational action is executed",
        "expectedFireworksBehavior": "optional explanation support with deterministic fallback; never required for this route",
        "blockedActions": ["release blocked", "quarantine blocked", "discard blocked", "reroute blocked", "outbound messaging blocked"],
        "routeLinks": route_links,
        "safetyBoundaries": SAFETY_BOUNDARIES,
        "benchmarkEvidence": {
            "rows": row.get("rows"),
            "positiveRate": row.get("positiveRate"),
            "averageAdvisoryScore": row.get("avgSersStyleScore"),
        },
    }


def get_scenario_library_payload() -> dict[str, Any]:
    artifact = load_expanded_benchmark_artifact()
    cases = [_case_from_coverage(row) for row in artifact["scenarioCoverage"]] if artifact else []
    return {
        "phase": PHASE,
        "status": "READY",
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
        "scenarioCount": len(cases),
        "artifactSource": ARTIFACT_PATH,
        "artifactAvailable": artifact is not None,
        "scenarioFamilies": [case["scenarioFamily"] for case in cases],
        "scenarios": cases,
        "safetyBoundaries": SAFETY_BOUNDARIES,
        "routeMap": {
            "scenarioLibraryV4": "/scenario-library-v4",
            "expandedBenchmark": "/expanded-benchmark",
            "evaluationMatrixV2": "/evaluation-matrix-v2",
            "reviewerWorkspace": "/reviewer-workspace",
        },
    }


def get_expanded_scenario_payload(case_id: str) -> dict[str, Any]:
    for case in get_scenario_library_payload()["scenarios"]:
        if case["caseId"] == case_id:
            return case
    raise KeyError(f"Unknown expanded scenario: {case_id}")


def render_scenario_library_html() -> str:
    payload = get_scenario_library_payload()
    cards = "".join(
        f'<article class="card"><h2>{html.escape(case["title"])}</h2>'
        f'<p>{html.escape(case["syntheticPattern"])}</p>'
        f'<a class="button" href="{case["routeLinks"]["scenario"]}">Scenario JSON</a> '
        f'<a class="button" href="{case["routeLinks"]["expandedEvidence"]}">Expanded evidence</a></article>'
        for case in payload["scenarios"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Expanded Scenario Library v4</title>
<style>body{{margin:0;background:#07131b;color:#edf7f5;font:16px system-ui,sans-serif}}main{{max-width:1160px;margin:auto;padding:28px 18px 48px}}a{{color:#8ee8cb}}.badges,.grid{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}}.badge{{border:1px solid #347263;border-radius:999px;padding:7px 11px}}.card{{flex:1 1 280px;background:#102631;border:1px solid #244852;border-radius:12px;padding:16px}}.button{{display:inline-block;border:1px solid #347263;border-radius:8px;padding:7px 9px;margin:4px 2px}}@media(max-width:600px){{main{{padding:20px 12px}}}}</style>
</head><body><main><p><a href="/">ColdChain Sentinel</a> / <a href="/scenario-library-v4.json">JSON</a></p>
<h1>Expanded Scenario Library v4</h1><p>Expanded scenarios are synthetic benchmark/demo evidence only. They support human review and do not execute operational actions.</p>
<div class="badges"><span class="badge">Synthetic-only</span><span class="badge">Advisory-only</span><span class="badge">Runtime GPU required: false</span><span class="badge">Runtime external service required: false</span><span class="badge">Deterministic rules authoritative</span></div>
<p>{payload["scenarioCount"]} scenarios loaded from the validated Phase 21 artifact.</p><section class="grid">{cards}</section>
</main></body></html>"""


get_scenario_library_v4_payload = get_scenario_library_payload
get_scenario_case_payload = get_expanded_scenario_payload
render_scenario_library_v4_html = render_scenario_library_html
