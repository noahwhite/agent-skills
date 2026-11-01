#!/usr/bin/env bash
# Run one scenario of the qa-unfinished-own-steps case and grade it.
#
#   run.sh CHECKOUT SCENARIO RUN_DIR
#
# CHECKOUT is the repository checkout holding the skill to test, SCENARIO one of
# own-steps, owner-action or new-round, and RUN_DIR the directory this run writes to,
# which must sit outside CHECKOUT. EVAL_AGENT_CMD overrides the agent command; the
# prompt is attached to it as a file and never put in argv.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
checkout="${1:?usage: run.sh CHECKOUT SCENARIO RUN_DIR}"
scenario="${2:?usage: run.sh CHECKOUT SCENARIO RUN_DIR}"
run="${3:?usage: run.sh CHECKOUT SCENARIO RUN_DIR}"

case "$(realpath -m "$run")/" in
  "$(realpath "$checkout")"/*) echo "run.sh: RUN_DIR must sit outside CHECKOUT" >&2; exit 2 ;;
esac
test -d "$case_dir/scenarios/$scenario" || { echo "run.sh: no scenario $scenario" >&2; exit 2; }

mkdir -p "$run"
cp "$case_dir/scenarios/$scenario/scenario.md" "$case_dir/scenarios/$scenario/qa-round-1.json" "$run/"
cp "$case_dir/runtime/qa-runtime" "$case_dir/runtime/qa-runtime.md" "$run/"
chmod +x "$run/qa-runtime"
sed -e "s|{skill_dir}|$checkout/skills/story-to-done|g" -e "s|{run_dir}|$run|g" \
  "$case_dir/prompt.md" > "$run/prompt.md"

agent=(opencode run --model deepseek/deepseek-v4-pro "Follow the instructions in the attached file exactly.")
if [ -n "${EVAL_AGENT_CMD:-}" ]; then
  read -r -a agent <<< "$EVAL_AGENT_CMD"
fi
(cd "$checkout" && timeout "${EVAL_TIMEOUT:-900}" "${agent[@]}" --file "$run/prompt.md" > "$run/agent-output.txt" 2>&1) || true

python3 "$case_dir/grader.py" --run-dir "$run" --expectation "$scenario" | tee "$run/grader-output.txt"
