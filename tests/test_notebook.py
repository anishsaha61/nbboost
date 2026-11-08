import os
import time

import nbformat
import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import errors
from nbboost.notebook import EXIT_ENV, Notebook, NotebookExit, NotebookRunError

pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")


def make_nb(tmp_path, name, *cells):
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell(c) for c in cells]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    p = tmp_path / name
    nbformat.write(nb, str(p))
    return str(p)


def test_run_passes_arguments_and_returns_exit_value(tmp_path):
    child = make_nb(
        tmp_path, "child.ipynb",
        "from nbboost import nbutils\nnbutils.widgets.text('n', '1')",
        "n = int(nbutils.widgets.get('n'))",
        "nbutils.notebook.exit(n * 2)",
        "raise RuntimeError('cells after exit must not run')",
    )
    out = tmp_path / "out.ipynb"
    assert Notebook().run(child, 120, {"n": 21}, output_path=str(out)) == "42"
    assert out.exists()


def test_run_without_exit_returns_none_and_finds_file_without_suffix(tmp_path):
    child = make_nb(tmp_path, "plain.ipynb", "x = 1")
    assert Notebook().run(str(tmp_path / "plain"), 120) is None


def test_child_runs_in_its_own_directory(tmp_path):
    (tmp_path / "data.txt").write_text("hello")
    child = make_nb(tmp_path, "c.ipynb",
                    "from nbboost import nbutils\nnbutils.notebook.exit(open('data.txt').read())")
    cwd = os.getcwd()
    os.chdir("/")
    try:
        assert Notebook().run(child, 120) == "hello"
    finally:
        os.chdir(cwd)


def test_failure_names_cell_and_error(tmp_path):
    child = make_nb(tmp_path, "bad.ipynb", "x = 1", "1/0")
    with pytest.raises(NotebookRunError, match=r"cell 2: ZeroDivisionError"):
        Notebook().run(child, 120)


def test_timeout_stops_the_child(tmp_path):
    child = make_nb(tmp_path, "slow.ipynb", "import time\ntime.sleep(60)")
    t0 = time.time()
    with pytest.raises(TimeoutError):
        Notebook().run(child, 5)
    assert time.time() - t0 < 40


def test_missing_notebook(tmp_path):
    with pytest.raises(FileNotFoundError):
        Notebook().run(str(tmp_path / "nope.ipynb"))


def test_exit_outside_run_raises_and_writes_nothing(monkeypatch):
    monkeypatch.delenv(EXIT_ENV, raising=False)
    with pytest.raises(NotebookExit) as e:
        Notebook().exit(5)
    assert e.value.value == "5"


def test_interactive_exit_shows_a_message_not_a_traceback(monkeypatch, capsys):
    ip = InteractiveShell.instance()
    errors.uninstall(ip)
    errors.install(ip)
    shown = []
    import nbboost.notebook as nbmod
    monkeypatch.setattr(nbmod, "_ipy_display", lambda o, **k: shown.append(o.data))
    try:
        ip.run_cell("from nbboost.notebook import Notebook\nNotebook().exit('done')")
    finally:
        errors.uninstall(ip)
    assert len(shown) == 1 and "Notebook exited" in shown[0] and "done" in shown[0]
    assert "Traceback" not in capsys.readouterr().out
