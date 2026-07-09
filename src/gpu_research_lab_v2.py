from __future__ import annotations

from functools import lru_cache
import html
import json
from typing import Any

PHASE = "Phase 11 - GPU Synthetic Research Lab"
STATUS = "FOUNDATION_READY"


@lru_cache(maxsize=1)
def get_gpu_research_lab_payload() -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False,
        "gpuWorkflow": {
            "environment": "Jupyter notebooks with GPU access",
            "purpose": "accelerate synthetic cold-chain benchmark experimentation",
            "liveAppDependency": "none",
            "artifactPolicy": "small sanitized summaries only",
            "notebookOutputCommitted": False,
            "largeDatasetCommitted": False,
        },
        "benchmarkSummary": {
            "datasetScale": {
                "syntheticTrainingWindows": 4200,
                "syntheticValidationWindows": 1200,
                "readingsPerWindow": 12,
                "scenarioFamilies": 7,
            },
            "scenarioFamilies": [
                "no_excursion_control",
                "slow_warming_excursion",
                "door_left_open_warming",
                "early_warning_slope",
                "false_single_sensor_spike",
                "unresolved_mapping_risk",
                "dropout_weak_signal_noise",
            ],
            "comparisonScope": "deterministic synthetic benchmark summaries only",
            "gpuUse": [
                "larger synthetic dataset generation experiments",
                "repeatable advisory model benchmark experiments",
                "CPU/GPU timing comparison in notebook context",
                "export of small sanitized evidence summaries",
            ],
            "baselineComparison": [
                {"name": "current temperature threshold", "role": "simple baseline"},
                {"name": "rolling average threshold", "role": "simple baseline"},
                {"name": "simple slope rule", "role": "simple baseline"},
                {"name": "SERS advisory scorer", "role": "deterministic synthetic reference"},
            ],
        },
        "safetyBoundaries": {
            "realCustomerDataUsed": False,
            "realShipmentDataUsed": False,
            "productionUseAllowed": False,
            "pharmaValidationClaimed": False,
            "realWorldValidationClaimed": False,
            "complianceCertificationClaimed": False,
            "autonomousActionsAllowed": False,
            "deterministicRulesAuthoritative": True,
            "notClaimed": [
                "production operation readiness",
                "pharma validation",
                "real-world validation",
                "compliance certification",
                "release/quarantine/discard/reroute decisions",
                "customer messaging decisions",
                "specific GPU model advantage",
            ],
        },
        "nextExperimentQueue": [
            "export sanitized notebook summary artifact",
            "compare deterministic SERS against larger synthetic baselines",
            "measure CPU/GPU timing on synthetic training loops",
            "document notebook reproducibility steps",
            "keep live app dependency-free",
        ],
        "routeLinks": {
            "html": "/gpu-research-lab",
            "json": "/gpu-research-lab.json",
            "report": "/gpu-research-report",
            "commandCenter": "/command-center",
            "trainingLab": "/training-lab",
            "modelBenchmarkV2": "/model-benchmark-v2",
            "scenarioLab": "/scenario-lab",
            "validationEvidence": "/validation-evidence.json",
        },
    }


def get_gpu_research_report_payload() -> dict[str, Any]:
    lab = get_gpu_research_lab_payload()
    return {
        "title": "GPU Synthetic Research Report",
        "phase": lab["phase"],
        "status": lab["status"],
        "purpose": "Use GPU-backed Jupyter experimentation to strengthen synthetic cold-chain benchmark discipline without adding runtime GPU dependency to the demo app.",
        "scope": {
            "data": "synthetic-only",
            "decisioning": "advisory-only",
            "runtime": "CPU-compatible static app routes",
            "externalServices": "none required",
        },
        "methodology": [
            "Generate deterministic synthetic sensor windows with known scenario families.",
            "Run larger benchmark experiments in GPU-backed notebooks.",
            "Compare advisory scoring behavior against simple baselines.",
            "Export only small sanitized summaries into the app.",
            "Keep deterministic rules authoritative for demo behavior.",
        ],
        "limitations": lab["safetyBoundaries"]["notClaimed"],
        "realWorldReadinessRequirements": [
            "authorized real data access",
            "sensor calibration study",
            "cold-chain domain review",
            "regulated validation plan",
            "security and privacy review",
            "human operating procedure approval",
        ],
        "syntheticOnly": True,
        "advisoryOnly": True,
        "runtimeGpuRequired": False,
    }


def _json_block(payload: dict[str, Any]) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True))


