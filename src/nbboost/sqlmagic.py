"""``%sql`` / ``%%sql`` cell magic: run SQL on the notebook's ``spark`` session and show the result."""
from __future__ import annotations

from IPython import get_ipython

from ._display import DEFAULT_LIMIT, display


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



def sql_magic(line, cell=None):
    """``%%sql`` / ``%sql``: run SQL on the notebook's ``spark`` session, and show the last result."""
    ip = get_ipython()
    spark = ip.user_ns.get("spark")
    if spark is None:
        print("No `spark` session in this notebook. Create one first, e.g. spark = SparkSession.builder.remote(...).getOrCreate()")
        return None
    limit = DEFAULT_LIMIT
    text = cell if cell is not None else line
    if cell is not None:                   # options on the %%sql line:  %%sql --limit 500
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("-l", "--limit"):
            limit = None if parts[1].lower() in ("none", "all", "0") else int(parts[1])
    stmts = split_sql(text)
    if not stmts:
        return None
    last = None
    for q in stmts:
        last = spark.sql(q)
    ip.user_ns["_sql_df"] = last
    display(last, limit=limit)
    return None



def register(ip) -> None:
    """Register ``%sql`` (line) and ``%%sql`` (cell) on an IPython shell."""
    ip.register_magic_function(sql_magic, magic_kind="line_cell", magic_name="sql")
