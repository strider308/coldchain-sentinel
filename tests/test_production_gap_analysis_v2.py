import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from production_gap_analysis_v2 import (  # noqa: E402
    GAP_CATEGORIES,
    get_production_gap_analysis_payload,
    render_production_gap_analysis_html,
)


class ProductionGapAnalysisV2Tests(unittest.TestCase):
    def test_payload_shape_and_boundaries(self):
        payload = get_production_gap_analysis_payload()
        self.assertEqual(payload["phase"], "Phase 20 - Production Gap Analysis")
        self.assertEqual(payload["status"], "GAPS_IDENTIFIED")
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in ("productionValidated", "pharmaValidated", "realWorldValidated", "complianceCertified", "autonomousActionsAllowed"):
            self.assertFalse(payload[key])
        self.assertEqual(payload["readinessBoundary"], {
            "demoReady": True,
            "realDeploymentReady": False,
            "requiresHumanReview": True,
            "requiresExternalExpertReview": True,
        })

    def test_exact_categories_fields_and_routes(self):
        payload = get_production_gap_analysis_payload()
        self.assertEqual(tuple(item["category"] for item in payload["gapCategories"]), GAP_CATEGORIES)
        self.assertEqual(len(GAP_CATEGORIES), 11)
        fields = {"category", "currentDemoStatus", "missingBeforeRealUse", "suggestedNextStep", "owner", "priority"}
        self.assertTrue(all(set(item) == fields for item in payload["gapCategories"]))
        self.assertEqual(payload["routeMap"], {
            "finalValidation": "/final-validation",
            "demoConsole": "/demo-console",
            "opsReadiness": "/ops-readiness",
        })

    def test_builder_needs_no_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network call")):
            json.dumps(get_production_gap_analysis_payload(), sort_keys=True)

    def test_html_matrix_priorities_and_boundary_language(self):
        page = render_production_gap_analysis_html()
        self.assertIn("Gap matrix", page)
        self.assertIn("priority high", page)
        self.assertIn("priority medium", page)
        self.assertIn("Demo evidence exists; real deployment requires additional validation and review.", page)
        self.assertIn("<style>", page)

    def test_forbidden_positive_claims_absent(self):
        text = (json.dumps(get_production_gap_analysis_payload()) + render_production_gap_analysis_html()).lower()
        forbidden = [
            "production" + " validated",
            "pharma" + " validated",
            "real-world" + " validated",
            "compliance" + " certified",
            "production" + "-ready",
            "production" + " ready",
            "safe for " + "distribution",
            "approved for " + "release",
            "autonomous " + "release",
            "autonomous " + "quarantine",
            "autonomous " + "discard",
            "autonomous " + "reroute",
            "customer " + "notified",
            "customer " + "notification",
        ]
        for claim in forbidden:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)


if __name__ == "__main__":
    unittest.main()
