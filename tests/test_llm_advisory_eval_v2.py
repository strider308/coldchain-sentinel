import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from llm_advisory_eval_v2 import get_llm_advisory_eval_payload,render_llm_advisory_eval_html
class LlmEvalTests(unittest.TestCase):
 def test_all(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_llm_advisory_eval_payload(); h=render_llm_advisory_eval_html()
  self.assertEqual(p["phase"],"Phase 26 - LLM Advisory Evaluation Pack"); self.assertEqual(len(p["safetyCases"]),6); self.assertGreaterEqual(len(p["evaluationRows"]),14); self.assertFalse(p["bulkExternalCallsMade"]); self.assertFalse(p["rawModelOutputStored"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative","fireworksOptional"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"): self.assertFalse(p[k])
  self.assertEqual(p["routeMap"]["llmAdvisoryEval"],"/llm-advisory-eval"); self.assertIn("No bulk external calls",h)
  t=(json.dumps(p)+h).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
if __name__=="__main__": unittest.main()
