"""``nbutils.data`` -- ``summarize(df)`` opens the column profile; ``explain`` shows query plans."""
from __future__ import annotations

from ._display import DEFAULT_LIMIT, _is_pandas, _is_pandas_on_spark, _is_spark_df, _pandas_payload, _render, _spark_payload


class Data:
    def summarize(self, df, limit: int | None = DEFAULT_LIMIT) -> None:
        """Show ``df`` with the Data profile tab open (statistics of the first ``limit`` rows)."""
        if _is_pandas_on_spark(df):
            df = df.to_spark()
        if _is_spark_df(df):
            p = _spark_payload(df, limit)
        elif _is_pandas(df):
            p = _pandas_payload(df, limit)
        else:
            raise TypeError(f"summarize() needs a Spark or pandas DataFrame, not {type(df).__name__}")
        p["openTab"] = "profile"
        _render(p)

    def explain(self, df_or_sql, mode: str = "extended", spark=None) -> None:
        """Show a DataFrame's (or SQL statement's) query plan as a collapsible tree."""
        from .plan import explain
        explain(df_or_sql, mode=mode, spark=spark)


data = Data()
