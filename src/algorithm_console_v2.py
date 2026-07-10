from __future__ import annotations

import html
from typing import Any

from behavior_predictor_v2 import (
    ARTIFACT_PATHS,
    CASE_TARGETS,
    get_behavior_predictor_payload,
    load_stbl_artifacts,
)
from inspection_engine_v2 import get_inspection_engine_payload


PHASE = "Phase 37 - Algorithm Evidence Console"

FEATURE_CONTEXT = {
    "temperatureSlopeCPerHour": ("Rate of thermal change.", "Inspect the thermal timeline and threshold proximity."),
    "temperatureVolatilityC": ("Short-window temperature variation.", "Compare spikes with neighboring sensors."),
    "sensorDisagreementC": ("Difference among sensors in one zone.", "Inspect the suspect sensor and its peers."),
    "zoneDisagreementC": ("Difference across synthetic zones.", "Inspect zone mapping and cross-zone context."),
    "humiditySlopePercentPerHour": ("Rate of humidity change.", "Inspect humidity and condensation indicators."),
    "doorOpenCount": ("Door events in the evidence window.", "Compare door timestamps with warming."),
    "shockEventCount": ("Recorded synthetic shock events.", "Inspect handling-event timing."),
    "tiltEventCount": ("Recorded synthetic tilt events.", "Inspect handling and orientation evidence."),
    "lightExposureCount": ("Recorded synthetic light events.", "Inspect enclosure or door context."),
    "weakSignalShare": ("Share of weak-signal readings.", "Inspect gateway and signal coverage."),
    "lowBatteryShare": ("Share of low-battery readings.", "Inspect device health and missing windows."),
    "missingReadingCount": ("Missing readings in the window.", "Inspect coverage before thermal interpretation."),
    "duplicateReadingCount": ("Duplicate readings in the window.", "Inspect ingestion and identity evidence."),
    "outOfOrderCount": ("Out-of-order readings.", "Compare device and gateway timestamps."),
    "lateArrivalCount": ("Readings received after event time.", "Inspect arrival delay and review-window completeness."),
    "maxIngestionDelaySeconds": ("Largest ingestion delay.", "Inspect gateway timestamps and route segment."),
    "mappingConfidenceMin": ("Lowest identity-mapping confidence.", "Inspect pallet-zone identity mapping."),
    "calibrationOffsetC": ("Estimated calibration offset.", "Inspect sensor drift and calibration trend."),
    "qualityScore": ("Aggregate synthetic evidence quality.", "Resolve quality warnings before interpretation."),
}

FAULT_CATEGORIES = {
    "thermal behavior faults": ["normal_stable", "slow_warming", "rapid_temperature_spike", "single_sensor_false_spike", "multi_sensor_confirmed_warming", "cooling_or_freezing_risk", "door_open_warming", "reefer_setpoint_mismatch", "reefer_alarm_active", "thermal_stratification", "hot_wall_or_roof_exposure"],
    "environmental exposure faults": ["humidity_anomaly", "condensation_risk", "light_exposure"],
    "handling event faults": ["shock_event", "vibration_event", "tilt_event"],
    "sensor/device faults": ["sensor_drift", "calibration_offset", "stuck_sensor", "noisy_sensor", "impossible_physics", "low_battery", "firmware_mismatch"],
    "network/gateway faults": ["late_arriving_data", "gateway_delay", "weak_signal", "clock_drift", "sequence_reset"],
    "data quality faults": ["duplicate_readings", "missing_readings", "dropout_window", "out_of_order_readings"],
    "identity/mapping faults": ["sensor_id_collision", "pallet_zone_mapping_conflict", "container_mismatch", "unresolved_mapping_risk"],
    "mixed evidence faults": ["mixed_quality_evidence"],
}


def _fault_target(fault: str, category: str) -> str:
    direct = {
        "door_open_warming": CASE_TARGETS["door-open-warming"],
        "single_sensor_false_spike": CASE_TARGETS["single-sensor-spike"],
        "multi_sensor_confirmed_warming": CASE_TARGETS["multi-sensor-confirmed-warming"],
        "gateway_delay": CASE_TARGETS["gateway-delay"],
        "late_arriving_data": CASE_TARGETS["late-arriving-data"],
        "low_battery": CASE_TARGETS["battery-degradation"],
        "humidity_anomaly": CASE_TARGETS["humidity-anomaly"],
        "unresolved_mapping_risk": CASE_TARGETS["unresolved-mapping-risk"],
        "mixed_quality_evidence": CASE_TARGETS["mixed-quality-evidence"],
    }
    defaults = {
        "thermal behavior faults": "thermal timeline and neighboring sensors",
        "environmental exposure faults": "environmental sensor and event timeline",
        "handling event faults": "handling event timeline",
        "sensor/device faults": "sensor health and calibration evidence",
        "network/gateway faults": "gateway, signal, and timestamp evidence",
        "data quality faults": "ingestion quality and reading sequence",
        "identity/mapping faults": "device, pallet, and zone identity mapping",
        "mixed evidence faults": "data quality before thermal interpretation",
    }
    return direct.get(fault, defaults[category])


