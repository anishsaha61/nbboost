"""Tab completion of table and column names from the Spark catalog.

Works in ``%%sql`` cells, ``%sql`` lines, ``spark.table("…")`` (and ``saveAsTable`` / ``insertInto``)
and inside the string passed to ``spark.sql("…")``.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .catalog import Catalog, catalog as _default_catalog
from .widgets import _mask_sql

_DB_CONTEXT = re.compile(r"(?:\bshow\s+tables\s+(?:in|from)|\buse|\bdatabase|\bschema|\bnamespace)\s+$", re.I)
_TABLE_CONTEXT = re.compile(
    r"(?:\bfrom|\bjoin|\binto|\btable|\bupdate|\bdescribe(?:\s+(?:extended|detail|history|formatted))?|\bdesc|\bexists)\s+$",
    re.I)
_REF = re.compile(r"\b(?:from|join|update|into)\s+([\w.`]+)(?:\s+(?:as\s+)?([A-Za-z_]\w*))?", re.I)
_NOT_ALIAS = {"where", "join", "on", "left", "right", "inner", "outer", "full", "cross", "natural", "group",
              "order", "limit", "union", "using", "lateral", "having", "window", "select", "set", "values",
              "semi", "anti", "partition", "tablesample", "pivot", "unpivot", "except", "intersect", "minus",
              "sort", "cluster", "distribute", "qualify", "when", "as"}
MAX = 200


def analyze(full_text: str, cursor_line: int, cursor_pos: int) -> Optional[Tuple[str, str, str]]:
    """Return (kind, text_before_cursor, whole_sql) for SQL/table contexts, else None."""
    lines = full_text.split("\n")
    if cursor_line >= len(lines):
        return None
    cur = lines[cursor_line][:cursor_pos]
    before = "\n".join(lines[:cursor_line] + [cur])
    stripped = full_text.lstrip()
    if stripped.startswith("%%sql"):
        start = full_text.find("%%sql")
        nl = full_text.find("\n", start)
        if nl < 0 or len(before) <= nl:
            return None                                  # cursor is on the %%sql options line
        return ("sql", before[nl + 1:], full_text[nl + 1:])
    m = re.match(r"\s*%sql\s+(.*)$", cur)
    if m:
        return ("sql", m.group(1), lines[cursor_line].split("%sql", 1)[1])
    m = re.search(r"""\.(?:table|saveAsTable|insertInto)\(\s*(?:\w+\s*=\s*)?[rRbBuU]?(["'])([^"'\n]*)$""", before)
    if m:
        return ("table", m.group(2), m.group(2))
    m = re.search(r"""\.sql\(\s*(?:\w+\s*=\s*)?[fFrR]{0,2}("{3}|'{3}|"|')(.*)$""", before, re.S)
    if m and m.group(1) not in m.group(2):
        return ("sql", m.group(2), m.group(2))
    return None


def _filter(items, frag):
    f = frag.replace("`", "").lower()
    seen, out = set(), []
    for it in items:
        if it.lower().startswith(f) and it not in seen:
            seen.add(it)
            out.append(it)
    return out[:MAX]


def _table_candidates(cat: Catalog, frag: str) -> List[Tuple[str, str]]:
    f = frag.replace("`", "")
    parts = f.split(".")
    if len(parts) == 1:
        items = [(d + ".", "database") for d in cat.database_names()]
        items += [(t, "table") for t in cat.table_names()]
    elif len(parts) == 2:
        db = parts[0]
        if db.lower() == "spark_catalog":
            items = [(f"{db}.{d}.", "database") for d in cat.database_names()]
        else:
            items = [(f"{db}.{t}", "table") for t in cat.table_names(db)]
    else:
        pre = ".".join(parts[:2])
        items = [(f"{pre}.{t}", "table") for t in cat.table_names(parts[1])]
    keep = set(_filter([i for i, _ in items], f))
    return [(i, k) for i, k in items if i in keep]


def _refs(sql: str):
    masked, _ = _mask_sql(sql)
    out = []
    for m in _REF.finditer(masked):
        start, end = m.span(1)
        table = sql[start:end]
        alias = m.group(2)
        if alias and alias.lower() in _NOT_ALIAS:
            alias = None
        out.append((table, alias))
    return out


def suggest(kind: str, before: str, whole: str, cat: Catalog) -> Tuple[str, List[Tuple[str, str]]]:
    """(fragment being replaced, [(completion, type)])"""
    frag = re.search(r"[\w.`]*$", before).group(0)
    if kind == "table":
        return frag, _table_candidates(cat, frag)
    masked, open_quote = _mask_sql(before)
    if open_quote:
        return frag, []                                  # inside a SQL string literal
    head = masked[: len(masked) - len(frag)] if frag else masked
    if _DB_CONTEXT.search(head):
        return frag, [(d, "database") for d in _filter(cat.database_names(), frag)]
    if _TABLE_CONTEXT.search(head):
        return frag, _table_candidates(cat, frag)
    refs = _refs(whole)
    if not refs:
        return frag, []
    f = frag.replace("`", "")
    if "." in f:
        qual, colfrag = f.rsplit(".", 1)
        target = None
        for table, alias in refs:
            t = table.replace("`", "")
            if qual.lower() in {(alias or "").lower(), t.lower(), t.split(".")[-1].lower()}:
                target = table
                break
        if target is None:
            return frag, []
        cols = _filter(cat.column_names(target), colfrag)
        return frag, [(f"{qual}.{c}", "column") for c in cols]
    cols: List[str] = []
    for table, _ in refs:
        cols += cat.column_names(table)
    return frag, [(c, "column") for c in _filter(cols, f)]


def make_matcher(cat: Catalog = None):
    from IPython.core.completer import SimpleCompletion, context_matcher

    cat = cat or _default_catalog

    @context_matcher(identifier="nbboost.catalog")
    def nbboost_catalog_matcher(context):
        try:
            res = analyze(context.full_text, context.cursor_line, context.cursor_position)
            if res is None:
                return {"completions": [], "suppress": False}
            frag, items = suggest(*res, cat)
        except Exception:
            return {"completions": [], "suppress": False}
        return {"completions": [SimpleCompletion(t, type=k) for t, k in items],
                "matched_fragment": frag, "suppress": bool(items)}

    return nbboost_catalog_matcher


_DDL = re.compile(r"\b(create|drop|alter|rename|use|msck|refresh|replace|saveAsTable|register)\b", re.I)


def _post_run_cell(result=None):
    try:
        raw = getattr(getattr(result, "info", None), "raw_cell", "") or ""
        if _DDL.search(raw):
            _default_catalog.refresh()
    except Exception:
        pass


def install(ip) -> bool:
    """Add the catalog matcher to IPython's completer (idempotent). False if IPython is too old."""
    comp = getattr(ip, "Completer", None)
    if comp is None or not hasattr(comp, "custom_matchers"):
        return False
    try:
        matcher = make_matcher()
    except ImportError:
        return False
    comp.custom_matchers[:] = [m for m in comp.custom_matchers
                               if getattr(m, "matcher_identifier", None) != "nbboost.catalog"]
    comp.custom_matchers.append(matcher)
    try:
        ip.events.unregister("post_run_cell", _post_run_cell)
    except ValueError:
        pass
    ip.events.register("post_run_cell", _post_run_cell)
    return True


def uninstall(ip) -> None:
    comp = getattr(ip, "Completer", None)
    if comp is not None and hasattr(comp, "custom_matchers"):
        comp.custom_matchers[:] = [m for m in comp.custom_matchers
                                   if getattr(m, "matcher_identifier", None) != "nbboost.catalog"]
    try:
        ip.events.unregister("post_run_cell", _post_run_cell)
    except ValueError:
        pass
