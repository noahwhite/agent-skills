---
name: linear-spike
description: >-
  Create a Linear Spike (a timeboxed research story) to a fixed template - a `[Spike]` title, a fixed timebox
  instead of a point estimate, and a Spike Summary / Success Criteria / Research Questions / Deliverables /
  Definition of Done body. Uses the linear CLI first and the Linear MCP server only if the CLI fails. Use when asked
  to create, file, or open a spike, research story, timeboxed investigation, PoC, or proof-of-concept task in Linear.
license: Apache-2.0
compatibility: Requires the linear CLI (schpet/linear-cli); the Linear MCP server is an optional fallback.
---

# Create a Linear Spike

Use this skill to file a **Spike**: a timeboxed research task that reduces uncertainty before committing to implementation.
Its output is knowledge (findings, a recommendation, a Go/No-Go), not necessarily code.
For an implementation story use `linear-user-story`; for an alert or page diagnosis use `linear-investigation`.

## Read first

1. [references/profile.md](references/profile.md): how to find the profile and overlays.
2. [references/linear.md](references/linear.md): tooling (CLI first, MCP fallback, team key vs name), search before create, states, triage, estimation, relations.
3. [references/runtimes.md](references/runtimes.md): scratch directory and session label.

## Profile values

| Placeholder | Profile key |
|---|---|
| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |
| team name (for the MCP server) | `profile.tracker.team_name` |
| assignee | `profile.tracker.assignee` |
| creation state | `profile.tracker.states.backlog` |
| closing state | `profile.tracker.states.done` |
| spike label | `profile.tracker.labels.spike` |
| title prefix | `profile.tracker.title_prefixes.spike` if set, else `[Spike]` |
| agent stamp on or off | `profile.tracker.agent_stamp` |

## Spike rules

- **Search first** as [references/linear.md](references/linear.md) describes, to avoid duplicating an existing spike or story.
- **Title:** the title prefix, then the research question or goal.
- **Label:** the spike label.
- **Timeboxed, not estimated:** the timebox (e.g. 3 days) is the only measure of size.
  Do not assign a point estimate.
- **Output is knowledge:** success is validated learning - findings, a recommendation, and a Go/No-Go decision.
- **State:** create in the backlog state; never in progress.
- **Assignee:** always `profile.tracker.assignee`.

## Template (the description)

```markdown
**Spike Summary**

[One sentence describing what we're investigating and why]

**Timebox:** [X days]

---

**✅ Success Criteria**

- [ ] Specific, measurable outcomes
- [ ] Questions answered or blockers identified

---

**📝 Research Questions**

1. [Key question to answer]
2. [Key question to answer]

---

**📦 Deliverables**

- [ ] Proof-of-concept or documentation
- [ ] Go/No-Go recommendation
- [ ] If No-Go: alternative approaches identified

---

**📦 Definition of Done**

- [ ] Success criteria validated (or blockers documented)
- [ ] Findings documented in Linear
- [ ] Go/No-Go decision made
- [ ] Next steps defined
```

## Create it (linear CLI)

```bash
spike="$(mktemp "<scratch dir>/spike.XXXXXX")"
cat > "$spike" <<'EOF'
<filled-in template>
EOF

# ABC = profile.tracker.team_key (the CLI resolves the key, not the team name)
linear issue create \
  --team ABC \
  --title "<title prefix> <research question or goal>" \
  --description-file "$spike" \
  --label "<spike label>" \
  --state "<backlog state>" \
  --assignee "<assignee>" \
  --no-use-default-template --no-interactive
# do NOT pass --estimate - the timebox in the body is the only measure
```

## Agent stamp

When `profile.tracker.agent_stamp` is true, comment right after creation.

```bash
linear issue comment add <ID> --body "Worked by agent <session label> at $(date -u '+%Y-%m-%d %H:%M') UTC"
```

`<session label>` comes from the runtime as [references/runtimes.md](references/runtimes.md) maps it.

## MCP fallback (only if the CLI create fails)

Fall back only when the **create itself** fails; if creation succeeded, resume the failed step against the returned id rather than re-creating.

1. The Linear MCP server's save_issue tool, in one call: `team` = `profile.tracker.team_name` (name, not key), `title`, `description` (the filled template), `labels` (the spike label, by name), `state` = the backlog state, `assignee` (for `self` the MCP takes `me`).
   Do not set an estimate.
   If the combined call is rejected, create with team, title, and description only, then update by the returned id.
2. The save_comment tool for the agent stamp, when enabled.

## After creation

The spike is in the backlog state.
Triage sets priority, not an estimate.
When the timebox is spent, record the findings and the Go/No-Go in the issue and move it to the done state.
Any resulting implementation is separate work in its own user story.
