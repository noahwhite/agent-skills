# SKL-59 AC2 tabletop at 702f53c9

This directory holds the inspectable artefacts of the AC2 behavioural round: twelve voter prompts, the twelve raw outputs of those voter processes, the raw session record, and the pointing record posted on the fixture.

## Run statement

- Delivered text loaded: **`702f53c9ab6fe4209fd4600ad2224c6e0431671a`**, the squash merge of implementation PR #49 on `main`, read from a detached worktree checkout of that commit.
- Fixture: [SKL-72](https://linear.app/officina-pub/issue/SKL-72/tabletop-fixture-add-a-changed-only-filter-to-the-cleanup-dry-run-skl) `[Tabletop fixture] Add a --changed-only filter to the cleanup dry run (SKL-59 AC2 rerun)`, priority none, no implementation, canceled after the run.
- One durable pointing record was posted on SKL-72; `pointing-record.md` is that record.
- Contexts: twelve separate voter processes, each in its own directory holding only its own prompt file, so no voter could see another voter's prompt, value or rationale. `prompts/` and `outputs/` are `.txt` because they are captured artefacts kept byte-for-byte, not repository prose. One challenge process overwrote its own prompt file with its answer; that prompt was restored from the same generator and values used for the run, and its answer is the process output captured separately.
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

## What this establishes

- A voter rationale weighing verification strength and another weighing testability were both challenged and retracted; no surviving rationale carries either.
- A third scripted ground, coverage, was challenged and deliberately left unretracted, and it alone stopped the round.
- The blind re-run ran in newly created contexts that exclude the tainted discussion and the sizing comment, and every surviving rationale names only drivers the pointing basis admits.
- The posted record quotes each injected ground and the facilitator's challenge verbatim, carries the standing re-run values in the values block, and records the voided value, the voided consensus position and the replacement blind vote under the superseded line.

## Why no automated guard covers the duty

A phrase test pins the facilitator's challenge duty and the mutation evidence proves that pin, but only a run can show a facilitator performing it. This directory is that run: the prompts show what each voter was asked, the outputs show what each voter answered, and the record shows each challenge with its outcome.
