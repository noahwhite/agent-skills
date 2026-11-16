"""promptfoo `python` assertion: grade a replayed run with the case's own grader.py.

promptfoo calls `get_assert(output, context)` with the provider's output, the JSON line
`provider.py` printed. Each grade the recorded run took is taken again by running the
committed `grader.py` on the rebuilt run directory, unchanged and as a subprocess, exactly as
the case's `run.sh` runs it. A grade passes when the grader's last line that is not blank is
`PASS` once stripped, which is how the suite reads a grade file. The run passes when every
grade passes, which is run.sh's exit status. Nothing here reads the recorded verdicts.

What the grader prints can quote the run, so it is written beside the rebuilt run and never
handed to promptfoo, which copies an assertion's reason and an exception's text into its
export and its log.
"""

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import records  # noqa: E402  (the line above lets promptfoo's loader find it)


def get_assert(output: str, context: dict) -> dict:
    replay = json.loads(output)
    run_dir = pathlib.Path(os.environ["SKL312_WORK"]) / replay["run_dir"]
    components, scores = [], {}
    for grade in replay["grades"]:
        try:
            done = subprocess.run(
                [sys.executable, str(records.GRADER), "--run-dir", str(run_dir), "--expectation", grade["expectation"]],
                capture_output=True, text=True, timeout=records.SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"grader.py did not finish in {records.SECONDS} s for {grade['expectation']}") from None
        lines = [line.strip() for line in done.stdout.splitlines() if line.strip()]
        passed = bool(lines) and lines[-1] == "PASS"
        if done.returncode != (0 if passed else 1):
            (run_dir / f"{grade['file']}.stderr").write_text(done.stderr)
            raise RuntimeError(f"grader.py exited {done.returncode} for {grade['expectation']}; "
                               f"its stderr is beside the rebuilt run, in {grade['file']}.stderr")
        # Kept beside the run under the name run.sh gives it, for compare.py to read.
        (run_dir / grade["file"]).write_text(done.stdout)
        scores[grade["expectation"]] = 1.0 if passed else 0.0
        components.append({"pass": passed, "score": scores[grade["expectation"]],
                           "reason": f"{grade['file']} {'ends' if passed else 'does not end'} in PASS"})
    passed = bool(components) and all(component["pass"] for component in components)
    return {
        "pass": passed,
        "score": 1.0 if passed else 0.0,
        "reason": "every grade passed" if passed else "a grade failed, or the run took none",
        "componentResults": components,
        "namedScores": scores,
    }
