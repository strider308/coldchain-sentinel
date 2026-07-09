from __future__ import annotations

import html
import json
from functools import lru_cache
from typing import Any

PHASE = "Phase 7 - Synthetic Scenario Simulator / What-If Lab"
VERSION = "scenario-lab-v2.0.0"

CLAIMS_BOUNDARY = {
    "dataScope": "synthetic scenario data only",
    "decisionScope": "advisory review support only",
    "authority": "deterministic rules remain authoritative",
    "sersScope": "SERS remains advisory-only",
    "noRealData": [
        "No real customer data.",
        "No real pharma data.",
        "No real logistics data.",
        "No real patient data.",
        "No real shipment data.",
        "No real sensor data.",
    ],
    "notClaimed": [
        "production validation",
        "pharma validation",
        "real-world validation",
        "compliance certification",
        "autonomous release",
        "autonomous quarantine",
        "autonomous discard",
        "autonomous reroute",
        "autonomous customer notification",
        "competitor superiority",
    ],
}


BLOCKED_AUTONOMOUS_ACTIONS = [
    "release action blocked",
    "quarantine or hold action blocked",
    "discard action blocked",
    "reroute action blocked",
    "customer notification action blocked",
    "compliance certification action blocked",
]


def _scenario(
    *,
    scenario_id: str,
    scenario_name: str,
    summary: str,
    input_signals: dict[str, Any],
    data_quality_findings: list[str],
    zone_consensus_findings: list[str],
    sers_advisory_findings: dict[str, Any],
    human_review_checklist: list[str],
    expected_system_behavior: list[str],
) -> dict[str, Any]:
    return {
        "scenarioId": scenario_id,
        "scenarioName": scenario_name,
        "summary": summary,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "version": VERSION,
        "claimsBoundary": CLAIMS_BOUNDARY,
        "inputSignals": input_signals,
        "dataQualityFindings": data_quality_findings,
        "zoneConsensusFindings": zone_consensus_findings,
        "sersAdvisoryFindings": sers_advisory_findings,
        "humanReviewChecklist": human_review_checklist,
        "blockedAutonomousActions": BLOCKED_AUTONOMOUS_ACTIONS,
        "expectedSystemBehavior": expected_system_behavior,
    }


