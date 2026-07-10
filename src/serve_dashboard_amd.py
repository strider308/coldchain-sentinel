"""AMD evidence route wrapper for ColdChain Sentinel.

This module extends the existing stdlib dashboard without changing deterministic
review logic. It surfaces sanitized AMD GPU notebook evidence and, when present,
the synthetic SERS GPU benchmark artifact.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from http.server import ThreadingHTTPServer

from serve_dashboard import (
    HOST,
    PORT,
    DashboardHandler as BaseDashboardHandler,
    badge,
    command_center_payload,
    global_nav,
    page,
    render_command_center,
    system_status_json,
    validation_evidence_json,
)
from ui_design_system_v2 import render_metric_cards, render_page_shell, render_route_buttons

from sers_v2 import (
    render_sers_page,
    risk_timeline_json,
    sers_case_json,
    sers_json,
    sers_model_card_json,
)

from consensus_v2 import (
    consensus_json,
    consensus_report_json,
    render_consensus_page,
)

from data_quality_v2 import (
    data_quality_json,
    quality_events_json,
    quality_report_json,
    rejected_readings_json,
    render_data_quality_page,
)

from sensor_data_model_v2 import (
    data_contract_v2_json,
    normalized_sensor_window_json,
    parse_window_query,
    raw_schema_json,
    raw_sensor_window_json,
    render_data_contract_v2_page,
    render_raw_schema_page,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AMD_ENVIRONMENT_ARTIFACT = REPO_ROOT / "artifacts" / "amd_gpu_environment_evidence.json"
AMD_SERS_BENCHMARK_ARTIFACT = REPO_ROOT / "artifacts" / "amd_sers_gpu_benchmark.json"


def _safe_json_artifact(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _benchmark_available(benchmark: dict[str, Any] | None) -> bool:
    return bool(
        benchmark
        and benchmark.get("gpuVerified") is True
        and benchmark.get("benchmarkStatus") == "AMD_GPU_SYNTHETIC_SERS_BENCHMARK_COMPLETE"
    )


def amd_acceleration_json() -> dict[str, Any]:
    evidence = _safe_json_artifact(AMD_ENVIRONMENT_ARTIFACT)
    benchmark = _safe_json_artifact(AMD_SERS_BENCHMARK_ARTIFACT)

    gpu_verified = bool(evidence and evidence.get("gpuVerified") and evidence.get("torchCudaAvailable"))
    benchmark_available = _benchmark_available(benchmark)

    if benchmark_available:
        allowed_claim = (
            "AMD ROCm/PyTorch GPU execution was verified, and a synthetic "
            "SERS-style GPU training benchmark completed in the notebook environment."
        )
        claims_scope = "environment verification plus synthetic SERS benchmark evidence"
        not_claimed = [
            "real-world validation",
            "production ML acceleration",
            "pharma/compliance validation",
            "specific AMD GPU model",
            "AMD improved SERS accuracy",
            "autonomous operational action or customer messaging",
        ]
    else:
        allowed_claim = (
            "AMD ROCm/PyTorch GPU execution was verified in the notebook environment."
            if gpu_verified
            else "No AMD GPU verification claim is made yet."
        )
        claims_scope = "environment verification only" if gpu_verified else "none"
        not_claimed = [
            "specific AMD GPU model",
            "SERS GPU training completed",
            "CPU/GPU speedup proven",
            "production ML acceleration validated",
            "real-world cold-chain model trained",
            "AMD GPU improved SERS accuracy",
        ]

    cpu_result = benchmark.get("cpuResult") if benchmark_available else None
    gpu_result = benchmark.get("gpuResult") if benchmark_available else None

    return {
        "amdGpuEvidenceStatus": evidence.get("amdGpuEvidenceStatus", "AMD_GPU_VERIFIED") if gpu_verified else "AMD_GPU_EVIDENCE_PENDING",
        "amdGpuVerified": gpu_verified,
        "amdBenchmarkAvailable": benchmark_available,
        "amdClaimsAllowed": gpu_verified,
        "amdClaimsScope": claims_scope,
        "allowedClaim": allowed_claim,
        "benchmarkStatus": benchmark.get("benchmarkStatus") if benchmark_available else None,
        "sersGpuTrainingBenchmarkStatus": "complete" if benchmark_available else "pending",
        "cpuGpuSpeedupStatus": "measured on synthetic notebook benchmark only" if benchmark_available else "pending",
        "specificGpuModelClaimed": False,
        "device": evidence.get("device") if evidence else None,
        "deviceCount": evidence.get("deviceCount") if evidence else None,
        "deviceName": evidence.get("deviceName", "") if evidence else "",
        "deviceNameCaveat": evidence.get("deviceNameNote", "No GPU model name is claimed.") if evidence else "No GPU model name is claimed until evidence exists.",
        "torchVersion": evidence.get("torchVersion") if evidence else None,
        "torchCudaAvailable": bool(evidence.get("torchCudaAvailable")) if evidence else False,
        "rocmSmiAvailable": bool(evidence.get("rocmSmiAvailable")) if evidence else False,
        "rocminfoAvailable": bool(evidence.get("rocminfoAvailable")) if evidence else False,
        "matrixBenchmark": evidence.get("matrixBenchmark") if evidence else None,
        "trainingRows": benchmark.get("trainingRows") if benchmark_available else None,
        "testRows": benchmark.get("testRows") if benchmark_available else None,
        "featureCount": benchmark.get("featureCount") if benchmark_available else None,
        "epochs": benchmark.get("epochs") if benchmark_available else None,
        "cpuResult": cpu_result,
        "gpuResult": gpu_result,
        "cpuTrainSeconds": cpu_result.get("trainSeconds") if isinstance(cpu_result, dict) else None,
        "gpuTrainSeconds": gpu_result.get("trainSeconds") if isinstance(gpu_result, dict) else None,
        "speedupRatio": benchmark.get("speedupRatio") if benchmark_available else None,
        "speedupClaimAllowed": bool(benchmark.get("speedupClaimAllowed")) if benchmark_available else False,
        "metricsClaimScope": benchmark.get("metricsClaimScope", "synthetic benchmark only") if benchmark_available else None,
        "notClaimed": not_claimed,
        "artifactPaths": {
            "environmentEvidence": "artifacts/amd_gpu_environment_evidence.json",
            "sersGpuBenchmark": "artifacts/amd_sers_gpu_benchmark.json",
        },
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "sersAdvisoryOnly": True,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
    }


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_amd_acceleration() -> str:
    payload = amd_acceleration_json()
    matrix = payload.get("matrixBenchmark") or {}
    matrix_summary = (
        f'{matrix.get("matrixSize")}x{matrix.get("matrixSize")} matrix, '
        f'{matrix.get("iterations")} iterations, {matrix.get("elapsedSeconds")} seconds'
        if matrix
        else "No matrix benchmark artifact available."
    )

    cpu = payload.get("cpuResult") or {}
    gpu = payload.get("gpuResult") or {}

    if payload["amdBenchmarkAvailable"]:
        benchmark_panel = f"""
      <article class="panel" data-testid="amd-sers-benchmark">
        <h2>Synthetic SERS GPU benchmark</h2>
        <p>Benchmark status: {html.escape(str(payload["benchmarkStatus"]))}</p>
        <p>Training rows: {payload["trainingRows"]}. Test rows: {payload["testRows"]}. Features: {payload["featureCount"]}. Epochs: {payload["epochs"]}.</p>
        <p>CPU train seconds: {_fmt(payload["cpuTrainSeconds"])}. GPU train seconds: {_fmt(payload["gpuTrainSeconds"])}. Speedup ratio: {_fmt(payload["speedupRatio"])}x.</p>
        <p>CPU accuracy: {_fmt(cpu.get("accuracy"))}. GPU accuracy: {_fmt(gpu.get("accuracy"))}.</p>
        <p>CPU precision/recall: {_fmt(cpu.get("precision"))} / {_fmt(cpu.get("recall"))}. GPU precision/recall: {_fmt(gpu.get("precision"))} / {_fmt(gpu.get("recall"))}.</p>
        <p>In this synthetic notebook run, GPU training was faster than CPU. GPU accuracy was not higher than CPU, so no accuracy-improvement claim is made.</p>
      </article>
"""
    else:
        benchmark_panel = """
      <article class="panel" data-testid="amd-sers-benchmark">
        <h2>Synthetic SERS GPU benchmark</h2>
        <p>Pending. No SERS GPU training or CPU/GPU speedup claim is made yet.</p>
      </article>
"""

    body = f"""
  <header data-testid="amd-acceleration-page">
    {global_nav()}
    <h1>AMD GPU Acceleration Evidence</h1>
    <p>Sanitized notebook evidence for AMD ROCm/PyTorch GPU environment verification and synthetic-only SERS benchmarking.</p>
    {badge("AMD environment: " + payload["amdGpuEvidenceStatus"], "good" if payload["amdGpuVerified"] else "warn")}
    {badge("SERS GPU benchmark: " + payload["sersGpuTrainingBenchmarkStatus"], "good" if payload["amdBenchmarkAvailable"] else "warn")}
    {badge("Synthetic only", "warn")}
  </header>
  <main>
    <section class="grid">
      <article class="panel" data-testid="amd-environment-status">
        <h2>Environment status</h2>
        <p>GPU verified: {str(payload["amdGpuVerified"]).lower()}</p>
        <p>ROCm tools: rocm-smi={str(payload["rocmSmiAvailable"]).lower()}, rocminfo={str(payload["rocminfoAvailable"]).lower()}</p>
        <p>PyTorch CUDA-compatible ROCm path: {str(payload["torchCudaAvailable"]).lower()}</p>
        <p>Device path: {html.escape(str(payload["device"]))}</p>
      </article>
      <article class="panel" data-testid="amd-matrix-benchmark">
        <h2>Notebook matrix benchmark</h2>
        <p>{html.escape(matrix_summary)}</p>
        <p>Allowed claim: {html.escape(payload["allowedClaim"])}</p>
      </article>
      {benchmark_panel}
      <article class="panel status-block" data-testid="amd-claim-boundary">
        <h2>Claim boundary</h2>
        <p>{html.escape(payload["deviceNameCaveat"])}</p>
        <p>No real-world validation, production acceleration, pharma/compliance validation, specific GPU model, autonomous action, or AMD accuracy-improvement claim is made.</p>
      </article>
    </section>
    <section class="panel">
      <div class="toolbar">
        <a class="button" href="/amd-acceleration.json">AMD JSON</a>
        <a class="button" href="/gpu-benchmark-plan">GPU Benchmark Plan</a>
        <a class="button" href="/gpu-research-lab">GPU Research Lab</a>
        <a class="button" href="/fireworks-advisory">Fireworks Advisory</a>
        <a class="button" href="/model-benchmark">Model Benchmark</a>
        <a class="button" href="/sers-model-card">SERS Model Card</a>
      </div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel AMD GPU Evidence", body)


def gpu_benchmark_plan_json() -> dict[str, Any]:
    status = amd_acceleration_json()["sersGpuTrainingBenchmarkStatus"]
    return {
        "benchmarkMode": "synthetic_sers_gpu_training",
        "currentStatus": status,
        "steps": [
            "Generate deterministic synthetic SERS training windows.",
            "Train a dependency-light PyTorch model using cuda when ROCm is available.",
            "Measure CPU and GPU timing in the notebook.",
            "Compare SERS metrics against simple baselines on synthetic data.",
            "Export a small sanitized artifacts/amd_sers_gpu_benchmark.json summary.",
            "Update app evidence without committing raw generated datasets or secrets.",
        ],
        "requiredArtifact": "artifacts/amd_sers_gpu_benchmark.json",
        "claimsBoundary": "Claims are limited to synthetic notebook benchmark evidence. No real-world, production, pharma/compliance, specific-GPU-model, or accuracy-improvement claim is made.",
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "sersAdvisoryOnly": True,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False,
    }


