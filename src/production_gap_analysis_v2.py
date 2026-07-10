"""Static synthetic production gap analysis for reviewer transparency."""

from __future__ import annotations

import html
import json
from typing import Any


PHASE = "Phase 20 - Production Gap Analysis"
STATUS = "GAPS_IDENTIFIED"
GAPS = (
    ("data validation", "Synthetic scenarios only", "Representative real-use data and acceptance criteria", "Define a governed validation plan", "data lead", "high"),
    ("security review", "Demo controls only", "Threat model, testing, and remediation evidence", "Commission an independent security review", "security lead", "high"),
    ("privacy review", "Synthetic data only", "Privacy impact assessment and handling controls", "Complete a privacy review", "privacy lead", "high"),
    ("domain expert review", "Rules demonstrated on synthetic cases", "Independent domain assessment of rules and evidence", "Engage qualified domain experts", "domain lead", "high"),
    ("customer pilot", "No real customer pilot", "Scoped pilot with agreed safeguards and success measures", "Design a human-supervised pilot", "product lead", "high"),
    ("operational monitoring", "Evidence-health pages only", "Service, data-quality, and alert monitoring", "Define service objectives and monitoring", "operations lead", "high"),
    ("audit logging hardening", "Static demo audit evidence", "Tamper resistance, access controls, and retention tests", "Specify and test hardened audit storage", "platform lead", "medium"),
    ("incident response process", "No operational response process", "Documented roles, escalation, exercises, and review", "Create and exercise an incident plan", "operations lead", "high"),
    ("data retention policy", "No real data retained", "Approved retention, deletion, and legal-hold rules", "Draft and approve a retention policy", "privacy lead", "medium"),
    ("vendor/legal agreements", "No production vendor commitments", "Approved terms, responsibilities, and risk review", "Complete vendor and legal review", "legal lead", "medium"),
    ("human reviewer training", "Demo reviewer workflow only", "Role-based training, assessment, and refresh process", "Develop and test reviewer training", "training lead", "high"),
)
GAP_CATEGORIES = tuple(gap[0] for gap in GAPS)


def get_production_gap_analysis_payload() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "productionValidated": False,
        "pharmaValidated": False,
        "realWorldValidated": False,
        "complianceCertified": False,
        "autonomousActionsAllowed": False,
        "deterministicRulesAuthoritative": True,
        "gapCategories": [
            dict(zip(("category", "currentDemoStatus", "missingBeforeRealUse", "suggestedNextStep", "owner", "priority"), gap))
            for gap in GAPS
        ],
        "readinessBoundary": {
            "demoReady": True,
            "realDeploymentReady": False,
            "requiresHumanReview": True,
            "requiresExternalExpertReview": True,
        },
        "routeMap": {
            "finalValidation": "/final-validation",
            "demoConsole": "/demo-console",
            "opsReadiness": "/ops-readiness",
        },
    }


def render_production_gap_analysis_html() -> str:
    payload = get_production_gap_analysis_payload()
    rows = "".join(
        "<tr>"
        f'<th scope="row">{html.escape(item["category"])}</th>'
        f'<td>{html.escape(item["currentDemoStatus"])}</td>'
        f'<td>{html.escape(item["missingBeforeRealUse"])}</td>'
        f'<td>{html.escape(item["suggestedNextStep"])}</td>'
        f'<td>{html.escape(item["owner"])}</td>'
        f'<td><span class="priority {html.escape(item["priority"])}">{html.escape(item["priority"])}</span></td>'
        "</tr>"
        for item in payload["gapCategories"]
    )
    evidence = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Production Gap Analysis</title><style>
body{{margin:0;background:#071014;color:#eef7f2;font:16px system-ui,sans-serif}}main{{max-width:1240px;margin:auto;padding:32px 20px 56px}}a{{color:#96e6b3}}
.card{{background:#102129;border:1px solid #21414d;border-radius:16px;padding:20px;margin:18px 0}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse}}
th,td{{border-bottom:1px solid #21414d;padding:12px 8px;text-align:left;vertical-align:top}}.priority{{display:inline-block;border-radius:999px;padding:4px 9px;text-transform:uppercase;font-weight:700}}
.priority.high{{background:#633134;color:#ffe3e3}}.priority.medium{{background:#594819;color:#fff0b3}}pre{{white-space:pre-wrap;word-break:break-word;overflow:auto;background:#071014;padding:16px;border-radius:12px}}
</style></head><body><main>
<p><a href="/">ColdChain Sentinel</a> · <a href="/production-gap-analysis.json">JSON</a> · <a href="/final-validation">Final validation</a> · <a href="/demo-console">Demo console</a> · <a href="/ops-readiness">Ops readiness</a></p>
<h1>Production Gap Analysis</h1><p><strong>Demo evidence exists; real deployment requires additional validation and review.</strong></p>
<section class="card"><p>Synthetic-only · Advisory-only · Deterministic rules authoritative · Human and external expert review required</p></section>
<section class="card"><h2>Gap matrix</h2><div class="table-wrap"><table><thead><tr><th>Category</th><th>Current demo status</th><th>Missing before real use</th><th>Suggested next step</th><th>Owner</th><th>Priority</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="card"><h2>Machine-readable boundary</h2><pre>{evidence}</pre></section>
</main></body></html>"""
