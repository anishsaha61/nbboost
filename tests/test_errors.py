import pytest
from IPython.core.interactiveshell import InteractiveShell

from nbboost import errors


class SparkLike(Exception):
    __module__ = "pyspark.errors.exceptions.connect"

    def __init__(self, msg, cls=None, state=None):
        super().__init__(msg)
        self._m, self._c, self._s = msg, cls, state

    def getMessage(self):
        return self._m

    def getErrorClass(self):
        return self._c

    def getSqlState(self):
        return self._s


def test_is_spark_error():
    assert errors.is_spark_error(SparkLike("x"))
    assert not errors.is_spark_error(ValueError("x"))


def test_summarize_strips_jvm_stacktrace():
    e = SparkLike("[TABLE_NOT_FOUND] no table t\n\nJVM stacktrace:\norg.apache.spark...\n at x", "TABLE_NOT_FOUND", "42P01")
    s = errors.summarize(e)
    assert s["message"] == "[TABLE_NOT_FOUND] no table t"
    assert s["errorClass"] == "TABLE_NOT_FOUND" and s["sqlstate"] == "42P01"


def test_render_escapes_and_collapses():
    try:
        raise SparkLike("bad <script>alert(1)</script>", "X")
    except SparkLike as e:
        h = errors.render(e)
    assert "<script>" not in h and "&lt;script&gt;" in h
    assert "<details" in h and "Show stack trace" in h and "SparkLike" in h


def test_grpc_style_error_uses_details():
    class Rpc(Exception):
        __module__ = "grpc._channel"

        def code(self):
            class C:
                name = "UNAVAILABLE"
            return C()

        def details(self):
            return "connection refused"

    Rpc.__name__ = "_InactiveRpcError"
    assert errors.is_spark_error(Rpc())
    assert errors.summarize(Rpc())["message"] == "UNAVAILABLE: connection refused"


@pytest.fixture
def ip(monkeypatch):
    ip = InteractiveShell.instance()
    errors.uninstall(ip)
    shown = []
    monkeypatch.setattr(errors, "_ipy_display", lambda o, **k: shown.append(o))
    errors.install(ip)
    ip._shown = shown
    yield ip
    errors.uninstall(ip)


def test_hook_replaces_spark_errors_only(ip, capsys):
    ip.run_cell("raise ValueError('plain')")
    assert ip._shown == [] and "ValueError" in capsys.readouterr().out
    ip.user_ns["SparkLike"] = SparkLike
    ip.run_cell("raise SparkLike('boom', 'CLS')")
    assert len(ip._shown) == 1 and "boom" in ip._shown[0].data


def test_install_is_idempotent_and_reversible(ip):
    wrapped = ip.showtraceback
    errors.install(ip)
    assert ip.showtraceback is wrapped
    errors.uninstall(ip)
    assert ip.showtraceback != wrapped
