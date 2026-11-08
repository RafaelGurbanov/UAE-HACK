"""End-to-end smoke tests against the running website (offline JSON mode).

Start the site first (run-website.cmd), then:
    backend\\.venv\\Scripts\\python -m pip install playwright pytest
    backend\\.venv\\Scripts\\python -m playwright install chromium
    backend\\.venv\\Scripts\\python -m pytest e2e -q
Set BASE_URL to test another address (default http://localhost:5173).
Set E2E_CHROME to a Chrome/Edge executable to skip the chromium download.
"""
from __future__ import annotations

import json
import os
import re

import pytest
from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:5173").rstrip("/")
ROUTES = ["/", "/laws", "/scenario", "/gaps", "/audit", "/about", "/laws/entry/children-data-consent"]


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        kw = {"executable_path": os.environ["E2E_CHROME"]} if os.environ.get("E2E_CHROME") else {}
        b = p.chromium.launch(**kw)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(accept_downloads=True, permissions=["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    pg.errors = []  # type: ignore[attr-defined]
    pg.on("console", lambda m: m.type == "error" and pg.errors.append(m.text))  # type: ignore[attr-defined]
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))  # type: ignore[attr-defined]
    pg.on("response", lambda r: r.status >= 500 and pg.errors.append(f"{r.status} {r.url}"))  # type: ignore[attr-defined]
    yield pg
    ctx.close()


def ask(page: Page, q: str):
    box = page.get_by_role("search").get_by_role("textbox")
    box.fill(q)
    box.press("Enter")


def lit(page: Page) -> int:
    return page.locator('[data-node][data-active="true"]').count()


# ---------------- start-up / global ----------------
@pytest.mark.parametrize("route", ROUTES)
def test_direct_url_loads_without_errors(page: Page, route: str):
    page.goto(BASE + route)
    expect(page.locator("main h1").first).to_be_visible()
    page.wait_for_load_state("networkidle")
    assert page.errors == [], page.errors  # type: ignore[attr-defined]


@pytest.mark.parametrize("route", ROUTES)
def test_no_horizontal_scroll_at_360(browser, route: str):
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    pg = ctx.new_page()
    pg.goto(BASE + route)
    pg.wait_for_load_state("networkidle")
    sw = pg.evaluate("document.documentElement.scrollWidth")
    ctx.close()
    assert sw <= 361, f"{route} scrollWidth={sw}"


def test_arabic_rtl_and_theme_persist(page: Page):
    page.goto(BASE + "/")
    page.get_by_role("button", name=re.compile("Arabic|العربية")).first.click()
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    page.goto(BASE + "/gaps")
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    expect(page.locator("main h1")).to_have_text(re.compile("[؀-ۿ]"))
    before = page.locator("html").get_attribute("data-theme")
    page.get_by_role("button", name=re.compile("theme|المظهر", re.I)).first.click()
    after = page.locator("html").get_attribute("data-theme")
    page.reload()
    assert page.locator("html").get_attribute("data-theme") == after != before


# ---------------- legal search ----------------
def test_short_input_shows_prompt_without_request(page: Page):
    page.goto(BASE + "/")
    calls = []
    page.on("request", lambda r: "/api/ask" in r.url and calls.append(r.url))
    ask(page, "hi")
    expect(page.get_by_text(re.compile("at least 3 characters"))).to_be_visible()
    page.get_by_role("button", name=re.compile("^Ask")).click()
    expect(page.get_by_text(re.compile("at least 3 characters"))).to_be_visible()
    assert calls == []
    assert page.errors == []  # type: ignore[attr-defined]


def test_answered_question_full_flow(page: Page):
    page.goto(BASE + "/")
    ask(page, "What consent is required to process a child's personal data?")
    expect(page.get_by_text("Answered from knowledge base data (no AI generation)").first).to_be_visible(timeout=15000)
    for h in ["Short answer", "Legal basis", "Details", "Status and limits"]:
        expect(page.get_by_role("heading", name=h)).to_be_visible()
    expect(page.get_by_text("Source to be verified").first).to_be_visible()
    assert lit(page) > 0
    page.locator("main button[data-citation]").first.click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    page.keyboard.press("Escape")
    expect(dlg).to_be_hidden()


def test_no_source_question(page: Page):
    page.goto(BASE + "/")
    ask(page, "weather in Paris")
    expect(page.get_by_text("No supporting source found in the knowledge base")).to_be_visible(timeout=15000)
    assert lit(page) == 0


@pytest.mark.parametrize("greet", ["hello", "salam"])
def test_greeting_gives_clickable_examples(page: Page, greet: str):
    page.goto(BASE + "/")
    ask(page, greet)
    expect(page.get_by_role("heading", name="How to ask")).to_be_visible(timeout=15000)
    assert lit(page) == 0
    ex = page.locator("#guidance-title").locator("..").get_by_role("button").first
    ex.click()
    expect(page.get_by_text("Answered from knowledge base data (no AI generation)").first).to_be_visible(timeout=15000)


@pytest.mark.parametrize("q", ["طفل بيانات موافقة الوالدين", "uşaq məlumatları valideyn razılığı"])
def test_arabic_and_azerbaijani_retrieve(page: Page, q: str):
    page.goto(BASE + "/")
    ask(page, q)
    expect(page.get_by_text("Answered from knowledge base data (no AI generation)").first).to_be_visible(timeout=15000)


def test_topic_chip_runs_search(page: Page):
    page.goto(BASE + "/")
    page.get_by_role("button", name="In-app purchases").click()
    expect(page.get_by_role("search").get_by_role("textbox")).to_have_value("In-app purchases")
    expect(page.get_by_text("Answered from knowledge base data (no AI generation)").first).to_be_visible(timeout=15000)


