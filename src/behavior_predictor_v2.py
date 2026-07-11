from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from ui_design_system_v2 import unified_page


PHASE = "Phase 35B - Sentinel Thermal Behavior Learner App Ingestion"
ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATHS = {
    "training": "artifacts/stbl_training_artifact_phase35.json",
    "rules": "artifacts/stbl_distilled_rules_phase35.json",
    "modelCard": "artifacts/stbl_model_card_phase35.json",
}
REVIEW_WORKSPACE_CASE_IDS = {
    "no-excursion-control", "single-sensor-spike", "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk", "door-open-warming", "dropout-weak-signal",
}
FEATURES = (
    "temperatureSlopeCPerHour", "temperatureVolatilityC", "sensorDisagreementC",
    "zoneDisagreementC", "humiditySlopePercentPerHour", "doorOpenCount",
    "shockEventCount", "tiltEventCount", "lightExposureCount", "weakSignalShare",
    "lowBatteryShare", "missingReadingCount", "duplicateReadingCount",
    "outOfOrderCount", "lateArrivalCount", "maxIngestionDelaySeconds",
    "mappingConfidenceMin", "calibrationOffsetC", "qualityScore",
)


def _features(**overrides: float) -> dict[str, float]:
    values = {
        "temperatureSlopeCPerHour": 0.0, "temperatureVolatilityC": 0.2,
        "sensorDisagreementC": 0.25, "zoneDisagreementC": 0.2,
        "humiditySlopePercentPerHour": 0.0, "doorOpenCount": 0.0,
        "shockEventCount": 0.0, "tiltEventCount": 0.0, "lightExposureCount": 0.0,
        "weakSignalShare": 0.05, "lowBatteryShare": 0.03, "missingReadingCount": 1.0,
        "duplicateReadingCount": 0.0, "outOfOrderCount": 0.0, "lateArrivalCount": 1.0,
        "maxIngestionDelaySeconds": 45.0, "mappingConfidenceMin": 0.95,
        "calibrationOffsetC": 0.0, "qualityScore": 91.0,
    }
    values.update(overrides)
    return values


CASE_FEATURES = {
    "no-excursion-control": _features(),
    "single-sensor-spike": _features(temperatureVolatilityC=2.8, sensorDisagreementC=4.2, qualityScore=76),
    "multi-sensor-confirmed-warming": _features(temperatureSlopeCPerHour=1.5, temperatureVolatilityC=.45, sensorDisagreementC=.3),
    "unresolved-mapping-risk": _features(zoneDisagreementC=2.4, mappingConfidenceMin=.18, qualityScore=58),
    "door-open-warming": _features(temperatureSlopeCPerHour=1.1, humiditySlopePercentPerHour=2.3, doorOpenCount=5, lightExposureCount=2),
    "dropout-weak-signal": _features(weakSignalShare=.72, missingReadingCount=46, qualityScore=37),
    "borderline-warming": _features(temperatureSlopeCPerHour=.42, temperatureVolatilityC=.3, qualityScore=84),
    "multi-zone-conflict": _features(sensorDisagreementC=1.7, zoneDisagreementC=2.8, mappingConfidenceMin=.58, qualityScore=62),
    "sensor-drift-over-time": _features(temperatureSlopeCPerHour=.18, sensorDisagreementC=1.2, calibrationOffsetC=1.6, qualityScore=64),
    "gateway-delay": _features(outOfOrderCount=9, lateArrivalCount=18, maxIngestionDelaySeconds=2400, qualityScore=49),
    "battery-degradation": _features(weakSignalShare=.36, lowBatteryShare=.78, missingReadingCount=12, qualityScore=51),
    "humidity-anomaly": _features(humiditySlopePercentPerHour=5.7, temperatureVolatilityC=.35, qualityScore=83),
    "late-arriving-data": _features(outOfOrderCount=5, lateArrivalCount=24, maxIngestionDelaySeconds=980, qualityScore=55),
    "mixed-quality-evidence": _features(sensorDisagreementC=1.3, zoneDisagreementC=1.1, weakSignalShare=.38, missingReadingCount=19, duplicateReadingCount=8, qualityScore=43),
}

