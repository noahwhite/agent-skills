# Runtime capability map

The skills name capabilities, not tools.
This table maps each capability to Claude Code and OpenCode V2; OpenCode V1 guidance is legacy, untested.
The V2 guidance targets 2.1.2 from `@opencode/cli`, pinned by the discovery CI check; discovery is not end-to-end verification of delegated workflows or review models.
V2 supported legacy fields are translated in memory; migration to native syntax is optional, not a claim that every V1 field is broken.
If your runtime is not listed, map each capability to its closest equivalent and say which one you used.

| Capability | Claude Code | OpenCode (version-qualified) |
|---|---|---|
| Todo list (visible plan) | `TaskCreate` / `TaskUpdate` (older builds: `TodoWrite`) | V2: `todowrite` only when `experimental.todo: true` and exposed by the harness; otherwise checklist file (including primary sessions); V1: `todowrite` |
| Load a skill | `Skill` tool | `skill` tool |
| Spawn a subagent | `Agent` tool, `subagent_type` and optional `model` | V2: `subagent` tool and permission action; V1: `task` tool, `subagent_type` |
| Define a reusable subagent | `.claude/agents/<name>.md` | `.opencode/agents/<name>.md`, `mode: subagent` |
| Choose a subagent's model | `model` parameter, or the agent file's `model:` | V2: agent file `model: provider/model#variant`; V1: `model: provider/model` and separate `variant:` |
| Choose a subagent's reasoning effort | `effort` parameter (`low`, `medium`, `high`, `xhigh`, `max`) | V2: `#variant` in the agent model reference; V1: separate `variant:` (provider-specific, for example `high` or `max`) |
| Ask the user a question | `AskUserQuestion` | `question` |
| Wake the manager (merge approval) | `SendMessage` | no push capability; the approvals file plus the manager's watcher is the delivery path |
| Run a shell command | `Bash` | V2: `shell`; V1: `bash` |
| Fetch a URL | `WebFetch` | `webfetch` |
| Hosted evidence (the artefacts a session published for itself) | reachable where the session published artifacts from its own conversation on `claude.ai`: list and download them in that conversation's artifact view, and delete a single artifact with that product's per-artifact delete action; where no per-artifact delete action is exposed, the map gives none and the copy stays | none: an OpenCode session publishes no hosted artefacts, so there is nothing to list, download, or delete |
| Scratch base directory | `$CLAUDE_JOB_DIR/tmp` in background jobs, else `profile.workspace.scratch_dir` | `profile.workspace.scratch_dir` |
| Session label (for agent stamps) | the session or job name if set, else the session id | the session title if set, else the session id |
| Tracker writes from a subagent | a subagent's write can be denied by the auto-mode permission check; only the owner grants it | V2: agent `permissions` rules for `shell`; V1: `permission.bash`; probe the actual write path |

## Rules that follow from the map

- **Merge-approval wake.** The delegated engineer records the request in the approvals file before it wakes the manager.
  The wake is a prompt to read the file, never the record itself.
  Where the runtime has no push capability, the approvals file plus the manager's watcher is the delivery path.
  The handshake is defined once in the merge-approval capability.
- **Scratch files.** Create exactly one scratch directory for the session's lifetime with `mktemp -d` inside the base directory the runtime or the profile gives, and use it for every scratch artefact of the session: gate dossiers, throwaway checkouts, agent config homes, checklist files, and subagent inputs.
  The base directory is the runtime's own scratch directory when the runtime provides one (the capability row above), else `profile.workspace.scratch_dir`; it is a base only, never the directory a session works in, and the runtime's base wins when both exist.
  Pass the session's directory to every subagent and shell-launched agent you start.
  When neither the runtime nor `profile.workspace.scratch_dir` gives a directory, create one with a standalone `mktemp -d` and use it for the whole task.
  A base that cannot be created or written falls back the same way.
  Keep the base outside every repository under review: a session directory inside a checkout shows up as untracked work and fails the clean-tree preflight.
  Never write to a fixed file directly under the base directory or under `/tmp`; parallel sessions collide there.
  The one deliberate exception is the merge-approval rendezvous, which is an engagement's shared file rather than a session's scratch (the merge-approval handshake).

  ```bash
  # One scratch directory per session: inside the base directory when there is one. Run it once
  # per session and pass the printed path to every subagent and shell-launched agent.
  # scratch_base is the runtime's scratch base when it gives one, else profile.workspace.scratch_dir,
  # and is empty when neither gives one. A relative base is refused, not resolved.
  case "${scratch_base:-}" in /*) ;; *) scratch_base="" ;; esac
  if [ -n "$scratch_base" ] && mkdir -p -- "$scratch_base" && [ -w "$scratch_base" ]; then
    scratch="$(mktemp -d -- "${scratch_base%/}/session.XXXXXX")" || scratch="$(mktemp -d)"
  else
    scratch="$(mktemp -d)"
  fi
  if [ -z "$scratch" ] || [ ! -d "$scratch" ]; then
    printf 'could not create a scratch directory\n' >&2
    exit 1
  fi
  printf '%s\n' "$scratch"
  ```
