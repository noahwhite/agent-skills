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
- **The first round-two re-vote (`rv-*`).** The first capture produced rationales that named a target value for the story, weighed verification strength and bounded a scale position. The facilitator rejected them and re-ran the re-vote with the rationale rule restated in the prompt. The rejected capture is not kept as a file; it is summarised in `raw-record.md` under "Round two, re-vote", and `prompts/rv-*` and `outputs/rv-*` are the clean run captured in `5cf7604`.
- **The round-one challenge prompts (`c-*`).** An earlier challenge round used shorter challenge text; those files were superseded when the record's quoted challenges were aligned with the prompts. The current prompts and outputs are the aligned set captured in `5ccf5ea`.
- **The first round-two re-vote prompts and the path vote for the first value set.** Superseded and deleted in `5ccf5ea` and `4c075ea` when the value set changed; the surviving files are the ones described above.

## What this means for a reader

Where a file is a reconstruction or a replacement, this file says so and names the commit that holds the surviving capture. The posted record on SKL-72 cites this file, so the tracker and the repository agree on what is original and what was corrected.
