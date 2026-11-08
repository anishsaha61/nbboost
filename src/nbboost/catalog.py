"""``nbutils.catalog`` -- cached catalog lookups (databases, tables, columns) used by autocomplete."""
from __future__ import annotations

import html
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FutTimeout
from typing import Callable, List, Optional

TTL = 60.0        # seconds a lookup is reused
TIMEOUT = 1.5     # seconds autocomplete waits for the catalog before giving up


class Rows(list):
    """A list of NamedTuples that renders as an HTML table."""

    def _repr_html_(self) -> str:
        if not self:
            return "<div style='opacity:.6'>(none)</div>"
        fields = self[0]._fields
        head = "".join(f"<th style='text-align:left;padding:3px 10px'>{f}</th>" for f in fields)
        body = "".join("<tr>" + "".join(f"<td style='padding:3px 10px'>{html.escape('' if v is None else str(v))}</td>"
                                        for v in r) + "</tr>" for r in self)
        return (f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
                f"<div style='font-size:12px;opacity:.6'>{len(self)} item(s)</div>")


def _spark():
    from IPython import get_ipython
    ip = get_ipython()
    return ip.user_ns.get("spark") if ip is not None else None


def _unquote(name: str) -> str:
    return name.replace("`", "")


class Catalog:
    """Read the Spark catalog of the notebook's ``spark`` session, with a short cache."""

    def __init__(self, spark_getter: Callable = _spark):
        self._get_spark = spark_getter
        self._cache: dict = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="nbboost-catalog")

    # ---- public listing --------------------------------------------------------------------
    def databases(self) -> Rows:
        sp = self._need_spark()
        return Rows(sp.catalog.listDatabases())

    def tables(self, database: Optional[str] = None) -> Rows:
        sp = self._need_spark()
        return Rows(sp.catalog.listTables(database) if database else sp.catalog.listTables())

    def columns(self, table: str) -> Rows:
        return Rows(self._need_spark().catalog.listColumns(_unquote(table)))

    def refresh(self) -> None:
        """Forget cached names (also happens automatically after CREATE / DROP / ALTER / USE)."""
        with self._lock:
            self._cache.clear()

    # ---- cached names for autocomplete ------------------------------------------------------
    def database_names(self) -> List[str]:
        return self._cached("dbs", lambda sp: [d.name for d in sp.catalog.listDatabases()])

    def table_names(self, database: Optional[str] = None) -> List[str]:
        key = "tables:" + (database or "")
        return self._cached(key, lambda sp: [t.name for t in (sp.catalog.listTables(database) if database
                                                                  else sp.catalog.listTables())])

    def column_names(self, table: str) -> List[str]:
        t = _unquote(table)
        return self._cached("cols:" + t.lower(), lambda sp: [c.name for c in sp.catalog.listColumns(t)])

    # ---- internals --------------------------------------------------------------------------
    def _need_spark(self):
        sp = self._get_spark()
        if sp is None:
            raise RuntimeError("no `spark` session in this notebook")
        return sp

    def _cached(self, key: str, fn) -> List[str]:
        sp = self._get_spark()
        if sp is None:
            return []
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(key)
            if hit and hit[0] is not None and now - hit[0] < TTL:
                return hit[1]
            fut = hit[2] if hit and hit[2] is not None and not hit[2].done() else None
            fresh = fut is None
            if fresh:
                fut = self._pool.submit(fn, sp)
                self._cache[key] = (None, [], fut)
        if fresh:  # outside the lock: the callback may run right here if fn already finished
            fut.add_done_callback(lambda f, k=key: self._store(k, f))
        try:
            return list(fut.result(timeout=TIMEOUT))
        except _FutTimeout:
            return []           # slow catalog: no suggestions now, the cache fills in the background
        except Exception:
            return []

    def _store(self, key, fut):
        try:
            val = list(fut.result())
        except Exception:
            val = []
        with self._lock:
            self._cache[key] = (time.monotonic(), val, None)


catalog = Catalog()
