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
- One durable pointing record: SKL-77 comment `264d0a47`. The chain is `04540f95` (first post, omitted the voided rationales), `1dd2bb8c` (added them but quoted the target sentence in its Anchoring events line), `077378a0` (used a non-template tracker-writes form), `45e5ecac` (still claimed a discussion that was never held), and `2b11599e`, which records that no discussion was held, names the event by kind, cites `raw-record.md` for the verbatim sentence, keeps the voided rationales only in the superseded-values line that the delivered template exempts, and uses the template's `product owner` form.
- Artefacts: `tabletop/round3/prompts/` (nine prompts) and `tabletop/round3/outputs/` (nine captures), `tabletop/round3/raw-record.md`, and `tabletop/round3/pointing-record.md`, whose body is the exact text posted on the fixture.

### What the round shows

1. Three blind voters recorded values in separate processes. Engineer one's recorded rationale names a target value for this story: "This should be 2 rather than 3, because the earlier cleanup flag landed at two."
2. The facilitator saw it and stopped the round on sight: no challenge was issued, because the rule gives a target value no repair path; no discussion was opened; no sizing context was offered; the three recorded values and the consensus position were voided.
3. The independent vote from Step 3 was re-run blind in newly created voter contexts that exclude the tainted rationale and values, and those rationales name only drivers the pointing basis admits.
4. The re-vote recorded `{2}`, `{1}` and `{1, 2}`, which do not intersect, so the round has no consensus and the no-consensus decision ran: the three path votes intersect on re-refine.

### Matching check

`round3/check_record.py` checks the record semantically, not by substring: each of the seventeen template fields must appear exactly once in the delivered order; the values block must equal the three standing captures line for line; the re-vote line must carry each capture's accepted set and rationale, and the recorded consensus is recomputed from those sets; the discussion line is recomputed from the standing values; the superseded line must carry the three voided captures; the target sentence, read from `raw-record.md`, must appear nowhere outside the superseded line, with explicit absence checks on the Challenges and Anchoring events lines; and the fixed header values and capture inventory must match. Probes that appended off-basis text to a recorded rationale, changed a captured value, leaked the exact target sentence into the Anchoring events line, made a path capture disagree with the record, and restored a false discussion claim into a re-vote prompt each failed the check. Its committed output is `round3/check_record.out`.

## 4. What is new, what is unchanged

- New: `tabletop/round3/` (prompts, outputs, raw record, record), this file, and the SKL-77 fixture with its record.
- New: the SKL-72 correction comment `c2121700`.
- Unchanged: all earlier captures, the `rejected/` files, the mutation evidence, the skill text and the tests. No capture was rewritten for this round; `PROVENANCE.md` is extended, not pruned.

## 5. Record defects found and corrected while preparing this round

Three defects in earlier drafts of the SKL-77 record and its prompts were caught before this PR and are recorded here for completeness.

- The first posted record quoted the target sentence in its Anchoring events line; the durable record names the event by kind and cites `raw-record.md` instead.
- The discussion field asserted a high and a low of the standing values, and the first re-vote prompts described that non-existent discussion to the voters. Both were wrong: no discussion was held. The re-vote was run again with a prompt that says so, and the record now records `Discussion: none`. The captures from the first re-vote are not kept as the record's basis; they are superseded by the truthful run, and this note is the record of that replacement.
- The re-vote sets from that truthful run do not intersect, so the no-consensus decision ran on the same fixture: the three path votes intersect on re-refine, which the record carries.

## 6. Round four: the discussion round and the one-record requirement (QA round 3)

QA round 3 found that the round-three recovery skipped the Step 4 discussion round and that six records had been posted where one was required.

- The discussion round is now held where the delivered text puts it: after the blind re-vote, in the newly created voter contexts, naming only the high value 5 and the low value 2, and challenging the one off-basis ground (coverage), which was retracted. The tainted thread is still not resumed: the stop and the void happened on the recorded target value in round one, and the discussion that was held is a new one in fresh contexts.
- The run is on a new canceled priority-none fixture, SKL-78, and carries exactly one pointing record, comment `e0bcb6f8`, generated from the captures and committed as `round4/pointing-record.md`. That one comment was updated in place once, to drop a field the delivered template does not define, so the run still holds a single record and no supersession line.
- The supersession history of the earlier fixtures is unchanged and stays in this file and in `PROVENANCE.md`; the SKL-78 record carries no supersession line because it is the only record for that run, and `tabletop/round4/pointing-record.md` states that in its preamble.

## 7. Round five: the amended reading, and the delivery of it in the skill text

The 2026-10-25 owner amendments (tracker comment `9e5b9868`) resolved the conflict four QA rounds turned on. Two changes follow.

- The delivered text now states the reading: a factual reference naming an already-estimated item's recorded value, alone or with a basis difference, is permitted and never stops a round, while a prescription of this story's value - from the SM/EM or from a voter - is an anchoring event; and the discussion round's "names only the high and the low" governs the shared content and other voters' values, while a voter's own record may be carried privately in its own prompt. The changes are in `skills/story-refinement/SKILL.md` Step 3 item 7, Step 4 item 1 and the Anchoring guardrail, and in `skills/story-refinement/references/refinement-record.md`'s phrasing prose and Discussion field note.
- The behavioural evidence is a fresh run on the canceled priority-none fixture SKL-79, with one durable record, comment `466d7155`. It shows the permitted reference present and the round continuing past it, a prescription stopping the round on sight, an injected ground left unretracted that voids the consensus and is followed by a blind re-vote in newly created contexts, the recovered discussion naming only the high and the low, and surviving rationales that name only basis drivers.
- The comparable is the real, already-estimated SKL-53, whose pointing record fixed its consensus at 5 points; it is cited as 5 everywhere in the record and this provenance, replacing the invented comparable the 2026-10-25 evidence cited inconsistently.

## 8. Round five corrections in place (same PR, after review)

Review of this round found three defects in its evidence, each corrected rather than argued:

- The record quoted an SM/EM sizing context that was not the captured one, so the SM/EM event is now a captured prompt and output (`round5/prompts/sm-em-prompt.txt`, `round5/outputs/sm-em-output.txt`), the record quotes it exactly, and the pointer comment `466d7155` was updated in place rather than superseded.
- The checker's prescription test matched one hardcoded string, so it was replaced by a phrasing-agnostic detector: any sentence pairing a number with a reference to the story under estimate and a sizing verb is a prescription, and ten distinct phrasings are confirmed to fail the check.
- The discussion-disclosure check could not see a prompt that named another voter's value, so it now fails any discussion prompt that carries another voter's role at all, and the probe that injects `Engineer one. Their value: 3.` fails as it should.

The prescription detector is held to the case matrix in `round5/prescription-cases.md`: nineteen sentences that must trip it, each a different prescription phrasing (value, first person, target, answer, settlement, non-numeric, and the mixed forms the review found), and ten that must not, each a permitted reference or ordinary record sentence (another story's score or target, a constraint count, a basis-driver rationale).
`check_record.py` re-runs that matrix on every invocation and reports its counts, so the claim is checkable rather than asserted.
It is a lint, not a proof: a prescription phrased outside these forms would pass, and the record is also read by a human reviewer for exactly that reason.
