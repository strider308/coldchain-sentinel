from __future__ import annotations

import html
import json
from functools import lru_cache
from typing import Any

from scenario_lab_v2 import SCENARIOS, get_scenario_payload

VERSION = "human-review-workbench-v2.0.0"

BLOCKED_ACTIONS = [
    "release action blocked",
    "quarantine or hold action blocked",
    "discard action blocked",
    "reroute action blocked",
    "outbound customer notice blocked",
    "compliance signoff blocked",
]

CLAIMS_BOUNDARY = {
    "dataScope": "synthetic scenario evidence only",
    "decisionScope": "human review support only",
    "decisionAuthority": "deterministic rules remain authoritative",
    "sersScope": "SERS remains advisory-only",
    "externalDataScope": "no actual customer, pharma, logistics, patient, shipment, or sensor datasets are used",
    "operationalBoundary": "no operational action is executed by this workbench",
}


def _route(scenario_id: str) -> str:
    return f"/review-workbench/{scenario_id}.json"


def _evidence_links(scenario_id: str) -> dict[str, str]:
    return {
        "scenario": f"/scenario-lab/{scenario_id}.json",
        "scenarioCatalog": "/scenario-lab.json",
        "trainingLab": "/training-lab.json",
        "modelBenchmarkV2": "/model-benchmark-v2.json",
        "modelCard": "/model-card.json",
        "sers": "/sers.json",
        "consensus": "/consensus.json",
        "dataQuality": "/data-quality.json",
    }


