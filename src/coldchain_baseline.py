"""Deterministic ColdChain Sentinel baseline and review packet."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_FIXTURE = ROOT / "fixtures" / "baseline-shipment.json"


def load_fixture(path: Path = BASELINE_FIXTURE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError(f"timestamp must be UTC/Z: {value}")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def detect_excursion(case: dict[str, Any]) -> dict[str, Any]:
    max_c = case["shipment"]["temperatureRangeC"]["max"]
    readings = sorted(
        (r for r in case["sensorReadings"] if r["quality"] == "OK"),
        key=lambda reading: parse_utc(reading["timestampUtc"]),
    )

    start = None
    affected_zone = None
    for reading in readings:
        if start is None and reading["temperatureC"] > max_c:
            start = reading
            affected_zone = reading["zoneId"]
            continue
        if start is not None and reading["temperatureC"] <= max_c:
            minutes = int(
                (parse_utc(reading["timestampUtc"]) - parse_utc(start["timestampUtc"])).total_seconds() // 60
            )
            return {
                "startUtc": start["timestampUtc"],
                "endUtc": reading["timestampUtc"],
                "durationMinutes": minutes,
                "thresholdMaxC": max_c,
                "zoneId": affected_zone,
                "evidenceIds": sorted({start["evidenceId"], reading["evidenceId"], "E-CC-002"}),
            }

    raise ValueError("no closed high-temperature excursion found")


def resolve_pallets(case: dict[str, Any], zone_id: str) -> dict[str, list[str]]:
    mapped = []
    unresolved = []
    valid_zone_pallets = {
        pallet_id
        for mapping in case["zoneMappings"]
        if mapping["zoneId"] == zone_id
        for pallet_id in mapping["palletIds"]
    }

    for pallet in case["pallets"]:
        if pallet["id"] in valid_zone_pallets and pallet["zoneId"] == zone_id:
            mapped.append(pallet["id"])
        else:
            unresolved.append(pallet["id"])

    return {"mappedPalletIds": mapped, "unresolvedPalletIds": unresolved}


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("dataClassification") != "synthetic":
        raise ValueError("Batch baseline accepts synthetic fixtures only")

    excursion = detect_excursion(case)
    pallets = resolve_pallets(case, excursion["zoneId"])
    blockers = ["TEMPERATURE_EXCURSION_DETECTED"]
    if pallets["unresolvedPalletIds"]:
        blockers.append("UNRESOLVED_PALLET_MAPPING")
    if case["reviewPolicy"].get("humanReviewRequired", True):
        blockers.append("HUMAN_REVIEW_REQUIRED")

    return {
        "shipmentId": case["shipment"]["id"],
        "excursion": excursion,
        "mappedPalletIds": pallets["mappedPalletIds"],
        "unresolvedPalletIds": pallets["unresolvedPalletIds"],
        "reviewStatus": "HUMAN_REVIEW_REQUIRED",
        "finalDisposition": "BLOCKED",
        "autonomousActionsAllowed": False,
        "blockers": blockers,
    }


def build_review_packet(case: dict[str, Any]) -> dict[str, Any]:
    result = evaluate_case(case)
    unresolved = result["unresolvedPalletIds"]
    return {
        "packetId": "PACKET-SYN-001",
        "caseId": "CASE-SYN-001",
        "dataClassification": "synthetic",
        "productBoundary": "Synthetic deterministic hackathon demo; not a validated pharmaceutical, medical, logistics compliance, or safety product.",
        "summary": "Synthetic cold-chain excursion requires human review before any consequential action.",
        "result": result,
        "blockingReasons": [
            "Temperature excursion detected.",
            "PAL-SYN-1004 has missing zone mapping.",
            "Final disposition cannot be completed safely from the deterministic baseline.",
        ],
        "prohibitedAutonomousActions": [
            "No autonomous release.",
            "No autonomous quarantine.",
            "No autonomous discard.",
            "No autonomous reroute.",
            "No autonomous customer notification.",
        ],
        "reviewerChecklist": [
            "Confirm the synthetic excursion window and duration.",
            "Inspect mapped pallets PAL-SYN-1001, PAL-SYN-1002, and PAL-SYN-1003.",
            "Resolve missing zone mapping for PAL-SYN-1004.",
            "Confirm no operational disposition is taken from this demo packet.",
            "Record any real-world decision outside this hackathon demo system.",
        ],
        "nextInspection": [
            "Request the zone or handling record for PAL-SYN-1004.",
            "Review source evidence E-CC-001, E-CC-002, E-CC-003, E-CC-004, and E-CC-006.",
            "Keep final disposition blocked until a qualified reviewer resolves the missing mapping.",
        ],
        "limitations": [
            "Synthetic demo data only.",
            "Deterministic rules are authoritative.",
            "No provider output used.",
            "Human review required.",
            "Final disposition blocked.",
            "No autonomous release, quarantine, discard, reroute, or customer notification.",
        ],
        "unresolvedEvidence": [f"{pallet_id} has missing zone mapping." for pallet_id in unresolved],
    }


def self_check() -> None:
    case = load_fixture()
    result = evaluate_case(case)
    packet = build_review_packet(case)
    expected = case["expected"]

    assert result["excursion"]["startUtc"] == expected["excursionStartUtc"]
    assert result["excursion"]["endUtc"] == expected["excursionEndUtc"]
    assert result["excursion"]["durationMinutes"] == expected["durationMinutes"]
    assert result["mappedPalletIds"] == expected["mappedPalletIds"]
    assert result["unresolvedPalletIds"] == expected["unresolvedPalletIds"]
    assert result["finalDisposition"] == expected["finalDisposition"]
    assert result["reviewStatus"] == expected["reviewStatus"]
    assert result["autonomousActionsAllowed"] is False
    assert "TEMPERATURE_EXCURSION_DETECTED" in result["blockers"]
    assert "UNRESOLVED_PALLET_MAPPING" in result["blockers"]
    assert packet["dataClassification"] == "synthetic"
    assert "No autonomous release." in packet["prohibitedAutonomousActions"]
    assert packet["unresolvedEvidence"] == ["PAL-SYN-1004 has missing zone mapping."]


if __name__ == "__main__":
    self_check()
    print(json.dumps(build_review_packet(load_fixture()), indent=2, sort_keys=True))
