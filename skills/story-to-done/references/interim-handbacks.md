# Interim handbacks (story-to-done)

Read this when the senior engineer or a QA agent hands back.

An interim handback is a handback from the senior engineer that names an awaited item of its own background work (a CI run, a deploy, a tracker move, a review in flight) and is neither a final handback nor blocked.
Naming the awaited item does not make it a blocked handback or a stated blocker.
A QA agent's handback that names an awaited item of its own background work (for example its evidence PR's review-of-record gate or CI run) and is neither a final handback nor blocked is an interim handback too.
A QA agent's handback that also names a failed item, or an outstanding item owned by anyone other than that QA agent (an awaited item of its own background work counts as its own), is not an interim handback; it goes to step 0's checklist read-back and step 4 as usual.
An unnamed waiting handback is a handback from the senior engineer or a QA agent that is neither a final handback nor blocked, says it waits on the role's own background work, and names no awaited item.
A QA agent's handback that names a failed item, or an outstanding item owned by anyone other than that QA agent, is not an unnamed waiting handback; it goes to step 0's checklist read-back and step 4 as usual.
An unnamed waiting handback is a stall, never an interim handback.
Step 0's stated-blocker sentence covers only the other handbacks, since neither an interim handback nor an unnamed waiting handback reaches the read-back.
The coordinator classifies an interim handback before step 0's checklist read-back and before step 2's deployment-review check and stop.
The coordinator classifies a QA agent's interim handback before step 0's checklist read-back of that QA agent and before step 4's classification.
So the awaited item gets the deadline below, never step 0's read-back resume.
The coordinator classifies an unnamed waiting handback before step 0's checklist read-back, step 2's check and step 4's classification.

## Deadline

On an interim handback the coordinator records on the todo list the awaited item, its primary source, its target state, and an absolute UTC deadline measured from receipt of the handback: the expected duration the handback states, or 30 minutes when it states none, plus the greater of 10 minutes and 50% of that duration.
Receipt is the coordinator's first clock read after the handback arrives.
For example, a stated 4 minutes gives 14 minutes, a stated 60 minutes gives 90, and no stated duration gives 45.
It never waits on the subagent's own wake-up alone: it reaches the deadline with a bounded foreground wait on the awaited item's primary source that returns at or before the deadline (for a CI run, a watch on the run under a timeout), repeated until the deadline.
Each wait lasts the lesser of 90 seconds and the time left to the deadline less 5 seconds for process start-up, under a timeout that also bounds every read inside it, so it returns at or before the deadline, the runtime never moves it to the background, and a handback that arrives during a wait is handled when that wait returns.
With 5 seconds or less left, it starts no further wait, lets the deadline pass, and only then makes the deadline read below, so that read never comes before the deadline.
When the awaited CI run belongs to a PR, it also watches the PR, so a new head and its new run are not missed ([references/code-review.md](code-review.md), Watching the PR).

If the engineer hands back again before the deadline, the coordinator clears the deadline and handles that handback.
A handback that arrived before the deadline clears it even when the coordinator sees it only after the deadline.
Otherwise, at the deadline the coordinator reads the awaited item's state from its primary source (for a CI run, the run's status from the forge; for a tracker move, the tracker), never from the subagent.
If the awaited item has concluded (success, failure, or cancelled), the coordinator resumes the same engineer with the awaited item and its observed conclusion, records the resume on the todo list, and handles the engineer's next handback as usual.
An item not yet in a terminal state is pending (a CI run `requested`, `queued`, `waiting`, `pending` or `in_progress`; a tracker item still in a non-terminal state short of its target state); any terminal state counts as concluded, so a CI run `completed` with any conclusion resumes the engineer.
If the runtime cannot resume the engineer, the coordinator reports the limitation and the observed state and stops; it spawns no new subagent for a deadline resume.
A deadline resume does not count against step 0's read-back resume cap.
With `metrics` on, each deadline resume is its own launch row.
A deadline is missed when the item is still pending or its primary source is unreadable; the coordinator counts the miss against that awaited item and records on the todo list the deadline, the state or read error observed, and the count.
After the first miss the coordinator records on the todo list a new deadline measured from the missed deadline by the same rule, and checks again at it exactly as at the initial deadline, including the before-deadline handback, the concluded-item resume and the no-resume stop.
After the second miss on the same awaited item the coordinator stops before setting another deadline; it launches nothing further, makes no tracker write beyond the one Boundaries permits with `metrics` on, and rules on nothing.
A repeated interim handback on the same awaited item does not reset the count; an interim handback on a different awaited item starts a new count.
The stop report to the owner names the awaited item, its primary source, the state or read error observed at each missed deadline, and both missed deadlines.

