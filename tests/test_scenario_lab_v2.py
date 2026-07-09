import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scenario_lab_v2 import (  # noqa: E402
    CLAIMS_BOUNDARY,
    SCENARIOS,
    get_scenario_lab_payload,
    get_scenario_payload,
)


class ScenarioLabV2Tests(unittest.TestCase):
    def test_catalog_is_json_serializable_and_lists_expected_routes(self):
        payload = get_scenario_lab_payload()
        json.dumps(payload, sort_keys=True)

        expected_routes = {
            "/scenario-lab/single-sensor-spike.json",
            "/scenario-lab/multi-sensor-confirmed-warming.json",
            "/scenario-lab/unresolved-mapping-risk.json",
            "/scenario-lab/door-open-warming.json",
            "/scenario-lab/dropout-weak-signal.json",
            "/scenario-lab/no-excursion-control.json",
        }

        self.assertEqual(set(payload["scenarioRoutes"]), expected_routes)
        self.assertEqual(payload["scenarioCount"], 6)

    def test_each_scenario_has_required_review_fields(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["scenarioId"]):
                payload = get_scenario_payload(scenario["scenarioId"])
                json.dumps(payload, sort_keys=True)

                self.assertTrue(payload["syntheticOnly"])
                self.assertTrue(payload["advisoryOnly"])
                self.assertIn("inputSignals", payload)
                self.assertIn("dataQualityFindings", payload)
                self.assertIn("zoneConsensusFindings", payload)
                self.assertIn("sersAdvisoryFindings", payload)
                self.assertIn("humanReviewChecklist", payload)
                self.assertIn("blockedAutonomousActions", payload)
                self.assertIn("expectedSystemBehavior", payload)

    def test_no_excursion_control_regression_guard(self):
        payload = get_scenario_payload("no-excursion-control")
        advisory = payload["sersAdvisoryFindings"]

        self.assertEqual(advisory["riskBand"], "WATCH")
        self.assertLessEqual(advisory["riskScore"], 34)
        self.assertEqual(advisory["unresolvedMappingRiskContribution"], 0)
        self.assertTrue(payload["inputSignals"]["mappingResolved"])

    def test_claim_boundary_is_synthetic_advisory_and_blocks_actions(self):
        catalog = get_scenario_lab_payload()
        text = json.dumps(
            {
                "catalog": catalog,
                "claimsBoundary": CLAIMS_BOUNDARY,
                "scenarios": [get_scenario_payload(s["scenarioId"]) for s in SCENARIOS],
            },
            sort_keys=True,
        ).lower()

        self.assertIn("synthetic scenario data only", text)
        self.assertIn("advisory review support only", text)
        self.assertIn("deterministic rules remain authoritative", text)
        self.assertIn("release action blocked", text)
        self.assertIn("quarantine or hold action blocked", text)
        self.assertIn("discard action blocked", text)
        self.assertIn("reroute action blocked", text)
        self.assertIn("customer notification action blocked", text)

        forbidden_positive_claims = [
            "production validated",
            "pharma validated",
            "real-world validated",
            "compliance certified",
            "safe for distribution",
            "approved for release",
            "autonomous action performed",
            "automatically released",
            "automatically quarantined",
            "automatically discarded",
            "automatically rerouted",
            "customer notified",
            "better than competitors",
        ]

        for claim in forbidden_positive_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)

    def test_unknown_scenario_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_scenario_payload("missing-scenario")


if __name__ == "__main__":
    unittest.main()