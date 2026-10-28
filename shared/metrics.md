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

For a command launch, the role names what the command does (for example `tracker-write preflight`), the runtime is `command`, and the model and the effort are `not set`.

What each runtime's usage report returns is in the "Read a subagent's usage (duration, tokens, tool calls)" row of `references/runtimes.md`, and for a shell-launched agent in its "Usage from shell-launched agents" rule.

### Figures

- Roles spawned inside a delegated role get no row; their usage counts only if the parent's figure is stated to include it.
- A figure the runtime does not return is `not reported`; it is never estimated or inferred.
- A resumed role's figures are recorded as returned.
  A figure that is cumulative over earlier launches is marked `cumulative` in its row and is excluded from the run total unless the runtime separately reports a launch-scoped figure.

### Run totals

- The elapsed wall-clock from the invocation's start to its end.
- Per figure (tokens and tool calls), the sum of the launch-scoped figures that were reported.
- A per-figure total with no reported launch-scoped figure reads `not reported`, never `0`.
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
| <role> | <runtime> | <model or not set> | <effort or not set> | <duration> | <tokens> | <tool calls> |

<one line per extra of this skill: name: value>

Totals
- Elapsed wall-clock: <elapsed>
- Tokens: <sum> [partial: <n> not reported, <n> cumulative]
- Tool calls: <sum> [partial: <n> not reported, <n> cumulative]
```

The heading line names the skill, the story key, and the invocation's end state or stop reason.
Each launch gets one table row with the fields in the order above; a figure cell holds the number, `not reported`, or the number followed by `cumulative`.
Rows are listed in launch order, so the n-th row for a role is that role's n-th launch.
An extra with one value per QA round lists the values on its one line in round order, as `round 1: <value>; round 2: <value>`.
In a cell value, a `|` is written as `\|` and a line break as a space.
The bracketed `partial` note appears only under the condition in Run totals.
With no launches, the table is replaced by the line `no launches`, the elapsed wall-clock is still given, and each per-figure total reads `not applicable`.

## Independence

- Collected figures live only in one metrics file in the session's one scratch directory (the Scratch files rule in `references/runtimes.md`).
  Every skill passes each voter, engineer, and QA only its own per-role or per-story subdirectory of that directory, never the directory itself and never another role's files, so that no voter is handed another voter's votes or inputs.
- The metrics file is never named in any brief.
- The poster the consuming skill names writes the metrics file and posts the summary: the facilitator for `story-refinement`, the coordinator for `story-to-done`.
- No brief and no voter-visible record contains this invocation's metrics or another role's figures from this invocation, other than the summary comment this invocation posts at its end.
  A summary comment an earlier invocation posted on the story is not a breach.

## Posting

- Subject to the ordering below, the summary is posted at the end of every invocation that reaches a permitted post, as one comment on the story, read back, and repeated in the closing report (the facilitator's closing message where the skill has no report).
- A resumed run is a new invocation and posts its own comment, except a resume in the same session after the owner authorizes the denied tracker writes fallback, which is the same invocation.
- If the post is denied or unavailable, the summary goes in the closing report with the denied write named, and no other tool or server is tried.
- The comment contains no secrets and no local or scratch paths.
  The template has no placeholder for a path.
- Whenever the invocation ends before a post is permitted, the totals and the stop reason go in the closing report and no post is attempted.

### `story-refinement` order

- The comment is posted only when no further voter round will run in this invocation, after the pointing, unpointed, or split record and every slice re-estimate.
- On a stop before such a record exists, the comment is posted only after the three Stage 1 voter inputs are recorded and every voter context launched in the round that stopped has finished or stopped.
- Both are subject to the denied tracker writes fallback.
  While a tracker write is denied and the owner has not authorized the denied tracker writes fallback, no post is attempted.
- The comment is never posted while an anchoring recovery re-vote is still to run in this invocation.

### `story-to-done`

- The coordinator makes no tracker write other than its summary comment: the delegated engineer and QA make their own writes, and failed QA items reach the engineer in the hand-back brief, never as a coordinator tracker write.
- The coordinator never sets the story state.
