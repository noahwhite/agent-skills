"""Record each run of story-to-done's path selector in one run of the spike-no-deployment case.

run.sh copies this file into the run directory's `selector-hook/`, puts that directory first on
PYTHONPATH for the agent command, and names the record file in EVAL_SELECTOR_LOG. Python imports it
at startup. When the script being run is `select-path.py`, it copies what the script prints and, on
exit, appends one line to the record: the time, the script's arguments and what it printed. Any
other Python program is left alone. The sitecustomize this one shadows, if there is one, still runs.
"""

import atexit
import datetime
import importlib.machinery
import importlib.util
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _run_shadowed() -> None:
    path = [entry for entry in sys.path if os.path.abspath(entry or ".") != _HERE]
    spec = importlib.machinery.PathFinder.find_spec("sitecustomize", path)
    if spec is not None and spec.loader is not None:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


class _Copy(io.TextIOBase):
    """Stdout, with a copy of everything written to it."""

    def __init__(self, inner):
        self.inner = inner
        self.seen = []

    def write(self, text):
        self.seen.append(text)
        return self.inner.write(text)

    def flush(self):
        self.inner.flush()

    def __getattr__(self, name):
        return getattr(self.inner, name)


def _watch(log: str) -> None:
    copy = _Copy(sys.stdout)
    sys.stdout = copy

    def record() -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        entry = {"at": now.isoformat(timespec="microseconds").replace("+00:00", "Z"), "argv": sys.argv[1:], "stdout": "".join(copy.seen)}
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    atexit.register(record)


_log = os.environ.get("EVAL_SELECTOR_LOG")
if _log and sys.argv and os.path.basename(sys.argv[0]) == "select-path.py":
    _watch(_log)
_run_shadowed()
