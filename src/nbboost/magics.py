"""``%fs``, ``%md`` and ``%sh`` magics."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys

from IPython.display import Markdown
from IPython.display import display as _ipy_display

from .nbutils import fs

_FS_USAGE = """usage: %fs <command> ...
  ls [path]            head <path> [maxBytes]     mkdirs <path>
  cp [-r] <src> <dst>  mv <src> <dst>             rm [-r] <path>
  put [-f] <path> <text...>"""


def run_fs(line: str):
    """Execute one ``%fs`` command line and return its result (None for usage errors)."""
    try:
        argv = shlex.split(line)
    except ValueError as e:
        print(f"%fs: {e}")
        return None
    if not argv:
        print(_FS_USAGE)
        return None
    cmd, args = argv[0], argv[1:]
    flags = {a for a in args if a in ("-r", "-f")}
    pos = [a for a in args if a not in ("-r", "-f")]
    try:
        if cmd == "ls":
            return fs.ls(pos[0] if pos else ".")
        if cmd == "head" and pos:
            out = fs.head(pos[0], int(pos[1])) if len(pos) > 1 else fs.head(pos[0])
            print(out, end="" if out.endswith("\n") else "\n")
            return None
        if cmd == "mkdirs" and pos:
            return fs.mkdirs(pos[0])
        if cmd in ("cp", "mv") and len(pos) == 2:
            return getattr(fs, cmd)(pos[0], pos[1], recurse="-r" in flags)
        if cmd == "rm" and pos:
            return fs.rm(pos[0], recurse="-r" in flags)
        if cmd == "put" and len(pos) >= 2:
            return fs.put(pos[0], " ".join(pos[1:]), overwrite="-f" in flags)
    except Exception as e:  # keep the notebook tidy: a one-line message instead of a traceback
        print(f"%fs {cmd}: {type(e).__name__}: {e}")
        return None
    print(_FS_USAGE)
    return None


def fs_magic(line, cell=None):
    """``%fs <command> ...`` or a ``%%fs`` cell with one command per line."""
    if cell is None:
        return run_fs(line)
    last = None
    for ln in cell.splitlines():
        if ln.strip() and not ln.lstrip().startswith("#"):
            last = run_fs(ln)
            if last is not None and not isinstance(last, bool):
                _ipy_display(last)
    return None


def md_magic(line, cell=None):
    """Render Markdown: ``%%md`` cell (or ``%md text``)."""
    text = cell if cell is not None else line
    _ipy_display(Markdown(text))


def sh_magic(line, cell=None):
    """Run shell commands and stream their output (stdout and stderr interleaved)."""
    script = cell if cell is not None else line
    if not script.strip():
        return None
    shell = shutil.which("bash") or "/bin/sh"
    proc = subprocess.Popen([shell, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, bufsize=0, env=os.environ.copy())
    try:
        while True:
            chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(4096)
            if not chunk:
                break
            sys.stdout.write(chunk.decode("utf-8", errors="replace"))
            sys.stdout.flush()
        rc = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("\n[interrupted]")
        return None
    if rc != 0:
        print(f"\n[exit code {rc}]")
    return None


def register(ip) -> None:
    for name, fn in (("fs", fs_magic), ("md", md_magic), ("sh", sh_magic)):
        ip.register_magic_function(fn, magic_kind="line_cell", magic_name=name)
