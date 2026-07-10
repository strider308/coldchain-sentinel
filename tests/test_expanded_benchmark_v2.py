import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from expanded_benchmark_v2 import (
    ARTIFACT_PATH,
    get_expanded_benchmark_payload,
    load_expanded_benchmark_artifact,
    render_expanded_benchmark_html,
    validate_expanded_benchmark_artifact,
)


class ExpandedBenchmarkV2Tests(unittest.TestCase):
    def test_artifact_loads_and_validates(self):
        artifact = load_expanded_benchmark_artifact()
        self.assertIsNotNone(artifact)
        self.assertTrue(validate_expanded_benchmark_artifact(artifact))

    def test_payload_shape_and_safety_flags(self):
        payload = get_expanded_benchmark_payload()
        self.assertEqual(payload["phase"], "Phase 21 - Expanded Synthetic Benchmark Refresh")
        self.assertEqual(payload["artifactPath"], ARTIFACT_PATH)
        self.assertTrue(payload["artifactAvailable"])
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in ("runtimeGpuRequired", "runtimeExternalServiceRequired", "autonomousActionsAllowed"):
            self.assertFalse(payload[key])

    def test_benchmark_sections_and_routes(self):
        payload = get_expanded_benchmark_payload()
        self.assertGreaterEqual(len(payload["scenarioCoverage"]), 14)
        self.assertTrue(payload["trainingBenchmark"])
        self.assertTrue(payload["benchmarkComparison"])
        self.assertTrue(payload["dataset"])
        self.assertEqual(payload["routeMap"]["expandedBenchmark"], "/expanded-benchmark")
        self.assertEqual(payload["routeMap"]["benchmarkRefresh"], "/benchmark-refresh")

    def test_html_boundary_language(self):
        page = render_expanded_benchmark_html()
        for text in (
            "Synthetic-only",
            "Advisory-only",
            "Runtime GPU required: false",
            "Runtime external service required: false",
            "Deterministic rules authoritative",
            "GPU/Jupyter was used offline only.",
            "Scenario coverage",
        ):
            self.assertIn(text, page)

    def test_forbidden_positive_claims_absent(self):
        text = (json.dumps(get_expanded_benchmark_payload()) + render_expanded_benchmark_html()).lower()
        forbidden = (
            "production" + "-ready",
            "pharma" + " validated",
            "real-world" + " validated",
            "compliance" + " certified",
            "autonomous" + " release",
            "autonomous" + " quarantine",
            "autonomous" + " discard",
            "autonomous" + " reroute",
            "customer" + " notification",
        )
        for claim in forbidden:
            self.assertNotIn(claim, text)


if __name__ == "__main__":
    unittest.main()
