"""Query plans as a collapsible tree (``nbutils.data.explain`` and ``%%sql --explain``)."""
from __future__ import annotations

import contextlib
import html
import io
import re
from typing import Dict, List, Optional, Tuple

from IPython.display import HTML
from IPython.display import display as _ipy_display

MODES = ("simple", "extended", "codegen", "cost", "formatted")
_SQL_KEYWORD = {"simple": "", "extended": "EXTENDED", "codegen": "CODEGEN", "cost": "COST", "formatted": "FORMATTED"}

# operators worth calling out: (regex, label, colour)
_FLAGS = [
    (r"^(\*\(\d+\)\s*)?(CartesianProduct|BroadcastNestedLoopJoin)\b", "expensive join", "#d13438"),
    (r"^(\*\(\d+\)\s*)?(Exchange|ShuffleExchange)\b", "shuffle", "#c75000"),
    (r"^(\*\(\d+\)\s*)?BroadcastExchange\b", "broadcast", "#8a6d00"),
    (r"^(\*\(\d+\)\s*)?(SortMergeJoin|ShuffledHashJoin)\b", "shuffle join", "#c75000"),
    (r"^(\*\(\d+\)\s*)?BroadcastHashJoin\b", "broadcast join", "#2e7d32"),
    (r"^(\*\(\d+\)\s*)?(FileScan|Scan|BatchScan)\b", "scan", "#1f77b4"),
]


def plan_text(obj, mode: str = "extended", spark=None) -> str:
    """The plan as Spark prints it. ``obj`` is a DataFrame or a SQL string (which is not executed)."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if isinstance(obj, str):
        if spark is None:
            from IPython import get_ipython
            ip = get_ipython()
            spark = ip.user_ns.get("spark") if ip is not None else None
        if spark is None:
            raise RuntimeError("explain(sql) needs a `spark` session in the notebook")
        from .widgets import sql_args
        q = f"EXPLAIN {_SQL_KEYWORD[mode]} {obj}"
        args = sql_args(obj)
        rows = (spark.sql(q, args=args) if args else spark.sql(q)).collect()
        return "\n".join(str(r[0]) for r in rows)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        obj.explain(mode=mode)
    return buf.getvalue()


# ---- parsing -----------------------------------------------------------------------------
_NODE = re.compile(r"^((?:[ :|]  )*)(\+- |:- )(.*)$")


def split_sections(text: str) -> List[Tuple[str, str]]:
    """[(title, body)] for each ``== Title ==`` block (one untitled block if there are none)."""
    parts, title, buf = [], None, []
    for line in text.splitlines():
        m = re.match(r"^==+ (.+?) ==+\s*$", line)
        if m:
            if title is not None or any(b.strip() for b in buf):
                parts.append((title or "Plan", "\n".join(buf).strip("\n")))
            title, buf = m.group(1), []
        else:
            buf.append(line)
    if title is not None or any(b.strip() for b in buf):
        parts.append((title or "Plan", "\n".join(buf).strip("\n")))
    return parts


def parse_tree(body: str) -> List[dict]:
    """Turn Spark's ``+-`` / ``:-`` tree text into nested ``{"text", "children"}`` nodes."""
    roots: List[dict] = []
    stack: List[Tuple[int, dict]] = []
    for raw in body.splitlines():
        if not raw.strip():
            continue
        m = _NODE.match(raw)
        if m:
            depth = len(m.group(1)) // 3 + 1
            node = {"text": m.group(3), "children": []}
            while stack and stack[-1][0] >= depth:
                stack.pop()
            (stack[-1][1]["children"] if stack else roots).append(node)
            stack.append((depth, node))
        elif raw[:1] in (" ", ":", "|") and stack:
            stack[-1][1]["text"] += "\n" + raw.strip(" :|")   # continuation of a long node
        else:
            node = {"text": raw.rstrip(), "children": []}
            roots.append(node)
            stack = [(0, node)]
    return roots


