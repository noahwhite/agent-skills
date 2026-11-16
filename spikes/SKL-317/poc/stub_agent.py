#!/usr/bin/env python3
"""Stub agent for dry runs of the SKL-317 proof of concept: no model is called.

The case's run.sh starts it in place of the agent, as `stub_agent.py BEHAVIOUR --file PROMPT`,
and the prompt file sits in the run directory. It makes the role calls of the own-steps
scenario through the run's own qa-runtime, so the case's run.sh and grader.py grade a dry run
exactly as they grade a live one.

  pass  reads round 1's checklist, then resumes round 1's session naming its scratch subdirectory
  fail  records a stop, which the grader fails
"""

import json
import pathlib
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("pass", "fail") or sys.argv[2] != "--file":
        sys.exit("usage: stub_agent.py pass|fail --file PROMPT")
    run = pathlib.Path(sys.argv[3]).resolve().parent
    runtime = str(run / "qa-runtime")
    if sys.argv[1] == "fail":
        subprocess.run([runtime, "stop", "--reason", "stub agent: a stop where a resume is due"], check=True)
        return 0
    round_one = json.loads((run / "qa-round-1.json").read_text())
    subdirectory = round_one["scratch_subdirectory"]
    subprocess.run([runtime, "read", "--path", str(run / subdirectory / f"{subdirectory}-todo.md")],
                   check=True, stdout=subprocess.DEVNULL)
    message = run / "stub-message.txt"
    message.write_text(f"The round is unfinished. Continue in {subdirectory}.\n")
    subprocess.run([runtime, "resume", "--session", round_one["session"], "--label", round_one["label"],
                    "--message", str(message)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
