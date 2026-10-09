<!-- GENERATED from shared/runtimes.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->

# Runtime capability map

The skills name capabilities, not tools.
This table maps each capability to the tools of each supported runtime.
If your runtime is not listed, map each capability to its closest equivalent and say which one you used.

| Capability | Claude Code | opencode |
|---|---|---|
| Todo list (visible plan) | `TaskCreate` / `TaskUpdate` (older builds: `TodoWrite`) | `todowrite` |
| Load a skill | `Skill` tool | `skill` tool |
| Spawn a subagent | `Agent` tool, `subagent_type` and optional `model` | `task` tool, `subagent_type` |
| Define a reusable subagent | `.claude/agents/<name>.md` | `.opencode/agents/<name>.md`, `mode: subagent` |
| Choose a subagent's model | `model` parameter, or the agent file's `model:` | the agent file's `model: <provider>/<model>` |
| Ask the user a question | `AskUserQuestion` | `question` |
| Run a shell command | `Bash` | `bash` |
| Fetch a URL | `WebFetch` | `webfetch` |
| Scratch directory | `$CLAUDE_JOB_DIR/tmp` in background jobs, else `profile.workspace.scratch_dir` | `profile.workspace.scratch_dir` |
| Session label (for agent stamps) | the session or job name if set, else the session id | the session title if set, else the session id |

## Rules that follow from the map

- **Scratch files.** When neither the runtime nor `profile.workspace.scratch_dir` gives a directory, create one with `mktemp -d` and use it for the whole task.
  Never write to a fixed path under `/tmp`; parallel sessions collide there.
- **Nested subagents.** A delegated agent that runs a review gate spawns subagents of its own.
  Claude Code allows that.
  opencode stops it by default: its `subagent_depth` setting defaults to 1, and a child session gets no `task` tool unless its agent file grants `permission: { task: allow }`.
  On opencode either raise `subagent_depth` to 2 and grant `task` to the delegated agent, or have the primary session run the review roles itself after the delegated agent hands back the PR.
  The delegated agent also needs the `skill` tool to load the skill its brief names; opencode allows it by default, so check that the agent file neither denies it under `permission.skill` nor sets `tools.skill: false`.
- **Subagents have no todo tool.** A subagent keeps its checklist in a file in the scratch directory (see `todo-tracking.md`).
- **Models.** A skill that asks for a specific model role (reviewer, adjudicator) takes the model from the profile.
  If the runtime cannot run that model, stop and say so; do not silently substitute another model for a review of record.
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
