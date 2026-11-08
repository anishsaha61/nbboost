import json
import re

import pandas as pd
import pytest

import nbboost
from nbboost import _display as disp
from conftest import html_of


def payload_of(item):
    m = re.search(r'<script type="application/json" id="[^"]+-data">(.*?)</script>', html_of(item), re.S)
    assert m, "no data script in output"
    return json.loads(m.group(1))


def test_dataframe_renders_widget_and_payload(shown):
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", None, "c"], "ok": [True, False, True]})
    nbboost.display(df)
    assert len(shown) == 1
    out = html_of(shown[0])
    assert 'class="nbb-root"' in out and "<style>" in out
    p = payload_of(shown[0])
    assert [c["name"] for c in p["columns"]] == ["id", "name", "ok"]
    assert [c["kind"] for c in p["columns"]] == ["int", "string", "bool"]
    assert p["rows"][1][1] is None
    assert p["truncated"] is False


def test_static_fallback_table_is_present(shown):
    nbboost.display(pd.DataFrame({"x": [1]}))
    assert "<table class='nbb-static'>" in html_of(shown[0])


def test_limit_truncates_and_flags(shown):
    nbboost.display(pd.DataFrame({"x": range(50)}), limit=10)
    p = payload_of(shown[0])
    assert len(p["rows"]) == 10 and p["truncated"] is True and p["limit"] == 10


def test_series_is_shown_as_one_column_table(shown):
    nbboost.display(pd.Series([1, 2], name="s"))
    assert [c["name"] for c in payload_of(shown[0])["columns"]] == ["s"]


def test_nan_and_special_values_are_valid_json(shown):
    nbboost.display(pd.DataFrame({"f": [1.5, float("nan"), float("inf")], "t": pd.to_datetime(["2026-01-01", None, "2026-01-03"])}))
    payload_of(shown[0])  # json.loads would raise on NaN/Infinity


def test_html_in_cells_is_not_injected(shown):
    nbboost.display(pd.DataFrame({"x": ["<script>alert(1)</script>"]}))
    out = html_of(shown[0])
    assert "<script>alert(1)</script>" not in out


def test_non_dataframe_falls_through(shown):
    nbboost.display("hello", 42)
    assert shown == ["hello", 42]


def test_show_html(shown):
    nbboost.show_html("<b>x</b>")
    assert html_of(shown[0]) == "<b>x</b>"


def test_cell_key_counts_displays_within_one_cell(shown, monkeypatch):
    monkeypatch.setattr(disp, "_SEQ", {"msg": None, "n": 0})
    cols = [{"name": "a", "type": "int"}]
    k1, k2 = disp._cell_key(cols), disp._cell_key(cols)
    assert k1 != k2 and k1.endswith("#0") and k2.endswith("#1")


def test_summarize_opens_profile_tab(shown):
    from nbboost.nbutils import nbutils
    nbutils.data.summarize(pd.DataFrame({"a": [1, 2]}))
    assert payload_of(shown[0])["openTab"] == "profile"


def test_summarize_rejects_other_objects():
    from nbboost.nbutils import nbutils
    with pytest.raises(TypeError):
        nbutils.data.summarize([1, 2])