def get_review_packet_payload(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario_payload(scenario_id)
    advisory = scenario["sersAdvisoryFindings"]

    return {
        "reviewPacketId": f"review-{scenario_id}",
        "scenarioId": scenario_id,
        "scenarioName": scenario["scenarioName"],
        "version": VERSION,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "claimsBoundary": CLAIMS_BOUNDARY,
        "decisionAuthority": "deterministic rules remain authoritative",
        "sersScope": "advisory-only",
        "riskBand": advisory["riskBand"],
        "riskScore": advisory["riskScore"],
        "confidenceLabel": advisory["confidenceLabel"],
        "evidenceLinks": _evidence_links(scenario_id),
        "evidenceTabs": [
            {
                "tabId": "scenario-summary",
                "title": "Scenario summary",
                "findings": [scenario["summary"]],
                "evidenceRoute": f"/scenario-lab/{scenario_id}.json",
            },
            {
                "tabId": "sensor-evidence",
                "title": "Synthetic sensor evidence references",
                "findings": [
                    "Review raw and normalized synthetic readings where available.",
                    "Compare input signals against scenario findings.",
                ],
                "evidenceRoute": f"/scenario-lab/{scenario_id}.json",
            },
            {
                "tabId": "data-quality",
                "title": "Data quality findings",
                "findings": scenario["dataQualityFindings"],
                "evidenceRoute": "/data-quality.json",
            },
            {
                "tabId": "zone-consensus",
                "title": "Zone consensus findings",
                "findings": scenario["zoneConsensusFindings"],
                "evidenceRoute": "/consensus.json",
            },
            {
                "tabId": "sers-advisory",
                "title": "SERS advisory findings",
                "findings": [
                    f"Risk band: {advisory['riskBand']}",
                    f"Risk score: {advisory['riskScore']}",
                    f"Confidence: {advisory['confidenceLabel']}",
                    f"Primary reason: {advisory['primaryReason']}",
                ],
                "evidenceRoute": "/sers.json",
            },
            {
                "tabId": "training-benchmark",
                "title": "Synthetic training and benchmark evidence",
                "findings": [
                    "Synthetic benchmark data is deterministic.",
                    "Model evidence is advisory and not real-world validation.",
                ],
                "evidenceRoute": "/training-lab.json",
            },
            {
                "tabId": "human-checklist",
                "title": "Human checklist",
                "findings": scenario["humanReviewChecklist"],
                "evidenceRoute": _route(scenario_id),
            },
            {
                "tabId": "blocked-actions",
                "title": "Blocked autonomous actions",
                "findings": BLOCKED_ACTIONS,
                "evidenceRoute": _route(scenario_id),
            },
        ],
        "checklistStatus": [
            {
                "checkId": f"{scenario_id}-check-{index + 1}",
                "label": item,
                "required": True,
                "status": "incomplete",
                "autoDecision": False,
            }
            for index, item in enumerate(scenario["humanReviewChecklist"])
        ],
        "conflictSummary": {
            "summary": scenario["summary"],
            "dataQualityFindings": scenario["dataQualityFindings"],
            "zoneConsensusFindings": scenario["zoneConsensusFindings"],
        },
        "confidenceLimits": [
            "Synthetic scenario evidence is not field validation.",
            "Advisory scoring supports review prioritization only.",
            "Final interpretation requires human review and deterministic rules.",
        ],
        "blockedAutonomousActions": BLOCKED_ACTIONS,
        "finalHumanReviewPrompt": (
            "Inspect the synthetic evidence packet, resolve checklist items, and document the human review outcome outside this advisory demo."
        ),
        "expectedSystemBehavior": scenario["expectedSystemBehavior"],
    }


@lru_cache(maxsize=1)
def get_review_workbench_payload() -> dict[str, Any]:
    packets = [
        {
            "scenarioId": scenario["scenarioId"],
            "scenarioName": scenario["scenarioName"],
            "riskBand": scenario["sersAdvisoryFindings"]["riskBand"],
            "riskScore": scenario["sersAdvisoryFindings"]["riskScore"],
            "confidenceLabel": scenario["sersAdvisoryFindings"]["confidenceLabel"],
            "route": _route(scenario["scenarioId"]),
        }
        for scenario in SCENARIOS
    ]

    return {
        "phase": "Phase 8 - Human Review Workbench v2",
        "version": VERSION,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "claimsBoundary": CLAIMS_BOUNDARY,
        "packetCount": len(packets),
        "packetRoutes": [item["route"] for item in packets],
        "packets": packets,
        "blockedAutonomousActions": BLOCKED_ACTIONS,
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
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }}
.item {{ background:#0b171d; border:1px solid #1c3944; border-radius:14px; padding:14px; }}
.pill {{ display:inline-block; border:1px solid #315c6d; border-radius:999px; padding:5px 9px; margin:4px 5px 4px 0; color:#c8f7dc; }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#071014; border:1px solid #21414d; border-radius:14px; padding:16px; }}
</style>
</head>
<body>
<main>
<p><a href="/">ColdChain Sentinel</a> · <a href="/scenario-lab">Scenario Lab</a> · <a href="/review-workbench.json">JSON</a></p>
<h1>{html.escape(title)}</h1>
<p>{html.escape(summary)}</p>
<section class="card">
<span class="pill">Synthetic-only</span>
<span class="pill">Advisory-only</span>
<span class="pill">Human review</span>
<span class="pill">Deterministic rules authoritative</span>
</section>
<section class="card">
<h2>Machine-readable payload</h2>
<pre>{_json(payload)}</pre>
</section>
</main>
</body>
</html>"""


def render_review_workbench_html() -> str:
    payload = get_review_workbench_payload()
    cards = "\n".join(
        f"""<div class="item">
<strong>{html.escape(item["scenarioName"])}</strong>
<p><span class="pill">{html.escape(item["riskBand"])}</span><span class="pill">Risk {item["riskScore"]}</span><span class="pill">{html.escape(item["confidenceLabel"])}</span></p>
<p><a href="{html.escape(item["route"])}">{html.escape(item["route"])}</a></p>
</div>"""
        for item in payload["packets"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Human Review Workbench v2</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ margin:0; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#071014; color:#eef7f2; }}
main {{ max-width:1160px; margin:0 auto; padding:32px 20px 56px; }}
a {{ color:#96e6b3; }}
.card {{ background:#102129; border:1px solid #21414d; border-radius:18px; padding:20px; margin:18px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }}
.item {{ background:#0b171d; border:1px solid #1c3944; border-radius:14px; padding:14px; }}
.pill {{ display:inline-block; border:1px solid #315c6d; border-radius:999px; padding:5px 9px; margin:4px 5px 4px 0; color:#c8f7dc; }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#071014; border:1px solid #21414d; border-radius:14px; padding:16px; }}
</style>
</head>
<body>
<main>
<p><a href="/">ColdChain Sentinel</a> · <a href="/review-workbench.json">JSON</a></p>
<h1>Human Review Workbench v2</h1>
<p>Structured synthetic review packets for scenario evidence, conflicts, confidence limits, and blocked autonomous actions.</p>
<section class="card">
<span class="pill">Synthetic-only</span>
<span class="pill">Advisory-only</span>
<span class="pill">No automatic final decision</span>
<span class="pill">Human checklist incomplete by default</span>
</section>
<section class="card">
<h2>Review packets</h2>
<div class="grid">{cards}</div>
</section>
<section class="card">
<h2>Payload</h2>
<pre>{_json(payload)}</pre>
</section>
</main>
</body>
</html>"""


def render_review_packet_html(scenario_id: str) -> str:
    payload = get_review_packet_payload(scenario_id)
    return _page(payload["scenarioName"], "Synthetic human review packet.", payload)