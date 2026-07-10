import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from demo_freeze_gate_v2 import get_demo_freeze_gate_payload,get_final_demo_checklist_payload,render_demo_freeze_gate_html
class FreezeGateTests(unittest.TestCase):
 def test_payload_alias_and_boundaries(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_demo_freeze_gate_payload(); alias=get_final_demo_checklist_payload(); h=render_demo_freeze_gate_html()
  self.assertEqual(p,alias); self.assertEqual(p["phase"],"Phase 31 - Final Demo QA Freeze Gate"); self.assertEqual(p["status"],"READY_FOR_OWNER_FREEZE_DECISION"); self.assertEqual(len(p["qaChecklist"]),13); self.assertEqual(len(p["liveValidationChecklist"]),12); self.assertTrue(p["goNoGoRules"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative","ownerFreezeDecisionRequired"):self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed","demoFreezeActive","productionValidated","pharmaValidated","realWorldValidated","complianceCertified","databaseRequired","persistenceEnabled"):self.assertFalse(p[k])
  self.assertEqual(p["routeMap"]["demoFreeze"],"/demo-freeze"); self.assertIn("Owner freeze decision required",h); self.assertIn("not production validation",h)
 def test_claims(self):
  t=json.dumps(get_demo_freeze_gate_payload()).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"):self.assertNotIn(s,t)
if __name__=="__main__":unittest.main()
