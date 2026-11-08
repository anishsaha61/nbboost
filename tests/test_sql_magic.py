import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import sqlmagic
from nbboost.sqlmagic import split_sql


@pytest.mark.parametrize(
    "text, expected",
    [
        ("select 1", ["select 1"]),
        ("select 1; select 2;", ["select 1", "select 2"]),
        ("select 'a;b' as x; select 2", ["select 'a;b' as x", "select 2"]),
        ('select "a;b"', ['select "a;b"']),
        ("select `a;b` from t", ["select `a;b` from t"]),
        ("select 1 -- ; comment\n; select 2", ["select 1 \n", "select 2"]),
        ("select /* ; */ 1; select 2", ["select  1", "select 2"]),
        ("  ;  ; ", []),
        ("select 'it\\'s; ok'", ["select 'it\\'s; ok'"]),
    ],
)
def test_split_sql(text, expected):
    assert [s.strip() for s in split_sql(text)] == [e.strip() for e in expected]


class FakeSpark:
    def __init__(self):
        self.ran = []

    def sql(self, q):
        self.ran.append(q)
        return f"result-of:{q}"


@pytest.fixture
def shell(monkeypatch):
    ip = InteractiveShell.instance()
    spark = FakeSpark()
    ip.user_ns["spark"] = spark
    shown = []
    monkeypatch.setattr(sqlmagic, "display", lambda obj, limit=None: shown.append((obj, limit)))
    sqlmagic.register(ip)
    yield ip, spark, shown
    ip.user_ns.pop("spark", None)
    ip.user_ns.pop("_sql_df", None)


def test_cell_magic_runs_all_statements_and_shows_last(shell):
    ip, spark, shown = shell
    ip.run_cell_magic("sql", "", "create view v as select 1; select * from v;")
    assert spark.ran == ["create view v as select 1", "select * from v"]
    assert [s[0] for s in shown] == ["result-of:select * from v"]
    assert ip.user_ns["_sql_df"] == "result-of:select * from v"


def test_line_magic(shell):
    ip, spark, shown = shell
    ip.run_line_magic("sql", "select 2")
    assert spark.ran == ["select 2"]


def test_limit_option(shell):
    ip, _, shown = shell
    ip.run_cell_magic("sql", "--limit 5", "select 1")
    ip.run_cell_magic("sql", "--limit all", "select 1")
    assert [s[1] for s in shown] == [5, None]


def test_missing_spark_session_is_reported_not_raised(shell, capsys):
    ip, _, shown = shell
    ip.user_ns.pop("spark")
    ip.run_cell_magic("sql", "", "select 1")
    assert "spark" in capsys.readouterr().out and shown == []


def test_empty_cell_does_nothing(shell):
    ip, spark, shown = shell
    ip.run_cell_magic("sql", "", "  ;  -- nothing\n")
    assert spark.ran == [] and shown == []