def get_feature_weights_payload() -> dict[str, Any]:
    artifacts = load_stbl_artifacts()
    weights = artifacts.get("rules", {}).get("featureWeights", {})
    rows = [
        {"feature": feature, "weight": weight, "interpretation": FEATURE_CONTEXT[feature][0], "inspectionMeaning": FEATURE_CONTEXT[feature][1]}
        for feature, weight in sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "featureWeightCount": len(rows), "featureWeights": rows,
        "topWeightedFeatures": rows[:5],
        "safetyBoundary": "Weights describe synthetic distilled evidence and do not determine operational disposition.",
    }


def get_error_coverage_payload() -> dict[str, Any]:
    artifacts = load_stbl_artifacts()
    rules = artifacts.get("rules", {})
    behavior_map = rules.get("faultToBehavior", {})
    prototypes = rules.get("faultPrototypes", {})
    rows = []
    category_rows = []
    for category, faults in FAULT_CATEGORIES.items():
        supported = [fault for fault in faults if fault in behavior_map]
        category_rows.append({"category": category, "faultCount": len(supported), "faults": supported})
        rows.extend({
            "faultLabel": fault, "behaviorLabel": behavior_map[fault],
            "prototypeAvailable": fault in prototypes,
            "inspectionTarget": _fault_target(fault, category),
            "supportedByDistilledRuntime": fault in prototypes,
            "routeLinks": {"coverage": "/algorithm-console/error-coverage.json", "inspectionEngine": "/inspection-engine"},
        } for fault in supported)
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "supportedFaultCount": len(rows), "categoryCoverage": category_rows,
        "faultCoverageRows": rows,
        "coverageBoundary": {
            "projectDefinedSyntheticFaultUniverse": True,
            "exhaustiveFieldCoverageClaimed": False,
            "externalValidationClaimed": False,
        },
    }


def get_prediction_table_payload() -> dict[str, Any]:
    predictor = get_behavior_predictor_payload()
    rows = [{
        "caseId": item["caseId"], "predictedBehaviorLabel": item["predictedBehaviorLabel"],
        "predictedFaultLabel": item["predictedFaultLabel"], "confidenceBand": item["confidenceBand"],
        "primaryInspectionTarget": item["primaryInspectionTarget"], "topAlternatives": item["topAlternatives"],
        "humanReviewRequired": item["humanReviewRequired"],
        "inspectionPlanRoute": f'/cases/{item["caseId"]}/inspection-plan.json',
        "rootCauseRoute": f'/cases/{item["caseId"]}/root-cause-analysis.json',
        "behaviorPredictionRoute": f'/cases/{item["caseId"]}/behavior-prediction.json',
    } for item in predictor.get("casePredictions", [])]
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True, "predictionRows": rows,
        "summary": {
            "caseCount": len(rows), "humanReviewRequiredCount": sum(row["humanReviewRequired"] for row in rows),
            "lowConfidenceCount": sum(row["confidenceBand"] == "low" for row in rows),
            "mappingRiskCount": sum("mapping" in row["predictedFaultLabel"] for row in rows),
            "dataQualityRiskCount": sum(row["predictedBehaviorLabel"] in ("data_quality_fault", "evidence_insufficient") for row in rows),
        },
    }


def get_weaknesses_payload() -> dict[str, Any]:
    training = load_stbl_artifacts().get("training", {})
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "weakFaultsForNextDataExpansion": training.get("weakFaultsForNextDataExpansion", []),
        "uncertaintyPatterns": ["similar fault families", "data quality overlap", "mapping ambiguity", "subtle thermal drift", "mixed evidence windows"],
        "mitigation": ["show top alternatives", "require human review", "route to inspection engine", "keep deterministic rules authoritative"],
        "noGoBoundary": ["no operational disposition", "no automated action", "no external validation claim"],
    }


