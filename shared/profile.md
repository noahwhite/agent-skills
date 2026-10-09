# Consumer profile and overlays

These skills carry process, not project facts.
Every project-specific value comes from the consumer's profile, and every operational detail comes from the consumer's overlays.

## Find the profile

Use the first file that exists:

1. The path in the `AGENT_SKILLS_PROFILE` environment variable.
2. `.agent-skills/profile.yaml` at the root of the current repository.
3. `~/.config/agent-skills/profile.yaml`.

Read the whole file once per task.
Its format is defined by `profile/schema.json` in the agent-skills repository.

## Read values

Skills cite values as `profile.<path>`, for example `profile.git.integration_branch`.

- A cited value that is set is authoritative for this project.
- A key whose schema entry has a `default` counts as set to that default when the profile omits it.
  The skill states that default where it cites the key, so you never need the schema to apply it.
- ⛔ A cited value that is unset, or a missing profile, stops the step that needs it.
  Ask the user for the value, or report the step as blocked on it.
  Never substitute a value from an example, from memory of another project, or from a guess.
- Values under the profile's `extra` key belong to overlays; base skills never read them.

## Apply overlays

`profile.overlays` maps a skill name, or a shared capability name such as `linear` or `code-review`, to a Markdown file relative to the profile file.

- After reading a skill or capability, read its overlay if one is configured.
- An overlay adds operational detail: hosts, workflows, commands, accounts, runbooks, and project rules.
- An overlay may tighten a base rule.
  It may loosen a base rule only where the base rule says the behavior is configurable.
- Where an overlay and the base disagree on a project fact, the overlay wins.
