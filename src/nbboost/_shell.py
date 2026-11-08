"""Notebook integration: ``df.display()`` methods, the %sql magic and the per-cell hook."""
from __future__ import annotations

import sys

from IPython import get_ipython

from . import sqlmagic
from ._display import DEFAULT_LIMIT, display, show_html


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


def load(*, namespace: bool = True, methods: bool = True, sql_magic: bool = True) -> None:
    """Wire nbboost into the running IPython/Jupyter session.

    ``namespace``  puts ``display`` and ``show_html`` into the notebook's variables.
    ``methods``    adds ``.display()`` to Spark / pandas DataFrames (and re-checks before each cell).
    ``sql_magic``  registers ``%sql`` / ``%%sql``.
    Safe to call more than once.
    """
    ip = get_ipython()
    if ip is None:
        raise RuntimeError("nbboost.load() must be called from IPython or Jupyter")
    if namespace:
        ip.push({"display": display, "show_html": show_html})
    if methods:
        install_methods()
        try:
            ip.events.unregister("pre_run_cell", _pre_run_cell)
        except ValueError:
            pass
        ip.events.register("pre_run_cell", _pre_run_cell)
    if sql_magic:
        sqlmagic.register(ip)