def get_runtime_boundary_payload() -> dict[str, Any]:
    artifacts = load_stbl_artifacts()
    return {
        "phase": PHASE, "syntheticOnly": True, "advisoryOnly": True,
        "runtimeGpuRequired": False, "runtimePyTorchRequired": False,
        "runtimeExternalServiceRequired": False, "stdlibOnly": True,
        "neuralModelRuntimeLoaded": False,
        "distilledRulesRuntimeLoaded": artifacts["artifactAvailable"],
        "artifactsUsed": [path.rsplit("/", 1)[-1] for path in ARTIFACT_PATHS.values()],
        "safetyBoundary": {"advisoryOnly": True, "humanReviewRequired": True, "deterministicRulesAuthoritative": True},
    }


def get_algorithm_console_payload() -> dict[str, Any]:
    predictor = get_behavior_predictor_payload()
    inspection = get_inspection_engine_payload()
    available = predictor["artifactAvailable"]
    return {
        "phase": PHASE, "status": "READY" if available else "ARTIFACT_UNAVAILABLE",
        "algorithmName": "STBL - Sentinel Thermal Behavior Learner",
        "syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False,
        "realCustomerDataUsed": False, "realShipmentDataUsed": False,
        "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False,
        "runtimePyTorchRequired": False, "notebookRequiredAtRuntime": False,
        "deterministicRulesAuthoritative": True, "autonomousActionsAllowed": False,
        "databaseRequired": False, "persistenceEnabled": False,
        "artifactAvailable": available, "predictorIntegrated": predictor["predictorAvailable"],
        "inspectionEngineIntegrated": available and inspection["stblIntegrated"],
        "trainingRows": predictor["trainingRows"], "faultPrototypeCount": predictor["faultPrototypeCount"],
        "featureWeightCount": predictor["featureWeightCount"], "supportedFaultCount": predictor["supportedFaultCount"],
        "supportedFeatureCount": predictor["supportedFeatureCount"],
        "neuralMetrics": predictor["neuralMetrics"], "distilledMetrics": predictor["distilledMetrics"],
        "distilledMethod": predictor["distilledMethod"],
        "evidenceSections": ["offline training summary", "runtime distillation", "feature weights", "fault coverage", "case prediction table", "uncertainty and weak classes", "safety boundaries", "inspection integration"],
        "routeMap": {
            "algorithmConsole": "/algorithm-console", "featureWeights": "/algorithm-console/feature-weights.json",
            "errorCoverage": "/algorithm-console/error-coverage.json", "predictionTable": "/algorithm-console/prediction-table.json",
            "weaknesses": "/algorithm-console/weaknesses.json", "runtimeBoundary": "/algorithm-console/runtime-boundary.json",
            "behaviorPredictor": "/behavior-predictor", "inspectionEngine": "/inspection-engine",
            "dashboardStrategy": "/dashboard-strategy", "commandCenter": "/command-center",
        },
    }