SCENARIOS: tuple[dict[str, Any], ...] = (
    _scenario(
        scenario_id="single-sensor-spike",
        scenario_name="Single Sensor Spike",
        summary="One synthetic sensor reports a sharp temperature jump while neighboring sensors remain stable.",
        input_signals={
            "currentTemperatureC": 10.8,
            "neighborMedianTemperatureC": 4.6,
            "singleSensorSpikeScore": 0.94,
            "neighborAgreementScore": 0.24,
            "zoneConsensusScore": 0.31,
            "doorOpenRatio": 0.0,
            "dropoutRatio": 0.03,
            "weakSignalRatio": 0.08,
            "mappingResolved": True,
        },
        data_quality_findings=[
            "Spike is isolated to one synthetic sensor.",
            "Neighbor sensors do not confirm the excursion.",
            "Signal quality is acceptable, so the conflict is preserved for review instead of discarded silently.",
        ],
        zone_consensus_findings=[
            "Low neighbor agreement reduces confidence in the isolated spike.",
            "Zone consensus does not support a confirmed zone-level excursion.",
            "Conflict is retained for human review.",
        ],
        sers_advisory_findings={
            "riskBand": "WATCH",
            "riskScore": 36,
            "confidenceLabel": "LOW",
            "primaryReason": "single-sensor conflict without multi-sensor confirmation",
            "advisoryOnly": True,
        },
        human_review_checklist=[
            "Inspect sensor placement and calibration profile.",
            "Compare neighboring pallet or zone readings.",
            "Check whether the spike repeats in later windows.",
            "Do not infer product status from this isolated signal.",
        ],
        expected_system_behavior=[
            "Do not overreact to one synthetic bad sensor.",
            "Preserve conflict evidence.",
            "Keep deterministic review rules authoritative.",
        ],
    ),
    _scenario(
        scenario_id="multi-sensor-confirmed-warming",
        scenario_name="Multi-Sensor Confirmed Warming",
        summary="Multiple synthetic sensors rise together, creating stronger advisory evidence than a single spike.",
        input_signals={
            "currentTemperatureC": 9.2,
            "neighborMedianTemperatureC": 8.9,
            "singleSensorSpikeScore": 0.08,
            "neighborAgreementScore": 0.88,
            "zoneConsensusScore": 0.86,
            "doorOpenRatio": 0.16,
            "dropoutRatio": 0.04,
            "weakSignalRatio": 0.09,
            "mappingResolved": True,
        },
        data_quality_findings=[
            "Readings are internally consistent across synthetic sensors.",
            "No duplicate or obvious single-sensor artifact dominates the window.",
            "Signal quality is sufficient for advisory review.",
        ],
        zone_consensus_findings=[
            "Neighboring synthetic sensors agree with the warming pattern.",
            "Temporal persistence supports a non-isolated event.",
            "Consensus score increases advisory concern but does not make an operational decision.",
        ],
        sers_advisory_findings={
            "riskBand": "ELEVATED",
            "riskScore": 72,
            "confidenceLabel": "MEDIUM",
            "primaryReason": "multi-sensor warming with temporal persistence",
            "advisoryOnly": True,
        },
        human_review_checklist=[
            "Inspect route timing and handling notes.",
            "Review door-open and loading-window context.",
            "Compare normalized readings against raw synthetic readings.",
            "Escalate for human review if deterministic rules require it.",
        ],
        expected_system_behavior=[
            "Raise advisory concern because multiple synthetic sensors agree.",
            "Do not claim product release or rejection.",
            "Route the case to human review evidence.",
        ],
    ),
    _scenario(
        scenario_id="unresolved-mapping-risk",
        scenario_name="Unresolved Mapping Risk",
        summary="Synthetic readings exist, but the sensor-to-zone or pallet mapping is unresolved.",
        input_signals={
            "currentTemperatureC": 5.1,
            "neighborMedianTemperatureC": 5.0,
            "singleSensorSpikeScore": 0.02,
            "neighborAgreementScore": 0.79,
            "zoneConsensusScore": 0.52,
            "doorOpenRatio": 0.0,
            "dropoutRatio": 0.14,
            "weakSignalRatio": 0.22,
            "mappingResolved": False,
        },
        data_quality_findings=[
            "Mapping uncertainty is preserved as an evidence gap.",
            "The synthetic temperature pattern itself is not a confirmed excursion.",
            "Weak signal and dropout reduce confidence.",
        ],
        zone_consensus_findings=[
            "Zone consensus is limited because mapping is unresolved.",
            "The system separates data-location uncertainty from temperature breach evidence.",
            "Mapping conflict is not treated as proof of thermal failure.",
        ],
        sers_advisory_findings={
            "riskBand": "WATCH",
            "riskScore": 44,
            "confidenceLabel": "LOW",
            "primaryReason": "mapping evidence gap, not confirmed warming",
            "advisoryOnly": True,
        },
        human_review_checklist=[
            "Verify gateway, zone, pallet, and sensor mapping.",
            "Inspect ingestion delay and calibration profile.",
            "Confirm whether the reading belongs to the reviewed synthetic case.",
            "Avoid turning mapping uncertainty into an operational decision.",
        ],
        expected_system_behavior=[
            "Flag unresolved mapping as a review gap.",
            "Avoid risk inflation from mapping uncertainty alone.",
            "Keep the case advisory-only.",
        ],
    ),
    _scenario(
        scenario_id="door-open-warming",
        scenario_name="Door-Open Warming",
        summary="Synthetic temperature rises while a door-open pattern is present.",
        input_signals={
            "currentTemperatureC": 8.7,
            "neighborMedianTemperatureC": 8.3,
            "singleSensorSpikeScore": 0.12,
            "neighborAgreementScore": 0.81,
            "zoneConsensusScore": 0.78,
            "doorOpenRatio": 0.62,
            "dropoutRatio": 0.05,
            "weakSignalRatio": 0.12,
            "mappingResolved": True,
        },
        data_quality_findings=[
            "Door-open context is visible in the synthetic window.",
            "Temperature rise is not isolated to one sensor.",
            "Signal quality remains adequate for advisory review.",
        ],
        zone_consensus_findings=[
            "Multiple sensors support a warming pattern.",
            "Door-open context helps explain why risk is rising.",
            "Consensus supports advisory escalation without autonomous action.",
        ],
        sers_advisory_findings={
            "riskBand": "ELEVATED",
            "riskScore": 69,
            "confidenceLabel": "MEDIUM",
            "primaryReason": "door-open warming with multi-sensor support",
            "advisoryOnly": True,
        },
        human_review_checklist=[
            "Review synthetic door-open interval.",
            "Compare loading or handoff timing.",
            "Inspect whether temperature normalized after door closure.",
            "Preserve evidence for deterministic human review.",
        ],
        expected_system_behavior=[
            "Explain risk rise through door-open context.",
            "Avoid autonomous customer or operational action.",
            "Keep deterministic review rules authoritative.",
        ],
    ),
    _scenario(
        scenario_id="dropout-weak-signal",
        scenario_name="Dropout and Weak Signal",
        summary="Synthetic sensor coverage degrades, reducing confidence in the advisory assessment.",
        input_signals={
            "currentTemperatureC": 6.4,
            "neighborMedianTemperatureC": 6.1,
            "singleSensorSpikeScore": 0.18,
            "neighborAgreementScore": 0.57,
            "zoneConsensusScore": 0.49,
            "doorOpenRatio": 0.08,
            "dropoutRatio": 0.46,
            "weakSignalRatio": 0.74,
            "mappingResolved": True,
        },
        data_quality_findings=[
            "High dropout limits continuity of evidence.",
            "Weak signal reduces confidence in sensor coverage.",
            "The system exposes low-confidence evidence instead of hiding it.",
        ],
        zone_consensus_findings=[
            "Zone consensus is limited by sparse coverage.",
            "No strong multi-sensor confirmation is available.",
            "Review should focus on evidence completeness.",
        ],
        sers_advisory_findings={
            "riskBand": "WATCH",
            "riskScore": 41,
            "confidenceLabel": "LOW",
            "primaryReason": "coverage and signal quality limitations",
            "advisoryOnly": True,
        },
        human_review_checklist=[
            "Inspect gateway connectivity.",
            "Check whether dropout aligns with transit or handoff windows.",
            "Compare with any available neighboring synthetic signals.",
            "Do not treat missing evidence as proof of safety or failure.",
        ],
        expected_system_behavior=[
            "Lower confidence when evidence is sparse.",
            "Preserve dropout as a review finding.",
            "Do not make autonomous operational decisions.",
        ],
    ),
    _scenario(
        scenario_id="no-excursion-control",
        scenario_name="No-Excursion Control",
        summary="Synthetic control case with stable temperatures, resolved mapping, and no breach evidence.",
        input_signals={
            "currentTemperatureC": 4.8,
            "neighborMedianTemperatureC": 4.7,
            "singleSensorSpikeScore": 0.01,
            "neighborAgreementScore": 0.91,
            "zoneConsensusScore": 0.9,
            "doorOpenRatio": 0.0,
            "dropoutRatio": 0.02,
            "weakSignalRatio": 0.06,
            "mappingResolved": True,
            "unresolvedMappingRiskContribution": 0,
        },
        data_quality_findings=[
            "Synthetic readings are stable.",
            "Mapping is resolved.",
            "No unresolved mapping risk contribution is added.",
        ],
        zone_consensus_findings=[
            "Neighbor agreement is strong.",
            "Zone consensus supports a stable control window.",
            "No single-sensor or multi-sensor excursion is indicated.",
        ],
        sers_advisory_findings={
            "riskBand": "WATCH",
            "riskScore": 34,
            "confidenceLabel": "MEDIUM",
            "primaryReason": "stable synthetic control window",
            "unresolvedMappingRiskContribution": 0,
            "advisoryOnly": True,
        },
        human_review_checklist=[
            "Confirm stable normalized readings.",
            "Confirm mapping remains resolved.",
            "Use as regression guard for Phase 5 calibration.",
            "Do not infer real-world distribution status.",
        ],
        expected_system_behavior=[
            "Remain WATCH.",
            "Keep risk score at 34 or lower.",
            "Keep unresolvedMappingRisk contribution at 0 when mapping is resolved.",
            "Do not regress Phase 5 no-excursion-control calibration.",
        ],
    ),
)


