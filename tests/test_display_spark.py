import json
import re

import pytest

pyspark = pytest.importorskip("pyspark")

import nbboost
from conftest import html_of


@pytest.fixture(scope="module")
def spark():
    from pyspark.sql import SparkSession

    s = SparkSession.builder.master("local[1]").config("spark.ui.enabled", "false").getOrCreate()
    yield s
    s.stop()


def payload_of(item):
    return json.loads(re.search(r'<script type="application/json" id="[^"]+-data">(.*?)</script>', html_of(item), re.S).group(1))


def test_spark_types_and_complex_values(spark, shown):
    df = spark.sql("select 1 as i, 'x' as s, array(1, 2) as a, named_struct('k', 1) as st, date'2026-01-02' as d, cast(1.5 as decimal(10,2)) as dec")
    nbboost.display(df)
    p = payload_of(shown[0])
    kinds = {c["name"]: c["kind"] for c in p["columns"]}
    assert kinds["i"] == "int" and kinds["s"] == "string" and kinds["a"] == "complex" and kinds["d"] == "date" and kinds["dec"] == "decimal"
    assert json.loads(p["rows"][0][2]) == [1, 2]


def test_spark_limit_marks_truncated(spark, shown):
    nbboost.display(spark.range(100), limit=10)
    p = payload_of(shown[0])
    assert len(p["rows"]) == 10 and p["truncated"] is True


def test_df_display_method(spark, shown):
    nbboost.install_methods()
    spark.range(3).display()
    assert len(payload_of(shown[0])["rows"]) == 3


def test_command_result_without_columns(spark, shown):
    nbboost.display(spark.sql("create or replace temp view tv as select 1"))
    assert payload_of(shown[0])["columns"] == []


def test_real_spark_error_is_not_logged_as_json_when_muted(spark, monkeypatch):
    from pyspark.errors.exceptions.base import PySparkException
    from pyspark.logger import PySparkLogger

    from nbboost import errors

    def boom(*a, **k):
        raise AssertionError("PySpark tried to log the error")

    monkeypatch.setattr(PySparkLogger, "getLogger", staticmethod(boom))
    assert errors.mute_pyspark_logging()
    try:
        with pytest.raises(PySparkException):
            spark.sql("select * from nope_tbl_xyz")
    finally:
        errors.unmute_pyspark_logging()