def render_gpu_benchmark_plan() -> str:
    payload = gpu_benchmark_plan_json()
    steps = "\n".join(
        f'<li data-testid="gpu-plan-step-{index}">{html.escape(step)}</li>'
        for index, step in enumerate(payload["steps"], start=1)
    )
    body = f"""
  <header data-testid="gpu-benchmark-plan-page">
    {global_nav()}
    <h1>GPU Benchmark Plan</h1>
    <p>Synthetic SERS GPU benchmark evidence flow. Current status: {html.escape(payload["currentStatus"])}.</p>
  </header>
  <main>
    <section class="panel">
      <ol>{steps}</ol>
      <p>{html.escape(payload["claimsBoundary"])}</p>
      <div class="toolbar">
        <a class="button" href="/gpu-benchmark-plan.json">Plan JSON</a>
        <a class="button" href="/amd-acceleration">AMD Evidence</a>
      </div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel GPU Benchmark Plan", body)


@lru_cache(maxsize=1)
def _cached_command_center_with_amd_json() -> dict[str, Any]:
    from command_center_algorithm_v2 import get_command_center_algorithm_payload
    from dashboard_strategy_v2 import get_dashboard_strategy_payload
    payload = command_center_payload()
    amd = amd_acceleration_json()
    strategy = get_dashboard_strategy_payload()
    algorithm = get_command_center_algorithm_payload()
    payload["amdAccelerationSummary"] = {
        "amdGpuEvidenceStatus": amd["amdGpuEvidenceStatus"],
        "amdGpuVerified": amd["amdGpuVerified"],
        "amdBenchmarkAvailable": amd["amdBenchmarkAvailable"],
        "sersGpuTrainingBenchmarkStatus": amd["sersGpuTrainingBenchmarkStatus"],
        "speedupRatio": amd["speedupRatio"],
        "specificGpuModelClaimed": False,
        "claimsScope": amd["amdClaimsScope"],
    }
    payload["dashboardStrategySummary"] = {
        "sentinelReadinessScore": strategy["sentinelReadinessScore"],
        "evidenceConfidencePulse": strategy["evidenceConfidencePulse"],
        "whatNext": strategy["whatNext"],
        "demoHighlights": strategy["demoHighlights"],
        "whyLayer": strategy["whyLayer"],
    }
    payload["algorithmIntegrationSummary"] = {
        "headlineMetrics": algorithm["headlineMetrics"],
        "topAlgorithmInsights": algorithm["topAlgorithmInsights"],
        "whatToInspectNext": algorithm["whatToInspectNext"],
        "safetyBoundary": algorithm["safetyBoundary"],
    }
    payload.setdefault("routeMap", {})["amdAcceleration"] = "/amd-acceleration"
    payload.setdefault("routeMap", {})["gpuBenchmarkPlan"] = "/gpu-benchmark-plan"
    payload.setdefault("routeMap", {})["gpuResearchLab"] = "/gpu-research-lab"
    payload.setdefault("routeMap", {})["fireworksAdvisory"] = "/fireworks-advisory"
    payload.setdefault("routeMap", {})["demoConsole"] = "/demo-console"
    payload.setdefault("routeMap", {})["judgeEvidence"] = "/judge-evidence"
    payload.setdefault("routeMap", {})["finalValidation"] = "/final-validation"
    payload.setdefault("routeMap", {})["validationPacket"] = "/validation-packet"
    payload.setdefault("routeMap", {})["integrationSandbox"] = "/integration-sandbox"
    payload.setdefault("routeMap", {})["auditLedger"] = "/audit-ledger"
    payload.setdefault("routeMap", {})["reviewerWorkspace"] = "/reviewer-workspace"
    payload.setdefault("routeMap", {})["fireworksCoverage"] = "/fireworks-coverage"
    payload.setdefault("routeMap", {})["opsReadiness"] = "/ops-readiness"
    payload.setdefault("routeMap", {})["evidenceHealth"] = "/evidence-health.json"
    payload.setdefault("routeMap", {})["productionGapAnalysis"] = "/production-gap-analysis"
    payload.setdefault("routeMap", {})["expandedBenchmark"] = "/expanded-benchmark"
    payload.setdefault("routeMap", {})["benchmarkRefresh"] = "/benchmark-refresh"
    payload.setdefault("routeMap", {}).update({
        "scenarioLibraryV4": "/scenario-library-v4",
        "evaluationMatrixV2": "/evaluation-matrix-v2",
        "evidenceExport": "/evidence-export",
        "policySandbox": "/policy-sandbox",
        "llmAdvisoryEval": "/llm-advisory-eval",
        "routeReliability": "/route-reliability",
        "demoSafeMode": "/demo-safe-mode",
        "decisionSimulator": "/decision-simulator",
        "partnerApiContract": "/partner-api-contract",
        "demoFlow": "/demo-flow",
        "demoNavigation": "/demo-navigation",
        "navigationMap": "/navigation-map",
        "demoFreeze": "/demo-freeze",
        "finalDemoChecklist": "/final-demo-checklist",
        "dashboardStrategy": "/dashboard-strategy",
        "screenshotWorthyDashboard": "/screenshot-worthy-dashboard",
        "behaviorPredictor": "/behavior-predictor",
        "behaviorPredictorModelCard": "/behavior-predictor/model-card.json",
        "inspectionEngine": "/inspection-engine",
        "algorithmConsole": "/algorithm-console",
        "commandCenterAlgorithm": "/command-center-algorithm",
        "algorithmInsights": "/algorithm-insights",
        "whatToInspectNext": "/what-to-inspect-next.json",
        "judgePack": "/judge-pack",
        "largeScaleDataLab": "/large-scale-data-lab",
        "faultAtlas": "/fault-atlas",
        "caseWalkthroughs": "/case-walkthroughs",
        "finalRouteManifest": "/final-route-manifest",
        "submissionReadiness": "/submission-readiness",
        "demoScriptFinal": "/demo-script-final",
        "visualPolish": "/visual-polish",
        "finalFreeze": "/final-freeze",
    })
    payload.update({
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "runtimePyTorchRequired": False,
        "autonomousActionsAllowed": False,
        "deterministicRulesAuthoritative": True,
        "uiVersion": "coherent-fast-v1",
        "simplifiedDashboard": True,
        "performanceOptimized": True,
        "primaryDemoRoutes": ["/case-walkthroughs/door-open-warming", "/algorithm-console", "/judge-pack", "/submission-readiness"],
        "aboveTheFoldActions": 4,
        "visibleMetricCount": 4,
        "visibleInspectionCardCount": 4,
    })
    return payload


def command_center_with_amd_json() -> dict[str, Any]:
    # ponytail: static synthetic summary; invalidate only when source evidence changes.
    return deepcopy(_cached_command_center_with_amd_json())


def render_command_center_with_amd() -> str:
    inspections = [
        ("Door-open warming", "Door event timeline and affected zone", "/case-walkthroughs/door-open-warming"),
        ("Gateway delay", "Gateway receipt timestamps and route segment", "/case-walkthroughs/gateway-delay"),
        ("Unresolved mapping", "Pallet-zone identity mapping", "/case-walkthroughs/unresolved-mapping-risk"),
        ("Mixed quality evidence", "Quality warnings before interpretation", "/case-walkthroughs/mixed-quality-evidence"),
    ]
    inspection_cards = "".join(f'<article class="ui-panel"><h3>{html.escape(title)}</h3><p class="ui-subtitle">{html.escape(target)}</p><a href="{route}">Inspect case</a></article>' for title, target, route in inspections)
    evidence = render_route_buttons([
        ("Algorithm Console", "/algorithm-console"), ("Behavior Predictor", "/behavior-predictor"),
        ("Inspection Engine", "/inspection-engine"), ("Fault Atlas", "/fault-atlas"),
        ("Large Scale Data Lab", "/large-scale-data-lab"), ("Final Route Manifest", "/final-route-manifest"),
    ])
    sections = f'''{render_metric_cards([("171,000", "synthetic rows"), ("38", "fault classes"), ("95.51%", "neural fault accuracy"), ("94.06%", "distilled behavior accuracy")])}
    <section class="ui-section"><h2>What to inspect next</h2><p class="ui-subtitle">Choose one concise evidence path instead of scanning the full route inventory.</p><div class="ui-grid">{inspection_cards}</div></section>
    <section class="ui-safety"><h2>Why it is safe</h2><p>No real data. No autonomous operations. Deterministic rules remain authoritative. No runtime GPU or PyTorch.</p></section>
    <section class="ui-section"><h2>Evidence map</h2><p class="ui-subtitle">Open a focused detail route when you need deeper evidence.</p>{evidence}</section>'''
    return render_page_shell(
        "ColdChain Sentinel", "Synthetic-only. Advisory-only. Human-review-first.",
        ["Synthetic-only", "Advisory-only", "Human-review-first"],
        [("Start Demo", "/case-walkthroughs/door-open-warming"), ("Algorithm Evidence", "/algorithm-console"), ("Judge Pack", "/judge-pack"), ("Submission", "/submission-readiness")],
        sections,
        [("Dashboard Strategy", "/dashboard-strategy"), ("Final Freeze", "/final-freeze")],
    )


def render_root_with_design_system() -> str:
    sections = '''<section class="ui-section"><h2>Start here</h2><p class="ui-subtitle">Follow one synthetic case from signal to a human inspection target.</p></section>
    <section class="ui-safety"><h2>Safety boundary</h2><p>Synthetic-only evidence. Advisory-only signals. Deterministic rules remain authoritative and operational actions stay with humans.</p></section>'''
    return render_page_shell(
        "ColdChain Sentinel", "A concise evidence path for synthetic cold-chain review.",
        ["Synthetic-only", "Advisory-only", "Deterministic rules authoritative"],
        [("Command Center", "/command-center"), ("Judge Pack", "/judge-pack"), ("Case Walkthroughs", "/case-walkthroughs"), ("Algorithm Console", "/algorithm-console"), ("Submission", "/submission-readiness")],
        sections,
        [("Review cases", "/cases"), ("Review workspace", "/cases/blocked-unresolved-pallet/review"), ("Sensor Lab", "/sensor-lab"), ("Data Pipeline", "/data-pipeline")],
    )


def system_status_with_amd_json() -> dict[str, Any]:
    status = system_status_json()
    amd = amd_acceleration_json()
    status.update({
        "amdGpuEvidenceStatus": amd["amdGpuEvidenceStatus"],
        "amdGpuVerified": amd["amdGpuVerified"],
        "amdBenchmarkAvailable": amd["amdBenchmarkAvailable"],
        "amdClaimsAllowed": amd["amdClaimsAllowed"],
        "amdClaimsScope": amd["amdClaimsScope"],
        "specificGpuModelClaimed": False,
        "sersGpuTrainingBenchmarkStatus": amd["sersGpuTrainingBenchmarkStatus"],
        "speedupRatio": amd["speedupRatio"],
        "metricsClaimScope": amd["metricsClaimScope"],
    })
    return status


def validation_evidence_with_amd_json() -> dict[str, Any]:
    payload = validation_evidence_json()
    payload["amdAccelerationEvidence"] = amd_acceleration_json()
    return payload


class AmdDashboardHandler(BaseDashboardHandler):
    def do_GET(self) -> None:
        # Phases 43-47 - final submission readiness and owner freeze decision
        final_path = self.path.split("?", 1)[0]
        if final_path in ("/", "/index.html"):
            self.respond_text(render_root_with_design_system())
            return
        final_routes = {
            "/final-route-manifest", "/final-route-manifest.json", "/live-qa-checklist",
            "/live-qa-checklist.json", "/live-validation-script.ps1", "/submission-readiness",
            "/submission-readiness.json", "/submission-checklist", "/submission-checklist.json",
            "/submission-copy.json", "/demo-script-final", "/demo-script-final.json", "/judge-qna",
            "/judge-qna.json", "/safe-claims-guide.json", "/visual-polish", "/visual-polish.json",
            "/screenshot-checklist", "/screenshot-checklist.json", "/screenshot-route-map.json",
            "/final-freeze", "/final-freeze.json", "/owner-freeze-decision.json",
        }
        if final_path in final_routes:
            import json as final_json
            from demo_script_qna_v2 import get_demo_script_final_payload, get_judge_qna_payload, get_safe_claims_guide_payload, render_demo_script_qna_html
            from final_freeze_v2 import get_final_freeze_payload, get_owner_freeze_decision_payload, render_final_freeze_html
            from final_route_manifest_v2 import get_final_route_manifest_payload, get_live_qa_checklist_payload, get_live_validation_script, render_final_route_manifest_html
            from final_visual_polish_v2 import get_screenshot_checklist_payload, get_screenshot_route_map_payload, get_visual_polish_payload, render_visual_polish_html
            from submission_readiness_v2 import get_submission_checklist_payload, get_submission_copy_payload, get_submission_readiness_payload, render_submission_readiness_html
            if final_path in ("/final-route-manifest", "/live-qa-checklist"): body, content_type = render_final_route_manifest_html(), "text/html; charset=utf-8"
            elif final_path == "/final-route-manifest.json": body, content_type = final_json.dumps(get_final_route_manifest_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/live-qa-checklist.json": body, content_type = final_json.dumps(get_live_qa_checklist_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/live-validation-script.ps1": body, content_type = get_live_validation_script(), "text/plain; charset=utf-8"
            elif final_path in ("/submission-readiness", "/submission-checklist"): body, content_type = render_submission_readiness_html(), "text/html; charset=utf-8"
            elif final_path == "/submission-readiness.json": body, content_type = final_json.dumps(get_submission_readiness_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/submission-checklist.json": body, content_type = final_json.dumps(get_submission_checklist_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/submission-copy.json": body, content_type = final_json.dumps(get_submission_copy_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path in ("/demo-script-final", "/judge-qna"): body, content_type = render_demo_script_qna_html(), "text/html; charset=utf-8"
            elif final_path == "/demo-script-final.json": body, content_type = final_json.dumps(get_demo_script_final_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/judge-qna.json": body, content_type = final_json.dumps(get_judge_qna_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/safe-claims-guide.json": body, content_type = final_json.dumps(get_safe_claims_guide_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path in ("/visual-polish", "/screenshot-checklist"): body, content_type = render_visual_polish_html(), "text/html; charset=utf-8"
            elif final_path == "/visual-polish.json": body, content_type = final_json.dumps(get_visual_polish_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/screenshot-checklist.json": body, content_type = final_json.dumps(get_screenshot_checklist_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/screenshot-route-map.json": body, content_type = final_json.dumps(get_screenshot_route_map_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif final_path == "/final-freeze": body, content_type = render_final_freeze_html(), "text/html; charset=utf-8"
            elif final_path == "/final-freeze.json": body, content_type = final_json.dumps(get_final_freeze_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            else: body, content_type = final_json.dumps(get_owner_freeze_decision_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phases 39-42 - judge evidence, scale profiles, fault atlas, and walkthroughs
        evidence_path = self.path.split("?", 1)[0]
        evidence_exact = {
            "/judge-pack", "/judge-pack.json", "/judge-pack/demo-script.json",
            "/judge-pack/technical-proof.json", "/judge-pack/claims-boundary.json",
            "/large-scale-data-lab", "/large-scale-data-lab.json",
            "/large-scale-data-lab/profiles.json", "/large-scale-data-lab/throughput-summary.json",
            "/fault-atlas", "/fault-atlas.json", "/fault-atlas/coverage.json",
            "/case-walkthroughs", "/case-walkthroughs.json",
        }
        evidence_parts = [part for part in evidence_path.split("/") if part]
        fault_detail = len(evidence_parts) == 2 and evidence_parts[0] == "fault-atlas" and evidence_parts[1].endswith(".json")
        case_detail = len(evidence_parts) == 2 and evidence_parts[0] == "case-walkthroughs"
        if evidence_path in evidence_exact or fault_detail or case_detail:
            import json as evidence_json
            from case_walkthroughs_v2 import get_case_walkthrough_payload, get_case_walkthroughs_payload, render_case_walkthroughs_html
            from fault_atlas_v2 import get_fault_atlas_coverage_payload, get_fault_atlas_payload, get_fault_detail_payload, render_fault_atlas_html
            from judge_evidence_pack_v2 import get_claims_boundary_payload, get_demo_script_payload, get_judge_evidence_pack_payload, get_technical_proof_payload, render_judge_evidence_pack_html
            from large_scale_data_lab_v2 import get_large_scale_data_lab_payload, get_large_scale_profiles_payload, get_throughput_summary_payload, render_large_scale_data_lab_html
            try:
                if evidence_path == "/judge-pack": body, content_type = render_judge_evidence_pack_html(), "text/html; charset=utf-8"
                elif evidence_path == "/judge-pack.json": body, content_type = evidence_json.dumps(get_judge_evidence_pack_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/judge-pack/demo-script.json": body, content_type = evidence_json.dumps(get_demo_script_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/judge-pack/technical-proof.json": body, content_type = evidence_json.dumps(get_technical_proof_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/judge-pack/claims-boundary.json": body, content_type = evidence_json.dumps(get_claims_boundary_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/large-scale-data-lab": body, content_type = render_large_scale_data_lab_html(), "text/html; charset=utf-8"
                elif evidence_path == "/large-scale-data-lab.json": body, content_type = evidence_json.dumps(get_large_scale_data_lab_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/large-scale-data-lab/profiles.json": body, content_type = evidence_json.dumps(get_large_scale_profiles_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/large-scale-data-lab/throughput-summary.json": body, content_type = evidence_json.dumps(get_throughput_summary_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/fault-atlas": body, content_type = render_fault_atlas_html(), "text/html; charset=utf-8"
                elif evidence_path == "/fault-atlas.json": body, content_type = evidence_json.dumps(get_fault_atlas_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/fault-atlas/coverage.json": body, content_type = evidence_json.dumps(get_fault_atlas_coverage_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif fault_detail:
                    body, content_type = evidence_json.dumps(get_fault_detail_payload(evidence_parts[1][:-5]), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif evidence_path == "/case-walkthroughs": body, content_type = render_case_walkthroughs_html(), "text/html; charset=utf-8"
                elif evidence_path == "/case-walkthroughs.json": body, content_type = evidence_json.dumps(get_case_walkthroughs_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                else:
                    case_id = evidence_parts[1][:-5] if evidence_parts[1].endswith(".json") else evidence_parts[1]
                    payload = get_case_walkthrough_payload(case_id)
                    body, content_type = (evidence_json.dumps(payload, indent=2, sort_keys=True), "application/json; charset=utf-8") if evidence_parts[1].endswith(".json") else (render_case_walkthroughs_html(case_id), "text/html; charset=utf-8")
                self.send_response(200)
            except KeyError:
                body, content_type = evidence_json.dumps({"error": "not found", "path": evidence_path}, sort_keys=True), "application/json; charset=utf-8"
                self.send_response(404)
            self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phases 37-38 - algorithm evidence and command-center insights
        algorithm_path = self.path.split("?", 1)[0]
        algorithm_routes = {
            "/algorithm-console", "/algorithm-console.json", "/algorithm-console/feature-weights.json",
            "/algorithm-console/error-coverage.json", "/algorithm-console/prediction-table.json",
            "/algorithm-console/weaknesses.json", "/algorithm-console/runtime-boundary.json",
            "/command-center-algorithm", "/command-center-algorithm.json", "/algorithm-insights",
            "/algorithm-insights.json", "/what-to-inspect-next.json",
        }
        if algorithm_path in algorithm_routes:
            import json as algorithm_json
            from algorithm_console_v2 import (
                get_algorithm_console_payload, get_error_coverage_payload, get_feature_weights_payload,
                get_prediction_table_payload, get_runtime_boundary_payload, get_weaknesses_payload,
                render_algorithm_console_html,
            )
            from command_center_algorithm_v2 import (
                get_command_center_algorithm_payload, get_what_to_inspect_next_payload,
                render_command_center_algorithm_html,
            )
            if algorithm_path == "/algorithm-console": body, content_type = render_algorithm_console_html(), "text/html; charset=utf-8"
            elif algorithm_path == "/algorithm-console.json": body, content_type = algorithm_json.dumps(get_algorithm_console_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif algorithm_path == "/algorithm-console/feature-weights.json": body, content_type = algorithm_json.dumps(get_feature_weights_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif algorithm_path == "/algorithm-console/error-coverage.json": body, content_type = algorithm_json.dumps(get_error_coverage_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif algorithm_path == "/algorithm-console/prediction-table.json": body, content_type = algorithm_json.dumps(get_prediction_table_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif algorithm_path == "/algorithm-console/weaknesses.json": body, content_type = algorithm_json.dumps(get_weaknesses_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif algorithm_path == "/algorithm-console/runtime-boundary.json": body, content_type = algorithm_json.dumps(get_runtime_boundary_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif algorithm_path in ("/command-center-algorithm", "/algorithm-insights"): body, content_type = render_command_center_algorithm_html(), "text/html; charset=utf-8"
            elif algorithm_path == "/what-to-inspect-next.json": body, content_type = algorithm_json.dumps(get_what_to_inspect_next_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            else: body, content_type = algorithm_json.dumps(get_command_center_algorithm_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phases 35B-36 - distilled behavior prediction and inspection guidance
        stbl_path = self.path.split("?", 1)[0]
        stbl_exact = {
            "/behavior-predictor", "/behavior-predictor.json",
            "/behavior-predictor/model-card.json", "/behavior-predictor/training-artifact.json",
            "/behavior-predictor/distilled-rules.json", "/inspection-engine", "/inspection-engine.json",
        }
        stbl_parts = [part for part in stbl_path.split("/") if part]
        stbl_case_route = (
            len(stbl_parts) == 3 and stbl_parts[0] == "cases"
            and stbl_parts[2] in ("behavior-prediction.json", "inspection-plan.json", "root-cause-analysis.json")
        )
        if stbl_path in stbl_exact or stbl_case_route:
            import json as stbl_json
            from behavior_predictor_v2 import (
                get_behavior_predictor_payload, get_distilled_rules_payload, get_model_card_payload,
                get_training_artifact_payload, predict_case_behavior, render_behavior_predictor_html,
            )
            from inspection_engine_v2 import (
                get_inspection_engine_payload, get_inspection_plan, get_root_cause_analysis,
                render_inspection_engine_html,
            )
            try:
                if stbl_path == "/behavior-predictor": body, content_type = render_behavior_predictor_html(), "text/html; charset=utf-8"
                elif stbl_path == "/behavior-predictor.json": body, content_type = stbl_json.dumps(get_behavior_predictor_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif stbl_path == "/behavior-predictor/model-card.json": body, content_type = stbl_json.dumps(get_model_card_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif stbl_path == "/behavior-predictor/training-artifact.json": body, content_type = stbl_json.dumps(get_training_artifact_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif stbl_path == "/behavior-predictor/distilled-rules.json": body, content_type = stbl_json.dumps(get_distilled_rules_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif stbl_path == "/inspection-engine": body, content_type = render_inspection_engine_html(), "text/html; charset=utf-8"
                elif stbl_path == "/inspection-engine.json": body, content_type = stbl_json.dumps(get_inspection_engine_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif stbl_parts[2] == "behavior-prediction.json": body, content_type = stbl_json.dumps(predict_case_behavior(stbl_parts[1]), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif stbl_parts[2] == "inspection-plan.json": body, content_type = stbl_json.dumps(get_inspection_plan(stbl_parts[1]), indent=2, sort_keys=True), "application/json; charset=utf-8"
                else: body, content_type = stbl_json.dumps(get_root_cause_analysis(stbl_parts[1]), indent=2, sort_keys=True), "application/json; charset=utf-8"
            except KeyError:
                self.send_response(404); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(stbl_json.dumps({"error": "unknown case"}).encode("utf-8")); return
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phase 33 - screenshot-worthy command center strategy
        phase33_path = self.path.split("?", 1)[0]
        if phase33_path in (
            "/dashboard-strategy", "/dashboard-strategy.json", "/screenshot-worthy-dashboard",
            "/screenshot-worthy-dashboard.json", "/command-center-strategy.json",
        ):
            import json as phase33_json
            from dashboard_strategy_v2 import get_dashboard_strategy_payload, render_dashboard_strategy_html
            if phase33_path in ("/dashboard-strategy", "/screenshot-worthy-dashboard"):
                body, content_type = render_dashboard_strategy_html(), "text/html; charset=utf-8"
            else:
                body, content_type = phase33_json.dumps(get_dashboard_strategy_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phases 31-32 - demo freeze gate and navigation polish
        phase3132_path = self.path.split("?", 1)[0]
        if phase3132_path in (
            "/demo-freeze", "/demo-freeze.json", "/final-demo-checklist", "/final-demo-checklist.json",
            "/demo-navigation", "/demo-navigation.json", "/navigation-map", "/navigation-map.json",
        ):
            import json as phase3132_json
            from demo_freeze_gate_v2 import get_demo_freeze_gate_payload, render_demo_freeze_gate_html
            from demo_navigation_v2 import get_demo_navigation_payload, render_demo_navigation_html
            if phase3132_path in ("/demo-freeze", "/final-demo-checklist"):
                body, content_type = render_demo_freeze_gate_html(), "text/html; charset=utf-8"
            elif phase3132_path in ("/demo-freeze.json", "/final-demo-checklist.json"):
                body, content_type = phase3132_json.dumps(get_demo_freeze_gate_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            elif phase3132_path in ("/demo-navigation", "/navigation-map"):
                body, content_type = render_demo_navigation_html(), "text/html; charset=utf-8"
            else:
                body, content_type = phase3132_json.dumps(get_demo_navigation_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phases 29-30 - static partner contract and guided demo flow
        phase2930_path = self.path.split("?", 1)[0]
        phase2930_exact = {
            "/partner-api-contract", "/partner-api-contract.json", "/partner-api-contract/openapi-preview.json",
            "/partner-api-contract/errors.json", "/partner-api-contract/sample-request.json", "/partner-api-contract/sample-response.json",
            "/demo-flow", "/demo-flow.json",
        }
        phase2930_step_paths = {f"/demo-flow/step-{number}" for number in range(1, 15)}
        if phase2930_path in phase2930_exact or phase2930_path in phase2930_step_paths:
            import json as phase2930_json
            from demo_flow_v2 import get_demo_flow_payload, render_demo_flow_html, render_demo_step_html
            from partner_api_contract_v2 import (
                get_openapi_preview_payload, get_partner_api_contract_payload, get_partner_error_catalog_payload,
                get_partner_sample_request_payload, get_partner_sample_response_payload, render_partner_api_contract_html,
            )
            try:
                if phase2930_path == "/partner-api-contract": body, content_type = render_partner_api_contract_html(), "text/html; charset=utf-8"
                elif phase2930_path == "/partner-api-contract.json": body, content_type = phase2930_json.dumps(get_partner_api_contract_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2930_path == "/partner-api-contract/openapi-preview.json": body, content_type = phase2930_json.dumps(get_openapi_preview_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2930_path == "/partner-api-contract/errors.json": body, content_type = phase2930_json.dumps(get_partner_error_catalog_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2930_path == "/partner-api-contract/sample-request.json": body, content_type = phase2930_json.dumps(get_partner_sample_request_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2930_path == "/partner-api-contract/sample-response.json": body, content_type = phase2930_json.dumps(get_partner_sample_response_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2930_path == "/demo-flow": body, content_type = render_demo_flow_html(), "text/html; charset=utf-8"
                elif phase2930_path == "/demo-flow.json": body, content_type = phase2930_json.dumps(get_demo_flow_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                else: body, content_type = render_demo_step_html(int(phase2930_path.rsplit("-", 1)[-1])), "text/html; charset=utf-8"
            except (KeyError, ValueError):
                self.send_response(404); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(phase2930_json.dumps({"error": "unknown demo step"}).encode("utf-8")); return
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phases 22-28 - static expanded evidence, evaluation, exports, and review simulation
        phase2228_path = self.path.split("?", 1)[0]
        phase2228_exact = {
            "/scenario-library-v4", "/scenario-library-v4.json", "/evaluation-matrix-v2", "/evaluation-matrix-v2.json",
            "/evidence-export", "/evidence-export.json", "/evidence-export/summary.md", "/evidence-export/routes.json",
            "/policy-sandbox", "/policy-sandbox.json", "/policy-sandbox/sample-sop.md", "/policy-sandbox/mapping.json",
            "/llm-advisory-eval", "/llm-advisory-eval.json", "/llm-advisory-eval/safety-cases.json",
            "/route-reliability", "/route-reliability.json", "/demo-safe-mode", "/demo-safe-mode.json",
            "/decision-simulator", "/decision-simulator.json",
        }
        phase2228_parts = [part for part in phase2228_path.split("/") if part]
        phase2228_dynamic = (
            phase2228_path.startswith("/scenario-library-v4/") and phase2228_path.endswith(".json")
        ) or (
            phase2228_path.startswith("/decision-simulator/") and phase2228_path.endswith(".json")
        ) or (
            len(phase2228_parts) == 3
            and phase2228_parts[0] == "cases"
            and phase2228_parts[2] in ("expanded-evidence.json", "evaluation-row.json")
        )
        if phase2228_path in phase2228_exact or phase2228_dynamic:
            import json as phase2228_json
            from decision_simulator_v2 import get_decision_simulator_case_payload, get_decision_simulator_payload, render_decision_simulator_html
            from evaluation_matrix_v2 import get_evaluation_matrix_payload, get_evaluation_row_payload, render_evaluation_matrix_html
            from evidence_export_pack_v2 import get_evidence_export_payload, get_evidence_route_manifest_payload, render_evidence_export_html
            from llm_advisory_eval_v2 import get_llm_advisory_eval_payload, get_llm_safety_cases_payload, render_llm_advisory_eval_html
            from policy_sandbox_v2 import get_policy_mapping_payload, get_policy_sandbox_payload, render_policy_sandbox_html
            from route_reliability_v2 import get_route_reliability_payload, render_route_reliability_html
            from scenario_library_v4 import get_expanded_scenario_payload, get_scenario_library_payload, render_scenario_library_html
            try:
                if phase2228_path == "/scenario-library-v4": body, content_type = render_scenario_library_html(), "text/html; charset=utf-8"
                elif phase2228_path == "/scenario-library-v4.json": body, content_type = phase2228_json.dumps(get_scenario_library_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path.startswith("/scenario-library-v4/"):
                    body, content_type = phase2228_json.dumps(get_expanded_scenario_payload(phase2228_path.rsplit("/", 1)[-1][:-5]), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path.endswith("/expanded-evidence.json"):
                    body, content_type = phase2228_json.dumps(get_expanded_scenario_payload(phase2228_path.split("/")[2]), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/evaluation-matrix-v2": body, content_type = render_evaluation_matrix_html(), "text/html; charset=utf-8"
                elif phase2228_path == "/evaluation-matrix-v2.json": body, content_type = phase2228_json.dumps(get_evaluation_matrix_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path.endswith("/evaluation-row.json"):
                    body, content_type = phase2228_json.dumps(get_evaluation_row_payload(phase2228_path.split("/")[2]), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/evidence-export": body, content_type = render_evidence_export_html(), "text/html; charset=utf-8"
                elif phase2228_path == "/evidence-export.json": body, content_type = phase2228_json.dumps(get_evidence_export_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/evidence-export/summary.md": body, content_type = get_evidence_export_payload()["summaryMarkdown"], "text/markdown; charset=utf-8"
                elif phase2228_path == "/evidence-export/routes.json": body, content_type = phase2228_json.dumps(get_evidence_route_manifest_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/policy-sandbox": body, content_type = render_policy_sandbox_html(), "text/html; charset=utf-8"
                elif phase2228_path == "/policy-sandbox.json": body, content_type = phase2228_json.dumps(get_policy_sandbox_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/policy-sandbox/sample-sop.md": body, content_type = get_policy_sandbox_payload()["sampleSyntheticSopMarkdown"], "text/markdown; charset=utf-8"
                elif phase2228_path == "/policy-sandbox/mapping.json": body, content_type = phase2228_json.dumps(get_policy_mapping_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/llm-advisory-eval": body, content_type = render_llm_advisory_eval_html(), "text/html; charset=utf-8"
                elif phase2228_path == "/llm-advisory-eval.json": body, content_type = phase2228_json.dumps(get_llm_advisory_eval_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/llm-advisory-eval/safety-cases.json": body, content_type = phase2228_json.dumps(get_llm_safety_cases_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path in ("/route-reliability", "/demo-safe-mode"): body, content_type = render_route_reliability_html(), "text/html; charset=utf-8"
                elif phase2228_path in ("/route-reliability.json", "/demo-safe-mode.json"): body, content_type = phase2228_json.dumps(get_route_reliability_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                elif phase2228_path == "/decision-simulator": body, content_type = render_decision_simulator_html(), "text/html; charset=utf-8"
                elif phase2228_path == "/decision-simulator.json": body, content_type = phase2228_json.dumps(get_decision_simulator_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8"
                else: body, content_type = phase2228_json.dumps(get_decision_simulator_case_payload(phase2228_path.rsplit("/", 1)[-1][:-5]), indent=2, sort_keys=True), "application/json; charset=utf-8"
            except KeyError:
                self.send_response(404); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(phase2228_json.dumps({"error": "unknown synthetic case"}).encode("utf-8")); return
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body.encode("utf-8")); return

        # Phase 21 route wiring - expanded synthetic benchmark artifact
        phase21_path = self.path.split("?", 1)[0]
        if phase21_path in (
            "/expanded-benchmark",
            "/expanded-benchmark.json",
            "/benchmark-refresh",
            "/benchmark-refresh.json",
        ):
            import json as phase21_json
            from expanded_benchmark_v2 import get_expanded_benchmark_payload, render_expanded_benchmark_html

            if phase21_path in ("/expanded-benchmark", "/benchmark-refresh"):
                phase21_body = render_expanded_benchmark_html()
                phase21_type = "text/html; charset=utf-8"
            else:
                phase21_body = phase21_json.dumps(get_expanded_benchmark_payload(), indent=2, sort_keys=True)
                phase21_type = "application/json; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", phase21_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase21_body.encode("utf-8"))
            return

        # Phase 19/20 route wiring - static evidence health and gap analysis
        phase1920_path = self.path.split("?", 1)[0]
        if phase1920_path in (
            "/ops-readiness",
            "/ops-readiness.json",
            "/evidence-health.json",
            "/production-gap-analysis",
            "/production-gap-analysis.json",
        ):
            import json as phase1920_json
            from ops_readiness_v2 import get_ops_readiness_payload, render_ops_readiness_html
            from production_gap_analysis_v2 import (
                get_production_gap_analysis_payload,
                render_production_gap_analysis_html,
            )

            if phase1920_path == "/ops-readiness":
                phase1920_body = render_ops_readiness_html()
                phase1920_type = "text/html; charset=utf-8"
            elif phase1920_path in ("/ops-readiness.json", "/evidence-health.json"):
                phase1920_body = phase1920_json.dumps(get_ops_readiness_payload(), indent=2, sort_keys=True)
                phase1920_type = "application/json; charset=utf-8"
            elif phase1920_path == "/production-gap-analysis":
                phase1920_body = render_production_gap_analysis_html()
                phase1920_type = "text/html; charset=utf-8"
            else:
                phase1920_body = phase1920_json.dumps(get_production_gap_analysis_payload(), indent=2, sort_keys=True)
                phase1920_type = "application/json; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", phase1920_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase1920_body.encode("utf-8"))
            return

        # Phase 17/18 route wiring - static reviewer workflow and advisory coverage
        phase1718_path = self.path.split("?", 1)[0]
        if phase1718_path in (
            "/reviewer-workspace",
            "/reviewer-workspace.json",
            "/fireworks-coverage",
            "/fireworks-coverage.json",
        ) or (phase1718_path.startswith("/reviewer-workspace/") and phase1718_path.endswith(".json")):
            import json as phase1718_json
            from fireworks_coverage_v2 import get_fireworks_coverage_payload, render_fireworks_coverage_html
            from reviewer_workspace_v3 import (
                get_case_reviewer_workspace_payload,
                get_reviewer_workspace_payload,
                render_reviewer_workspace_html,
            )

            if phase1718_path == "/reviewer-workspace":
                phase1718_body = render_reviewer_workspace_html()
                phase1718_type = "text/html; charset=utf-8"
            elif phase1718_path == "/reviewer-workspace.json":
                phase1718_body = phase1718_json.dumps(get_reviewer_workspace_payload(), indent=2, sort_keys=True)
                phase1718_type = "application/json; charset=utf-8"
            elif phase1718_path == "/fireworks-coverage":
                phase1718_body = render_fireworks_coverage_html()
                phase1718_type = "text/html; charset=utf-8"
            elif phase1718_path == "/fireworks-coverage.json":
                phase1718_body = phase1718_json.dumps(get_fireworks_coverage_payload(), indent=2, sort_keys=True)
                phase1718_type = "application/json; charset=utf-8"
            else:
                phase1718_case_id = phase1718_path.rsplit("/", 1)[-1][:-5]
                try:
                    phase1718_body = phase1718_json.dumps(
                        get_case_reviewer_workspace_payload(phase1718_case_id), indent=2, sort_keys=True
                    )
                except KeyError:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(phase1718_json.dumps({"error": "unknown synthetic reviewer case"}).encode("utf-8"))
                    return
                phase1718_type = "application/json; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", phase1718_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase1718_body.encode("utf-8"))
            return

        # Phase 15/16 route wiring - static integration contracts and audit ledger
        phase1516_path = self.path.split("?", 1)[0]
        if phase1516_path in (
            "/integration-sandbox",
            "/integration-sandbox.json",
            "/integration-sandbox/sample-request.json",
            "/integration-sandbox/sample-response.json",
            "/integration-sandbox/rejection-example.json",
            "/audit-ledger",
            "/audit-ledger.json",
        ) or (phase1516_path.startswith("/cases/") and phase1516_path.endswith("/audit-ledger.json")):
            import json as phase1516_json
            from audit_ledger_v2 import get_audit_ledger_payload, get_case_audit_ledger_payload, render_audit_ledger_html
            from integration_sandbox_v2 import (
                get_integration_sandbox_payload,
                get_rejection_example_payload,
                get_sample_request_payload,
                get_sample_response_payload,
                render_integration_sandbox_html,
            )

            if phase1516_path == "/integration-sandbox":
                phase1516_body = render_integration_sandbox_html()
                phase1516_type = "text/html; charset=utf-8"
            elif phase1516_path == "/integration-sandbox.json":
                phase1516_body = phase1516_json.dumps(get_integration_sandbox_payload(), indent=2, sort_keys=True)
                phase1516_type = "application/json; charset=utf-8"
            elif phase1516_path == "/integration-sandbox/sample-request.json":
                phase1516_body = phase1516_json.dumps(get_sample_request_payload(), indent=2, sort_keys=True)
                phase1516_type = "application/json; charset=utf-8"
            elif phase1516_path == "/integration-sandbox/sample-response.json":
                phase1516_body = phase1516_json.dumps(get_sample_response_payload(), indent=2, sort_keys=True)
                phase1516_type = "application/json; charset=utf-8"
            elif phase1516_path == "/integration-sandbox/rejection-example.json":
                phase1516_body = phase1516_json.dumps(get_rejection_example_payload(), indent=2, sort_keys=True)
                phase1516_type = "application/json; charset=utf-8"
            elif phase1516_path == "/audit-ledger":
                phase1516_body = render_audit_ledger_html()
                phase1516_type = "text/html; charset=utf-8"
            elif phase1516_path == "/audit-ledger.json":
                phase1516_body = phase1516_json.dumps(get_audit_ledger_payload(), indent=2, sort_keys=True)
                phase1516_type = "application/json; charset=utf-8"
            else:
                phase1516_case_id = [part for part in phase1516_path.split("/") if part][1]
                try:
                    phase1516_body = phase1516_json.dumps(get_case_audit_ledger_payload(phase1516_case_id), indent=2, sort_keys=True)
                except KeyError:
                    super().do_GET()
                    return
                phase1516_type = "application/json; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", phase1516_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase1516_body.encode("utf-8"))
            return

        # Phase 13/14 route wiring - demo evidence and validation packets
        phase1314_path = self.path.split("?", 1)[0]
        if phase1314_path in (
            "/demo-console",
            "/demo-console.json",
            "/judge-evidence",
            "/judge-evidence.json",
            "/final-validation",
            "/final-validation.json",
            "/validation-packet",
            "/validation-packet.json",
        ):
            import json as phase1314_json
            from demo_console_v2 import get_demo_console_payload, render_demo_console_html
            from final_validation_packet_v2 import (
                get_final_validation_packet_payload,
                render_final_validation_packet_html,
            )

            if phase1314_path in ("/demo-console", "/judge-evidence"):
                phase1314_body = render_demo_console_html()
                phase1314_type = "text/html; charset=utf-8"
            elif phase1314_path in ("/demo-console.json", "/judge-evidence.json"):
                phase1314_body = phase1314_json.dumps(get_demo_console_payload(), indent=2, sort_keys=True)
                phase1314_type = "application/json; charset=utf-8"
            elif phase1314_path in ("/final-validation", "/validation-packet"):
                phase1314_body = render_final_validation_packet_html()
                phase1314_type = "text/html; charset=utf-8"
            else:
                phase1314_body = phase1314_json.dumps(get_final_validation_packet_payload(), indent=2, sort_keys=True)
                phase1314_type = "application/json; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", phase1314_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase1314_body.encode("utf-8"))
            return

        # Phase 12 route wiring - Fireworks advisory explanation layer
        phase12_path = self.path.split("?", 1)[0]
        if phase12_path in (
            "/fireworks-advisory",
            "/fireworks-advisory.json",
            "/fireworks-model-card",
            "/fireworks-model-card.json",
        ) or (
            phase12_path.startswith("/cases/") and phase12_path.endswith("/fireworks-advisory.json")
        ):
            import json as phase12_json
            from fireworks_advisory_v2 import (
                get_case_fireworks_advisory_payload,
                get_fireworks_advisory_payload,
                get_fireworks_model_card_payload,
                render_fireworks_advisory_html,
                render_fireworks_model_card_html,
            )

            try:
                if phase12_path == "/fireworks-advisory":
                    phase12_body = render_fireworks_advisory_html()
                    phase12_type = "text/html; charset=utf-8"
                elif phase12_path == "/fireworks-advisory.json":
                    phase12_body = phase12_json.dumps(get_fireworks_advisory_payload(), indent=2, sort_keys=True)
                    phase12_type = "application/json; charset=utf-8"
                elif phase12_path == "/fireworks-model-card":
                    phase12_body = render_fireworks_model_card_html()
                    phase12_type = "text/html; charset=utf-8"
                elif phase12_path == "/fireworks-model-card.json":
                    phase12_body = phase12_json.dumps(get_fireworks_model_card_payload(), indent=2, sort_keys=True)
                    phase12_type = "application/json; charset=utf-8"
                else:
                    phase12_parts = [part for part in phase12_path.split("/") if part]
                    phase12_case_id = phase12_parts[1]
                    phase12_body = phase12_json.dumps(
                        get_case_fireworks_advisory_payload(phase12_case_id),
                        indent=2,
                        sort_keys=True,
                    )
                    phase12_type = "application/json; charset=utf-8"
            except KeyError:
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(phase12_json.dumps({"error": "unknown synthetic advisory case"}).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-Type", phase12_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase12_body.encode("utf-8"))
            return

        # Phase 11 route wiring - GPU synthetic research lab
        phase11_path = self.path.split("?", 1)[0]
        if phase11_path in (
            "/gpu-research-lab",
            "/gpu-research-lab.json",
            "/gpu-research-report",
        ):
            import json as phase11_json
            from gpu_research_lab_v2 import (
                get_gpu_research_lab_payload,
                render_gpu_research_lab_html,
                render_gpu_research_report_html,
            )

            if phase11_path == "/gpu-research-lab":
                phase11_body = render_gpu_research_lab_html()
                phase11_type = "text/html; charset=utf-8"
            elif phase11_path == "/gpu-research-lab.json":
                phase11_body = phase11_json.dumps(get_gpu_research_lab_payload(), indent=2, sort_keys=True)
                phase11_type = "application/json; charset=utf-8"
            else:
                phase11_body = render_gpu_research_report_html()
                phase11_type = "text/html; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", phase11_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase11_body.encode("utf-8"))
            return

        # Phase 8-10 route wiring - review replay integration
        phase810_path = self.path.split("?", 1)[0]
        if phase810_path == "/review-workbench" or phase810_path == "/review-workbench.json" or (
            phase810_path.startswith("/review-workbench/") and phase810_path.endswith(".json")
        ):
            import json as phase810_json
            from human_review_workbench_v2 import (
                get_review_packet_payload,
                get_review_workbench_payload,
                render_review_packet_html,
                render_review_workbench_html,
            )
            try:
                if phase810_path == "/review-workbench":
                    phase810_body = render_review_workbench_html()
                    phase810_type = "text/html; charset=utf-8"
                elif phase810_path == "/review-workbench.json":
                    phase810_body = phase810_json.dumps(get_review_workbench_payload(), indent=2, sort_keys=True)
                    phase810_type = "application/json; charset=utf-8"
                else:
                    phase810_scenario_id = phase810_path.rsplit("/", 1)[-1][:-5]
                    phase810_body = phase810_json.dumps(get_review_packet_payload(phase810_scenario_id), indent=2, sort_keys=True)
                    phase810_type = "application/json; charset=utf-8"
            except KeyError:
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(phase810_json.dumps({"error": "unknown synthetic review packet"}).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", phase810_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase810_body.encode("utf-8"))
            return

        if phase810_path == "/incident-replay" or phase810_path == "/incident-replay.json" or (
            phase810_path.startswith("/incident-replay/") and phase810_path.endswith(".json")
        ):
            import json as phase810_json
            from incident_replay_v2 import (
                get_incident_replay_catalog_payload,
                get_incident_replay_payload,
                render_incident_replay_catalog_html,
                render_incident_replay_html,
            )
            try:
                if phase810_path == "/incident-replay":
                    phase810_body = render_incident_replay_catalog_html()
                    phase810_type = "text/html; charset=utf-8"
                elif phase810_path == "/incident-replay.json":
                    phase810_body = phase810_json.dumps(get_incident_replay_catalog_payload(), indent=2, sort_keys=True)
                    phase810_type = "application/json; charset=utf-8"
                else:
                    phase810_scenario_id = phase810_path.rsplit("/", 1)[-1][:-5]
                    phase810_body = phase810_json.dumps(get_incident_replay_payload(phase810_scenario_id), indent=2, sort_keys=True)
                    phase810_type = "application/json; charset=utf-8"
            except KeyError:
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(phase810_json.dumps({"error": "unknown synthetic replay"}).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", phase810_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase810_body.encode("utf-8"))
            return

        if phase810_path in (
            "/integration-readiness",
            "/integration-readiness.json",
            "/integration-contract",
            "/integration-contract.json",
            "/integration-safety",
            "/integration-safety.json",
        ):
            import json as phase810_json
            from integration_readiness_v2 import (
                get_integration_contract_payload,
                get_integration_readiness_payload,
                get_integration_safety_payload,
                render_integration_contract_html,
                render_integration_readiness_html,
                render_integration_safety_html,
            )
            if phase810_path == "/integration-readiness":
                phase810_body = render_integration_readiness_html()
                phase810_type = "text/html; charset=utf-8"
            elif phase810_path == "/integration-readiness.json":
                phase810_body = phase810_json.dumps(get_integration_readiness_payload(), indent=2, sort_keys=True)
                phase810_type = "application/json; charset=utf-8"
            elif phase810_path == "/integration-contract":
                phase810_body = render_integration_contract_html()
                phase810_type = "text/html; charset=utf-8"
            elif phase810_path == "/integration-contract.json":
                phase810_body = phase810_json.dumps(get_integration_contract_payload(), indent=2, sort_keys=True)
                phase810_type = "application/json; charset=utf-8"
            elif phase810_path == "/integration-safety":
                phase810_body = render_integration_safety_html()
                phase810_type = "text/html; charset=utf-8"
            else:
                phase810_body = phase810_json.dumps(get_integration_safety_payload(), indent=2, sort_keys=True)
                phase810_type = "application/json; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", phase810_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase810_body.encode("utf-8"))
            return

        # Phase 7 route wiring - synthetic scenario simulator
        phase7_path = self.path.split("?", 1)[0]
        if phase7_path == "/scenario-lab" or phase7_path == "/scenario-lab.json" or (
            phase7_path.startswith("/scenario-lab/") and phase7_path.endswith(".json")
        ):
            import json as phase7_json
            from scenario_lab_v2 import (
                get_scenario_lab_payload,
                get_scenario_payload,
                render_scenario_html,
                render_scenario_lab_html,
            )
        
            try:
                if phase7_path == "/scenario-lab":
                    phase7_body = render_scenario_lab_html()
                    phase7_content_type = "text/html; charset=utf-8"
                elif phase7_path == "/scenario-lab.json":
                    phase7_body = phase7_json.dumps(get_scenario_lab_payload(), indent=2, sort_keys=True)
                    phase7_content_type = "application/json; charset=utf-8"
                else:
                    phase7_scenario_id = phase7_path.rsplit("/", 1)[-1][:-5]
                    phase7_body = phase7_json.dumps(get_scenario_payload(phase7_scenario_id), indent=2, sort_keys=True)
                    phase7_content_type = "application/json; charset=utf-8"
            except KeyError:
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(phase7_json.dumps({"error": "unknown synthetic scenario"}).encode("utf-8"))
                return
        
            self.send_response(200)
            self.send_header("Content-Type", phase7_content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase7_body.encode("utf-8"))
            return

        # Phase 6 route wiring - synthetic training lab endpoints
        phase6_path = self.path.split("?", 1)[0]
        if phase6_path in (
            "/training-lab",
            "/training-lab.json",
            "/model-benchmark-v2",
            "/model-benchmark-v2.json",
            "/model-card",
            "/model-card.json",
        ):
            import json as phase6_json
            from training_lab_v2 import (
                get_model_benchmark_v2_payload,
                get_model_card_payload,
                get_training_lab_payload,
                render_model_benchmark_v2_html,
                render_model_card_html,
                render_training_lab_html,
            )
        
            if phase6_path == "/training-lab":
                phase6_body = render_training_lab_html()
                phase6_content_type = "text/html; charset=utf-8"
            elif phase6_path == "/training-lab.json":
                phase6_body = phase6_json.dumps(get_training_lab_payload(), indent=2, sort_keys=True)
                phase6_content_type = "application/json; charset=utf-8"
            elif phase6_path == "/model-benchmark-v2":
                phase6_body = render_model_benchmark_v2_html()
                phase6_content_type = "text/html; charset=utf-8"
            elif phase6_path == "/model-benchmark-v2.json":
                phase6_body = phase6_json.dumps(get_model_benchmark_v2_payload(), indent=2, sort_keys=True)
                phase6_content_type = "application/json; charset=utf-8"
            elif phase6_path == "/model-card":
                phase6_body = render_model_card_html()
                phase6_content_type = "text/html; charset=utf-8"
            else:
                phase6_body = phase6_json.dumps(get_model_card_payload(), indent=2, sort_keys=True)
                phase6_content_type = "application/json; charset=utf-8"
        
            self.send_response(200)
            self.send_header("Content-Type", phase6_content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(phase6_body.encode("utf-8"))
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/raw-schema":
            self.respond_text(render_raw_schema_page())
            return
        if path == "/raw-schema.json":
            self.respond_json(raw_schema_json())
            return
        if path == "/data-contract":
            self.respond_text(render_data_contract_v2_page())
            return
        if path == "/data-contract.json":
            self.respond_json(data_contract_v2_json())
            return
        if path == "/data-quality":
            self.respond_text(render_data_quality_page())
            return
        if path == "/data-quality.json":
            self.respond_json(data_quality_json())
            return
        if path == "/consensus":
            self.respond_text(render_consensus_page())
            return
        if path == "/consensus.json":
            self.respond_json(consensus_json())
            return
        if path == "/sers":
            self.respond_text(render_sers_page())
            return
        if path == "/sers.json":
            self.respond_json(sers_json())
            return
        if path.startswith("/cases/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 3 and parts[2] in ("risk-timeline.json", "sers-model-card.json"):
                selected = parts[1]
                try:
                    if parts[2] == "risk-timeline.json":
                        self.respond_json(risk_timeline_json(selected))
                    else:
                        self.respond_json(sers_model_card_json(selected))
                except KeyError:
                    self.respond_text(f"Case not found: {html.escape(selected)}", 404)
                return
        if path.startswith("/cases/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 3 and parts[2] == "consensus-report.json":
                selected = parts[1]
                try:
                    self.respond_json(consensus_report_json(selected))
                except KeyError:
                    self.respond_text(f"Case not found: {html.escape(selected)}", 404)
                return
        if path.startswith("/cases/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 3 and parts[2] in ("quality-events.json", "rejected-readings.json"):
                selected = parts[1]
                offset, limit = parse_window_query(parsed.query)
                try:
                    if parts[2] == "quality-events.json":
                        self.respond_json(quality_events_json(selected))
                    else:
                        self.respond_json(rejected_readings_json(selected, offset, limit))
                except KeyError:
                    self.respond_text(f"Case not found: {html.escape(selected)}", 404)
                return
        if path.startswith("/cases/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 3 and parts[2] in ("raw-sensor-window.json", "normalized-sensor-window.json"):
                selected = parts[1]
                offset, limit = parse_window_query(parsed.query)
                try:
                    if parts[2] == "raw-sensor-window.json":
                        self.respond_json(raw_sensor_window_json(selected, offset, limit))
                    else:
                        self.respond_json(normalized_sensor_window_json(selected, offset, limit))
                except KeyError:
                    self.respond_text(f"Case not found: {html.escape(selected)}", 404)
                return

        if path == "/amd-acceleration":
            self.respond_text(render_amd_acceleration())
            return
        if path == "/amd-acceleration.json":
            self.respond_json(amd_acceleration_json())
            return
        if path == "/gpu-benchmark-plan":
            self.respond_text(render_gpu_benchmark_plan())
            return
        if path == "/gpu-benchmark-plan.json":
            self.respond_json(gpu_benchmark_plan_json())
            return
        if path == "/command-center":
            self.respond_text(render_command_center_with_amd())
            return
        if path == "/command-center.json":
            self.respond_json(command_center_with_amd_json())
            return
        if path == "/system-status.json":
            self.respond_json(system_status_with_amd_json())
            return
        if path == "/validation-evidence.json":
            self.respond_json(validation_evidence_with_amd_json())
            return

        super().do_GET()


def self_check() -> None:
    amd = amd_acceleration_json()
    assert amd["amdGpuVerified"] is True, "expected committed AMD GPU evidence artifact"
    assert amd["specificGpuModelClaimed"] is False
    assert amd["sersGpuTrainingBenchmarkStatus"] in ("pending", "complete")
    if amd["amdBenchmarkAvailable"]:
        assert amd["speedupRatio"] is not None
        assert amd["cpuTrainSeconds"] is not None
        assert amd["gpuTrainSeconds"] is not None
        assert "SERS GPU training completed" not in amd["notClaimed"]
        assert "CPU/GPU speedup proven" not in amd["notClaimed"]
    from gpu_research_lab_v2 import get_gpu_research_lab_payload, render_gpu_research_lab_html
    gpu_lab = get_gpu_research_lab_payload()
    assert gpu_lab["phase"] == "Phase 11 - GPU Synthetic Research Lab"
    assert gpu_lab["syntheticOnly"] is True
    assert gpu_lab["advisoryOnly"] is True
    assert gpu_lab["runtimeGpuRequired"] is False
    assert gpu_lab["runtimeExternalServiceRequired"] is False
    assert gpu_lab["safetyBoundaries"]["autonomousActionsAllowed"] is False
    assert "No runtime GPU dependency" in render_gpu_research_lab_html()
    from fireworks_advisory_v2 import (
        get_case_fireworks_advisory_payload,
        get_fireworks_advisory_payload,
        get_fireworks_model_card_payload,
        render_fireworks_advisory_html,
    )
    fireworks_catalog = get_fireworks_advisory_payload()
    fireworks_case = get_case_fireworks_advisory_payload("no-excursion-control")
    fireworks_card = get_fireworks_model_card_payload()
    assert fireworks_catalog["phase"] == "Phase 12 - Fireworks Advisory Explanation Layer"
    assert fireworks_catalog["syntheticOnly"] is True
    assert fireworks_catalog["advisoryOnly"] is True
    assert fireworks_catalog["runtimeExternalServiceRequired"] is False
    assert fireworks_case["provider"]["displayedAdvisorySource"] in ("deterministic_fallback", "fireworks_safety_gated_json")
    assert fireworks_case["context"]["autonomousActionsAllowed"] is False
    assert fireworks_card["runtimeExternalServiceRequired"] is False
    assert "Fallback always available" in render_fireworks_advisory_html()
    from demo_console_v2 import get_demo_console_payload, render_demo_console_html
    demo_console = get_demo_console_payload()
    demo_html = render_demo_console_html()
    assert demo_console["phase"] == "Phase 13 - Judge Demo Evidence Console"
    assert demo_console["syntheticOnly"] is True
    assert demo_console["advisoryOnly"] is True
    assert demo_console["runtimeGpuRequired"] is False
    assert demo_console["runtimeExternalServiceRequired"] is False
    assert demo_console["deterministicRulesAuthoritative"] is True
    assert "Synthetic-only" in demo_html
    assert "Advisory-only" in demo_html
    assert "Runtime GPU required: false" in demo_html
    assert "Runtime external service required: false" in demo_html
    from final_validation_packet_v2 import get_final_validation_packet_payload, render_final_validation_packet_html
    validation_packet = get_final_validation_packet_payload()
    validation_html = render_final_validation_packet_html()
    assert validation_packet["phase"] == "Phase 14 - Final Validation Evidence Packet"
    assert validation_packet["syntheticOnly"] is True
    assert validation_packet["advisoryOnly"] is True
    assert validation_packet["runtimeGpuRequired"] is False
    assert validation_packet["runtimeExternalServiceRequired"] is False
    assert validation_packet["deterministicRulesAuthoritative"] is True
    assert validation_packet["productionValidated"] is False
    assert validation_packet["pharmaValidated"] is False
    assert validation_packet["realWorldValidated"] is False
    assert validation_packet["complianceCertified"] is False
    assert validation_packet["autonomousActionsAllowed"] is False
    assert "Demo-ready evidence packet, not production validation" in validation_html
    assert "Synthetic-only" in validation_html
    assert "Runtime GPU required: false" in validation_html
    assert "Runtime external service required: false" in validation_html
    from integration_sandbox_v2 import get_integration_sandbox_payload, render_integration_sandbox_html
    integration_sandbox = get_integration_sandbox_payload()
    integration_html = render_integration_sandbox_html()
    assert integration_sandbox["phase"] == "Phase 15 - Integration Sandbox"
    assert integration_sandbox["syntheticOnly"] is True
    assert integration_sandbox["advisoryOnly"] is True
    assert integration_sandbox["runtimeGpuRequired"] is False
    assert integration_sandbox["runtimeExternalServiceRequired"] is False
    assert integration_sandbox["deterministicRulesAuthoritative"] is True
    assert integration_sandbox["externalCallsMade"] is False
    assert integration_sandbox["webhooksEnabled"] is False
    assert "No external calls" in integration_html
    from audit_ledger_v2 import get_audit_ledger_payload, render_audit_ledger_html
    audit_ledger = get_audit_ledger_payload()
    audit_html = render_audit_ledger_html()
    assert audit_ledger["phase"] == "Phase 16 - Evidence Audit Ledger"
    assert audit_ledger["syntheticOnly"] is True
    assert audit_ledger["advisoryOnly"] is True
    assert audit_ledger["runtimeGpuRequired"] is False
    assert audit_ledger["runtimeExternalServiceRequired"] is False
    assert audit_ledger["deterministicRulesAuthoritative"] is True
    assert audit_ledger["autonomousActionsAllowed"] is False
    assert len(audit_ledger["ledgerSteps"]) == 8
    assert "audit-style synthetic evidence trail, not compliance certification" in audit_html.lower()
    from reviewer_workspace_v3 import get_reviewer_workspace_payload, render_reviewer_workspace_html
    reviewer_workspace = get_reviewer_workspace_payload()
    reviewer_html = render_reviewer_workspace_html()
    assert reviewer_workspace["phase"] == "Phase 17 - Reviewer Workspace v3"
    assert reviewer_workspace["syntheticOnly"] is True
    assert reviewer_workspace["advisoryOnly"] is True
    assert reviewer_workspace["runtimeGpuRequired"] is False
    assert reviewer_workspace["runtimeExternalServiceRequired"] is False
    assert reviewer_workspace["deterministicRulesAuthoritative"] is True
    assert reviewer_workspace["autonomousActionsAllowed"] is False
    assert reviewer_workspace["databaseRequired"] is False
    assert "Static synthetic reviewer workflow, no operational action." in reviewer_html
    from fireworks_coverage_v2 import get_fireworks_coverage_payload, render_fireworks_coverage_html
    fireworks_coverage = get_fireworks_coverage_payload()
    coverage_html = render_fireworks_coverage_html()
    assert fireworks_coverage["phase"] == "Phase 18 - Fireworks Multi-Case Advisory Coverage"
    assert fireworks_coverage["syntheticOnly"] is True
    assert fireworks_coverage["advisoryOnly"] is True
    assert fireworks_coverage["runtimeGpuRequired"] is False
    assert fireworks_coverage["runtimeExternalServiceRequired"] is False
    assert fireworks_coverage["deterministicRulesAuthoritative"] is True
    assert fireworks_coverage["autonomousActionsAllowed"] is False
    assert fireworks_coverage["fireworksOptional"] is True
    assert fireworks_coverage["bulkExternalCallsMade"] is False
    assert "No bulk external calls" in coverage_html
    from ops_readiness_v2 import get_ops_readiness_payload, render_ops_readiness_html
    ops_readiness = get_ops_readiness_payload()
    ops_html = render_ops_readiness_html()
    assert ops_readiness["phase"] == "Phase 19 - Ops Readiness and Evidence Health"
    assert ops_readiness["syntheticOnly"] is True
    assert ops_readiness["advisoryOnly"] is True
    assert ops_readiness["runtimeGpuRequired"] is False
    assert ops_readiness["runtimeExternalServiceRequired"] is False
    assert ops_readiness["productionMonitoringClaimed"] is False
    assert ops_readiness["deterministicRulesAuthoritative"] is True
    assert ops_readiness["readinessSummary"]["productionOpsReady"] is False
    assert ops_readiness["readinessSummary"]["externalDependenciesRequiredForBoot"] is False
    assert ops_readiness["readinessSummary"]["humanReviewRequiredForOperationalUse"] is True
    assert "Evidence health only, not production monitoring." in ops_html
    from production_gap_analysis_v2 import get_production_gap_analysis_payload, render_production_gap_analysis_html
    gap_analysis = get_production_gap_analysis_payload()
    gap_html = render_production_gap_analysis_html()
    assert gap_analysis["phase"] == "Phase 20 - Production Gap Analysis"
    assert gap_analysis["syntheticOnly"] is True
    assert gap_analysis["advisoryOnly"] is True
    assert gap_analysis["productionValidated"] is False
    assert gap_analysis["pharmaValidated"] is False
    assert gap_analysis["realWorldValidated"] is False
    assert gap_analysis["complianceCertified"] is False
    assert gap_analysis["autonomousActionsAllowed"] is False
    assert gap_analysis["deterministicRulesAuthoritative"] is True
    assert gap_analysis["readinessBoundary"]["realDeploymentReady"] is False
    assert gap_analysis["readinessBoundary"]["requiresHumanReview"] is True
    assert gap_analysis["readinessBoundary"]["requiresExternalExpertReview"] is True
    assert "Demo evidence exists; real deployment requires additional validation and review." in gap_html
    from expanded_benchmark_v2 import get_expanded_benchmark_payload, render_expanded_benchmark_html
    expanded_benchmark = get_expanded_benchmark_payload()
    expanded_html = render_expanded_benchmark_html()
    assert expanded_benchmark["phase"] == "Phase 21 - Expanded Synthetic Benchmark Refresh"
    assert expanded_benchmark["artifactAvailable"] is True
    assert expanded_benchmark["syntheticOnly"] is True
    assert expanded_benchmark["advisoryOnly"] is True
    assert expanded_benchmark["runtimeGpuRequired"] is False
    assert expanded_benchmark["runtimeExternalServiceRequired"] is False
    assert expanded_benchmark["deterministicRulesAuthoritative"] is True
    assert expanded_benchmark["autonomousActionsAllowed"] is False
    assert len(expanded_benchmark["scenarioCoverage"]) >= 14
    assert expanded_benchmark["trainingBenchmark"]
    assert "GPU/Jupyter was used offline only." in expanded_html
    from scenario_library_v4 import get_scenario_library_payload, render_scenario_library_html
    from evaluation_matrix_v2 import get_evaluation_matrix_payload, render_evaluation_matrix_html
    from evidence_export_pack_v2 import get_evidence_export_payload, render_evidence_export_html
    from policy_sandbox_v2 import get_policy_sandbox_payload, render_policy_sandbox_html
    from llm_advisory_eval_v2 import get_llm_advisory_eval_payload, render_llm_advisory_eval_html
    from route_reliability_v2 import get_route_reliability_payload, render_route_reliability_html
    from decision_simulator_v2 import get_decision_simulator_payload, render_decision_simulator_html
    phase2228 = [
        (get_scenario_library_payload(), "Phase 22 - Expanded Scenario Library v4"),
        (get_evaluation_matrix_payload(), "Phase 23 - Evaluation Matrix v2"),
        (get_evidence_export_payload(), "Phase 24 - Evidence Export Pack"),
        (get_policy_sandbox_payload(), "Phase 25 - SOP Policy Knowledge Sandbox"),
        (get_llm_advisory_eval_payload(), "Phase 26 - LLM Advisory Evaluation Pack"),
        (get_route_reliability_payload(), "Phase 27 - Route Reliability and Demo Resilience"),
        (get_decision_simulator_payload(), "Phase 28 - Human Review Decision Simulator"),
    ]
    for payload, expected_phase in phase2228:
        assert payload["phase"] == expected_phase
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
    assert "synthetic benchmark/demo evidence only" in render_scenario_library_html()
    assert "not external validation" in render_evaluation_matrix_html()
    assert "Synthetic-only advisory evidence" in render_evidence_export_html()
    assert "no real SOP ingestion" in render_policy_sandbox_html()
    assert get_llm_advisory_eval_payload()["bulkExternalCallsMade"] is False
    assert "Fallback always available" in render_llm_advisory_eval_html()
    assert get_route_reliability_payload()["safeModeAvailable"] is True
    assert "no self-HTTP monitoring" in render_route_reliability_html()
    assert get_decision_simulator_payload()["persistenceEnabled"] is False
    assert "no persistence; no operational action" in render_decision_simulator_html()
    from partner_api_contract_v2 import (
        get_openapi_preview_payload, get_partner_api_contract_payload, get_partner_error_catalog_payload,
        render_partner_api_contract_html,
    )
    from demo_flow_v2 import get_demo_flow_payload, render_demo_flow_html, render_demo_step_html
    partner_contract = get_partner_api_contract_payload()
    demo_flow = get_demo_flow_payload()
    for payload, expected_phase in (
        (partner_contract, "Phase 29 - Partner API Contract v2"),
        (demo_flow, "Phase 30 - Final Demo Flow Builder"),
    ):
        assert payload["phase"] == expected_phase
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
    assert partner_contract["externalCallsMade"] is False
    assert partner_contract["webhooksEnabled"] is False
    assert get_openapi_preview_payload()["openapi"] == "3.1.0"
    assert len(get_partner_error_catalog_payload()["errorCatalog"]) == 6
    assert "not a live partner API" in render_partner_api_contract_html()
    assert demo_flow["demoFreezeActive"] is False
    assert demo_flow["stepCount"] == 14
    assert "Demo not frozen" in render_demo_flow_html()
    assert "Jupyter/GPU used offline only" in render_demo_flow_html()
    assert "Presenter script" in render_demo_step_html(1)
    assert "no operational action" in render_demo_step_html(1)
    assert "Step 14" in render_demo_step_html(14)
    from demo_freeze_gate_v2 import get_demo_freeze_gate_payload, get_final_demo_checklist_payload, render_demo_freeze_gate_html
    from demo_navigation_v2 import get_demo_navigation_payload, get_navigation_map_payload, render_demo_navigation_html
    freeze_gate = get_demo_freeze_gate_payload()
    navigation = get_demo_navigation_payload()
    for payload, expected_phase in (
        (freeze_gate, "Phase 31 - Final Demo QA Freeze Gate"),
        (navigation, "Phase 32 - UI Polish Demo Navigation Pass"),
    ):
        assert payload["phase"] == expected_phase
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
    assert get_final_demo_checklist_payload() == freeze_gate
    assert freeze_gate["demoFreezeActive"] is False
    assert freeze_gate["ownerFreezeDecisionRequired"] is True
    assert "Owner freeze decision required" in render_demo_freeze_gate_html()
    assert "not production validation" in render_demo_freeze_gate_html()
    assert get_navigation_map_payload() == navigation
    assert navigation["polishOnly"] is True
    assert navigation["architectureChanged"] is False
    assert navigation["dependenciesAdded"] is False
    assert "Start demo" in render_demo_navigation_html()
    assert "Freeze gate" in render_demo_navigation_html()
    from dashboard_strategy_v2 import get_dashboard_strategy_payload, render_dashboard_strategy_html
    dashboard_strategy = get_dashboard_strategy_payload()
    strategy_html = render_dashboard_strategy_html()
    assert dashboard_strategy["phase"] == "Phase 33 - Screenshot-Worthy Command Center Upgrade"
    assert dashboard_strategy["syntheticOnly"] is True
    assert dashboard_strategy["advisoryOnly"] is True
    assert dashboard_strategy["runtimeGpuRequired"] is False
    assert dashboard_strategy["runtimeExternalServiceRequired"] is False
    assert dashboard_strategy["deterministicRulesAuthoritative"] is True
    assert dashboard_strategy["autonomousActionsAllowed"] is False
    assert dashboard_strategy["dependenciesAdded"] is False
    assert dashboard_strategy["architectureChanged"] is False
    assert dashboard_strategy["syntheticLiveView"]["liveDataClaimed"] is False
    assert dashboard_strategy["syntheticLiveView"]["syntheticActivityOnly"] is True
    assert dashboard_strategy["whyLayer"]["noExternalCallFromDashboard"] is True
    assert dashboard_strategy["sentinelReadinessScore"]
    assert dashboard_strategy["whatNext"]
    assert dashboard_strategy["screenshotWorthyChecklist"]
    for required_text in ("Sentinel Readiness Score", "What Next?", "Synthetic Live View", "Fireworks optional", "Deterministic rules authoritative"):
        assert required_text in strategy_html
    from behavior_predictor_v2 import get_behavior_predictor_payload, render_behavior_predictor_html
    from inspection_engine_v2 import get_inspection_engine_payload, render_inspection_engine_html
    behavior_predictor = get_behavior_predictor_payload()
    inspection_engine = get_inspection_engine_payload()
    behavior_html = render_behavior_predictor_html()
    inspection_html = render_inspection_engine_html()
    assert behavior_predictor["phase"] == "Phase 35B - Sentinel Thermal Behavior Learner App Ingestion"
    assert inspection_engine["phase"] == "Phase 36 - Root Cause and Inspection Recommendation Engine"
    assert behavior_predictor["artifactAvailable"] is True
    assert behavior_predictor["predictorAvailable"] is True
    assert behavior_predictor["trainingRows"] == 171000
    assert behavior_predictor["faultPrototypeCount"] == 38
    assert behavior_predictor["featureWeightCount"] == 19
    assert behavior_predictor["distilledMethod"] == "weighted-centroid-prototypes-plus-rule-boosts"
    for payload in (behavior_predictor, inspection_engine):
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload["realWorldDataUsed"] is False
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["runtimePyTorchRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
    assert behavior_predictor["runtimeBoundary"]["noExternalService"] is True
    assert inspection_engine["stblIntegrated"] is True
    for required_text in ("Sentinel Thermal Behavior Learner", "171,000", "distilled", "Synthetic-only", "Advisory-only"):
        assert required_text in behavior_html
    assert "What is wrong" in inspection_html
    assert "What should a human inspect" in inspection_html
    assert "Synthetic-only" in inspection_html
    assert "Advisory-only" in inspection_html
    from algorithm_console_v2 import get_algorithm_console_payload, render_algorithm_console_html
    from command_center_algorithm_v2 import get_command_center_algorithm_payload, render_command_center_algorithm_html
    algorithm_console = get_algorithm_console_payload()
    command_algorithm = get_command_center_algorithm_payload()
    algorithm_html = render_algorithm_console_html()
    command_algorithm_html = render_command_center_algorithm_html()
    assert algorithm_console["phase"] == "Phase 37 - Algorithm Evidence Console"
    assert command_algorithm["phase"] == "Phase 38 - Command Center Algorithm Integration"
    assert algorithm_console["trainingRows"] == 171000
    assert algorithm_console["faultPrototypeCount"] == 38
    assert algorithm_console["supportedFaultCount"] == 38
    assert algorithm_console["featureWeightCount"] == 19
    assert command_algorithm["headlineMetrics"]["trainingRows"] == 171000
    assert command_algorithm["headlineMetrics"]["supportedFaultCount"] == 38
    assert command_algorithm["headlineMetrics"]["featureWeightCount"] == 19
    for payload in (algorithm_console, command_algorithm):
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload["realWorldDataUsed"] is False
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["runtimePyTorchRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
    assert command_algorithm["dependenciesAdded"] is False
    assert command_algorithm["architectureChanged"] is False
    for required_text in ("Algorithm Evidence Console", "171,000", "feature weights", "Fault coverage", "Runtime safety boundary"):
        assert required_text in algorithm_html
    for required_text in ("What is wrong", "What should we inspect", "STBL", "Algorithm Console", "Behavior Predictor", "Inspection Engine"):
        assert required_text in command_algorithm_html
    command_center_html = render_command_center_with_amd()
    command_center = command_center_with_amd_json()
    for required_text in ("ColdChain Sentinel", "Start Demo", "Algorithm Evidence", "Judge Pack", "Submission", "What to inspect next", "Synthetic-only", "Advisory-only", "Algorithm Console", "Behavior Predictor", "Inspection Engine"):
        assert required_text in command_center_html
    assert len(command_center_html.encode("utf-8")) < 120_000
    assert command_center_html.count("<a ") < 30
    assert command_center["simplifiedDashboard"] is True
    assert command_center["performanceOptimized"] is True
    assert command_center["uiVersion"] == "coherent-fast-v1"
    for key, expected in (("syntheticOnly", True), ("advisoryOnly", True), ("runtimeGpuRequired", False), ("runtimeExternalServiceRequired", False), ("autonomousActionsAllowed", False), ("deterministicRulesAuthoritative", True)):
        assert command_center[key] is expected
    root_html = render_root_with_design_system()
    assert 'data-ui-version="coherent-fast-v1"' in root_html
    assert "/command-center" in root_html
    from case_walkthroughs_v2 import get_case_walkthroughs_payload, render_case_walkthroughs_html
    from fault_atlas_v2 import get_fault_atlas_payload, render_fault_atlas_html
    from judge_evidence_pack_v2 import get_judge_evidence_pack_payload, render_judge_evidence_pack_html
    from large_scale_data_lab_v2 import get_large_scale_data_lab_payload, render_large_scale_data_lab_html
    phase_payloads = (
        get_judge_evidence_pack_payload(), get_large_scale_data_lab_payload(),
        get_fault_atlas_payload(), get_case_walkthroughs_payload(),
    )
    assert [item["phase"] for item in phase_payloads] == [
        "Phase 39 - Final Judge Evidence Pack",
        "Phase 40 - Large-Scale Synthetic Data Demonstration",
        "Phase 41 - Fault Universe Error Atlas",
        "Phase 42 - End-to-End Case Walkthroughs",
    ]
    for payload in phase_payloads:
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload["realWorldDataUsed"] is False
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["runtimePyTorchRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
        assert payload["externalCallsRequired"] is False
        assert payload["dependenciesAdded"] is False
    assert phase_payloads[0]["headlineMetrics"]["trainingRows"] == 171000
    assert phase_payloads[1]["rawLargeDatasetsCommitted"] is False
    assert phase_payloads[2]["faultCount"] == 38
    assert phase_payloads[3]["supportedWalkthroughCount"] == 6
    phase_html = (
        render_judge_evidence_pack_html(), render_large_scale_data_lab_html(),
        render_fault_atlas_html(), render_case_walkthroughs_html(),
    )
    for rendered, title in zip(phase_html, (
        "Final Judge Evidence Pack", "Large-Scale Synthetic Data",
        "Fault Universe", "End-to-End Case Walkthroughs",
    )):
        assert title in rendered
        assert "Synthetic-only" in rendered
        assert "Advisory-only" in rendered
    for label in ("Start Demo", "Judge Pack", "Fault Atlas", "Large Scale Data Lab"):
        assert label in command_center_html
    from demo_script_qna_v2 import get_demo_script_final_payload, get_judge_qna_payload, render_demo_script_qna_html
    from final_freeze_v2 import get_final_freeze_payload, render_final_freeze_html
    from final_route_manifest_v2 import get_final_route_manifest_payload, render_final_route_manifest_html
    from final_visual_polish_v2 import get_visual_polish_payload, render_visual_polish_html
    from submission_readiness_v2 import get_submission_readiness_payload, render_submission_readiness_html
    final_payloads = (
        get_final_route_manifest_payload(), get_submission_readiness_payload(),
        get_demo_script_final_payload(), get_visual_polish_payload(), get_final_freeze_payload(),
    )
    assert [item["phase"] for item in final_payloads] == [
        "Phase 43 - Final Route Manifest and Live QA Sweep",
        "Phase 44 - Submission Readiness Pack",
        "Phase 45 - Demo Script and Judge Q&A",
        "Phase 46 - Visual Polish and Screenshot Pass",
        "Phase 47 - Final Freeze",
    ]
    for payload in final_payloads:
        assert payload["syntheticOnly"] is True
        assert payload["advisoryOnly"] is True
        assert payload.get("realWorldDataUsed", False) is False
        assert payload["runtimeGpuRequired"] is False
        assert payload["runtimeExternalServiceRequired"] is False
        assert payload["runtimePyTorchRequired"] is False
        assert payload["deterministicRulesAuthoritative"] is True
        assert payload["autonomousActionsAllowed"] is False
        assert payload["externalCallsRequired"] is False
        assert payload["dependenciesAdded"] is False
    assert len(final_payloads[0]["requiredRoutes"]) >= 35
    assert final_payloads[1]["ownerSubmissionRequired"] is True
    assert len(get_judge_qna_payload()["questions"]) >= 18
    assert final_payloads[3]["polishOnly"] is True
    assert final_payloads[3]["architectureChanged"] is False
    assert final_payloads[4]["ownerFreezeDecisionRequired"] is True
    assert final_payloads[4]["demoFreezeActive"] is False
    assert final_payloads[4]["automaticFreezeEnabled"] is False
    final_html = (
        render_final_route_manifest_html(), render_submission_readiness_html(),
        render_demo_script_qna_html(), render_visual_polish_html(), render_final_freeze_html(),
    )
    for rendered, title in zip(final_html, (
        "Final Route Manifest", "Submission Readiness Pack", "Demo Script and Judge Q&amp;A",
        "Visual Polish and Screenshot Pass", "Final Freeze",
    )):
        assert title in rendered
        assert "Synthetic-only" in rendered
        assert "Advisory-only" in rendered
    for label in ("Final Route Manifest", "Submission", "Final Freeze"):
        assert label in command_center_html
    schema = raw_schema_json()
    assert schema["schemaVersion"] == "raw-sensor-reading-v2"
    assert "timestampUtc" in schema["acceptedFields"]
    assert "ingestionDelaySeconds" in schema["acceptedFields"]
    raw_window = raw_sensor_window_json("blocked-unresolved-pallet", 0, 10)
    normalized_window = normalized_sensor_window_json("blocked-unresolved-pallet", 0, 10)
    assert raw_window["returnedReadings"] == 10
    assert normalized_window["returnedReadings"] == 10
    assert normalized_window["schemaVersion"] == "normalized-sensor-reading-v2"
    assert "whatGetsNormalized" in data_contract_v2_json()
    assert "AMD GPU Acceleration Evidence" in render_amd_acceleration()
    assert "No real-world validation" in render_amd_acceleration()
    assert "Synthetic SERS GPU benchmark" in render_amd_acceleration()
    assert "Data Contract v2" in render_data_contract_v2_page()
    dq = data_quality_json()
    assert dq["pipelineAcronym"] == "SDTP"
    assert len(dq["stages"]) == 13
    qreport = quality_report_json("blocked-unresolved-pallet")
    assert qreport["metrics"]["acceptedReadings"] > 0
    assert qreport["metrics"]["rejectedReadings"] >= 1
    assert "cleanEvidencePercentage" in qreport["metrics"]
    qevents = quality_events_json("blocked-unresolved-pallet")
    assert qevents["totalEvents"] > 0
    rejected = rejected_readings_json("blocked-unresolved-pallet", 0, 100)
    assert rejected["totalRejectedReadings"] >= 1
    assert "Sentinel Data Trust Pipeline" in render_data_quality_page()
    consensus = consensus_json()
    assert consensus["engineAcronym"] == "ZCE"
    assert "sensorTrustScore" in consensus["factors"]
    zce_report = consensus_report_json("blocked-unresolved-pallet")
    assert zce_report["engineAcronym"] == "ZCE"
    assert zce_report["summary"]["zoneCount"] >= 1
    assert zce_report["summary"]["sensorCount"] >= 1
    assert zce_report["zoneConsensus"][0]["zoneConsensusScore"] >= 0
    assert zce_report["sensorTrust"][0]["sensorTrustScore"] >= 0
    assert "Zone Consensus Engine" in render_consensus_page()
    sers_payload = sers_json()
    assert sers_payload["modelVersion"] == "sers-v2"
    assert sers_payload["status"] == "ADVISORY_ONLY"
    assert "CRITICAL" in sers_payload["riskBands"]
    sers_timeline = risk_timeline_json("blocked-unresolved-pallet")
    assert sers_timeline["currentRisk"]["riskBand"] in ("LOW", "WATCH", "REVIEW", "CRITICAL")
    assert len(sers_timeline["riskTimeline"]) > 0
    sers_card = sers_model_card_json("blocked-unresolved-pallet")
    assert sers_card["advisoryOnly"] is True
    assert sers_card["autonomousActionsAllowed"] is False
    assert "automatic release" in sers_card["notIntendedUse"]
    control_sers = sers_case_json("no-excursion-control")
    control_mapping = next(
        item for item in control_sers["factorsThatMatterMost"]
        if item["featureId"] == "unresolvedMappingRisk"
    )
    assert control_mapping["contributionPoints"] == 0
    assert control_sers["currentRisk"]["riskBand"] in ("LOW", "WATCH")
    assert "SERS v2 Advisory Risk Model" in render_sers_page()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ColdChain Sentinel dashboard with AMD evidence routes.")
    parser.add_argument("--check", action="store_true", help="Render AMD evidence routes and run assertions.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    if args.check:
        self_check()
        print("AMD evidence dashboard self-check passed")
        return

    server = ThreadingHTTPServer((args.host, args.port), AmdDashboardHandler)
    print(f"ColdChain Sentinel dashboard with AMD evidence: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
