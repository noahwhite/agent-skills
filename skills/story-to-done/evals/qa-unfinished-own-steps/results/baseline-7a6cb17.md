# Baseline run: 7a6cb17

The skill as committed on the integration branch before this case, read from a detached
checkout of `7a6cb17`.

- Configuration: `opencode run --model deepseek/deepseek-v4-pro`, default agent, auto-approved permissions.
- Launcher: `run.sh` as committed with this case, its one substitution being the checkout under test.
- Graded on: session identity and the calls `qa-runtime` recorded, never on prose.

## own-steps: 0 of 3 runs pass

| Run | Call recorded | Graded verdict | Why it fails the case |
|---|---|---|---|
| 1 | `stop`, reason naming the two QA-owned items | FAIL | the round is continued, so a stop is the wrong call |
| 2 | `resume qa-round-1-session`, round 1 | FAIL | the message restated the items, the gate, the merge rules and the verdicts |
| 3 | `resume qa-round-1-session`, round 1 | FAIL | the message restated the handback, the items, the gate, the merge rules and the verdicts |

Run 1 is what the baseline text prescribes: step 4 meets In Deployment Review, so it reports
the remainder and stops. Runs 2 and 3 continued the round, which the baseline forbids twice,
in step 3 and in the metrics run rules, and both carried the items, the merge rules and the
verdicts, so they fail the message rule as well.

The baseline therefore never passes, and its two shapes are both instructive: a coordinator
reading the baseline literally stops, and one that ignores the prohibition still hands the
agent the material AC 1 excludes.

## Controls

| Scenario | Call recorded | Verdict |
|---|---|---|
| owner-action | `stop`, reason naming the maintainer's approval | PASS |
| new-round | `launch`, `qa-round-2-session` | PASS |

Both controls pass on the baseline, so `own-steps` is the discriminating scenario.

## Call records

```text
own-steps 1: {"action": "stop", "reason": "QA not finished: evidence PR unmerged with review-of-record gate still running and one DoD check not yet run; QA owns both, no other owner named"}
own-steps 2: {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "# Continue QA round 1 - story ABC-123 ... Finish your own round-1 work that is still outstanding: ..."}
own-steps 3: {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "You are the QA agent for story ABC-123, continuing QA round 1. Your round-1 handback left two items outstanding ..."}
owner-action: {"action": "stop", "reason": "In Deployment Review - QA not finished: evidence PR unmerged (review-of-record gate still running, QA's own work) and a maintainer approval pending on the story owner"}
new-round:    {"action": "launch", "session": "qa-round-2-session", "round": 2, "label": "qa-agent-round-2"}
```

## History

An earlier version of this file recorded five runs against the earlier grader: one stop and four
resumes, each resume failing the older message check. The grader was then replaced, because it did
not read the session ledger and its term list missed the handback and the merge rules, so all runs
were repeated and re-graded at this head. The three runs above are the record of this branch; the
earlier five are superseded, not deleted from history, and their shape is preserved here: one stop
and four substantive resumes.
