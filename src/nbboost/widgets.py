"""``nbutils.widgets`` -- input widgets for parameterising notebooks.

    nbutils.widgets.text("country", "IN", "Country")
    nbutils.widgets.dropdown("year", "2026", ["2024", "2025", "2026"])
    nbutils.widgets.get("year")            # -> "2026" (always a string)

In ``%%sql`` cells, ``:year`` is bound to the widget value as a SQL parameter.
Inputs are drawn with ipywidgets when it is installed; otherwise a read-only label is shown and
values can only be set from code. When a notebook is started by ``nbutils.notebook.run(...,
arguments={...})``, those arguments override the widget values.
"""
from __future__ import annotations

import html
import json
import os
from typing import Dict, List, Optional, Sequence

from IPython.display import HTML
from IPython.display import display as _ipy_display

ARGS_ENV = "NBBOOST_NOTEBOOK_ARGS"
_KINDS = ("text", "dropdown", "combobox", "multiselect")


def _ipywidgets():
    try:
        import ipywidgets  # noqa: F401
        return ipywidgets
    except Exception:
        return None


class Widgets:
    """Create, read and remove notebook input widgets."""

    def __init__(self, display=_ipy_display):
        self._display = display
        self._defs: Dict[str, dict] = {}
        self._overrides: Dict[str, str] = {}
        raw = os.environ.get(ARGS_ENV)
        if raw:
            try:
                self._overrides = {str(k): str(v) for k, v in json.loads(raw).items()}
            except Exception:
                self._overrides = {}

    # ---- creation ------------------------------------------------------------------------
    def text(self, name: str, defaultValue: str = "", label: Optional[str] = None) -> None:
        self._create("text", name, str(defaultValue), None, label)

    def dropdown(self, name: str, defaultValue: str, choices: Sequence[str], label: Optional[str] = None) -> None:
        self._create("dropdown", name, str(defaultValue), choices, label)

    def combobox(self, name: str, defaultValue: str, choices: Sequence[str], label: Optional[str] = None) -> None:
        self._create("combobox", name, str(defaultValue), choices, label)

    def multiselect(self, name: str, defaultValue: str, choices: Sequence[str], label: Optional[str] = None) -> None:
        """``defaultValue`` is one choice or several joined by commas."""
        self._create("multiselect", name, str(defaultValue), choices, label)

    # ---- reading -------------------------------------------------------------------------
    def get(self, name: str) -> str:
        """Current value as a string (multiselect values are joined with commas)."""
        if name in self._overrides:
            return self._overrides[name]
        d = self._defs.get(name)
        if d is None:
            known = ", ".join(sorted(self._defs)) or "none"
            raise ValueError(f"No widget named {name!r}. Defined widgets: {known}.")
        v = d["value"]
        return ",".join(v) if isinstance(v, (list, tuple)) else str(v)

    def getAll(self) -> Dict[str, str]:
        out = {n: self.get(n) for n in self._defs}
        out.update(self._overrides)
        return out

    def has(self, name: str) -> bool:
        return name in self._defs or name in self._overrides

    # ---- removal and display -------------------------------------------------------------
    def remove(self, name: str) -> None:
        d = self._defs.pop(name, None)
        if d is None:
            raise ValueError(f"No widget named {name!r}.")
        ctl = d.get("control")
        if ctl is not None:
            try:
                ctl.close()
            except Exception:
                pass

    def removeAll(self) -> None:
        for n in list(self._defs):
            self.remove(n)

    def show(self) -> None:
        """Show all widgets together (handy at the top of a notebook)."""
        ipw = _ipywidgets()
        ctls = [d["control"] for d in self._defs.values() if d.get("control") is not None]
        if ipw is not None and ctls:
            self._display(ipw.HBox(ctls, layout=ipw.Layout(flex_flow="row wrap", gap="8px")))
        else:
            for n in self._defs:
                self._display(HTML(self._label_html(n)))

    # ---- internals -----------------------------------------------------------------------
    def _create(self, kind, name, default, choices, label):
        if not name or not isinstance(name, str):
            raise ValueError("widget name must be a non-empty string")
        choices = None if choices is None else [str(c) for c in choices]
        if kind != "text" and not choices:
            raise ValueError(f"{kind} widget {name!r} needs a non-empty list of choices")
        if kind in ("dropdown",) and default not in choices:
            raise ValueError(f"default {default!r} is not one of the choices for {name!r}")
        if kind == "multiselect":
            default_v = [x.strip() for x in default.split(",") if x.strip()]
            bad = [x for x in default_v if x not in choices]
            if bad:
                raise ValueError(f"default value(s) {bad} not in the choices for {name!r}")
        else:
            default_v = default

        old = self._defs.get(name)
        if old is not None and old["kind"] == kind and old["choices"] == choices:
            d = old  # re-running the defining cell keeps what the user picked
            d["label"] = label or name
        else:
            if old is not None:
                self.remove(name)
            d = {"kind": kind, "choices": choices, "label": label or name, "value": default_v, "control": None}
            self._defs[name] = d
        if name in self._overrides:
            ov = self._overrides[name]
            d["value"] = [x for x in ov.split(",") if x] if kind == "multiselect" else ov
        if d["control"] is None:
            d["control"] = self._make_control(name, d)
        if d["control"] is not None:
            try:
                d["control"].description = d["label"]
            except Exception:
                pass
            self._display(d["control"])
        else:
            self._display(HTML(self._label_html(name)))

    def _make_control(self, name, d):
        ipw = _ipywidgets()
        if ipw is None:
            return None
        common = dict(description=d["label"], style={"description_width": "initial"},
                      layout=ipw.Layout(width="auto", min_width="220px"))
        k, v, ch = d["kind"], d["value"], d["choices"]
        if k == "text":
            ctl = ipw.Text(value=v, **common)
        elif k == "dropdown":
            ctl = ipw.Dropdown(options=ch, value=v, **common)
        elif k == "combobox":
            ctl = ipw.Combobox(options=ch, value=v, ensure_option=False, **common)
        else:
            ctl = ipw.SelectMultiple(options=ch, value=tuple(v), rows=min(6, len(ch)), **common)

        def on_change(change, _d=d):
            nv = change["new"]
            _d["value"] = list(nv) if isinstance(nv, tuple) else nv

        ctl.observe(on_change, names="value")
        return ctl

    def _label_html(self, name):
        d = self._defs[name]
        return (f"<div style='font:13px ui-sans-serif,system-ui,sans-serif;margin:2px 0'>"
                f"<b>{html.escape(d['label'])}</b>: <code>{html.escape(self.get(name))}</code> "
                f"<span style='opacity:.6'>(install ipywidgets for an input box)</span></div>")