def render_algorithm_console_html() -> str:
    payload = get_algorithm_console_payload()
    features = get_feature_weights_payload()["topWeightedFeatures"]
    coverage = get_error_coverage_payload()
    predictions = get_prediction_table_payload()
    weaknesses = get_weaknesses_payload()
    feature_cards = "".join(f'<article><strong>{html.escape(row["feature"])}</strong><span>{row["weight"]}</span><p>{html.escape(row["interpretation"])}</p></article>' for row in features)
    prediction_cards = "".join(f'<article><strong>{html.escape(row["caseId"])}</strong><p>{html.escape(row["predictedFaultLabel"])} / {html.escape(row["confidenceBand"])}</p><a href="{html.escape(row["inspectionPlanRoute"])}">Inspect plan</a></article>' for row in predictions["predictionRows"][:6])
    weak_rows = "".join(f'<li><strong>{html.escape(row["fault"])}</strong><span>{float(row["accuracy"])*100:.2f}% synthetic test accuracy</span></li>' for row in weaknesses["weakFaultsForNextDataExpansion"][:5])
    n, d = payload["neuralMetrics"], payload["distilledMetrics"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Algorithm Evidence Console</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--surface2:#122722;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1180px,100%);margin:auto;padding:24px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.hero{{display:grid;grid-template-columns:1.25fr .75fr;gap:14px}}.hero>div{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:clamp(24px,5vw,50px)}}h1{{font-size:clamp(42px,6vw,70px);line-height:1;letter-spacing:-.045em;margin:0 0 18px}}.hero p,.note{{color:var(--muted);max-width:62ch}}.hero .facts{{background:var(--accent);color:#07110f;display:grid;grid-template-columns:1fr 1fr;gap:18px}}.fact strong{{display:block;font-size:28px}}.fact span{{font-size:13px}}.badges,.routes{{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0 40px}}.badges span,.routes a{{border:1px solid var(--line);border-radius:8px;padding:7px 10px;color:var(--muted)}}section{{margin-top:44px}}.strip{{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}.strip article{{padding:16px;border-right:1px solid var(--line);min-height:150px}}.strip article:last-child{{border:0}}.strip strong,.strip span{{display:block;word-break:break-word}}.strip span{{color:var(--accent);font-size:24px}}.predictions{{display:grid;grid-template-columns:1.2fr .8fr;gap:10px}}.predictions article{{background:var(--surface);border-top:3px solid var(--accent);padding:17px;min-height:140px}}.weak{{display:grid;grid-template-columns:.8fr 1.2fr;gap:16px;background:var(--surface2);border-radius:var(--radius);padding:24px}}.weak ul{{margin:0;padding:0;list-style:none}}.weak li{{display:flex;justify-content:space-between;gap:14px;padding:8px 0;border-bottom:1px solid var(--line)}}.boundary{{border-left:6px solid var(--accent);background:var(--surface);padding:24px;border-radius:var(--radius)}}@media(max-width:780px){{main{{padding:14px 12px 44px}}.hero,.weak{{grid-template-columns:1fr}}.strip,.predictions{{grid-template-columns:1fr}}.strip article{{border:0;border-bottom:1px solid var(--line)}}h1{{font-size:44px}}}}
    </style></head><body><main><section class="hero"><div><h1>Algorithm Evidence Console</h1><p>See what STBL learned, how it performs, where it is uncertain, and why runtime prediction stays transparent.</p></div><div class="facts"><div class="fact"><strong>171,000</strong><span>synthetic rows</span></div><div class="fact"><strong>38</strong><span>fault prototypes</span></div><div class="fact"><strong>19</strong><span>feature weights</span></div><div class="fact"><strong>{float(n.get("faultAccuracy",0))*100:.2f}%</strong><span>neural synthetic fault accuracy</span></div><div class="fact"><strong>{float(n.get("behaviorAccuracy",0))*100:.2f}%</strong><span>neural synthetic behavior accuracy</span></div><div class="fact"><strong>{float(d.get("faultAccuracy",0))*100:.2f}%</strong><span>distilled synthetic fault accuracy</span></div><div class="fact"><strong>{float(d.get("behaviorAccuracy",0))*100:.2f}%</strong><span>distilled synthetic behavior accuracy</span></div></div></section>
    <div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Stdlib runtime</span><span>GPU required: false</span><span>PyTorch required: false</span><span>External service required: false</span><span>Deterministic rules authoritative</span><span>Human review required</span></div>
    <section><h2>How STBL was trained</h2><p class="note">GPU and Jupyter training used 171,000 synthetic rows offline. Neural weights are not loaded by the live app.</p></section>
    <section><h2>How runtime distillation works</h2><p class="note">Weighted fault centroids, global feature statistics, and transparent rule boosts produce advisory behavior and fault-family predictions.</p></section>
    <section><h2>Top feature weights</h2><div class="strip">{feature_cards}</div></section>
    <section><h2>Fault coverage</h2><p class="note">{coverage["supportedFaultCount"]} project-defined synthetic fault families across {len(coverage["categoryCoverage"])} evidence categories.</p><a href="/algorithm-console/error-coverage.json">Open coverage JSON</a></section>
    <section><h2>Case predictions</h2><div class="predictions">{prediction_cards}</div></section>
    <section class="weak"><div><h2>Weaknesses and uncertainty</h2><p class="note">Top alternatives and inspection routes expose ambiguity instead of hiding it.</p></div><ul>{weak_rows}</ul></section>
    <section class="boundary"><h2>Runtime safety boundary</h2><p>No GPU, PyTorch, notebook, database, or external service is required. Deterministic rules remain authoritative and human review remains required.</p></section>
    <nav class="routes"><a href="/behavior-predictor">Behavior Predictor</a><a href="/inspection-engine">Inspection Engine</a><a href="/dashboard-strategy">Dashboard Strategy</a><a href="/command-center">Command Center</a></nav></main></body></html>'''
