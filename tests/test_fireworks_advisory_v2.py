import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fireworks_advisory_v2 import (  # noqa: E402
    get_case_fireworks_advisory_payload,
    get_fireworks_advisory_payload,
    get_fireworks_model_card_payload,
    render_fireworks_advisory_html,
    render_fireworks_model_card_html,
)


class FireworksAdvisoryV2Tests(unittest.TestCase):
    def test_catalog_payload_shape_and_fallback_boundary(self):
        payload = get_fireworks_advisory_payload()

        self.assertEqual(payload["phase"], "Phase 12 - Fireworks Advisory Explanation Layer")
        self.assertEqual(payload["status"], "SAFETY_GATED_OPTIONAL")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["runtimeExternalServiceRequired"])
        self.assertGreaterEqual(len(payload["cases"]), 1)
        self.assertIn("safetyBoundaries", payload)

    def test_missing_key_uses_deterministic_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            payload = get_case_fireworks_advisory_payload("no-excursion-control")

        self.assertFalse(payload["provider"]["fireworksConfigured"])
        self.assertFalse(payload["provider"]["fireworksCallSucceeded"])
        self.assertEqual(payload["provider"]["displayedAdvisorySource"], "deterministic_fallback")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["provider"]["runtimeExternalServiceRequired"])
        self.assertFalse(payload["context"]["autonomousActionsAllowed"])

    def test_structured_fireworks_response_passes_safety_gate(self):
        response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "Synthetic review remains pending because the advisory risk evidence needs inspection.",
                                "riskDrivers": ["Temperature trend requires review."],
                                "evidenceToInspect": ["Inspect synthetic consensus and sensor-quality evidence."],
                                "confidenceLimits": ["Synthetic-only benchmark context."],
                                "humanReviewPrompt": "Document what evidence a reviewer would inspect next.",
                                "safetyNote": "Deterministic rules remain authoritative.",
                            }
                        )
                    }
                }
            ]
        }

        def requester(api_key, payload):
            self.assertEqual(api_key, "fake-key")
            self.assertEqual(payload["response_format"]["type"], "json_object")
            return response

        with patch.dict(os.environ, {"FIREWORKS_API_KEY": "fake-key"}, clear=True):
            payload = get_case_fireworks_advisory_payload("no-excursion-control", requester=requester)

        self.assertTrue(payload["provider"]["fireworksConfigured"])
        self.assertTrue(payload["provider"]["fireworksCallSucceeded"])
        self.assertTrue(payload["provider"]["fireworksSafetyGatePassed"])
        self.assertEqual(payload["provider"]["displayedAdvisorySource"], "fireworks_safety_gated_json")

    def test_unsafe_fireworks_output_falls_back(self):
        response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "This should approve shipment.",
                                "riskDrivers": ["Unsafe operational wording."],
                                "evidenceToInspect": ["None."],
                                "confidenceLimits": ["None."],
                                "humanReviewPrompt": "Proceed.",
                                "safetyNote": "Unsafe.",
                            }
                        )
                    }
                }
            ]
        }

        with patch.dict(os.environ, {"FIREWORKS_API_KEY": "fake-key"}, clear=True):
            payload = get_case_fireworks_advisory_payload(
                "no-excursion-control",
                requester=lambda _api_key, _payload: response,
            )

        self.assertTrue(payload["provider"]["fireworksCallSucceeded"])
        self.assertFalse(payload["provider"]["fireworksSafetyGatePassed"])
        self.assertEqual(payload["provider"]["displayedAdvisorySource"], "deterministic_fallback")

    def test_model_card_and_html_boundary_language(self):
        card = get_fireworks_model_card_payload()
        html = render_fireworks_advisory_html()
        model_card_html = render_fireworks_model_card_html()

        self.assertTrue(card["syntheticOnly"])
        self.assertTrue(card["advisoryOnly"])
        self.assertFalse(card["runtimeExternalServiceRequired"])
        self.assertIn("Fireworks Advisory Explanation Layer", html)
        self.assertIn("Fallback always available", html)
        self.assertIn("Safety Controls", model_card_html)

    def test_phase12_payloads_have_no_forbidden_positive_claims(self):
        text = json.dumps(
            {
                "catalog": get_fireworks_advisory_payload(),
                "modelCard": get_fireworks_model_card_payload(),
                "case": get_case_fireworks_advisory_payload("no-excursion-control"),
            },
            sort_keys=True,
        ).lower()

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
