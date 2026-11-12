# Interim handbacks (story-to-done)

Read this when the senior engineer hands back.

An interim handback is a handback from the senior engineer that names an awaited item of its own background work (a CI run, a deploy, a tracker move, a review in flight) and is neither a final handback nor blocked.
Naming the awaited item does not make it a blocked handback or a stated blocker.
Step 0's stated-blocker sentence covers only the other handbacks, since an interim handback never reaches the read-back.
The coordinator classifies an interim handback before step 0's checklist read-back and before step 2's deployment-review check and stop.
So the awaited item gets the deadline below, never step 0's read-back resume.

## Deadline

On an interim handback the coordinator records on the todo list the awaited item, its primary source, its target state, and an absolute UTC deadline measured from receipt of the handback: the expected duration the handback states, or 30 minutes when it states none, plus the greater of 10 minutes and 50% of that duration.
Receipt is the coordinator's first clock read after the handback arrives.
For example, a stated 4 minutes gives 14 minutes, a stated 60 minutes gives 90, and no stated duration gives 45.
It never waits on the subagent's own wake-up alone: it reaches the deadline with a bounded foreground wait on the awaited item's primary source that returns at or before the deadline (for a CI run, a watch on the run under a timeout), repeated until the deadline.
Each wait lasts the lesser of 90 seconds and the time left to the deadline less 5 seconds for process start-up, under a timeout that also bounds every read inside it, so it returns at or before the deadline, the runtime never moves it to the background, and a handback that arrives during a wait is handled when that wait returns.
With 5 seconds or less left, it starts no further wait and makes the deadline read below.
When the awaited CI run belongs to a PR, it also watches the PR, so a new head and its new run are not missed ([references/code-review.md](code-review.md), Watching the PR).

If the engineer hands back again before the deadline, the coordinator clears the deadline and handles that handback.
A handback that arrived before the deadline clears it even when the coordinator sees it only after the deadline.
Otherwise, at the deadline the coordinator reads the awaited item's state from its primary source (for a CI run, the run's status from the forge; for a tracker move, the tracker), never from the subagent, and stops.
Its report to the owner names the awaited item, its primary source, the state or read error observed, and the deadline; it launches nothing further, makes no tracker write beyond the one Boundaries permits with `metrics` on, and rules on nothing.

## Limits

This rule changes no step logic for final or blocked handbacks, and leaves step 2's stop clause, every QA step, and the no-write and no-verdict constraints unchanged; it only comes before step 0's read-back and step 2's check.
