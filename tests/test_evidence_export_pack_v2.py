import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from evidence_export_pack_v2 import get_evidence_export_payload,get_evidence_route_manifest_payload,render_evidence_export_html
class EvidenceExportTests(unittest.TestCase):
 def test_payload(self):
  p=get_evidence_export_payload(); self.assertEqual(p["phase"],"Phase 24 - Evidence Export Pack"); self.assertEqual(len(p["evidenceSections"]),11); self.assertIn("ColdChain Sentinel",p["summaryMarkdown"])
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"): self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"): self.assertFalse(p[k])
  self.assertTrue(get_evidence_route_manifest_payload()["routes"])
 def test_html_routes_network_claims(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_evidence_export_payload(); h=render_evidence_export_html()
  self.assertEqual(p["routeMap"]["evidenceExport"],"/evidence-export"); self.assertIn("Route manifest",h)
  t=(json.dumps(p)+h).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"): self.assertNotIn(s,t)
if __name__=="__main__": unittest.main()
