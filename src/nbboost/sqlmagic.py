"""``%sql`` / ``%%sql`` cell magic: run SQL on the notebook's ``spark`` session and show the result."""
from __future__ import annotations

from IPython import get_ipython

from ._display import DEFAULT_LIMIT, display
from .widgets import sql_args


def split_sql(text):
    """Split a SQL cell into statements on ';' (ignores quotes, backticks and comments)."""
    out, buf, i, n, quote = [], [], 0, len(text), None
    while i < n:
        ch = text[i]
        two = text[i:i + 2]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote != "`" and i + 1 < n:
                buf.append(text[i + 1]); i += 1
            elif ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch; buf.append(ch)
        elif two == "--":
            j = text.find("\n", i)
            j = n if j < 0 else j
            i = j - 1                      # drop the comment, keep the newline
        elif two == "/*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 1
        elif ch == ";":
            out.append("".join(buf)); buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [q.strip() for q in out if q.strip()]



def _parse_options(line: str):
    """``%%sql`` options: ``-l/--limit N|all`` and ``--explain [simple|extended|codegen|cost|formatted]``."""
    opts = {"limit": DEFAULT_LIMIT, "explain": None}
    toks = line.split()
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ("-l", "--limit") and i + 1 < len(toks):
            v = toks[i + 1]
            opts["limit"] = None if v.lower() in ("none", "all", "0") else int(v)
            i += 2
        elif t == "--explain":
            opts["explain"] = "extended"
            if i + 1 < len(toks) and toks[i + 1].lower() in _EXPLAIN_MODES:
                opts["explain"] = toks[i + 1].lower()
                i += 1
            i += 1
        else:
            raise ValueError(f"unknown %%sql option {t!r} (use --limit N or --explain [mode])")
    return opts


_EXPLAIN_MODES = ("simple", "extended", "codegen", "cost", "formatted")


def _run(spark, q):
    args = sql_args(q)
    return spark.sql(q, args=args) if args else spark.sql(q)


def sql_magic(line, cell=None):
    """``%%sql`` / ``%sql``: run SQL on the notebook's ``spark`` session, and show the last result.

    ``:name`` markers are bound to widget values (``nbutils.widgets``) as SQL parameters.
    """
    ip = get_ipython()
    spark = ip.user_ns.get("spark")
    if spark is None:
        print("No `spark` session in this notebook. Create one first, e.g. spark = SparkSession.builder.remote(...).getOrCreate()")
        return None
    text = cell if cell is not None else line
    opts = {"limit": DEFAULT_LIMIT, "explain": None}
    if cell is not None:
        try:
            opts = _parse_options(line)
        except ValueError as e:
            print(f"%%sql: {e}")
            return None
    stmts = split_sql(text)
    if not stmts:
        return None
    if opts["explain"]:
        for q in stmts[:-1]:
            _run(spark, q)
        from .plan import explain
        explain(stmts[-1], mode=opts["explain"], spark=spark)
        return None
    last = None
    for q in stmts:
        last = _run(spark, q)
    ip.user_ns["_sql_df"] = last
    display(last, limit=opts["limit"])
    return None


def register(ip) -> None:
    """Register ``%sql`` (line) and ``%%sql`` (cell) on an IPython shell."""
    ip.register_magic_function(sql_magic, magic_kind="line_cell", magic_name="sql")
