---
name: linear-investigation
description: >-
  Create a Linear Investigation for an incident raised by an alert or page, to a fixed template - an
  `[Investigation] <alert reference> - <symptom> (<affected component>)` title, the investigation and operational
  labels, no point estimate, routing (cycle, epic) from the consumer overlay, and an Incident / Findings /
  Remediation / Evidence body. Uses the linear CLI first and the Linear MCP server only if the CLI fails. Use when
  investigating an alert, page, or on-call incident and the diagnosis, root cause, and follow-ups need a Linear issue.
license: Apache-2.0
compatibility: Requires the linear CLI (schpet/linear-cli); the Linear MCP server is an optional fallback.
---

# Create a Linear Investigation

Use this skill **whenever you investigate an incident raised by an alert or page**.
Create the Investigation before or while investigating, so the diagnosis, root cause, and follow-ups are captured even when the fix lands in a separate story.
The remediation itself is a separate `linear-bug` or `linear-user-story`; the investigation closes on diagnosis, not on the fix.

## Read first

1. [references/profile.md](references/profile.md): how to find the profile and overlays.
2. [references/linear.md](references/linear.md): tooling (CLI first, MCP fallback, team key vs name), search before create, states, relations.
3. [references/runtimes.md](references/runtimes.md): scratch directory and session label.
4. This skill's overlay, if configured: it names the paging system, how to read an incident from it, and where investigations are routed (cycle, epic).

## Profile values

| Placeholder | Profile key |
|---|---|
| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |
| team name (for the MCP server) | `profile.tracker.team_name` |
| assignee | `profile.tracker.assignee` |
| creation state | `profile.tracker.states.backlog` |
| closing state | `profile.tracker.states.done` |
| investigation label | `profile.tracker.labels.investigation` |
| operational label | `profile.tracker.labels.rtb` |
| title prefix | `profile.tracker.title_prefixes.investigation` if set, else `[Investigation]` |
| agent stamp on or off | `profile.tracker.agent_stamp` |

## Investigation rules

- **Search first** as [references/linear.md](references/linear.md) describes.
  The incident may already have an investigation, and a finding inside scope an existing story owns reopens that story.
- **Title:** the title prefix, the paging system's incident reference, the observable symptom, and the affected component, e.g. `[Investigation] Page #123 - API 5xx rate above threshold (api-gateway)`.
- **Labels:** the investigation label plus the operational label.
- **Routing:** the consumer overlay says which cycle and which epic an investigation goes under.
  If the overlay routes it to an epic that does not exist yet, create that epic first with the `linear-epic` skill, then file the investigation under it.
  With no overlay routing, file it in the team with no cycle or epic and say so in your report.
- **Estimate: none.** Like spikes and bugs, an investigation is not pointed.
- **State:** create in the backlog state; never in progress.
- **Assignee:** always `profile.tracker.assignee`.
- **Closing:** move it to the done state once the root cause is established and every follow-up is filed.
  The remediation is separate work with its own story and PR, not a condition for closing.

## Template (the description)

```markdown
**Incident**

<Paging system> <incident reference> - <alert title> (<service>, <environment>, <affected component>).

---

**🔍 Findings**

- What fired, when, and where (component / service / environment), with the raw signal (the log line or metric).
- Root cause - **verified against ground truth** (the running system, logs, repository), never assumed.

---

**🛠️ Remediation**

- What was done and/or recommended, and the fix story/PR that resolves it - or an explicit note that remediation is outstanding, and why.

---

**📎 Evidence**

- Links: the paging incident, log and metric queries, commands run, PRs, and related stories.
```

## Create it (linear CLI)

```bash
invest="$(mktemp "<scratch dir>/investigation.XXXXXX")"
cat > "$invest" <<'EOF'
<filled-in template>
EOF

# ABC = profile.tracker.team_key (the CLI resolves the key, not the team name)
linear issue create \
  --team ABC \
  --title "<title prefix> <incident ref> - <symptom> (<affected component>)" \
  --description-file "$invest" \
  --label "<investigation label>" --label "<operational label>" \
  --state "<backlog state>" \
  --assignee "<assignee>" \
  --no-use-default-template --no-interactive
# add the overlay's routing, e.g. --cycle active and --project "<epic name or id>"
# do NOT pass --estimate
```

## Agent stamp

When `profile.tracker.agent_stamp` is true, comment right after creation.

```bash
linear issue comment add <ID> --body "Worked by agent <session label> at $(date -u '+%Y-%m-%d %H:%M') UTC"
```

`<session label>` comes from the runtime as [references/runtimes.md](references/runtimes.md) maps it.

## MCP fallback (only if the CLI create fails)

Fall back only when the **create itself** fails; if creation succeeded, resume the failed step against the returned id rather than re-creating.

1. The Linear MCP server's save_issue tool, in one call: `team` = `profile.tracker.team_name` (name, not key), `title`, `description` (the filled template), `labels` by name (investigation label, operational label), `state` = the backlog state, `assignee` (for `self` the MCP takes `me`), and the overlay's `project` and `cycle`.
   The MCP `cycle` field takes the cycle's number or name (find it with the list_cycles tool), not `active`.
   Do not set an estimate.
   If the combined call is rejected, create with team, title, and description only, then update by the returned id.
2. The save_comment tool for the agent stamp, when enabled.

## After creation

Investigate against ground truth: the running system, its logs, and the repository.
When the root cause is established and any follow-up fix stories are filed, move the investigation to the done state; do not hold it open for the remediation.