CASE_TARGETS = {
    "no-excursion-control": "routine evidence review",
    "single-sensor-spike": "suspect sensor and neighboring sensors",
    "multi-sensor-confirmed-warming": "zone consensus sensors and thermal timeline",
    "unresolved-mapping-risk": "pallet-zone identity mapping",
    "door-open-warming": "door event timeline and affected zone",
    "dropout-weak-signal": "gateway signal timeline and missing readings",
    "borderline-warming": "temperature slope and threshold proximity",
    "multi-zone-conflict": "zone disagreement and identity mapping",
    "sensor-drift-over-time": "sensor calibration trend and offset",
    "gateway-delay": "gateway timestamps and route segment",
    "battery-degradation": "battery timeline and missing windows",
    "humidity-anomaly": "humidity sensor and condensation indicators",
    "late-arriving-data": "device and gateway timestamps",
    "mixed-quality-evidence": "data quality evidence before thermal interpretation",
}


def _valid_artifacts(training: Any, rules: Any, model_card: Any) -> bool:
    return bool(
        isinstance(training, dict) and training.get("totalRows") == 171000
        and training.get("syntheticOnly") is True
        and isinstance(rules, dict)
        and rules.get("distilledMethod") == "weighted-centroid-prototypes-plus-rule-boosts"
        and len(rules.get("features", [])) == 19
        and len(rules.get("featureWeights", {})) == 19
        and len(rules.get("faultPrototypes", {})) == 38
        and isinstance(rules.get("globalFeatureStats"), dict)
        and isinstance(rules.get("faultToBehavior"), dict)
        and isinstance(model_card, dict)
        and model_card.get("syntheticOnly") is True
    )


def load_stbl_artifacts() -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    try:
        for name, path in ARTIFACT_PATHS.items():
            with (ROOT / path).open("r", encoding="utf-8-sig") as handle:
                loaded[name] = json.load(handle)
    except (OSError, json.JSONDecodeError):
        loaded = {}
    available = _valid_artifacts(loaded.get("training"), loaded.get("rules"), loaded.get("modelCard"))
    return {"artifactAvailable": available, **loaded} if available else {"artifactAvailable": False}


def get_case_feature_vector(case_id: str) -> dict[str, float]:
    if case_id not in CASE_FEATURES:
        raise KeyError(case_id)
    return dict(CASE_FEATURES[case_id])


def _rule_boosts(values: dict[str, float]) -> dict[str, float]:
    boosts: dict[str, float] = {}

    def add(label: str, amount: float) -> None:
        boosts[label] = boosts.get(label, 0.0) + amount

    slope, volatility = values["temperatureSlopeCPerHour"], values["temperatureVolatilityC"]
    disagreement = values["sensorDisagreementC"]
    if values["doorOpenCount"] >= 1 and slope > .3: add("door_open_warming", 6)
    if slope > .5 and disagreement < .8: add("multi_sensor_confirmed_warming", 5)
    if volatility > 1 and disagreement > 1.5:
        add("single_sensor_false_spike", 6); add("noisy_sensor", 3)
    if values["weakSignalShare"] > .3 and values["missingReadingCount"] > 8:
        add("weak_signal", 4); add("dropout_window", 5)
    if values["lowBatteryShare"] > .3: add("low_battery", 6)
    if values["maxIngestionDelaySeconds"] > 600:
        add("gateway_delay", 5); add("late_arriving_data", 3)
    if values["lateArrivalCount"] > 12: add("late_arriving_data", 4)
    if values["mappingConfidenceMin"] < .5:
        add("unresolved_mapping_risk", 6); add("pallet_zone_mapping_conflict", 4)
    if values["humiditySlopePercentPerHour"] > 2:
        add("humidity_anomaly", 5); add("condensation_risk", 3)
    if abs(values["calibrationOffsetC"]) > .7:
        add("sensor_drift", 5); add("calibration_offset", 4)
    if values["zoneDisagreementC"] > 1.5: add("pallet_zone_mapping_conflict", 3)
    if values["qualityScore"] < 55 and values["missingReadingCount"] > 10: add("mixed_quality_evidence", 4)
    return boosts


