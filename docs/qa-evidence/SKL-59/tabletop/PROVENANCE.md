# Provenance of the captured artefacts

This file states exactly how each file in `prompts/` and `outputs/` came to exist, because some captures were replaced during the run and a reader must be able to see which are original.

## What is original

- `prompts/v1-*-prompt.txt`, `outputs/v1-*-output.txt` - round one's blind values, captured from their processes and committed unchanged in `41741ae`.
- `outputs/v2-*`, `outputs/v3-*` - round one's blind re-run and re-vote, captured from their processes and committed unchanged in `41741ae`.
- `prompts/c-*-prompt.txt` (apart from the note below), `outputs/c-*-output.txt`, `outputs/c-e1-rechallenge-output.txt` - the round-one challenge exchanges, captured in `5ccf5ea`.
- `prompts/r2-*`, `outputs/r2-*`, `prompts/r3-*`, `outputs/r3-*` - round two's blind values and blind re-run, captured in `23d974d`.
- `prompts/path-*`, `outputs/path-*` - the no-consensus path votes, captured in `4c075ea`.

## What was replaced, and why

- **Engineer one's round-one challenge prompt.** The first challenge process overwrote its own prompt file with its answer. The prompt was regenerated from the same template and the same recorded value and rationale, and the answer is the separate captured output. `prompts/c-e1-prompt.txt` is therefore a reconstruction, not a capture.
- **The first round-two re-vote (`rv-*`).** The first capture produced rationales that named a target value for the story, weighed verification strength and bounded a scale position. The facilitator rejected them and re-ran the re-vote with the rationale rule restated in the prompt. The rejected capture is kept verbatim in `rejected/rv-po-output.txt`, `rejected/rv-e1-output.txt` and `rejected/rv-e2-output.txt`, restored from git history, and `raw-record.md` names the rejection. One intervening clean run was then replaced in `fb98aa1` by the captured run in `outputs/rv-*`, because its prompt asserted a discussion that did not happen; the current `outputs/rv-*` are the captures taken with the truthful prompt.
- **The round-one challenge prompts (`c-*`).** An earlier challenge round used shorter challenge text; those files were superseded when the record's quoted challenges were aligned with the prompts. The current prompts and outputs are the aligned set captured in `5ccf5ea`.
- **The first round-two re-vote prompts and the path vote for the first value set.** Superseded and deleted in `5ccf5ea` and `4c075ea` when the value set changed; the surviving files are the ones described above.

## What this means for a reader

Where a file is a reconstruction or a replacement, this file says so and names the commit that holds the surviving capture. The posted record on SKL-72 cites this file, so the tracker and the repository agree on what is original and what was corrected.

## Round 3 (SKL-59 AC2 round 3, after QA round 2)

- `round3/prompts/` and `round3/outputs/` are original captures from nine voter processes, taken after the delivered text at `662c84b21e6aea973b41f2a2981b30b18af4118f`, and committed unchanged.
- `round3/pointing-record.md` is the record generated from those captures and posted on SKL-77 as comment `45e5ecac`, superseding `077378a0`, `04540f95` and `1dd2bb8c`; the first omitted the voided rationales, the second quoted the target on the story surface in its Anchoring events line, and the third used a non-template tracker-writes form.
- The SKL-72 record was corrected in the tracker, not in the captures: comment `c2121700` carries the committed record verbatim and names the comments it supersedes.
- No capture from an earlier round was removed or rewritten in this round; the earlier labels above stand, including the one recording that the first round-two re-vote was rejected and that one intervening clean run was replaced. Two index files were edited: the SKL-72 record id in `tabletop/README.md` and `pointing-record.md`, and the counts in both READMEs.
