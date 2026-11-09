# Superseded baseline run: 7a6cb17

Kept as history, not as current evidence. Its runs predate the checklist read-back rule and the
grader's requirement that every scenario read QA round 1's checklist file before its role call, so
they no longer re-grade to the verdicts below; the baseline was rerun with the harness at `4a622c1`
and `baseline-7a6cb17-harness-4a622c1.md` is the current baseline record.

# Baseline run: 7a6cb17

The skill as committed on the integration branch before this case, read from a detached
checkout of `7a6cb17`.

- Configuration: `opencode run --model deepseek/deepseek-v4-pro`, default agent, auto-approved permissions.
- Launcher: `run.sh` as committed with this case, its one substitution being the checkout under test.
- Graded on: session identity and the calls `qa-runtime` recorded, never on prose.
- The calls and grades behind every line below are in `baseline-7a6cb17-calls.jsonl`.

## own-steps: 0 of 3 runs pass

| Run | Call recorded | Graded verdict | Why it fails the case |
|---|---|---|---|
| 1 | `stop`, reason naming the two outstanding items | FAIL | the round is continued, so a stop is the wrong call |
| 2 | `stop`, reason naming the two outstanding items | FAIL | the same stop, and it also sends step 3 to re-clear the work |
| 3 | `stop`, reason naming the two outstanding items | FAIL | the same stop, with QA named as the owner of both items |

All three runs do what the baseline text prescribes: step 4 meets In Deployment Review, so it
reports the remainder and stops. That is the behavior the story changes, and the case fails it on
the decision itself before any message rule is reached.

## Controls

| Scenario | Call recorded | Verdict |
|---|---|---|
| owner-action | `stop`, reason naming the maintainer's approval and the evidence PR | PASS |
| new-round | `launch`, `qa-round-2-session` | PASS |

Both controls pass on the baseline, so `own-steps` is the discriminating scenario.

## Call records

```text
own-steps 1: {"action": "stop", "reason": "QA not finished: evidence PR unmerged with review-of-record gate still running, and one DoD check not yet run; QA owns both, no other owner named"}
own-steps 2: {"action": "stop", "reason": "In Deployment Review; QA round 1 not finished - evidence PR unmerged (review-of-record gate still running) and one DoD check unrun; QA owns both; stop and resume step 3 once cleared"}
own-steps 3: {"action": "stop", "reason": "In Deployment Review: QA round 1 not finished - evidence PR unmerged (review-of-record gate still running) and one DoD check not yet run; owner QA agent"}
owner-action: {"action": "stop", "reason": "..." }
new-round:    {"action": "launch", "session": "qa-round-2-session", "round": 2, "label": "qa-agent-round-2"}
```

## History

This record has been rewritten as the harness changed, and each earlier version is preserved in
git and summarized here rather than silently replaced.

- At the first head, five runs: one stop and four resumes. The resumes carried the items, the merge
  rules and the verdicts, and the grader at the time let them through, which is what drove the
  rewrite of the grader.
- At the second head, three runs on the fixed grader: one stop and two substantive resumes, the two
  resumes failing the message rule.
- At this head the scenarios no longer label each item's owner, so the classification is the
  coordinator's own; the baseline now stops in all three runs, as the text prescribes.
