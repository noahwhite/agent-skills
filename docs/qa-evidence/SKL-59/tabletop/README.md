# SKL-59 AC2 tabletop, run at 702f53c9

This directory holds the inspectable artefacts of the AC2 behavioural round: every voter prompt, every voter output, the raw session record with the verbatim target quotation, and the elided pointing record that was posted on the fixture.

## Run statement

- Delivered text loaded: **`702f53c9ab6fe4209fd4600ad2224c6e0431671a`**, the squash merge of implementation PR #49 on `main`, read from a detached worktree checkout of that commit.
- Fixture: [SKL-72](https://linear.app/officina-pub/issue/SKL-72/tabletop-fixture-add-a-changed-only-filter-to-the-cleanup-dry-run-skl) `[Tabletop fixture] Add a --changed-only filter to the cleanup dry run (SKL-59 AC2 rerun)`, priority none, no implementation, canceled after the run.
- One durable pointing record was posted on SKL-72 and is reproduced from this directory as `pointing-record.md`.
- Voter contexts: one process and one directory per voter per round, each directory holding only that voter's prompt. Twelve separate voter processes ran across the two runs, plus two challenge-reply processes. The outputs in `runA/outputs/` and `runB/outputs/` are the raw replies of those processes, with only the CLI banner removed.
- Raw record: `raw-record.md` holds the verbatim sizing comment and every value and rationale, including the target quotation the posted record must elide.
- The prompt and output files are `.txt` because they are captured artefacts kept byte-for-byte; the repository's Markdown prose rules do not apply to them.

## The two runs

Run A demonstrates the immediate target-value stop, so that the tainted discussion is never opened.
Run B demonstrates the voter-side grounds, the challenge duty, a retraction, an unretracted ground, the void and the fresh blind re-run.

### Run A - the SM/EM sizing comment stops the round on sight

1. Three blind voters recorded values with basis-only rationales (`runA/outputs/round1-*.txt`): product owner 2, engineer one 3, engineer two 2.
2. The SM/EM sizing comment was then authored (verbatim in `raw-record.md`). Under the delivered rule it names a target value for this story implied by the inherited 3-point split pointing, so it is an anchoring event as soon as the facilitator sees it, with no challenge, restatement or retraction path.
3. The facilitator stopped the round before the discussion opened, recorded the comment, voided the consensus and the three recorded values, and re-ran the independent vote in newly created voter contexts that exclude the tainted discussion and sizing comment.
4. The blind re-run (`runA/outputs/rerun-*.txt`) recorded product owner 3, engineer one 2, engineer two 2, all with basis-only rationales.
5. The re-vote (`runA/outputs/revote-*.txt`) recorded the accepted sets `{2}`, `{2}`, `{2}`; consensus 2.

### Run B - voter grounds, a retraction and an unretracted ground

1. Three blind voters recorded values (`runB/outputs/round1-*.txt`):
   - product owner 2, rationale: "The acceptance criteria are checkable only by phrase tests in the skill text, so verification strength is the main thing I weighed."
   - engineer one 2, rationale: "Testability is weak here: the flag's behaviour can only be confirmed by reading the skill text, and that is what I weighed."
   - engineer two 5, rationale: "Coverage is thin - no test reaches the new filter path - so a silent regression there would go unnoticed."
2. The reveal recorded all three values; the discussion named high 5 and low 2 only.
3. The facilitator challenged every off-basis ground:
   - the product owner's verification-strength ground (`runB/prompts/B1-po-challenge.md`);
   - engineer one's testability ground (`runB/prompts/B1-e1-challenge.md`);
   - engineer two's coverage ground, which was not answered and so remains unretracted.
4. First challenge replies (`runB/outputs/challenge-*.txt`) restated the same ground as an "unknown", which is not a restatement as a basis driver; the facilitator did not accept them and re-challenged with that stated (`runB/prompts/*-challenge2.md`). Both voters then retracted (`runB/outputs/challenge2-*.txt`).
5. Engineer two's coverage ground was neither restated nor retracted, so it is an anchoring event. The round stopped: the consensus and the three recorded values were voided, and the independent vote was re-run blind in newly created voter contexts that exclude the tainted discussion.
6. The blind re-run (`runB/outputs/rerun-*.txt`) recorded 2, 2, 2 with basis-only rationales; the re-vote (`runB/outputs/revote-*.txt`) recorded `{2}`, `{2}`, `{2}`; consensus 2, the highest value in the intersection.

## What this establishes

- A voter's verification-strength and testability grounds were challenged and retracted; no surviving rationale carries one.
- A ground that was neither restated nor retracted stopped the round, voided the consensus and forced a fresh blind re-run in newly created contexts.
- A target value in the SM/EM sizing comment stopped the round on sight, before any discussion, and the discussion was never opened.
- Every surviving rationale in both re-runs names only drivers the pointing basis admits.
- The posted record (`pointing-record.md`) elides the target quotation and carries the standing values in the values block with the voided values under the superseded line; the verbatim quotation lives in `raw-record.md`, cited by its base name.

## Why no automated guard covers the duty

A phrase test can pin the challenge duty's text, and the mutation evidence proves that pin, but only a run can show a facilitator performing the challenge. This directory is that run: the prompts show what each voter was asked, the outputs show what each voter answered, and the record shows the challenge and its outcome.
