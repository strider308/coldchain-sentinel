"""Sentinel Data Trust Pipeline v2.

Synthetic-only cleaning and quality metrics for ColdChain Sentinel.
No real shipment, customer, pharma, logistics, patient, or sensor data is used.
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

from case_engine import load_cases
from sensor_data_model_v2 import normalized_sensor_window_json, raw_sensor_window_json
from serve_dashboard import badge, global_nav, page

SDTP_STAGES: list[dict[str, str]] = [
    {"stage": "1", "name": "Schema validation", "purpose": "Validate required identity, timing, environmental, and sequence fields."},
    {"stage": "2", "name": "Unit normalization", "purpose": "Preserve canonical Celsius temperature and normalize quality fields."},
    {"stage": "3", "name": "Timestamp normalization", "purpose": "Normalize reading timestamps to UTC ISO-8601."},
    {"stage": "4", "name": "Duplicate detection", "purpose": "Detect repeated device/sequence readings in the same case window."},
    {"stage": "5", "name": "Sequence-gap detection", "purpose": "Detect suspicious gaps in per-sensor sequence continuity."},
    {"stage": "6", "name": "Dropout detection", "purpose": "Flag delayed or missing-context readings that may indicate telemetry dropout."},
    {"stage": "7", "name": "Outlier rejection", "purpose": "Reject impossible environmental values before evidence generation."},
    {"stage": "8", "name": "Drift detection", "purpose": "Flag temperature movement that may represent sensor drift or rising risk."},
    {"stage": "9", "name": "Low battery flagging", "purpose": "Flag device readings with low-battery context."},
    {"stage": "10", "name": "Weak signal flagging", "purpose": "Flag gateway/device signal quality issues."},
    {"stage": "11", "name": "Door-open context enrichment", "purpose": "Attach door-open context to evidence candidates."},
    {"stage": "12", "name": "Neighbor sensor comparison", "purpose": "Prepare accepted readings for zone-level redundancy and consensus."},
    {"stage": "13", "name": "Accepted/rejected evidence split", "purpose": "Separate clean evidence candidates from rejected readings and warnings."},
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


def _all_raw(case_id: str) -> list[dict[str, Any]]:
    return raw_sensor_window_json(case_id, 0, 10_000)["readings"]


def _all_normalized(case_id: str) -> list[dict[str, Any]]:
    return normalized_sensor_window_json(case_id, 0, 10_000)["readings"]


def _detect_duplicates(raw_readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    duplicates: list[dict[str, Any]] = []
    for reading in raw_readings:
        key = (str(reading.get("deviceId")), int(reading.get("readingSequence", -1)))
        if key in seen:
            duplicates.append(reading)
        seen.add(key)
    return duplicates


def _detect_sequence_gaps(raw_readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sensor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reading in raw_readings:
        by_sensor[str(reading.get("sensorId"))].append(reading)

    events: list[dict[str, Any]] = []
    for sensor_id, readings in by_sensor.items():
        ordered = sorted(readings, key=lambda row: int(row.get("readingSequence", 0)))
        for previous, current in zip(ordered, ordered[1:]):
            gap = int(current["readingSequence"]) - int(previous["readingSequence"])
            if gap > 18:
                events.append(
                    {
                        "eventType": "SEQUENCE_GAP_DETECTED",
                        "severity": "warning",
                        "sensorId": sensor_id,
                        "fromSequence": previous["readingSequence"],
                        "toSequence": current["readingSequence"],
                        "gap": gap,
                        "timestampUtc": current["timestampUtc"],
                        "meaning": "Synthetic sequence gap detected for telemetry quality review.",
                    }
                )
    return events


def _detect_drift_candidates(normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sensor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reading in normalized:
        if reading["normalizationStatus"] == "ACCEPTED":
            by_sensor[str(reading["sensorId"])].append(reading)

    events: list[dict[str, Any]] = []
    for sensor_id, readings in by_sensor.items():
        ordered = sorted(readings, key=lambda row: int(row["readingSequence"]))
        for previous, current in zip(ordered, ordered[1:]):
            prev_temp = previous.get("temperatureC")
            current_temp = current.get("temperatureC")
            if isinstance(prev_temp, (int, float)) and isinstance(current_temp, (int, float)):
                delta = current_temp - prev_temp
                if delta >= 1.15:
                    events.append(
                        {
                            "eventType": "DRIFT_CANDIDATE",
                            "severity": "warning",
                            "sensorId": sensor_id,
                            "timestampUtc": current["timestampUtc"],
                            "readingSequence": current["readingSequence"],
                            "temperatureDeltaC": round(delta, 2),
                            "meaning": "Synthetic temperature movement flagged for drift/risk review.",
                        }
                    )
    return events


def quality_events_json(case_id: str) -> dict[str, Any]:
    raw = _all_raw(case_id)
    normalized = _all_normalized(case_id)

    events: list[dict[str, Any]] = []

    for duplicate in _detect_duplicates(raw):
        events.append(
            {
                "eventType": "DUPLICATE_READING_REJECTED",
                "severity": "reject",
                "sensorId": duplicate["sensorId"],
                "deviceId": duplicate["deviceId"],
                "timestampUtc": duplicate["timestampUtc"],
                "readingSequence": duplicate["readingSequence"],
                "meaning": "Duplicate device/sequence reading rejected by SDTP.",
            }
        )

    events.extend(_detect_sequence_gaps(raw))
    events.extend(_detect_drift_candidates(normalized))

    for reading in normalized:
        if reading["normalizationStatus"] == "REJECTED":
            event_type = "OUTLIER_REJECTED" if "impossible temperature value" in reading["rejectionReasons"] else "SCHEMA_VALIDATION_FAILED"
            events.append(
                {
                    "eventType": event_type,
                    "severity": "reject",
                    "sensorId": reading["sensorId"],
                    "deviceId": reading["deviceId"],
                    "timestampUtc": reading["timestampUtc"],
                    "readingSequence": reading["readingSequence"],
                    "rejectionReasons": reading["rejectionReasons"],
                    "meaning": "Reading excluded from clean evidence.",
                }
            )

        for warning in reading["normalizationWarnings"]:
            mapped_type = {
                "LOW_BATTERY_CONTEXT": "LOW_BATTERY_FLAGGED",
                "WEAK_SIGNAL_CONTEXT": "WEAK_SIGNAL_FLAGGED",
                "INGESTION_DELAY_GT_60_SECONDS": "DROPOUT_CONTEXT_FLAGGED",
                "DOOR_OPEN_CONTEXT": "DOOR_OPEN_CONTEXT_ENRICHED",
                "SHOCK_VIBRATION_CONTEXT": "SHOCK_VIBRATION_CONTEXT_FLAGGED",
                "TILT_CONTEXT": "TILT_CONTEXT_FLAGGED",
                "LIGHT_EXPOSURE_CONTEXT": "LIGHT_EXPOSURE_CONTEXT_FLAGGED",
            }.get(warning, "NORMALIZATION_WARNING")

            events.append(
                {
                    "eventType": mapped_type,
                    "severity": "warning",
                    "sensorId": reading["sensorId"],
                    "deviceId": reading["deviceId"],
                    "timestampUtc": reading["timestampUtc"],
                    "readingSequence": reading["readingSequence"],
                    "warning": warning,
                    "meaning": "Accepted reading enriched with quality/context warning.",
                }
            )

        if reading["evidenceCandidate"]:
            events.append(
                {
                    "eventType": "ACCEPTED_EVIDENCE_CANDIDATE",
                    "severity": "evidence",
                    "sensorId": reading["sensorId"],
                    "deviceId": reading["deviceId"],
                    "timestampUtc": reading["timestampUtc"],
                    "readingSequence": reading["readingSequence"],
                    "evidenceType": reading["evidenceType"],
                    "evidenceId": reading["evidenceId"],
                    "meaning": "Accepted normalized reading promoted to evidence candidate.",
                }
            )

    events.sort(key=lambda row: (str(row.get("timestampUtc", "")), str(row.get("eventType", ""))))
    return {
        "caseId": case_id,
        "pipelineName": "Sentinel Data Trust Pipeline",
        "pipelineAcronym": "SDTP",
        "pipelineVersion": "sdtp-v2",
        "totalEvents": len(events),
        "events": events,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
    }


def rejected_readings_json(case_id: str, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    normalized = _all_normalized(case_id)
    rejected = [reading for reading in normalized if reading["normalizationStatus"] == "REJECTED"]
    window = rejected[offset : offset + limit]
    return {
        "caseId": case_id,
        "pipelineName": "Sentinel Data Trust Pipeline",
        "pipelineAcronym": "SDTP",
        "offset": offset,
        "limit": limit,
        "totalRejectedReadings": len(rejected),
        "returnedReadings": len(window),
        "readings": window,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "autonomousActionsAllowed": False,
    }


def quality_report_json(case_id: str) -> dict[str, Any]:
    raw = _all_raw(case_id)
    normalized = _all_normalized(case_id)
    events = quality_events_json(case_id)["events"]

    total = len(normalized)
    accepted = sum(1 for reading in normalized if reading["normalizationStatus"] == "ACCEPTED")
    rejected = total - accepted
    duplicates = len(_detect_duplicates(raw))
    dropout_windows = sum(1 for event in events if event["eventType"] in ("DROPOUT_CONTEXT_FLAGGED", "SEQUENCE_GAP_DETECTED"))
    outliers = sum(1 for event in events if event["eventType"] == "OUTLIER_REJECTED")
    drift_candidates = sum(1 for event in events if event["eventType"] == "DRIFT_CANDIDATE")
    weak_signal = sum(1 for event in events if event["eventType"] == "WEAK_SIGNAL_FLAGGED")
    low_battery = sum(1 for event in events if event["eventType"] == "LOW_BATTERY_FLAGGED")
    evidence_candidates = sum(1 for reading in normalized if reading["evidenceCandidate"])
    clean_evidence_percentage = round((evidence_candidates / max(1, accepted)) * 100, 2)
    duplicate_rejection_rate = round((duplicates / max(1, total)) * 100, 2)
    outlier_rate = round((outliers / max(1, total)) * 100, 2)

    return {
        "caseId": case_id,
        "pipelineName": "Sentinel Data Trust Pipeline",
        "pipelineAcronym": "SDTP",
        "pipelineVersion": "sdtp-v2",
        "stages": SDTP_STAGES,
        "metrics": {
            "totalReadings": total,
            "acceptedReadings": accepted,
            "rejectedReadings": rejected,
            "duplicateRejectionRatePercent": duplicate_rejection_rate,
            "dropoutWindows": dropout_windows,
            "outlierRatePercent": outlier_rate,
            "driftCandidates": drift_candidates,
            "weakSignalReadings": weak_signal,
            "lowBatteryReadings": low_battery,
            "cleanEvidencePercentage": clean_evidence_percentage,
            "evidenceCandidateCount": evidence_candidates,
        },
        "qualityEventRoute": f"/cases/{case_id}/quality-events.json",
        "rejectedReadingsRoute": f"/cases/{case_id}/rejected-readings.json?offset=0&limit=100",
        "claimBoundary": "SDTP metrics are deterministic synthetic-demo quality metrics only, not production validation.",
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "sersAdvisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def data_quality_json() -> dict[str, Any]:
    cases = load_cases()
    reports = [quality_report_json(case["caseId"]) for case in cases]
    aggregate = {
        "totalReadings": sum(report["metrics"]["totalReadings"] for report in reports),
        "acceptedReadings": sum(report["metrics"]["acceptedReadings"] for report in reports),
        "rejectedReadings": sum(report["metrics"]["rejectedReadings"] for report in reports),
        "dropoutWindows": sum(report["metrics"]["dropoutWindows"] for report in reports),
        "driftCandidates": sum(report["metrics"]["driftCandidates"] for report in reports),
        "weakSignalReadings": sum(report["metrics"]["weakSignalReadings"] for report in reports),
        "lowBatteryReadings": sum(report["metrics"]["lowBatteryReadings"] for report in reports),
    }
    return {
        "pipelineName": "Sentinel Data Trust Pipeline",
        "pipelineAcronym": "SDTP",
        "pipelineVersion": "sdtp-v2",
        "goal": "Make the cleaning layer explainable, measurable, and defensible before evidence generation.",
        "stages": SDTP_STAGES,
        "aggregateMetrics": aggregate,
        "caseReports": reports,
        "routes": [
            "/data-quality",
            "/data-quality.json",
            "/cases/blocked-unresolved-pallet/quality-events.json",
            "/cases/blocked-unresolved-pallet/rejected-readings.json?offset=0&limit=100",
        ],
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "autonomousActionsAllowed": False,
    }


def render_data_quality_page() -> str:
    payload = data_quality_json()
    primary = quality_report_json("blocked-unresolved-pallet")
    metrics = primary["metrics"]

    stage_rows = [[stage["stage"], stage["name"], stage["purpose"]] for stage in SDTP_STAGES]
    metric_rows = [
        ["Accepted readings", metrics["acceptedReadings"]],
        ["Rejected readings", metrics["rejectedReadings"]],
        ["Duplicate rejection rate", f'{metrics["duplicateRejectionRatePercent"]}%'],
        ["Dropout windows", metrics["dropoutWindows"]],
        ["Outlier rate", f'{metrics["outlierRatePercent"]}%'],
        ["Drift candidates", metrics["driftCandidates"]],
        ["Weak-signal readings", metrics["weakSignalReadings"]],
        ["Low-battery readings", metrics["lowBatteryReadings"]],
        ["Clean evidence percentage", f'{metrics["cleanEvidencePercentage"]}%'],
    ]

    body = f"""
  <header data-testid="data-quality-page">
    {global_nav()}
    <h1>Sentinel Data Trust Pipeline</h1>
    <p>SDTP v2 turns raw synthetic sensor readings into accepted evidence candidates, quality warnings, and rejected readings.</p>
    {badge("SDTP v2", "good")}{badge("Synthetic only", "warn")}{badge("No autonomous action", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="sdtp-summary">
        <h2>Pipeline goal</h2>
        <p>{html.escape(payload["goal"])}</p>
        <p>{html.escape(primary["claimBoundary"])}</p>
      </article>
      <article class="panel" data-testid="sdtp-visible-metrics">
        <h2>Visible quality metrics</h2>
        {_table(["Metric", "Value"], metric_rows, "sdtp-metrics-table")}
      </article>
    </section>
    <section class="panel" data-testid="sdtp-stages">
      <h2>Cleaning stages</h2>
      {_table(["Stage", "Name", "Purpose"], stage_rows, "sdtp-stages-table")}
    </section>
    <section class="panel">
      <div class="toolbar">
        <a class="button" href="/data-quality.json">Data quality JSON</a>
        <a class="button" href="/cases/blocked-unresolved-pallet/quality-events.json">Quality events</a>
        <a class="button" href="/cases/blocked-unresolved-pallet/rejected-readings.json?offset=0&limit=100">Rejected readings</a>
        <a class="button" href="/cases/blocked-unresolved-pallet/normalized-sensor-window.json?offset=0&limit=25">Normalized readings</a>
      </div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel SDTP Data Quality", body)