# ---------------- laws ----------------
def test_laws_lists_entries_and_detail(page: Page):
    page.goto(BASE + "/laws")
    rows = page.locator('a[href^="/laws/entry/"]')
    expect(rows.first).to_be_visible()
    assert rows.count() >= 8
    rows.first.click()
    expect(page.get_by_text("Answered from knowledge base data (no AI generation)")).to_be_visible()


# ---------------- scenario room ----------------
def test_scenario_full_run(page: Page):
    page.goto(BASE + "/scenario")
    page.get_by_role("button", name="Start scenario").click()
    nxt = page.get_by_test_id("release-next")
    expect(nxt).to_be_enabled(timeout=10000)
    n = 0
    while n < 10 and "All events released" not in nxt.inner_text():
        expect(nxt).to_be_enabled(timeout=15000)
        nxt.click()
        n += 1
        expect(page.get_by_test_id("timeline-event")).to_have_count(n, timeout=15000)
        page.wait_for_function(
            "() => { const b = document.querySelector('[data-testid=release-next]');"
            " return b && (!b.disabled || /All events released/.test(b.textContent || '')); }",
            timeout=20000,
        )
    expect(nxt).to_be_disabled()
    assert n >= 4
    expect(page.get_by_text("Conflict between agents").first).to_be_visible()
    expect(page.get_by_text(re.compile("prohibit", re.I)).first).to_be_visible()
    expect(page.get_by_text(re.compile("national AI ethics oversight", re.I)).first).to_be_visible()
    review = page.locator("[data-review]").first
    review.get_by_role("button", name="Escalate").click()
    expect(review.get_by_text(re.compile("need a short reason"))).to_be_visible()
    review.get_by_role("button", name="Approve").click()
    expect(page.get_by_text(re.compile("Decision recorded"))).to_be_visible(timeout=10000)
    page.get_by_role("button", name="Restart").click()
    expect(page.get_by_test_id("timeline-event")).to_have_count(0, timeout=10000)
    assert page.errors == []  # type: ignore[attr-defined]


# ---------------- gaps ----------------
def test_gap_board_filter_and_radar(page: Page):
    page.goto(BASE + "/gaps")
    expect(page.locator("article[data-gap-type]").first).to_be_visible()
    total = page.locator("article[data-gap-type]").count()
    page.get_by_role("button", name="Legislative gap").click()
    page.wait_for_timeout(500)
    types = page.locator("article[data-gap-type]").evaluate_all("els => els.map(e => e.dataset.gapType)")
    assert types and set(types) == {"legislative_gap"} and len(types) <= total
    assert page.locator("[data-testid=radar] path").count() > 0
    expect(page.get_by_text("Gap (analysis, not law)").first).to_be_visible()


# ---------------- audit ----------------
def test_audit_records_and_exports(page: Page):
    page.goto(BASE + "/")
    ask(page, "Can an app show targeted ads to minors?")
    expect(page.get_by_text("Answered from knowledge base data (no AI generation)").first).to_be_visible(timeout=15000)
    page.goto(BASE + "/audit")
    row = page.locator("li[data-audit] > button").first
    expect(row).to_be_visible()
    row.click()
    expect(row).to_have_attribute("aria-expanded", "true")
    with page.expect_download() as d:
        page.get_by_role("button", name="Download JSON").click()
    data = json.loads(open(d.value.path(), encoding="utf-8").read())
    assert isinstance(data, list) and data and "timestamp" in data[0]
    page.get_by_role("button", name="Copy JSON").click()
    expect(page.get_by_text(re.compile("Copied as JSON|Copy failed"))).to_be_visible()
    page.reload()
    expect(page.locator("li[data-audit]").first).to_be_visible()


# ---------------- keyboard ----------------
def test_keyboard_focus_visible(page: Page):
    page.goto(BASE + "/")
    page.wait_for_load_state("networkidle")
    for _ in range(4):
        page.keyboard.press("Tab")
        style = page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
        assert style not in ("none", ""), "focused element has no visible outline"


def test_controversy_scenario_and_no_source_agent(page: Page):
    page.goto(BASE + "/scenario")
    sel = page.get_by_label("Scenario")
    val = sel.locator("option", has_text="controversial").first.get_attribute("value")
    sel.select_option(val)
    page.get_by_role("button", name="Start scenario").click()
    nxt = page.get_by_test_id("release-next")
    expect(nxt).to_be_enabled(timeout=10000)
    nxt.click()
    expect(page.get_by_test_id("timeline-event")).to_have_count(1, timeout=15000)
    expect(page.locator('[data-agent="ai_ethics"][data-status="done"]')).to_be_visible(timeout=15000)
    expect(page.locator('[data-agent="ai_ethics"]').get_by_text(re.compile("no source|No .*source", re.I)).first).to_be_visible()


def test_audit_filters(page: Page):
    page.goto(BASE + "/audit")
    expect(page.locator("li[data-audit]").first).to_be_visible()
    page.get_by_label("Result").select_option("no_source")
    page.wait_for_timeout(800)
    texts = page.locator("li[data-audit] > button").all_inner_texts()
    assert all("no_source" in t for t in texts)
    page.get_by_label("Result").select_option("")
    page.get_by_label("Agent").select_option("coordinator")
    page.wait_for_timeout(800)
    texts = page.locator("li[data-audit] > button").all_inner_texts()
    assert texts and all("coordinator" in t for t in texts)
