"""Static check for undefined names.

Editing this codebase has three times silently deleted a function that other
code still called, which the test suite did not catch because the calling path
needed the network and was stubbed. A name that does not exist is a class of
error worth catching without running anything.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_undefined_names():
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", "app", "tests", "seed.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    undefined = [
        line for line in result.stdout.splitlines()
        if "undefined name" in line or "may be undefined" in line
    ]
    assert not undefined, "undefined names:\n" + "\n".join(undefined)


def test_no_unused_imports_outside_known_cases():
    """Dead imports are usually the residue of a deletion that went too far."""
    allowed = ("app/db.py",)   # models imported for its table-registration side effect
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", "app", "tests", "seed.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    unused = [
        line for line in result.stdout.splitlines()
        if "imported but unused" in line and not line.startswith(allowed)
    ]
    assert not unused, "unused imports:\n" + "\n".join(unused)
