import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from route_reliability_v2 import get_route_reliability_payload,render_route_reliability_html
class ReliabilityTests(unittest.TestCase):
 def test_all(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("self-http")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_route_reliability_payload(); h=render_route_reliability_html()
  self.assertEqual(p["phase"],"Phase 27 - Route Reliability and Demo Resilience"); self.assertTrue(p["safeModeAvailable"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"): self.assertFalse(p[k])
  self.assertTrue(all(not x["requiredForBoot"] for x in p["optionalDependencies"].values())); self.assertEqual(p["routeMap"]["demoSafeMode"],"/demo-safe-mode"); self.assertIn("no self-HTTP monitoring",h)
  t=(json.dumps(p)+h).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
if __name__=="__main__": unittest.main()
