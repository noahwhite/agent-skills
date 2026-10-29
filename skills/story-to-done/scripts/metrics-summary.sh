#!/bin/sh
# story-to-done end form: records its own row in the metrics file given as $1, then prints the run summary's
# table, the recorded extras and Totals from it.
printf 'start %s end\nend %s end\n' "$(date -u +%s.%N)" "$(date -u +%s.%N)" >> "$1" && awk '
function span(a, b,  x, y, d) { split(a, x, "."); split(b, y, "."); d = (y[1] - x[1]) * 1000000000 + substr(y[2] "000000000", 1, 9) - substr(x[2] "000000000", 1, 9); return sprintf("%d.%09ds", int(d / 1000000000), d % 1000000000) }
function label(s) { if (s == "qa-rounds") return "QA rounds"; if (s == "failed-items") return "Failed items"; if (s == "fix-rounds") return "Fix rounds"; if (s == "prs-merged") return "PRs merged"; if (s == "start") return "Start"; if (s == "time-to-deployment-review") return "Time to deployment review"; if (s == "qa-round-durations") return "QA round durations"; if (s == "end-state") return "End state"; return "" }
function figure(v, c) { return (v == "") ? "not reported" : v (c == 1 ? " cumulative" : "") }
BEGIN { split("qa-rounds failed-items fix-rounds prs-merged start time-to-deployment-review qa-round-durations end-state", known, " ") }
$1 == "extra" { rest = substr($0, 7); i = index(rest, "\t"); if (i > 0) extras[substr(rest, 1, i - 1)] = substr(rest, i + 1); else extras[rest] = ""; next }
{ k = substr($0, length($1) + length($2) + 3); split(k, f, "\t"); k = f[1]; if (!(k in seen)) { seen[k]; order[++n] = k }; at[$1, k] = $2
  if ($1 == "start") { if (f[2] != "") rt[k] = f[2]; if (f[3] != "") model[k] = f[3]; if (f[4] != "") effort[k] = f[4] }
  if ($1 == "end") { if (f[2] != "") tok[k] = f[2]; if (f[3] != "") calls[k] = f[3]; if (f[4] == "cumulative") cum[k] = 1 }
}
END {
  print "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |\n|---|---|---|---|---|---|---|"
  for (i = 1; i <= n; i++) { k = order[i]
    if (tok[k] != "" && tok[k] ~ /^[0-9]+$/) { if (cum[k] == 1) tcu++; else { ttok += tok[k]; ttn++ } } else tnt++
    if (calls[k] != "" && calls[k] ~ /^[0-9]+$/) { if (cum[k] == 1) ccu++; else { tcal += calls[k]; tcn++ } } else cnt++
    printf "| %s | %s | %s | %s | %s | %s | %s |\n", k, (rt[k] != "" ? rt[k] : "command"), (model[k] != "" ? model[k] : "not set"), (effort[k] != "" ? effort[k] : "not set"), (("end", k) in at) ? span(at["start", k], at["end", k]) : "lost", figure(tok[k], cum[k]), figure(calls[k], cum[k])
  }
  a = at["start", "start"]; z = at["end", "end"]; printf "\n"
  for (i = 1; i <= 8; i++) if (known[i] in extras) { printf "%s: %s\n", label(known[i]), extras[known[i]]; ne++ }
  if (ne > 0) printf "\n"
  printf "Totals\n- Elapsed wall-clock: %s (%s to %s)\n", span(a, z), a, z
  printf "- Tokens: %s%s\n", (ttn > 0 ? sprintf("%.0f", ttok) : "not reported"), ((tnt + tcu) > 0 ? sprintf(" [partial: %d not reported, %d cumulative]", tnt, tcu) : "")
  printf "- Tool calls: %s%s\n", (tcn > 0 ? sprintf("%.0f", tcal) : "not reported"), ((cnt + ccu) > 0 ? sprintf(" [partial: %d not reported, %d cumulative]", cnt, ccu) : "")
}' "$1"
