"""Headless-browser smoke test: the widget must render, sort, and raise no JS errors.

Skipped automatically when Playwright or Chromium is unavailable.
Run only these with:  pytest -m browser
"""
import pandas as pd
import pytest

import nbboost
from conftest import html_of

pytestmark = pytest.mark.browser
sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # browser binary not installed
            pytest.skip(f"chromium unavailable: {e}")
        yield b
        b.close()


def render_page(browser, shown, df):
    nbboost.display(df)
    page = browser.new_page(viewport={"width": 1100, "height": 700})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.set_content(f"<!doctype html><html><body>{html_of(shown[0])}</body></html>")
    page.wait_for_selector(".nbb-row", timeout=5000)
    return page, errors


def test_table_renders_rows_and_no_js_errors(browser, shown):
    df = pd.DataFrame({"id": range(1, 101), "name": [f"n{i}" for i in range(100)], "v": [i * 1.5 for i in range(100)]})
    page, errors = render_page(browser, shown, df)
    assert page.locator(".nbb-row").count() > 5      # virtualized: only visible rows exist
    text = page.locator(".nbb-root").inner_text()
    assert "name" in text and "n0" in text
    assert errors == []
    page.close()


def test_scroll_renders_later_rows(browser, shown):
    page, errors = render_page(browser, shown, pd.DataFrame({"id": range(1, 2001)}))
    page.locator(".nbb-scroll").evaluate("e => { e.scrollTop = e.scrollHeight; }")
    page.wait_for_function("document.querySelector('.nbb-root').innerText.includes('2000')", timeout=5000)
    assert errors == []
    page.close()


def test_empty_and_null_values_render(browser, shown):
    page, errors = render_page(browser, shown, pd.DataFrame({"a": [None, 1.0], "b": ["x", None]}))
    assert page.locator(".nbb-row").count() >= 2  # data rows (+ header)
    assert errors == []
    page.close()


def test_spark_jobs_block_keeps_open_state_across_updates(browser):
    from types import SimpleNamespace as NS

    from nbboost import runtime

    S = lambda i, n, d, f=False: NS(stage_id=i, num_tasks=n, num_completed_tasks=d, num_bytes_read=0, done=f)  # noqa: E731
    outs, clock = [], NS(t=0.0)

    class H:
        def update(self, o):
            outs.append(o.data)

    bar = runtime.ProgressBar(display=lambda o, display_id=False: (outs.append(o.data), H())[1], clock=lambda: clock.t)
    bar([S(1, 10, 0)], 2, "q", False)
    clock.t = 1.0
    bar([S(1, 10, 4)], 2, "q", False)
    clock.t = 2.0
    bar(None, 0, "q", True)
    # render the way JupyterLab does: replace the output HTML and run its scripts
    render = """(h)=>{const c=document.getElementById('out');c.innerHTML=h;
      c.querySelectorAll('script').forEach(s=>{const n=document.createElement('script');n.textContent=s.textContent;s.replaceWith(n);});}"""
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content("<!doctype html><html><body><div id='out'></div></body></html>")
    page.evaluate(render, outs[0])
    assert page.evaluate("document.querySelector('details.nbb-jobs').open") is False   # collapsed by default
    page.click("details.nbb-jobs > summary")
    page.evaluate(render, outs[-1])
    assert page.evaluate("document.querySelector('details.nbb-jobs').open") is True    # stays open
    assert "1 query" in page.inner_text("details.nbb-jobs > summary")
    assert errors == []
    page.close()


def test_summarize_opens_profile_tab(browser, shown):
    from nbboost.nbutils import nbutils
    nbutils.data.summarize(pd.DataFrame({"x": [1, 2, 3], "s": ["a", "b", None]}))
    page = browser.new_page(viewport={"width": 1100, "height": 700})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(f"<!doctype html><html><body>{html_of(shown[0])}</body></html>")
    page.wait_for_selector(".nbb-root .nbb-tabs", timeout=5000)
    page.wait_for_function("document.querySelector('.nbb-root').innerText.includes('Profile of')", timeout=5000)
    assert errors == []
    page.close()
