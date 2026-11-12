# SKL-83 evidence

Resolution path for `story-to-done`'s engineer and QA seats, run on 2026-11-11 from this branch's checkout.
`<checkout>` is the branch worktree; `<no-seats>` is a scratch git repository whose `.agent-skills/profile.yaml` is this repository's profile with the `story_to_done` keys removed.
`AGENT_SKILLS_PROFILE` was unset in both runs, so the chain selected each repository's `.agent-skills/profile.yaml`.

## With the `story_to_done` seats

```
$ python3 shared/resolve-model-role.py --role story_to_done.engineer --repo <checkout> --json
{"role": "story_to_done.engineer", "runtime": "command", "model": "deepseek/deepseek-flash", "effort": "high", "source": "<checkout>/.agent-skills/profile.yaml", "command": "opencode run --model \"{model}#{effort}\" \"Follow the instructions in the attached file exactly.\" --title \"{session_title}\" --file \"{prompt_file}\" < /dev/null > \"{output_file}\""}

$ python3 shared/resolve-model-role.py --role story_to_done.qa --repo <checkout> --json
{"role": "story_to_done.qa", "runtime": "command", "model": "deepseek/deepseek-v4-pro", "effort": "high", "source": "<checkout>/.agent-skills/profile.yaml", "command": "opencode run --model \"{model}#{effort}\" \"Follow the instructions in the attached file exactly.\" --title \"{session_title}\" --file \"{prompt_file}\" < /dev/null > \"{output_file}\""}

$ uv run --locked python -c "import yaml; p=yaml.safe_load(open('.agent-skills/profile.yaml'))['story_to_done']; print({k: (v['model'], v.get('effort')) for k, v in p.items()})"
{'engineer': ('deepseek/deepseek-flash', 'high'), 'qa': ('deepseek/deepseek-v4-pro', 'high')}
```

Both labs answered a live launch: `opencode run --model deepseek/deepseek-flash#high` and `opencode run --model deepseek/deepseek-v4-pro#high` each replied to a probe prompt.
The engineer seat's own `command`, filled with a probe brief, wrote the expected reply to its output file.

A `deepseek/deepseek-flash` orchestrator given `SKILL.md`, this profile and the invocation `story to done SKL-83` (dry run, Arguments section only) reported:

| Value | Resolved | Source |
|---|---|---|
| `engineer-model` | `deepseek/deepseek-flash` | `story_to_done.engineer.model` |
| `engineer-effort` | `high` | `story_to_done.engineer.effort` |
| `qa-model` | `deepseek/deepseek-v4-pro` | `story_to_done.qa.model` |
| `qa-effort` | `high` | `story_to_done.qa.effort` |

Both seats launch as `command` processes by the shell-launched agents rule, and its next action was `SPAWN senior engineer`.
That dry run predates the owner decision of 2026-11-11: under the current `SKILL.md`, a run whose user has not confirmed this profile as trusted asks once before step 1 whether to run the two `command` seats, and the four values above resolve the same way without asking.

## With the `story_to_done` keys removed

```
$ python3 shared/resolve-model-role.py --role story_to_done.engineer --repo <no-seats>
resolve-model-role: role story_to_done.engineer is absent from the profile; profile key story_to_done.engineer; searched: $AGENT_SKILLS_PROFILE (unset), <no-seats>/.agent-skills/profile.yaml (selected)
exit 16

$ python3 shared/resolve-model-role.py --role story_to_done.qa --repo <no-seats>
resolve-model-role: role story_to_done.qa is absent from the profile; profile key story_to_done.qa; searched: $AGENT_SKILLS_PROFILE (unset), <no-seats>/.agent-skills/profile.yaml (selected)
exit 16
```

The same dry run against this profile reported all four values `unresolved`, with the `high` effort default not applied because neither model resolved, and its next action was `STOP AND ASK`:

> The selected profile has no `story_to_done` section, so neither the senior engineer nor the QA seat has a model. What model and reasoning effort should the senior engineer use, and what model and reasoning effort should the QA agent use? Effort must be one of low, medium, high, xhigh, or max.

## Out of reach

The installed `~/.config/agent-skills/profile.yaml` and the container-repository copies are not edited here; their seats follow SKL-82 and SKL-57.

## QA round 1

