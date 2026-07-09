import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_replay_v2 import get_incident_replay_catalog_payload, get_incident_replay_payload


SCENARIOS = {
    "single-sensor-spike",
    "multi-sensor-confirmed-warming",
    "unresolved-mapping-risk",
    "door-open-warming",
    "dropout-weak-signal",
    "no-excursion-control",
}


class IncidentReplayV2Tests(unittest.TestCase):
    def test_catalog_routes(self):
        payload = get_incident_replay_catalog_payload()
        json.dumps(payload, sort_keys=True)
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertEqual(set(route.split("/")[-1][:-5] for route in payload["replayRoutes"]), SCENARIOS)

    def test_replay_timeline_sorted_and_complete(self):
        required_types = {
            "synthetic_sensor_ingestion",
            "normalization",
            "data_quality_filtering",
            "consensus_scoring",
            "sers_advisory_scoring",
            "human_review_packet_creation",
            "blocked_autonomous_action_audit",
        }

        for scenario_id in SCENARIOS:
            payload = get_incident_replay_payload(scenario_id)
            json.dumps(payload, sort_keys=True)
            self.assertTrue(payload["syntheticOnly"])
            self.assertTrue(payload["advisoryOnly"])
            offsets = [event["minuteOffset"] for event in payload["timelineEvents"]]
            self.assertEqual(offsets, sorted(offsets))
            self.assertEqual({event["eventType"] for event in payload["timelineEvents"]}, required_types)

    def test_no_excursion_control_guard(self):
        payload = get_incident_replay_payload("no-excursion-control")
        text = json.dumps(payload, sort_keys=True)
        self.assertIn("WATCH", text)
        self.assertIn("34", text)

    def test_forbidden_positive_claims_absent(self):
        text = json.dumps(get_incident_replay_catalog_payload(), sort_keys=True).lower()
        for scenario_id in SCENARIOS:
            text += json.dumps(get_incident_replay_payload(scenario_id), sort_keys=True).lower()

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