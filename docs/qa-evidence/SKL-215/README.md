# SKL-215 QA evidence

## Round 1

Date: 2026-11-08 UTC, independent QA round 1.
Build under test: `main` at `9f90a932962996e9b3136f56fa08dfc9f5ae7b77`, the squash merge of PR 166, whose reviewed head is `5d6184fa7bfc4831f7d319605825af9ce0da9fc3`.
Environment: the profile lists no environments, so every item was verified against `main` and its CI.
Tool versions: uv 0.13.7.
Fixtures: none.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-215 as the "SKL-215 QA round 1 raw assertion output" attachment.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: priority step | Verified | `skills/story-refinement/SKILL.md` lines 294 to 302 are one Triage bullet. It names ready, backlog and each split sibling. It has the PO decide, apply and read back a priority before the invocation ends and before any move to ready. It requires a comparison with at least one prioritised story in the team of `STORY_ID`, a PO-authored write with read-back, and says "No priority" is unset. `grep -rnF` finds "Priority comes from the PO's decision" nowhere under `skills/` or `shared/`. |
| AC2: stop and ask | Verified | The same bullet stops the ceremony with the priority unset and "Priority is clear" unticked when the PO cannot decide, including when no comparable prioritised story exists. It reports `needs input` to the owner naming the story, and says "The PO never guesses a priority." |
| AC3: seed item | Verified | "set priority (the PO's decision, the comparison it rests on, and the read-back)" sits immediately before "each PO tracker write and read-back" in `shared/todo-tracking.md` and in all 18 vendored copies. |
| AC4: tick rule and triage record | Verified | The tick rule is at `SKILL.md` line 301. `references/refinement-record.md` has a Triage record template with a `Priority:` line and a `Priority comparison:` line, posted by the product owner as a triage write. The Records section lists the template at line 307. The record file has no generated header, and `skills.json` vendors only linear, todo-tracking, engineering-practice and metrics into story-refinement. |
| AC5: tests | Verified | The 16 new tests pass. Fourteen assert their phrase inside the Triage priority bullet, the Records section, the Triage record template or the story-refinement seed entry. `test_triage_replaces_the_bare_priority_bullet` asserts across the whole Triage section that the old phrase is absent and the priority bullet lead occurs once. `test_triage_priority_stop_names_itself_as_the_closing_stop_reason` asserts its phrase inside the priority bullet and also keeps the Closing clause that bullet relies on. The PR 166 body records 23 mutations, each failing its named test, and states that no test on `main` pinned the removed phrase. The test diff is 151 lines added and 0 deleted. |
| AC6: regeneration and gate | Verified | `uv run --locked pytest -q` reports 1356 passed. `scripts/vendor_shared.py --check` exits 0. The `checks` and `discovery` runs succeeded on `5d6184f` and on `9f90a93`, and `main` push run 42523577397 succeeded. |
| DoD1: all acceptance criteria met | Verified | AC1 to AC6 are verified. |
| DoD2: tests written and passing | Verified | See AC5 and AC6. |
| DoD3: independently reviewed | Verified | The latest review of record on PR 166 (Codex GPT-6 Sol reviewer, DeepSeek V4 Pro adjudicator) is on `5d6184f`, the merged head. |
| DoD4: docs updated | Verified | The change is the guidance itself, and the vendored copies are in step. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; `main` at `9f90a93` was verified directly. |
| DoD6: no critical bugs or regressions | Verified | The full suite and `main` CI are green. |

Closing decision: Done, once this evidence merges.
