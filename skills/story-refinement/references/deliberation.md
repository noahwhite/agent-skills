# Deliberation

These hand-written rules govern how the voters' judgements are formed and shared in Step 2 and Step 4 of [SKILL.md](../SKILL.md).

## Anonymised draft

- The reconciled story of Step 2 item 1, and each amended refinement of Step 2 item 6, is one merged draft with authorship stripped: it names no voter, no SM/EM, no family, no model and no input file, and attributes no item to an input.
- Every list in the draft, such as the acceptance criteria, the risks and the amendments, takes an order the facilitator draws at random, for example with `shuf`, independently of every input's order, so a draw that happens to match one input's order stands.
  The order inside one item whose sequence carries meaning, such as the steps of one acceptance criterion, is kept.
  An amended draft takes a newly drawn order.
- The refinement comment's `Refined story snapshot:` line carries that draft.
  Where that line records an immutable snapshot reference instead, the facilitator resolves the reference and anonymises the text it resolves to under these same rules.

## Codebook judgement

- The codebook is the Definition of Ready boxes the filing template has and the INVEST criteria, as Triage and Definition of Ready in [linear.md](linear.md) lists them.
- Each accept-round brief carries the anonymised draft under a snapshot label that names no comment, no voter and no input, and the codebook verbatim, the notes after its six INVEST criteria included, with each Definition of Ready box copied in full from the filing template.
  It carries nothing that attributes the draft or leads to an attribution: no refinement comment id, no voter input, no voter-input line, no per-voter verdict and no family or model name.
  The facilitator alone keeps the mapping from the snapshot label to the refinement comment id.
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

- Each re-vote prompt and each basis-challenge prompt carries this rule: the rationale names what moved the voter's vote, when the value that stands for it differs from its first vote: each new fact it cites that its Step 3 rationale did not, each ground it retracted, or neither.
- A voter's first vote is the value it recorded in Step 3 before any discussion or basis challenge, the blind re-run's value after a void; its re-vote value is the highest value of its accepted set, the lowest for a slice, or its Step 3 value when it records no consensus; its basis-challenge replacement is the value a basis-challenge launch records in place of its recorded value.
- A vote that moved with no new fact cited is flagged `conformity` in the pointing record, whatever else moved it, a retracted ground included; the flag is recorded apart from the reason the vote moved.
  The flag is informational and changes no consensus, no residual variance outcome, no estimate and no stop.
- The votes-per-voter lines of the Pointing record in [refinement-record.md](refinement-record.md) record each voter's first vote, assumptions, evidence cited and what moved its vote.
