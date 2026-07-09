from __future__ import annotations

import html
import json
from functools import lru_cache
from typing import Any

from scenario_lab_v2 import SCENARIOS, get_scenario_payload

VERSION = "incident-replay-v2.0.0"


def _route(scenario_id: str) -> str:
    return f"/incident-replay/{scenario_id}.json"


def _event(minute: int, event_type: str, title: str, evidence: list[str], interpretation: str) -> dict[str, Any]:
    return {
        "minuteOffset": minute,
        "eventType": event_type,
        "title": title,
        "evidence": evidence,
        "advisoryInterpretation": interpretation,
        "blockedAutonomousAction": "No operational action emitted.",
    }


def get_incident_replay_payload(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario_payload(scenario_id)
    advisory = scenario["sersAdvisoryFindings"]

    events = [
        _event(
            0,
            "synthetic_sensor_ingestion",
            "Synthetic readings ingested",
            [f"Scenario: {scenario['scenarioName']}", "Input signals are synthetic."],
            "The replay begins from deterministic synthetic evidence only.",
        ),
        _event(
            5,
            "normalization",
            "Synthetic readings normalized",
            ["Sensor, zone, and timing fields are prepared for review.", "No external partner system is called."],
            "Normalization supports review consistency without creating a final decision.",
        ),
        _event(
            10,
            "data_quality_filtering",
            "Data quality findings generated",
            scenario["dataQualityFindings"],
            "Quality findings affect confidence and evidence completeness.",
        ),
        _event(
            15,
            "consensus_scoring",
            "Zone consensus evaluated",
            scenario["zoneConsensusFindings"],
            "Consensus explains whether the signal is isolated or supported by neighbors.",
        ),
        _event(
            20,
            "sers_advisory_scoring",
            "SERS advisory score produced",
            [
                f"Risk band: {advisory['riskBand']}",
                f"Risk score: {advisory['riskScore']}",
                f"Confidence: {advisory['confidenceLabel']}",
                f"Primary reason: {advisory['primaryReason']}",
            ],
            "SERS supports prioritization and explanation only.",
        ),
        _event(
            25,
            "human_review_packet_creation",
            "Human review packet prepared",
            [f"Review route: /review-workbench/{scenario_id}.json", "Checklist remains incomplete by default."],
            "The system hands off evidence for human review.",
        ),
        _event(
            30,
            "blocked_autonomous_action_audit",
            "Autonomous action audit recorded",
            [
                "Release action blocked.",
                "Hold/quarantine action blocked.",
                "Discard action blocked.",
                "Reroute action blocked.",
                "Outbound customer notice blocked.",
            ],
            "The replay documents that advisory evidence did not execute an operational action.",
        ),
    ]

    return {
        "replayId": f"replay-{scenario_id}",
        "scenarioId": scenario_id,
        "scenarioName": scenario["scenarioName"],
        "version": VERSION,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "timelineEvents": sorted(events, key=lambda item: item["minuteOffset"]),
        "replaySummary": scenario["summary"],
        "whatChanged": [
            "Synthetic evidence moved from input signals to quality review, consensus review, advisory scoring, and human packet creation.",
            f"Advisory risk band is {advisory['riskBand']} with score {advisory['riskScore']}.",
        ],
        "whatDidNotChange": [
            "No real incident is claimed.",
            "No operational action is executed.",
            "Deterministic rules remain authoritative.",
            "SERS remains advisory-only.",
        ],
        "humanReviewHandoff": f"/review-workbench/{scenario_id}.json",
        "deterministicRuleBoundary": "deterministic rules remain authoritative",
        "sersAdvisoryBoundary": "SERS remains advisory-only",
    }


@lru_cache(maxsize=1)
def get_incident_replay_catalog_payload() -> dict[str, Any]:
    return {
        "phase": "Phase 9 - Synthetic Incident Replay Timeline",
        "version": VERSION,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "replayCount": len(SCENARIOS),
        "replayRoutes": [_route(scenario["scenarioId"]) for scenario in SCENARIOS],
        "replays": [
            {
                "scenarioId": scenario["scenarioId"],
                "scenarioName": scenario["scenarioName"],
                "route": _route(scenario["scenarioId"]),
                "riskBand": scenario["sersAdvisoryFindings"]["riskBand"],
                "riskScore": scenario["sersAdvisoryFindings"]["riskScore"],
            }
            for scenario in SCENARIOS
        ],
        "boundary": [
            "synthetic replay only",
            "advisory-only",
            "no operational action emitted",
            "human review handoff",
        ],
    }


def _json(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def _page(title: str, summary: str, payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ margin:0; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#071014; color:#eef7f2; }}
main {{ max-width:1160px; margin:0 auto; padding:32px 20px 56px; }}
a {{ color:#96e6b3; }}
.card {{ background:#102129; border:1px solid #21414d; border-radius:18px; padding:20px; margin:18px 0; }}
.pill {{ display:inline-block; border:1px solid #315c6d; border-radius:999px; padding:5px 9px; margin:4px 5px 4px 0; color:#c8f7dc; }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#071014; border:1px solid #21414d; border-radius:14px; padding:16px; }}
</style>
</head>
<body>
<main>
<p><a href="/">ColdChain Sentinel</a> · <a href="/incident-replay.json">JSON</a></p>
<h1>{html.escape(title)}</h1>
<p>{html.escape(summary)}</p>
<section class="card">
<span class="pill">Synthetic replay</span>
<span class="pill">Advisory-only</span>
<span class="pill">No operational action emitted</span>
</section>
<section class="card">
<h2>Payload</h2>
<pre>{_json(payload)}</pre>
</section>
</main>
</body>
</html>"""


def render_incident_replay_catalog_html() -> str:
    return _page(
        "Synthetic Incident Replay Timeline",
        "Deterministic synthetic timeline from signal ingestion to human review handoff.",
        get_incident_replay_catalog_payload(),
    )


def render_incident_replay_html(scenario_id: str) -> str:
    payload = get_incident_replay_payload(scenario_id)
    return _page(payload["scenarioName"], "Synthetic incident replay timeline.", payload)