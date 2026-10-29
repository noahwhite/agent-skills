#!/bin/sh
# story-to-done end form: records its own row in the metrics file given as $1, then prints the run summary's table and Totals from it.
printf 'start %s end\nend %s end\n' "$(date -u +%s.%N)" "$(date -u +%s.%N)" >> "$1" && awk '
function span(a, b,  x, y, d) { split(a, x, "."); split(b, y, "."); d = (y[1] - x[1]) * 1000000000 + substr(y[2] "000000000", 1, 9) - substr(x[2] "000000000", 1, 9); return sprintf("%d.%09ds", int(d / 1000000000), d % 1000000000) }
{ k = substr($0, length($1) + length($2) + 3); if (!(k in seen)) { seen[k]; order[++n] = k }; at[$1, k] = $2 }
END {
  print "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |\n|---|---|---|---|---|---|---|"
  for (i = 1; i <= n; i++) { k = order[i]; printf "| %s | command | not set | not set | %s | not reported | not reported |\n", k, (("end", k) in at) ? span(at["start", k], at["end", k]) : "lost" }
  a = at["start", "start"]; z = at["end", "end"]; printf "\nTotals\n- Elapsed wall-clock: %s (%s to %s)\n", span(a, z), a, z
  printf "- Tokens: not reported [partial: %d not reported, 0 cumulative]\n- Tool calls: not reported [partial: %d not reported, 0 cumulative]\n", n, n
}' "$1"
