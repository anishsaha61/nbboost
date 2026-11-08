"""Short, readable Spark error boxes with the stack trace folded away."""
from __future__ import annotations

import html
import sys
import traceback

from IPython.display import HTML
from IPython.display import display as _ipy_display

_JVM_MARKERS = ("\n\nJVM stacktrace", "\nJVM stacktrace", "\n\nJVM stack trace", "\n\n== Stacktrace")


def is_spark_error(exc: BaseException) -> bool:
    """True for PySpark / Spark Connect / py4j / gRPC errors."""
    for cls in type(exc).__mro__:
        mod = getattr(cls, "__module__", "") or ""
        if mod.startswith(("pyspark.errors", "pyspark.sql.connect", "py4j")):
            return True
        if mod.startswith("grpc") and cls.__name__ in ("RpcError", "_InactiveRpcError", "_MultiThreadedRendezvous"):
            return True
    return False


def _call(exc, name):
    f = getattr(exc, name, None)
    if callable(f):
        try:
            return f()
        except Exception:
            return None
    return None


def summarize(exc: BaseException) -> dict:
    """Pull out ``title``, ``message`` and optional ``sqlstate`` / ``code`` from a Spark error."""
    cls = _call(exc, "getErrorClass") or _call(exc, "getCondition")
    sqlstate = _call(exc, "getSqlState")
    msg = _call(exc, "getMessage")
    if not msg:
        java = getattr(exc, "java_exception", None)
        msg = _call(java, "getMessage") if java is not None else None
    if not msg and _call(exc, "details"):  # grpc
        code = _call(exc, "code")
        msg = f"{getattr(code, 'name', code)}: {exc.details()}" if code else exc.details()
    msg = str(msg if msg else exc)
    for marker in _JVM_MARKERS:
        i = msg.find(marker)
        if i > 0:
            msg = msg[:i]
    msg = msg.strip()
    title = type(exc).__name__
    return {"title": title, "errorClass": cls, "sqlstate": sqlstate, "message": msg}


def render(exc: BaseException) -> str:
    s = summarize(exc)
    full = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    meta = []
    if s["errorClass"]:
        meta.append(f"<code>{html.escape(str(s['errorClass']))}</code>")
    if s["sqlstate"]:
        meta.append(f"SQLSTATE {html.escape(str(s['sqlstate']))}")
    meta_html = (f"<div style='font-size:12px;opacity:.75;margin:2px 0 6px'>{' · '.join(meta)}</div>" if meta else "")
    return (
        "<div class='nbb-err' style='border:1px solid #d13438;border-left:4px solid #d13438;"
        "background:rgba(209,52,56,.08);border-radius:4px;padding:10px 14px;margin:4px 0;"
        "font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.45'>"
        f"<div style='font-weight:600;color:#d13438'>{html.escape(s['title'])}</div>{meta_html}"
        f"<pre style='white-space:pre-wrap;word-break:break-word;margin:0;font:12.5px/1.45 ui-monospace,monospace;"
        f"background:none;border:0;padding:0'>{html.escape(s['message'])}</pre>"
        "<details style='margin-top:8px'><summary style='cursor:pointer;font-size:12px;opacity:.8'>"
        "Show stack trace</summary>"
        f"<pre style='white-space:pre-wrap;word-break:break-word;margin:6px 0 0;font:11.5px/1.4 ui-monospace,monospace;"
        f"max-height:420px;overflow:auto;background:none;border:0;padding:0;opacity:.85'>{html.escape(full)}</pre>"
        "</details></div>"
    )


_ORIG = "_nbboost_orig_showtraceback"


def install(ip) -> None:
    """Replace ``ip.showtraceback`` so Spark errors render as a short box (idempotent)."""
    if getattr(ip, _ORIG, None) is not None:
        return
    orig = ip.showtraceback

    def showtraceback(exc_tuple=None, *args, **kwargs):
        try:
            _, value, _ = ip._get_exc_info(exc_tuple)
            if value is not None and is_spark_error(value):
                _ipy_display(HTML(render(value)))
                return
        except Exception:
            pass
        return orig(exc_tuple, *args, **kwargs)

    setattr(ip, _ORIG, orig)
    ip.showtraceback = showtraceback


def uninstall(ip) -> None:
    orig = getattr(ip, _ORIG, None)
    if orig is not None:
        ip.showtraceback = orig
        delattr(ip, _ORIG)
