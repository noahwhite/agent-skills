# SKL-59 AC2 tabletop at 702f53c9

This directory holds the inspectable artefacts of the AC2 behavioural round: twenty-four voter prompts, the twenty-four raw outputs of those voter processes, the raw session record, and the pointing record posted on the fixture.

## Run statement

- Delivered text loaded: **`702f53c9ab6fe4209fd4600ad2224c6e0431671a`**, the squash merge of implementation PR #49 on `main`, read from a detached worktree checkout of that commit.
- Fixture: [SKL-72](https://linear.app/officina-pub/issue/SKL-72/tabletop-fixture-add-a-changed-only-filter-to-the-cleanup-dry-run-skl) `[Tabletop fixture] Add a --changed-only filter to the cleanup dry run (SKL-59 AC2 rerun)`, priority none, no implementation, canceled after the run.
- One durable pointing record was posted on SKL-72; `pointing-record.md` is that record.
- Contexts: twenty-four separate voter processes, each in its own directory holding only its own prompt file, so no voter could see another voter's prompt, value or rationale. `prompts/` and `outputs/` are `.txt` because they are captured artefacts kept byte-for-byte, not repository prose. One challenge process overwrote its own prompt file with its answer; that prompt was restored from the same generator and values used for the run, and its answer is the process output captured separately.
- Raw record: `raw-record.md` holds every value and rationale, the sizing comment verbatim, and the facilitator's challenge text.

## One round, three injected grounds, one stop

1. **Blind values.** Three voters recorded values and rationales in separate processes, before any sizing context and before the reveal (`prompts/v1-*-prompt.txt`, `outputs/v1-*-output.txt`):
   - product owner 2, "The acceptance criteria are checkable only by phrase tests in the skill text, so verification strength is the main thing I weighed."
   - engineer one 3, "Testability is weak here: the flag's behaviour can only be confirmed by reading the skill text, and that is what I weighed."
   - engineer two 5, "Coverage is thin - no test reaches the new filter path - so a silent regression there would go unnoticed."
2. **The reveal and the SM/EM sizing context.** All three values were recorded, then the SM/EM sizing comment was offered. It names an already-estimated item's recorded value together with one basis difference, which the 2026-10-24 owner amendment permits after the reveal, so it raises no anchoring event and the round continues. Its verbatim text is in `raw-record.md` and quoted in the record.
3. **The discussion and the challenges.** The discussion named high 5 and low 2 only. The facilitator then challenged every off-basis ground in the same round, and both the ground and the challenge are quoted verbatim in `pointing-record.md`:
   - the product owner's verification-strength ground, challenged and **retracted** (`prompts/v1-po-challenge-prompt.txt`, `outputs/v1-po-challenge-output.txt`);
   - engineer one's testability ground, challenged and **retracted** (`prompts/v1-e1-challenge-prompt.txt`, `outputs/v1-e1-challenge-output.txt`);
   - engineer two's coverage ground, challenged and left **unretracted** (`prompts/v1-e2-challenge-prompt.txt`, `outputs/v1-e2-challenge-output.txt`).
4. **The stop.** Engineer two's coverage ground is neither restated as a basis driver nor retracted, so it is an anchoring event. The facilitator stopped the round there: the consensus position and the vote that ground carries were voided, and the discussion was not resumed.
5. **The blind re-run.** The independent vote was re-run in newly created voter contexts that exclude the tainted discussion and the sizing comment (`prompts/v2-*-prompt.txt`, `outputs/v2-*-output.txt`): product owner 2, engineer one 2, engineer two 3, all with basis-only rationales.
6. **The re-vote.** The discussion on the standing values named high 3 and low 2 only; the re-vote recorded `{2}`, `{2}`, `{2}` (`prompts/v3-*-prompt.txt`, `outputs/v3-*-output.txt`); consensus 2, the highest value in the intersection.

## Round 2 - the off-basis SM/EM sizing note, stopped on sight

1. **Blind values.** Three fresh voter contexts recorded `3`, `3`, `3` with basis-only rationales (`prompts/r2-*-prompt.txt`, `outputs/r2-*-output.txt`).
2. **The sizing note.** The SM/EM then offered a note naming an earlier tabletop's recorded value as this fixture's target: "The earlier tabletop on this same fixture settled at three, so this one should settle at three as well."
3. **The stop on sight.** A target value for this story is an anchoring event as soon as the facilitator sees it, with no challenge, restatement or retraction path. The round stopped before the discussion opened, the consensus position and the three recorded values were voided, and the discussion was never resumed.
4. **The blind re-run.** The independent vote was re-run in newly created contexts that exclude the tainted sizing comment (`prompts/r3-*-prompt.txt`, `outputs/r3-*-output.txt`): product owner 2, engineer one 3, engineer two 2.
5. **The re-vote and the no-consensus decision.** The discussion named high 3 and low 2; the re-vote recorded `{2}`, `{3}` and `{2, 3}` (`prompts/r4-*`, `outputs/r4-*`), so the intersection is empty. Each voter then recorded the paths it accepts (`prompts/r5-*`, `outputs/r5-*`): product owner `{re-refine, leave unpointed}`, engineer one `{re-refine}`, engineer two `{re-refine}`; the group-chosen path is re-refine. The fixture is disposed at that point and the re-refine is not run.

## What this establishes

- A voter rationale weighing verification strength and another weighing testability were both challenged and retracted; no surviving rationale carries either.
- A third scripted ground, coverage, was challenged and deliberately left unretracted, and it alone stopped round one.
- Round two injected the off-basis SM/EM sizing note, which stopped the round on sight.
- The blind re-run ran in newly created contexts that exclude the tainted discussion and the sizing comment, and every surviving rationale names only drivers the pointing basis admits.
- The posted record quotes each injected ground and the facilitator's challenge verbatim in both rounds, carries the standing re-run values in the values block, and records the voided values, the voided consensus position and the replacement blind vote under the superseded line.

## Why no automated guard covers the duty

A phrase test pins the facilitator's challenge duty and the mutation evidence proves that pin, but only a run can show a facilitator performing it. This directory is that run: the prompts show what each voter was asked, the outputs show what each voter answered, and the record shows each challenge with its outcome.
