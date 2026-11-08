"""Notebook integration: ``df.display()`` methods, the %sql magic and the per-cell hook."""
from __future__ import annotations

import sys

from IPython import get_ipython

from . import errors, magics, runtime, sqlmagic
from ._display import DEFAULT_LIMIT, display, show_html
from .nbutils import nbutils


def _display_method(self, limit: int | None = DEFAULT_LIMIT):
    """``df.display()`` -- same as ``display(df)``."""
    display(self, limit=limit)


_METHOD_TARGETS = (
    ("pyspark.sql", "DataFrame"),
    ("pyspark.sql.connect.dataframe", "DataFrame"),
    ("pandas", "DataFrame"),
    ("pandas", "Series"),
    ("pyspark.pandas", "DataFrame"),
    ("pyspark.pandas", "Series"),
)


def install_methods():
    """Add ``.display()`` to the DataFrame classes that are already imported.

    Safe to call repeatedly; it also runs before every notebook cell, so libraries imported
    later are picked up. A class that already has its own ``display`` attribute is left alone.
    """
    for mod, name in _METHOD_TARGETS:
        m = sys.modules.get(mod)
        cls = getattr(m, name, None) if m is not None else None
        if isinstance(cls, type) and "display" not in cls.__dict__ and not hasattr(cls, "display"):
            try:
                cls.display = _display_method
            except Exception:
                pass



def _pre_run_cell(*_args, **_kwargs):
    install_methods()


def _before_cell(*_args, **_kwargs):
    runtime.before_cell()
    ip = get_ipython()
    if ip is not None:
        runtime.attach_progress(ip)


def _reregister(ip, event, fn, on):
    try:
        ip.events.unregister(event, fn)
    except ValueError:
        pass
    if on:
        ip.events.register(event, fn)


def load(*, namespace: bool = True, methods: bool = True, sql_magic: bool = True,
         magics_: bool = True, errors_: bool = True, timing: bool = True, progress: bool = True) -> None:
    """Wire nbboost into the running IPython/Jupyter session.

    ``namespace``  puts ``display``, ``show_html`` and ``nbutils`` into the notebook's variables.
    ``methods``    adds ``.display()`` to Spark / pandas DataFrames (and re-checks before each cell).
    ``sql_magic``  registers ``%sql`` / ``%%sql``.
    ``magics_``    registers ``%fs``, ``%md`` and ``%sh`` (``%sh`` replaces IPython's built-in one).
    ``errors_``    shows Spark errors as a short box with the stack trace collapsed.
    ``timing``     prints "Command took 2.3s" after cells that run for at least half a second.
    ``progress``   shows a live progress bar for slow Spark Connect queries.
    Safe to call more than once.
    """
    ip = get_ipython()
    if ip is None:
        raise RuntimeError("nbboost.load() must be called from IPython or Jupyter")
    if namespace:
        ip.push({"display": display, "show_html": show_html, "nbutils": nbutils})
    if methods:
        install_methods()
    _reregister(ip, "pre_run_cell", _pre_run_cell, methods)
    if sql_magic:
        sqlmagic.register(ip)
    if magics_:
        magics.register(ip)
    if errors_:
        errors.install(ip)
    else:
        errors.uninstall(ip)
    _reregister(ip, "pre_run_cell", _before_cell, timing or progress)
    _reregister(ip, "post_run_cell", runtime.after_cell, timing)
    if progress:
        runtime.attach_progress(ip)
