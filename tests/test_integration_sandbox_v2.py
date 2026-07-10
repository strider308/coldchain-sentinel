import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from integration_readiness_v2 import PHASE2_FIELDS
from integration_sandbox_v2 import (
    get_integration_sandbox_payload,
    get_rejection_example_payload,
    get_sample_request_payload,
    get_sample_response_payload,
    render_integration_sandbox_html,
)


class IntegrationSandboxV2Tests(unittest.TestCase):
    def test_payload_shape_and_boundaries(self):
        payload = get_integration_sandbox_payload()
        json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["phase"], "Phase 15 - Integration Sandbox")
        self.assertEqual(payload["status"], "READY")
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in (
            "runtimeExternalServiceRequired",
            "runtimeGpuRequired",
            "externalCallsMade",
            "webhooksEnabled",
            "secretsRequired",
        ):
            self.assertFalse(payload[key])

    def test_samples_and_rejection(self):
        request = get_sample_request_payload()
        response = get_sample_response_payload()
        rejection = get_rejection_example_payload()
        self.assertTrue(set(PHASE2_FIELDS).issubset(request))
        self.assertTrue(response["syntheticOnly"])
        self.assertTrue(response["advisoryOnly"])
        self.assertTrue(response["humanReviewRequired"])
        self.assertFalse(rejection["accepted"])
        self.assertTrue(rejection["errors"])

    def test_routes_and_html(self):
        payload = get_integration_sandbox_payload()
        expected = {
            "/integration-sandbox",
            "/integration-sandbox.json",
            "/integration-sandbox/sample-request.json",
            "/integration-sandbox/sample-response.json",
            "/integration-sandbox/rejection-example.json",
            "/integration-readiness",
            "/data-quality",
            "/consensus",
            "/sers",
            "/demo-console",
            "/final-validation",
        }
        self.assertEqual(set(payload["routeMap"].values()), expected)
        page = render_integration_sandbox_html()
        for text in (
            "Synthetic-only",
            "Advisory-only",
            "No external calls",
            "No webhooks",
            "Deterministic rules authoritative",
            "Sample request",
            "Sample response",
            "Rejection example",
            "/integration-readiness",
            "/demo-console",
        ):
            self.assertIn(text, page)

    def test_forbidden_positive_claims_absent(self):
        text = json.dumps(get_integration_sandbox_payload(), sort_keys=True).lower()
        forbidden = [
            "production" + "-ready",
            "pharma" + " validated",
            "real-world" + " validated",
            "compliance" + " certified",
            "autonomous" + " release",
            "autonomous" + " quarantine",
            "autonomous" + " discard",
            "autonomous" + " reroute",
            "customer" + " notification",
        ]
        for claim in forbidden:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)


if __name__ == "__main__":
    unittest.main()
