# Run metrics

Read this when a skill's metrics switch is on.
This file is the single home for what a run collects, the summary template, and the independence and posting rules.
The consuming skill decides when the switch is on and where each figure is taken; this file decides what is recorded and how the summary is posted.

## What is collected

### One row per launch

Record one row per subagent or command launch that the facilitator or coordinator itself spawns, including each re-launch and the tracker-write preflight where the skill has one.
Round counters are not rows; they are listed separately under the extras below.

Each row has these fields, in this order:

1. **Role:** the role the launch filled.
2. **Runtime:** the role's configured `runtime` value; for a `story-to-done` role, the session runtime it was launched on, since that skill's arguments set only model and effort.
   The runtime is recorded as a data value; this file names no runtime's tools or paths.
3. **Model:** the model the launch ran on.
4. **Effort:** the reasoning effort the launch ran at, or `not set` where the role has none.
5. **Duration:** the wall-clock duration the facilitator or coordinator measures from timestamps it takes immediately before the launch and after the launch returns.
6. **Tokens:** the token count the runtime's usage report returns for that launch.
7. **Tool calls:** the tool-call count the runtime's usage report returns for that launch.

What each runtime's usage report returns is in the "Read a subagent's usage (duration, tokens, tool calls)" row of `references/runtimes.md`.

### Figures

- Roles spawned inside a delegated role get no row; their usage counts only if the parent's figure is stated to include it.
- A figure the runtime does not return is `not reported`; it is never estimated or inferred.
- A resumed role's figures are recorded as returned.
  A figure that is cumulative over earlier launches is marked `cumulative` in its row and is excluded from the run total unless the runtime separately reports a launch-scoped figure.

### Run totals

- The elapsed wall-clock from the invocation's start to its end.
- Per figure (tokens and tool calls), the sum of the launch-scoped figures that were reported.
- A total is labelled `partial`, with the count of launches not reported and the count excluded as `cumulative`, only when either count is non-zero.
- An invocation that performs no launch states `no launches`, the end state or stop reason, and `not applicable` for every per-figure total.

### `story-refinement` extras

- **Accept rounds:** the number of accept rounds run.
- **Pointing rounds:** one per blind value collection: Step 3, the Step 3 re-run after a Step 4 re-refine, each split slice estimate under the Split rule, and each anchoring recovery re-run.
- **Re-votes:** one per Step 4 re-vote, including the re-vote after a re-refine's Step 3 re-run.
- **Re-refine:** whether re-refine ran.
- **Anchoring events:** the number of anchoring events.
- **Outcome:** the consensus value or size, unpointed, split with the slice count, or the stop reason, including `needs input` on a denied tracker write.
- **Denied tracker writes fallback:** whether the denied tracker writes fallback was used.

### `story-to-done` extras

- **QA rounds:** the number of QA rounds.
- **Failed items:** the failed items per QA round.
- **Fix rounds:** the number of fix rounds.
- **PRs merged:** the number of PRs merged.
- **Start:** the state found at the start, and whether the implementation step ran.
- **Time to deployment review:** from the invocation's start to the coordinator's read-back confirming `profile.tracker.states.in_deployment_review`; `not applicable` when the implementation step did not run or the story never reached that state.
- **QA round durations:** each QA round's duration, which is its launch row's duration.
- **End state:** Done or the stop reason.

## Summary template

```text
Run metrics: <skill> <story key> - <end state or stop reason>

| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |
|---|---|---|---|---|---|---|
| <role> | <runtime> | <model> | <effort or not set> | <duration> | <tokens> | <tool calls> |

<one line per extra of this skill: name: value>

Totals
- Elapsed wall-clock: <elapsed>
- Tokens: <sum> [partial: <n> not reported, <n> cumulative]
- Tool calls: <sum> [partial: <n> not reported, <n> cumulative]
```

The heading line names the skill, the story key, and the invocation's end state or stop reason.
Each launch gets one table row with the fields in the order above; a figure cell holds the number, `not reported`, or the number followed by `cumulative`.
The bracketed `partial` note appears only under the condition in Run totals.
With no launches, the table is replaced by the line `no launches` and each total reads `not applicable`.