- **Nested subagents.** A delegated agent that runs a review gate spawns subagents of its own.
  Claude Code allows that.
  OpenCode V2 defaults `experimental.subagent_depth` to 1; top-level `subagent_depth` is ignored with a warning.
  The built-in `general` cannot launch children: use a custom child with a `subagent` allow rule and `experimental.subagent_depth: 2` (example below), or launch review roles as shell commands per the shell-launched agents rule.
  Alternatively the primary session can run review roles after the delegated agent hands back its PR, only when the calling skill permits that handback boundary.
  V1 legacy guidance: raise top-level `subagent_depth` to 2 and grant `permission: { task: allow }` to the child.
  Both versions also need skill loading available; V2 uses the `skill` permission action, while V1 uses `permission.skill` / `tools.skill`.
- **Tracker writes from a subagent.** State only what was observed.
  On Claude Code, on 2026-10-21 a subagent's tracker write was denied by the auto-mode permission check, although a matching `permissions.allow` rule existed.
  The same write passed in a later session after the owner's own message in that session asked for PO tracker writes.
  Approval relayed by the facilitator was not accepted.
  An agent's edit of the auto-mode allow list was denied as self-modification, so only the owner can grant the permission.
  The remedy is an owner action: state the authorization in the session before the ceremony, or add the permission themselves.
  The preflight probe in Step 1 of `story-refinement` is the deciding check; an allow rule alone was not sufficient.
  On OpenCode V2, use the agent's ordered `permissions` rules with action `shell` for CLI writes; V1 uses the agent file's `permission.bash` setting.
  MCP writes have their own permission path; the real preflight probe remains decisive, not the presence of a shell allow rule.
- **Hosted evidence.** A skill that touches hosted evidence reads this row and names no host itself.
  A capability the row gives but the session cannot reach is a failure the skill reports loudly, with a non-zero exit and an error line naming it, never a silent skip and never a pass.
- **Todo availability.** The record of work is required in every runtime; only its storage differs.
  OpenCode V2 ships todos off by default (`experimental.todo: true` opts in, and the harness must still expose the tool), so the checklist file is what every session falls back to when no todo tool is exposed (see `references/todo-tracking.md`).
- **Models.** A skill that asks for a specific model role (reviewer, adjudicator) takes the model from the profile.
  If the runtime cannot run that model, stop and say so; do not silently substitute another model for a review of record.
  A gate phase launched through `run-adversarial-pipeline.sh` takes the model id with `--model` and, when the consumer configures one, an availability probe with `--probe-cmd`; the script never resolves or substitutes a model.
  The script reads only a phase's own stderr, its stdout log and its artifact, never a runtime's session log or event stream: a runtime that reports provider errors only there must surface them on the phase's stderr in its `--agent-cmd` template, or a rate-limited or unauthorized model cannot be diagnosed.
  A phase killed by its `--timeout` exits 19, and a failed availability check exits 20 unless the phase deadline expired during the check, in which case the timeout-kill rule (19) applies; report either as a failed phase, never as a clean one.
  While a gate-script phase spends model budget it reports progress on stderr (first after a second, then at least every 30 seconds) and ends with one completion line carrying the elapsed time and its exit status, on failure as well as success; a dossier and record subagent flow has no such lines.
  The same holds for a reasoning effort a skill asks for: if the runtime or model does not offer that level, stop and say so; never substitute another level.
  On Claude Code, `CLAUDE_CODE_EFFORT_LEVEL` overrides every subagent's effort and removes the `effort` parameter; if it differs from the effort a skill asks for, stop and say so.
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is an on/off flag: when it is on, the `model` parameter is removed and a subagent runs on `CLAUDE_CODE_SUBAGENT_MODEL`, or on the main session's model when that is unset or `inherit`; if that model differs from the one a skill asks for, stop and say so.
  Under the flag, a fork and a skill that runs in a subagent with `model: inherit` still run on the main session's model, and the built-in Explore subagent runs on its own listed model when only the flag is set; never use one of these for a model-pinned role.