def _formatted_details(body: str) -> Tuple[str, Dict[str, str]]:
    """Formatted mode: (tree part, {"(n)": details})."""
    blocks = re.split(r"\n\s*\n", body.strip("\n"))
    tree, details = blocks[0], {}
    for b in blocks[1:]:
        m = re.match(r"^(\(\d+\))", b.strip())
        if m:
            details[m.group(1)] = b.strip()
    return tree, details


# ---- rendering ---------------------------------------------------------------------------
_CSS = """
.nbb-plan{font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;margin:4px 0}
.nbb-plan>details{border:1px solid rgba(128,128,128,.3);border-radius:6px;margin:6px 0;padding:4px 10px}
.nbb-plan>details>summary{font:600 13px ui-sans-serif,system-ui,sans-serif;cursor:pointer;padding:2px 0}
.nbb-plan .nbb-pn{margin-left:14px;border-left:1px dashed rgba(128,128,128,.45);padding-left:8px}
.nbb-plan .nbb-pn.root{margin-left:0;border-left:0;padding-left:0}
.nbb-plan summary.nbb-pt,.nbb-plan .nbb-pl{white-space:pre-wrap;word-break:break-word;cursor:pointer}
.nbb-plan .nbb-pl{cursor:default;padding-left:14px}
.nbb-plan .nbb-tag{font:600 10.5px ui-sans-serif,system-ui,sans-serif;border-radius:3px;padding:0 5px;margin-right:6px;color:#fff;vertical-align:1px}
.nbb-plan .nbb-cap{opacity:.7;margin:2px 0 4px}
.nbb-plan .nbb-det{opacity:.8;margin:2px 0 4px 14px;white-space:pre-wrap;font-size:11.5px}
.nbb-plan pre{white-space:pre-wrap;margin:4px 0;font-size:11.5px;background:none;border:0;padding:0}
"""


def _tag(text: str) -> str:
    for pat, label, colour in _FLAGS:
        if re.search(pat, text):
            return f"<span class='nbb-tag' style='background:{colour}'>{label}</span>"
    return ""


def _node_html(n: dict, details: Dict[str, str], root: bool = False) -> str:
    text = n["text"]
    head = _tag(text) + html.escape(text)
    det = ""
    m = re.search(r"(\(\d+\))\s*$", text)
    if m and m.group(1) in details:
        det = f"<div class='nbb-det'>{html.escape(details[m.group(1)])}</div>"
    cls = "nbb-pn root" if root else "nbb-pn"
    if n["children"]:
        kids = "".join(_node_html(c, details) for c in n["children"])
        return f"<div class='{cls}'><details open><summary class='nbb-pt'>{head}</summary>{det}{kids}</details></div>"
    return f"<div class='{cls}'><div class='nbb-pl'>{head}</div>{det}</div>"


def render(text: str) -> str:
    sections = split_sections(text)
    out = []
    for i, (title, body) in enumerate(sections):
        details: Dict[str, str] = {}
        cap = ""
        if title.lower().startswith("physical") and re.search(r"\n\s*\n\(\d+\)", body):
            body, details = _formatted_details(body)
        if title.lower().startswith("analyzed"):
            first, _, rest = body.partition("\n")
            if rest and not _NODE.match(first) and rest.strip() and not _NODE.match(rest.splitlines()[0]):
                cap, body = first, rest
        tree = parse_tree(body)
        inner = (f"<div class='nbb-cap'>Output: {html.escape(cap)}</div>" if cap else "") + \
            ("".join(_node_html(n, details, root=True) for n in tree) or f"<pre>{html.escape(body)}</pre>")
        is_open = " open" if (title.lower().startswith("physical") or len(sections) == 1 or
                              (i == len(sections) - 1 and not any(t.lower().startswith("physical") for t, _ in sections))) else ""
        out.append(f"<details{is_open}><summary>{html.escape(title)}</summary>{inner}</details>")
    out.append(f"<details><summary>Raw text</summary><pre>{html.escape(text)}</pre></details>")
    return f"<style>{_CSS}</style><div class='nbb-plan'>{''.join(out)}</div>"


def explain(obj, mode: str = "extended", spark=None) -> None:
    _ipy_display(HTML(render(plan_text(obj, mode=mode, spark=spark))))