@lru_cache(maxsize=1)
def get_scenario_lab_payload() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "version": VERSION,
        "claimsBoundary": CLAIMS_BOUNDARY,
        "scenarioCount": len(SCENARIOS),
        "scenarioRoutes": [
            f"/scenario-lab/{scenario['scenarioId']}.json" for scenario in SCENARIOS
        ],
        "scenarios": [
            {
                "scenarioId": scenario["scenarioId"],
                "scenarioName": scenario["scenarioName"],
                "summary": scenario["summary"],
                "riskBand": scenario["sersAdvisoryFindings"]["riskBand"],
                "riskScore": scenario["sersAdvisoryFindings"]["riskScore"],
                "confidenceLabel": scenario["sersAdvisoryFindings"]["confidenceLabel"],
                "route": f"/scenario-lab/{scenario['scenarioId']}.json",
            }
            for scenario in SCENARIOS
        ],
        "expectedSystemBehaviors": [
            "single bad synthetic sensor does not trigger overreaction",
            "multi-sensor confirmed warming raises advisory concern",
            "unresolved mapping is treated as an evidence gap",
            "door-open warming is explained without autonomous action",
            "dropout and weak signal reduce confidence",
            "no-excursion-control remains WATCH with riskScore 34 or lower",
        ],
    }


