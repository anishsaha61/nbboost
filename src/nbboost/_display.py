"""Interactive result tables and charts for Jupyter notebooks.

Builds a typed JSON payload from Spark (classic or Connect), pandas or pandas-on-Spark and renders it
as an HTML widget (vanilla JS/CSS from ``nbboost/assets``, no network access needed).
"""
from __future__ import annotations

import base64
import datetime as _dt
import decimal
import functools
import html as _html
import json
import math
import time
import uuid
from importlib import resources

from IPython import get_ipython
from IPython.display import HTML as _HTML
from IPython.display import display as _ipy_display

DEFAULT_LIMIT = 10_000
_STATIC_ROWS = 50


@functools.lru_cache(maxsize=None)
def _asset(name: str) -> str:
    return resources.files("nbboost").joinpath("assets", name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def display(*objs, limit: int | None = DEFAULT_LIMIT, **kwargs):
    """Show Spark / pandas DataFrames as an interactive table; pass everything else to IPython's display()."""
    for obj in objs:
        if _is_pandas_on_spark(obj):
            obj = obj.to_spark()
        if _is_spark_df(obj):
            if getattr(obj, "isStreaming", False):
                _ipy_display(_HTML(_notice(
                    "Streaming DataFrames aren't supported by this display(). "
                    "Write the stream to a memory/Delta sink and display that table.")))
                continue
            _render(_spark_payload(obj, limit))
        elif _is_pandas(obj):
            _render(_pandas_payload(obj, limit))
        else:
            _ipy_display(obj, **kwargs)


def show_html(html: str):
    """Render a raw HTML string in the cell output."""
    _ipy_display(_HTML(html))



# --------------------------------------------------------------------------- #
# Type detection
# --------------------------------------------------------------------------- #
def _is_spark_df(obj) -> bool:
    cls = type(obj)
    return cls.__name__ == "DataFrame" and cls.__module__.startswith("pyspark.sql")


def _is_pandas_on_spark(obj) -> bool:
    cls = type(obj)
    return cls.__module__.startswith("pyspark.pandas") and cls.__name__ in ("DataFrame", "Series")


def _is_pandas(obj) -> bool:
    cls = type(obj)
    return cls.__module__.startswith("pandas") and cls.__name__ in ("DataFrame", "Series")


def _spark_kind(dt):
    from pyspark.sql import types as T

    def has(name):
        t = getattr(T, name, None)
        return t is not None and isinstance(dt, t)

    if isinstance(dt, (T.ByteType, T.ShortType, T.IntegerType)):
        return "int", None
    if isinstance(dt, T.LongType):
        return "long", None
    if isinstance(dt, (T.FloatType, T.DoubleType)):
        return "float", None
    if isinstance(dt, T.DecimalType):
        return "decimal", None
    if isinstance(dt, T.BooleanType):
        return "bool", None
    if isinstance(dt, T.StringType) or has("CharType") or has("VarcharType"):
        return "string", None
    if isinstance(dt, T.DateType):
        return "date", None
    if has("TimestampNTZType"):
        return "timestamp_ntz", None
    if isinstance(dt, T.TimestampType):
        return "timestamp", None
    if isinstance(dt, T.BinaryType):
        return "binary", None
    if isinstance(dt, T.ArrayType):
        return "complex", "array"
    if isinstance(dt, T.MapType):
        return "complex", "map"
    if isinstance(dt, T.StructType):
        return "complex", "struct"
    if has("VariantType"):
        return "complex", "variant"
    return "other", None


# --------------------------------------------------------------------------- #
# Payload builders
# --------------------------------------------------------------------------- #
def _clean(v):
    if isinstance(v, float) and not math.isfinite(v):
        return "NaN" if math.isnan(v) else ("Infinity" if v > 0 else "-Infinity")
    return v


def _spark_payload(df, limit):
    from pyspark.sql import functions as F

    fields = df.schema.fields
    cols, kinds = [], []
    for f in fields:
        kind, sub = _spark_kind(f.dataType)
        kinds.append((kind, sub))
        cols.append({"name": f.name, "type": f.dataType.simpleString(), "kind": kind, "sub": sub})

    # Positional rename: survives duplicate names (joins), dots, backticks.
    renamed = df.toDF(*[f"c{i}" for i in range(len(fields))]) if fields else df

    def build(json_ok=True):
        exprs = []
        for i, (kind, sub) in enumerate(kinds):
            c = F.col(f"c{i}")
            if kind in ("int", "float", "bool"):
                e = c
            elif kind == "timestamp":
                e = F.date_format(c, "yyyy-MM-dd'T'HH:mm:ss.SSSxxx")
            elif kind == "timestamp_ntz":
                e = F.date_format(c, "yyyy-MM-dd'T'HH:mm:ss.SSS")
            elif kind == "binary":
                e = F.base64(c)
            elif kind == "complex" and sub != "variant" and json_ok:
                e = F.to_json(c)
            else:
                e = c.cast("string")
            exprs.append(e.alias(f"c{i}"))
        q = renamed.select(*exprs)
        return q.limit(limit + 1) if limit is not None else q

    t0 = time.time()
    if not fields:
        rows = []
    else:
        try:
            rows = build(True).collect()
        except Exception:
            rows = build(False).collect()      # e.g. to_json unsupported for a nested type
    elapsed = time.time() - t0

    truncated = limit is not None and len(rows) > limit
    if truncated:
        rows = rows[:limit]
    data = [[_clean(v) for v in r] for r in rows]
    return _payload(cols, data, truncated, limit, elapsed)


def _pandas_payload(pdf, limit):
    import pandas as pd
    from pandas.api import types as pt

    t0 = time.time()
    if isinstance(pdf, pd.Series):
        pdf = pdf.to_frame(name=pdf.name if pdf.name is not None else "value")
    if not isinstance(pdf.index, pd.RangeIndex):
        pdf = pdf.reset_index()
    truncated = limit is not None and len(pdf) > limit
    sub = pdf.head(limit) if limit is not None else pdf

    def isnull(v):
        if v is None:
            return True
        try:
            r = pd.isna(v)
            return bool(r) if isinstance(r, (bool,)) or type(r).__name__ == "bool_" else False
        except (TypeError, ValueError):
            return False

    cols, converters = [], []
    for name in sub.columns:
        s = sub[name]
        dt = s.dtype
        if pt.is_bool_dtype(dt):
            kind, conv = "bool", bool
        elif pt.is_integer_dtype(dt):
            kind, conv = "int", int
        elif pt.is_float_dtype(dt):
            kind, conv = "float", float
        elif pt.is_datetime64_any_dtype(dt):
            tz = getattr(dt, "tz", None) is not None
            kind = "timestamp" if tz else "timestamp_ntz"
            conv = lambda v: pd.Timestamp(v).isoformat(timespec="milliseconds")
        else:
            first = next((v for v in s if not isnull(v)), None)
            kind, conv = _py_kind(first)
        sub_kind = None
        if kind == "complex":
            sub_kind = "struct" if isinstance(first, dict) else "array"
        cols.append({"name": str(name), "type": str(dt), "kind": kind, "sub": sub_kind})
        converters.append(conv)

    data = []
    for row in sub.itertuples(index=False, name=None):
        out = []
        for v, conv in zip(row, converters):
            if isnull(v):
                out.append(None)
            else:
                try:
                    out.append(_clean(conv(v)))
                except Exception:
                    out.append(str(v))
        data.append(out)
    return _payload(cols, data, truncated, limit, time.time() - t0)


def _py_kind(v):
    if isinstance(v, bool):
        return "bool", bool
    if isinstance(v, int):
        return "int", int
    if isinstance(v, float):
        return "float", float
    if isinstance(v, decimal.Decimal):
        return "decimal", str
    if isinstance(v, _dt.datetime):
        return ("timestamp" if v.tzinfo else "timestamp_ntz"), lambda x: x.isoformat(timespec="milliseconds")
    if isinstance(v, _dt.date):
        return "date", lambda x: x.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return "binary", lambda x: base64.b64encode(bytes(x)).decode()
    if isinstance(v, (dict, list, tuple)) or type(v).__name__ == "ndarray":
        def to_json(x):
            if type(x).__name__ == "ndarray":
                x = x.tolist()
            return json.dumps(x, default=str, ensure_ascii=False)
        return "complex", to_json
    return "string", str


_SEQ = {"msg": None, "n": 0}


def _cell_key(cols):
    """Stable id for "this display() call in this cell", so saved visualizations survive re-runs."""
    cid = msg = None
    try:
        ip = get_ipython()
        parent = (ip.get_parent() if hasattr(ip, "get_parent") else ip.kernel.get_parent()) or {}
        cid = (parent.get("metadata") or {}).get("cellId")
        msg = (parent.get("header") or {}).get("msg_id")
    except Exception:
        pass
    if msg != _SEQ["msg"]:
        _SEQ["msg"], _SEQ["n"] = msg, 0
    n = _SEQ["n"]
    _SEQ["n"] += 1
    if cid:
        return f"{cid}#{n}"
    import hashlib
    sig = hashlib.md5("|".join(f"{c['name']}:{c['type']}" for c in cols).encode()).hexdigest()[:10]
    return f"sig-{sig}#{n}"


def _payload(cols, rows, truncated, limit, elapsed):
    return {
        "key": _cell_key(cols),
        "columns": cols,
        "rows": rows,
        "truncated": bool(truncated),
        "limit": limit,
        "elapsed": round(elapsed, 3),
        "generatedAt": int(time.time() * 1000),
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _notice(msg):
    return f'<div style="font:13px system-ui;padding:8px 12px;border-left:3px solid #FFAB00">{_html.escape(msg)}</div>'


def _static_table(p):
    """Plain table shown when scripts can't run (untrusted notebook, nbconvert, GitHub)."""
    cols = p["columns"]
    if not cols:
        return "<div>OK</div>"
    head = "".join(f"<th>{_html.escape(c['name'])}</th>" for c in cols)
    body = []
    for r in p["rows"][:_STATIC_ROWS]:
        cells = "".join(
            "<td><i>null</i></td>" if v is None else f"<td>{_html.escape(str(v)[:200])}</td>" for v in r)
        body.append(f"<tr>{cells}</tr>")
    more = len(p["rows"]) - _STATIC_ROWS
    note = f"<div style='opacity:.7;font-size:12px'>… {more:,} more rows. Trust the notebook (File › Trust Notebook) and re-run for the interactive view.</div>" if more > 0 else ""
    return f"<table class='nbb-static'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>{note}"


def _render(payload):
    rid = "nbb-" + uuid.uuid4().hex[:12]
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)
    data = data.replace("<", "\\u003c")
    out = (
        f'<div id="{rid}" class="nbb-root" data-lm-suppress-shortcuts="true" '
        f'data-p-suppress-shortcuts="true">{_static_table(payload)}</div>'
        f"<style>{_asset("nbboost.css")}</style>"
        f'<script type="application/json" id="{rid}-data">{data}</script>'
        f"<script>{_asset('nbboost.js').replace('__ROOT_ID__', rid)}</script>"
    )
    _ipy_display(_HTML(out))


