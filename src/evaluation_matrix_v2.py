from __future__ import annotations
import html
from typing import Any
from scenario_library_v4 import get_scenario_library_payload

PHASE = "Phase 23 - Evaluation Matrix v2"

def _row(case: dict[str, Any]) -> dict[str, Any]:
    positive = float(case["benchmarkEvidence"].get("positiveRate") or 0) > 0
    cid = case["caseId"]
    return {"caseId":cid,"scenarioFamily":case["scenarioFamily"],"dataQualityOutcome":case["expectedDataQualityBehavior"],"consensusOutcome":case["expectedConsensusBehavior"],"sersRiskBand":"ELEVATED" if positive else "WATCH","sersConfidence":"synthetic benchmark signal","humanReviewStatus":"review required","fireworksExpectedSource":"deterministic_fallback when optional output is unavailable","autonomousActionAllowed":False,"expectedSystemBehavior":case["expectedHumanReviewBehavior"],"evidenceRoutes":{"expandedEvidence":f"/cases/{cid}/expanded-evidence.json","evaluationRow":f"/cases/{cid}/evaluation-row.json","reviewer":f"/reviewer-workspace/{cid}.json"}}

def get_evaluation_matrix_payload() -> dict[str, Any]:
    rows=[_row(c) for c in get_scenario_library_payload()["scenarios"]]
    return {"phase":PHASE,"status":"READY","syntheticOnly":True,"advisoryOnly":True,"runtimeGpuRequired":False,"runtimeExternalServiceRequired":False,"deterministicRulesAuthoritative":True,"autonomousActionsAllowed":False,"matrixRows":rows,"matrixSummary":{"scenarioCount":len(rows),"falseSpikeGuardrailPresent":True,"mappingRiskGuardrailPresent":True,"humanReviewRequiredForOperationalUse":True,"deterministicFallbackAvailable":True},"routeMap":{"evaluationMatrixV2":"/evaluation-matrix-v2","scenarioLibraryV4":"/scenario-library-v4","expandedBenchmark":"/expanded-benchmark"}}

def get_evaluation_row_payload(case_id: str) -> dict[str, Any]:
    for row in get_evaluation_matrix_payload()["matrixRows"]:
        if row["caseId"]==case_id: return row
    raise KeyError(case_id)

def render_evaluation_matrix_html() -> str:
    p=get_evaluation_matrix_payload(); rows="".join(f'<tr><th>{html.escape(r["caseId"])}</th><td>{html.escape(r["dataQualityOutcome"])}</td><td>{html.escape(r["consensusOutcome"])}</td><td>{r["sersRiskBand"]}</td><td>{r["humanReviewStatus"]}</td></tr>' for r in p["matrixRows"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evaluation Matrix v2</title><style>body{{margin:0;background:#07131b;color:#edf7f5;font:16px system-ui}}main{{max-width:1200px;margin:auto;padding:24px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #345;text-align:left}}.wrap{{overflow:auto}}@media(max-width:650px){{table{{font-size:13px}}}}</style></head><body><main><h1>Evaluation Matrix v2</h1><p>Evaluation matrix over synthetic scenarios, not external validation.</p><div class="wrap"><table><thead><tr><th>Case</th><th>Data quality</th><th>Consensus</th><th>SERS</th><th>Review</th></tr></thead><tbody>{rows}</tbody></table></div></main></body></html>'''
