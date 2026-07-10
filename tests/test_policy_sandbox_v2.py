import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from policy_sandbox_v2 import get_policy_sandbox_payload,render_policy_sandbox_html
class PolicyTests(unittest.TestCase):
 def test_all(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_policy_sandbox_payload(); h=render_policy_sandbox_html()
  self.assertEqual(p["phase"],"Phase 25 - SOP Policy Knowledge Sandbox"); self.assertFalse(p["realSopUsed"]); self.assertFalse(p["vectorDatabaseRequired"]); self.assertFalse(p["retrievalRuntimeRequired"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"): self.assertFalse(p[k])
  self.assertEqual(p["routeMap"]["policySandbox"],"/policy-sandbox"); self.assertIn("no real SOP ingestion",h)
  t=(json.dumps(p)+h).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
if __name__=="__main__": unittest.main()
