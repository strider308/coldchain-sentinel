import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from decision_simulator_v2 import get_decision_simulator_payload,get_decision_simulator_case_payload,render_decision_simulator_html
class SimulatorTests(unittest.TestCase):
 def test_payload(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_decision_simulator_payload()
  self.assertEqual(p["phase"],"Phase 28 - Human Review Decision Simulator"); self.assertGreaterEqual(len(p["simulatorCases"]),14); self.assertFalse(p["databaseRequired"]); self.assertFalse(p["persistenceEnabled"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"): self.assertFalse(p[k])
  self.assertEqual(p["allowedReviewerActions"],["inspect","annotate","request evidence","mark review status"]); self.assertEqual(p["routeMap"]["decisionSimulator"],"/decision-simulator")
 def test_html_claims_unknown(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_decision_simulator_payload(); h=render_decision_simulator_html()
  self.assertIn("no persistence; no operational action",h)
  t=(json.dumps(p)+h).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
  with self.assertRaises(KeyError): get_decision_simulator_case_payload("unknown-case")
if __name__=="__main__": unittest.main()
