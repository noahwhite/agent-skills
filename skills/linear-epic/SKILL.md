---
name: linear-epic
description: >-
  Create an Epic, which is a Linear project, to a fixed template - the profile's epic name prefix, the epic label
  plus a T-shirt size label, the profile's project lead and icon, and a Goal/Outcome + Business Value + Definition
  of Ready + Definition of Done overview. Uses the linear CLI first and the Linear MCP server only if the CLI fails.
  Use when asked to create, file, or open an epic, a Linear project, or an initiative-level container in Linear.
license: Apache-2.0
compatibility: Requires the linear CLI (schpet/linear-cli); the Linear MCP server is an optional fallback.
---

# Create a Linear Epic

Use this skill to create an **Epic**.
In Linear an epic is a **project**, not an issue, so this uses `linear project create`, not `linear issue create`.
Stories are then filed into the epic with the other `linear-*` skills through their `--project` flag.

## Read first

1. [references/profile.md](references/profile.md): how to find the profile and overlays.
2. [references/linear.md](references/linear.md): tooling (CLI first, MCP fallback, team key vs name), search before create, epic lifecycle.
3. [references/runtimes.md](references/runtimes.md): scratch directory.

## Profile values

| Placeholder | Profile key |
|---|---|
| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |
| team name (for the MCP server) | `profile.tracker.team_name` |
| name prefix | `profile.tracker.epic.name_prefix` |
| epic label | `profile.tracker.epic.label` |
| project lead | `profile.tracker.epic.lead` |
| icon | `profile.tracker.epic.icon` |
| size labels | `profile.tracker.epic.size_labels.small`, `profile.tracker.epic.size_labels.medium`, `profile.tracker.epic.size_labels.large`, `profile.tracker.epic.size_labels.extra_large` |
| cycle length | `profile.tracker.cycle_weeks` |

## Epic rules

- **Search first:** run `linear project list`; the epic may already exist under a sibling name.
- **Name:** the name prefix, then the epic name, e.g. `[EPIC] Self-serve onboarding`.
- **Labels:** the epic label **plus** exactly one size label.
  Pass the size label's full name from the profile, not a short form like `Medium`.
- **Lead:** always `profile.tracker.epic.lead`, never a person's named seat the profile does not name.
- **Icon:** always `profile.tracker.epic.icon`; do not pick a custom icon.
- **Overview:** the template goes in the project **overview** (`--content-file`), never in `--description`, which Linear caps at 255 characters.
- **No "Issues / Stories" or "Related Projects or Epics" sections** in the overview; Linear's UI already shows them.
- **Status:** create as backlog; move to in progress when its first story starts.
  An epic with open stories is not closed.

## T-shirt sizing

A cycle is `profile.tracker.cycle_weeks` weeks long.

| Size | Complexity / Effort | Typical time |
|------|---------------------|--------------|
| **Small (S)** | Well-understood, minor dependencies, low risk | 1-2 cycles |
| **Medium (M)** | Standard feature, some integration, moderate unknowns | 3-4 cycles |
| **Large (L)** | Complex logic, multiple touchpoints, significant risk | about a quarter |
| **Extra Large (XL)** | Cross-team, large architectural shifts | multiple quarters - break down first |

Break an XL epic into smaller epics before starting it.

## Template (the overview)

```markdown
### Goal / Outcome

[One paragraph describing what this epic aims to achieve]

**Business Value:**
[Explain why this work matters - what problem does it solve? What risk does it mitigate? What capability does it enable? How does it benefit the user/business?]

[Additional details about the approach, architecture diagrams, or bullet points expanding on the goals]

---

### Definition of Ready (DoR)

- [ ] Epic goal is clearly articulated and aligns with team/organization objectives
- [ ] Relevant stakeholders are identified
- [ ] Dependencies and constraints are understood
- [ ] Acceptance Criteria (AC) defined at a high level
- [ ] Estimation: T-shirt size or rough timebox assigned
- [ ] Stories are sliced into deliverables, and no story tracks a decision document (ADR) as an umbrella container

---

### Definition of Done (DoD)

- [ ] All associated stories are completed and accepted
- [ ] All functionality works as expected in the pre-production environment
- [ ] Documentation is written or updated as needed
- [ ] Monitoring and health checks are validated
- [ ] [Epic-specific completion criteria]
```

"Pre-production environment" means the non-production entries of `profile.environments`.

## Create it (linear CLI)

```bash
epic="$(mktemp "<scratch dir>/epic.XXXXXX")"
cat > "$epic" <<'EOF'
<filled-in overview>
EOF

# ABC = profile.tracker.team_key (the CLI resolves the key, not the team name)
linear project create \
  --team ABC \
  --name "[EPIC] <epic name>" \
  --content-file "$epic" \
  --lead "<project lead>" \
  --icon "<icon>" \
  --status backlog \
  --label "<epic label>" --label "<size label>"
```

## MCP fallback (only if the CLI create fails)

The Linear MCP server's save_project tool: `name` (with the prefix), `addTeams` = [`profile.tracker.team_name`] (the tool has **no** team field; attach the team through `addTeams` or `setTeams`, which take the name), the overview as `description` (**not** `content`; `summary` is the 255-character short field), `lead` (for `@me` the MCP takes `me`), `icon`, and `labels` (epic label and size label, by name).
save_project exposes only the project lead, not arbitrary members.
If creation succeeded and a later step failed, update by the returned id; never re-create.

## After creation

The epic is an empty project.
File its stories with `linear-user-story`, `linear-bug`, `linear-spike`, or `linear-investigation`, passing `--project "<epic name or id>"`.
Move the epic to in progress once its first story starts.
