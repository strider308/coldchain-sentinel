"""Zone Consensus Engine v2.

Synthetic-only redundancy and consensus scoring for ColdChain Sentinel.
The goal is to show that the platform does not overreact to one bad sensor.
"""

from __future__ import annotations

import html
from collections import defaultdict
from statistics import mean
from typing import Any

from case_engine import get_case, load_cases
from data_quality_v2 import quality_events_json
from sensor_data_model_v2 import normalized_sensor_window_json
from serve_dashboard import badge, global_nav, page

ZCE_FACTORS: list[str] = [
    "sensorTrustScore",
    "zoneConsensusScore",
    "neighborAgreement",
    "temporalPersistence",
    "singleSensorSpikePenalty",
    "multiSensorConfirmationBonus",
    "dropoutPenalty",
    "driftPenalty",
    "signalQualityPenalty",
]

ZCE_SAFETY_BOUNDARY = [
    "Synthetic demo data only.",
    "ZCE is deterministic reviewer intelligence, not an operational release decision.",
    "No autonomous release, quarantine, discard, reroute, or customer notification.",
    "Deterministic case rules remain authoritative.",
    "SERS remains advisory only.",
    "No production, pharma, compliance, or real-world validation claim.",
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


def _all_normalized(case_id: str) -> list[dict[str, Any]]:
    return normalized_sensor_window_json(case_id, 0, 10_000)["readings"]


def _case_threshold(case_id: str) -> float:
    case = get_case(case_id)
    return float(case.get("thresholdMaxC", 8.0))


def _events_by_sensor(case_id: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in quality_events_json(case_id)["events"]:
        sensor_id = str(event.get("sensorId", "UNKNOWN_SENSOR"))
        grouped[sensor_id].append(event)
    return grouped


def _quality_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        counts[str(event.get("eventType"))] += 1
    return dict(counts)


def sensor_trust_table(case_id: str) -> list[dict[str, Any]]:
    readings = _all_normalized(case_id)
    events_by_sensor = _events_by_sensor(case_id)
    by_sensor: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for reading in readings:
        by_sensor[str(reading["sensorId"])].append(reading)

    rows: list[dict[str, Any]] = []
    for sensor_id, sensor_readings in sorted(by_sensor.items()):
        accepted = sum(1 for reading in sensor_readings if reading["normalizationStatus"] == "ACCEPTED")
        rejected = sum(1 for reading in sensor_readings if reading["normalizationStatus"] == "REJECTED")
        evidence_candidates = sum(1 for reading in sensor_readings if reading["evidenceCandidate"])
        warnings = sum(len(reading["normalizationWarnings"]) for reading in sensor_readings)
        event_counts = _quality_counts(events_by_sensor.get(sensor_id, []))
        weak_signal = event_counts.get("WEAK_SIGNAL_FLAGGED", 0)
        low_battery = event_counts.get("LOW_BATTERY_FLAGGED", 0)
        dropout = event_counts.get("DROPOUT_CONTEXT_FLAGGED", 0) + event_counts.get("SEQUENCE_GAP_DETECTED", 0)
        drift = event_counts.get("DRIFT_CANDIDATE", 0)
        outliers = event_counts.get("OUTLIER_REJECTED", 0)

        trust_score = 100.0
        trust_score -= rejected * 18
        trust_score -= outliers * 18
        trust_score -= dropout * 1.2
        trust_score -= drift * 6
        trust_score -= weak_signal * 5
        trust_score -= low_battery * 4
        trust_score -= max(0, warnings - evidence_candidates) * 0.5
        trust_score = round(max(0.0, min(100.0, trust_score)), 2)

        if trust_score >= 90:
            trust_band = "HIGH_TRUST"
        elif trust_score >= 70:
            trust_band = "REVIEW_TRUST"
        else:
            trust_band = "LOW_TRUST"

        zones = sorted({str(reading["zoneId"]) for reading in sensor_readings})
        rows.append(
            {
                "sensorId": sensor_id,
                "zoneIds": zones,
                "sensorTrustScore": trust_score,
                "trustBand": trust_band,
                "acceptedReadings": accepted,
                "rejectedReadings": rejected,
                "evidenceCandidateCount": evidence_candidates,
                "weakSignalEvents": weak_signal,
                "lowBatteryEvents": low_battery,
                "dropoutEvents": dropout,
                "driftEvents": drift,
                "outlierEvents": outliers,
                "explanation": (
                    "High trust synthetic sensor."
                    if trust_band == "HIGH_TRUST"
                    else "Trust reduced by synthetic quality warnings or rejected readings."
                ),
            }
        )

    return rows


def _zone_time_buckets(readings: list[dict[str, Any]], threshold: float) -> dict[str, dict[str, list[dict[str, Any]]]]:
    buckets: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for reading in readings:
        if reading["normalizationStatus"] != "ACCEPTED":
            continue
        zone_id = str(reading["zoneId"])
        timestamp = str(reading["timestampUtc"])
        buckets[zone_id][timestamp].append(reading)
    return buckets


def _zone_consensus_rows(case_id: str) -> list[dict[str, Any]]:
    readings = _all_normalized(case_id)
    threshold = _case_threshold(case_id)
    trust_by_sensor = {row["sensorId"]: row for row in sensor_trust_table(case_id)}
    buckets = _zone_time_buckets(readings, threshold)

    rows: list[dict[str, Any]] = []

    for zone_id, by_timestamp in sorted(buckets.items()):
        accepted_zone_readings = [reading for timestamp_rows in by_timestamp.values() for reading in timestamp_rows]
        sensor_ids = sorted({str(reading["sensorId"]) for reading in accepted_zone_readings})
        total_sensors = max(1, len(sensor_ids))

        threshold_timestamps: list[dict[str, Any]] = []
        single_sensor_spikes = 0
        multi_sensor_windows = 0
        ignored_spikes: list[dict[str, Any]] = []

        for timestamp, timestamp_readings in sorted(by_timestamp.items()):
            above = [
                reading
                for reading in timestamp_readings
                if isinstance(reading.get("temperatureC"), (int, float)) and float(reading["temperatureC"]) > threshold
            ]
            above_sensors = sorted({str(reading["sensorId"]) for reading in above})
            if above_sensors:
                threshold_timestamps.append(
                    {
                        "timestampUtc": timestamp,
                        "aboveThresholdSensorCount": len(above_sensors),
                        "aboveThresholdSensors": above_sensors,
                    }
                )
                if len(above_sensors) == 1:
                    single_sensor_spikes += 1
                    ignored_spikes.append(
                        {
                            "timestampUtc": timestamp,
                            "sensorId": above_sensors[0],
                            "reason": "Only one accepted sensor crossed threshold in this timestamp bucket.",
                        }
                    )
                else:
                    multi_sensor_windows += 1

        confirming_sensors = sorted(
            {
                str(reading["sensorId"])
                for reading in accepted_zone_readings
                if isinstance(reading.get("temperatureC"), (int, float)) and float(reading["temperatureC"]) > threshold
            }
        )
        neighbor_agreement = round(len(confirming_sensors) / total_sensors, 3)
        temporal_persistence = len(threshold_timestamps)

        dropout_penalty = sum(trust_by_sensor.get(sensor_id, {}).get("dropoutEvents", 0) for sensor_id in sensor_ids)
        drift_penalty = sum(trust_by_sensor.get(sensor_id, {}).get("driftEvents", 0) for sensor_id in sensor_ids)
        signal_quality_penalty = sum(trust_by_sensor.get(sensor_id, {}).get("weakSignalEvents", 0) for sensor_id in sensor_ids)
        avg_trust = mean([trust_by_sensor.get(sensor_id, {}).get("sensorTrustScore", 0.0) for sensor_id in sensor_ids]) if sensor_ids else 0.0

        single_sensor_spike_penalty = single_sensor_spikes * 8
        multi_sensor_confirmation_bonus = multi_sensor_windows * 12
        consensus_score = (
            avg_trust
            + (neighbor_agreement * 30)
            + min(20, temporal_persistence * 2)
            + multi_sensor_confirmation_bonus
            - single_sensor_spike_penalty
            - min(15, dropout_penalty * 0.7)
            - min(15, drift_penalty * 4)
            - min(12, signal_quality_penalty * 4)
        )
        consensus_score = round(max(0.0, min(100.0, consensus_score)), 2)

        if consensus_score >= 85 and multi_sensor_windows > 0:
            consensus_band = "MULTI_SENSOR_CONFIRMED"
        elif consensus_score >= 70 and threshold_timestamps:
            consensus_band = "REVIEW_ESCALATION_CANDIDATE"
        elif threshold_timestamps:
            consensus_band = "SINGLE_SENSOR_OR_LOW_CONFIDENCE_REVIEW"
        else:
            consensus_band = "NO_CONSENSUS_EXCURSION"

        why_escalated = (
            "Escalated because accepted threshold evidence persists across the zone and redundancy score is review-worthy."
            if threshold_timestamps and consensus_score >= 70
            else "Not escalated by ZCE because multi-sensor confirmation or persistence is insufficient."
        )
        why_spike_ignored = (
            "Single-sensor threshold spikes are penalized unless neighboring sensors or temporal persistence confirm the event."
            if single_sensor_spikes
            else "No isolated single-sensor spike needed suppression in this zone."
        )
        conflict_explanation = (
            "Some sensors disagree with the zone signal; ZCE preserves the conflict for human review instead of making an automatic decision."
            if single_sensor_spikes or signal_quality_penalty or drift_penalty
            else "No meaningful synthetic sensor conflict detected for this zone."
        )

        rows.append(
            {
                "zoneId": zone_id,
                "zoneConsensusScore": consensus_score,
                "consensusBand": consensus_band,
                "sensorIds": sensor_ids,
                "confirmingSensors": confirming_sensors,
                "neighborAgreement": neighbor_agreement,
                "temporalPersistence": temporal_persistence,
                "singleSensorSpikePenalty": single_sensor_spike_penalty,
                "multiSensorConfirmationBonus": multi_sensor_confirmation_bonus,
                "dropoutPenalty": round(dropout_penalty, 2),
                "driftPenalty": round(drift_penalty, 2),
                "signalQualityPenalty": round(signal_quality_penalty, 2),
                "averageSensorTrustScore": round(avg_trust, 2),
                "ignoredSingleSensorSpikes": ignored_spikes[:10],
                "conflictingSensorExplanation": conflict_explanation,
                "whyWindowWasEscalated": why_escalated,
                "whySpikeWasIgnored": why_spike_ignored,
            }
        )

    return rows


def consensus_report_json(case_id: str) -> dict[str, Any]:
    sensor_rows = sensor_trust_table(case_id)
    zone_rows = _zone_consensus_rows(case_id)
    escalated_zones = [row for row in zone_rows if row["consensusBand"] in ("MULTI_SENSOR_CONFIRMED", "REVIEW_ESCALATION_CANDIDATE")]
    ignored_spikes = [spike for row in zone_rows for spike in row["ignoredSingleSensorSpikes"]]

    return {
        "caseId": case_id,
        "engineName": "Zone Consensus Engine",
        "engineAcronym": "ZCE",
        "engineVersion": "zce-v2",
        "goal": "Avoid overreacting to one bad sensor by scoring redundancy, trust, persistence, and conflict.",
        "factors": ZCE_FACTORS,
        "zoneConsensus": zone_rows,
        "sensorTrust": sensor_rows,
        "summary": {
            "zoneCount": len(zone_rows),
            "sensorCount": len(sensor_rows),
            "escalatedZoneCount": len(escalated_zones),
            "ignoredSingleSensorSpikeCount": len(ignored_spikes),
            "bestZoneConsensusScore": max([row["zoneConsensusScore"] for row in zone_rows] or [0]),
            "lowestSensorTrustScore": min([row["sensorTrustScore"] for row in sensor_rows] or [0]),
        },
        "humanReviewGuidance": [
            "Inspect zones with high consensus score and temporal persistence.",
            "Do not treat a single-sensor spike as enough for release/quarantine decisions.",
            "Review low-trust sensors before relying on their evidence.",
            "Use ZCE as reviewer intelligence only; deterministic rules remain authoritative.",
        ],
        "safetyBoundary": ZCE_SAFETY_BOUNDARY,
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "deterministicRulesAuthoritative": True,
        "sersAdvisoryOnly": True,
        "autonomousActionsAllowed": False,
    }


def consensus_json() -> dict[str, Any]:
    reports = [consensus_report_json(case["caseId"]) for case in load_cases()]
    return {
        "engineName": "Zone Consensus Engine",
        "engineAcronym": "ZCE",
        "engineVersion": "zce-v2",
        "goal": "Prove ColdChain Sentinel does not overreact to one bad sensor.",
        "factors": ZCE_FACTORS,
        "caseReports": reports,
        "routes": [
            "/consensus",
            "/consensus.json",
            "/cases/blocked-unresolved-pallet/consensus-report.json",
        ],
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "autonomousActionsAllowed": False,
    }


def render_consensus_page() -> str:
    payload = consensus_json()
    primary = consensus_report_json("blocked-unresolved-pallet")
    zone_rows = [
        [
            row["zoneId"],
            row["zoneConsensusScore"],
            row["consensusBand"],
            row["neighborAgreement"],
            row["temporalPersistence"],
            ", ".join(row["confirmingSensors"]) or "None",
            row["whyWindowWasEscalated"],
        ]
        for row in primary["zoneConsensus"]
    ]
    sensor_rows = [
        [
            row["sensorId"],
            ", ".join(row["zoneIds"]),
            row["sensorTrustScore"],
            row["trustBand"],
            row["acceptedReadings"],
            row["rejectedReadings"],
            row["weakSignalEvents"],
            row["lowBatteryEvents"],
            row["driftEvents"],
        ]
        for row in primary["sensorTrust"]
    ]

    conflict_items = [row["conflictingSensorExplanation"] for row in primary["zoneConsensus"]]
    spike_items = [row["whySpikeWasIgnored"] for row in primary["zoneConsensus"]]

    body = f"""
  <header data-testid="consensus-page">
    {global_nav()}
    <h1>Zone Consensus Engine</h1>
    <p>ZCE v2 scores redundancy, persistence, sensor trust, and conflict so the platform does not overreact to one bad sensor.</p>
    {badge("ZCE v2", "good")}{badge("Synthetic only", "warn")}{badge("No autonomous action", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="zce-summary">
        <h2>Consensus goal</h2>
        <p>{html.escape(payload["goal"])}</p>
        <p>Factors: {html.escape(", ".join(payload["factors"]))}</p>
      </article>
      <article class="panel status-block" data-testid="zce-boundary">
        <h2>Safety boundary</h2>
        <ul>{_items(primary["safetyBoundary"], "zce-boundary")}</ul>
      </article>
    </section>
    <section class="panel" data-testid="zone-consensus-table">
      <h2>Zone-by-zone consensus</h2>
      {_table(["Zone", "Score", "Band", "Neighbor agreement", "Temporal persistence", "Confirming sensors", "Why escalated"], zone_rows, "zce-zone-table")}
    </section>
    <section class="panel" data-testid="sensor-trust-table">
      <h2>Sensor trust table</h2>
      {_table(["Sensor", "Zones", "Trust score", "Band", "Accepted", "Rejected", "Weak signal", "Low battery", "Drift"], sensor_rows, "zce-sensor-table")}
    </section>
    <section class="grid">
      <article class="panel" data-testid="conflicting-sensor-explanation"><h2>Conflicting sensor explanation</h2><ul>{_items(conflict_items, "zce-conflict")}</ul></article>
      <article class="panel" data-testid="spike-ignored-explanation"><h2>Why this spike was ignored</h2><ul>{_items(spike_items, "zce-spike")}</ul></article>
    </section>
    <section class="panel">
      <div class="toolbar">
        <a class="button" href="/consensus.json">Consensus JSON</a>
        <a class="button" href="/cases/blocked-unresolved-pallet/consensus-report.json">Case consensus report</a>
        <a class="button" href="/data-quality">Data Quality</a>
        <a class="button" href="/data-contract">Data Contract</a>
      </div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel Zone Consensus Engine", body)
