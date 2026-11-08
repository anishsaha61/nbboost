"""End-to-end test of the JupyterLab extension in a real JupyterLab (skipped if JupyterLab,
Playwright/Chromium or the installed extension are missing). Run with:  pytest -m jupyterlab
"""
import json
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

pytestmark = pytest.mark.jupyterlab
pytest.importorskip("jupyterlab")
sync_api = pytest.importorskip("playwright.sync_api")
nbformat = pytest.importorskip("nbformat")


def _extension_installed():
    out = subprocess.run([sys.executable, "-m", "jupyter", "labextension", "list"],
                         capture_output=True, text=True).stdout + \
        subprocess.run([sys.executable, "-m", "jupyter", "labextension", "list"],
                       capture_output=True, text=True).stderr
    return any(line.strip().startswith("nbboost") and "enabled" in line for line in out.splitlines())


if not _extension_installed():
    pytest.skip("nbboost labextension is not installed in this environment", allow_module_level=True)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def lab(tmp_path_factory):
    root = tmp_path_factory.mktemp("lab")
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell("# Demo"),
        nbformat.v4.new_code_cell("import nbboost\nnbboost.load()"),
        nbformat.v4.new_code_cell("x = 21\nprint('first', x)"),
        nbformat.v4.new_code_cell("y = x * 2\nprint('second', y)"),
        nbformat.v4.new_code_cell("print('third', y + 1)"),
    ]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbformat.write(nb, str(root / "demo.ipynb"))
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "jupyter", "lab", "--no-browser", f"--port={port}", "--ServerApp.token=",
         "--ServerApp.password=", "--ServerApp.disable_check_xsrf=True", f"--ServerApp.root_dir={root}",
         "--LabApp.expose_app_in_browser=True", "--allow-root"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url + "/lab", timeout=2)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.skip("JupyterLab did not start")
    yield url
    proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def page(lab):
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:
            pytest.skip(f"chromium unavailable: {e}")
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.goto(lab + "/lab/tree/demo.ipynb")
        pg.wait_for_selector(".jp-Notebook .nbb-run", state="attached", timeout=90000)
        pg.wait_for_timeout(500)
        yield pg
        b.close()


def cells(pg):
    return pg.evaluate("""() => window.jupyterapp.shell.currentWidget.content.widgets
        .map(c => [c.model.type, c.model.sharedModel.getSource()])""")


def outputs(pg):
    return pg.evaluate("""() => Array.from(document.querySelectorAll('.jp-CodeCell'))
        .map(c => c.querySelector('.jp-OutputArea').innerText.trim())""")


def test_controls_are_added(page):
    n = len(cells(page))
    assert page.locator(".jp-Cell > .nbb-insert:not(.nbb-insert-top)").count() == n
    assert page.locator(".jp-Cell > .nbb-insert-top").count() == 1
    assert page.locator(".jp-Cell > .nbb-run").count() == n
    assert page.locator(".jp-NotebookPanel-toolbar .nbb-tb-runall").count() == 1
    assert page.errors == []


def test_insert_sql_markdown_and_code(page):
    bars = page.locator(".jp-Cell > .nbb-insert:not(.nbb-insert-top)")
    bars.nth(1).hover()
    bars.nth(1).locator("button[data-kind='sql']").click()
    page.wait_for_timeout(400)
    assert page.evaluate("window.jupyterapp.shell.currentWidget.content.mode") == "edit"
    page.keyboard.type("select 1")
    page.wait_for_timeout(200)
    page.keyboard.press("Escape")
    got = cells(page)
    assert got[2] == ["code", "%%sql\nselect 1"]          # right below cell 2, cursor on line 2

    bars = page.locator(".jp-Cell > .nbb-insert:not(.nbb-insert-top)")
    bars.last.hover()
    bars.last.locator("button[data-kind='markdown']").click()
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    page.locator(".nbb-insert-top").hover()
    page.locator(".nbb-insert-top button[data-kind='code']").click()
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    kinds = [k for k, _ in cells(page)]
    assert kinds[0] == "code" and kinds[-1] == "markdown" and len(kinds) == 8
    assert page.locator(".jp-Cell > .nbb-insert-top").count() == 1   # only on the (new) first cell
    assert page.errors == []


def test_run_menu_and_run_all(page):
    third = page.locator(".jp-Cell").filter(has_text="print('third'")
    third.hover()
    third.locator(".nbb-run-more").click()
    assert page.locator(".nbb-run-menu button").all_inner_texts() == [
        "Run cell", "Run all above", "Run this and all below"]
    third.locator(".nbb-run-menu button[data-mode='above']").click()
    page.wait_for_function(
        "() => Array.from(document.querySelectorAll('.jp-OutputArea-output')).some(e => e.innerText.includes('second 42'))",
        timeout=90000)
    page.wait_for_timeout(500)
    assert outputs(page)[-1] == ""                         # 'run all above' does not run the cell itself
    assert page.locator(".nbb-run-menu").count() == 0       # menu closed
    third.hover()
    third.locator(".nbb-run-play").click()
    page.wait_for_function(
        "() => Array.from(document.querySelectorAll('.jp-OutputArea-output')).some(e => e.innerText.includes('third 43'))",
        timeout=90000)
    page.locator(".nbb-tb-runall").click()
    page.wait_for_timeout(1500)
    assert page.errors == []