widgets = Widgets()


# ---- SQL parameters ----------------------------------------------------------------------
def _mask_sql(sql: str):
    """Blank out quoted strings, backtick identifiers and comments (same length). Returns (masked, open_quote)."""
    out, i, n, quote = [], 0, len(sql), None
    while i < n:
        ch, two = sql[i], sql[i:i + 2]
        if quote:
            if ch == "\\" and quote != "`" and i + 1 < n:
                out.append("  "); i += 2; continue
            out.append(" ")
            if ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch; out.append(" ")
        elif two == "--":
            j = sql.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j; continue
        elif two == "/*":
            j = sql.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append(" " * (j - i)); i = j; continue
        else:
            out.append(ch)
        i += 1
    return "".join(out), quote


def sql_param_names(sql: str) -> List[str]:
    """Names used as ``:name`` parameter markers (not inside strings/comments, not ``::`` casts)."""
    import re

    masked, _ = _mask_sql(sql)
    seen = []
    for m in re.finditer(r"(?<![:\w]):([A-Za-z_]\w*)", masked):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def sql_args(sql: str, w: Widgets = None) -> Dict[str, str]:
    """Widget values for the ``:name`` markers in ``sql`` that match a widget."""
    w = w or widgets
    return {n: w.get(n) for n in sql_param_names(sql) if w.has(n)}
