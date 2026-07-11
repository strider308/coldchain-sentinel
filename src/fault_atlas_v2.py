from __future__ import annotations

import html
from typing import Any

from algorithm_console_v2 import FAULT_CATEGORIES, get_error_coverage_payload
from behavior_predictor_v2 import load_stbl_artifacts
from inspection_engine_v2 import BLOCKED_ACTIONS
from ui_design_system_v2 import unified_page


PHASE = "Phase 41 - Fault Universe Error Atlas"
CATEGORY_IDS = {
    "thermal behavior faults": "thermal_behavior",
    "environmental exposure faults": "environmental_exposure",
    "handling event faults": "handling_event",
    "sensor/device faults": "sensor_device_fault",
    "network/gateway faults": "network_gateway_fault",
    "data quality faults": "data_quality_fault",
    "identity/mapping faults": "identity_mapping_fault",
    "mixed evidence faults": "mixed_evidence_fault",
}
EXAMPLE_CASES = {
    "normal_stable": "no-excursion-control", "slow_warming": "borderline-warming",
    "single_sensor_false_spike": "single-sensor-spike", "multi_sensor_confirmed_warming": "multi-sensor-confirmed-warming",
    "door_open_warming": "door-open-warming", "humidity_anomaly": "humidity-anomaly",
    "condensation_risk": "humidity-anomaly", "sensor_drift": "sensor-drift-over-time",
    "calibration_offset": "sensor-drift-over-time", "missing_readings": "dropout-weak-signal",
    "dropout_window": "dropout-weak-signal", "late_arriving_data": "late-arriving-data",
    "gateway_delay": "gateway-delay", "weak_signal": "dropout-weak-signal",
    "low_battery": "battery-degradation", "pallet_zone_mapping_conflict": "multi-zone-conflict",
    "container_mismatch": "multi-zone-conflict", "mixed_quality_evidence": "mixed-quality-evidence",
    "unresolved_mapping_risk": "unresolved-mapping-risk",
}


def _category_for(fault_id: str) -> str:
    for category, faults in FAULT_CATEGORIES.items():
        if fault_id in faults:
            return CATEGORY_IDS[category]
    raise KeyError(fault_id)


def _false_positive(category: str) -> str:
    return {
        "thermal_behavior": "A short isolated change without sustained multi-sensor agreement.",
        "environmental_exposure": "Environmental context without a confirmed thermal effect.",
        "handling_event": "A recorded event that does not alter sensor quality or thermal evidence.",
        "sensor_device_fault": "A real zone change that resembles one drifting device.",
        "network_gateway_fault": "Normal batching or clock skew within an accepted arrival window.",
        "data_quality_fault": "Intentional replay or deduplication behavior in a synthetic fixture.",
        "identity_mapping_fault": "A valid remap that has not yet propagated to every record.",
        "mixed_evidence_fault": "One weak signal inside otherwise complete and consistent evidence.",
    }[category]


def _fault_detail(fault_id: str) -> dict[str, Any]:
    artifacts = load_stbl_artifacts()
    rules = artifacts.get("rules", {})
    prototypes = rules.get("faultPrototypes", {})
    behavior_map = rules.get("faultToBehavior", {})
    if fault_id not in prototypes or fault_id not in behavior_map:
        raise KeyError(fault_id)
    category = _category_for(fault_id)
    prototype = prototypes[fault_id]["centroid"]
    stats = rules["globalFeatureStats"]
    feature_signals = sorted(
        ({"feature": feature, "centroid": round(float(value), 4), "standardizedDifference": round(abs(float(value) - float(stats[feature]["mean"])) / max(float(stats[feature]["std"]), 1e-9), 4)} for feature, value in prototype.items()),
        key=lambda row: row["standardizedDifference"], reverse=True,
    )[:6]
    example = EXAMPLE_CASES.get(fault_id)
    prediction_route = f"/cases/{example}/behavior-prediction.json" if example else "/behavior-predictor"
    inspection_route = f"/cases/{example}/inspection-plan.json" if example else "/inspection-engine"
    root_route = f"/cases/{example}/root-cause-analysis.json" if example else "/inspection-engine"
    inspect_first = next(row["inspectionTarget"] for row in get_error_coverage_payload()["faultCoverageRows"] if row["faultLabel"] == fault_id)
    return {
        "phase": PHASE, "faultId": fault_id, "behaviorLabel": behavior_map[fault_id],
        "category": category, "syntheticOnly": True, "advisoryOnly": True,
        "whatGoesWrong": f"The synthetic evidence matches the {fault_id.replace('_', ' ')} fault family.",
        "readingPattern": "Strongest prototype signals: " + ", ".join(row["feature"] for row in feature_signals[:3]) + ".",
        "featureSignals": feature_signals, "inspectFirst": inspect_first,
        "secondaryInspectionTargets": [row["feature"] for row in feature_signals[1:4]],
        "commonFalsePositive": _false_positive(category), "exampleCaseId": example,
        "routeLinks": {"faultDetail": f"/fault-atlas/{fault_id}.json", "behaviorPrediction": prediction_route, "inspectionPlan": inspection_route, "rootCause": root_route, "algorithmConsole": "/algorithm-console"},
        "blockedOperationalActions": list(BLOCKED_ACTIONS),
        "safetyBoundary": {"syntheticOnly": True, "advisoryOnly": True, "notOperationalDisposition": True, "deterministicRulesAuthoritative": True},
    }


