---
name: linear-user-story
description: >-
  Create a Linear User Story (a feature, improvement, or user-facing change) to a fixed template - a
  `[User Story]` title prefix, the user-story label plus a type label, created in Backlog, and a Story Summary /
  Acceptance Criteria / Additional Context / Definition of Ready / Definition of Done body. Uses the linear CLI
  first and the Linear MCP server only if the CLI fails. Use when asked to create, file, open, write, or draft a
  user story, feature story, or improvement story in Linear.
license: Apache-2.0
compatibility: Requires the linear CLI (schpet/linear-cli); the Linear MCP server is an optional fallback.
---

# Create a Linear User Story

Use this skill to file a **User Story**: a feature, an improvement, or another user-facing change.
For a defect use `linear-bug`, for timeboxed research `linear-spike`, for an alert or page diagnosis `linear-investigation`, for an epic `linear-epic`.
After the story exists, triage and implementation follow the shared lifecycle in [references/linear.md](references/linear.md).

## Read first

1. [references/profile.md](references/profile.md): how to find the profile and overlays.
2. [references/linear.md](references/linear.md): tooling (CLI first, MCP fallback, team key vs name), search before create, states, triage, Definition of Ready, estimation, relations.
3. [references/runtimes.md](references/runtimes.md): scratch directory and session label.

## Profile values

| Placeholder | Profile key |
|---|---|
| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |
| team name (for the MCP server) | `profile.tracker.team_name` |
| assignee | `profile.tracker.assignee` |
| creation state | `profile.tracker.states.backlog` |
| story label | `profile.tracker.labels.user_story` |
| type labels | `profile.tracker.labels.feature`, `profile.tracker.labels.improvement`, `profile.tracker.labels.bug` |
| operational label | `profile.tracker.labels.rtb` |
| title prefix | `profile.tracker.title_prefixes.user_story` if set, else `[User Story]` |
| agent stamp on or off | `profile.tracker.agent_stamp` |

## User Story rules

- **Search first.** Search the target epic and the backlog before creating, as [references/linear.md](references/linear.md) describes.
  A finding inside scope an existing story owns reopens that story; do not file a duplicate.
- **Title:** the title prefix, then the capability, e.g. `[User Story] Add a shared deploy stack`.
  Check the prefix before creating.
- **Labels:** the story label plus exactly one type label:
  - feature: a new capability;
  - improvement: an enhancement to an existing feature;
  - bug: a defect fix framed as a story.
- The operational (run-the-business) label is **additive** and independent of the type: add it for maintenance work such as CI fixes, dependency upgrades, config corrections, and observability.
  A maintenance defect story carries the story label, the bug label, and the operational label.
- **State:** create in the backlog state; never create in progress.
- **Assignee:** always `profile.tracker.assignee`, never a person's named seat the profile does not name.
- **Estimate:** not set at creation; triage sets it.

## Template (the description)

```markdown
**Story Summary**

As a [role], I want [feature/capability], so that [business value].

---

**✅ Acceptance Criteria**

- [ ] Clear, testable criteria
- [ ] Use Given/When/Then format if applicable

---

**📝 Additional Context**

* Design: [Design considerations or approach]
* Docs: [Documentation to update or reference]
* Related Issues/PRs: [Links and dependencies]

---

**📦 Definition of Ready**

- [ ] Acceptance criteria are observable behaviour, and have been checked against the implementation this story modifies (not only the design), with a refinement note on the story naming the files read and any AC the code cannot support
- [ ] Where an AC says to copy an existing pattern, the ways this case differs from that pattern are enumerated
- [ ] Any artefact or method this story changes that another story also changes has the split stated
- [ ] No blocking stories, no unresolved external dependencies, and no other story already owns this scope - with the backlog search performed and any owning or overlapping story recorded on the story
- [ ] Story is estimated
- [ ] Team has necessary skills and access
- [ ] Priority is clear
- [ ] Business value understood

---

**✅ Definition of Done**

- [ ] All acceptance criteria met
- [ ] Unit/integration tests written & passing
- [ ] Independently reviewed (see **Review Policy**)
- [ ] Docs updated (if applicable)
- [ ] Verified in a deployed environment (if needed)
- [ ] No critical bugs/regressions
```

> **Review Policy** (referenced by the DoD): "Independently reviewed" means the review of record in [references/code-review.md](references/code-review.md) - an independent reviewer (`profile.review.reviewer`), then a separate clean, neutral adjudicator (`profile.review.adjudicator`) - is clean on the PR head, every finding is adjudicated, and operationally risky changes are verified at runtime.
> A lighter path may lower who signs off, never what gets checked.

## Create it (linear CLI)

Write the filled template to a unique file in the scratch directory; a fixed name races parallel sessions.

```bash
story="$(mktemp "<scratch dir>/story.XXXXXX")"
cat > "$story" <<'EOF'
<filled-in template>
EOF

# ABC = profile.tracker.team_key (the CLI resolves the key, not the team name)
linear issue create \
  --team ABC \
  --title "<title prefix> <concise capability>" \
  --description-file "$story" \
  --label "<user story label>" --label "<type label>" \
  --state "<backlog state>" \
  --assignee "<assignee>" \
  --no-use-default-template --no-interactive
# add --label "<operational label>" for maintenance work
# add --project "<epic name or id>" to file it under an epic
```

`--no-use-default-template` stops the team's default template layering over yours; `--no-interactive` stops creation blocking on a prompt.

## Agent stamp

When `profile.tracker.agent_stamp` is true, comment right after creation; the assignee stays as set, the stamp is a separate traceability signal.

```bash
linear issue comment add <ID> --body "Worked by agent <session label> at $(date -u '+%Y-%m-%d %H:%M') UTC"
```

`<session label>` comes from the runtime as [references/runtimes.md](references/runtimes.md) maps it.

## MCP fallback (only if the CLI create fails)

Fall back only when the **create itself** fails.
If creation succeeded and a later step failed (stamp, label), resume that step against the returned id; never re-create, or you duplicate the issue.

1. The Linear MCP server's save_issue tool, in one call: `team` = `profile.tracker.team_name` (the MCP takes the name, not the key, and never a team id), `title`, `description` (the filled template), `labels` by name (story label, type label, operational label if any), `state` = the backlog state, `assignee` (for `self` the MCP takes `me`), plus `project` and `priority` as needed.
   Use `state` and `assignee`, never status, state id, or assignee id fields.
   If the combined call is rejected, create with team, title, and description only, then update by the returned id.
2. The save_comment tool for the agent stamp, when enabled.

## After creation

The story is in the backlog state.
Triage it next (estimate, priority, assignee, Definition of Ready) as [references/linear.md](references/linear.md) describes; implementation starts only after that.
