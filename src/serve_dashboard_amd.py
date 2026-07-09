"""AMD evidence route wrapper for ColdChain Sentinel.

This module extends the existing stdlib dashboard without changing deterministic
review logic. It only surfaces sanitized AMD GPU notebook evidence when the
committed artifact is present.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
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


def amd_acceleration_json() -> dict[str, Any]:
    evidence = _safe_json_artifact(AMD_ENVIRONMENT_ARTIFACT)
    benchmark = _safe_json_artifact(AMD_SERS_BENCHMARK_ARTIFACT)

    gpu_verified = bool(evidence and evidence.get("gpuVerified") and evidence.get("torchCudaAvailable"))
    benchmark_available = bool(benchmark and benchmark.get("gpuVerified"))
    device_name = str(evidence.get("deviceName", "")) if evidence else ""

    return {
        "amdGpuEvidenceStatus": evidence.get("amdGpuEvidenceStatus", "AMD_GPU_VERIFIED") if gpu_verified else "AMD_GPU_EVIDENCE_PENDING",
        "amdGpuVerified": gpu_verified,
        "amdClaimsAllowed": gpu_verified,
        "amdClaimsScope": "environment verification only" if gpu_verified else "none",
        "amdBenchmarkAvailable": benchmark_available,
        "sersGpuTrainingBenchmarkStatus": "complete" if benchmark_available else "pending",
        "cpuGpuSpeedupStatus": "pending" if not benchmark_available else "available only if artifact includes CPU/GPU timing",
        "specificGpuModelClaimed": False,
        "device": evidence.get("device") if evidence else None,
        "deviceCount": evidence.get("deviceCount") if evidence else None,
        "deviceName": device_name,
        "deviceNameCaveat": evidence.get("deviceNameNote", "No GPU model name is claimed.") if evidence else "No GPU model name is claimed until evidence exists.",
        "torchVersion": evidence.get("torchVersion") if evidence else None,
        "torchCudaAvailable": bool(evidence.get("torchCudaAvailable")) if evidence else False,
        "rocmSmiAvailable": bool(evidence.get("rocmSmiAvailable")) if evidence else False,
        "rocminfoAvailable": bool(evidence.get("rocminfoAvailable")) if evidence else False,
        "matrixBenchmark": evidence.get("matrixBenchmark") if evidence else None,
        "allowedClaim": "AMD ROCm/PyTorch GPU execution was verified in the notebook environment." if gpu_verified else "No AMD GPU verification claim is made yet.",
        "notClaimed": [
            "specific AMD GPU model",
            "SERS GPU training completed",
            "CPU/GPU speedup proven",
            "production ML acceleration validated",
            "real-world cold-chain model trained",
            "AMD GPU improved SERS accuracy"
        ],
        "artifactPaths": {
            "environmentEvidence": "artifacts/amd_gpu_environment_evidence.json",
            "sersGpuBenchmark": "artifacts/amd_sers_gpu_benchmark.json"
        },
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "sersAdvisoryOnly": True,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False
    }


def render_amd_acceleration() -> str:
    payload = amd_acceleration_json()
    matrix = payload.get("matrixBenchmark") or {}
    matrix_summary = (
        f'{matrix.get("matrixSize")}x{matrix.get("matrixSize")} matrix, '
        f'{matrix.get("iterations")} iterations, {matrix.get("elapsedSeconds")} seconds'
        if matrix else "No matrix benchmark artifact available."
    )

    body = f"""
  <header data-testid="amd-acceleration-page">
    {global_nav()}
    <h1>AMD GPU Acceleration Evidence</h1>
    <p>Sanitized notebook evidence for AMD ROCm/PyTorch GPU environment verification.</p>
    {badge("AMD environment: " + payload["amdGpuEvidenceStatus"], "good" if payload["amdGpuVerified"] else "warn")}
    {badge("SERS GPU benchmark: " + payload["sersGpuTrainingBenchmarkStatus"], "warn")}
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
      <article class="panel status-block" data-testid="amd-claim-boundary">
        <h2>Claim boundary</h2>
        <p>{html.escape(payload["deviceNameCaveat"])}</p>
        <p>No specific GPU model, SERS GPU training completion, CPU/GPU speedup, production acceleration, or real-world training claim is made.</p>
      </article>
      <article class="panel" data-testid="amd-next-step">
        <h2>Next benchmark step</h2>
        <p>Run the synthetic SERS GPU training notebook and commit only a small sanitized benchmark artifact.</p>
      </article>
    </section>
    <section class="panel">
      <div class="toolbar">
        <a class="button" href="/amd-acceleration.json">AMD JSON</a>
        <a class="button" href="/gpu-benchmark-plan">GPU Benchmark Plan</a>
        <a class="button" href="/model-benchmark">Model Benchmark</a>
        <a class="button" href="/sers-model-card">SERS Model Card</a>
      </div>
    </section>
  </main>
