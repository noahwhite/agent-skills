# SKL-230 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `d883eb5a158cedf67077e6a049375ce629ab37cd`, the squash merge of PR 241.
The reviewed head is `3dcfee632722cd2b40be0542ace8fe108bc101d6`; `git diff` between the head and the build touches only `docs/qa-evidence/SKL-239/README.md`, so none of the PR's 22 files differ.
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a fresh clone of `origin/main`), GitHub, the tracker and the persistent memory store.
Fixtures: none needed; the probes read `skills/story-refinement/SKILL.md` and `shared/linear.md` at the build, mutate them in the clone, and run the repository's guards.
The raw output is attached to SKL-230 as `SKL-230-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| K1: Split rule re-splits an oversize slice with no escalation exit | Verified | `SKILL.md` lines 326 and 339 to 340; details below. |
| K2: one split rule for refinement, filing and triage, with the boundary order | Verified | `shared/linear.md` lines 82 to 96; details below. |
| K3: tests, regenerated copies and guards | Verified | Tests pass, three mutations fail them, no vendoring drift, CI green; details below. |
| K4: memory note retired | Verified | The note and its index entry are gone from the live store, and the retirement is named on the PR and the story. |
| DoD: all acceptance criteria met | Verified | K1 to K4. |
| DoD: tests written and passing | Verified | K3. |
| DoD: independently reviewed | Verified | The PR 241 review of record names `3dcfee632722cd2b40be0542ace8fe108bc101d6` in its first line and as its `commit_id`, the merged head, with Codex GPT-6 Sol reviewing and DeepSeek V4.1 Flash adjudicating, and no open finding. |
| DoD: docs updated | Verified | The change is the skill and shared reference text itself. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43522915543) and on `main` (run 43523610496), and the full suite passed locally on the build. |

Details:

- K1:
  - Line 326 defines the split trigger: a recorded estimate above `profile.refinement.point_cap` or 8 or more.
  - Line 339 splits a slice that meets the trigger again under the same bullets: it stays the core slice and blocks its new siblings, each acceptance criterion is mapped to a sub-slice in a split comment, and each sub-slice gets its own three-voter blind estimate, until no slice meets the trigger.
  - Line 340 states there is no escalation exit and cites the boundary order in `references/linear.md` without restating it.
  - "or escalated" is absent from the section; its only escalation mention is "no escalation exit".
  - The unpointed variance stop (lines 337 to 338) is unchanged by the merge.
- K2:
  - Line 82 splits a story above `profile.refinement.point_cap` or at 8 or more, without asking, before it is assigned or work is delegated; line 83 makes it one rule for refinement, filing and triage.
  - Line 85 re-splits every slice that still meets the trigger, with no escalation exit.
  - Lines 88 to 92 give the boundary order: planned PR or slice boundary, acceptance criterion, a rewrite of an over-broad criterion into narrower observable ones, then the smallest independently reviewable, mergeable and verifiable outcome including enabling work.
  - Line 94 states that no rung discards scope, delegates an oversize slice or hands one to the owner as an estimate.
  - The "without asking" wording stays, and the close-time bullet (line 96) is unchanged.
- K3:
  - On the build, `tests/test_story_refinement.py` and `tests/test_shared_linear.py` passed (463 tests), and the full `uv run --locked pytest -q` passed (2270 tests locally; CI collects 2288).
  - Adding an escalation line to the Split rule fails 2 tests; restoring the original "or escalated" line fails 4 tests.
  - Changing the shared trigger to 13 fails the test that compares the `SKILL.md` and `shared/linear.md` triggers.
  - `scripts/vendor_shared.py --check` exits 0 on the build and lists all 18 copies as stale after an unvendored edit.
  - The public leak scan exited 0; its private half runs only in CI.
  - CI run 43522915543 on the reviewed head passed `checks` (2288 tests, the leak scan with `--require-private`, and `skills-ref validate` for all 18 skills) and `discovery` (all 18 skills in each of 6 layouts).
  - CI run 43523610496 on `main` passed both jobs.
- K4:
  - The memory note K4 names no longer exists in the live memory store, and no file in that store references it.
  - The PR body's "K4 memory retirement" section and the story's implementation note name the note as deleted and read back.

Closing decision: SKL-230 moves to Done once this evidence PR merges.
