import pandas as pd
from IPython.core.interactiveshell import InteractiveShell

import nbboost
from nbboost import _shell


def test_install_methods_adds_display_to_pandas(monkeypatch):
    monkeypatch.delattr(pd.DataFrame, "display", raising=False)
    nbboost.install_methods()
    assert pd.DataFrame.display is _shell._display_method
    nbboost.install_methods()  # idempotent
    assert pd.DataFrame.display is _shell._display_method


def test_existing_display_attribute_is_not_overwritten(monkeypatch):
    sentinel = lambda self: "mine"  # noqa: E731
    monkeypatch.setattr(pd.Series, "display", sentinel, raising=False)
    nbboost.install_methods()
    assert pd.Series.display is sentinel


def test_method_passes_limit(monkeypatch):
    seen = {}
    monkeypatch.setattr(_shell, "display", lambda obj, limit=None: seen.update(limit=limit))
    _shell._display_method(pd.DataFrame({"a": [1]}), limit=7)
    assert seen["limit"] == 7


def test_load_registers_everything_and_is_repeatable():
    ip = InteractiveShell.instance()
    nbboost.load()
    nbboost.load()
    assert ip.user_ns["display"] is nbboost.display and ip.user_ns["show_html"] is nbboost.show_html
    assert "sql" in ip.magics_manager.magics["line"] and "sql" in ip.magics_manager.magics["cell"]
    assert ip.events.callbacks["pre_run_cell"].count(_shell._pre_run_cell) == 1


def test_load_can_skip_the_sql_magic():
    ip = InteractiveShell.instance()
    ip.magics_manager.magics["line"].pop("sql", None)
    ip.magics_manager.magics["cell"].pop("sql", None)
    nbboost.load(sql_magic=False)
    assert "sql" not in ip.magics_manager.magics["line"]


def test_load_wires_new_features_and_flags_turn_them_off():
    ip = InteractiveShell.instance()
    nbboost.load()
    assert ip.user_ns["nbutils"] is nbboost.nbutils
    for k in ("fs", "md", "sh"):
        assert k in ip.magics_manager.magics["line"]
    assert ip.events.callbacks["pre_run_cell"].count(_shell._before_cell) == 1
    assert ip.events.callbacks["post_run_cell"].count(_shell.runtime.after_cell) == 1
    assert hasattr(ip, "_nbboost_orig_showtraceback")
    nbboost.load(timing=False, progress=False, errors_=False)
    assert _shell._before_cell not in ip.events.callbacks["pre_run_cell"]
    assert _shell.runtime.after_cell not in ip.events.callbacks["post_run_cell"]
    assert not hasattr(ip, "_nbboost_orig_showtraceback")
    nbboost.load()
