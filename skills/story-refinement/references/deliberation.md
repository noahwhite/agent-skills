# Deliberation

These hand-written rules govern how the voters' judgements are formed and shared in Step 2 and Step 4 of [SKILL.md](../SKILL.md).

## Anonymised draft

- The reconciled story of Step 2 item 1, and each amended refinement of Step 2 item 6, is one merged draft with authorship stripped: it names no voter, no SM/EM, no family, no model and no input file, and attributes no item to an input.
- Every list in the draft, such as the acceptance criteria, the risks and the amendments, takes an order the facilitator draws at random, for example with `shuf`, and never one input's order.
  An amended draft takes a newly drawn order.
- The refinement comment's `Refined story snapshot:` line carries that draft.

## Codebook judgement

- The codebook is the Definition of Ready boxes the filing template has and the INVEST criteria, as Triage and Definition of Ready in [linear.md](linear.md) lists them.
- Each accept-round brief carries the refinement comment id, the draft from that comment's `Refined story snapshot:` line and the codebook verbatim, and nothing that attributes the draft: no voter input, no voter-input line, no per-voter verdict and no family or model name.
- Every `OBJECT` names the codebook item the draft fails, with its blocking amendment.
  A blocking amendment is one that fixes a codebook item the draft fails.
- An `OBJECT` that names no codebook item is re-recorded once, in a launch that starts a new voter context; a second such answer from the same voter counts as a missing voter.
- The Accept round result comment carries each `OBJECT` with the codebook item it names.

## Evidence discussion

- In the Step 4 item 3 discussion the voters exchange assumptions and evidence, never point numbers.
- The high and the low voters state their assumptions and the evidence they cite first, then the third voter.
- The shared discussion content carries no voter's value and no other point number, so an assumption or a piece of evidence that embeds one, a ledger price included, is passed on with that number elided.
- Do not compare values, and do not single out a voter beyond that speaking order.

## Vote movement

- Each re-vote prompt carries this rule: the re-vote rationale names what moved the voter's vote, when its re-vote value differs from its first vote: the new fact it cites that its Step 3 rationale did not, or none.
- A voter's first vote is the value it recorded in Step 3 before any discussion or basis challenge, the blind re-run's value after a void; its re-vote value is the highest value of its accepted set, the lowest for a slice, or its Step 3 value when it records no consensus.
- A vote that moved with no new fact cited is flagged `conformity` in the pointing record.
  The flag is informational and changes no consensus, no residual variance outcome, no estimate and no stop.
- The votes-per-voter lines of the Pointing record in [refinement-record.md](refinement-record.md) record each voter's first vote, assumptions, evidence cited and what moved its vote.
