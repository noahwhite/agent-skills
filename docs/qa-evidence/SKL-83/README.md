# SKL-83 evidence

Resolution path for `story-to-done`'s engineer and QA seats, run on 2026-11-11 from this branch's checkout.
`<checkout>` is the branch worktree; `<no-seats>` is a scratch git repository whose `.agent-skills/profile.yaml` is this repository's profile with the `story_to_done` keys removed.
`AGENT_SKILLS_PROFILE` was unset in both runs, so the chain selected each repository's `.agent-skills/profile.yaml`.

## With the `story_to_done` seats

```
$ python3 shared/resolve-model-role.py --role story_to_done.engineer --repo <checkout> --json
{"role": "story_to_done.engineer", "runtime": "command", "model": "deepseek/deepseek-flash", "source": "<checkout>/.agent-skills/profile.yaml", "command": "opencode run --model \"{model}#{effort}\" \"Follow the instructions in the attached file exactly.\" --title \"{session_title}\" --file \"{prompt_file}\" > \"{output_file}\""}

$ python3 shared/resolve-model-role.py --role story_to_done.qa --repo <checkout> --json
{"role": "story_to_done.qa", "runtime": "command", "model": "deepseek/deepseek-v4-pro", "source": "<checkout>/.agent-skills/profile.yaml", "command": "opencode run --model \"{model}#{effort}\" \"Follow the instructions in the attached file exactly.\" --title \"{session_title}\" --file \"{prompt_file}\" > \"{output_file}\""}

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
