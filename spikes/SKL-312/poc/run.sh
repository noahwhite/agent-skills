#!/usr/bin/env bash
# Replay the recorded runs of the qa-unfinished-own-steps case through promptfoo and compare
# what promptfoo reports with what the suite recorded.
#
#   bash spikes/SKL-312/poc/run.sh
#
# It installs the pinned promptfoo into a temporary directory outside the repository, replays
# every suite run record it can use through the script provider (provider.py) and the case's
# own grader.py (grade.py), probes the exit statuses no record has, and writes compare.md and
# provider-contract/envelope.json beside this script. No agent runs and no model is called.
#
# Exit status: 0 when every replayed run and probe landed on its mapped promptfoo outcome and
# the two written files are the ones that were there; 1 when one did not (compare.md names
# it), when a written file changed, or when a step failed. On a non-zero exit the temporary
# directory is kept without the install and named on stderr when the replay wrote anything
# into it; otherwise it is removed. Nothing is created when a prerequisite is missing, the
# clone is shallow or the temporary directory would be inside the repository.
set -euo pipefail

# The exact promptfoo version this spike tested; README.md names it too.
version="0.125.1"
# No Node lockfile is committed, so the packages promptfoo depends on are pinned by date:
# npm resolves each one to the newest version published before this instant.
resolved_before="2026-11-15T00:00:00Z"
# The Node.js floor promptfoo $version declares, and the space the install and its download
# cache take together, in megabytes.
node_floor="22.22.0"
space_mb=1600

stop() {
  echo "run.sh: $*" >&2
  exit 1
}
# newer_or_same A B: true when dotted version A is B or newer, compared number by number.
newer_or_same() {
  local -a have want
  local i
  IFS=. read -r -a have <<<"$1"
  IFS=. read -r -a want <<<"$2"
  for i in 0 1 2; do
    [ "$((10#${have[i]:-0}))" -gt "$((10#${want[i]:-0}))" ] && return 0
    [ "$((10#${have[i]:-0}))" -lt "$((10#${want[i]:-0}))" ] && return 1
  done
  return 0
}
# dotted TEXT: the X.Y.Z of a version line such as "v24.1.0" or "v25.0.0-nightly2026", less
# any prerelease or build suffix, or nothing.
dotted() {
  [[ "$1" =~ ^[[:space:]]*v?([0-9]+\.[0-9]+\.[0-9]+)([-+][0-9A-Za-z.+-]+)?[[:space:]]*$ ]] && echo "${BASH_REMATCH[1]}"
}
# exact TEXT: a version line less the space around it and a leading "v", suffix included.
exact() {
  [[ "$1" =~ ^[[:space:]]*v?([^[:space:]]+)[[:space:]]*$ ]] && echo "${BASH_REMATCH[1]}"
}

# Prerequisites, before anything is created.
for tool in git python3 node npm df awk realpath mktemp; do
  command -v "$tool" >/dev/null || stop "$tool is needed and is not on PATH (see README.md, Prerequisites)"
done
node_version="$(dotted "$(node --version)")" || stop "node --version did not print a version: $(node --version)"
newer_or_same "$node_version" "$node_floor" || stop "Node.js $node_floor or later is needed, and node is $node_version"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || stop "python3 3.12 or later is needed"

poc="$(cd "$(dirname "$0")" && pwd)"
root="$(git -C "$poc" rev-parse --show-toplevel)" || stop "$poc is not in a git checkout"
[ "$(git -C "$poc" rev-parse --is-shallow-repository)" = "false" ] ||
  stop "the clone is shallow, and the replay reads history to see that the case is the one the records were graded with"
# promptfoo's database, logs and output, the install and the rebuilt runs all go under one
# temporary directory, which must not be in the repository: checked before it is created.
base="$(realpath -e "${TMPDIR:-/tmp}" 2>/dev/null)" || stop "the temporary directory ${TMPDIR:-/tmp} does not exist"
case "$base/" in
  "$(realpath "$root")"/*) stop "the temporary directory $base is inside the repository; set TMPDIR outside it" ;;
esac
free_mb="$(df -Pm "$base" | awk 'NR == 2 { print $4 }')"
[ "$free_mb" -ge "$space_mb" ] || stop "$base has $free_mb MB free and the install needs $space_mb MB"

work="$(mktemp -d "$base/skl312-poc.XXXXXX")"
# A failed run keeps what explains it (promptfoo's export and log, the provider's log, the
# rebuilt runs, which hold recorded run content) and drops the install and its download cache.
trap 'status=$?
if [ "$status" -eq 0 ]; then
  rm -rf "$work"
else
  rm -rf "$work/npm" "$work/npm-cache" "$work/tmp"
  rmdir "$work/home" 2>/dev/null || true
  rmdir "$work" 2>/dev/null ||
    echo "run.sh: kept $work (it holds rebuilt run content; remove it when read)" >&2
fi' EXIT

cd "$poc"
# Refuses, before the install, a checkout or a record the replay cannot use.
python3 compare.py tests "$work"

# npm gets a scrubbed environment too: no credential or registry setting of the caller, an
# empty home, and its download cache and temporary files under $work. It installs without
# running any package's install script, then checks every installed package's registry
# signature. No lockfile or node_modules reaches the repository.
mkdir -p "$work/npm" "$work/home" "$work/tmp"
printf '%s\n' '{"private":true}' > "$work/npm/package.json"
scrubbed_npm() {
  env -i PATH="$PATH" HOME="$work/home" TMPDIR="$work/tmp" LANG=C.UTF-8 npm_config_cache="$work/npm-cache" \
    npm_config_update_notifier=false npm "$@" --prefix "$work/npm" >&2
}
scrubbed_npm install --no-audit --no-fund --ignore-scripts --loglevel=error --before="$resolved_before" "promptfoo@$version"
scrubbed_npm audit signatures
rm -rf "$work/npm-cache"

# promptfoo gets a scrubbed environment: no provider credential, an empty home, its own state
# and temporary files under $work, and telemetry, update checks, sharing and remote generation
# switched off.
promptfoo() {
  env -i PATH="$PATH" HOME="$work/home" TMPDIR="$work/tmp" LANG=C.UTF-8 SKL312_WORK="$work" \
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
    stop "promptfoo eval exited $status"
  fi
}

reported="$(promptfoo --version)"
installed="$(exact "$reported")" || stop "promptfoo --version printed no version: $reported"
[ "$installed" = "$version" ] || stop "expected promptfoo $version, and the install reports $installed"

evaluate --config promptfooconfig.yaml --tests "$work/tests.csv" --output "$work/results.json"
# The probes: one eval, then the same eval again through --retry-errors, which rewrites its output.
evaluate --config promptfooconfig.yaml --tests "$work/probes.csv" --output "$work/probes.json"
cp "$work/probes.json" "$work/probes-first.json"
evaluate --retry-errors
python3 compare.py report "$work"