- **Shell-launched agents.** An agent with `runtime: command` or `runtime: codex` in the profile runs as a separate process.
  Give it its prompt as a file and read its result from its output file.
  Never leave its stdin on the terminal (a CLI agent run in the background otherwise waits on stdin until it times out): redirect stdin from the prompt file when the CLI reads its prompt on stdin, as Codex does with `-`, and from `/dev/null` otherwise.
  For `runtime: codex`, the base command is `codex exec -m <model> -s read-only --cd <checkout> -o <output_file> - < <prompt_file>`.
  The `-` makes Codex read the prompt from stdin, which here is the prompt file, so a long prompt never hits the argument-length limit and nothing waits on a terminal.
  Codex's `read-only` and `workspace-write` sandboxes need bubblewrap on Linux; where it cannot start, every command fails with a `bwrap:` error and the review comes back empty.
  ⛔ That error means the reviewer cannot run as configured: report the review unavailable, never empty or clean, and do not substitute another reviewer.
  The fix is to make the sandbox work (for example, allow unprivileged user namespaces on the host or container).
  `-s danger-full-access` is acceptable only when the operator has confirmed that the whole session already runs inside an outer sandbox they control, such as a disposable container or VM holding no credentials beyond what the review needs; the profile or an overlay records that confirmation, and an agent never assumes it.
  A worktree is not that boundary: it only keeps edits out of the main checkout, while the process can still read credentials, reach the network, and write anywhere the user can.
  Under that flag, run every phase against a throwaway detached worktree, never the primary checkout, and afterwards confirm that `git status --porcelain` of the primary checkout is unchanged.

## OpenCode V2 configuration and invocation

Use native V2 syntax in new examples, keeping each agent or command entry entirely native or entirely legacy rather than mixing nested formats.
`permissions` is an ordered array of `{action, resource, effect}` rules; the last matching rule wins, so broad rules precede exceptions.
V2 action `subagent` replaces V1 `task`, and `shell` replaces V1 `bash`.
This custom child can run nested reviewers when the parent's permissions also allow launching it:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "experimental": { "subagent_depth": 2 },
  "agents": {
    "delegated-engineer": {
      "description": "Implement a story and run its review gates",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-5#high",
      "permissions": [
        { "action": "subagent", "resource": "*", "effect": "allow" },
        { "action": "skill", "resource": "*", "effect": "allow" }
      ]
    }
  }
}
```

The model above illustrates syntax, not a substitute for a profile's required role model.
Scope child-agent permissions to the review roles needed where possible, and check the actual exposed tools before delegation.
For CLI tracker writes, a V2 agent permission rule has the shape `{ "action": "shell", "resource": "linear *", "effect": "allow" }`; this does not authorize unrelated write paths or override a denial elsewhere.

### Automation

For the V2 2.1.2 CLI, use `opencode run --agent ID --model provider/model#variant "PROMPT"` for automation, not flags on the root interactive command.
Replace placeholders with a real configured agent ID and the exact required provider, model, and variant.
The root TUI rejects `--agent` and `--model`; V1 root invocations using those flags are legacy guidance, not V2 commands.
Check `opencode --version` and `opencode run --help` on the installed binary before relying on its invocation contract.
For long or sensitive briefs, use a prompt file through the supported invocation path rather than placing secrets in argv, and obey the shell-launched agents stdin rule above.

### Interactive sessions

Use configuration defaults (`default_agent` and root `model`) and reusable agent files for interactive startup, or command frontmatter to select an explicit agent and `model: provider/model#variant` for that command.
Selecting a primary agent does not change the session model, and changing `default_agent` does not replace the agent already stored on an existing session.
The root `model` default can retain its `#variant` for fresh sessions; a root default or primary agent file alone does not pin an existing session's model and effort, so verify the effective model and variant on a resumed or already-selected session.
Use an explicit command model reference for a variant-pinned interactive role and verify the effective model before starting the role.
For per-process defaults, `OPENCODE_CONFIG_CONTENT` can supply inline configuration with a private server (`opencode --standalone`), rather than assuming a previously started shared server adopts a new client's environment.
For example, `OPENCODE_CONFIG_CONTENT='{"default_agent":"build","model":"anthropic/claude-sonnet-4-5"}' opencode --standalone` sets fresh-session defaults, not a guarantee for a resumed session or reasoning variant.
Do not change shared service settings or restart another session's server to force a role's defaults.

Authoritative V2 references:

- [Agents](https://opencode.ai/v2/docs/agents): model references, custom children, and ordered permissions.
- [Config](https://opencode.ai/v2/docs/config): experimental depth/todo settings and root model limits.
- [V1 migration](https://opencode.ai/v2/docs/migrate-v1): supported translation versus ignored fields.
- [CLI](https://opencode.ai/v2/docs/cli): automation and private-server startup.
- [Skills](https://opencode.ai/v2/docs/skills): skill loading and discovery.
