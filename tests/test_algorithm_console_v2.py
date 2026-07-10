import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithm_console_v2 import (
    get_algorithm_console_payload,
    get_error_coverage_payload,
    get_feature_weights_payload,
    get_prediction_table_payload,
    get_runtime_boundary_payload,
    get_weaknesses_payload,
    render_algorithm_console_html,
)


class AlgorithmConsoleTests(unittest.TestCase):
    def test_payload_routes_and_html(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            payload = get_algorithm_console_payload()
            weights = get_feature_weights_payload()
            coverage = get_error_coverage_payload()
            predictions = get_prediction_table_payload()
            weaknesses = get_weaknesses_payload()
            boundary = get_runtime_boundary_payload()
            page = render_algorithm_console_html()
        self.assertEqual(payload["phase"], "Phase 37 - Algorithm Evidence Console")
        self.assertEqual(payload["status"], "READY")
        self.assertTrue(payload["artifactAvailable"])
        self.assertTrue(payload["predictorIntegrated"])
        self.assertTrue(payload["inspectionEngineIntegrated"])
        self.assertEqual(payload["trainingRows"], 171000)
        self.assertEqual(payload["faultPrototypeCount"], 38)
        self.assertEqual(payload["featureWeightCount"], 19)
        self.assertEqual(payload["supportedFaultCount"], 38)
        self.assertEqual(payload["neuralMetrics"]["faultAccuracy"], .9551)
        self.assertEqual(payload["distilledMetrics"]["behaviorAccuracy"], .9406)
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "notebookRequiredAtRuntime", "autonomousActionsAllowed", "databaseRequired", "persistenceEnabled"):
            self.assertFalse(payload[key])
        self.assertEqual(len(weights["featureWeights"]), 19)
        values = [row["weight"] for row in weights["featureWeights"]]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertEqual(len(coverage["faultCoverageRows"]), 38)
        self.assertGreaterEqual(len(predictions["predictionRows"]), 14)
        self.assertTrue(weaknesses["uncertaintyPatterns"])
        self.assertTrue(weaknesses["mitigation"])
        self.assertTrue(boundary["stdlibOnly"])
        self.assertFalse(boundary["runtimeGpuRequired"])
        self.assertFalse(boundary["runtimePyTorchRequired"])
        self.assertFalse(boundary["runtimeExternalServiceRequired"])
        for text in ("Algorithm Evidence Console", "171,000", "Top feature weights", "Fault coverage", "Runtime safety boundary"):
            self.assertIn(text, page)
        source = (Path(__file__).resolve().parents[1] / "src" / "algorithm_console_v2.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("import " + "torch", source)

    def test_missing_artifacts_fail_safe(self):
        with tempfile.TemporaryDirectory() as directory, patch("behavior_predictor_v2.ROOT", Path(directory)):
            payload = get_algorithm_console_payload()
            page = render_algorithm_console_html()
        self.assertFalse(payload["artifactAvailable"])
        self.assertFalse(payload["predictorIntegrated"])
        self.assertFalse(payload["inspectionEngineIntegrated"])
        self.assertIn("Algorithm Evidence Console", page)


if __name__ == "__main__":
    unittest.main()
