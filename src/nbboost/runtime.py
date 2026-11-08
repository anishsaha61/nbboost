"""Per-cell timing ("Command took 2.3s") and a collapsible, live "Spark Jobs" progress block (Spark Connect)."""
from __future__ import annotations

import time
import uuid

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
    _BAR.new_cell()


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


def _bar(pct: float, height: int = 6, width: str = "100%") -> str:
    return (f"<span style='display:inline-block;vertical-align:middle;width:{width};height:{height}px;"
            "border-radius:3px;background:rgba(128,128,128,.25);overflow:hidden'>"
            f"<span style='display:block;height:100%;width:{max(0.0, min(100.0, pct)):.1f}%;"
            "background:#1f77b4;transition:width .2s'></span></span>")


def _totals(stages):
    total = sum(s["tasks"] for s in stages)
    done = sum(s["completed"] for s in stages)
    return done, total


_JOBS_CSS = (
    ".nbb-jobs{font:12px ui-sans-serif,system-ui,sans-serif;margin:4px 0;border:1px solid rgba(128,128,128,.3);"
    "border-radius:6px;padding:4px 10px;max-width:900px}"
    ".nbb-jobs>summary{cursor:pointer;list-style:revert;padding:2px 0}"
    ".nbb-jobs .nbb-js{display:inline-flex;gap:8px;align-items:center;flex-wrap:wrap}"
    ".nbb-jobs .nbb-jq{margin:6px 0 2px;font-weight:600}"
    ".nbb-jobs table{border-collapse:collapse;width:100%;margin:2px 0 4px;table-layout:fixed;font:inherit}"
    ".nbb-jobs td{padding:2px 8px 2px 0;white-space:nowrap;vertical-align:middle;font:inherit;"
    "overflow:hidden;text-overflow:ellipsis}"
    ".nbb-jobs td.sid{width:80px}.nbb-jobs td.bar{width:40%}.nbb-jobs td.mk{width:18px;text-align:center}"
    ".nbb-jobs tr.stale td{opacity:.55}"
    ".nbb-jobs .dim{opacity:.65}"
)


def render_jobs(cell: dict, now: float) -> str:
    """Collapsible "Spark Jobs" block for one notebook cell (all its Spark Connect queries)."""
    ops = list(cell["ops"].values())
    running = [o for o in ops if not o["done"]]
    all_stages = [st for o in ops for st in o["stages"].values()]
    done_t, total_t = _totals(all_stages)
    t0 = min(o["start"] for o in ops)
    t1 = now if running else max(o["end"] or now for o in ops)
    nq, ns = len(ops), len(all_stages)
    q = f"{nq} quer{'y' if nq == 1 else 'ies'}"
    st = f"{ns} stage{'' if ns == 1 else 's'}"
    if running:
        r_stages = [x for o in running for x in o["stages"].values()]
        rd, rt = _totals(r_stages)
        pct = 100 * rd / rt if rt else 0
        inflight = sum(o["inflight"] for o in running)
        head = (f"<b>Spark Jobs</b> {_bar(pct, 8, '220px')} "
                f"<span>{rd:,}/{rt:,} tasks · {inflight} running · {fmt_duration(t1 - t0)}</span>"
                f"<span class='dim'>{q} · {st}</span>")
    else:
        head = (f"<b>Spark Jobs</b> <span class='dim'>{q} · {st} · {done_t:,}/{total_t:,} tasks · "
                f"{fmt_duration(t1 - t0)}</span>")
    body = []
    for o in ops:
        dur = fmt_duration((o["end"] or now) - o["start"])
        state = "finished" if o["done"] else "running"
        body.append(f"<div class='nbb-jq'>Query {o['n']} <span class='dim'>· {state} · {dur}</span></div>")
        rows = []
        for sid in sorted(o["stages"]):
            x = o["stages"][sid]
            pct = 100 * x["completed"] / x["tasks"] if x["tasks"] else (100 if x["done"] else 0)
            read = f" · {_fmt_bytes(x['read'])} read" if x["read"] else ""
            if x["done"]:
                tr, mark = "<tr>", "✓"
            elif o["done"]:   # query ended but this stage was never reported complete
                tr = ("<tr class='stale' title=\"Spark didn't report this stage as complete "
                      "(skipped, cancelled or failed)\">")
                mark = "–"
            else:
                tr, mark = "<tr>", ""
            rows.append(f"{tr}<td class='sid'>Stage {sid}</td><td class='bar'>{_bar(pct)}</td>"
                        f"<td>{x['completed']:,}/{x['tasks']:,} tasks{read}</td><td class='mk'>{mark}</td></tr>")
        body.append("<table>" + "".join(rows) + "</table>" if rows
                    else "<div class='dim'>no stage information reported</div>")
    did = cell["id"]
    # Keep the block open/closed across live updates (each update re-renders the HTML).
    keep = ("<script>(function(){var w=window,d=document.getElementById('" + did + "');if(!d)return;"
            "w.__nbbJobs=w.__nbbJobs||{};if(w.__nbbJobs['" + did + "'])d.open=true;"
            "var s=d.querySelector('summary');if(s)s.addEventListener('click',function(){w.__nbbJobs['" + did + "']=!d.open;});"
            "d.addEventListener('toggle',function(){w.__nbbJobs['" + did + "']=d.open;});})();</script>")
    return (f"<style>{_JOBS_CSS}</style><details class='nbb-jobs' id='{did}'>"
            f"<summary><span class='nbb-js'>{head}</span></summary>{''.join(body)}</details>{keep}")


class ProgressBar:
    """Callable registered with ``spark.registerProgressHandler`` (Spark Connect).

    Shows one collapsible "Spark Jobs" block per notebook cell. It appears once a query has run for
    ``PROGRESS_DELAY`` seconds, updates live, and stays (collapsed) after the cell finishes.
    """

    def __init__(self, display=_ipy_display, clock=time.monotonic):
        self._display, self._clock = display, clock
        self._cell = None

    def new_cell(self) -> None:
        self._cell = None

    def __call__(self, stages, inflight_tasks, operation_id, done) -> None:
        try:
            self._update(stages, inflight_tasks, operation_id, done)
        except Exception:  # a cosmetic feature must never break a query
            pass

    def _update(self, stages, inflight, op, done) -> None:
        now = self._clock()
        if self._cell is None:
            self._cell = {"id": "nbb-jobs-" + uuid.uuid4().hex[:10], "ops": {}, "handle": None, "last": 0.0}
        cell = self._cell
        o = cell["ops"].get(op)
        if o is None:
            o = cell["ops"][op] = {"n": len(cell["ops"]) + 1, "start": now, "end": None, "done": False,
                                   "inflight": 0, "stages": {}}
        for x in stages or []:
            o["stages"][x.stage_id] = {"tasks": int(x.num_tasks), "completed": int(x.num_completed_tasks),
                                       "read": int(x.num_bytes_read), "done": bool(x.done)}
        o["inflight"] = int(inflight or 0)
        if done:
            o["done"], o["end"], o["inflight"] = True, now, 0
        if cell["handle"] is None:
            # quick queries leave no trace; a block appears once something runs for a while
            if done or now - o["start"] < PROGRESS_DELAY:
                return
            cell["last"] = now
            cell["handle"] = self._display(HTML(render_jobs(cell, now)), display_id=True)
            return
        if not done and now - cell["last"] < PROGRESS_EVERY:
            return
        cell["last"] = now
        cell["handle"].update(HTML(render_jobs(cell, now)))


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
