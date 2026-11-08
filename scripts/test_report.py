#!/usr/bin/env python3
"""Turn pytest's JUnit XML (+ optional coverage.xml) into a short Markdown test report.

    python scripts/test_report.py test-results.xml [coverage.xml] > test-report.md
"""
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def main(junit, cov=None):
    root = ET.parse(junit).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    tests = sum(int(s.get("tests", 0)) for s in suites)
    fails = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    skips = sum(int(s.get("skipped", 0)) for s in suites)
    secs = sum(float(s.get("time", 0)) for s in suites)
    passed = tests - fails - skips
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        sha = os.environ.get("GITHUB_SHA", "unknown")[:7]
    pct = ""
    if cov and os.path.exists(cov):
        rate = float(ET.parse(cov).getroot().get("line-rate", 0)) * 100
        pct = f"| Line coverage | {rate:.0f}% |\n"
    skipped_names = [f"{c.get('classname')}::{c.get('name')}" for s in suites for c in s.iter("testcase")
                     if c.find("skipped") is not None]
    out = [
        "## Test evidence",
        "",
        "| | |", "|---|---|",
        f"| Commit | `{sha}` |",
        f"| Date (UTC) | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} |",
        f"| Python | {platform.python_version()} |",
        f"| Result | {'PASS' if fails == 0 else 'FAIL'} |",
        f"| Passed / failed / skipped | {passed} / {fails} / {skips} |",
        f"| Duration | {secs:.1f}s |",
    ]
    text = "\n".join(out) + "\n" + pct
    if skipped_names:
        text += "\nSkipped:\n" + "\n".join(f"- `{n}`" for n in skipped_names[:20]) + "\n"
    print(text)
    return 1 if fails else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:3]))
