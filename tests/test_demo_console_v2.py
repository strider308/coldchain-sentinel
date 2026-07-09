import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from demo_console_v2 import get_demo_console_payload, render_demo_console_html  # noqa: E402


class DemoConsoleV2Tests(unittest.TestCase):
    def test_payload_shape_and_safety_flags(self):
        payload = get_demo_console_payload()

        self.assertEqual(payload["phase"], "Phase 13 - Judge Demo Evidence Console")
        self.assertEqual(payload["status"], "READY")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["runtimeGpuRequired"])
        self.assertFalse(payload["runtimeExternalServiceRequired"])
        self.assertTrue(payload["deterministicRulesAuthoritative"])
        self.assertTrue(payload["fireworksOptional"])
        self.assertIn("artifactAvailable", payload)
        self.assertGreaterEqual(len(payload["evidenceSections"]), 12)

    def test_route_map_contains_required_routes(self):
        route_map = get_demo_console_payload()["routeMap"]

        for route in (
            "/command-center",
            "/raw-schema",
            "/data-quality",
            "/consensus",
            "/sers",
            "/training-lab",
            "/scenario-lab",
            "/review-workbench",
            "/incident-replay",
            "/integration-readiness",
            "/gpu-research-lab",
            "/fireworks-advisory",
            "/fireworks-model-card",
            "/demo-console",
            "/judge-evidence",
        ):
            self.assertIn(route, route_map.values())

    def test_html_contains_boundary_badges_and_preview(self):
        rendered = render_demo_console_html()

        self.assertIn("Synthetic-only", rendered)
        self.assertIn("Advisory-only", rendered)
        self.assertIn("Deterministic rules authoritative", rendered)
        self.assertIn("Fireworks optional", rendered)
        self.assertIn("Runtime GPU required: false", rendered)
        self.assertIn("Runtime external service required: false", rendered)
        self.assertIn("Compact JSON evidence preview", rendered)

    def test_missing_fireworks_key_does_not_break_payload(self):
        with patch.dict(os.environ, {}, clear=True):
            payload = get_demo_console_payload()

        self.assertFalse(payload["fireworksStatus"]["fireworksConfigured"])
        self.assertEqual(
            payload["fireworksStatus"]["caseSummary"]["displayedAdvisorySource"],
            "deterministic_fallback",
        )
        self.assertFalse(payload["fireworksStatus"]["caseSummary"]["runtimeExternalServiceRequired"])

    def test_no_forbidden_positive_claims_in_payload(self):
        text = json.dumps(get_demo_console_payload(), sort_keys=True).lower()
        forbidden = [
            "production" + "-ready",
            "pharma" + " validated",
            "real" + "-world validated",
            "compliance" + " certified",
            "autonomous" + " release",
            "autonomous" + " quarantine",
            "autonomous" + " discard",
            "autonomous" + " reroute",
            "customer" + " notification",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, text)


if __name__ == "__main__":
    unittest.main()
