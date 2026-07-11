from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from algorithm_console_v2 import render_algorithm_console_html  # noqa: E402
from behavior_predictor_v2 import render_behavior_predictor_html  # noqa: E402
from case_walkthroughs_v2 import render_case_walkthroughs_html  # noqa: E402
from dashboard_strategy_v2 import render_dashboard_strategy_html  # noqa: E402
from demo_script_qna_v2 import render_demo_script_qna_html  # noqa: E402
from fault_atlas_v2 import render_fault_atlas_html  # noqa: E402
from final_freeze_v2 import render_final_freeze_html  # noqa: E402
from final_route_manifest_v2 import render_final_route_manifest_html  # noqa: E402
from final_visual_polish_v2 import render_visual_polish_html  # noqa: E402
from inspection_engine_v2 import render_inspection_engine_html  # noqa: E402
from judge_evidence_pack_v2 import render_judge_evidence_pack_html  # noqa: E402
from large_scale_data_lab_v2 import render_large_scale_data_lab_html  # noqa: E402
from serve_dashboard import render_not_found  # noqa: E402
from serve_dashboard_amd import render_command_center_with_amd, render_root_with_design_system  # noqa: E402
from submission_readiness_v2 import render_submission_readiness_html  # noqa: E402


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.asset_urls: list[str] = []
        self.h1 = 0
        self.main = 0
        self.title = 0
        self.lang = ""

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if tag == "title":
            self.title += 1
        for name, value in attrs:
            name = name.lower()
            if tag == "html" and name == "lang":
                self.lang = value or ""
            if name == "id" and value is not None:
                self.ids.append(value)
            if tag == "a" and name == "href" and value is not None:
                self.hrefs.append(value)
            if tag in {"img", "script", "source", "video", "audio"} and name == "src" and value:
                self.asset_urls.append(value)
            if tag == "link" and name == "href" and value:
                self.asset_urls.append(value)


def pages() -> dict[str, str]:
    return {
        "/": render_root_with_design_system(),
        "/command-center": render_command_center_with_amd(),
        "/dashboard-strategy": render_dashboard_strategy_html(),
        "/algorithm-console": render_algorithm_console_html(),
        "/behavior-predictor": render_behavior_predictor_html(),
        "/inspection-engine": render_inspection_engine_html(),
        "/judge-pack": render_judge_evidence_pack_html(),
        "/case-walkthroughs": render_case_walkthroughs_html(),
        "/case-walkthroughs/door-open-warming": render_case_walkthroughs_html("door-open-warming"),
        "/fault-atlas": render_fault_atlas_html(),
        "/large-scale-data-lab": render_large_scale_data_lab_html(),
        "/final-route-manifest": render_final_route_manifest_html(),
        "/submission-readiness": render_submission_readiness_html(),
        "/demo-script-final": render_demo_script_qna_html(),
        "/judge-qna": render_demo_script_qna_html(),
        "/visual-polish": render_visual_polish_html(),
        "/final-freeze": render_final_freeze_html(),
        "/unknown": render_not_found(),
    }


def test_primary_pages_share_accessible_responsive_shell() -> None:
    for route, markup in pages().items():
        parser = StructureParser()
        parser.feed(markup)
        assert parser.lang == "en", route
        assert parser.title == 1 and parser.h1 == 1 and parser.main == 1, route
        assert len(parser.ids) == len(set(parser.ids)), route
        assert "main-content" in parser.ids, route
        assert "#main-content" in parser.hrefs, route
        assert all(href.strip() for href in parser.hrefs), route
        assert not any(url.startswith(("http://", "https://", "//")) for url in parser.asset_urls), route
        assert 'data-design-system="coherent-fast-v1"' in markup, route
        assert ":focus-visible" in markup, route
        assert "prefers-reduced-motion:reduce" in markup, route
        assert "@media(max-width:720px)" in markup, route


def test_walkthrough_title_and_404_recovery_are_meaningful() -> None:
    detail = render_case_walkthroughs_html("door-open-warming")
    assert "<title>Door-Open Warming</title>" in detail
    not_found = render_not_found()
    assert "Page not found" in not_found
    assert 'href="/command-center"' in not_found
    assert "Traceback" not in not_found


def test_duplicate_attributes_are_not_hidden_by_the_test_parser() -> None:
    parser = StructureParser()
    parser.feed('<main id="main-content" id="main-content"></main>')
    assert parser.ids == ["main-content", "main-content"]
