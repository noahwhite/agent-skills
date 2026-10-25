# SKL-59 AC2 tabletop at 702f53c9

This directory holds the inspectable artefacts of the AC2 behavioural round: twelve voter prompts, the twelve raw outputs of those voter processes, the raw session record with the verbatim target quotation, and the elided pointing record posted on the fixture.

## Run statement

- Delivered text loaded: **`702f53c9ab6fe4209fd4600ad2224c6e0431671a`**, the squash merge of implementation PR #49 on `main`, read from a detached worktree checkout of that commit.
- Fixture: [SKL-72](https://linear.app/officina-pub/issue/SKL-72/tabletop-fixture-add-a-changed-only-filter-to-the-cleanup-dry-run-skl) `[Tabletop fixture] Add a --changed-only filter to the cleanup dry run (SKL-59 AC2 rerun)`, priority none, no implementation, canceled after the run.
- One durable pointing record was posted on SKL-72; `pointing-record.md` is that record.
- Contexts: twelve separate voter processes. One challenge process overwrote its own prompt file with its answer; that prompt was restored from the same generator and values used for the run, and its answer is the process output captured separately. Each ran in its own directory holding only its own prompt file, so no voter could see another voter's prompt, value or rationale. `prompts/` and `outputs/` are `.txt` because they are captured artefacts kept byte-for-byte, not repository prose.
- Raw record: `raw-record.md` holds the verbatim sizing comment and every value and rationale, including the target quotation the posted record must elide.

## One round, three injected grounds, one void

The AC2 round is a single ceremony on one fixture, in this order.

1. **Blind values.** Three voters recorded values and rationales in separate processes (`prompts/v1-*-prompt.txt`, `outputs/v1-*-output.txt`):
   - product owner 2, weighing verification strength;
   - engineer one 3, weighing testability;
   - engineer two 5, weighing coverage.
2. **The facilitator's challenges to the recorded voter grounds.** Every recorded ground was challenged in the same round, before any sizing context was offered, and the challenge text is reproduced verbatim in `pointing-record.md`:
   - the product owner's verification-strength ground, challenged and **retracted** (`prompts/v1-po-challenge-prompt.txt`, `outputs/v1-po-challenge-output.txt`);
   - engineer one's testability ground, challenged and **retracted** (`prompts/v1-e1-challenge-prompt.txt`, `outputs/v1-e1-challenge-output.txt`);
   - engineer two's coverage ground, challenged and left **unretracted** (`prompts/v1-e2-challenge-prompt.txt`, `outputs/v1-e2-challenge-output.txt`).
3. **The SM/EM sizing comment, seen after the challenges.** The sizing comment was then authored and seen by the facilitator. Its verbatim text is in `raw-record.md`; under the product owner's 2026-10-25 ruling it names a target value for this story implied by the inherited 3-point split pointing, so it is an anchoring event as soon as it is seen and has no restatement or retraction path.
4. **The void, on sight.** Seeing that comment is what stopped the round: the discussion was never opened, the consensus and the three recorded values were voided, and engineer two's unretracted coverage ground stands as a second anchoring event.
5. **The blind re-run.** The independent vote was re-run in newly created voter contexts that exclude the tainted discussion and the sizing comment (`prompts/v2-*-prompt.txt`, `outputs/v2-*-output.txt`): product owner 2, engineer one 2, engineer two 3, all with basis-only rationales.
6. **The re-vote.** The discussion named high 3 and low 2 only; the re-vote recorded `{2}`, `{2}`, `{2}` (`prompts/v3-*-prompt.txt`, `outputs/v3-*-output.txt`); consensus 2, the highest value in the intersection.

## What this establishes

- A voter rationale weighing verification strength and another weighing testability were both challenged and retracted; no surviving rationale carries either.
- A third scripted ground, coverage, was challenged and deliberately left unretracted, and it stopped the round with the consensus voided.
- An SM/EM sizing comment naming the inherited value is an anchoring event on sight; the discussion was never opened on it, so nothing resumed the tainted discussion.
- The blind re-run ran in newly created contexts that exclude the tainted discussion and the sizing comment, and every surviving rationale names only drivers the pointing basis admits.
- The posted record carries the standing re-run values in the values block and the voided values under the superseded line, quotes each voter ground and the facilitator's challenge verbatim, and elides only the target quotation, which lives in `raw-record.md` and is cited there by base name.

## Why no automated guard covers the duty

A phrase test pins the facilitator's challenge duty and the mutation evidence proves that pin, but only a run can show a facilitator performing it. This directory is that run: the prompts show what each voter was asked, the outputs show what each voter answered, and the record shows each challenge with its outcome.
