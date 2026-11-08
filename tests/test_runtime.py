from types import SimpleNamespace as NS

import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import runtime


@pytest.mark.parametrize("s, out", [(0.04, "0.0s"), (2.34, "2.3s"), (65, "1m 05s"), (3725, "1h 02m 05s")])
def test_fmt_duration(s, out):
    assert runtime.fmt_duration(s) == out


def stage(n, done, fin=False, b=0):
    return NS(num_tasks=n, num_completed_tasks=done, num_bytes_read=b, done=fin)


class Handle:
    def __init__(self):
        self.updates = []

    def update(self, obj):
        self.updates.append(obj.data)


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def make_bar():
    clock, handles = Clock(), []

    def disp(obj, display_id=False):
        h = Handle()
        h.first = obj.data
        handles.append(h)
        return h

    return runtime.ProgressBar(display=disp, clock=clock), clock, handles


def stage_at(sid, n, done, fin=False, b=0):
    return NS(stage_id=sid, num_tasks=n, num_completed_tasks=done, num_bytes_read=b, done=fin)


def test_fast_queries_show_no_block():
    bar, clock, handles = make_bar()
    bar([stage_at(1, 2, 1)], 1, "op", False)
    clock.t = 0.1
    bar([stage_at(1, 2, 2)], 0, "op", False)
    bar(None, 0, "op", True)
    assert handles == []


def test_slow_query_shows_live_block_then_keeps_a_collapsed_summary():
    bar, clock, handles = make_bar()
    bar([stage_at(3, 10, 0)], 4, "op", False)
    clock.t = 1.0
    bar([stage_at(3, 10, 3, b=2048)], 4, "op", False)        # appears after the delay
    clock.t = 1.05
    bar([stage_at(3, 10, 4)], 4, "op", False)                 # throttled
    clock.t = 2.0
    bar([stage_at(3, 10, 8), stage_at(4, 5, 0)], 2, "op", False)
    clock.t = 2.5
    bar(None, 0, "op", True)                                  # finished: always rendered
    assert len(handles) == 1
    h = handles[0]
    assert "<details class='nbb-jobs'" in h.first and " open" not in h.first.split("<summary")[0]
    assert "3/10 tasks · 4 running" in h.first and "2.0 KiB read" in h.first
    assert len(h.updates) == 2
    assert "8/15 tasks" in h.updates[0] and "Stage 4" in h.updates[0]
    final = h.updates[-1]
    assert "1 query · 2 stages · 8/15 tasks · 2.5s" in final and "finished" in final
    assert "running" not in final.split("</summary>")[0]
    assert "class='stale'" in final       # stage 4 never reported complete -> shown dimmed, not as running




def test_one_block_per_cell_lists_every_query():
    bar, clock, handles = make_bar()
    bar([stage_at(1, 4, 0)], 1, "a", False)
    clock.t = 1.0
    bar([stage_at(1, 4, 2)], 1, "a", False)
    bar(None, 0, "a", True)
    clock.t = 1.5
    bar([stage_at(2, 6, 6, fin=True)], 0, "b", False)
    bar(None, 0, "b", True)
    assert len(handles) == 1
    final = handles[0].updates[-1]
    assert "2 queries" in final and "Query 1" in final and "Query 2" in final and "✓" in final
    bar.new_cell()                                             # next cell gets its own block
    clock.t = 3.0
    bar([stage_at(9, 1, 0)], 1, "c", False)
    clock.t = 4.0
    bar([stage_at(9, 1, 0)], 1, "c", False)
    assert len(handles) == 2


def test_block_remembers_open_state_across_updates():
    bar, clock, handles = make_bar()
    bar([stage_at(1, 2, 0)], 1, "op", False)
    clock.t = 1.0
    bar([stage_at(1, 2, 1)], 1, "op", False)
    h = handles[0].first
    did = h.split("id='")[1].split("'")[0]
    assert f"getElementById('{did}')" in h and "__nbbJobs" in h


def test_before_cell_starts_a_new_block(monkeypatch):
    called = []
    monkeypatch.setattr(runtime._BAR, "new_cell", lambda: called.append(1))
    runtime.before_cell()
    assert called == [1]


def test_handler_never_raises():
    bar, *_ = make_bar()
    bar("garbage", "x", "op", False)


def test_attach_progress_registers_connect_sessions_once():
    ip = InteractiveShell.instance()

    class Sess:
        __module__ = "pyspark.sql.connect.session"
        calls = 0

        def registerProgressHandler(self, h):
            Sess.calls += 1

    Sess.__module__ = "pyspark.sql.connect.session"
    s = Sess()
    ip.user_ns["_t_sess"] = s
    ip.user_ns["_t_other"] = object()
    try:
        assert runtime.attach_progress(ip) == 1
        assert runtime.attach_progress(ip) == 0 and Sess.calls == 1
    finally:
        ip.user_ns.pop("_t_sess"), ip.user_ns.pop("_t_other")


def test_timing_line(monkeypatch):
    ip = InteractiveShell.instance()
    ip.kernel = object()
    shown = []
    monkeypatch.setattr(runtime, "_ipy_display", lambda o, **k: shown.append(o.data))
    try:
        times = iter([100.0, 102.3])
        monkeypatch.setattr(runtime.time, "perf_counter", lambda: next(times))
        runtime.before_cell()
        runtime.after_cell(NS(error_in_exec=None))
        assert "Command took 2.3s" in shown[0]
        times = iter([0.0, 1.0])
        runtime.before_cell()
        runtime.after_cell(NS(error_in_exec=ValueError()))
        assert "Command failed after 1.0s" in shown[1]
        times = iter([0.0, 0.1])
        runtime.before_cell()
        runtime.after_cell(NS(error_in_exec=None))
        assert len(shown) == 2  # fast cell: no line
    finally:
        del ip.kernel


def test_no_timing_outside_a_kernel(monkeypatch):
    shown = []
    monkeypatch.setattr(runtime, "_ipy_display", lambda o, **k: shown.append(o))
    runtime._t0["t"] = 0.0
    runtime.after_cell(None)
    assert shown == []
