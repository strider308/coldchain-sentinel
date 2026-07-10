import json
import os
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_readiness_v2 import get_ops_readiness_payload, render_ops_readiness_html  # noqa: E402


class OpsReadinessV2Tests(unittest.TestCase):
    def test_payload_shape_and_safety_flags(self):
        payload = get_ops_readiness_payload()
        json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["phase"], "Phase 19 - Ops Readiness and Evidence Health")
        self.assertEqual(payload["status"], "READY")
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in ("runtimeGpuRequired", "runtimeExternalServiceRequired", "productionMonitoringClaimed"):
            self.assertFalse(payload[key])

    def test_evidence_health_and_readiness_summary(self):
        payload = get_ops_readiness_payload()
        self.assertEqual(
            set(payload["evidenceHealth"]),
            {
                "gpuArtifactAvailable",
                "fireworksConfigured",
                "fireworksFallbackAvailable",
                "demoConsoleAvailable",
                "validationPacketAvailable",
                "integrationSandboxAvailable",
                "auditLedgerAvailable",
                "reviewerWorkspaceAvailable",
                "scenarioEvidenceAvailable",
            },
        )
        self.assertTrue(payload["evidenceHealth"]["fireworksFallbackAvailable"])
        self.assertTrue(all(row["expectedAvailable"] for row in payload["routeHealth"]))
        self.assertEqual(
            payload["readinessSummary"],
            {
                "demoEvidenceReady": True,
                "productionOpsReady": False,
                "externalDependenciesRequiredForBoot": False,
                "humanReviewRequiredForOperationalUse": True,
            },
        )

    def test_payload_builder_makes_no_network_calls(self):
        sentinel = "test-key-must-not-leak"
        with (
            patch.dict(os.environ, {"FIREWORKS_API_KEY": sentinel}),
            patch.object(socket, "create_connection", side_effect=AssertionError("network call")),
            patch("urllib.request.urlopen", side_effect=AssertionError("network call")),
        ):
            content = json.dumps(get_ops_readiness_payload()) + render_ops_readiness_html()
        self.assertNotIn(sentinel, content)

    def test_html_boundary_language_and_claim_scan(self):
        page = render_ops_readiness_html()
        self.assertIn("Evidence health only, not production monitoring.", page)
        self.assertIn("Static route health", page)
        self.assertIn("<style>", page)
        content = (json.dumps(get_ops_readiness_payload()) + page).lower()
        forbidden = [
            "production" + " validated",
            "pharma" + " validated",
            "real-world" + " validated",
            "compliance" + " certified",
            "production" + "-ready",
            "production" + " ready",
            "autonomous " + "release",
            "autonomous " + "quarantine",
            "autonomous " + "discard",
            "autonomous " + "reroute",
            "customer" + " notification",
        ]
        for claim in forbidden:
            self.assertNotIn(claim, content)


if __name__ == "__main__":
    unittest.main()
