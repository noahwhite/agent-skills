#!/usr/bin/env bash
# Run the own-steps scenario of the qa-unfinished-own-steps case live through promptfoo, with
# the suite's void retry in the script provider, and write compare.md.
#
#   bash spikes/SKL-317/poc/run.sh
#
# It installs the pinned promptfoo into a temporary directory outside the repository, clones
# the commit under test into the same directory, and runs one promptfoo eval that repeats the
# single test N times, one call at a time. Each call of the script provider (provider.py) runs
# attempts of the case's own run.sh until one is graded, so promptfoo receives N graded runs or
# an error. compare.py then writes compare.md beside this script.
#
# Settings, all optional:
#   SKL317_MODE=stub        a dry run: a stub agent stands in for the model, nothing is spent and
#                           compare.md goes to stdout, never to the repository. Default: live.
#   SKL317_STUB_PLAN        stub only: what each attempt does, in order and comma-separated, of
#                           pass, fail, void and broken. It replaces the injected void.
#   SKL317_NPM_PREFIX       stub only: a directory that already holds the pinned promptfoo
#                           install, to skip installing it again.
#   SKL317_SPEND_LEDGER     the file that holds what every attempt of this spike spent.
#   EVAL_TIMEOUT, EVAL_PASS_ENV   as run-suite.sh reads them.
#
# Exit status: 0 when promptfoo received N graded runs and its report matches the provider's
# record of them; 1 when it did not, when a blocker stopped the run, or when a step failed;
# 2 when the run refused to start. compare.md names the reason for a 1.
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
# N, the graded runs wanted. The provider stops at 2 x N attempts across the whole run.
runs=3
# The one void this run injects, by attempt number: for that attempt the provider gives the
# case's run.sh an agent command that fails, so run.sh itself exits 2 and no model is called.
inject_void_attempt=2

refuse() {
  echo "run.sh: $*" >&2
  exit 2
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
# dotted TEXT: the X.Y.Z of a version line such as "v24.1.0", less any suffix, or nothing.
dotted() {
  [[ "$1" =~ ^[[:space:]]*v?([0-9]+\.[0-9]+\.[0-9]+)([-+][0-9A-Za-z.+-]+)?[[:space:]]*$ ]] && echo "${BASH_REMATCH[1]}"
}
# exact TEXT: a version line less the space around it and a leading "v", suffix included.
exact() {
  [[ "$1" =~ ^[[:space:]]*v?([^[:space:]]+)[[:space:]]*$ ]] && echo "${BASH_REMATCH[1]}"
}

mode="${SKL317_MODE:-live}"
plan="${SKL317_STUB_PLAN:-}"
case "$mode" in
  live)
    [ -z "$plan" ] || refuse "SKL317_STUB_PLAN is for a stub run"
    [ -z "${SKL317_NPM_PREFIX:-}" ] || refuse "SKL317_NPM_PREFIX is for a stub run; a live run installs and checks promptfoo itself"
    ;;
  stub) [ -z "$plan" ] || inject_void_attempt=0 ;;
  *) refuse "SKL317_MODE is live or stub" ;;
esac

# Prerequisites, before anything is created.
tools=(git python3 node npm df awk realpath mktemp timeout)
[ "$mode" = stub ] || tools+=(opencode)
for tool in "${tools[@]}"; do
  command -v "$tool" >/dev/null || refuse "$tool is needed and is not on PATH (see README.md, Prerequisites)"
done
node_version="$(dotted "$(node --version)")" || refuse "node --version did not print a version: $(node --version)"
newer_or_same "$node_version" "$node_floor" || refuse "Node.js $node_floor or later is needed, and node is $node_version"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || refuse "python3 3.12 or later is needed"

poc="$(cd "$(dirname "$0")" && pwd)"
root="$(git -C "$poc" rev-parse --show-toplevel)" || refuse "$poc is not in a git checkout"
# The agent command is split on whitespace, and a stub run names stub_agent.py in it by path.
case "$poc" in
  *[[:space:]]*) refuse "the path of this checkout holds whitespace, which an agent command cannot carry" ;;
esac
commit="$(git -C "$root" rev-parse HEAD)"
# A live run is of one commit: this script, the provider and the case are the committed ones.
# compare.md is the file the run writes, so it alone may differ.
dirty="$(git -C "$root" status --porcelain --untracked-files=all -- . ':(exclude)spikes/SKL-317/poc/compare.md')"
if [ "$mode" = live ] && [ -n "$dirty" ]; then
  refuse "the checkout has changes that are not committed; a live run is of the commit it names"
