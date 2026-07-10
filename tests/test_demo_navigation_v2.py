import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from demo_navigation_v2 import get_demo_navigation_payload,get_navigation_map_payload,render_demo_navigation_html
class NavigationTests(unittest.TestCase):
 def test_payload_alias_groups_and_boundaries(self):
  with patch.object(socket,"create_connection",side_effect=AssertionError("network")),patch("urllib.request.urlopen",side_effect=AssertionError("network")): p=get_demo_navigation_payload(); alias=get_navigation_map_payload(); h=render_demo_navigation_html()
  self.assertEqual(p,alias); self.assertEqual(p["phase"],"Phase 32 - UI Polish Demo Navigation Pass"); self.assertEqual(len(p["navigationGroups"]),6); self.assertTrue(p["polishOnly"]); self.assertFalse(p["architectureChanged"]); self.assertFalse(p["dependenciesAdded"]); self.assertFalse(p["databaseRequired"]); self.assertFalse(p["persistenceEnabled"])
  required={"title","route","purpose","demoUse","safetyBadge","priority"}; self.assertTrue(all(set(x)==required for g in p["navigationGroups"] for x in g["items"]))
  for k in ("syntheticOnly","advisoryOnly","deterministicRulesAuthoritative"):self.assertTrue(p[k])
  for k in ("runtimeGpuRequired","runtimeExternalServiceRequired","autonomousActionsAllowed"):self.assertFalse(p[k])
  self.assertEqual(p["routeMap"]["navigationMap"],"/navigation-map"); self.assertIn("Start demo",h); self.assertIn("Freeze gate",h)
 def test_claims(self):
  t=json.dumps(get_demo_navigation_payload()).lower()
  for s in ("production"+"-ready","pharma"+" validated","real-world"+" validated","compliance"+" certified","autonomous"+" release","autonomous"+" quarantine","autonomous"+" discard","autonomous"+" reroute","customer"+" notification"):self.assertNotIn(s,t)
if __name__=="__main__":unittest.main()
