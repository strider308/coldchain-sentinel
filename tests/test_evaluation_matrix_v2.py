import json, socket, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from evaluation_matrix_v2 import get_evaluation_matrix_payload,get_evaluation_row_payload,render_evaluation_matrix_html
class EvaluationMatrixV2Tests(unittest.TestCase):
 def test_payload(self):
  p=get_evaluation_matrix_payload(); self.assertEqual(p["phase"],"Phase 23 - Evaluation Matrix v2"); self.assertGreaterEqual(len(p["matrixRows"]),14)
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"): self.assertFalse(p[k])
  self.assertFalse(get_evaluation_row_payload("no-excursion-control")["autonomousActionAllowed"])
 def test_html_routes_network_claims(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_evaluation_matrix_payload(); h=render_evaluation_matrix_html()
  self.assertEqual(p["routeMap"]["evaluationMatrixV2"],"/evaluation-matrix-v2"); self.assertIn("not external validation",h)
  t=(json.dumps(p)+h).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
 def test_unknown(self):
  with self.assertRaises(KeyError): get_evaluation_row_payload("unknown-case")
if __name__=="__main__": unittest.main()
