#!/usr/bin/env bash
# Bounded foreground wait on a Linear issue's state.
# Usage: wait-state.sh <ISSUE> <TARGET_STATE> <SECONDS>
# Polls every 15s (each read bounded by timeout), exits when the target state is seen
# or the seconds elapse. Prints the last observed state.
issue="$1"
target="$2"
budget="$3"
end=$(( $(date +%s) + budget ))
state="unread"
while :; do
  now=$(date +%s)
  left=$(( end - now ))
  [ "$left" -le 0 ] && break
  rt=$(( left < 20 ? left : 20 ))
  s=$(timeout "$rt" linear issue view "$issue" --json 2>/dev/null | jq -r '.state.name' 2>/dev/null)
  [ -n "$s" ] && state="$s"
  if [ "$state" = "$target" ]; then
    break
  fi
  now=$(date +%s)
  left=$(( end - now ))
  [ "$left" -le 0 ] && break
  sleep $(( left < 15 ? left : 15 ))
done
printf '%s state: %s at %s\n' "$issue" "$state" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
