from types import SimpleNamespace as NS

import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import completion
from nbboost.catalog import Catalog, Rows
from nbboost.completion import analyze, suggest


class FakeCatalogAPI:
    calls = 0

    def __init__(self):
        self.dbs = {"default": ["people", "orders"], "jobs_ingest_prod": ["jobs_raw", "jobs_scored"]}
        self.cols = {"people": ["id", "name", "city"], "orders": ["order_id", "person_id", "amount"],
                     "jobs_ingest_prod.jobs_raw": ["job_id", "title", "company"]}

    def listDatabases(self):
        FakeCatalogAPI.calls += 1
        return [NS(name=d) for d in self.dbs]

    def currentDatabase(self):
        return "default"

    def listTables(self, db=None):
        return [NS(name=t) for t in self.dbs[db or "default"]]

    def listColumns(self, table):
        return [NS(name=c) for c in self.cols[table]]


@pytest.fixture
def cat():
    sp = NS(catalog=FakeCatalogAPI())
    return Catalog(lambda: sp)


def run(cat, cell, cursor=None):
    lines = cell.split("\n")
    if cursor is None:
        cursor = (len(lines) - 1, len(lines[-1]))
    res = analyze(cell, *cursor)
    if res is None:
        return None
    frag, items = suggest(*res, cat)
    return frag, [t for t, _ in items]


def test_tables_after_from_in_sql_cell(cat):
    frag, items = run(cat, "%%sql\nselect * from pe")
    assert frag == "pe" and items == ["people"]


def test_databases_and_tables_on_empty_fragment(cat):
    _, items = run(cat, "%%sql\nselect * from ")
    assert "jobs_ingest_prod." in items and "people" in items


def test_qualified_table(cat):
    frag, items = run(cat, "%%sql\nselect * from jobs_ingest_prod.jo")
    assert frag == "jobs_ingest_prod.jo" and items == ["jobs_ingest_prod.jobs_raw", "jobs_ingest_prod.jobs_scored"]


def test_three_part_names(cat):
    _, items = run(cat, "%%sql\nselect * from spark_catalog.jo")
    assert items == ["spark_catalog.jobs_ingest_prod."]
    _, items = run(cat, "%%sql\nselect * from spark_catalog.jobs_ingest_prod.jobs_r")
    assert items == ["spark_catalog.jobs_ingest_prod.jobs_raw"]


def test_columns_use_tables_from_the_whole_cell(cat):
    cell = "%%sql\nselect na\nfrom people p join orders o on p.id = o.person_id"
    frag, items = run(cat, cell, (1, len("select na")))
    assert frag == "na" and items == ["name"]


def test_alias_dot_columns(cat):
    cell = "%%sql\nselect o.am\nfrom people p join orders o on p.id = o.person_id"
    frag, items = run(cat, cell, (1, len("select o.am")))
    assert frag == "o.am" and items == ["o.amount"]


def test_qualified_table_columns(cat):
    _, items = run(cat, "%%sql\nselect ti from jobs_ingest_prod.jobs_raw", (1, len("select ti")))
    assert items == ["title"]


def test_use_and_show_tables_suggest_databases(cat):
    assert run(cat, "%%sql\nuse jo")[1] == ["jobs_ingest_prod"]
    assert run(cat, "%%sql\nshow tables in de")[1] == ["default"]


def test_no_completion_inside_string_literal_or_options_line(cat):
    assert run(cat, "%%sql\nselect * from people where name = 'pe")[1] == []
    assert run(cat, "%%sql --limit 5", (0, 10)) is None


def test_python_contexts(cat):
    assert run(cat, 'df = spark.table("jobs_ingest_prod.jo')[1] == ["jobs_ingest_prod.jobs_raw", "jobs_ingest_prod.jobs_scored"]
    assert run(cat, "df.write.saveAsTable('or")[1] == ["orders"]
    assert run(cat, 'spark.sql("select * from peo')[1] == ["people"]
    assert run(cat, 'spark.sql(f"""\nselect *\nfrom jobs_ingest_prod.jobs_r')[1] == ["jobs_ingest_prod.jobs_raw"]
    assert run(cat, "%sql select * from ord")[1] == ["orders"]
    assert run(cat, "x = 1 + pe") is None
    assert run(cat, 'spark.sql("select 1").show()') is None


def test_lookups_are_cached(cat):
    FakeCatalogAPI.calls = 0
    run(cat, "%%sql\nselect * from ")
    run(cat, "%%sql\nselect * from ")
    assert FakeCatalogAPI.calls == 1
    cat.refresh()
    run(cat, "%%sql\nselect * from ")
    assert FakeCatalogAPI.calls == 2


def test_no_spark_session_means_no_suggestions():
    c = Catalog(lambda: None)
    assert run(c, "%%sql\nselect * from pe")[1] == []


def test_slow_catalog_times_out_quickly(monkeypatch):
    import time
    import nbboost.catalog as C
    monkeypatch.setattr(C, "TIMEOUT", 0.2)

    class Slow(FakeCatalogAPI):
        def listDatabases(self):
            time.sleep(2)
            return []

    c = Catalog(lambda: NS(catalog=Slow()))
    t0 = time.time()
    run(c, "%%sql\nuse x")
    assert time.time() - t0 < 1.0


def test_listing_renders_html():
    from collections import namedtuple
    Db = namedtuple("Db", "name description")
    sp = NS(catalog=NS(listDatabases=lambda: [Db("jobs<x>", None)]))
    rows = Catalog(lambda: sp).databases()
    assert isinstance(rows, Rows)
    h = rows._repr_html_()
    assert "<th" in h and "jobs&lt;x&gt;" in h and "1 item(s)" in h


def test_end_to_end_through_ipython_completer(monkeypatch):
    sp = NS(catalog=FakeCatalogAPI())
    c = Catalog(lambda: sp)
    ip = InteractiveShell.instance()
    monkeypatch.setattr(completion, "_default_catalog", c)
    completion.install(ip)
    try:
        text = "%%sql\nselect * from jobs_ingest_prod.jobs_r"
        from IPython.core.completer import provisionalcompleter
        with provisionalcompleter():
            comps = list(ip.Completer.completions(text, len(text)))
        texts = [x.text for x in comps]
        assert "jobs_ingest_prod.jobs_raw" in texts
        hit = comps[texts.index("jobs_ingest_prod.jobs_raw")]
        assert text[:hit.start] + hit.text == "%%sql\nselect * from jobs_ingest_prod.jobs_raw"
        completion.install(ip)   # idempotent
        assert sum(getattr(m, "matcher_identifier", "") == "nbboost.catalog" for m in ip.Completer.custom_matchers) == 1
    finally:
        completion.uninstall(ip)
    assert not any(getattr(m, "matcher_identifier", "") == "nbboost.catalog" for m in ip.Completer.custom_matchers)


def test_ddl_cells_refresh_the_cache(monkeypatch):
    called = []
    monkeypatch.setattr(completion._default_catalog, "refresh", lambda: called.append(1))
    completion._post_run_cell(NS(info=NS(raw_cell="%%sql\ncreate table x (a int)")))
    completion._post_run_cell(NS(info=NS(raw_cell="select 1")))
    assert called == [1]
