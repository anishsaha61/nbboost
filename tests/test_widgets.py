import json

import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import sqlmagic, widgets as W
from nbboost.widgets import Widgets, sql_args, sql_param_names


@pytest.fixture
def w():
    shown = []
    ws = Widgets(display=lambda o, **k: shown.append(o))
    ws._shown = shown
    return ws


def test_text_get_and_live_update(w):
    w.text("country", "IN", "Country")
    assert w.get("country") == "IN"
    ctl = w._defs["country"]["control"]
    ctl.value = "US"                       # what typing in the box does
    assert w.get("country") == "US"
    assert ctl.description == "Country"


def test_dropdown_combobox_multiselect(w):
    w.dropdown("year", "2026", [2024, 2025, 2026])
    w.combobox("city", "Kolkata", ["Kolkata", "Pune"])
    w.multiselect("tags", "a,b", ["a", "b", "c"])
    assert w.get("year") == "2026" and w.get("city") == "Kolkata" and w.get("tags") == "a,b"
    w._defs["tags"]["control"].value = ("c",)
    assert w.get("tags") == "c"
    assert w.getAll() == {"year": "2026", "city": "Kolkata", "tags": "c"}


def test_validation(w):
    with pytest.raises(ValueError):
        w.dropdown("d", "x", ["a"])
    with pytest.raises(ValueError):
        w.multiselect("m", "a,z", ["a"])
    with pytest.raises(ValueError):
        w.dropdown("e", "a", [])
    with pytest.raises(ValueError):
        w.get("missing")


def test_rerunning_definition_keeps_user_choice(w):
    w.text("t", "default")
    w._defs["t"]["control"].value = "typed"
    w.text("t", "default")                 # cell re-run
    assert w.get("t") == "typed"
    w.dropdown("t", "a", ["a", "b"])        # different kind replaces it
    assert w.get("t") == "a"


def test_remove(w):
    w.text("a", "1"); w.text("b", "2")
    w.remove("a")
    assert w.getAll() == {"b": "2"}
    w.removeAll()
    assert w.getAll() == {}
    with pytest.raises(ValueError):
        w.remove("b")


def test_notebook_run_arguments_override(monkeypatch):
    monkeypatch.setenv(W.ARGS_ENV, json.dumps({"year": 2025, "extra": "x"}))
    ws = Widgets(display=lambda *a, **k: None)
    ws.dropdown("year", "2026", ["2025", "2026"])
    assert ws.get("year") == "2025" and ws.get("extra") == "x"
    assert ws._defs["year"]["control"].value == "2025"


def test_fallback_without_ipywidgets(w, monkeypatch):
    monkeypatch.setattr(W, "_ipywidgets", lambda: None)
    w.text("n", "<b>5</b>")
    assert w.get("n") == "<b>5</b>"
    assert "&lt;b&gt;5&lt;/b&gt;" in w._shown[-1].data


@pytest.mark.parametrize("sql, names", [
    ("select * from t where y = :year and c = :country", ["year", "country"]),
    ("select ':year' as s, x::int from t where a = :a", ["a"]),
    ("select 1 -- :nope\n, 2 /* :nope2 */ where b = :b", ["b"]),
    ("select `:x` from t where k = :k and k2 = :k", ["k"]),
    ("select 1", []),
])
def test_sql_param_names(sql, names):
    assert sql_param_names(sql) == names


def test_sql_args_only_for_known_widgets(w):
    w.text("year", "2026")
    assert sql_args("select :year, :other", w) == {"year": "2026"}


class FakeSpark:
    def __init__(self):
        self.calls = []

    def sql(self, q, args=None):
        self.calls.append((q, args))
        return f"df:{q}"


def test_sql_magic_binds_widget_parameters(monkeypatch):
    ip = InteractiveShell.instance()
    spark = FakeSpark()
    ip.user_ns["spark"] = spark
    monkeypatch.setattr(sqlmagic, "display", lambda *a, **k: None)
    monkeypatch.setattr(W, "widgets", Widgets(display=lambda *a, **k: None))
    W.widgets.text("year", "2026")
    sqlmagic.register(ip)
    try:
        ip.run_cell_magic("sql", "", "select * from t where y = :year; select 1")
    finally:
        ip.user_ns.pop("spark", None)
    assert spark.calls == [("select * from t where y = :year", {"year": "2026"}), ("select 1", None)]


def test_sql_magic_rejects_unknown_option(capsys):
    ip = InteractiveShell.instance()
    ip.user_ns["spark"] = FakeSpark()
    sqlmagic.register(ip)
    try:
        ip.run_cell_magic("sql", "--bogus", "select 1")
    finally:
        ip.user_ns.pop("spark", None)
    assert "unknown %%sql option" in capsys.readouterr().out
