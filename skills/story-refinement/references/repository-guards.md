# Repository guards

The repository guard check that Step 1 item 6 of `SKILL.md` runs.
This file is hand-written and edited directly.

The facilitator runs this check in Step 1, after the tracker-write preflight and before any voter launches, whenever the story's acceptance criteria add or change any tracked file.
A [Short path](../SKILL.md#short-path) ending skips this check.
The guards and their commands come from the repository under refinement; this skill names guard kinds only.

1. **Guard list.** The facilitator lists the guards of the repository under refinement that every added or changed tracked file must pass, not only checks on the files the story edits: test modules that scan tracked files, linters, schema or spec validators, and leak or spelling scanners.
   It discovers them from that repository's CI configuration and test suite.
   The refinement note records each guard, the command that runs it, and the discovery source.
   The guard list is part of the story surface every voter receives.
   The refined acceptance criteria require every added or changed tracked file the story commits to pass every guard on the guard list.
2. **Producible output.** When the story commits generated or frozen output (a recorded baseline, a captured dossier, or a golden file produced by a tool or by an earlier commit), the facilitator produces that output: the exact bytes the story commits where they exist before implementation, otherwise a representative sample produced the same way.
   It places the output at its intended path in a throwaway checkout, stages it there so guards that enumerate tracked files see it, and runs every guard on the guard list against it from that checkout, leaving the primary checkout unchanged.
   Every guard runs twice, once with the output staged and not yet committed and once after the output is committed there, so a guard that reads the staged set, the index or committed content sees it; a guard passes only when both runs pass.
   The throwaway checkout is a disposable clone of the repository under refinement with its own object store, never a worktree that shares one, at the revision the story's work starts from; it sits in the session's scratch directory, and the whole clone is removed after the check.
   A run passes only when the guard exits zero and reports no finding.
   The refinement note records, for each guard, the command, the exit status and the result of each run, and for a sample its provenance and coverage limits.
3. **Output not yet producible.** When the output cannot be produced before implementation because code the story writes generates it, the refinement note states why, naming the code the story writes that generates it and confirming that no tool or earlier commit produces those bytes before implementation, and the refined acceptance criteria require the committed output to pass every guard on the guard list and name the resolution the implementer may use if a guard rejects it, chosen from the kinds item 4 lists.
4. **Rejection.** When a guard rejects output checked under item 2, the refined acceptance criteria state the resolution: an exemption the story adds, scoped to its own files; a normalization; an encoding; or an amendment to the criterion that forbade one of these.
   The resolved output is re-run through the rejecting guard and passes, and through every other guard on the guard list, which pass too; the refinement note records the rejection, the resolution and the passing re-run.
5. **Stop.** When a guard on the guard list cannot be run, or the resolved output still fails any guard on the guard list, the facilitator stops and reports `needs input` to the owner naming the guard, its command and its result.
6. **Refresh.** When an accept-round amendment adds or changes a tracked file or committed output the check has not covered, the facilitator runs the check again against the amended acceptance criteria before the updated refinement comment is posted.
   A split sibling under the [Split rule](../SKILL.md#split-rule) gets the check against its own acceptance criteria before its estimate voters launch, and its guard list is part of the story surface those voters receive.
   A story whose acceptance criteria changed after an earlier check gets the check against its final acceptance criteria before the PO decides the "checked against the implementation" Definition of Ready box.
7. **No secrets.** The guard list, guard output given to a voter, and the refinement note contain no secrets: a rejection that matched secret text is cited by guard, file and line, never quoted.
