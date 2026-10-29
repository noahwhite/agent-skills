# SKL-94 QA evidence

## Round 1, 2026-10-29

The repository deploys nothing (`environments: []`), so the environment under test is merged `main`, build `59ac7db26c38ca90e83275df1fb42819ffc34802` from [PR #92](https://github.com/noahwhite/agent-skills/pull/92).
PR head `3bd15aa4d27b3cc7ab68fe70d5c540f1070362d0` and the squash merge have the same tree (`37c19c8f68a0ab47f3ffcf3902c9976815ea97bf`).
Both live runs load `skills/story-to-done/SKILL.md` and its references from a detached checkout at that PR head, not from the installed skill.
Fixtures are SKL-133 (Run 1, created In Deployment Review) and SKL-134 (Run 2, created Blocked), both `[Tabletop fixture]` issues in SKL.
There is no visual surface; structured assertions and raw command output are the evidence, without screenshots.
The tracker record is QA comment `83880a11` on SKL-94 and its attachments `SKL-94 QA round 1 - AC and DoD assertions` and `SKL-94 QA round 1 - Run 1 coordinator shell commands`.

Outcome: C4 is not met, so the story returns to In Progress.

| Item | Verdict | Evidence |
|---|---|---|
| C1 post the summary | Verified | Every C1 sentence is present in the shipped `SKILL.md`, both removed sentences are absent, and the end-form sentence precedes the post sentence; no file under `shared/`, no vendored reference, and not `metrics-summary.sh` changed; both live runs below show the behaviour. |
| C2 docs | Verified | The README row clause, the kept switch phrase, and the new step 0 seed sentence are present, and the old sentence is absent. |
| C3 tests | Verified | 788 tests pass, the named guard tests pass, and `vendor_shared.py --check` exits 0; the replaced tests are gone and the guarded tests are unchanged; PR #92 records a mutation table; [CI run 40941004265](https://github.com/noahwhite/agent-skills/actions/runs/40941004265) succeeded on the PR head and [CI run 40942095692](https://github.com/noahwhite/agent-skills/actions/runs/40942095692) on merged `main`. |
| C4 verified end to end | Not met | Run 1's comment `44f720b2` on SKL-133 has 19 rows, but the coordinator launched two commands outside the wrapper, so the comment does not have one row per launch (see Run 1); Run 2 meets every Run 2 clause, and both comments equal their closing report's summary byte for byte. |
| DoD all acceptance criteria met | Not met | C4. |
| DoD tests written and passing | Verified | C3. |
| DoD independently reviewed | Verified | [Review 5703909396](https://github.com/noahwhite/agent-skills/pull/92#pullrequestreview-5703909396) binds head `3bd15aa4d27b3cc7ab68fe70d5c540f1070362d0`: Codex GPT-6 Sol reviewer, DeepSeek V4 Pro and Opus 5.5 adjudicators, no merge-blocking finding. |
| DoD docs updated | Verified | C2. |
| DoD staging | Not met | No staging target exists; C4 stands in for it and is not met. |
| DoD no critical bugs or regressions | Verified | The full suite and CI are green; the C4 gap is recorded under C4. |

### Run 1 (SKL-133)

The coordinator read SKL-133 as In Deployment Review, skipped the implementation step, and launched one QA round on Opus 5.5 at high effort.
QA verified the fixture, merged evidence [PR #93](https://github.com/noahwhite/agent-skills/pull/93) on reviewed head `2a4cf8b3d67a4778efe7f7d7b3a6e6653d7e8730`, and set SKL-133 to Done.
QA's handback never reached the coordinator, so the run ended as a recorded stop at step 4 with the completion record unconfirmed.
The coordinator posted comment `44f720b2` on SKL-133 with one `linear issue comment add` call, which the permission system allowed, and read it back.
The comment heading is `Run metrics: story-to-done SKL-133 - stopped: QA round 1 handback not received, completion record unconfirmed (story read back Done)`.
Its 19 rows are in launch order, from `start` through the `qa-round-1` role row to `end`.
The attached command listing from the coordinator's transcript shows 21 launches that need a row: the start form, 16 wrapped commands, the QA launch, the end form, and two commands with no row.
While waiting on its background QA launch, it read the background task's output file and ran a one-second wait, both outside the metrics wrapper, so neither has a row.
Every Duration cell is seconds with nine decimals, and every Tokens and Tool calls cell is `not reported`.
All eight extras are filled, including `QA round durations: round 1: 763.852641532s` and `PRs merged: 1`.
QA's independent read-back of the comment equals the summary in the closing report byte for byte (2753 bytes), and the closing report names the comment and its link.
A search of the comment and closing report for local paths and token patterns returns nothing.
Run end state: stopped at step 4 with the story read back Done; QA then canceled SKL-133 and read it back as Canceled.

### Run 2 (SKL-134)

The coordinator read SKL-134 as Blocked and stopped at step 1; no senior engineer or QA agent was spawned.
It posted comment `6fc7406e` on SKL-134 with one `linear issue comment add` call, which the permission system allowed, and read it back with `linear api`.
The comment heading is `Run metrics: story-to-done SKL-134 - stopped at step 1: story is Blocked`.
Its nine rows, in launch order, are `start`, seven wrapped commands (reference reads, an environment check, and the step 1 story read), and `end`.
Every Duration cell is seconds with nine decimals, and every Tokens and Tool calls cell is `not reported`.
All eight extras are filled, `Time to deployment review` reads `not applicable`, and the comment does not read `no launches`.
The elapsed wall-clock, 59.738747866s, equals the `invocation_end` minus `invocation_start` timestamps in the metrics file, and the comment was created after `invocation_end`.
QA's independent read-back of the comment equals the summary in the closing report byte for byte (1503 bytes), and the closing report names the comment.
A search of the comment and closing report for local paths and token patterns returns nothing.
Run end state: stopped at step 1, story Blocked; QA then canceled SKL-134 and read it back as Canceled.

### Failed item for the engineer

C4: in Run 1 the coordinator launched two commands outside the metrics wrapper while it waited on its background QA launch, so the posted comment does not have one row per launch.
It wrapped its other waits; QA's handback never reached it.
C4 is re-run at the fix head.

### Other deviations

In both runs the summary comment was the coordinator's only tracker write.

- The Run 1 coordinator was a nested Claude Code subagent; its turn ended before QA handed back, and it was resumed.
  Its `qa-round-1` end was recorded about three minutes after QA finished, so the 763.85s duration overstates the round.
- Its extras write appended a duplicate `end` line, which it removed before the end form ran.

Decision: In Progress; C4 is re-run at the fix head.

## Round 2, 2026-10-29

The environment under test is merged `main`, build `2fcbc042b512512e65d6cce751a383541367e26e` from [PR #95](https://github.com/noahwhite/agent-skills/pull/95), which has the same tree as PR head `9043327f334f2f26b5126c6b6fa5ee60930aaa25`.
Every live run loads `skills/story-to-done/SKILL.md` and its references from a detached checkout at that PR head, not from the installed skill.
Fixtures are SKL-139 (Run 1 attempt 1, created In Deployment Review), SKL-141 (Run 1 attempt 2, created In Deployment Review), and SKL-140 (Run 2, created Blocked), all `[Tabletop fixture]` issues in SKL.
There is no visual surface; structured assertions and raw command output are the evidence, without screenshots.
The tracker record is QA comment `6c132ec8` on SKL-94 and its attachment `SKL-94 QA round 2 assertions (2026-10-29)`.

Outcome: C4 is not met, so the story returns to In Progress.

| Item | Verdict | Evidence |
|---|---|---|
| C1 post the summary | Verified | All 16 phrase checks pass in the shipped `SKILL.md`, the removed sentences are absent, and the end-form sentence precedes the post sentence; nothing under `shared/`, no vendored reference, `metrics-summary.sh`, or todo tracking changed. |
| C2 docs | Verified | The README row clause, the kept switch phrase, and the step 0 seed sentence are present, and the old sentence is absent. |
| C3 tests | Verified | 790 tests pass, including the named guard tests and the two wait-rule tests PR #95 added, and `vendor_shared.py --check` exits 0; [CI run 40951799712](https://github.com/noahwhite/agent-skills/actions/runs/40951799712) succeeded on the PR head and [CI run 40952600556](https://github.com/noahwhite/agent-skills/actions/runs/40952600556) on merged `main`. |
| C4 verified end to end | Not met | Run 2 meets every Run 2 clause; in Run 1 two launches after the end form have no row, and the closing report names a local path (see Run 1 attempt 2). |
| DoD all acceptance criteria met | Not met | C4. |
| DoD tests written and passing | Verified | C3. |
| DoD independently reviewed | Verified | [Review 5704776979](https://github.com/noahwhite/agent-skills/pull/95#pullrequestreview-5704776979) binds head `9043327f334f2f26b5126c6b6fa5ee60930aaa25`: Codex GPT-6 Sol reviewer, DeepSeek V4 Pro and Opus 5.5 adjudicators, no merge-blocking finding. |
| DoD docs updated | Verified | C2. |
| DoD staging | Not met | No staging target exists; C4 stands in for it and is not met. |
| DoD no critical bugs or regressions | Verified | The full suite and CI are green; the C4 gap is recorded under C4. |

### Run 1 attempt 1 (SKL-139)

The coordinator ran as a nested Claude Code subagent and launched one background QA round.
The runtime made it hand back while QA was still running, so the run ended as a recorded stop at step 4.
The runtime refused its write of the summary body file, its single post attempt failed, and no comment was posted, so this attempt gives no C4 evidence.
Every shell command it launched before the stop ran in the metrics wrapper.
The orphaned fixture QA later merged evidence [PR #96](https://github.com/noahwhite/agent-skills/pull/96) on reviewed head `c04af614cf0569b6090b61aa07a00717845325e3` and set SKL-139 to Done.
QA then canceled SKL-139 and read it back as Canceled.

### Run 1 attempt 2 (SKL-141)

The coordinator ran as a top-level headless Claude Code session, read SKL-141 as In Deployment Review, and launched one QA round.
QA closed [PR #98](https://github.com/noahwhite/agent-skills/pull/98) unmerged after its commit was signed with an unregistered key, merged evidence [PR #99](https://github.com/noahwhite/agent-skills/pull/99) on reviewed head `61b9b443aa024753c09646720a46e6325cd85d99`, and set SKL-141 to Done.
The coordinator posted comment `158b4cb4` on SKL-141 and read it back.
Its 22 rows are in launch order, from `start` through the role row `QA agent round 1` (553.20s, 114625 tokens, 53 tool calls) to `end`.
Every Tokens, Tool calls, and Duration cell is well formed, all eight extras are filled, and `PRs merged` reads 1.
The posted body equals the closing report's summary line for line and differs only by one trailing newline (2696 against 2695 bytes), which the headless capture of the closing report may trim.
The comment holds no local path or token pattern.
The top-level transcript shows two shell launches after the end form with no row: a `linear issue comment add --help` lookup in the same command that wrote the summary body file, and a `sed -i` that ticked the coordinator's own checklist item for the post after the read-back.
The closing report names a local path, a home-directory SSH public key file, while relaying QA's signing finding.
A `cat` of `SKILL.md` before the start form also has no row; the QA brief told the coordinator to read the skill from the checkout, so it is not counted against C4.
Run end state: Done; QA then canceled SKL-141 and read it back as Canceled.

### Run 2 (SKL-140)

The coordinator read SKL-140 as Blocked and stopped at step 1; no senior engineer or QA agent was spawned.
It posted comment `6becf2df` on SKL-140 and read it back.
Its 11 rows, in launch order, are `start`, nine wrapped commands, and `end`, one per shell launch in the transcript.
The comment carries the stop reason, an elapsed wall-clock of 71.08s, all eight extras, and the totals, and does not read `no launches`.
It equals the summary in the closing report byte for byte (1753 bytes), and neither holds a local path or token pattern.
Run end state: stopped at step 1, story Blocked; QA then canceled SKL-140 and read it back as Canceled.

### Failed item for the engineer

C4: in Run 1 attempt 2 the coordinator ran a CLI help lookup between the end form and the post and updated its own checklist after the read-back, both without a row, so the end form was not the last launch and the comment does not have one row per launch.
Its closing report also names a local path.
C4 is re-run at the fix head.

Decision: In Progress; C4 is re-run at the fix head.
