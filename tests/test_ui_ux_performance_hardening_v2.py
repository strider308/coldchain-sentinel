import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from algorithm_console_v2 import render_algorithm_console_html  # noqa: E402
from dashboard_strategy_v2 import render_dashboard_strategy_html  # noqa: E402
from final_freeze_v2 import render_final_freeze_html  # noqa: E402
from judge_evidence_pack_v2 import render_judge_evidence_pack_html  # noqa: E402
from serve_dashboard_amd import (  # noqa: E402
    command_center_with_amd_json,
    render_command_center_with_amd,
    render_root_with_design_system,
)
from submission_readiness_v2 import render_submission_readiness_html  # noqa: E402
from ui_design_system_v2 import DESIGN_TOKENS, SHARED_CSS  # noqa: E402


def test_shared_shell_and_fast_command_center_contract():
    assert DESIGN_TOKENS["accent"] == "#62c9a5"
    assert 'data-design-system="coherent-fast-v1"' in SHARED_CSS
    payload = command_center_with_amd_json()
    assert payload["simplifiedDashboard"] is True
    assert payload["performanceOptimized"] is True
    assert payload["uiVersion"] == "coherent-fast-v1"
    assert payload["aboveTheFoldActions"] == 4
    assert payload["visibleMetricCount"] == 4
    assert payload["visibleInspectionCardCount"] == 4
    for key, expected in {
        "syntheticOnly": True, "advisoryOnly": True, "runtimeGpuRequired": False,
        "runtimeExternalServiceRequired": False, "runtimePyTorchRequired": False,
        "autonomousActionsAllowed": False, "deterministicRulesAuthoritative": True,
    }.items():
        assert payload[key] is expected


def test_command_center_and_root_are_compact_and_safe():
    center = render_command_center_with_amd()
    root = render_root_with_design_system()
    for text in ("ColdChain Sentinel", "Start Demo", "Algorithm Evidence", "Judge Pack", "Submission", "What to inspect next", "Synthetic-only", "Advisory-only"):
        assert text in center
    assert len(center.encode("utf-8")) < 120_000
    assert center.count("<a ") < 30
    assert "routeMap" not in center
    assert 'data-ui-version="coherent-fast-v1"' in center
    assert '@media(max-width:720px)' in center
    assert "/command-center" in root
    assert 'data-ui-version="coherent-fast-v1"' in root
    assert "https://" not in center + root


def test_core_demo_pages_share_shell_without_external_assets():
    pages = [
        render_dashboard_strategy_html(), render_algorithm_console_html(),
        render_judge_evidence_pack_html(), render_submission_readiness_html(),
        render_final_freeze_html(),
    ]
    assert all('data-design-system="coherent-fast-v1"' in page for page in pages)
    assert all('class="ui-global-nav"' in page for page in pages)
    assert all("https://" not in page and "<script" not in page.lower() for page in pages)
    source = (ROOT / "src" / "serve_dashboard_amd.py").read_text(encoding="utf-8").lower()
    assert "import " + "torch" not in source
