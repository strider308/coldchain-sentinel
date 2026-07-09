import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gpu_research_lab_v2 import (  # noqa: E402
    get_gpu_research_lab_payload,
    get_gpu_research_report_payload,
    render_gpu_research_lab_html,
    render_gpu_research_report_html,
)


class GpuResearchLabV2Tests(unittest.TestCase):
    def test_payload_has_required_phase11_keys(self):
        payload = get_gpu_research_lab_payload()

        self.assertEqual(payload["phase"], "Phase 11 - GPU Synthetic Research Lab")
        self.assertEqual(payload["status"], "FOUNDATION_READY")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["runtimeGpuRequired"])
        self.assertFalse(payload["runtimeExternalServiceRequired"])
        self.assertIn("gpuWorkflow", payload)
        self.assertIn("benchmarkSummary", payload)
        self.assertIn("safetyBoundaries", payload)
        self.assertIn("routeLinks", payload)


    def test_artifact_ingestion_when_summary_exists(self):
        payload = get_gpu_research_lab_payload()

        self.assertTrue(payload["artifactAvailable"])
        self.assertEqual(payload["artifactPath"], "artifacts/gpu_synthetic_research_summary.json")
        self.assertIsInstance(payload["artifactSummary"], dict)
        self.assertTrue(payload["artifactSummary"]["syntheticOnly"])
        self.assertTrue(payload["artifactSummary"]["advisoryOnly"])
        self.assertFalse(payload["artifactSummary"]["runtimeGpuRequired"])

    def test_runtime_boundary_is_dependency_free(self):
        payload = get_gpu_research_lab_payload()

        self.assertEqual(payload["gpuWorkflow"]["liveAppDependency"], "none")
        self.assertFalse(payload["gpuWorkflow"]["notebookOutputCommitted"])
        self.assertFalse(payload["gpuWorkflow"]["largeDatasetCommitted"])
        self.assertFalse(payload["safetyBoundaries"]["realCustomerDataUsed"])
        self.assertFalse(payload["safetyBoundaries"]["realShipmentDataUsed"])

    def test_safety_boundaries_block_operational_claims(self):
        payload = get_gpu_research_lab_payload()
        boundaries = payload["safetyBoundaries"]

        self.assertFalse(boundaries["productionUseAllowed"])
        self.assertFalse(boundaries["pharmaValidationClaimed"])
        self.assertFalse(boundaries["realWorldValidationClaimed"])
        self.assertFalse(boundaries["complianceCertificationClaimed"])
        self.assertFalse(boundaries["autonomousActionsAllowed"])
        self.assertTrue(boundaries["deterministicRulesAuthoritative"])

    def test_html_contains_required_boundary_language(self):
        html = render_gpu_research_lab_html()

        self.assertIn("Synthetic-only", html)
        self.assertIn("Advisory-only", html)
        self.assertIn("No runtime GPU dependency", html)
        self.assertIn("/gpu-research-lab.json", html)
        self.assertIn("/gpu-research-report", html)

    def test_report_payload_and_html_are_consistent(self):
        payload = get_gpu_research_report_payload()
        html = render_gpu_research_report_html()

        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["runtimeGpuRequired"])
        self.assertIn("GPU Synthetic Research Report", html)
        self.assertIn("Requirements Before Real Deployment", html)

    def test_no_forbidden_positive_claims_in_phase11_payloads(self):
        text = json.dumps(
            {
                "lab": get_gpu_research_lab_payload(),
                "report": get_gpu_research_report_payload(),
            },
            sort_keys=True,
        ).lower()

        forbidden_terms = [
            ("production" + "-ready"),
            ("pharma" + " validated"),
            ("real" + "-world validated"),
            ("compliance" + " certified"),
            ("autonomous" + " release"),
            ("autonomous" + " quarantine"),
            ("autonomous" + " discard"),
            ("autonomous" + " reroute"),
            ("automatic" + " customer" + " notification"),
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, text)


if __name__ == "__main__":
    unittest.main()



