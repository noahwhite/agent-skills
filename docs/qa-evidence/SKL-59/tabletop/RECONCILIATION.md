# Reconciliation after QA round 2

QA round 2 (tracker comment `89a12de3`) ruled AC2 outstanding for two reasons: the live SKL-72 pointing record did not reproduce the committed captures, and the rejected target-value re-vote rationales lacked the fresh blind recovery the delivered rule requires. This file records what was corrected and what was run.

## 1. The SKL-72 record, corrected to the captures

The live SKL-72 comments had drifted from the committed record. Their round-two re-vote rationales and the engineer-one re-challenge did not reproduce the captured outputs and prompt, and one version still said there was no product-owner voter.

- The committed record in `tabletop/pointing-record.md` was already generated from the captures; the live comment was not.
- Correction posted: SKL-72 comment `c2121700`, which carries the committed record verbatim, names the superseded comments (`7698722f`, `1de27e80`, `3c822ac7`), and states the drift.
- Nothing in the captures was changed. The record was corrected to the captures, not the other way round.

## 2. The earlier handling of the rejected target-value rationales, stated plainly

The first round-two re-vote on SKL-72 produced rationales that named a target value for the story - `rejected/rv-po-output.txt` and `rejected/rv-e2-output.txt` each say "so it sizes at 2 rather than 3".

That is an anchoring event on sight, with no repair path, so the required recovery was a fresh independent blind vote in newly created voter contexts. What was done at the time was to re-run the re-vote with the rationale rule restated. That is a deviation from the delivered rule, and the evidence does not claim otherwise: `tabletop/raw-record.md` and `tabletop/PROVENANCE.md` record the rejection and the re-run, and this file records the deviation.

The required recovery is supplied by the run below, not by assertion.

## 3. The compliant run: SKL-77

A new canceled priority-none fixture was used because SKL-72 already carried several record comments and could not hold "one durable pointing record".

- Fixture: SKL-77, `[Tabletop fixture] Show candidate path age in the cleanup dry run (SKL-59 AC2 round 3)`, priority none, no implementation, canceled after the run, tracker-write preflight comment `19253345`.
- Delivered text loaded: `662c84b21e6aea973b41f2a2981b30b18af4118f`.
- One durable pointing record: SKL-77 comment `2b11599e`. The chain is `04540f95` (first post, omitted the voided rationales), `1dd2bb8c` (added them but quoted the target sentence in its Anchoring events line), `077378a0` (used a non-template tracker-writes form), `45e5ecac` (still claimed a discussion that was never held), and `2b11599e`, which records that no discussion was held, names the event by kind, cites `raw-record.md` for the verbatim sentence, keeps the voided rationales only in the superseded-values line that the delivered template exempts, and uses the template's `product owner` form.
- Artefacts: `tabletop/round3/prompts/` (nine prompts) and `tabletop/round3/outputs/` (nine captures), `tabletop/round3/raw-record.md`, and `tabletop/round3/pointing-record.md`, whose body is the exact text posted on the fixture.

### What the round shows

1. Three blind voters recorded values in separate processes. Engineer one's recorded rationale names a target value for this story: "This should be 2 rather than 3, because the earlier cleanup flag landed at two."
2. The facilitator saw it and stopped the round on sight: no challenge was issued, because the rule gives a target value no repair path; no discussion was opened; no sizing context was offered; the three recorded values and the consensus position were voided.
3. The independent vote from Step 3 was re-run blind in newly created voter contexts that exclude the tainted rationale and values, and those rationales name only drivers the pointing basis admits.
4. The re-vote recorded `{2}`, `{2}` and `{2}`; consensus 2.

### Matching check

`round3/check_record.py` checks the record semantically, not by substring: each of the seventeen template fields must appear exactly once in the delivered order; the values block must equal the three standing captures line for line; the re-vote line must carry each capture's accepted set and rationale, and the recorded consensus is recomputed from those sets; the discussion line is recomputed from the standing values; the superseded line must carry the three voided captures; the target sentence, read from `raw-record.md`, must appear nowhere outside the superseded line, with explicit absence checks on the Challenges and Anchoring events lines; and the fixed header values and capture inventory must match. Probes that appended off-basis text to a recorded rationale, changed a captured value, and leaked the exact target sentence into the Anchoring events line each failed the check. Its committed output is `round3/check_record.out`.

## 4. What is new, what is unchanged

- New: `tabletop/round3/` (prompts, outputs, raw record, record), this file, and the SKL-77 fixture with its record.
- New: the SKL-72 correction comment `c2121700`.
- Unchanged: all earlier captures, the `rejected/` files, the mutation evidence, the skill text and the tests. No capture was rewritten for this round; `PROVENANCE.md` is extended, not pruned.

## 5. Record defects found and corrected while preparing this round

Two defects in earlier drafts of the SKL-77 record were caught before this PR and are recorded here for completeness.

- The first posted record quoted the target sentence in its Anchoring events line; the durable record names the event by kind and cites `raw-record.md` instead.
- The discussion field asserted a high and a low of the standing values. No discussion was held, and the durable record says so. The re-vote prompt's preamble nevertheless described a high and a low, which is a defect in that prompt: the voters' accepted sets are their own and unaffected, but the preamble should have said no discussion was held. The record does not repeat the claim.

