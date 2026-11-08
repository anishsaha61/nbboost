"""``nbutils`` -- small notebook helpers. Currently: ``nbutils.fs`` (local file system).

    nbutils.fs.ls("/home/jovyan/data")      # shown as a table
    nbutils.fs.head("data/a.csv")           # first 64 KiB as text
    nbutils.fs.cp / mv / rm / mkdirs / put

Paths are local paths; a leading ``file:`` is accepted and ``~`` is expanded.
"""
from __future__ import annotations

import html
import os
import shutil
from datetime import datetime
from typing import List, NamedTuple, Union

__all__ = ["FileInfo", "FileList", "FS", "fs", "nbutils"]


class FileInfo(NamedTuple):
    path: str
    name: str  # directories end with "/"
    size: int  # bytes; 0 for directories
    modificationTime: int  # epoch milliseconds


def _fmt_size(n: int) -> str:
    v = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if v < 1024 or unit == "TiB":
            return f"{int(v)} B" if unit == "B" else f"{v:.1f} {unit}"
        v /= 1024
    return str(n)


class FileList(list):
    """A list of :class:`FileInfo` that renders as an HTML table in notebooks."""

    def _repr_html_(self) -> str:
        head = "".join(f"<th style='text-align:left;padding:4px 12px'>{h}</th>"
                       for h in ("path", "name", "size", "modificationTime"))
        rows = []
        for f in self:
            ts = datetime.fromtimestamp(f.modificationTime / 1000).strftime("%Y-%m-%d %H:%M:%S")
            cells = (html.escape(f.path), html.escape(f.name), f"{f.size:,} ({_fmt_size(f.size)})", ts)
            rows.append("<tr>" + "".join(
                f"<td style='text-align:{'right' if i == 2 else 'left'};padding:4px 12px'>{c}</td>"
                for i, c in enumerate(cells)) + "</tr>")
        if not rows:
            rows = ["<tr><td colspan=4 style='padding:4px 12px;opacity:.6'>(empty)</td></tr>"]
        return (f"<table class='nbb-fs'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
                f"<div style='font-size:12px;opacity:.6;margin-top:4px'>{len(self)} item(s)</div>")


def _p(path: Union[str, os.PathLike]) -> str:
    s = os.fspath(path)
    if s.startswith("file://"):
        s = s[len("file://"):]
    elif s.startswith("file:"):
        s = s[len("file:"):]
    return os.path.abspath(os.path.expanduser(s))


def _info(path: str) -> FileInfo:
    st = os.stat(path)
    isdir = os.path.isdir(path)
    name = os.path.basename(path.rstrip("/")) + ("/" if isdir else "")
    return FileInfo(path + ("/" if isdir else ""), name, 0 if isdir else st.st_size, int(st.st_mtime * 1000))


class FS:
    """File-system helpers (local disk)."""

    def ls(self, path: str = ".") -> FileList:
        """List a directory (or describe a single file)."""
        p = _p(path)
        if os.path.isdir(p):
            return FileList(_info(os.path.join(p, n)) for n in sorted(os.listdir(p)))
        return FileList([_info(p)])

    def head(self, path: str, maxBytes: int = 65536) -> str:
        """Return up to ``maxBytes`` of a file decoded as UTF-8 (undecodable bytes replaced)."""
        with open(_p(path), "rb") as fh:
            return fh.read(maxBytes).decode("utf-8", errors="replace")

    def mkdirs(self, path: str) -> bool:
        os.makedirs(_p(path), exist_ok=True)
        return True

    def cp(self, src: str, dst: str, recurse: bool = False) -> bool:
        s, d = _p(src), _p(dst)
        if os.path.isdir(s):
            if not recurse:
                raise IsADirectoryError(f"{src} is a directory; pass recurse=True to copy it")
            shutil.copytree(s, os.path.join(d, os.path.basename(s)) if os.path.isdir(d) else d, dirs_exist_ok=True)
        else:
            if os.path.isdir(d):
                d = os.path.join(d, os.path.basename(s))
            os.makedirs(os.path.dirname(d) or ".", exist_ok=True)
            shutil.copy2(s, d)
        return True

    def mv(self, src: str, dst: str, recurse: bool = False) -> bool:
        s, d = _p(src), _p(dst)
        if not os.path.exists(s):
            raise FileNotFoundError(src)
        if os.path.isdir(d):
            d = os.path.join(d, os.path.basename(s))
        os.makedirs(os.path.dirname(d) or ".", exist_ok=True)
        shutil.move(s, d)
        return True

    def rm(self, path: str, recurse: bool = False) -> bool:
        """Delete a file; a directory needs ``recurse=True``. Returns False if nothing existed."""
        p = _p(path)
        if p == os.path.abspath(os.sep) or p == os.path.abspath(os.path.expanduser("~")):
            raise ValueError(f"refusing to delete {p}")
        if not os.path.lexists(p):
            return False
        if os.path.isdir(p) and not os.path.islink(p):
            if not recurse:
                raise IsADirectoryError(f"{path} is a directory; pass recurse=True to delete it")
            shutil.rmtree(p)
        else:
            os.remove(p)
        return True

    def put(self, path: str, contents: str, overwrite: bool = False) -> bool:
        p = _p(path)
        if os.path.exists(p) and not overwrite:
            raise FileExistsError(f"{path} exists; pass overwrite=True")
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(contents)
        return True


class _NbUtils:
    """Namespace object exposed as ``nbutils`` in notebooks."""

    def __init__(self):
        from .catalog import catalog
        from .data import data
        from .notebook import notebook
        from .secrets import secrets
        from .widgets import widgets

        self.fs = fs
        self.widgets = widgets
        self.notebook = notebook
        self.secrets = secrets
        self.data = data
        self.catalog = catalog

    def __repr__(self):
        return "nbutils(" + ", ".join(k for k in vars(self) if not k.startswith("_")) + ")"


fs = FS()
nbutils = _NbUtils()
