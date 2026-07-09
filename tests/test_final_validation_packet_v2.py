import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from final_validation_packet_v2 import (  # noqa: E402
    get_final_validation_packet_payload,
    render_final_validation_packet_html,
)


class FinalValidationPacketV2Tests(unittest.TestCase):
    def test_payload_shape_and_boundaries(self):
        payload = get_final_validation_packet_payload()

        self.assertEqual(payload["phase"], "Phase 14 - Final Validation Evidence Packet")
        self.assertEqual(payload["status"], "DEMO_READY_NOT_PRODUCTION_VALIDATED")
        self.assertTrue(payload["syntheticOnly"])
        self.assertTrue(payload["advisoryOnly"])
        self.assertFalse(payload["productionValidated"])
        self.assertFalse(payload["pharmaValidated"])
        self.assertFalse(payload["realWorldValidated"])
        self.assertFalse(payload["complianceCertified"])
        self.assertFalse(payload["autonomousActionsAllowed"])
        self.assertFalse(payload["runtimeGpuRequired"])
        self.assertFalse(payload["runtimeExternalServiceRequired"])
        self.assertTrue(payload["deterministicRulesAuthoritative"])

    def test_commands_and_live_routes_are_present(self):
        payload = get_final_validation_packet_payload()

        self.assertIn("python tests/test_coldchain_validation.py", payload["requiredLocalCommands"])
        self.assertIn("python src/serve_dashboard_amd.py --check", payload["requiredLocalCommands"])
        for route in (
            "/demo-console",
            "/demo-console.json",
            "/judge-evidence",
            "/judge-evidence.json",
            "/final-validation",
            "/final-validation.json",
            "/validation-packet",
            "/validation-packet.json",
            "/gpu-research-lab.json",
            "/fireworks-advisory.json",
            "/cases/no-excursion-control/fireworks-advisory.json",
        ):
            self.assertIn(route, payload["requiredLiveRoutes"])

    def test_release_readiness_and_integrity(self):
        payload = get_final_validation_packet_payload()

        self.assertTrue(payload["releaseReadiness"]["demoReady"])
        self.assertFalse(payload["releaseReadiness"]["productionReady"])
        self.assertFalse(payload["releaseReadiness"]["privateBetaReady"])
        self.assertTrue(payload["releaseReadiness"]["needsOwnerManualRenderDeploy"])
        self.assertTrue(payload["evidenceIntegrity"]["noSecretsExpected"])
        self.assertFalse(payload["evidenceIntegrity"]["rawDataCommitted"])

    def test_html_contains_required_language(self):
        rendered = render_final_validation_packet_html()

        self.assertIn("Demo-ready evidence packet, not production validation", rendered)
        self.assertIn("Local validation commands", rendered)
        self.assertIn("Live routes after manual Render deploy", rendered)
        self.assertIn("Synthetic-only", rendered)
        self.assertIn("Advisory-only", rendered)
        self.assertIn("Runtime GPU required: false", rendered)
        self.assertIn("Runtime external service required: false", rendered)
        self.assertIn("/demo-console", rendered)
        self.assertIn("/command-center", rendered)

    def test_no_forbidden_positive_claims_in_payload(self):
        text = json.dumps(get_final_validation_packet_payload(), sort_keys=True).lower()
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
