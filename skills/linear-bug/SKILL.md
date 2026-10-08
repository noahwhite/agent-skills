---
name: linear-bug
description: >-
  Create a Linear Bug to a fixed template - a `[Bug] <observable symptom>` title, the bug label (plus the
  operational label for tooling defects), no point estimate, and a Bug / Observed / Expected / Fix body with
  Acceptance Criteria and Definition of Done. Uses the linear CLI first and the Linear MCP server only if the CLI
  fails. Use when asked to create, file, open, or report a bug, defect, or regression in Linear.
license: Apache-2.0
compatibility: Requires the linear CLI (schpet/linear-cli); the Linear MCP server is an optional fallback.
---

# Create a Linear Bug

Use this skill to file a **Bug**: a defect in existing behaviour.
For a new capability use `linear-user-story`; for an alert or page diagnosis use `linear-investigation`.
Reproduce the failure first if you can; a bug report without a concrete observation is a hypothesis.

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
| bug label | `profile.tracker.labels.bug` |
| operational label | `profile.tracker.labels.rtb` |
| title prefix | `profile.tracker.title_prefixes.bug` if set, else `[Bug]` |
| agent stamp on or off | `profile.tracker.agent_stamp` |

## Bug rules

- **Search first** as [references/linear.md](references/linear.md) describes.
  The defect may already be tracked, and a finding inside scope an existing story owns reopens that story rather than a new bug.
- **Title:** the title prefix, then the **observable symptom**: what goes wrong, not the suspected cause.
  The cause is often wrong on first read; the symptom is what was actually seen.
- **Labels:** the bug label, plus the operational label when the defect is in existing operational tooling (CI, deploys, provisioning).
- **Estimate: none.** Priority carries the urgency; the work is unknown until the cause is found.
  Do not point a bug.
- **State:** create in the backlog state; never in progress.
- **Assignee:** always `profile.tracker.assignee`.

## Template (the description)

```markdown
**Bug**

[What is broken, and the mechanism if known. Quote the offending config/code.]

**Observed**

[Concrete evidence: the run, PR, or command, with the actual output. A bug
report without an observation is a hypothesis.]

**Expected**

[What should have happened instead.]

**Fix** - [PR link]

[What changed and why that addresses the cause rather than the symptom.]

---

**✅ Acceptance Criteria**

- [ ] The originally observed failure no longer reproduces
- [ ] The behaviour that was wrongly suppressed/triggered now works correctly
- [ ] Adjacent cases the fix could plausibly break still work

---

**✅ Definition of Done**

- [ ] Root cause identified - not just the symptom suppressed
- [ ] Fix verified against the **original failing case**, with evidence linked
- [ ] Regression protection added where feasible (test, gate, or assertion), or its absence justified
- [ ] Independently reviewed per **Review Policy**
- [ ] Docs/comments updated where the fix encodes a non-obvious constraint
- [ ] No new regressions - adjacent paths checked, not assumed
```

> On "verified against the original failing case": re-running the fixed code proves it works now, not that it fixes *the thing that broke*.
> Where the original trigger is gone, say so explicitly rather than substituting a similar-looking case.

> **Review Policy** (referenced by the DoD): "Independently reviewed" means the review of record in [references/code-review.md](references/code-review.md) - an independent reviewer (`profile.review.reviewer`), then a separate clean-context adjudicator (`profile.review.adjudicator`) - is clean on the PR head, every finding is adjudicated, and operationally risky changes are verified at runtime.
> A lighter path may lower who signs off, never what gets checked.

## Create it (linear CLI)

```bash
bug="$(mktemp "<scratch dir>/bug.XXXXXX")"
cat > "$bug" <<'EOF'
<filled-in template>
EOF

# ABC = profile.tracker.team_key (the CLI resolves the key, not the team name)
linear issue create \
  --team ABC \
  --title "<title prefix> <observable symptom>" \
  --description-file "$bug" \
  --label "<bug label>" \
  --state "<backlog state>" \
  --assignee "<assignee>" \
  --no-use-default-template --no-interactive
# add --label "<operational label>" when the defect is in CI, deploy, or provisioning tooling
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

1. The Linear MCP server's save_issue tool, in one call: `team` = `profile.tracker.team_name` (name, not key), `title`, `description` (the filled template), `labels` by name (bug label, operational label if any), `state` = the backlog state, `assignee` (for `self` the MCP takes `me`).
   Do not set an estimate.
   If the combined call is rejected, create with team, title, and description only, then update by the returned id.
2. The save_comment tool for the agent stamp, when enabled.

## After creation

The bug is in the backlog state.
Triage sets priority, not an estimate.
Implementation starts by reproducing the failure end to end, as close to how a user meets it as possible, before fixing it.
