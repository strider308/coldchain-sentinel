from __future__ import annotations

import html
import json
from typing import Any


PHASE = "Phase 16 - Evidence Audit Ledger"
STATUS = "READY"
CASE_IDS = (
    "no-excursion-control",
    "single-sensor-spike",
    "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk",
    "door-open-warming",
    "dropout-weak-signal",
)


def _case_route(case_id: str) -> str:
    return f"/cases/{case_id}/audit-ledger.json"


def _ledger_steps(case_id: str) -> list[dict[str, str]]:
    scenario_route = f"/scenario-lab/{case_id}.json"
    specs = (
        ("reading-received", "Synthetic reading received", "scenario_lab_v2", scenario_route, "Synthetic input entered the review pipeline."),
        ("schema-normalized", "Schema normalized", "scenario_lab_v2", scenario_route, "Fields were normalized to the synthetic data contract."),
        ("data-quality-checked", "Data-quality checked", "scenario_lab_v2", scenario_route, "Quality findings were recorded for human inspection."),
        ("consensus-calculated", "Consensus calculated", "scenario_lab_v2", scenario_route, "Neighboring synthetic signals were compared."),
        ("sers-advisory-generated", "SERS advisory generated", "scenario_lab_v2", scenario_route, "An advisory risk signal was produced without changing deterministic facts."),
        ("human-review-created", "Human review packet created", "human_review_workbench_v2", f"/review-workbench/{case_id}.json", "Evidence was prepared for a human reviewer."),
        ("explanation-available", "Fireworks explanation available or fallback available", "fireworks_advisory_v2", f"/cases/{case_id}/fireworks-advisory.json", "Optional explanation support preserves a deterministic fallback."),
        ("autonomous-action-blocked", "Autonomous action blocked", "scenario_lab_v2", scenario_route, "No operational action or outbound message was executed."),
    )
    return [
        {
            "stepId": step_id,
            "sequenceLabel": f"SEQ-{index:02d}",
            "label": label,
            "sourceModule": source,
            "evidenceRoute": route,
            "status": "RECORDED",
            "humanMeaning": meaning,
            "safetyBoundary": "Synthetic advisory evidence only; deterministic rules remain authoritative.",
        }
        for index, (step_id, label, source, route, meaning) in enumerate(specs, 1)
    ]


def _boundaries() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeExternalServiceRequired": False,
        "runtimeGpuRequired": False,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
    }


def get_case_audit_ledger_payload(case_id: str) -> dict[str, Any]:
    if case_id not in CASE_IDS:
        raise KeyError(case_id)
    return {
        **_boundaries(),
        "caseId": case_id,
        "ledgerSteps": _ledger_steps(case_id),
        "sequenceType": "deterministic synthetic sequence labels",
        "boundary": "Audit-style synthetic evidence trail, not compliance certification.",
    }


def get_audit_ledger_payload() -> dict[str, Any]:
    return {
        **_boundaries(),
        "ledgerSteps": _ledger_steps("no-excursion-control"),
        "caseLedgers": [
            {"caseId": case_id, "route": _case_route(case_id)} for case_id in CASE_IDS
        ],
        "routeMap": {
            "auditLedger": "/audit-ledger",
            "auditLedgerJson": "/audit-ledger.json",
            **{case_id: _case_route(case_id) for case_id in CASE_IDS},
        },
        "boundary": "Audit-style synthetic evidence trail, not compliance certification.",
    }


def render_audit_ledger_html() -> str:
    payload = get_audit_ledger_payload()
    steps = "".join(
        f'<article class="step"><span>{html.escape(step["sequenceLabel"])}</span>'
        f'<h2>{html.escape(step["label"])}</h2><p>{html.escape(step["humanMeaning"])}</p>'
        f'<a href="{html.escape(step["evidenceRoute"])}">Evidence route</a></article>'
        for step in payload["ledgerSteps"]
    )
    routes = "".join(
        f'<a class="button" href="{html.escape(item["route"])}">{html.escape(item["caseId"])}</a>'
        for item in payload["caseLedgers"]
    )
    preview = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evidence Audit Ledger</title><style>
body{{margin:0;background:#07131b;color:#edf7f5;font:16px system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:28px 18px 48px}}
a{{color:#8ee8cb}}.badges,.routes{{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}}.badge,.button{{border:1px solid #347263;border-radius:999px;padding:7px 11px}}
.button{{text-decoration:none}}.timeline{{border-left:3px solid #347263;padding-left:18px}}.step{{background:#102631;border:1px solid #244852;border-radius:12px;padding:16px;margin:0 0 14px}}
.step span{{color:#8ee8cb;font-weight:700}}pre{{white-space:pre-wrap;word-break:break-word;background:#041016;padding:16px;border-radius:12px;overflow:auto}}
@media(max-width:600px){{main{{padding:20px 12px}}.button{{width:100%;text-align:center}}}}
</style></head><body><main><p><a href="/">ColdChain Sentinel</a> / <a href="/audit-ledger.json">JSON</a></p>
<h1>Evidence Audit Ledger</h1><p>Audit-style synthetic evidence trail, not compliance certification.</p>
<div class="badges"><span class="badge">Synthetic-only</span><span class="badge">Advisory-only</span><span class="badge">Deterministic rules authoritative</span><span class="badge">Autonomous actions blocked</span></div>
<div class="routes">{routes}</div><section class="timeline">{steps}</section><h2>Ledger JSON preview</h2><pre>{preview}</pre>
</main></body></html>"""
