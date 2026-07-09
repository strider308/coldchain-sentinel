import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from human_review_workbench_v2 import get_review_packet_payload, get_review_workbench_payload


SCENARIOS = {
    "single-sensor-spike",
    "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk",
    "door-open-warming",
    "dropout-weak-signal",
    "no-excursion-control",
}


class HumanReviewWorkbenchV2Tests(unittest.TestCase):
    def test_catalog_routes(self):
        payload = get_review_workbench_payload()
        json.dumps(payload, sort_keys=True)
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertEqual(set(route.split("/")[-1][:-5] for route in payload["packetRoutes"]), SCENARIOS)

    def test_packets_have_required_fields(self):
        for scenario_id in SCENARIOS:
            payload = get_review_packet_payload(scenario_id)
            json.dumps(payload, sort_keys=True)
            self.assertTrue(payload["syntheticOnly"])
            self.assertTrue(payload["advisoryOnly"])
            self.assertEqual(payload["decisionAuthority"], "deterministic rules remain authoritative")
            self.assertEqual(payload["sersScope"], "advisory-only")
            self.assertIn("evidenceTabs", payload)
            self.assertIn("checklistStatus", payload)
            self.assertTrue(all(item["status"] == "incomplete" for item in payload["checklistStatus"]))
            self.assertTrue(all(item["autoDecision"] is False for item in payload["checklistStatus"]))

    def test_no_excursion_control_guard(self):
        payload = get_review_packet_payload("no-excursion-control")
        self.assertEqual(payload["riskBand"], "WATCH")
        self.assertLessEqual(payload["riskScore"], 34)

    def test_forbidden_positive_claims_absent(self):
        text = json.dumps(get_review_workbench_payload(), sort_keys=True).lower()
        for scenario_id in SCENARIOS:
            text += json.dumps(get_review_packet_payload(scenario_id), sort_keys=True).lower()

        forbidden = [
            "production validated",
            "pharma validated",
            "real-world validated",
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

        for claim in forbidden:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)


if __name__ == "__main__":
    unittest.main()