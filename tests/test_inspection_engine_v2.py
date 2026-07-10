import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inspection_engine_v2 import (
    get_inspection_engine_payload,
    get_inspection_plan,
    get_root_cause_analysis,
    render_inspection_engine_html,
)


class InspectionEngineTests(unittest.TestCase):
    def test_payload_boundaries_and_html(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            payload = get_inspection_engine_payload()
            page = render_inspection_engine_html()
        self.assertEqual(payload["phase"], "Phase 36 - Root Cause and Inspection Recommendation Engine")
        self.assertEqual(payload["status"], "READY")
        self.assertGreaterEqual(payload["supportedCaseCount"], 14)
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative", "stblIntegrated"):
            self.assertTrue(payload[key])
        for key in ("realWorldDataUsed", "runtimeGpuRequired", "runtimeExternalServiceRequired", "runtimePyTorchRequired", "autonomousActionsAllowed", "databaseRequired", "persistenceEnabled"):
            self.assertFalse(payload[key])
        self.assertIn("What is wrong", page)
        self.assertIn("What should a human inspect", page)
        self.assertIn("Human review required", page)

    def test_case_guidance_and_unknown_case(self):
        for case_id in ("no-excursion-control", "single-sensor-spike", "unresolved-mapping-risk", "dropout-weak-signal", "gateway-delay", "late-arriving-data"):
            plan = get_inspection_plan(case_id)
            analysis = get_root_cause_analysis(case_id)
            self.assertGreaterEqual(len(plan["inspectionChecklist"]), 4)
            self.assertGreaterEqual(len(plan["humanReviewQuestions"]), 3)
            self.assertEqual(set(plan["blockedOperationalActions"]), {"release", "quarantine", "discard", "reroute", "customer messaging"})
            self.assertTrue(analysis["evidenceFor"])
            self.assertTrue(analysis["evidenceAgainst"])
            self.assertTrue(analysis["uncertaintyDrivers"])
            self.assertTrue(analysis["whatToInspectFirst"])
        self.assertIn("sensor", get_inspection_plan("single-sensor-spike")["primaryInspectionTarget"])
        self.assertIn("mapping", get_inspection_plan("unresolved-mapping-risk")["primaryInspectionTarget"])
        self.assertTrue(any(word in json.dumps(get_inspection_plan("dropout-weak-signal")).lower() for word in ("gateway", "signal")))
        self.assertTrue(any(word in json.dumps(get_inspection_plan("gateway-delay")).lower() for word in ("gateway", "timestamp")))
        self.assertIn("timestamp", json.dumps(get_inspection_plan("late-arriving-data")).lower())
        with self.assertRaises(KeyError):
            get_inspection_plan("unknown-case")
        with self.assertRaises(KeyError):
            get_root_cause_analysis("unknown-case")
        claims = json.dumps(get_inspection_engine_payload()).lower()
        for phrase in ("production" + "-ready", "pharma" + " validated", "real-world" + " validated", "compliance" + " certified", "autonomous" + " release", "customer" + " notification"):
            self.assertNotIn(phrase, claims)


if __name__ == "__main__":
    unittest.main()
