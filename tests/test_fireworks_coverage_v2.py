import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fireworks_advisory_v2 import CASE_IDS, DEFAULT_MODEL  # noqa: E402
from fireworks_coverage_v2 import (  # noqa: E402
    get_fireworks_coverage_payload,
    render_fireworks_coverage_html,
)


class FireworksCoverageV2Tests(unittest.TestCase):
    def test_payload_shape_safety_and_all_cases(self):
        with patch.dict(os.environ, {}, clear=True):
            payload = get_fireworks_coverage_payload()

        self.assertEqual(payload["phase"], "Phase 18 - Fireworks Multi-Case Advisory Coverage")
        self.assertEqual(payload["status"], "READY")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["runtimeExternalServiceRequired"])
        self.assertFalse(payload["runtimeGpuRequired"])
        self.assertTrue(payload["deterministicRulesAuthoritative"])
        self.assertFalse(payload["autonomousActionsAllowed"])
        self.assertTrue(payload["fireworksOptional"])
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["knownWorkingModel"], DEFAULT_MODEL)
        self.assertEqual(payload["defaultCoverageMode"], "route-available-no-bulk-external-call")
        self.assertFalse(payload["bulkExternalCallsMade"])
        self.assertEqual([row["caseId"] for row in payload["coverageRows"]], list(CASE_IDS))

        for row in payload["coverageRows"]:
            self.assertEqual(row["advisoryRoute"], f'/cases/{row["caseId"]}/fireworks-advisory.json')
            self.assertTrue(row["deterministicFallbackAvailable"])
            self.assertTrue(row["safetyGateRequired"])
            self.assertTrue(row["deterministicRulesAuthoritative"])
            self.assertEqual(row["expectedSourceWhenNoKey"], "deterministic_fallback")
            self.assertEqual(row["expectedSourceWhenAccepted"], "fireworks_safety_gated_json")

    def test_environment_is_reported_without_external_call(self):
        with patch.dict(
            os.environ,
            {"FIREWORKS_API_KEY": "test-only", "FIREWORKS_MODEL": "test/model"},
            clear=True,
        ), patch("urllib.request.urlopen") as urlopen:
            payload = get_fireworks_coverage_payload()
            rendered = render_fireworks_coverage_html()

        urlopen.assert_not_called()
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["knownWorkingModel"], "test/model")
        self.assertIn("test/model", rendered)

    def test_route_map_and_html_boundaries(self):
        payload = get_fireworks_coverage_payload()
        self.assertEqual(
            set(payload["routeMap"].values()),
            {"/fireworks-advisory", "/fireworks-model-card", "/demo-console", "/reviewer-workspace"},
        )

        rendered = render_fireworks_coverage_html()
        for text in (
            "Synthetic-only",
            "Advisory-only",
            "Fireworks optional",
            "Fallback available",
            "No bulk external calls",
            "Deterministic rules remain authoritative",
        ):
            self.assertIn(text, rendered)
        for case_id in CASE_IDS:
            self.assertIn(f"/cases/{case_id}/fireworks-advisory.json", rendered)

    def test_no_forbidden_positive_claims(self):
        text = (json.dumps(get_fireworks_coverage_payload(), sort_keys=True) + render_fireworks_coverage_html()).lower()
        forbidden = (
            "production" + "-ready",
            "pharma" + " validated",
            "real" + "-world validated",
            "compliance" + " certified",
            "autonomous" + " release",
            "autonomous" + " quarantine",
            "autonomous" + " discard",
            "autonomous" + " reroute",
            "customer" + " notification",
        )
        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, text)


if __name__ == "__main__":
    unittest.main()
