from __future__ import annotations

import html
from functools import wraps
from typing import Any, Callable

DESIGN_TOKENS = {
    "background": "#07110f", "surface": "#0d1c19", "surfaceRaised": "#122722",
    "border": "#29473f", "text": "#edf7f2", "muted": "#a9bcb5",
    "accent": "#62c9a5", "warning": "#ffd58a", "radius": "12px", "maxWidth": "1120px",
}

SHARED_CSS = """
<style data-design-system="coherent-fast-v1">
:root{--ui-bg:#07110f;--ui-surface:#0d1c19;--ui-raised:#122722;--ui-line:#29473f;--ui-ink:#edf7f2;--ui-muted:#a9bcb5;--ui-accent:#62c9a5;--ui-warn:#ffd58a;--ui-radius:12px;--ui-max:1120px}
*{box-sizing:border-box}body.ui-v2{margin:0;background:var(--ui-bg);color:var(--ui-ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}body.ui-v2 main{width:min(var(--ui-max),100%);margin:auto;padding:28px 18px 56px}body.ui-v2 h1{font-size:3rem;line-height:1.05;letter-spacing:-.035em;text-wrap:balance;margin:0 0 14px}body.ui-v2 h2,body.ui-v2 h3{text-wrap:balance}body.ui-v2 p{max-width:72ch;text-wrap:pretty}body.ui-v2 .ui-subtitle,body.ui-v2 .muted{color:var(--ui-muted)}body.ui-v2 a{color:var(--ui-accent)}body.ui-v2 a:focus-visible,body.ui-v2 summary:focus-visible{outline:3px solid var(--ui-accent);outline-offset:3px}body.ui-v2 .ui-skip{position:fixed;left:12px;top:-80px;z-index:10;background:var(--ui-accent);color:var(--ui-bg);padding:10px 14px;border-radius:8px}body.ui-v2 .ui-skip:focus{top:12px}body.ui-v2 .ui-global-nav{display:flex;flex-wrap:wrap;gap:6px;width:min(var(--ui-max),100%);margin:auto;padding:12px 18px;border-bottom:1px solid var(--ui-line)}body.ui-v2 .ui-global-nav a{display:inline-flex;align-items:center;min-height:44px;padding:7px 10px;border-radius:8px;text-decoration:none;font-weight:700}body.ui-v2 .ui-global-nav a:hover{background:var(--ui-surface)}body.ui-v2 .ui-badges,body.ui-v2 .badges,body.ui-v2 .ui-actions,body.ui-v2 .ui-routes{display:flex;flex-wrap:wrap;gap:8px}body.ui-v2 .ui-badge,body.ui-v2 .badges span{border:1px solid var(--ui-line);border-radius:8px;padding:7px 10px;background:transparent;color:var(--ui-ink)}body.ui-v2 .ui-button,body.ui-v2 .button,body.ui-v2 .ui-routes a{display:inline-flex;align-items:center;min-height:44px;border:1px solid var(--ui-line);border-radius:8px;padding:9px 12px;color:var(--ui-accent);text-decoration:none;font-weight:700}body.ui-v2 .ui-button:hover,body.ui-v2 .button:hover,body.ui-v2 .ui-routes a:hover{background:var(--ui-raised)}body.ui-v2 .ui-button-primary{background:var(--ui-accent);border-color:var(--ui-accent);color:var(--ui-bg)}body.ui-v2 .ui-panel,body.ui-v2 .panel,body.ui-v2 .card{border:1px solid var(--ui-line);border-radius:var(--ui-radius);background:var(--ui-surface);padding:20px;box-shadow:none}body.ui-v2 .hero{border-left:0!important;background:var(--ui-surface)!important;color:var(--ui-ink)!important;border-radius:var(--ui-radius);padding:28px}body.ui-v2 .ui-metrics{display:grid;grid-template-columns:repeat(4,1fr);border-block:1px solid var(--ui-line);margin:32px 0}body.ui-v2 .ui-metric{padding:18px 12px 18px 0}body.ui-v2 .ui-metric strong,body.ui-v2 .ui-metric span{display:block}body.ui-v2 .ui-metric strong{color:var(--ui-accent);font-size:1.55rem}body.ui-v2 .ui-metric span{color:var(--ui-muted)}body.ui-v2 .ui-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}body.ui-v2 .ui-section{margin-top:38px}body.ui-v2 .ui-compact{border-top:1px solid var(--ui-line)}body.ui-v2 .ui-compact article{display:grid;grid-template-columns:1fr auto;gap:18px;padding:14px 2px;border-bottom:1px solid var(--ui-line)}body.ui-v2 .ui-compact h3,body.ui-v2 .ui-compact p{margin:0}body.ui-v2 .ui-safety{background:var(--ui-raised);border-radius:var(--ui-radius);padding:20px;margin-top:38px}body.ui-v2 .ui-footer{margin-top:38px;padding-top:20px;border-top:1px solid var(--ui-line)}
@media(max-width:720px){body.ui-v2 main{padding:18px 12px 44px}body.ui-v2 h1{font-size:2.25rem}body.ui-v2 .ui-metrics,body.ui-v2 .ui-grid{grid-template-columns:1fr}body.ui-v2 .ui-metric{border-bottom:1px solid var(--ui-line)}body.ui-v2 .ui-compact article{grid-template-columns:1fr;gap:6px}body.ui-v2 .grid,body.ui-v2 .metrics,body.ui-v2 .routes,body.ui-v2 .proof,body.ui-v2 .split,body.ui-v2 .layout,body.ui-v2 .insights,body.ui-v2 .inspect,body.ui-v2 .story-boundary{grid-template-columns:1fr!important}body.ui-v2 .ui-button,body.ui-v2 .button{white-space:normal}}
</style>
"""