"""
    return page("ColdChain Sentinel AMD GPU Evidence", body)


def gpu_benchmark_plan_json() -> dict[str, Any]:
    return {
        "benchmarkMode": "planned_synthetic_sers_gpu_training",
        "currentStatus": amd_acceleration_json()["sersGpuTrainingBenchmarkStatus"],
        "steps": [
            "Generate deterministic synthetic SERS training windows.",
            "Train a dependency-light PyTorch model using cuda when ROCm is available.",
            "Run CPU fallback timing only if practical in the notebook.",
            "Compare SERS metrics against simple baselines on synthetic data.",
            "Export a small sanitized artifacts/amd_sers_gpu_benchmark.json summary.",
            "Update app evidence without committing raw generated datasets or secrets."
        ],
        "requiredArtifact": "artifacts/amd_sers_gpu_benchmark.json",
        "claimsBoundary": "No SERS GPU training, speedup, production acceleration, real-world validation, or accuracy improvement claim is made until sanitized evidence exists.",
        "syntheticOnly": True,
        "realDataUsed": False,
        "productionValidated": False,
        "sersAdvisoryOnly": True,
        "deterministicRulesAuthoritative": True,
        "autonomousActionsAllowed": False
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
    <p>Planned synthetic SERS GPU training evidence flow. No training or speedup claim is made yet.</p>
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
        "specificGpuModelClaimed": False,
        "claimsScope": amd["amdClaimsScope"]
    }
    payload.setdefault("routeMap", {})["amdAcceleration"] = "/amd-acceleration"
    payload.setdefault("routeMap", {})["gpuBenchmarkPlan"] = "/gpu-benchmark-plan"
    return payload


def render_command_center_with_amd() -> str:
    payload = amd_acceleration_json()
    card = f"""
    <section class="panel" data-testid="amd-acceleration-card">
      <h2>AMD GPU Evidence</h2>
      <p>AMD GPU environment: {html.escape(payload["amdGpuEvidenceStatus"])}.</p>
      <p>SERS GPU benchmark: {html.escape(payload["sersGpuTrainingBenchmarkStatus"])}. CPU/GPU speedup: pending.</p>
      <p>No specific GPU model is claimed. Deterministic rules remain authoritative.</p>
      <div class="toolbar">
        <a class="button" href="/amd-acceleration">AMD Evidence</a>
        <a class="button" href="/gpu-benchmark-plan">GPU Benchmark Plan</a>
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
        "sersGpuTrainingBenchmarkStatus": amd["sersGpuTrainingBenchmarkStatus"]
    })
    return status


class AmdDashboardHandler(BaseDashboardHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

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

        super().do_GET()


def self_check() -> None:
    amd = amd_acceleration_json()
    assert amd["amdGpuVerified"] is True, "expected committed AMD GPU evidence artifact"
    assert amd["specificGpuModelClaimed"] is False
    assert amd["sersGpuTrainingBenchmarkStatus"] in ("pending", "complete")
    assert "AMD GPU Acceleration Evidence" in render_amd_acceleration()
    assert "No specific GPU model" in render_amd_acceleration()
    assert "No training or speedup claim" in render_gpu_benchmark_plan()


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