def predict_case_behavior(case_id: str) -> dict[str, Any]:
    values = get_case_feature_vector(case_id)
    artifacts = load_stbl_artifacts()
    if not artifacts["artifactAvailable"]:
        return {
            "phase": PHASE, "caseId": case_id, "artifactAvailable": False,
            "predictorAvailable": False, "deterministicFallbackAvailable": True,
            "syntheticOnly": True, "advisoryOnly": True,
            "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False,
            "runtimePyTorchRequired": False, "autonomousActionsAllowed": False,
            "deterministicRulesAuthoritative": True,
        }
    rules = artifacts["rules"]
    boosts = _rule_boosts(values)
    scale = float(rules["bestBoostScale"])
    ranked = []
    for fault, prototype in rules["faultPrototypes"].items():
        raw = sum(
            float(rules["featureWeights"][feature])
            * ((values[feature] - float(prototype["centroid"][feature])) / max(float(rules["globalFeatureStats"][feature]["std"]), 1e-9)) ** 2
            for feature in rules["features"]
        )
        boost = boosts.get(fault, 0.0) * scale
        ranked.append({"faultLabel": fault, "adjustedDistance": raw - boost, "rawDistance": raw, "ruleBoost": boost})
    ranked.sort(key=lambda item: item["adjustedDistance"])
    best, second = ranked[:2]
    margin = second["adjustedDistance"] - best["adjustedDistance"]
    salient = sorted(
        values,
        key=lambda feature: abs(values[feature] - float(rules["globalFeatureStats"][feature]["mean"])) / max(float(rules["globalFeatureStats"][feature]["std"]), 1e-9),
        reverse=True,
    )[:6]
    evidence_routes = {
        "scenario": f"/scenario-library-v4/{case_id}.json",
        "evaluationRow": f"/cases/{case_id}/evaluation-row.json",
        "inspectionPlan": f"/cases/{case_id}/inspection-plan.json",
    }
    if case_id in REVIEW_WORKSPACE_CASE_IDS:
        evidence_routes.update({
            "reviewerWorkspace": f"/reviewer-workspace/{case_id}.json",
            "auditLedger": f"/cases/{case_id}/audit-ledger.json",
        })
    return {
        "phase": PHASE, "caseId": case_id, "syntheticOnly": True, "advisoryOnly": True,
        "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False,
        "runtimePyTorchRequired": False, "autonomousActionsAllowed": False,
        "deterministicRulesAuthoritative": True,
        "predictedBehaviorLabel": rules["faultToBehavior"][best["faultLabel"]],
        "predictedFaultLabel": best["faultLabel"],
        "confidenceBand": "high" if margin >= 2 else "medium" if margin >= .5 else "low",
        "humanReviewRequired": case_id != "no-excursion-control",
        "primaryInspectionTarget": CASE_TARGETS[case_id],
        "topAlternatives": [
            {"faultLabel": item["faultLabel"], "behaviorLabel": rules["faultToBehavior"][item["faultLabel"]], "adjustedDistance": round(item["adjustedDistance"], 4)}
            for item in ranked[1:4]
        ],
        "featureVectorSummary": {feature: values[feature] for feature in salient},
        "algorithmEvidence": {
            "distilledMethod": rules["distilledMethod"], "ruleBoost": round(best["ruleBoost"], 4),
            "margin": round(margin, 4), "rawCentroidDistance": round(best["rawDistance"], 4),
            "bestBoostScale": scale,
        },
        "safetyBoundary": {
            "advisoryOnly": True, "syntheticOnly": True, "notOperationalDisposition": True,
            "humanReviewRequiredForOperationalInterpretation": True,
            "deterministicRulesAuthoritative": True,
        },
        "evidenceRoutes": evidence_routes,
    }


