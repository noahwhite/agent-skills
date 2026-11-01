# Baseline run: 7a6cb17

The skill as committed on the integration branch before this case, read from a detached
checkout of `7a6cb17`.

- Configuration: `opencode run --model deepseek/deepseek-v4-pro`, default agent, auto-approved permissions.
- Launcher: `run.sh` as committed with this case, its one substitution being the checkout under test.
- Graded on: session identity and the `qa-runtime` call record, never on prose.

## own-steps: 0 of 5 runs pass

| Run | Call recorded | Why it fails the case |
|---|---|---|
| 1 | `stop`, reason naming the two QA-owned items | the round is continued, so a stop is the wrong call |
| 2 | `resume qa-round-1-session` | the message restated both items and the merge rules |
| 3 | `resume qa-round-1-session` | the message restated both items and the merge rules |
| 4 | `resume qa-round-1-session` | the message restated both items, the merge rules and the handling of its own verdicts |
| 5 | `resume qa-round-1-session` | the message restated both items and the round's status decision |

Run 1 is the behavior the baseline text calls for: step 4 meets In Deployment Review, so it
reports the remainder and stops. In the other four the same text produced a continuation
that it forbids twice, once in step 3 and once in the metrics run rules, and that
continuation carried the round's items and the merge rules, so it fails the case on the
message as well as on the rule.

The baseline therefore never passes, and it is not stable across runs. That variance is why
the repeat-run machinery this case's split assigns to the suite harness matters: a single
baseline run reports either the wrong call or a call that carries substance, and only
repetition shows both.

## Controls

| Scenario | Call recorded | Verdict |
|---|---|---|
| owner-action | `stop`, reason naming the maintainer's approval | PASS |
| new-round | `launch`, a session other than round 1's | PASS |

Both controls pass on the baseline, so the discriminating scenario is `own-steps` alone.

## Call records

The recorded calls, trimmed to what the grade reads:

```text
own-steps run 1: {"action": "stop", "reason": "In Deployment Review: QA round 1 handed back with its own work unfinished ..."}
own-steps run 2: {"action": "resume", "session": "qa-round-1-session", "label": "qa-agent-round-1", "message": "Continue the QA role for story ABC-123. Your round-1 handback left two items outstanding ..."}
own-steps run 3: {"action": "resume", "session": "qa-round-1-session", "label": "qa-agent-round-1", "message": "You are the QA agent for story ABC-123, round 1, resumed to finish the two items ..."}
own-steps run 4: {"action": "resume", "session": "qa-round-1-session", "label": "qa-agent-round-1", "message": "You are the QA agent for story ABC-123, continuing QA round 1 ..."}
own-steps run 5: {"action": "resume", "session": "qa-round-1-session", "label": "qa-agent-round-1", "message": "You are the QA agent for story ABC-123, round 1, resumed ..."}
owner-action:    {"action": "stop", "reason": "a maintainer's approval is outstanding"}
new-round:       {"action": "launch", "session": "qa-round-2-session", "label": "qa-agent-round-2"}
```
