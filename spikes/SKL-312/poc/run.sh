#!/usr/bin/env bash
# Replay the recorded runs of the qa-unfinished-own-steps case through promptfoo and compare
# what promptfoo reports with what the suite recorded.
#
#   bash spikes/SKL-312/poc/run.sh
#
# It installs the pinned promptfoo into a temporary directory outside the repository, replays
# every suite run record through the script provider (provider.py) and the case's own
# grader.py (grade.py), probes the exit statuses no record has, and writes compare.md and
# provider-contract/envelope.json beside this script. No agent runs and no model is called.
#
# Exit status: 0 when every replayed run and probe landed on its mapped promptfoo outcome,
# 1 when one did not (compare.md names it) or a step failed. On a non-zero exit the temporary
# directory is kept and named on stderr; otherwise it is removed.
set -euo pipefail

# The exact promptfoo version this spike tested; README.md names it too.
version="0.125.1"

poc="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$poc/../../.." && pwd)"
work="$(mktemp -d)"
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf "$work"; else echo "run.sh: kept $work" >&2; fi' EXIT
# promptfoo's database, logs and output all go under $work, which must not be in the repository.
case "$(realpath "$work")/" in
  "$(realpath "$root")"/*) echo "run.sh: the temporary directory $work is inside the repository; set TMPDIR outside it" >&2; exit 1 ;;
esac

# Install without running any package's install script, then check every installed package's
# registry signature. No lockfile or node_modules reaches the repository.
mkdir -p "$work/npm" "$work/home"
printf '%s\n' '{"private":true}' > "$work/npm/package.json"
npm install --prefix "$work/npm" --no-audit --no-fund --ignore-scripts --loglevel=error "promptfoo@$version" >&2
npm audit signatures --prefix "$work/npm" >&2

# promptfoo gets a scrubbed environment: no provider credential, an empty home, its own state
# under $work, and telemetry, update checks, sharing and remote generation switched off.
promptfoo() {
  env -i PATH="$PATH" HOME="$work/home" LANG=C.UTF-8 SKL312_WORK="$work" \
    PROMPTFOO_CONFIG_DIR="$work/promptfoo" PROMPTFOO_CACHE_ENABLED=false \
    PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 PROMPTFOO_DISABLE_SHARING=1 \
    PROMPTFOO_DISABLE_REMOTE_GENERATION=1 PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=1 \
    "$work/npm/node_modules/.bin/promptfoo" "$@"
}
# promptfoo exits 100 when a test failed or errored, which recorded fails and the probes do.
evaluate() {
  local status=0
  promptfoo eval "$@" --no-cache --no-share --no-progress-bar --no-table --max-concurrency 1 >&2 || status=$?
  if [ "$status" -ne 0 ] && [ "$status" -ne 100 ]; then
    echo "run.sh: promptfoo eval exited $status" >&2
    exit 1
  fi
}

cd "$poc"
installed="$(promptfoo --version)"
if [ "$installed" != "$version" ]; then
  echo "run.sh: expected promptfoo $version, and the install reports $installed" >&2
  exit 1
fi

python3 compare.py tests "$work"
evaluate --config promptfooconfig.yaml --tests "$work/tests.csv" --output "$work/results.json"
# The probes: one eval, then the same eval again through --retry-errors, which rewrites its output.
evaluate --config promptfooconfig.yaml --tests "$work/probes.csv" --output "$work/probes.json"
cp "$work/probes.json" "$work/probes-first.json"
evaluate --retry-errors
python3 compare.py report "$work"