def render_gpu_research_lab_html() -> str:
    payload = get_gpu_research_lab_payload()
    families = "\n".join(
        f"<li>{html.escape(item)}</li>" for item in payload["benchmarkSummary"]["scenarioFamilies"]
    )
    next_steps = "\n".join(
        f"<li>{html.escape(item)}</li>" for item in payload["nextExperimentQueue"]
    )
    not_claimed = "\n".join(
        f"<li>{html.escape(item)}</li>" for item in payload["safetyBoundaries"]["notClaimed"]
    )
    links = "\n".join(
        f'<a class="button" href="{html.escape(url)}">{html.escape(name)}</a>'
        for name, url in payload["routeLinks"].items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ColdChain Sentinel GPU Synthetic Research Lab</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #071014; color: #eef7f2; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
    .panel {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    .badge {{ display: inline-block; margin: 4px 8px 4px 0; padding: 6px 10px; border-radius: 999px; background: #20323a; border: 1px solid #3b5965; }}
    .button {{ display: inline-block; margin: 6px 8px 6px 0; padding: 8px 12px; border-radius: 12px; background: #18323b; color: #96e6b3; text-decoration: none; border: 1px solid #315766; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #071014; border: 1px solid #21414d; border-radius: 14px; padding: 16px; }}
    a {{ color: #96e6b3; }}
  </style>
</head>
<body>
<main data-testid="gpu-research-lab-page">
  <p><a href="/">ColdChain Sentinel</a></p>
  <h1>GPU Synthetic Research Lab</h1>
  <p>GPU/Jupyter research support for synthetic cold-chain benchmark experiments. The live app has no runtime GPU dependency.</p>
  <div>
    <span class="badge">Synthetic-only</span>
    <span class="badge">Advisory-only</span>
    <span class="badge">No runtime GPU dependency</span>
    <span class="badge">Deterministic rules authoritative</span>
  </div>

  <section class="grid">
    <article class="panel">
      <h2>Dataset Scale</h2>
      <p>Training windows: {payload["benchmarkSummary"]["datasetScale"]["syntheticTrainingWindows"]}</p>
      <p>Validation windows: {payload["benchmarkSummary"]["datasetScale"]["syntheticValidationWindows"]}</p>
      <p>Scenario families: {payload["benchmarkSummary"]["datasetScale"]["scenarioFamilies"]}</p>
    </article>
    <article class="panel">
      <h2>GPU Workflow</h2>
      <p>{html.escape(payload["gpuWorkflow"]["purpose"])}</p>
      <p>Live app dependency: {html.escape(payload["gpuWorkflow"]["liveAppDependency"])}</p>
    </article>
    <article class="panel">
      <h2>Runtime Boundary</h2>
      <p>Runtime GPU required: {str(payload["runtimeGpuRequired"]).lower()}</p>
      <p>External service required: {str(payload["runtimeExternalServiceRequired"]).lower()}</p>
    </article>
  </section>

  <section class="panel">
    <h2>Synthetic Scenario Families</h2>
    <ul>{families}</ul>
  </section>

  <section class="panel">
    <h2>Next Experiment Queue</h2>
    <ul>{next_steps}</ul>
  </section>

  <section class="panel">
    <h2>What We Do Not Claim</h2>
    <ul>{not_claimed}</ul>
  </section>

  <section class="panel">
    <h2>Routes</h2>
    <div>{links}</div>
  </section>

  <section class="panel">
    <h2>Machine-Readable Payload</h2>
    <pre>{_json_block(payload)}</pre>
  </section>
</main>
</body>
</html>"""


def render_gpu_research_report_html() -> str:
    payload = get_gpu_research_report_payload()
    methodology = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["methodology"])
    limitations = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["limitations"])
    readiness = "\n".join(
        f"<li>{html.escape(item)}</li>" for item in payload["realWorldReadinessRequirements"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ColdChain Sentinel GPU Synthetic Research Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #071014; color: #eef7f2; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 56px; }}
    section {{ background: #102129; border: 1px solid #21414d; border-radius: 18px; padding: 20px; margin: 18px 0; }}
    a {{ color: #96e6b3; }}
  </style>
</head>
<body>
<main data-testid="gpu-research-report-page">
  <p><a href="/gpu-research-lab">GPU Synthetic Research Lab</a></p>
  <h1>{html.escape(payload["title"])}</h1>
  <p>{html.escape(payload["purpose"])}</p>
  <section>
    <h2>Scope</h2>
    <p>Data: {html.escape(payload["scope"]["data"])}</p>
    <p>Decisioning: {html.escape(payload["scope"]["decisioning"])}</p>
    <p>Runtime: {html.escape(payload["scope"]["runtime"])}</p>
  </section>
  <section>
    <h2>Methodology</h2>
    <ol>{methodology}</ol>
  </section>
  <section>
    <h2>Limitations</h2>
    <ul>{limitations}</ul>
  </section>
  <section>
    <h2>Requirements Before Real Deployment</h2>
    <ul>{readiness}</ul>
  </section>
</main>
</body>
</html>"""
