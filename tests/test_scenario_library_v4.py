import json, socket, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scenario_library_v4 import get_expanded_scenario_payload, get_scenario_library_payload, render_scenario_library_html

class ScenarioLibraryV4Tests(unittest.TestCase):
    def test_payload_cases_and_boundaries(self):
        p = get_scenario_library_payload()
        self.assertEqual(p["phase"], "Phase 22 - Expanded Scenario Library v4")
        self.assertGreaterEqual(p["scenarioCount"], 14); self.assertTrue(p["artifactAvailable"])
        for key in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"): self.assertTrue(p[key])
        for key in ("runtimeGpuRequired", "runtimeExternalServiceRequired", "autonomousActionsAllowed"): self.assertFalse(p[key])
        case = get_expanded_scenario_payload("no-excursion-control")
        required = {"caseId","title","scenarioFamily","syntheticPattern","expectedDataQualityBehavior","expectedConsensusBehavior","expectedSersBehavior","expectedHumanReviewBehavior","expectedFireworksBehavior","blockedActions","routeLinks","safetyBoundaries"}
        self.assertTrue(required <= case.keys())
    def test_route_html_network_and_claims(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            p = get_scenario_library_payload(); html = render_scenario_library_html()
        self.assertEqual(p["routeMap"]["scenarioLibraryV4"], "/scenario-library-v4")
        self.assertIn("synthetic benchmark/demo evidence only", html)
        text = (json.dumps(p)+html).lower()
        for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,text)
    def test_unknown(self):
        with self.assertRaises(KeyError): get_expanded_scenario_payload("unknown-case")
if __name__ == "__main__": unittest.main()
