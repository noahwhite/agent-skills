#!/usr/bin/env bash
# Run a skill's eval suite against one skill checkout and record every attempt.
#
#   run-suite.sh EVALS [--runs N] [--resume] CHECKOUT LABEL [CASE...]
#   run-suite.sh EVALS --list
#
# Run it from the repository root. EVALS is a skill's evals/ directory, skills/<skill>/evals, in
# the checkout holding this script (the harness). Cases are listed from EVALS, never from
# CHECKOUT. Each scenario of each named CASE, or of every case directory in EVALS holding a
# case.yaml, runs through its case's run.sh until it has N graded runs (default 3), with void runs
# retried up to 2×N attempts. --list prints the case names and runs nothing. Exit status: 0 when
# every graded run passed, 1 when a graded run failed, a scenario is short of N or an attempt
# broke, 2 when it refuses to start. skills/story-to-done/evals/README.md states the layout, the
# naming and the exit codes in full.
set -euo pipefail
if ! python3 -c 'import yaml' 2> /dev/null; then
  echo "run-suite: python3 cannot import yaml; run this script through 'uv run --locked bash ...' from the repository root" >&2
  exit 2
fi
# The runner sits beside this script's real file, so a symlink to the script still finds it.
# Plain readlink, one link at a time, because readlink -f is not on every system.
source=${BASH_SOURCE[0]}
while [ -L "$source" ]; do
  link=$(readlink -- "$source")
  case $link in
    /*) source=$link ;;
    *) source=$(dirname -- "$source")/$link ;;
  esac
done
# CDPATH unset, or cd would print the directory into $here.
here=$(CDPATH='' cd -P -- "$(dirname -- "$source")" && pwd)
exec python3 "$here/eval_suite.py" "$@"
