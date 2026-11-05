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

## Resolve a model role

`shared/resolve-model-role.py` in the agent-skills repository is the one resolver that maps a model-launching role to its profile agent entry.
A skill whose scripts call it carries a vendored copy at `scripts/resolve-model-role.py`; callers and tests run it as a subprocess, never import it, and no script parses the profile itself.
A model-launching script either calls it or takes the launch command or model as a required argument its caller resolved with it.

```bash
python3 <path>/resolve-model-role.py --role <role-key> [--repo DIR] [--json] [--dry-run]
```

- **Role key.** `<role-key>` is a dotted path into the profile, such as `review.pre_pr.arbiter`.
  A role array is addressed by a zero-based index, such as `refinement.reviewers[1]`.
  A leading `profile.` is accepted and stripped from the reported role.
- **Which profile.** It reads the first of the three locations in Find the profile that exists, and a later location is never consulted.
  The repository-local candidate is `.agent-skills/profile.yaml` at the root of the repository under review, and only there.
  That root is `--repo DIR` when given; otherwise it is the git work tree holding the working directory, found with `git rev-parse --show-toplevel`.
  When git reports no work tree, the repository-local candidate does not exist.
  It is never read from the working directory path itself or from the resolver's own installation directory.
- **Output.** On success it prints five fields in this order, and nothing else on stdout: `role`, `runtime`, `model` (the effective model), `source` (the absolute path of the profile it read), and `command` only when the entry sets one.
  Text mode prints `key: value` lines, with each backslash, line feed and carriage return in a value escaped as `\\`, `\n` and `\r`.
  `--json` prints exactly one JSON object with those keys, `command` absent when the entry sets none, and the command text unchanged.
- **Entry classification.** An entry with a `command` and no `runtime` is read as `runtime: command`.
  A `runtime: command` entry is launched by its `command`: the resolver prints that command as the effective launch, with its `model` as the effective model when it sets one and `unresolved` when it does not.
  On any other runtime a `command` is ignored, so it never stands in for a missing model.
  The runtimes are the ones `profile/schema.json` defines for an agent entry; the resolver does not interpret `enabled`.
- **Fail closed.** Each of these exits with code 16 before any model call, with one line on stderr naming the profile key and every path searched (the selected path included where the selected file is at fault), nothing on stdout, and no substitute model:
  - no profile at any of the three locations;
  - a selected profile that is unreadable, not valid YAML, or not a mapping;
  - a role key absent from the profile, or a role path that does not resolve to an agent entry;
  - an entry with neither `runtime` nor `command`;
  - a runtime the profile schema does not define;
  - a model-launching runtime (`claude-code`, `opencode`, `codex`) with no `model`;
  - a `runtime: command` entry with no non-empty `command`;
  - a missing or older PyYAML, with an installation action and the resolver's own path.

  A selected file's failure never falls through to a lower-priority profile.
- **No execution.** The resolver only reads local files: it never runs the command text, starts a provider process, or makes a network request.
  `--dry-run` declares that intent for a caller, and its output is byte-identical to a normal run over the same profile and role.
- **Dependencies.** `python3`, `git` (for the repository root) and `PyYAML>=6`, installed as the consumer installs the other skill prerequisites.
- **Not yet here.** The `source` value `override`, override precedence, and wiring the resolver into launch sites belong to SKL-68; this resolver never prints `override`.

## Scratch directories

`profile.workspace.scratch_dir` is a base directory only: it is never the per-session directory, and a session never works directly in it.
The session creates exactly one directory for its lifetime with `mktemp -d` inside the base the runtime or the profile gives, and keeps every scratch artifact of that session in it (`runtimes.md`, Scratch files).
The key is optional, and no skill or overlay requires it to be set.
When the runtime gives no directory and the profile sets none, the session creates one with a standalone `mktemp -d` and uses it for the whole task.
The one deliberate exception is the merge-approval rendezvous: an engagement's shared file that the manager creates in a directory of its own inside that base before delegating (a standalone `mktemp -d` when there is no base), not a session's scratch directory (the merge-approval handshake).

## Apply overlays

`profile.overlays` maps a skill name, or a shared capability name such as `linear` or `code-review`, to a Markdown file relative to the profile file.

- After reading a skill or capability, read its overlay if one is configured.
- An overlay adds operational detail: hosts, workflows, commands, accounts, runbooks, and project rules.
- An overlay may tighten a base rule.
  It may loosen a base rule only where the base rule says the behavior is configurable.
- Where an overlay and the base disagree on a project fact, the overlay wins.
