"""A test file can be run on its own, and in any order.

Three files install a fake `mcp` package so `server.py` imports on a Python
without the SDK. They used to ask whether `mcp` had been imported yet, not
whether it was installed, so with the SDK installed:

- `pytest tests/test_server.py` and `pytest tests/test_refactored_helpers.py`
  failed at collection (the fake has no `mcp.server.lowlevel`);
- `pytest tests/test_security.py tests/test_mcp_compat.py` failed three
  tests in the second file, which was handed the first one's fake SDK.

The whole suite hid both: an earlier file imports the real SDK first.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp.server")

TESTS = Path(__file__).parent
SHIMMED = ["test_server.py", "test_refactored_helpers.py", "test_security.py"]


def _pytest(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
        cwd=TESTS.parent, capture_output=True, text=True, timeout=300,
    )


@pytest.mark.parametrize("name", SHIMMED)
def test_a_file_with_the_shim_collects_on_its_own(name):
    run = _pytest("--collect-only", str(TESTS / name))
    assert run.returncode == 0, run.stdout[-2000:]


@pytest.mark.parametrize("name", SHIMMED)
def test_a_file_with_the_shim_leaves_the_real_sdk_in_place(name):
    """Importing the file must not put a fake `mcp` in front of the SDK."""
    code = (
        "import importlib, sys; sys.path.insert(0, 'tests'); "
        f"importlib.import_module({name[:-3]!r}); import mcp; "
        "assert getattr(mcp, '__file__', None), 'mcp is the shim'"
    )
    run = subprocess.run([sys.executable, "-c", code], cwd=TESTS.parent,
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-2000:]


def test_the_shim_does_not_reach_the_next_file():
    run = _pytest(str(TESTS / "test_security.py"), str(TESTS / "test_mcp_compat.py"))
    assert run.returncode == 0, run.stdout[-2000:]
