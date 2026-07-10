import json, socket, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dashboard_strategy_v2 import get_dashboard_strategy_payload, render_dashboard_strategy_html
from serve_dashboard_amd import command_center_with_amd_json

class DashboardStrategyTests(unittest.TestCase):
    def test_payload_metrics_and_safety(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            p = get_dashboard_strategy_payload(); page = render_dashboard_strategy_html()
        self.assertEqual(p["phase"], "Phase 33 - Screenshot-Worthy Command Center Upgrade")
        for k in ("syntheticOnly", "advisoryOnly", "deterministicRulesAuthoritative"): self.assertTrue(p[k])
        for k in ("runtimeGpuRequired", "runtimeExternalServiceRequired", "autonomousActionsAllowed", "architectureChanged", "dependenciesAdded"): self.assertFalse(p[k])
        score=p["sentinelReadinessScore"]; self.assertIn(score["band"], {"READY","WATCH","REVIEW"}); self.assertTrue(0 <= score["score"] <= 100); self.assertTrue(score["notOperationalScore"])
        self.assertTrue(p["evidenceConfidencePulse"]["notRealWorldConfidence"]); self.assertTrue(p["whatNext"]); self.assertTrue(p["screenshotWorthyChecklist"])
        self.assertFalse(p["syntheticLiveView"]["liveDataClaimed"]); self.assertTrue(p["syntheticLiveView"]["syntheticActivityOnly"]); self.assertTrue(p["whyLayer"]["noExternalCallFromDashboard"])
        for text in ("Sentinel Readiness Score", "What Next?", "Synthetic Live View", "Fireworks optional", "Deterministic rules authoritative"): self.assertIn(text, page)
    def test_routes_command_center_and_claims(self):
        p=get_dashboard_strategy_payload(); required={"commandCenter","dashboardStrategy","screenshotWorthyDashboard","demoFlow","scenarioLibraryV4","evaluationMatrixV2","expandedBenchmark","fireworksAdvisory","llmAdvisoryEval","decisionSimulator","partnerApiContract","finalValidation","productionGapAnalysis"}; self.assertTrue(required <= p["routeMap"].keys())
        self.assertTrue(all(x["targetRoute"].startswith("/") for x in p["whatNext"])); routes=command_center_with_amd_json()["routeMap"]; self.assertEqual(routes["dashboardStrategy"],"/dashboard-strategy"); self.assertEqual(routes["screenshotWorthyDashboard"],"/screenshot-worthy-dashboard")
        text=json.dumps(p).lower()
        for claim in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(claim,text)
if __name__ == "__main__": unittest.main()