def get_behavior_predictor_payload() -> dict[str, Any]:
    artifacts = load_stbl_artifacts()
    available = artifacts["artifactAvailable"]
    training, rules = artifacts.get("training", {}), artifacts.get("rules", {})
    predictions = [predict_case_behavior(case_id) for case_id in CASE_FEATURES] if available else []
    return {
        "phase": PHASE, "status": "READY" if available else "ARTIFACT_UNAVAILABLE",
        "algorithmName": "STBL - Sentinel Thermal Behavior Learner",
        "syntheticOnly": True, "advisoryOnly": True, "realWorldDataUsed": False,
        "realCustomerDataUsed": False, "realShipmentDataUsed": False,
        "runtimeGpuRequired": False, "runtimeExternalServiceRequired": False,
        "runtimePyTorchRequired": False, "notebookRequiredAtRuntime": False,
        "deterministicRulesAuthoritative": True, "autonomousActionsAllowed": False,
        "predictorAvailable": available, "artifactAvailable": available,
        "distilledRuntimeAvailable": available,
        "deterministicFallbackAvailable": True,
        "distilledMethod": rules.get("distilledMethod"),
        "trainingRows": training.get("totalRows", 0),
        "faultPrototypeCount": len(rules.get("faultPrototypes", {})),
        "featureWeightCount": len(rules.get("featureWeights", {})),
        "neuralMetrics": training.get("finalNeuralMetrics", {}),
        "distilledMetrics": rules.get("distilledMetrics", {}),
        "supportedFaultCount": len(rules.get("faultToBehavior", {})),
        "supportedFeatureCount": len(rules.get("features", [])),
        "supportedCaseCount": len(CASE_FEATURES), "casePredictions": predictions,
        "outputs": ["predicted behavior label", "likely synthetic fault family", "confidence band", "top alternate fault families", "first inspection target", "human review required"],
        "runtimeBoundary": {"stdlibOnly": True, "noGpu": True, "noPyTorch": True, "noExternalService": True, "noRealData": True},
        "safetyBoundaries": {"syntheticOnly": True, "advisoryOnly": True, "notOperationalDisposition": True, "deterministicRulesAuthoritative": True},
        "artifactPaths": ARTIFACT_PATHS,
        "routeMap": {
            "behaviorPredictor": "/behavior-predictor", "modelCard": "/behavior-predictor/model-card.json",
            "distilledRules": "/behavior-predictor/distilled-rules.json", "inspectionEngine": "/inspection-engine",
            "evaluationMatrixV2": "/evaluation-matrix-v2", "scenarioLibraryV4": "/scenario-library-v4",
            "decisionSimulator": "/decision-simulator", "dashboardStrategy": "/dashboard-strategy",
        },
    }


def _artifact_payload(name: str) -> dict[str, Any]:
    artifacts = load_stbl_artifacts()
    return artifacts.get(name, {"phase": PHASE, "artifactAvailable": False, "deterministicFallbackAvailable": True})


def get_model_card_payload() -> dict[str, Any]: return _artifact_payload("modelCard")
def get_training_artifact_payload() -> dict[str, Any]: return _artifact_payload("training")
def get_distilled_rules_payload() -> dict[str, Any]: return _artifact_payload("rules")