fi
# promptfoo's database, logs and output, the install, the clone and the run directories all go
# under one temporary directory, which must not be in the repository: checked before it is created.
base="$(realpath -e "${TMPDIR:-/tmp}" 2>/dev/null)" || refuse "the temporary directory ${TMPDIR:-/tmp} does not exist"
case "$base/" in
  "$(realpath "$root")"/*) refuse "the temporary directory $base is inside the repository; set TMPDIR outside it" ;;
esac
# The spend ledger outlives a run, so it is not under the temporary directory, and it must not
# be in the repository either.
ledger="$(realpath -m "${SKL317_SPEND_LEDGER:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-skills-skl317/spend.jsonl}")"
case "$ledger" in
  "$(realpath "$root")"/*) refuse "the spend ledger $ledger is inside the repository; set SKL317_SPEND_LEDGER outside it" ;;
esac
if [ -z "${SKL317_NPM_PREFIX:-}" ]; then
  free_mb="$(df -Pm "$base" | awk 'NR == 2 { print $4 }')"
  [ "$free_mb" -ge "$space_mb" ] || refuse "$base has $free_mb MB free and the install needs $space_mb MB"
fi

work="$(mktemp -d "$base/skl317-poc.XXXXXX")"
# Names this run in the spend ledger and in the title of each agent session it starts.
run_id="$(date -u +%Y%m%dT%H%M%SZ)-${work##*.}"
# A run that did not exit 0 keeps what explains it (promptfoo's export and log, the provider's
# state and log) and drops the install, its download cache and the clone.
trap 'status=$?
if [ "$status" -eq 0 ]; then
  rm -rf "$work"
else
  rm -rf "$work/npm" "$work/npm-cache" "$work/tmp" "$work/checkout" "$work/runs" "$work/usage"
  rmdir "$work" 2>/dev/null ||
    echo "run.sh: kept $work (promptfoo output and the provider state and log; remove it when read)" >&2
fi' EXIT
mkdir -p "$work/tmp"

# npm gets a scrubbed environment: no credential or registry setting of the caller, an empty
# home, and its download cache and temporary files under $work. It installs without running any
# package's install script, then checks every installed package's registry signature. No
# lockfile or node_modules reaches the repository.
prefix="${SKL317_NPM_PREFIX:-$work/npm}"
if [ -z "${SKL317_NPM_PREFIX:-}" ]; then
  mkdir -p "$work/npm" "$work/npm-home"
  printf '%s\n' '{"private":true}' > "$work/npm/package.json"
  scrubbed_npm() {
    env -i PATH="$PATH" HOME="$work/npm-home" TMPDIR="$work/tmp" LANG=C.UTF-8 npm_config_cache="$work/npm-cache" \
      npm_config_update_notifier=false npm "$@" --prefix "$work/npm" >&2
  }
  scrubbed_npm install --no-audit --no-fund --ignore-scripts --loglevel=error --before="$resolved_before" "promptfoo@$version" ||
    refuse "the promptfoo install failed"
  scrubbed_npm audit signatures || refuse "npm audit signatures failed"
  rm -rf "$work/npm-cache" "$work/npm-home"
fi

# The commit under test, as a clone of its own: the case's run.sh, the grader and the skill the
# agent reads all come from it, and an attempt that changes it is void.
git clone --quiet --no-checkout "$root" "$work/checkout" || refuse "cannot clone $root"
git -C "$work/checkout" checkout --quiet --detach "$commit" || refuse "the clone does not hold commit $commit"

# promptfoo, and through it the provider and the agent, keep the variables suite.py gives an
# attempt and the ones EVAL_PASS_ENV names, and nothing else of the caller. Every other
# variable is unset in a subshell, so no value is ever put on a command line. The home
# directory stays the caller's, because the agent reads its configuration there; promptfoo's
# own state is pointed at $work, telemetry, update checks, sharing and remote generation are
# switched off, and Python writes no bytecode beside the scripts.
kept() {
  local name
  case "$1" in
    PATH | HOME | USER | LOGNAME | SHELL | LANG | TERM | TZ | EVAL_TIMEOUT | EVAL_PASS_ENV | LC_* | XDG_*) return 0 ;;
  esac
  for name in ${EVAL_PASS_ENV:-}; do
    [ "$name" = "$1" ] && return 0
  done
  return 1
}
promptfoo() {
  (
    for name in $(compgen -e); do
      kept "$name" || unset "$name" 2>/dev/null || true
    done
    export TMPDIR="$work/tmp" SKL317_WORK="$work" SKL317_CHECKOUT="$work/checkout" SKL317_MODE="$mode" \
      SKL317_RUNS="$runs" SKL317_INJECT_VOID_ATTEMPT="$inject_void_attempt" SKL317_STUB_PLAN="$plan" \
      SKL317_SPEND_LEDGER="$ledger" SKL317_RUN_ID="$run_id" PYTHONDONTWRITEBYTECODE=1 \
      PROMPTFOO_CONFIG_DIR="$work/promptfoo" PROMPTFOO_CACHE_ENABLED=false \
      PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 PROMPTFOO_DISABLE_SHARING=1 \
      PROMPTFOO_DISABLE_REMOTE_GENERATION=1 PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=1
    exec "$prefix/node_modules/.bin/promptfoo" "$@"
  )
}

reported="$(promptfoo --version)" || refuse "promptfoo --version failed"
installed="$(exact "$reported")" || refuse "promptfoo --version printed no version: $reported"
[ "$installed" = "$version" ] || refuse "expected promptfoo $version, and the install reports $installed"

# What the ledger held before this run, for the spend arithmetic in compare.md.
if [ -f "$ledger" ]; then cp "$ledger" "$work/ledger-before.jsonl"; else : > "$work/ledger-before.jsonl"; fi

# One eval: the single test repeated N times, one provider call at a time, no cache, and no
# --retry-errors, which is the only retry promptfoo $version has. promptfoo exits 100 when a
# test failed or errored.
cd "$poc"
eval_status=0
promptfoo eval --config promptfooconfig.yaml --repeat "$runs" --max-concurrency 1 --no-cache --no-share \
  --no-progress-bar --no-table --output "$work/results.json" >&2 || eval_status=$?

out="$poc/compare.md"
[ "$mode" = live ] || out="$work/compare.md"
status=0
python3 compare.py --work "$work" --ledger "$ledger" --mode "$mode" --runs "$runs" --commit "$commit" \
  --version "$version" --eval-status "$eval_status" --dirty "${dirty:+yes}" --out "$out" || status=$?
if [ "$mode" = stub ] && [ -f "$out" ]; then cat "$out"; fi
exit "$status"
