"""Static synthetic case engine for ColdChain Sentinel beta routes."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sensor_engine import sensor_summary

ROOT = Path(__file__).resolve().parents[1]
CASES_FIXTURE = ROOT / "fixtures" / "synthetic-cases.json"
BASELINE_CASE_ID = "blocked-unresolved-pallet"
PROHIBITED_ACTIONS = [
    "No autonomous release.",
    "No autonomous quarantine.",
    "No autonomous discard.",
    "No autonomous reroute.",
    "No autonomous customer notification.",
]


def load_cases() -> list[dict[str, Any]]:
    data = json.loads(CASES_FIXTURE.read_text(encoding="utf-8"))
    cases = data["cases"]
    if any(case.get("autonomousActionsAllowed") is not False for case in cases):
        raise ValueError("synthetic cases must not allow autonomous actions")
    return cases


def get_case(case_id: str = BASELINE_CASE_ID) -> dict[str, Any]:
    for case in load_cases():
        if case["caseId"] == case_id:
            return copy.deepcopy(case)
    raise KeyError(case_id)


def parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError(f"timestamp must be UTC/Z: {value}")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def temperature_readings(case: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(case["temperatureReadings"], key=lambda reading: parse_utc(reading["timestampUtc"]))


def detect_excursion(case: dict[str, Any]) -> dict[str, Any] | None:
    threshold = float(case["thresholdMaxC"])
    readings = temperature_readings(case)
    start = None
    high_evidence = []
    for reading in readings:
        if reading["temperatureC"] > threshold:
            start = start or reading
            high_evidence.append(reading["evidenceId"])
            continue
        if start is not None:
            minutes = int(
                (parse_utc(reading["timestampUtc"]) - parse_utc(start["timestampUtc"])).total_seconds() // 60
            )
            return {
                "startUtc": start["timestampUtc"],
                "endUtc": reading["timestampUtc"],
                "durationMinutes": minutes,
                "thresholdMaxC": threshold,
                "zoneId": start["zoneId"],
                "evidenceIds": high_evidence,
            }
    return None


def zone_mapped_pallets(case: dict[str, Any], zone_id: str | None) -> list[str]:
    if zone_id is None:
        mapped = {pallet for mapping in case["zoneMappings"] for pallet in mapping["palletIds"]}
    else:
        mapped = {
            pallet
            for mapping in case["zoneMappings"]
            if mapping["zoneId"] == zone_id
            for pallet in mapping["palletIds"]
        }
    return [pallet for pallet in case["palletIds"] if pallet in mapped]


def unresolved_pallets(case: dict[str, Any], mapped: list[str]) -> list[str]:
    mapped_set = set(mapped)
    return [pallet for pallet in case["palletIds"] if pallet not in mapped_set]


def derive_blockers(case: dict[str, Any], excursion: dict[str, Any] | None, unresolved: list[str]) -> list[str]:
    blockers = []
    if excursion:
        blockers.append("TEMPERATURE_EXCURSION_DETECTED")
    if unresolved:
        blockers.append("UNRESOLVED_PALLET_MAPPING")
    if excursion:
        blockers.append("HUMAN_REVIEW_REQUIRED")
    if not excursion:
        blockers.append("SYNTHETIC_CONTROL_REVIEW")
    return blockers


def derive_review_status(excursion: dict[str, Any] | None) -> str:
    return "HUMAN_REVIEW_REQUIRED" if excursion else "CONTROL_REVIEW_COMPLETE"


def derive_final_disposition(excursion: dict[str, Any] | None) -> str:
    return "BLOCKED" if excursion else "NO_EXCURSION_CONTROL"


def case_result(case: dict[str, Any], simulate_resolved: bool = False) -> dict[str, Any]:
    excursion = detect_excursion(case)
    mapped = zone_mapped_pallets(case, excursion["zoneId"] if excursion else None)
    unresolved = unresolved_pallets(case, mapped)
    blockers = derive_blockers(case, excursion, unresolved)
    review_status = derive_review_status(excursion)
    final_disposition = derive_final_disposition(excursion)

    if simulate_resolved and case["caseId"] == BASELINE_CASE_ID:
        mapped = sorted(set(mapped + unresolved))
        unresolved = []
        blockers = [blocker for blocker in blockers if blocker != "UNRESOLVED_PALLET_MAPPING"]
        review_status = "REVIEW_PACKET_COMPLETE"
        final_disposition = "MAPPING_REVIEW_SIMULATED"

    return {
        "shipmentId": case["shipmentId"],
        "excursion": excursion,
        "mappedPalletIds": mapped,
        "unresolvedPalletIds": unresolved,
        "reviewStatus": review_status,
        "finalDisposition": final_disposition,
        "autonomousActionsAllowed": False,
        "blockers": blockers,
    }


def rule_trace(case: dict[str, Any], simulate_resolved: bool = False) -> list[dict[str, Any]]:
    result = case_result(case, simulate_resolved)
    excursion = result["excursion"]
    readings = temperature_readings(case)
    high = [reading for reading in readings if reading["temperatureC"] > case["thresholdMaxC"]]
    mapped = result["mappedPalletIds"]
    unresolved = result["unresolvedPalletIds"]
    trace = [
        {
            "ruleId": "TEMP_THRESHOLD_CHECK",
            "ruleName": "Temperature threshold check",
            "status": "REVIEW_REQUIRED" if high else "PASS",
            "inputSummary": f'{len(readings)} synthetic readings checked against {case["thresholdMaxC"]} C.',
            "outputSummary": "Threshold exceeded in synthetic telemetry." if high else "No synthetic readings exceeded threshold.",
            "evidenceIds": [reading["evidenceId"] for reading in high],
            "safetyImpact": "Threshold breach requires deterministic review." if high else "Control case remains demo-only.",
        },
        {
            "ruleId": "EXCURSION_WINDOW_CALCULATION",
            "ruleName": "Excursion window calculation",
            "status": "INFO" if excursion else "PASS",
            "inputSummary": "Closed breach window derived from synthetic readings.",
            "outputSummary": (
                f'{excursion["startUtc"]} to {excursion["endUtc"]}; {excursion["durationMinutes"]} minutes.'
                if excursion
                else "No excursion window detected."
            ),
            "evidenceIds": excursion["evidenceIds"] if excursion else [],
            "safetyImpact": "Excursion duration is carried into reviewer packet." if excursion else "No excursion fact is created.",
        },
        {
            "ruleId": "ZONE_IMPACT_IDENTIFICATION",
            "ruleName": "Zone impact identification",
            "status": "INFO",
            "inputSummary": "Affected zone comes from first over-threshold synthetic reading.",
            "outputSummary": f'Zone {excursion["zoneId"]} affected.' if excursion else "No affected zone.",
            "evidenceIds": excursion["evidenceIds"] if excursion else [],
            "safetyImpact": "Zone determines pallet mapping scope." if excursion else "No zone impact is applied.",
        },
        {
            "ruleId": "PALLET_MAPPING_CHECK",
            "ruleName": "Pallet mapping check",
            "status": "REVIEW_REQUIRED" if unresolved else "PASS",
            "inputSummary": f'{len(case["palletIds"])} synthetic pallets checked against zone mappings.',
            "outputSummary": (
                f'Mapped: {", ".join(mapped) or "None"}; unresolved: {", ".join(unresolved) or "None"}.'
            ),
            "evidenceIds": [],
            "safetyImpact": "Unresolved mapping blocks packet completion." if unresolved else "Mapping is complete for synthetic review.",
        },
        {
            "ruleId": "UNRESOLVED_MAPPING_BLOCKER",
            "ruleName": "Unresolved mapping blocker",
            "status": "REVIEW_REQUIRED" if unresolved else "PASS",
            "inputSummary": "Unresolved synthetic pallet IDs are checked.",
            "outputSummary": ", ".join(unresolved) if unresolved else "No unresolved synthetic pallet mapping.",
            "evidenceIds": [],
            "safetyImpact": "Requires human review." if unresolved else "No unresolved-mapping blocker.",
        },
        {
            "ruleId": "HUMAN_REVIEW_GATE",
            "ruleName": "Human review gate",
            "status": "REVIEW_REQUIRED" if result["reviewStatus"] == "HUMAN_REVIEW_REQUIRED" else "INFO",
            "inputSummary": "Deterministic status and blockers are evaluated.",
            "outputSummary": result["reviewStatus"],
            "evidenceIds": [],
            "safetyImpact": "Reviewer packet remains non-operational.",
        },
        {
            "ruleId": "AUTONOMOUS_ACTION_DENY",
            "ruleName": "Autonomous action deny",
            "status": "PASS",
            "inputSummary": "All synthetic scenarios force autonomousActionsAllowed to false.",
            "outputSummary": "autonomousActionsAllowed: false",
            "evidenceIds": [],
            "safetyImpact": "AI and UI cannot authorize operational action.",
        },
    ]
    if simulate_resolved and case["caseId"] == BASELINE_CASE_ID:
        trace.insert(
            4,
            {
                "ruleId": "SIMULATED_MAPPING_RESOLUTION",
                "ruleName": "Simulated mapping resolution",
                "status": "INFO",
                "inputSummary": "PAL-SYN-1004 is synthetically mapped for packet completion.",
                "outputSummary": "Review packet completion is simulated; no operational action is authorized.",
                "evidenceIds": [],
                "safetyImpact": "Simulation does not authorize shipment movement.",
            },
        )
    return trace


def timeline(case: dict[str, Any], simulate_resolved: bool = False) -> list[dict[str, str]]:
    result = case_result(case, simulate_resolved)
    excursion = result["excursion"]
    rows = []
    if excursion:
        rows.extend(
            [
                {"time": excursion["startUtc"], "event": "Excursion starts"},
                {"time": excursion["endUtc"], "event": "Excursion ends"},
                {"time": "Duration", "event": f'{excursion["durationMinutes"]} minutes'},
                {"time": "Zone", "event": excursion["zoneId"]},
                {"time": "Evidence IDs", "event": ", ".join(excursion["evidenceIds"])},
            ]
        )
    else:
        rows.append({"time": "Control", "event": "No temperature excursion in synthetic fixture"})
    rows.extend(
        [
            {"time": "Mapped pallets", "event": ", ".join(result["mappedPalletIds"]) or "None"},
            {"time": "Unresolved pallets", "event": ", ".join(result["unresolvedPalletIds"]) or "None"},
            {"time": "Final disposition", "event": result["finalDisposition"]},
            {"time": "Review status", "event": result["reviewStatus"]},
        ]
    )
    return rows


def telemetry_timeline(case: dict[str, Any]) -> list[dict[str, Any]]:
    threshold = case["thresholdMaxC"]
    return [
        {
            "timestampUtc": reading["timestampUtc"],
            "temperatureC": reading["temperatureC"],
            "zoneId": reading["zoneId"],
            "thresholdExceeded": reading["temperatureC"] > threshold,
            "evidenceId": reading["evidenceId"],
        }
        for reading in temperature_readings(case)
    ]


def case_packet(case: dict[str, Any], simulate_resolved: bool = False) -> dict[str, Any]:
    result = case_result(case, simulate_resolved)
    blocking_reasons = [blocker.replace("_", " ").title() + "." for blocker in result["blockers"]]
    if not result["blockers"]:
        blocking_reasons = ["Synthetic mapping review simulated; no operational disposition is authorized."]
    return {
        "packetId": f'PACKET-{case["caseId"]}',
        "caseId": case["caseId"],
        "caseTitle": case["caseTitle"],
        "dataClassification": "synthetic",
        "scenarioSummary": case["scenarioSummary"],
        "productBoundary": "Synthetic deterministic hackathon demo; not a validated pharmaceutical, medical, logistics compliance, or safety product.",
        "summary": case["scenarioSummary"],
        "result": result,
        "blockingReasons": blocking_reasons,
        "prohibitedAutonomousActions": PROHIBITED_ACTIONS,
        "reviewerChecklist": list(case["reviewerChecklist"]),
        "nextInspection": list(case["reviewerChecklist"]),
        "limitations": list(case["safetyDisclaimers"]) + PROHIBITED_ACTIONS,
        "unresolvedEvidence": [f"{pallet_id} has missing zone mapping." for pallet_id in result["unresolvedPalletIds"]],
        "evidenceTimeline": timeline(case, simulate_resolved),
        "telemetryTimeline": telemetry_timeline(case),
        "ruleTrace": rule_trace(case, simulate_resolved),
    }


def evidence_json(case: dict[str, Any], simulate_resolved: bool = False) -> dict[str, Any]:
    packet = case_packet(case, simulate_resolved)
    return {
        "caseId": packet["caseId"],
        "shipmentId": packet["result"]["shipmentId"],
        "scenarioSummary": packet["scenarioSummary"],
        "result": packet["result"],
        "timeline": packet["evidenceTimeline"],
        "telemetryTimeline": packet["telemetryTimeline"],
        "trace": packet["ruleTrace"],
        "reviewerChecklist": packet["reviewerChecklist"],
        "safetyDisclaimers": packet["limitations"],
    }


def trace_json(case: dict[str, Any], simulate_resolved: bool = False) -> dict[str, Any]:
    packet = case_packet(case, simulate_resolved)
    sensors = sensor_summary(case, packet["result"])
    return {
        "caseId": packet["caseId"],
        "shipmentId": packet["result"]["shipmentId"],
        "trace": packet["ruleTrace"],
        "sensorAggregationReference": {
            "generatedReadingCount": sensors["generatedReadingCount"],
            "aboveThresholdReadingCount": sensors["aggregationSummary"]["aboveThresholdReadingCount"],
            "excursionWindowCount": len(sensors["excursionWindows"]),
            "impactedZones": sensors["impactedZones"],
        },
        "result": packet["result"],
        "safetyDisclaimers": packet["limitations"],
    }


def export_markdown(case: dict[str, Any], simulate_resolved: bool = False) -> str:
    packet = case_packet(case, simulate_resolved)
    result = packet["result"]
    excursion = result["excursion"]
    excursion_lines = ["- Excursion: none in synthetic control fixture."]
    if excursion:
        excursion_lines = [
            f'- Excursion start: {excursion["startUtc"]}',
            f'- Excursion end: {excursion["endUtc"]}',
            f'- Duration: {excursion["durationMinutes"]} minutes',
            f'- Zone: {excursion["zoneId"]}',
            f'- Evidence IDs: {", ".join(excursion["evidenceIds"])}',
        ]

    def bullet(values: list[str]) -> str:
        return "\n".join(f"- {value}" for value in values) or "- None"

    simulation_section = []
    if simulate_resolved and case["caseId"] == BASELINE_CASE_ID:
        before = case_result(case)
        simulation_section = [
            "",
            "## Simulated Resolution",
            "- Simulation: PAL-SYN-1004 synthetically mapped for review packet completion.",
            f'- Before unresolvedPalletIds: {", ".join(before["unresolvedPalletIds"]) or "None"}',
            f'- Before finalDisposition: {before["finalDisposition"]}',
            f'- Before reviewStatus: {before["reviewStatus"]}',
            f'- After unresolvedPalletIds: {", ".join(result["unresolvedPalletIds"]) or "None"}',
            f'- After finalDisposition: {result["finalDisposition"]}',
            f'- After reviewStatus: {result["reviewStatus"]}',
            f'- After autonomousActionsAllowed: {str(result["autonomousActionsAllowed"]).lower()}',
            "- This completes a synthetic review packet only and does not authorize any operational action.",
        ]

    timeline_lines = [f'- {row["time"]}: {row["event"]}' for row in packet["evidenceTimeline"]]
    telemetry_lines = [
        f'- {row["timestampUtc"]}: {row["temperatureC"]} C, zone {row["zoneId"]}, thresholdExceeded {str(row["thresholdExceeded"]).lower()}, evidence {row["evidenceId"]}'
        for row in packet["telemetryTimeline"]
    ]
    trace_lines = [
        f'- {row["ruleId"]}: {row["status"]} - {row["outputSummary"]} Safety impact: {row["safetyImpact"]}'
        for row in packet["ruleTrace"]
    ]
    return "\n".join(
        [
            f'# {packet["caseTitle"]}',
            "",
            f'- caseId: {packet["caseId"]}',
            f'- shipmentId: {result["shipmentId"]}',
            f'- scenarioSummary: {packet["scenarioSummary"]}',
            *excursion_lines,
            f'- Mapped pallets: {", ".join(result["mappedPalletIds"]) or "None"}',
            f'- Unresolved pallets: {", ".join(result["unresolvedPalletIds"]) or "None"}',
            f'- Blockers: {", ".join(result["blockers"]) or "None"}',
            f'- finalDisposition: {result["finalDisposition"]}',
            f'- reviewStatus: {result["reviewStatus"]}',
            f'- autonomousActionsAllowed: {str(result["autonomousActionsAllowed"]).lower()}',
            "",
            "## Synthetic Telemetry Summary",
            *telemetry_lines,
            "",
            "## Evidence Timeline",
            *timeline_lines,
            "",
            "## Deterministic Rule Trace",
            *trace_lines,
            "",
            "## Reviewer Checklist",
            bullet(packet["reviewerChecklist"]),
            "",
            "## Fireworks Assistant Role",
            "Fireworks may provide an optional non-authoritative reviewer explanation only. Deterministic rules remain authoritative.",
            "Fireworks output is quality-gated; rejected, malformed, unsafe, or low-quality output falls back to deterministic text.",
            "",
            "## Safety Disclaimers",
            bullet(packet["limitations"]),
            *simulation_section,
            "",
        ]
    )


def audit_markdown(case: dict[str, Any], simulate_resolved: bool = False) -> str:
    packet = case_packet(case, simulate_resolved)
    sensors = sensor_summary(case, packet["result"])
    sensor_lines = [
        f'- Generated readings represented: {sensors["generatedReadingCount"]}',
        f'- Sensor count: {sensors["sensorCount"]}',
        f'- Zone count: {sensors["zoneCount"]}',
        f'- Above-threshold readings: {sensors["aggregationSummary"]["aboveThresholdReadingCount"]}',
        f'- Rejected/noisy readings: {sensors["aggregationSummary"]["rejectedNoisyReadingCount"]}',
        f'- Excursion windows: {len(sensors["excursionWindows"])}',
        f'- Impacted zones: {", ".join(sensors["impactedZones"]) or "None"}',
        f'- Readings reduced into deterministic review packet: {sensors["generatedReadingCount"]}',
    ]
    quality_lines = [f"- {label}: {count}" for label, count in sorted(sensors["sensorQualitySummary"].items())]
    window_lines = [
        f'- {window["zoneId"]}: {window["startUtc"]} to {window["endUtc"]}; {window["durationMinutes"]} minutes'
        for window in sensors["excursionWindows"]
    ] or ["- None"]
    simulation_lines = []
    if simulate_resolved and case["caseId"] == BASELINE_CASE_ID:
        simulation_lines = [
            "",
            "## Audit Simulation Details",
            "- PAL-SYN-1004 is synthetically mapped for local review-session packet completion.",
            "- This is a demo archive packet state only; no operational action is authorized.",
        ]
    return "\n".join(
        [
            f'# Audit Packet - {packet["caseTitle"]}',
            "",
            export_markdown(case, simulate_resolved),
            "## High-Volume Sensor Aggregation Summary",
            *sensor_lines,
            "",
            "## Sensor Quality Labels Summary",
            *quality_lines,
            "",
            "## Sensor Excursion Windows",
            *window_lines,
            "",
            "## Reviewer Local Notes",
            "Reviewer local notes: stored only in browser localStorage and not included in server export.",
            "",
            "## Audit Packet Boundary",
            "- Local checklist and notes are browser-only demo state.",
            "- Fireworks output is optional, quality-gated, and non-authoritative.",
            "- Deterministic rules remain authoritative.",
            "- No autonomous operational action is allowed.",
            *simulation_lines,
            "",
        ]
    )
