from types import SimpleNamespace as NS

import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import runtime


@pytest.mark.parametrize("s, out", [(0.04, "0.0s"), (2.34, "2.3s"), (65, "1m 05s"), (3725, "1h 02m 05s")])
def test_fmt_duration(s, out):
    assert runtime.fmt_duration(s) == out


def stage(n, done, fin=False, b=0):
    return NS(num_tasks=n, num_completed_tasks=done, num_bytes_read=b, done=fin)


def test_render_progress():
    h = runtime.render_progress([stage(10, 4, b=2048), stage(5, 5, True)], 3, 1.25)
    assert "width:60.0%" in h and "9/15 tasks" in h and "stage 1/2" in h and "2.0 KiB read" in h and "1.2s" in h


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


def test_fast_queries_show_no_bar():
    bar, clock, handles = make_bar()
    bar([stage(2, 1)], 1, "op", False)
    clock.t = 0.1
    bar([stage(2, 2)], 0, "op", False)
    bar(None, 0, "op", True)
    assert handles == []


def test_slow_query_shows_updates_then_clears():
    bar, clock, handles = make_bar()
    bar([stage(10, 0)], 4, "op", False)
    clock.t = 1.0
    bar([stage(10, 3)], 4, "op", False)
    clock.t = 1.05  # throttled
    bar([stage(10, 4)], 4, "op", False)
    clock.t = 2.0
    bar([stage(10, 8)], 2, "op", False)
    bar(None, 0, "op", True)
    assert len(handles) == 1
    h = handles[0]
    assert "30.0%" in h.first and "80.0%" in h.updates[0] and h.updates[-1] == ""


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
