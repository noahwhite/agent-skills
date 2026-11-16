"""promptfoo `python` assertion: relay the grade the case's own run.sh gave an attempt.

promptfoo calls `get_assert(output, context)` with the provider's output, the JSON line
`provider.py` printed for a graded attempt. The attempt was graded by the case's run.sh, which
runs the case's grader.py unchanged and exits 0 for a graded pass and 1 for a graded fail.
Nothing is graded again here, and no void attempt reaches this assertion. An output that is
not that JSON line fails the assertion with a reason of its own, which compare.py lists as a
blocker, since no hand-back of the provider maps to it.
"""

import json


def get_assert(output: str, context: dict) -> dict:
    try:
        attempt = json.loads(output)
        passed = attempt["outcome"] == "pass"
        reason = f"attempt {attempt['attempt']}: run.sh exited {attempt['runner_exit_status']}, a graded {attempt['outcome']}"
    except (ValueError, KeyError, TypeError):
        return {"pass": False, "score": 0.0, "reason": "the provider's output is not one graded attempt"}
    return {"pass": passed, "score": 1.0 if passed else 0.0, "reason": reason}
