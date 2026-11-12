#!/usr/bin/env bash
# Bounded wait on SKL-263 reaching In Deployment Review. Arg 1: max seconds.
# Each read is bounded by the outer timeout this script runs under.
end=$(( $(date +%s) + $1 ))
while [ "$(date +%s)" -lt "$end" ]; do
  state="$(timeout 20 linear issue view SKL-263 2>&1 | grep -m1 '^\*\*State:\*\*')"
  echo "$(date -u +%H:%M:%SZ) $state"
  case "$state" in *"In Deployment Review"*) exit 0 ;; esac
  left=$(( end - $(date +%s) ))
  [ "$left" -le 0 ] && break
  [ "$left" -gt 15 ] && left=15
  sleep "$left"
done
exit 1
