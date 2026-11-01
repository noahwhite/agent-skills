#!/usr/bin/env bash
# Run one scenario of the qa-unfinished-own-steps case and grade it.
#
#   run.sh CHECKOUT SCENARIO RUN_DIR
#
# CHECKOUT is the repository checkout holding the skill to test, SCENARIO one of
# own-steps, owner-action or new-round, and RUN_DIR the empty directory this run writes to,
# which must sit outside CHECKOUT. EVAL_AGENT_CMD overrides the agent command and is split
# on whitespace, so it carries no quoted argument; the prompt is attached to it as a file
# and never put in argv. EVAL_TIMEOUT bounds the agent command in seconds.
#
# Exit codes: 0 the run was graded and passed, 1 the run was graded and failed, 2 the run
# itself is void (bad arguments, a run directory already in use, an agent command that
# failed or timed out, or a checkout the agent changed), and in that case nothing is graded.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
checkout="${1:?usage: run.sh CHECKOUT SCENARIO RUN_DIR}"
scenario="${2:?usage: run.sh CHECKOUT SCENARIO RUN_DIR}"
run="${3:?usage: run.sh CHECKOUT SCENARIO RUN_DIR}"

test -d "$checkout" || { echo "run.sh: no checkout at $checkout" >&2; exit 2; }
case "$scenario" in
  own-steps|owner-action|new-round) ;;
  *) echo "run.sh: unknown scenario $scenario" >&2; exit 2 ;;
esac
test -d "$case_dir/scenarios/$scenario" || { echo "run.sh: no scenario $scenario" >&2; exit 2; }
if [ -e "$run" ] && [ ! -d "$run" ]; then
  echo "run.sh: RUN_DIR $run is not a directory" >&2
  exit 2
fi
checkout_real="$(realpath "$checkout")"
case "$(realpath -m "$run")/" in
  "$checkout_real"/*) echo "run.sh: RUN_DIR must sit outside CHECKOUT" >&2; exit 2 ;;
esac
if [ -d "$run" ] && [ -n "$(ls -A "$run")" ]; then
  echo "run.sh: RUN_DIR $run is not empty; give each run its own directory" >&2
  exit 2
fi

# The checkout's whole state, content included: status alone repeats for a file that was
# already modified and is modified again, and it says nothing about an untracked file's
# contents, so the fingerprint carries the diff against HEAD and a hash per untracked file.
state() {
  git -C "$1" rev-parse HEAD
  git -C "$1" diff HEAD
  git -C "$1" ls-files --others --exclude-standard -z |
    while IFS= read -r -d '' file; do printf '%s\0' "$file"; sha256sum < "$1/$file"; done
}
state_before="$(state "$checkout_real")"

mkdir -p "$run"
cp "$case_dir/scenarios/$scenario/scenario.md" "$case_dir/scenarios/$scenario/qa-round-1.json" "$run/"
cp "$case_dir/runtime/qa-runtime" "$case_dir/runtime/qa-runtime.md" "$run/"
chmod +x "$run/qa-runtime"
# The paths go into the prompt through sed, so escape what sed reads specially.
escape() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
sed -e "s|{skill_dir}|$(escape "$checkout_real/skills/story-to-done")|g" \
    -e "s|{run_dir}|$(escape "$(realpath -m "$run")")|g" \
    "$case_dir/prompt.md" > "$run/prompt.md"

agent=(opencode run --model deepseek/deepseek-v4-pro "Follow the instructions in the attached file exactly.")
if [ -n "${EVAL_AGENT_CMD:-}" ]; then
  read -r -a agent <<< "$EVAL_AGENT_CMD"
fi
status=0
(cd "$checkout_real" && timeout "${EVAL_TIMEOUT:-900}" "${agent[@]}" --file "$run/prompt.md" > "$run/agent-output.txt" 2>&1) || status=$?
if [ "$status" -ne 0 ]; then
  echo "HARNESS: the agent command exited $status (124 means it hit EVAL_TIMEOUT); nothing was graded." >&2
  exit 2
fi
# The checkout under test must be exactly as it was: a new commit is as much a change as a
# dirty file, so the whole state taken before the agent ran is compared with the state after.
if [ "$(state "$checkout_real")" != "$state_before" ]; then
  echo "HARNESS: the agent changed $checkout_real; that run is void and nothing was graded." >&2
  git -C "$checkout_real" status --porcelain --untracked-files=all >&2
  exit 2
fi

python3 "$case_dir/grader.py" --run-dir "$run" --expectation "$scenario" | tee "$run/grader-output.txt"
