"""AMD evidence route wrapper for ColdChain Sentinel.

This module extends the existing stdlib dashboard without changing deterministic
review logic. It surfaces sanitized AMD GPU notebook evidence and, when present,
the synthetic SERS GPU benchmark artifact.
"""

from __future__ import annotations

import argparse
import html
import json
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


def command_center_with_amd_json() -> dict[str, Any]:
    payload = command_center_payload()
    amd = amd_acceleration_json()
    payload["amdAccelerationSummary"] = {
        "amdGpuEvidenceStatus": amd["amdGpuEvidenceStatus"],
        "amdGpuVerified": amd["amdGpuVerified"],
        "amdBenchmarkAvailable": amd["amdBenchmarkAvailable"],
        "sersGpuTrainingBenchmarkStatus": amd["sersGpuTrainingBenchmarkStatus"],
        "speedupRatio": amd["speedupRatio"],
        "specificGpuModelClaimed": False,
        "claimsScope": amd["amdClaimsScope"],
    }
    payload.setdefault("routeMap", {})["amdAcceleration"] = "/amd-acceleration"
    payload.setdefault("routeMap", {})["gpuBenchmarkPlan"] = "/gpu-benchmark-plan"
    payload.setdefault("routeMap", {})["gpuResearchLab"] = "/gpu-research-lab"
    payload.setdefault("routeMap", {})["fireworksAdvisory"] = "/fireworks-advisory"
    payload.setdefault("routeMap", {})["demoConsole"] = "/demo-console"
    payload.setdefault("routeMap", {})["judgeEvidence"] = "/judge-evidence"
    payload.setdefault("routeMap", {})["finalValidation"] = "/final-validation"
    payload.setdefault("routeMap", {})["validationPacket"] = "/validation-packet"
    return payload


def render_command_center_with_amd() -> str:
    payload = amd_acceleration_json()
    speedup = f'{_fmt(payload["speedupRatio"])}x' if payload.get("speedupRatio") else "pending"
    card = f"""
    <section class="panel" data-testid="amd-acceleration-card">
      <h2>AMD GPU Evidence</h2>
      <p>AMD GPU environment: {html.escape(payload["amdGpuEvidenceStatus"])}.</p>
      <p>SERS GPU benchmark: {html.escape(payload["sersGpuTrainingBenchmarkStatus"])}. Synthetic CPU/GPU speedup: {html.escape(speedup)}.</p>
      <p>No real-world, production, compliance, specific GPU model, or accuracy-improvement claim is made.</p>
      <div class="toolbar">
        <a class="button" href="/amd-acceleration">AMD Evidence</a>
        <a class="button" href="/gpu-benchmark-plan">GPU Benchmark Plan</a>
        <a class="button" href="/gpu-research-lab">GPU Research Lab</a>
        <a class="button" href="/fireworks-advisory">Fireworks Advisory</a>
        <a class="button" href="/demo-console">Demo Console</a>
        <a class="button" href="/final-validation">Final Validation</a>
      </div>
    </section>
"""
    return render_command_center().replace("</main>", card + "  </main>")


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
