#!/bin/sh
# story-to-done end form: checks the record, records its own row in the metrics file given as $1, then prints the
# run summary's table, the recorded extras and Totals from it.
awk '
function label(s) { if (s == "qa-rounds") return "QA rounds"; if (s == "failed-items") return "Failed items"; if (s == "fix-rounds") return "Fix rounds"; if (s == "prs-merged") return "PRs merged"; if (s == "start") return "Start"; if (s == "time-to-deployment-review") return "Time to deployment review"; if (s == "qa-round-durations") return "QA round durations"; if (s == "end-state") return "End state"; return "" }
$1 == "extra" { rest = $0; sub(/^extra[ \t]+/, "", rest); i = index(rest, "\t"); s = (i > 0 ? substr(rest, 1, i - 1) : rest); if (label(s) == "") { if (bad == "") bad = "unknown extra slug " s }; next }
$1 == "start" || $1 == "end" { k = substr($0, length($1) + length($2) + 3); parts = split(k, f, "\t"); k = f[1]
  if (parts > 1 && (k == "start" || k == "end")) { if (bad == "") bad = "the reserved label " k }
  if ($1 == "end") for (j = 2; j <= parts; j++) if (f[j] !~ /^[0-9]+( cumulative)?$/ && f[j] != "not reported") { if (bad == "") bad = "the figure " f[j] }
  if ($1 == "start" && (k in began)) { if (bad == "") bad = "the label " k " is used twice" }
  began[k] = 1
  next }
END { if (bad == "") exit 0; printf "metrics: the record is invalid: %s\n", bad > "/dev/stderr"; exit 1 }
' "$1" || exit $?
printf 'start %s end\nend %s end\n' "$(date -u +%s.%N)" "$(date -u +%s.%N)" >> "$1" && awk '
function span(a, b,  x, y, d) { split(a, x, "."); split(b, y, "."); d = (y[1] - x[1]) * 1000000000 + substr(y[2] "000000000", 1, 9) - substr(x[2] "000000000", 1, 9); return sprintf("%d.%09ds", int(d / 1000000000), d % 1000000000) }
function label(s) { if (s == "qa-rounds") return "QA rounds"; if (s == "failed-items") return "Failed items"; if (s == "fix-rounds") return "Fix rounds"; if (s == "prs-merged") return "PRs merged"; if (s == "start") return "Start"; if (s == "time-to-deployment-review") return "Time to deployment review"; if (s == "qa-round-durations") return "QA round durations"; if (s == "end-state") return "End state"; return "" }
function figure(v) { return (v == "" ? "not reported" : v) }
function esc(v) { gsub(/\|/, "\\|", v); gsub(/[\r\n]+/, " ", v); return v }
BEGIN { nknown = split("qa-rounds failed-items fix-rounds prs-merged start time-to-deployment-review qa-round-durations end-state", known, " ") }
$1 == "extra" { rest = $0; sub(/^extra[ \t]+/, "", rest); i = index(rest, "\t"); extras[(i > 0 ? substr(rest, 1, i - 1) : rest)] = (i > 0 ? substr(rest, i + 1) : ""); next }
$1 == "start" || $1 == "end" { k = substr($0, length($1) + length($2) + 3); parts = split(k, f, "\t"); k = f[1]
  if (!(k in seen)) { seen[k]; order[++n] = k }
  at[$1, k] = $2; if (parts > 1) roleish[k] = 1
  if (f[2] != "") { if ($1 == "start") rt[k] = f[2]; else tok[k] = f[2] }
  if (f[3] != "") { if ($1 == "start") model[k] = f[3]; else calls[k] = f[3] }
  if ($1 == "start" && f[4] != "") effort[k] = f[4]
  next
}
END {
  print "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |\n|---|---|---|---|---|---|---|"
  for (i = 1; i <= n; i++) { k = order[i]; tk = figure(tok[k]); cl = figure(calls[k])
    if (tk ~ /^[0-9]+$/) { ttok += tk; ttn++ } else if (tk ~ /^[0-9]+ cumulative$/) tcu++; else tnt++
    if (cl ~ /^[0-9]+$/) { tcal += cl; tcn++ } else if (cl ~ /^[0-9]+ cumulative$/) ccu++; else cnt++
    printf "| %s | %s | %s | %s | %s | %s | %s |\n", esc(k), esc(rt[k] != "" ? rt[k] : (roleish[k] ? "not reported" : "command")), esc(model[k] != "" ? model[k] : (roleish[k] ? "not reported" : "not set")), esc(effort[k] != "" ? effort[k] : (roleish[k] ? "not reported" : "not set")), ((("start", k) in at) && (("end", k) in at)) ? span(at["start", k], at["end", k]) : "lost", tk, cl
  }
  a = at["start", "start"]; z = at["end", "end"]; printf "\n"
  for (i = 1; i <= nknown; i++) if (i <= nknown && (known[i] in extras)) any = 1
  if (any) for (i = 1; i <= nknown; i++) { v = (known[i] in extras ? extras[known[i]] : ""); printf "%s: %s\n", label(known[i]), (v == "" ? "not reported" : v); ne++ }
  if (ne > 0) printf "\n"
  if (a == "" || z == "") printf "Totals\n- Elapsed wall-clock: not reported (%s to %s)\n", (a == "" ? "not recorded" : a), (z == "" ? "not recorded" : z)
  else printf "Totals\n- Elapsed wall-clock: %s (%s to %s)\n", span(a, z), a, z
  printf "- Tokens: %s%s\n", (ttn > 0 ? sprintf("%.0f", ttok) : "not reported"), ((tnt + tcu) > 0 ? sprintf(" [partial: %d not reported, %d cumulative]", tnt, tcu) : "")
  printf "- Tool calls: %s%s\n", (tcn > 0 ? sprintf("%.0f", tcal) : "not reported"), ((cnt + ccu) > 0 ? sprintf(" [partial: %d not reported, %d cumulative]", cnt, ccu) : "")
}' "$1"
