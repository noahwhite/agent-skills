"""promptfoo `python` assertion: relay the grade the case's own run.sh gave an attempt.

promptfoo calls `get_assert(output, context)` with the provider's output, the JSON line
`provider.py` printed for a graded attempt. The attempt was graded by the case's run.sh, which
runs the case's grader.py unchanged and exits 0 for a graded pass and 1 for a graded fail.
Nothing is graded again here, and no void attempt reaches this assertion.
"""

import json


def get_assert(output: str, context: dict) -> dict:
    attempt = json.loads(output)
    passed = attempt["outcome"] == "pass"
    return {
        "pass": passed,
        "score": 1.0 if passed else 0.0,
        "reason": f"attempt {attempt['attempt']}: run.sh exited {attempt['runner_exit_status']}, "
                  f"a graded {attempt['outcome']}",
    }
