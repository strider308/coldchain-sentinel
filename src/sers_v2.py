"""SERS v2 advisory risk model.

Synthetic-only proprietary-style risk scoring layer for ColdChain Sentinel.

SERS v2 answers:
- current risk
- why risk is rising
- factors that matter most
- confidence
- what a human should inspect

SERS v2 must never answer:
- release shipment
- quarantine shipment
- discard shipment
- reroute shipment
- notify customer
- certify compliance
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

from case_engine import get_case, load_cases
from consensus_v2 import consensus_report_json
from data_quality_v2 import quality_events_json, quality_report_json
from sensor_data_model_v2 import normalized_sensor_window_json
from serve_dashboard import badge, global_nav, page

SERS_VERSION = "sers-v2"
SERS_MODEL_NAME = "Synthetic Excursion Risk Score"
SERS_RISK_BANDS = ["LOW", "WATCH", "REVIEW", "CRITICAL"]
SERS_CONFIDENCE_LABELS = ["LOW", "MEDIUM", "HIGH"]

SERS_NOT_ALLOWED = [
    "APPROVED",
    "RELEASED",
    "SAFE_FOR_DISTRIBUTION",
    "COMPLIANT",
    "CERTIFIED",
    "automatic release",
    "automatic quarantine",
    "automatic discard",
    "automatic reroute",
    "automatic customer notification",
]

SERS_FEATURES = [
    {
        "featureId": "temperatureExcursionPressure",
        "label": "Temperature excursion pressure",
        "meaning": "Accepted normalized readings crossing the synthetic temperature threshold.",
    },
    {
        "featureId": "unresolvedMappingRisk",
        "label": "Unresolved pallet mapping risk",
        "meaning": "Risk from synthetic case evidence that cannot be mapped cleanly to all pallets.",
    },
    {
        "featureId": "dataQualityRisk",
        "label": "Data quality risk",
        "meaning": "Rejected readings, drift candidates, weak signal, low battery, and dropout context.",
    },
    {
        "featureId": "consensusUncertainty",
        "label": "Consensus uncertainty",
        "meaning": "Penalty when sensor agreement is weak, spikes are isolated, or ZCE refuses escalation.",
    },
    {
        "featureId": "sensorTrustRisk",
        "label": "Sensor trust risk",
        "meaning": "Penalty from low-trust sensors after SDTP and ZCE quality review.",
    },
    {
        "featureId": "contextEventRisk",
        "label": "Context event risk",
        "meaning": "Door-open, shock/vibration, tilt, light exposure, and ingestion-delay context.",
    },
]


def _table(headers: list[str], rows: list[list[Any]], testid: str) -> str:
    head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f'<table data-testid="{html.escape(testid)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _items(values: list[str], test_prefix: str) -> str:
    return "\n".join(
        f'<li data-testid="{html.escape(test_prefix)}-{index}">{html.escape(value)}</li>'
        for index, value in enumerate(values, start=1)
    )


def _band(score: float) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 45:
        return "REVIEW"
    if score >= 25:
        return "WATCH"
    return "LOW"


def _confidence(case_id: str, score: float) -> str:
    qreport = quality_report_json(case_id)
    zreport = consensus_report_json(case_id)
    metrics = qreport["metrics"]
    summary = zreport["summary"]

    if (
        metrics["acceptedReadings"] >= 250
        and metrics["rejectedReadings"] <= 3
        and summary["sensorCount"] >= 8
        and summary["lowestSensorTrustScore"] >= 70
    ):
        return "HIGH"

    if metrics["acceptedReadings"] >= 200 and summary["sensorCount"] >= 8:
        return "MEDIUM"

    return "LOW"


def _case_text(case_id: str) -> str:
    case = get_case(case_id)
    values: list[str] = []
    for key, value in case.items():
        if isinstance(value, (str, int, float, bool)):
            values.append(str(value))
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            values.extend(str(item) for item in value.values())
    return " ".join(values).upper()


def _event_counts(case_id: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in quality_events_json(case_id)["events"]:
        counts[str(event.get("eventType"))] += 1
    return dict(counts)


def feature_contributions_json(case_id: str) -> dict[str, Any]:
    normalized = normalized_sensor_window_json(case_id, 0, 10_000)["readings"]
    qreport = quality_report_json(case_id)
    zreport = consensus_report_json(case_id)
    metrics = qreport["metrics"]
    summary = zreport["summary"]
    events = _event_counts(case_id)
    case_text = _case_text(case_id)

    threshold_candidates = sum(1 for row in normalized if row.get("evidenceType") == "TEMPERATURE_EXCURSION_CANDIDATE")
    unmapped_candidates = sum(1 for row in normalized if row.get("evidenceCandidate") and row.get("palletId") is None)

    has_temperature_blocker = "TEMPERATURE_EXCURSION_DETECTED" in case_text or threshold_candidates > 0
    has_mapping_blocker = "UNRESOLVED_PALLET_MAPPING" in case_text or "UNRESOLVED" in case_text or unmapped_candidates > 0
    ignored_single_sensor_spikes = int(summary.get("ignoredSingleSensorSpikeCount", 0))
    best_zone_score = float(summary.get("bestZoneConsensusScore", 0.0))
    lowest_sensor_trust = float(summary.get("lowestSensorTrustScore", 100.0))

    data_quality_points = min(
        18,
        metrics["rejectedReadings"] * 4
        + metrics["driftCandidates"] * 3
        + metrics["weakSignalReadings"] * 2
        + metrics["lowBatteryReadings"] * 2
        + int(metrics["dropoutWindows"] / 60),
    )

    consensus_points = 0
    if has_temperature_blocker and best_zone_score < 70:
        consensus_points += 12
    if ignored_single_sensor_spikes:
        consensus_points += min(12, ignored_single_sensor_spikes * 4)
    if summary.get("escalatedZoneCount", 0) == 0 and has_temperature_blocker:
        consensus_points += 8
    consensus_points = min(24, consensus_points)

    sensor_trust_points = 0
    if lowest_sensor_trust < 50:
        sensor_trust_points = 15
    elif lowest_sensor_trust < 70:
        sensor_trust_points = 8

    context_events = (
        events.get("DOOR_OPEN_CONTEXT_ENRICHED", 0)
        + events.get("SHOCK_VIBRATION_CONTEXT_FLAGGED", 0)
        + events.get("TILT_CONTEXT_FLAGGED", 0)
        + events.get("LIGHT_EXPOSURE_CONTEXT_FLAGGED", 0)
        + events.get("DROPOUT_CONTEXT_FLAGGED", 0)
    )
    context_points = min(10, int(context_events / 10) + (4 if context_events else 0))

    contributions = [
        {
            "featureId": "temperatureExcursionPressure",
            "label": "Temperature excursion pressure",
            "contributionPoints": 25 if has_temperature_blocker else min(12, threshold_candidates * 3),
            "direction": "raises_risk" if has_temperature_blocker or threshold_candidates else "neutral",
            "evidence": f"{threshold_candidates} accepted synthetic threshold candidate readings.",
            "humanInspection": "Inspect temperature excursion windows and source sensors.",
        },
        {
            "featureId": "unresolvedMappingRisk",
            "label": "Unresolved pallet mapping risk",
            "contributionPoints": 30 if has_mapping_blocker else 0,
            "direction": "raises_risk" if has_mapping_blocker else "neutral",
            "evidence": f"{unmapped_candidates} evidence candidates have no pallet mapping, plus case blocker scan.",
            "humanInspection": "Inspect pallet mapping, unresolved pallets, and audit packet evidence.",
        },
        {
            "featureId": "dataQualityRisk",
            "label": "Data quality risk",
            "contributionPoints": data_quality_points,
            "direction": "raises_risk" if data_quality_points else "neutral",
            "evidence": (
                f'{metrics["rejectedReadings"]} rejected, '
                f'{metrics["driftCandidates"]} drift candidates, '
                f'{metrics["weakSignalReadings"]} weak-signal, '
                f'{metrics["lowBatteryReadings"]} low-battery, '
                f'{metrics["dropoutWindows"]} dropout windows.'
            ),
            "humanInspection": "Inspect SDTP rejected readings, quality events, and sensor health warnings.",
        },
        {
            "featureId": "consensusUncertainty",
            "label": "Consensus uncertainty",
            "contributionPoints": consensus_points,
            "direction": "raises_review_need" if consensus_points else "neutral",
            "evidence": (
                f"Best zone consensus score {best_zone_score}; "
                f"{ignored_single_sensor_spikes} ignored single-sensor spikes; "
                f'{summary.get("escalatedZoneCount", 0)} escalated zones.'
            ),
            "humanInspection": "Inspect ZCE zone consensus, conflicting sensor explanations, and ignored spikes.",
        },
        {
            "featureId": "sensorTrustRisk",
            "label": "Sensor trust risk",
            "contributionPoints": sensor_trust_points,
            "direction": "raises_review_need" if sensor_trust_points else "neutral",
            "evidence": f"Lowest synthetic sensor trust score is {lowest_sensor_trust}.",
            "humanInspection": "Inspect low-trust sensors before relying on their evidence.",
        },
        {
            "featureId": "contextEventRisk",
            "label": "Context event risk",
            "contributionPoints": context_points,
            "direction": "raises_risk" if context_points else "neutral",
            "evidence": f"{context_events} synthetic context/ingestion events found.",
            "humanInspection": "Inspect door-open, shock/vibration, tilt, light exposure, and ingestion-delay context.",
        },
    ]

    total_score = round(min(100.0, sum(item["contributionPoints"] for item in contributions)), 2)

    return {
        "caseId": case_id,
        "modelName": SERS_MODEL_NAME,
        "modelVersion": SERS_VERSION,
        "riskScore": total_score,
        "riskBand": _band(total_score),
        "confidenceLabel": _confidence(case_id, total_score),
        "featureContributions": contributions,
        "riskBandDefinitions": {
            "LOW": "No meaningful synthetic excursion pressure; monitor only.",
            "WATCH": "Some synthetic risk signals exist; keep under review.",
            "REVIEW": "Human review should inspect the case before any operational interpretation.",
            "CRITICAL": "Strong synthetic review pressure; human inspection required. This is not an automatic action.",
        },
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "advisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def risk_timeline_json(case_id: str) -> dict[str, Any]:
    normalized = normalized_sensor_window_json(case_id, 0, 10_000)["readings"]
    contribution_payload = feature_contributions_json(case_id)
    case_text = _case_text(case_id)
    unresolved_mapping = "UNRESOLVED_PALLET_MAPPING" in case_text or "UNRESOLVED" in case_text

    accepted = [row for row in normalized if row["normalizationStatus"] == "ACCEPTED"]
    bucket_size = 24
    timeline: list[dict[str, Any]] = []

    for index in range(0, len(accepted), bucket_size):
        bucket = accepted[index : index + bucket_size]
        if not bucket:
            continue

        threshold_count = sum(1 for row in bucket if row.get("evidenceType") == "TEMPERATURE_EXCURSION_CANDIDATE")
        context_count = sum(1 for row in bucket if row.get("normalizationWarnings"))
        unmapped_count = sum(1 for row in bucket if row.get("evidenceCandidate") and row.get("palletId") is None)
        weak_count = sum(1 for row in bucket if row.get("signalQualityLabel") == "WEAK_SIGNAL")
        low_battery_count = sum(1 for row in bucket if row.get("batteryQualityLabel") == "LOW_BATTERY")

        score = 5
        score += min(35, threshold_count * 9)
        score += 18 if unresolved_mapping else 0
        score += min(15, context_count * 2)
        score += min(10, unmapped_count * 4)
        score += min(8, weak_count * 3)
        score += min(8, low_battery_count * 3)
        score = round(min(100.0, score), 2)

        rising_reasons: list[str] = []
        if threshold_count:
            rising_reasons.append(f"{threshold_count} threshold candidates")
        if unresolved_mapping:
            rising_reasons.append("unresolved mapping context")
        if context_count:
            rising_reasons.append(f"{context_count} quality/context warnings")
        if unmapped_count:
            rising_reasons.append(f"{unmapped_count} unmapped evidence candidates")
        if not rising_reasons:
            rising_reasons.append("no major synthetic risk driver in this bucket")

        timeline.append(
            {
                "windowIndex": len(timeline) + 1,
                "startTimestampUtc": bucket[0]["timestampUtc"],
                "endTimestampUtc": bucket[-1]["timestampUtc"],
                "riskScore": score,
                "riskBand": _band(score),
                "whyRiskIsRising": rising_reasons,
                "thresholdCandidateCount": threshold_count,
                "contextWarningCount": context_count,
                "unmappedEvidenceCandidateCount": unmapped_count,
                "weakSignalCount": weak_count,
                "lowBatteryCount": low_battery_count,
            }
        )

    return {
        "caseId": case_id,
        "modelName": SERS_MODEL_NAME,
        "modelVersion": SERS_VERSION,
        "riskTimeline": timeline,
        "currentRisk": {
            "riskScore": contribution_payload["riskScore"],
            "riskBand": contribution_payload["riskBand"],
            "confidenceLabel": contribution_payload["confidenceLabel"],
        },
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "advisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def sers_case_json(case_id: str) -> dict[str, Any]:
    contribution_payload = feature_contributions_json(case_id)
    timeline_payload = risk_timeline_json(case_id)

    inspection_items = [
        item["humanInspection"]
        for item in contribution_payload["featureContributions"]
        if item["contributionPoints"] > 0
    ]
    if not inspection_items:
        inspection_items = ["Continue monitoring synthetic sensor quality and deterministic case evidence."]

    return {
        "caseId": case_id,
        "modelName": SERS_MODEL_NAME,
        "modelVersion": SERS_VERSION,
        "currentRisk": {
            "riskScore": contribution_payload["riskScore"],
            "riskBand": contribution_payload["riskBand"],
            "confidenceLabel": contribution_payload["confidenceLabel"],
        },
        "whyRiskIsRising": timeline_payload["riskTimeline"][-1]["whyRiskIsRising"] if timeline_payload["riskTimeline"] else [],
        "factorsThatMatterMost": sorted(
            contribution_payload["featureContributions"],
            key=lambda item: item["contributionPoints"],
            reverse=True,
        ),
        "whatHumanShouldInspect": inspection_items,
        "riskTimelineRoute": f"/cases/{case_id}/risk-timeline.json",
        "modelCardRoute": f"/cases/{case_id}/sers-model-card.json",
        "notAllowedAnswers": SERS_NOT_ALLOWED,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "advisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def sers_json() -> dict[str, Any]:
    cases = load_cases()
    case_reports = [sers_case_json(case["caseId"]) for case in cases]
    return {
        "modelName": SERS_MODEL_NAME,
        "modelVersion": SERS_VERSION,
        "status": "ADVISORY_ONLY",
        "riskBands": SERS_RISK_BANDS,
        "confidenceLabels": SERS_CONFIDENCE_LABELS,
        "caseReports": case_reports,
        "routes": [
            "/sers",
            "/sers.json",
            "/cases/blocked-unresolved-pallet/risk-timeline.json",
            "/cases/blocked-unresolved-pallet/sers-model-card.json",
        ],
        "answersAllowed": [
            "current risk",
            "why risk is rising",
            "factors that matter most",
            "confidence label",
            "what the human should inspect",
        ],
        "answersNotAllowed": SERS_NOT_ALLOWED,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "advisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def sers_model_card_json(case_id: str) -> dict[str, Any]:
    case_report = sers_case_json(case_id)
    return {
        "caseId": case_id,
        "modelName": SERS_MODEL_NAME,
        "modelVersion": SERS_VERSION,
        "modelType": "deterministic synthetic scoring model",
        "intendedUse": [
            "Advisory synthetic risk scoring.",
            "Human review prioritization.",
            "Explaining why risk is rising.",
            "Showing feature contributions and confidence.",
        ],
        "notIntendedUse": SERS_NOT_ALLOWED,
        "inputSources": [
            "normalized-sensor-window-v2",
            "SDTP data-quality metrics",
            "ZCE consensus report",
            "deterministic case blockers",
        ],
        "features": SERS_FEATURES,
        "outputs": [
            "riskScore",
            "riskBand",
            "confidenceLabel",
            "featureContributions",
            "riskTimeline",
            "humanInspectionItems",
        ],
        "riskBands": case_report["currentRisk"],
        "riskBandDefinitions": feature_contributions_json(case_id)["riskBandDefinitions"],
        "limitations": [
            "Synthetic data only.",
            "No real-world validation.",
            "No production validation.",
            "No pharma/compliance certification.",
            "No operational decision authority.",
            "No automatic release/quarantine/discard/reroute/customer notification.",
        ],
        "safetyBoundary": [
            "Deterministic rules remain authoritative.",
            "SERS is advisory only.",
            "A human reviewer must inspect evidence.",
            "SERS output must not change finalDisposition, reviewStatus, blockers, pallet mapping, or telemetry facts.",
        ],
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "advisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def render_sers_page() -> str:
    payload = sers_json()
    primary = sers_case_json("blocked-unresolved-pallet")
    current = primary["currentRisk"]

    contribution_rows = [
        [
            item["label"],
            item["contributionPoints"],
            item["direction"],
            item["evidence"],
            item["humanInspection"],
        ]
        for item in primary["factorsThatMatterMost"]
    ]

    timeline_rows = [
        [
            point["windowIndex"],
            point["startTimestampUtc"],
            point["endTimestampUtc"],
            point["riskScore"],
            point["riskBand"],
            "; ".join(point["whyRiskIsRising"]),
        ]
        for point in risk_timeline_json("blocked-unresolved-pallet")["riskTimeline"][:12]
    ]

    body = f"""
  <header data-testid="sers-page">
    {global_nav()}
    <h1>SERS v2 Advisory Risk Model</h1>
    <p>Synthetic Excursion Risk Score explains current risk, why risk is rising, what factors matter, confidence, and what a human should inspect.</p>
    {badge("SERS v2", "good")}{badge("Advisory only", "warn")}{badge("Synthetic only", "warn")}{badge("No autonomous action", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="sers-current-risk">
        <h2>Current risk</h2>
        <p><strong>Risk band:</strong> {html.escape(current["riskBand"])}</p>
        <p><strong>Risk score:</strong> {html.escape(str(current["riskScore"]))}</p>
        <p><strong>Confidence:</strong> {html.escape(current["confidenceLabel"])}</p>
      </article>
      <article class="panel status-block" data-testid="sers-not-allowed">
        <h2>SERS must not answer</h2>
        <ul>{_items(payload["answersNotAllowed"], "sers-not-allowed")}</ul>
      </article>
    </section>
    <section class="panel" data-testid="sers-feature-contributions">
      <h2>Feature contribution table</h2>
      {_table(["Feature", "Points", "Direction", "Evidence", "Human should inspect"], contribution_rows, "sers-contribution-table")}
    </section>
    <section class="panel" data-testid="sers-risk-timeline">
      <h2>Risk trend over time</h2>
      {_table(["Window", "Start", "End", "Score", "Band", "Why risk is rising"], timeline_rows, "sers-timeline-table")}
    </section>
    <section class="panel" data-testid="sers-human-inspection">
      <h2>What the human should inspect</h2>
      <ul>{_items(primary["whatHumanShouldInspect"], "sers-inspect")}</ul>
    </section>
    <section class="panel">
      <div class="toolbar">
        <a class="button" href="/sers.json">SERS JSON</a>
        <a class="button" href="/cases/blocked-unresolved-pallet/risk-timeline.json">Risk timeline</a>
        <a class="button" href="/cases/blocked-unresolved-pallet/sers-model-card.json">SERS model card</a>
        <a class="button" href="/consensus">Consensus</a>
        <a class="button" href="/data-quality">Data Quality</a>
      </div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel SERS v2", body)
