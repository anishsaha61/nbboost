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
