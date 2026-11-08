#!/usr/bin/env python3
"""Compare a fresh JupyterLab-extension build with the committed one.

    python scripts/check_labextension_build.py COMMITTED_DIR FRESH_DIR

The bundler numbers the container entry module from the build machine's directory layout, so
``static/remoteEntry.<hash>.js`` (and the ``_build.load`` pointer to it in package.json) differ
between machines even when nothing changed. Everything else -- the chunks with the extension's
code and CSS, and the rest of package.json -- must be identical.
"""
import hashlib
import json
import sys
from pathlib import Path


def snapshot(root: Path):
    files = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("static/remoteEntry.") and rel.endswith(".js"):
            continue
        if rel == "package.json":
            data = json.loads(p.read_text())
            data.get("jupyterlab", {}).get("_build", {}).pop("load", None)
            files[rel] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        else:
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return files


def main(committed: str, fresh: str) -> int:
    a, b = snapshot(Path(committed)), snapshot(Path(fresh))
    if a == b:
        print("labextension build is up to date")
        return 0
    for name in sorted(set(a) | set(b)):
        if a.get(name) != b.get(name):
            state = "only in fresh build" if name not in a else "only in committed" if name not in b else "differs"
            print(f"  {name}: {state}")
    print("::error::src/nbboost/labextension is out of date: run 'npm run build' in labextension/ and commit the result")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
