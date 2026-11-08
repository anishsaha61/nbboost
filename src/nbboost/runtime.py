"""Per-cell timing ("Command took 2.3s") and a live Spark Connect progress bar."""
from __future__ import annotations

import html
import time

from IPython.display import HTML
from IPython.display import display as _ipy_display

MIN_SECONDS = 0.5      # cells faster than this show no timing line
PROGRESS_DELAY = 0.4   # a bar only appears for queries slower than this
PROGRESS_EVERY = 0.2   # minimum seconds between bar updates


def fmt_duration(sec: float) -> str:
    if sec < 60:
        return f"{sec:.1f}s"
    m, s = divmod(int(round(sec)), 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def _is_kernel(ip) -> bool:
    return hasattr(ip, "kernel")


# ---- timing -----------------------------------------------------------------------------
_t0 = {"t": None}


def before_cell(*_a, **_k) -> None:
    _t0["t"] = time.perf_counter()


def after_cell(result=None) -> None:
    from IPython import get_ipython
    ip = get_ipython()
    t0, _t0["t"] = _t0["t"], None
    if t0 is None or ip is None or not _is_kernel(ip):
        return
    dur = time.perf_counter() - t0
    if dur < MIN_SECONDS:
        return
    failed = result is not None and getattr(result, "error_in_exec", None) is not None
    text = f"Command failed after {fmt_duration(dur)}" if failed else f"Command took {fmt_duration(dur)}"
    _ipy_display(HTML(f"<div class='nbb-timing' style='font:12px ui-sans-serif,system-ui,sans-serif;"
                      f"opacity:.6;margin-top:4px'>{text}</div>"))


# ---- progress ---------------------------------------------------------------------------
def _fmt_bytes(n: int) -> str:
    v = float(n)
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if v < 1024 or u == "TiB":
            return f"{v:.0f} {u}" if u == "B" else f"{v:.1f} {u}"
        v /= 1024


def render_progress(stages, inflight: int, elapsed: float) -> str:
    stages = list(stages or [])
    total = sum(s.num_tasks for s in stages)
    done = sum(s.num_completed_tasks for s in stages)
    pct = 100 * done / total if total else 0
    nstages_done = sum(1 for s in stages if s.done)
    read = sum(s.num_bytes_read for s in stages)
    label = (f"{done:,}/{total:,} tasks · stage {nstages_done}/{len(stages)} · {inflight} running"
             + (f" · {_fmt_bytes(read)} read" if read else "") + f" · {fmt_duration(elapsed)}")
    return (
        "<div class='nbb-progress' style='font:12px ui-sans-serif,system-ui,sans-serif;margin:4px 0'>"
        "<div style='height:8px;border-radius:4px;background:rgba(128,128,128,.25);overflow:hidden'>"
        f"<div style='height:100%;width:{pct:.1f}%;background:#1f77b4;transition:width .2s'></div></div>"
        f"<div style='opacity:.7;margin-top:3px'>{html.escape(label)}</div></div>"
    )


class ProgressBar:
    """Callable registered with ``spark.registerProgressHandler`` (Spark Connect)."""

    def __init__(self, display=_ipy_display, clock=time.monotonic):
        self._display, self._clock = display, clock
        self._ops: dict = {}

    def __call__(self, stages, inflight_tasks, operation_id, done) -> None:
        try:
            self._update(stages, inflight_tasks, operation_id, done)
        except Exception:  # a cosmetic feature must never break a query
            pass

    def _update(self, stages, inflight, op, done) -> None:
        now = self._clock()
        st = self._ops.setdefault(op, {"start": now, "last": 0.0, "handle": None})
        if done:
            self._ops.pop(op, None)
            if st["handle"] is not None:
                st["handle"].update(HTML(""))
            return
        if now - st["start"] < PROGRESS_DELAY or now - st["last"] < PROGRESS_EVERY:
            return
        st["last"] = now
        h = HTML(render_progress(stages, inflight, now - st["start"]))
        if st["handle"] is None:
            st["handle"] = self._display(h, display_id=True)
        else:
            st["handle"].update(h)


_BAR = ProgressBar()


def attach_progress(ip) -> int:
    """Register the progress bar on every Spark Connect session found in the notebook namespace."""
    n = 0
    for v in list(ip.user_ns.values()):
        t = type(v)
        if getattr(t, "__module__", "") != "pyspark.sql.connect.session" or getattr(v, "_nbboost_progress", False):
            continue
        try:
            v.registerProgressHandler(_BAR)
            v._nbboost_progress = True
            n += 1
        except Exception:
            pass
    return n
