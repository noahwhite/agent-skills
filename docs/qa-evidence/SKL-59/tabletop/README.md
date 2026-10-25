# SKL-59 AC2 tabletop at 702f53c9

This directory holds the inspectable artefacts of the AC2 behavioural round: twenty-five prompt files, the twenty-five outputs of those processes, the raw session record with the verbatim target quotation, and the pointing record posted on the fixture.

## Run statement

- Delivered text loaded: **`702f53c9ab6fe4209fd4600ad2224c6e0431671a`**, the squash merge of implementation PR #49 on `main`, read from a detached worktree checkout of that commit.
- Fixture: SKL-72 `[Tabletop fixture] Add a --changed-only filter to the cleanup dry run (SKL-59 AC2 rerun)`, priority none, no implementation, canceled after the run, with a tracker-write preflight comment `be040dec`.
- The SKL-72 record was corrected in the tracker as comment `c2121700`, which carries `pointing-record.md` verbatim and supersedes `7698722f`, `1de27e80` and `3c822ac7`. The fixture was canceled after the run.
- Contexts: twenty-one voter processes plus four challenge processes, each launched in its own directory holding only that process's own prompt file, so no voter could see another voter's prompt, value or rationale. `prompts/` and `outputs/` are `.txt` because they are captured artefacts kept byte-for-byte, not repository prose.
- Raw record: `raw-record.md` holds the values, rationales, the round-two target quotation verbatim, and the challenge text. `PROVENANCE.md` states which captures are original, which were reconstructed and which were replaced, with the commit that holds each surviving capture.

## Round one - the voter grounds

Order as it happened:

1. **Blind values** (`prompts/v1-*-prompt.txt`, `outputs/v1-*-output.txt`): product owner 2 weighing verification strength, engineer one 3 weighing testability, engineer two 5 weighing coverage.
2. **The reveal and the SM/EM sizing context.** All three values were recorded, then the sizing comparison was offered: "The earlier cleanup flag landed at three; this story carries one more interacting constraint than that one." The 2026-10-24 amendment permits that comparison after the reveal, so it raised no anchoring event.
3. **The discussion and the challenges.** The discussion named high 5 and low 2 only; the facilitator then challenged every off-basis ground, and the exact text each voter received is in `prompts/c-*-prompt.txt` and `prompts/c-e1-rechallenge-prompt.txt`:
   - the product owner's verification-strength ground, challenged and **retracted** (`outputs/c-po-output.txt`);
   - engineer one's testability ground, challenged, then re-challenged when its first reply repeated the same ground in other words, and **retracted** (`outputs/c-e1-output.txt`, `outputs/c-e1-rechallenge-output.txt`);
   - engineer two's coverage ground, challenged and left **unretracted** (`outputs/c-e2-output.txt`).
4. **The stop.** Engineer two's coverage ground is neither restated as a basis driver nor retracted, so it is an anchoring event. The facilitator stopped the round: the consensus position and the vote that ground carries were voided, and the discussion was not resumed.
5. **The blind re-run** (`prompts/v2-*`, `outputs/v2-*`): 2, 2, 3 with basis-only rationales.
6. **The re-vote** (`prompts/v3-*`, `outputs/v3-*`): `{2}`, `{2}`, `{2}`; consensus 2.

## Round two - the off-basis SM/EM sizing note

1. **Blind values** (`prompts/r2-*`, `outputs/r2-*`): 3, 3, 3 with basis-only rationales.
2. **The sizing note.** The SM/EM offered a note naming an earlier tabletop's recorded value as this fixture's target. Its verbatim text is in `raw-record.md`; the posted record elides it.
3. **The stop on sight.** A target value for this story is an anchoring event as soon as the facilitator sees it, with no challenge, restatement or retraction path. The round stopped before the discussion opened, the consensus position and the three recorded values were voided, and the discussion was never resumed.
4. **The blind re-run** (`prompts/r3-*`, `outputs/r3-*`): 2, 3, 2 with basis-only rationales.
5. **The re-vote and the no-consensus decision.** The re-vote (`prompts/rv-*`, `outputs/rv-*`) recorded `{3}`, `{2}` and `{2}`, so the intersection is empty. Each voter then recorded the paths it accepts (`prompts/path-*`, `outputs/path-*`): product owner `{leave unpointed}`, engineer one `{re-refine}`, engineer two `{re-refine}`. That intersection is empty too, so the story is left unpointed, the default when no path is in all three sets.

## What this establishes

- A voter rationale weighing verification strength and another weighing testability were both challenged and retracted; no surviving rationale carries either, and the testability challenge was re-issued rather than accepted when the first reply only relabelled the same ground.
- A third scripted ground, coverage, was challenged and deliberately left unretracted, and it alone stopped round one.
- Round two's off-basis SM/EM sizing note stopped the round on sight, before any discussion, so nothing resumed a tainted discussion.
- Both blind re-runs ran in newly created contexts that exclude the tainted discussion and sizing material, and every surviving rationale names only drivers the pointing basis admits.
- The posted record quotes each injected ground and each facilitator challenge verbatim, carries the standing re-run values in the values block, records the voided values and the voided consensus position under the superseded line, and elides only the round-two target, which `raw-record.md` holds verbatim.

## Why no automated guard covers the duty

A phrase test pins the facilitator's challenge duty and the mutation evidence proves that pin, but only a run can show a facilitator performing it. This directory is that run: the prompts show what each voter was asked, the outputs show what each voter answered, and the record shows each challenge with its outcome.

## Round three - the compliant run on SKL-77 (after QA round 2)

QA round 2 ruled the earlier run's target-value handling short of the delivered rule and its live record out of step with the captures. `RECONCILIATION.md` states what was corrected and what was run; `round3/` holds the artefacts.

- Fixture: SKL-77, priority none, no implementation, canceled after the run, tracker-write preflight comment `19253345`.
- One durable record: SKL-77 comment `077378a0` (superseding `04540f95` and `1dd2bb8c`), reproduced exactly by `round3/pointing-record.md`. The two-posting sequence is a deviation from the one-record precedent: the first post omitted the voided rationales, and the second elides the target from the Anchoring events line.
- The round: three blind voters; engineer one's recorded rationale named a target value; the facilitator stopped on sight, voided the recorded values and the consensus position, never opened the discussion and offered no sizing context; the independent vote was re-run blind in newly created contexts; the re-vote recorded `{2}`, `{2}`, `{2}` and consensus 2.
- Every rationale in the record, standing and voided, is generated from its capture in `round3/outputs/`.
