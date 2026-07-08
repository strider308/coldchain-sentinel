"""Static synthetic case engine for ColdChain Sentinel beta routes."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

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


def case_result(case: dict[str, Any], simulate_resolved: bool = False) -> dict[str, Any]:
    mapped = list(case["mappedPalletIds"])
    unresolved = list(case["unresolvedPalletIds"])
    blockers = list(case["blockers"])
    review_status = case["reviewStatus"]
    final_disposition = case["finalDisposition"]

    if simulate_resolved and case["caseId"] == BASELINE_CASE_ID:
        mapped = sorted(set(mapped + unresolved))
        unresolved = []
        blockers = [blocker for blocker in blockers if blocker != "UNRESOLVED_PALLET_MAPPING"]
        review_status = "REVIEW_PACKET_COMPLETE"
        final_disposition = "MAPPING_REVIEW_SIMULATED"

    return {
        "shipmentId": case["shipmentId"],
        "excursion": case["excursion"],
        "mappedPalletIds": mapped,
        "unresolvedPalletIds": unresolved,
        "reviewStatus": review_status,
        "finalDisposition": final_disposition,
        "autonomousActionsAllowed": False,
        "blockers": blockers,
    }


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
    }


def evidence_json(case: dict[str, Any], simulate_resolved: bool = False) -> dict[str, Any]:
    packet = case_packet(case, simulate_resolved)
    return {
        "caseId": packet["caseId"],
        "shipmentId": packet["result"]["shipmentId"],
        "scenarioSummary": packet["scenarioSummary"],
        "result": packet["result"],
        "timeline": packet["evidenceTimeline"],
        "reviewerChecklist": packet["reviewerChecklist"],
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
            "## Evidence Timeline",
            *timeline_lines,
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
