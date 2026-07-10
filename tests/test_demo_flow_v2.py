import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from demo_flow_v2 import get_demo_flow_payload,get_demo_step_payload,render_demo_flow_html,render_demo_step_html
class DemoFlowTests(unittest.TestCase):
 def test_payload_steps_boundaries(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_demo_flow_payload(); h=render_demo_flow_html(); h1=render_demo_step_html(1); h14=render_demo_step_html(14)
  self.assertEqual(p["phase"],"Phase 30 - Final Demo Flow Builder"); self.assertEqual(p["stepCount"],14); self.assertEqual(len(p["demoSteps"]),14); self.assertFalse(p["demoFreezeActive"]); self.assertTrue(p["demoReadyButNotFrozen"]); self.assertFalse(p["databaseRequired"]); self.assertFalse(p["persistenceEnabled"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"):self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"):self.assertFalse(p[k])
  self.assertEqual(get_demo_step_payload(1)["route"],"/command-center"); self.assertEqual(get_demo_step_payload(14)["route"],"/production-gap-analysis"); self.assertIn("Start demo",h); self.assertIn("Presenter script",h1); self.assertIn("Step 14",h14)
  for label in ("Synthetic-only","Advisory-only","Demo not frozen","Deterministic rules authoritative","Runtime GPU required: false","Runtime external service required: false"): self.assertIn(label,h)
 def test_routes_unknown_claims(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_demo_flow_payload()
  self.assertEqual(p["routeMap"]["demoFlow"],"/demo-flow"); self.assertEqual(p["routeMap"]["step14"],"/demo-flow/step-14")
  for i in range(1,15): self.assertEqual(p["routeMap"][f"step{i}"],f"/demo-flow/step-{i}")
  for key in ("demoConsole","judgeEvidence","finalValidation","productionGapAnalysis"): self.assertIn(key,p["routeMap"])
  with self.assertRaises(KeyError):get_demo_step_payload(999)
  t=json.dumps(p).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"):self.assertNotIn(s,t)
if __name__=="__main__":unittest.main()
