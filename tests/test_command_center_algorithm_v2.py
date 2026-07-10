import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from command_center_algorithm_v2 import (
    get_algorithm_insights_payload,
    get_command_center_algorithm_payload,
    get_what_to_inspect_next_payload,
    render_command_center_algorithm_html,
)
from dashboard_strategy_v2 import get_dashboard_strategy_payload
from serve_dashboard_amd import command_center_with_amd_json, render_command_center_with_amd


class CommandCenterAlgorithmTests(unittest.TestCase):
    def test_payload_alias_and_html(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            payload = get_command_center_algorithm_payload()
            alias = get_algorithm_insights_payload()
            inspect = get_what_to_inspect_next_payload()
            page = render_command_center_algorithm_html()
        self.assertEqual(payload, alias)
        self.assertEqual(payload["phase"], "Phase 38 - Command Center Algorithm Integration")
        self.assertEqual(payload["status"], "READY")
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative", "stblIntegrated", "inspectionEngineIntegrated", "algorithmConsoleIntegrated", "dashboardIntegrationOnly"):
            self.assertTrue(payload[key])
        for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed", "architectureChanged", "dependenciesAdded"):
            self.assertFalse(payload[key])
        self.assertEqual(payload["headlineMetrics"]["trainingRows"], 171000)
        self.assertEqual(payload["headlineMetrics"]["supportedFaultCount"], 38)
        self.assertEqual(payload["headlineMetrics"]["featureWeightCount"], 19)
        self.assertGreaterEqual(len(payload["whatToInspectNext"]), 5)
        self.assertGreaterEqual(len(inspect["priorityInspectionCards"]), 5)
        required = {"algorithmConsole", "behaviorPredictor", "inspectionEngine"}
        self.assertTrue(required.issubset(payload["routeMap"]))
        for text in ("What is wrong", "What should we inspect", "STBL", "Algorithm Console", "Behavior Predictor", "Inspection Engine"):
            self.assertIn(text, page)

    def test_command_center_integration(self):
        payload = command_center_with_amd_json()
        page = render_command_center_with_amd()
        for key in ("algorithmConsole", "commandCenterAlgorithm", "algorithmInsights", "whatToInspectNext", "behaviorPredictor", "inspectionEngine"):
            self.assertIn(key, payload["routeMap"])
        for text in ("Algorithm Console", "Behavior Predictor", "Inspection Engine", "What to inspect"):
            self.assertIn(text, page)
        strategy_routes = get_dashboard_strategy_payload()["routeMap"]
        self.assertEqual(strategy_routes["algorithmConsole"], "/algorithm-console")
        self.assertEqual(strategy_routes["commandCenterAlgorithm"], "/command-center-algorithm")


if __name__ == "__main__":
    unittest.main()
