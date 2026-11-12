#!/usr/bin/env bash
# Run the story-to-done eval suite against one skill checkout and record every attempt.
#
#   run-suite.sh [--runs N] [--resume] CHECKOUT LABEL [CASE...]
#
# Cases are listed from the checkout that holds this script (the harness checkout), never from
# CHECKOUT. Each scenario of each named CASE, or of every case directory holding a case.yaml,
# runs through its case's run.sh until it has N graded runs (default 3), with void runs retried
# up to 2×N attempts. README.md in this directory states the layout, the naming and the exit codes.
set -euo pipefail
if ! python3 -c 'import yaml' 2> /dev/null; then
  echo "run-suite: python3 cannot import yaml; run this script through 'uv run --locked bash ...' from the repository root" >&2
  exit 2
fi
exec python3 "$(dirname "$0")/suite.py" "$@"