## QA agents

For a QA agent's interim handback the deadline rule above applies with that QA agent in place of the engineer, except for the resume message.
At a concluded deadline the coordinator resumes the same QA agent with a message that states only that the round is unfinished and names the round's scratch subdirectory and the awaited item; it carries nothing else the coordinator observed (no conclusion, no verdict, no earlier round's conclusions, no senior engineer handback).
A QA deadline resume does not increment the QA round count, does not count against step 0's read-back resume cap, and does not consume step 4's "once per observed change to the remainder" continuation allowance.
A QA agent's handback that names an awaited item the coordinator already observed concluded at an earlier deadline of that round is not an interim handback, since that item is no longer awaited; it goes to step 0's checklist read-back and step 4 as usual, so step 0's read-back resume cap and step 4's no-progress rule bound it.
With `metrics` on, each QA deadline resume is its own launch row within that round.

## Unnamed waiting handbacks

On an unnamed waiting handback the coordinator resumes that role once, asking only for the awaited item, its primary source and its expected duration.
The naming resume carries no conclusion or verdict, does not count against step 0's read-back resume cap, does not increment a QA round count or consume step 4's continuation allowance, and with `metrics` on is its own launch row.
If the answer is an interim handback as defined above, the deadline rule above applies from receipt of the answer.
A second unnamed waiting handback from the same role after that resume, within the same senior-engineer delegation or, for a QA agent, the same QA round, counts as a missed deadline and stops the coordinator as at a second miss under the two-miss stop above; the stop report names the role and both unnamed waiting handbacks.
If the runtime cannot resume the role for the naming resume, the coordinator reports the limitation and stops, and spawns no new subagent.

## Checklist reads

At each interim handback and each unnamed waiting handback the coordinator reads the role's checklist file and records on the todo list the item marked `(in progress)`, or else the first `- [ ]` item, or `none` when every item is checked, or `missing or unreadable`, and whether the contents are identical to the contents read at the previous such handback from that role (`no previous read` at the first).
The read sends nothing to the role, is separate from step 0's checklist read-back, and does not count against its resume cap.

A checklist file is stale when its contents are identical, or it is missing or unreadable, at two consecutive interim or unnamed waiting handbacks from the same role within the same senior-engineer delegation or QA round.
The coordinator then sends that role one stale-checklist resume asking it to update the checklist and name what blocks it.
The stale-checklist resume is sent at most once per senior-engineer delegation and once per QA round, never on a handback that gets the naming resume, and never on a handback on which the coordinator stops under Unnamed waiting handbacks; that stop takes precedence over this resume, and staleness is judged again at the next such handback on which the coordinator does not stop.
It carries no conclusion or verdict, does not count against step 0's read-back resume cap, does not increment a QA round count or consume step 4's continuation allowance, changes no awaited item's deadline or miss count, and with `metrics` on is its own launch row.
If the runtime cannot resume the role for the stale-checklist resume, the coordinator reports the limitation and stops, and spawns no new subagent.

## Limits

This rule changes no step logic for final or blocked handbacks, and leaves step 2's stop clause, step 4's continuation content limits, mixed-owner stop, owner-action stop, and new-round rules, and the no-write and no-verdict constraints unchanged; it only comes before step 0's read-back, step 2's check and step 4's classification, and adds only its own checklist reads, its own resumes (the deadline resume, the naming resume and the stale-checklist resume) and its own stops.
