"""``nbutils.notebook`` -- run one notebook from another and pass a result back.

    value = nbutils.notebook.run("ingest.ipynb", timeout_seconds=600, arguments={"date": "2026-11-09"})

    # inside ingest.ipynb
    d = nbutils.widgets.get("date")
    ...
    nbutils.notebook.exit("rows=1234")

The child runs in a **separate, fresh kernel** (like a Databricks job context): it does not see the
caller's variables, and it must create its own ``spark`` session (or get one from an IPython startup
file). ``arguments`` become widget values in the child. Needs ``nbclient`` and ``ipykernel``.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Mapping, Optional

from IPython.display import HTML
from IPython.display import display as _ipy_display

from .widgets import ARGS_ENV

EXIT_ENV = "NBBOOST_NOTEBOOK_EXIT_FILE"


class NotebookExit(Exception):
    """Raised by :meth:`Notebook.exit` to stop the current notebook."""

    def __init__(self, value: str):
        super().__init__(value)
        self.value = value


class NotebookRunError(RuntimeError):
    """The child notebook failed (the message names the failing cell and error)."""


class Notebook:
    def run(self, path: str, timeout_seconds: int = 0, arguments: Optional[Mapping[str, object]] = None,
            output_path: Optional[str] = None, kernel_name: Optional[str] = None) -> Optional[str]:
        """Run ``path`` to completion in a new kernel and return the value it passed to ``exit()``.

        ``timeout_seconds`` limits the whole run (0 = no limit). ``output_path`` saves the executed
        notebook, with its outputs, for later inspection. Returns None if the child never called exit().
        """
        try:
            import nbformat
            from nbclient import NotebookClient
            from nbclient.exceptions import CellExecutionError
        except ImportError as e:  # pragma: no cover - depends on environment
            raise ImportError("nbutils.notebook.run needs nbclient: pip install nbclient ipykernel") from e

        full = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(full) and not full.endswith(".ipynb") and os.path.exists(full + ".ipynb"):
            full += ".ipynb"
        if not os.path.exists(full):
            raise FileNotFoundError(path)
        nb = nbformat.read(full, as_version=4)
        kname = kernel_name or (nb.metadata.get("kernelspec") or {}).get("name") or "python3"

        fd, exit_file = tempfile.mkstemp(prefix="nbboost-exit-", suffix=".json")
        os.close(fd)
        os.remove(exit_file)
        env = os.environ.copy()
        env[ARGS_ENV] = json.dumps({str(k): str(v) for k, v in (arguments or {}).items()})
        env[EXIT_ENV] = exit_file

        client = NotebookClient(nb, kernel_name=kname, timeout=None,
                                resources={"metadata": {"path": os.path.dirname(full)}})
        box = {}

        def work():
            try:
                client.execute(env=env)
            except BaseException as e:  # reported in the caller's thread
                box["error"] = e

        t = threading.Thread(target=work, name="nbboost-notebook-run", daemon=True)
        t.start()
        t.join(timeout_seconds or None)
        try:
            if t.is_alive():
                _shutdown(client)
                t.join(10)
                raise TimeoutError(f"{path} did not finish within {timeout_seconds}s; its kernel was stopped")
            value = _read_exit(exit_file)
            err = box.get("error")
            if err is not None:
                exited = isinstance(err, CellExecutionError) and getattr(err, "ename", "") == "NotebookExit"
                if not exited:
                    if isinstance(err, CellExecutionError):
                        cell = _failing_cell(nb)
                        where = f" in cell {cell}" if cell is not None else ""
                        raise NotebookRunError(f"{path} failed{where}: {err.ename}: {err.evalue}") from None
                    raise NotebookRunError(f"{path} failed: {type(err).__name__}: {err}") from err
            return value
        finally:
            if output_path:
                nbformat.write(nb, os.path.expanduser(output_path))
            try:
                os.remove(exit_file)
            except OSError:
                pass

    def exit(self, value: object = "") -> None:
        """Stop this notebook and hand ``value`` (as a string) back to ``notebook.run``."""
        s = str(value)
        f = os.environ.get(EXIT_ENV)
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump({"value": s}, fh)
        raise NotebookExit(s)


def _read_exit(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)["value"]
    except (OSError, ValueError, KeyError):
        return None


def _failing_cell(nb):
    for i, c in enumerate(nb.cells, 1):
        if c.get("cell_type") == "code" and any(o.get("output_type") == "error" for o in c.get("outputs", [])):
            return i
    return None


def _shutdown(client):
    """Kill the child kernel process (the client runs on another thread's event loop)."""
    km = getattr(client, "km", None)
    proc = getattr(getattr(km, "provisioner", None), "process", None)
    try:
        if proc is not None:
            proc.kill()
    except Exception:
        pass


def render_exit(exc: NotebookExit):
    """What the notebook shows when ``exit()`` is called interactively."""
    import html as _h
    _ipy_display(HTML("<div style='font:13px ui-sans-serif,system-ui,sans-serif;opacity:.75;margin:4px 0'>"
                      f"Notebook exited: <code>{_h.escape(exc.value)}</code></div>"))


notebook = Notebook()
