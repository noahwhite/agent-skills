# SKL-296 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `6838b357652260562f481f747cf5e653d0f4e7c8`, the squash merge of PR 238.
The reviewed head is `1a839aca61c4549059b5ba364e2ccff1af7305a7`; `skills/story-to-done/SKILL.md` and `tests/test_story_to_done.py` are identical at the head and the build (`git diff` between them over those two files is empty).
The squash merge's own diff touches only those two files (8 additions and 2 deletions in the skill, 179 additions and 1 deletion in the tests).
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a detached worktree of the build), GitHub and the tracker.
Fixtures: none needed; the probes read `skills/story-to-done/SKILL.md` and the PR diff at the build and run the repository's guards.
The raw output is attached to SKL-296 as `SKL-296-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: step 4 puts pending owner rulings to the user and keeps them out of hand-backs | Verified | Step 4 `in_deployment_review` and `in_progress` bullets; details below. |
| AC2: `done` read-back rejects an amendment alone and any pending item | Verified | Step 4 `done` bullet; details below. |
| AC3: pins in `tests/test_story_to_done.py` | Verified | Every added line pinned whole with its prefix, the one disturbed pin updated, negative pins on the record shape; details below. |
| AC4: five guards | Verified | Every guard passed on the build, the private leak scan in CI; details below. |
| Scope note: no step 5 README table change, no `shared/*.md` change | Verified | The squash merge changes only the two files above. |
| DoD: all acceptance criteria met | Verified | AC1 to AC4. |
| DoD: tests written and passing | Verified | AC3 and AC4. |
| DoD: independently reviewed | Verified | Review 5898759536 names `1a839aca61c4549059b5ba364e2ccff1af7305a7` in its first line and as its `commit_id`, the merged head, with Codex GPT-6 Sol reviewing and DeepSeek V4.1 Flash adjudicating, no findings. |
| DoD: docs updated | Verified | The change is the skill text itself. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43515662961) and on `main` (run 43517119042). |

Details:

- AC1:
  - The `in_deployment_review` bullet's report-and-stop now names an item QA recorded as `pending owner ruling` among the other-owner items (SKILL.md line 237).
  - Line 238 has that report put each such item to the user with the AC or DoD text QA quoted and each reading with its verdict, as QA recorded them in the tracker.
  - Line 239 says the coordinator rules on none of those items and relays none of them to the senior engineer or a QA agent.
  - Line 214, in the `in_progress` bullet, puts pending items to the user the same way while the hand-back goes on with the failed items alone.
  - Line 228 leaves every pending item out of every hand-back brief, including one carried from an earlier failed round.
  - Line 218 lists pending items apart, per round, in the `qa-round-cap` stop report, never among the failed items.
- AC2:
  - Line 210 says Done is never set on an AC amendment alone.
  - It requires no item still `pending owner ruling`, and a verified verdict from a new QA round (a new QA agent on the unchanged step 3 brief) run after the product owner's dated AC amendment.
  - Line 211 now reads "If all of these hold", replacing "If all three hold".
- AC3:
  - The squash merge adds 8 lines to the skill and removes 2; each added line is pinned whole with its two-space bullet prefix in the SKL-296 block of `tests/test_story_to_done.py`.
  - The one existing pin a changed line disturbed, `STEP4_OTHER_OWNER`, is updated in place, not deleted.
  - `git grep` over `tests/` at the parent commit finds no other pin on a changed line.
  - Negative pins: the step 3 QA brief source, the continuation lines of the `in_deployment_review` bullet and the engineer hand-back lines of the `in_progress` bullet are scanned with `RECORD_SHAPE` and pinned by SHA-256 digest.
  - `RECORD_SHAPE` matches the record (the ruling, a competing reading, a reading with its verdict, the quoted text, a pending item), and a test asserts it does not match the bare word "reading".
  - The 9 SKL-296 tests passed on the build.
- AC4:
  - On the build, `uv run --locked pytest -q` passed (2245 passed locally; CI collects 2263).
  - `python3 scripts/vendor_shared.py --check` exited 0.
  - `skills-ref validate` at the CI ref `69ef37e` passed for all 18 skills.
  - `bash scripts/smoke-opencode.sh` discovered 18 skills in each of its 6 layouts.
  - The public leak scan exited 0; its private half runs only in CI.
  - CI run 43515662961 on the reviewed head passed `checks` (2263 tests, and the leak scan with `--require-private` and the denylist loaded) and `discovery`.
  - CI run 43517119042 on `main` passed both jobs.

Closing decision: SKL-296 moves to Done once this evidence PR merges.
