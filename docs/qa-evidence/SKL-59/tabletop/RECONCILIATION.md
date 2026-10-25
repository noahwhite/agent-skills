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
- One durable pointing record: SKL-77 comment `077378a0`. The chain is `04540f95` (first post, omitted the voided rationales), then `1dd2bb8c` (added them but quoted the target sentence in its Anchoring events line), then `077378a0`, which names the event by kind, cites `raw-record.md` for the verbatim sentence and keeps the voided rationales only in the superseded-values line, which the delivered template exempts.
- Artefacts: `tabletop/round3/prompts/` (nine prompts) and `tabletop/round3/outputs/` (nine captures), `tabletop/round3/raw-record.md`, and `tabletop/round3/pointing-record.md`, whose body is the exact text posted on the fixture.

### What the round shows

1. Three blind voters recorded values in separate processes. Engineer one's recorded rationale names a target value for this story: "This should be 2 rather than 3, because the earlier cleanup flag landed at two."
2. The facilitator saw it and stopped the round on sight: no challenge was issued, because the rule gives a target value no repair path; no discussion was opened; no sizing context was offered; the three recorded values and the consensus position were voided.
3. The independent vote from Step 3 was re-run blind in newly created voter contexts that exclude the tainted rationale and values, and those rationales name only drivers the pointing basis admits.
4. The re-vote recorded `{2}`, `{2}` and `{2}`; consensus 2.

### Matching check

`round3/check_record.py` compares the record body against every capture: each `VALUE:`/`ACCEPTED:` token and each `RATIONALE:` line must appear verbatim, the four header fields must be present, and each stage must have exactly three captures. Its committed output is `round3/check_record.out`.

## 4. What is new, what is unchanged

- New: `tabletop/round3/` (prompts, outputs, raw record, record), this file, and the SKL-77 fixture with its record.
- New: the SKL-72 correction comment `c2121700`.
- Unchanged: all earlier captures, the `rejected/` files, the mutation evidence, the skill text and the tests. No capture was rewritten for this round; `PROVENANCE.md` is extended, not pruned.