def get_fault_detail_payload(fault_id: str) -> dict[str, Any]:
    return _fault_detail(fault_id)


def get_fault_atlas_coverage_payload() -> dict[str, Any]:
    rows = [_fault_detail(fault) for faults in FAULT_CATEGORIES.values() for fault in faults]
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "faultCount": len(rows), "categoryCounts": {category: sum(row["category"] == category for row in rows) for category in CATEGORY_IDS.values()},
        "faults": [row["faultId"] for row in rows],
    }


def get_fault_atlas_payload() -> dict[str, Any]:
    details = [_fault_detail(fault) for faults in FAULT_CATEGORIES.values() for fault in faults]
    rows = [{
        "faultId": item["faultId"], "behaviorLabel": item["behaviorLabel"], "category": item["category"],
        "whatGoesWrong": item["whatGoesWrong"], "readingPattern": item["readingPattern"],
        "topFeatures": [row["feature"] for row in item["featureSignals"][:3]],
        "inspectFirst": item["inspectFirst"], "commonFalsePositive": item["commonFalsePositive"],
        "behaviorPredictionRoute": item["routeLinks"]["behaviorPrediction"],
        "inspectionPlanRoute": item["routeLinks"]["inspectionPlan"], "rootCauseRoute": item["routeLinks"]["rootCause"],
    } for item in details]
    return {
        "phase": PHASE, "status": "READY", "syntheticOnly": True, "advisoryOnly": True,
        "realWorldDataUsed": False, "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False,
        "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True,
        "dependenciesAdded": False, "externalCallsRequired": False,
        "faultCount": len(rows), "featureCount": 19,
        "coverageBoundary": {"projectDefinedSyntheticFaultUniverse": True, "exhaustiveExternalCoverageClaimed": False, "regulatedValidationClaimed": False},
        "categoryGroups": list(CATEGORY_IDS.values()), "faultRows": rows,
        "routeMap": {"faultAtlas": "/fault-atlas", "coverage": "/fault-atlas/coverage.json", "behaviorPredictor": "/behavior-predictor", "inspectionEngine": "/inspection-engine", "caseWalkthroughs": "/case-walkthroughs"},
    }


@unified_page
def render_fault_atlas_html() -> str:
    payload = get_fault_atlas_payload()
    chips = "".join(f'<span>{html.escape(category)}: {sum(row["category"] == category for row in payload["faultRows"])}</span>' for category in payload["categoryGroups"])
    rows = "".join(
        f'<tr><th scope="row"><a href="/fault-atlas/{html.escape(row["faultId"])}.json">{html.escape(row["faultId"])}</a></th><td>{html.escape(row["behaviorLabel"])}</td><td>{html.escape(row["category"])}</td><td>{html.escape(row["inspectFirst"])}</td><td>{html.escape(", ".join(row["topFeatures"]))}</td></tr>'
        for row in payload["faultRows"]
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fault Universe Error Atlas</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1240px,100%);margin:auto;padding:28px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}h1{{font-size:46px;line-height:1.05;letter-spacing:-.035em;text-wrap:balance;margin:0 0 14px}}.intro{{max-width:72ch;color:var(--muted)}}.metrics{{display:flex;gap:28px;border-block:1px solid var(--line);padding:18px 0;margin:26px 0}}.metrics strong{{display:block;color:var(--accent);font-size:28px}}.chips,.routes{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 28px}}.chips span,.routes a{{border:1px solid var(--line);border-radius:8px;padding:7px 10px}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius)}}table{{width:100%;border-collapse:collapse;min-width:960px}}th,td{{text-align:left;padding:11px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-weight:700}}td{{color:var(--muted)}}tr:last-child th,tr:last-child td{{border-bottom:0}}.boundary{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px;margin-top:32px}}@media(max-width:760px){{main{{padding:18px 12px 44px}}h1{{font-size:36px}}.metrics{{gap:18px}}.table-wrap{{border-radius:8px}}}}
    </style></head><body><main><header><h1>Fault Universe / Error Atlas</h1><p class="intro">Thirty-eight project-defined synthetic fault prototypes connect reading patterns, behavior labels, and the first human inspection target.</p></header><div class="chips"><span>Synthetic-only</span><span>Advisory-only</span><span>Deterministic rules authoritative</span></div><section class="metrics"><div><strong>38</strong><span>fault prototypes</span></div><div><strong>19</strong><span>weighted features</span></div><div><strong>8</strong><span>coverage categories</span></div></section><div class="chips">{chips}</div><section><h2>Fault coverage</h2><div class="table-wrap"><table><thead><tr><th>Fault</th><th>Behavior</th><th>Category</th><th>Inspect first</th><th>Top features</th></tr></thead><tbody>{rows}</tbody></table></div></section><section class="boundary"><h2>Coverage boundary</h2><p>This atlas documents a project-defined synthetic fault universe. It does not claim exhaustive external coverage or regulated validation.</p></section><nav class="routes"><a href="/behavior-predictor">Behavior Predictor</a><a href="/inspection-engine">Inspection Engine</a><a href="/case-walkthroughs">Case Walkthroughs</a><a href="/fault-atlas/coverage.json">Coverage JSON</a></nav></main></body></html>'''
