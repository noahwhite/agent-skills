#!/usr/bin/env bash
# Bounded wait on Linear SKL-262 state. Arg 1: max seconds. Prints the last observed state line.
limit="$1"
end=$(( $(date +%s) + limit ))
while :; do
  line="$(linear issue view SKL-262 2>&1 | grep -a -m1 '^\*\*State:\*\*')"
  case "$line" in
    *"In Deployment Review"*) echo "$(date -u +%H:%M:%SZ) $line"; exit 0 ;;
  esac
  now=$(date +%s)
  if [ "$now" -ge "$end" ]; then echo "$(date -u +%H:%M:%SZ) $line"; exit 1; fi
  left=$(( end - now )); s=15; [ "$left" -lt 15 ] && s="$left"
  sleep "$s"
done