def get_scenario_payload(scenario_id: str) -> dict[str, Any]:
    for scenario in SCENARIOS:
        if scenario["scenarioId"] == scenario_id:
            return scenario
    raise KeyError(f"Unknown scenario: {scenario_id}")


def _json_pre(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def _page(title: str, summary: str, payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #071014; color: #eef7f2; }}
    main {{ max-width: 1160px; margin: 0 auto; padding: 32px 20px 56px; }}
    a {{ color: #96e6b3; }}
    .card {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
    .scenario {{ background: #0b171d; border: 1px solid #1c3944; border-radius: 14px; padding: 14px; }}
    .scenario strong {{ display: block; font-size: 1.1rem; margin-bottom: 6px; }}
    .pill {{ display: inline-block; border: 1px solid #315c6d; border-radius: 999px; padding: 5px 9px; margin: 4px 5px 4px 0; color: #c8f7dc; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #071014; border: 1px solid #21414d; border-radius: 14px; padding: 16px; overflow-x: auto; }}
  </style>
</head>
<body>
<main>
  <p><a href="/">ColdChain Sentinel</a> · <a href="/training-lab">Training Lab</a> · <a href="/scenario-lab.json">JSON</a></p>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(summary)}</p>
  <section class="card">
    <h2>Safety boundary</h2>
    <span class="pill">Synthetic-only</span>
    <span class="pill">Advisory-only</span>
    <span class="pill">Human review</span>
    <span class="pill">Deterministic rules authoritative</span>
  </section>
  <section class="card">
    <h2>Machine-readable evidence</h2>
    <pre>{_json_pre(payload)}</pre>
  </section>
</main>
</body>
</html>"""


def render_scenario_lab_html() -> str:
    payload = get_scenario_lab_payload()
    cards = "\n".join(
        f"""<div class="scenario">
  <strong>{html.escape(item["scenarioName"])}</strong>
  <p>{html.escape(item["summary"])}</p>
  <p><span class="pill">{html.escape(item["riskBand"])}</span><span class="pill">Risk {item["riskScore"]}</span><span class="pill">{html.escape(item["confidenceLabel"])}</span></p>
  <p><a href="{html.escape(item["route"])}">{html.escape(item["route"])}</a></p>
</div>"""
        for item in payload["scenarios"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Synthetic Scenario Simulator</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #071014; color: #eef7f2; }}
    main {{ max-width: 1160px; margin: 0 auto; padding: 32px 20px 56px; }}
    a {{ color: #96e6b3; }}
    .card {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .scenario {{ background: #0b171d; border: 1px solid #1c3944; border-radius: 14px; padding: 14px; }}
    .scenario strong {{ display: block; font-size: 1.1rem; margin-bottom: 6px; }}
    .pill {{ display: inline-block; border: 1px solid #315c6d; border-radius: 999px; padding: 5px 9px; margin: 4px 5px 4px 0; color: #c8f7dc; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #071014; border: 1px solid #21414d; border-radius: 14px; padding: 16px; overflow-x: auto; }}
  </style>
</head>
<body>
<main>
  <p><a href="/">ColdChain Sentinel</a> · <a href="/training-lab">Training Lab</a> · <a href="/scenario-lab.json">JSON</a></p>
  <h1>Synthetic Scenario Simulator / What-If Lab</h1>
  <p>Compare deterministic synthetic cold-chain edge cases without making operational decisions.</p>
  <section class="card">
    <h2>Boundary</h2>
    <span class="pill">Synthetic-only</span>
    <span class="pill">Advisory-only</span>
    <span class="pill">No autonomous action</span>
    <span class="pill">Human review required</span>
  </section>
  <section class="card">
    <h2>Scenarios</h2>
    <div class="grid">
      {cards}
    </div>
  </section>
  <section class="card">
    <h2>Payload</h2>
    <pre>{_json_pre(payload)}</pre>
  </section>
</main>
</body>
</html>"""


def render_scenario_html(scenario_id: str) -> str:
    payload = get_scenario_payload(scenario_id)
    return _page(payload["scenarioName"], payload["summary"], payload)