GLOBAL_NAV = '<a class="ui-skip" href="#main-content">Skip to content</a><nav class="ui-global-nav" aria-label="Primary"><a href="/">Home</a><a href="/command-center">Command Center</a><a href="/case-walkthroughs/door-open-warming">Start Demo</a><a href="/judge-pack">Evidence</a><a href="/submission-readiness">Submission</a></nav>'


def escape(value: Any) -> str:
    return html.escape(str(value))


def render_safety_badges(items: list[str]) -> str:
    return '<div class="ui-badges">' + "".join(f'<span class="ui-badge">{escape(item)}</span>' for item in items) + "</div>"


def render_route_buttons(items: list[tuple[str, str]], primary_count: int = 0) -> str:
    links = []
    for index, (label, route) in enumerate(items):
        primary = " ui-button-primary" if index < primary_count else ""
        links.append(f'<a class="ui-button{primary}" href="{escape(route)}">{escape(label)}</a>')
    return '<nav class="ui-actions" aria-label="Page actions">' + "".join(links) + "</nav>"


def render_metric_cards(items: list[tuple[str, str]]) -> str:
    return '<section class="ui-metrics" aria-label="Key metrics">' + "".join(f'<div class="ui-metric"><strong>{escape(value)}</strong><span>{escape(label)}</span></div>' for value, label in items) + "</section>"


def render_page_shell(title: str, subtitle: str, badges: list[str], primary_actions: list[tuple[str, str]], sections: str, secondary_actions: list[tuple[str, str]] | None = None) -> str:
    footer = render_route_buttons(secondary_actions or []) if secondary_actions else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>{SHARED_CSS}</head><body class="ui-v2" data-ui-version="coherent-fast-v1">{GLOBAL_NAV}<main id="main-content"><header><h1>{escape(title)}</h1><p class="ui-subtitle">{escape(subtitle)}</p>{render_safety_badges(badges)}{render_route_buttons(primary_actions, 1)}</header>{sections}<footer class="ui-footer">{footer}</footer></main></body></html>'''


def apply_design_system(page: str) -> str:
    if 'data-design-system="coherent-fast-v1"' not in page:
        page = page.replace("</head>", SHARED_CSS + "</head>", 1)
    if '<body class="ui-v2"' not in page:
        page = page.replace("<body>", '<body class="ui-v2" data-ui-version="coherent-fast-v1">', 1)
    if 'class="ui-global-nav"' not in page:
        page = page.replace('data-ui-version="coherent-fast-v1">', 'data-ui-version="coherent-fast-v1">' + GLOBAL_NAV, 1)
    if 'id="main-content"' not in page:
        page = page.replace("<main>", '<main id="main-content">', 1)
        page = page.replace("<main ", '<main id="main-content" ', 1)
    return page


def unified_page(renderer: Callable[..., str]) -> Callable[..., str]:
    @wraps(renderer)
    def wrapped(*args: Any, **kwargs: Any) -> str:
        return apply_design_system(renderer(*args, **kwargs))
    return wrapped
