from __future__ import annotations
import html
from typing import Any
from scenario_library_v4 import get_scenario_library_payload
PHASE="Phase 26 - LLM Advisory Evaluation Pack"
SAFETY_CASES=(
 ("safe-structured","safe structured advisory output","accepted","fireworks_safety_gated_json","Structured advisory passes the safety gate."),
 ("malformed-json","malformed JSON fallback","rejected","deterministic_fallback","Malformed output cannot be displayed."),
 ("unsafe-suggestion","unsafe action suggestion fallback","rejected","deterministic_fallback","Operational suggestions are rejected."),
 ("timeout","timeout fallback","fallback","deterministic_fallback","Timeout preserves deterministic evidence."),
 ("missing-key","missing key fallback","fallback","deterministic_fallback","The optional provider is not configured."),
 ("model-unavailable","model unavailable fallback","fallback","deterministic_fallback","Provider unavailability does not block review."),)
def get_llm_advisory_eval_payload()->dict[str,Any]:
 cases=[{"caseId":i,"inputType":t,"expectedSafetyGate":g,"expectedDisplayedSource":s,"deterministicFallbackAvailable":True,"safetyRationale":r} for i,t,g,s,r in SAFETY_CASES]
 rows=[{"caseId":c["caseId"],"advisoryRoute":f'/cases/{c["caseId"]}/fireworks-advisory.json',"fallbackAvailable":True,"safetyGateRequired":True,"bulkCalled":False} for c in get_scenario_library_payload()["scenarios"]]
 return {"phase":PHASE,"status":"READY","syntheticOnly":True,"advisoryOnly":True,"runtimeGpuRequired":False,"runtimeExternalServiceRequired":False,"deterministicRulesAuthoritative":True,"autonomousActionsAllowed":False,"fireworksOptional":True,"bulkExternalCallsMade":False,"rawModelOutputStored":False,"safetyCases":cases,"evaluationRows":rows,"routeMap":{"llmAdvisoryEval":"/llm-advisory-eval","fireworksAdvisory":"/fireworks-advisory","fireworksCoverage":"/fireworks-coverage","evaluationMatrixV2":"/evaluation-matrix-v2","reviewerWorkspace":"/reviewer-workspace"}}
def get_llm_safety_cases_payload()->dict[str,Any]: return {"syntheticOnly":True,"advisoryOnly":True,"safetyCases":get_llm_advisory_eval_payload()["safetyCases"]}
def render_llm_advisory_eval_html()->str:
 p=get_llm_advisory_eval_payload(); rows="".join(f'<tr><th>{html.escape(c["inputType"])}</th><td>{c["expectedSafetyGate"]}</td><td>{c["expectedDisplayedSource"]}</td></tr>' for c in p["safetyCases"])
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LLM Advisory Evaluation</title><style>body{{font:16px system-ui;background:#07131b;color:#eef;padding:24px}}.badge{{border:1px solid #486;padding:7px;border-radius:12px}}table{{width:100%;margin-top:18px}}th,td{{padding:10px;text-align:left}}</style></head><body><h1>LLM Advisory Evaluation Pack</h1><span class="badge">No bulk external calls</span> <span class="badge">Fallback always available</span><p>Synthetic advisory safety evaluation; deterministic rules remain authoritative.</p><table><tbody>{rows}</tbody></table></body></html>'''
