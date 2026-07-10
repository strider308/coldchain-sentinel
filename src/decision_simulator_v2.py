from __future__ import annotations
import html
from typing import Any
from scenario_library_v4 import get_scenario_library_payload
PHASE="Phase 28 - Human Review Decision Simulator"
ALLOWED=["inspect","annotate","request evidence","mark review status"]
BLOCKED=["release","quarantine","discard","reroute","customer messaging"]
OUTCOMES=["synthetic review incomplete","synthetic evidence requested","synthetic review status noted","synthetic escalation candidate"]
def _case(c:dict[str,Any])->dict[str,Any]:
 cid=c["caseId"]
 return {"caseId":cid,"scenarioFamily":c["scenarioFamily"],"currentSyntheticReviewState":"needs review","availableEvidenceTabs":["expanded evidence","evaluation row","audit ledger","optional advisory"],"allowedReviewerActions":ALLOWED,"blockedOperationalActions":BLOCKED,"suggestedReviewerQuestions":["Is evidence complete?","Do sensors agree?","Is mapping resolved?"],"possibleReviewOutcomes":OUTCOMES,"nextEvidenceRoutes":[f"/cases/{cid}/expanded-evidence.json",f"/cases/{cid}/evaluation-row.json",f"/cases/{cid}/audit-ledger.json"],"safetyBoundary":"Static synthetic workflow labels only; no operational action."}
def get_decision_simulator_payload()->dict[str,Any]:
 cases=[_case(c) for c in get_scenario_library_payload()["scenarios"]]
 return {"phase":PHASE,"status":"READY","syntheticOnly":True,"advisoryOnly":True,"runtimeGpuRequired":False,"runtimeExternalServiceRequired":False,"deterministicRulesAuthoritative":True,"autonomousActionsAllowed":False,"databaseRequired":False,"persistenceEnabled":False,"allowedReviewerActions":ALLOWED,"blockedOperationalActions":BLOCKED,"simulatorCases":cases,"routeMap":{"decisionSimulator":"/decision-simulator","scenarioLibraryV4":"/scenario-library-v4","evaluationMatrixV2":"/evaluation-matrix-v2","reviewerWorkspace":"/reviewer-workspace"}}
def get_decision_simulator_case_payload(case_id:str)->dict[str,Any]:
 for c in get_decision_simulator_payload()["simulatorCases"]:
  if c["caseId"]==case_id:return c
 raise KeyError(case_id)
def render_decision_simulator_html()->str:
 p=get_decision_simulator_payload(); cards="".join(f'<article><h2>{html.escape(c["caseId"])}</h2><p>{c["currentSyntheticReviewState"]}</p><a href="/decision-simulator/{c["caseId"]}.json">Case JSON</a></article>' for c in p["simulatorCases"])
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Decision Simulator</title><style>body{{font:16px system-ui;background:#07131b;color:#eef;padding:24px}}section{{display:flex;flex-wrap:wrap;gap:12px}}article{{flex:1 1 260px;background:#102631;padding:16px;border-radius:12px}}a{{color:#9ed}}</style></head><body><h1>Human Review Decision Simulator</h1><p>Static synthetic simulator; no persistence; no operational action.</p><section>{cards}</section></body></html>'''