Date: 2026-11-12 UTC, independent QA round 1.
Build under test: `main` at `21394d65f9d48464d6cc3c610569a588cb0b98cb`, the squash merge of PR 212, whose reviewed head is `c3d631c6adbcb054b6eaa0e4bbd2630589ed61fa`.
Environment: none; the lanes are the repository (detached worktrees of the build), GitHub and the tracker.
Fixtures: scratch git repositories whose `.agent-skills/profile.yaml` is the build's profile with one change each: seats removed, `qa` removed, the engineer `model` removed, and `qa.effort` set to `max`, left unset, or set to `ultra`.
The raw output is attached to SKL-83 as `SKL-83 QA round 1 assertions (main 21394d6)`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: dead model ids gone, Arguments defaults | Verified | `skills/story-to-done/SKILL.md` names no `claude-sonnet-5-5`, `claude-opus-5-5`, Sonnet 5.5 or Opus 5.5. The four Default cells read `profile.story_to_done.engineer`, seat effort (default `high`), `profile.story_to_done.qa`, seat effort (default `high`). |
| AC2: schema object and resolution rule | Verified | `profile/schema.json` requires `engineer` and `qa`, requires `model`, limits `effort` to the enum with default `high`, requires `command` for `runtime: command`, and rejects an unknown key such as `family`: 19 schema assertions pass. The Seat resolution section of `SKILL.md` states the per-value rule, the four differences from refinement, and the stop for a runtime it cannot launch. |
| AC3: fail closed, caller argument wins | Verified | The resolver exits 16 with no seats, with `qa` removed, and with no engineer `model` under `--require-model`. A `deepseek/deepseek-flash` orchestrator dry run with no seats reported all four values unresolved and asked for both seats. With `engineer-model=deepseek/deepseek-flash` on the invocation it took the engineer from the argument (effort `high`) and asked only for the QA seat. |
| AC4: seat pair in both profiles | Verified | `.agent-skills/profile.yaml` and `profile/example.yaml` set the engineer to `deepseek/deepseek-flash` and QA to `deepseek/deepseek-v4-pro`, both at `high` and `runtime: command`, with every placeholder double-quoted. The schema rejects an unquoted `{model}` and a model containing `;`. The dry run with seats resolved all four values without asking, then asked the one-time trust question for `command` seats. |
| AC5: baseline and mutation-proof tests | Verified | On the build, `uv run --locked python scripts/vendor_shared.py --check` exited 0 and `uv run --locked pytest -q` reported 1882 passed. On a throwaway worktree, deleting the per-value rule, re-adding `claude-sonnet-5-5` to the Arguments table, adding a `claude-opus-5-5` fallback sentence, and removing `story_to_done` from the schema each failed their named tests. |
| AC6: resolution-path evidence | Verified | The sections above and the implementer's comment of 2026-11-12 show both seats and the removed-keys stop, captured on head `82d8cc5`. Re-running the resolver on the build gave the same four values and the same exit 16. |
| AC7: adjudicator re-point and arbiter | Verified | Both profiles set `review.adjudicator` to DeepSeek V4.1 Flash (`opencode`, `deepseek/deepseek-flash`), and the Interim note is gone. No other reviewer, `pre_pr` or refinement seat line changed. `pre_pr.arbiter` on the build is Mistral Large 4 (`openrouter/mistralai/mistral-large-4-0`), which landed through the owner's PR 208 before PR 212. |
| AC8: resolver reports effort | Verified | `shared/resolve-model-role.py --json` prints `effort` as `high` or `max` when the seat sets it, omits it when unset, and exits 16 for `ultra`. `skills.json` vendors the resolver to no skill, so no copy needs updating, and the vendor check exits 0. |
| DoD: all acceptance criteria met | Verified | AC1 to AC8 above. |
| DoD: tests written and passing | Verified | AC5. |
| DoD: independently reviewed | Verified | Review 5867954215 names `c3d631c6adbcb054b6eaa0e4bbd2630589ed61fa` in its first line and as its `commit_id`, the merged head. Round 1 review 5867570770 named Codex GPT-6 Sol and DeepSeek V4.1 Flash. |
| DoD: docs updated | Verified | `shared/profile.md` documents `effort` and `--require-model`, `shared/runtimes.md` documents the codex effort flag, both vendored to every skill, and `SKILL.md` carries the Seat resolution section. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments; the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI `checks` and `discovery` passed on the reviewed head, and the full suite passed on the build. |

Closing decision: SKL-83 moves to Done once this evidence merges.
