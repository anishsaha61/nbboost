import pytest

from nbboost import plan

EXTENDED = """== Parsed Logical Plan ==
'Sort ['g ASC NULLS FIRST], true
+- Aggregate [g#1L], [g#1L, count(1) AS count#5L]
   +- Join Inner, (g#1L = k#3L)
      :- Project [id#0L]
      :  +- Range (0, 100, step=1, splits=Some(1))
      +- Project [id#2L AS k#3L]
         +- Range (0, 10, step=1, splits=Some(1))

== Analyzed Logical Plan ==
g: bigint, count: bigint
Sort [g#1L ASC NULLS FIRST], true
+- LocalRelation <empty>, [g#1L]

== Physical Plan ==
AdaptiveSparkPlan isFinalPlan=false
+- Sort [g#1L ASC NULLS FIRST], true, 0
   +- BroadcastHashJoin [g#1L], [k#3L], Inner, BuildRight, false, false
      :- Project [(id#0L % 3) AS g#1L]
      :  +- Range (0, 100, step=1, splits=1)
      +- BroadcastExchange HashedRelationBroadcastMode(List(input[0, bigint, false]),false), [plan_id=39]
         +- Exchange hashpartitioning(k#3L, 200), ENSURE_REQUIREMENTS, [plan_id=40]
            +- Range (0, 10, step=1, splits=1)
"""

FORMATTED = """== Physical Plan ==
AdaptiveSparkPlan (3)
+- Project (2)
   +- Range (1)


(1) Range
Output [1]: [id#0L]

(2) Project
Output [1]: [g#1L]

(3) AdaptiveSparkPlan
Arguments: isFinalPlan=false
"""


def test_split_sections():
    titles = [t for t, _ in plan.split_sections(EXTENDED)]
    assert titles == ["Parsed Logical Plan", "Analyzed Logical Plan", "Physical Plan"]
    assert plan.split_sections("just text") == [("Plan", "just text")]


def test_parse_tree_shape():
    body = dict(plan.split_sections(EXTENDED))["Parsed Logical Plan"]
    (root,) = plan.parse_tree(body)
    agg = root["children"][0]
    join = agg["children"][0]
    assert root["text"].startswith("'Sort") and agg["text"].startswith("Aggregate")
    assert [c["text"].split()[0] for c in join["children"]] == ["Project", "Project"]
    assert join["children"][0]["children"][0]["text"].startswith("Range (0, 100")
    assert join["children"][1]["children"][0]["text"].startswith("Range (0, 10,")


def test_render_html():
    h = plan.render(EXTENDED)
    assert h.count("<details") >= 4
    assert "Output: g: bigint, count: bigint" in h          # analyzed schema shown as a caption
    assert ">broadcast join<" in h and ">broadcast<" in h and ">shuffle<" in h
    assert "<details open><summary>Physical Plan" in h
    assert "Raw text" in h


def test_render_escapes():
    assert "<script>" not in plan.render("Project [<script>]")


def test_formatted_mode_attaches_details():
    h = plan.render(FORMATTED)
    assert "Range (1)" in h and "Output [1]: [id#0L]" in h
    assert h.index("Project (2)") < h.index("Output [1]: [g#1L]")


def test_bad_mode():
    with pytest.raises(ValueError):
        plan.plan_text(object(), mode="nope")


class FakeDF:
    def explain(self, mode):
        print("== Physical Plan ==\n*(1) Project [1 AS x]\n+- *(1) Scan OneRowRelation[]")


def test_plan_text_from_dataframe_and_display(monkeypatch):
    shown = []
    monkeypatch.setattr(plan, "_ipy_display", lambda o, **k: shown.append(o.data))
    plan.explain(FakeDF())
    assert ">scan<" in shown[0] and "Project [1 AS x]" in shown[0]


class FakeSpark:
    def __init__(self):
        self.q = None

    def sql(self, q, args=None):
        self.q = (q, args)

        class R:
            def collect(self_inner):
                return [("== Physical Plan ==\nLocalTableScan [x]",)]
        return R()


def test_sql_string_is_explained_not_executed():
    sp = FakeSpark()
    txt = plan.plan_text("insert into t select 1", mode="formatted", spark=sp)
    assert sp.q == ("EXPLAIN FORMATTED insert into t select 1", None)
    assert "LocalTableScan" in txt


def test_sql_magic_explain_runs_setup_statements_and_explains_the_last(monkeypatch):
    from IPython.core.interactiveshell import InteractiveShell
    from nbboost import sqlmagic

    ran, explained = [], []

    class Sp:
        def sql(self, q, args=None):
            ran.append(q)

    ip = InteractiveShell.instance()
    ip.user_ns["spark"] = Sp()
    monkeypatch.setattr(plan, "explain", lambda q, mode, spark: explained.append((q, mode)))
    sqlmagic.register(ip)
    try:
        ip.run_cell_magic("sql", "--explain formatted", "create temp view v as select 1; select * from v")
        ip.run_cell_magic("sql", "--explain", "select 2")
    finally:
        ip.user_ns.pop("spark", None)
    assert ran == ["create temp view v as select 1"]
    assert explained == [("select * from v", "formatted"), ("select 2", "extended")]