@unified_page
def render_behavior_predictor_html() -> str:
    payload = get_behavior_predictor_payload()
    cards = "".join(
        f'<article><p class="case">{html.escape(item["caseId"])}</p><h2>{html.escape(item["predictedBehaviorLabel"])}</h2>'
        f'<p>{html.escape(item["predictedFaultLabel"])}. Confidence: {html.escape(item["confidenceBand"])}.</p>'
        f'<p class="target">Inspect first: {html.escape(item["primaryInspectionTarget"])}</p>'
        f'<a href="/cases/{html.escape(item["caseId"])}/behavior-prediction.json">Prediction JSON</a> '
        f'<a href="/cases/{html.escape(item["caseId"])}/inspection-plan.json">Inspection plan</a></article>'
        for item in payload["casePredictions"]
    ) or '<p class="empty">Artifacts unavailable. Deterministic safety routes remain available.</p>'
    neural, distilled = payload["neuralMetrics"], payload["distilledMetrics"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sentinel Thermal Behavior Learner</title><style>
    :root{{--bg:#07110f;--surface:#0d1c19;--line:#29473f;--ink:#edf7f2;--muted:#a9bcb5;--accent:#62c9a5;--radius:12px}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:min(1180px,100%);margin:auto;padding:24px 18px 60px}}a{{color:var(--accent)}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.hero{{display:grid;grid-template-columns:1.25fr .75fr;gap:16px;align-items:stretch}}.intro,.metrics{{border:1px solid var(--line);border-radius:var(--radius);padding:clamp(24px,5vw,50px);background:var(--surface)}}h1{{font-size:clamp(38px,6vw,68px);line-height:1;letter-spacing:-.045em;margin:0 0 18px}}.intro>p{{color:var(--muted);max-width:58ch}}.metrics{{display:grid;grid-template-columns:1fr 1fr;gap:18px;background:var(--accent);color:#07110f}}.metric strong{{display:block;font-size:30px}}.metric span{{font-size:13px}}.badges{{display:flex;flex-wrap:wrap;gap:7px;margin:16px 0 40px}}.badges span{{border:1px solid var(--line);border-radius:8px;padding:6px 9px;color:var(--muted);font-size:13px}}section{{margin-top:42px}}section>p{{color:var(--muted);max-width:70ch}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}article{{border-top:3px solid var(--accent);background:var(--surface);padding:18px;min-height:210px}}article h2{{margin:10px 0;text-transform:capitalize}}.case{{color:var(--muted);font-family:ui-monospace,monospace}}.target{{color:var(--ink)}}.links{{display:flex;flex-wrap:wrap;gap:10px}}.links a{{border:1px solid var(--line);border-radius:8px;padding:9px 12px}}@media(max-width:760px){{main{{padding:14px 12px 44px}}.hero,.grid{{grid-template-columns:1fr}}.metrics{{padding:22px}}h1{{font-size:44px}}}}
    </style></head><body><main><section class="hero"><div class="intro"><h1>Sentinel Thermal Behavior Learner</h1><p>Offline synthetic training becomes transparent distilled behavior guidance for human inspection.</p></div><div class="metrics"><div class="metric"><strong>171,000</strong><span>synthetic rows</span></div><div class="metric"><strong>{float(neural.get("faultAccuracy",0))*100:.2f}%</strong><span>neural synthetic fault accuracy</span></div><div class="metric"><strong>{float(neural.get("behaviorAccuracy",0))*100:.2f}%</strong><span>neural synthetic behavior accuracy</span></div><div class="metric"><strong>{float(distilled.get("faultAccuracy",0))*100:.2f}%</strong><span>distilled synthetic fault accuracy</span></div><div class="metric"><strong>{float(distilled.get("behaviorAccuracy",0))*100:.2f}%</strong><span>distilled synthetic behavior accuracy</span></div></div></section>
    <div class="badges"><span>Synthetic-only</span><span>Advisory-only</span><span>Stdlib runtime</span><span>GPU required: false</span><span>PyTorch required: false</span><span>External service required: false</span><span>Deterministic rules authoritative</span></div>
    <section><h2>Transparent runtime boundary</h2><p>Neural training happened offline in Jupyter on GPU. The live app uses committed distilled JSON rules. It requires no GPU, PyTorch, notebook, or external service.</p><div class="links"><a href="/behavior-predictor/model-card.json">Model card</a><a href="/behavior-predictor/training-artifact.json">Training artifact</a><a href="/behavior-predictor/distilled-rules.json">Distilled rules</a><a href="/inspection-engine">Inspection engine</a></div></section>
    <section><h2>Case predictions</h2><p>Fourteen deterministic synthetic cases connect behavior, likely fault family, and the first human inspection target.</p><div class="grid">{cards}</div></section></main></body></html>'''
