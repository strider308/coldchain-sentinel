import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from behavior_predictor_v2 import (
    CASE_FEATURES,
    get_behavior_predictor_payload,
    get_case_feature_vector,
    load_stbl_artifacts,
    predict_case_behavior,
    render_behavior_predictor_html,
)
from serve_dashboard_amd import command_center_with_amd_json, render_command_center_with_amd


class BehaviorPredictorTests(unittest.TestCase):
    def test_artifacts_payload_and_boundaries(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            artifacts = load_stbl_artifacts()
            payload = get_behavior_predictor_payload()
            page = render_behavior_predictor_html()
        self.assertTrue(artifacts["artifactAvailable"])
        self.assertEqual(payload["phase"], "Phase 35B - Sentinel Thermal Behavior Learner App Ingestion")
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["trainingRows"], 171000)
        self.assertEqual(payload["faultPrototypeCount"], 38)
        self.assertEqual(payload["featureWeightCount"], 19)
        self.assertGreaterEqual(payload["supportedCaseCount"], 14)
        self.assertTrue(payload["predictorAvailable"])
        self.assertTrue(payload["distilledRuntimeAvailable"])
        self.assertTrue(payload["neuralMetrics"])
        self.assertTrue(payload["distilledMetrics"])
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"):
            self.assertTrue(payload[key])
        for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "notebookRequiredAtRuntime", "autonomousActionsAllowed"):
            self.assertFalse(payload[key])
        self.assertIn("Sentinel Thermal Behavior Learner", page)
        self.assertIn("171,000", page)
        self.assertIn("distilled", page.lower())
        self.assertIn("PyTorch required: false", page)
        command = command_center_with_amd_json()
        self.assertEqual(command["routeMap"]["behaviorPredictor"], "/behavior-predictor")
        self.assertEqual(command["routeMap"]["behaviorPredictorModelCard"], "/behavior-predictor/model-card.json")
        self.assertEqual(command["routeMap"]["inspectionEngine"], "/inspection-engine")
        command_html = render_command_center_with_amd()
        self.assertIn("Behavior Predictor", command_html)
        self.assertIn("Inspection Engine", command_html)

    def test_case_predictions_and_unknown_case(self):
        stable = predict_case_behavior("no-excursion-control")
        door = predict_case_behavior("door-open-warming")
        gateway = predict_case_behavior("gateway-delay")
        mapping = predict_case_behavior("unresolved-mapping-risk")
        self.assertIn(stable["predictedBehaviorLabel"], ("stable", "warming", "data_quality_fault"))
        for item in (stable, door, gateway, mapping):
            self.assertEqual(item["phase"], "Phase 35B - Sentinel Thermal Behavior Learner App Ingestion")
            self.assertTrue(item["topAlternatives"])
            self.assertTrue(item["featureVectorSummary"])
            self.assertIn("distilledMethod", item["algorithmEvidence"])
        self.assertIn("door", door["primaryInspectionTarget"])
        self.assertTrue(any(word in gateway["primaryInspectionTarget"] for word in ("gateway", "timestamp")))
        self.assertIn("mapping", mapping["primaryInspectionTarget"])
        self.assertEqual(len(CASE_FEATURES), 14)
        with self.assertRaises(KeyError):
            get_case_feature_vector("unknown-case")
        with self.assertRaises(KeyError):
            predict_case_behavior("unknown-case")
        source = (Path(__file__).resolve().parents[1] / "src" / "behavior_predictor_v2.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("import " + "torch", source)
        claims = json.dumps(get_behavior_predictor_payload()).lower()
        for phrase in ("production" + "-ready", "pharma" + " validated", "real-world" + " validated", "compliance" + " certified", "autonomous" + " release", "customer" + " notification"):
            self.assertNotIn(phrase, claims)

    def test_missing_artifacts_fail_safe(self):
        with tempfile.TemporaryDirectory() as directory, patch("behavior_predictor_v2.ROOT", Path(directory)):
            artifacts = load_stbl_artifacts()
            payload = get_behavior_predictor_payload()
            prediction = predict_case_behavior("door-open-warming")
        self.assertFalse(artifacts["artifactAvailable"])
        self.assertFalse(payload["predictorAvailable"])
        self.assertTrue(payload["deterministicFallbackAvailable"])
        self.assertFalse(prediction["predictorAvailable"])


if __name__ == "__main__":
    unittest.main()
