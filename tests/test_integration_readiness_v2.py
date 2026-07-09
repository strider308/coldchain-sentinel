import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from integration_readiness_v2 import (
    PHASE2_FIELDS,
    get_integration_contract_payload,
    get_integration_readiness_payload,
    get_integration_safety_payload,
)


class IntegrationReadinessV2Tests(unittest.TestCase):
    def test_payloads_are_json_serializable_and_bounded(self):
        for payload in [
            get_integration_readiness_payload(),
            get_integration_contract_payload(),
            get_integration_safety_payload(),
        ]:
            json.dumps(payload, sort_keys=True)
            self.assertTrue(payload["syntheticOnly"])
            self.assertTrue(payload["advisoryOnly"])
            self.assertEqual(payload["externalCalls"], "none")
            self.assertEqual(payload["webhookDelivery"], "disabled")

    def test_inbound_contract_matches_phase2_fields(self):
        payload = get_integration_contract_payload()
        inbound_names = [field["name"] for field in payload["sampleInboundContract"]["fields"]]
        self.assertEqual(inbound_names, PHASE2_FIELDS)

    def test_outbound_contract_is_advisory_and_human_review_required(self):
        sample = get_integration_contract_payload()["sampleOutboundAdvisoryContract"]["sample"]
        self.assertTrue(sample["syntheticOnly"])
        self.assertTrue(sample["advisoryOnly"])
        self.assertTrue(sample["humanReviewRequired"])
        self.assertEqual(sample["riskBand"], "WATCH")
        self.assertLessEqual(sample["riskScore"], 34)

    def test_forbidden_positive_claims_absent(self):
        text = json.dumps(
            {
                "readiness": get_integration_readiness_payload(),
                "contract": get_integration_contract_payload(),
                "safety": get_integration_safety_payload(),
            },
            sort_keys=True,
        ).lower()

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