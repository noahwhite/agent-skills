# SKL-156 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `f9b665982210d71771e78e4140e982125dc236a9`, the squash merge of PR 230.
Its tree is identical to the reviewed head `46a642366c0b79079be4b706d94eba78608c4305` (`git diff --stat` between them is empty).
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a detached worktree of the build), GitHub and the tracker.
Fixtures: none needed; the probes read `skills/qa-verification/SKILL.md` and the PR diff at the build and run the repository's guards.
The raw output is attached to SKL-156 as `SKL-156-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: step 4 pending owner ruling record | Verified | Step 4 items 1, 2 and 5; details below. |
| AC2: step 6 routing with pending items | Verified | Step 6 not-finished bullet, finished lead-in and `in_progress` bullet; details below. |
| AC3: ruling path and done guards | Verified | Step 6 ruling bullet and `done` bullet; details below. |
| AC4: pins | Verified | Every added sentence is pinned verbatim with its prefix, and no existing pin was disturbed; details below. |
| AC5: five guards | Verified | Every guard passed on the build, the private leak scan in CI; details below. |
| DoD: all acceptance criteria met | Verified | AC1 to AC5. |
| DoD: tests written and passing | Verified | AC4 and AC5. |
| DoD: independently reviewed | Verified | Review 5897035154 names `46a642366c0b79079be4b706d94eba78608c4305` in its first line and as its `commit_id`, the merged head, with Codex GPT-6 Sol reviewing and DeepSeek V4.1 Flash adjudicating. |
| DoD: docs updated | Verified | The change is the skill text itself. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43493927930) and on `main` (run 43495139116). |

Details:

- AC1:
  - Item 1 adds `failed` and `pending owner ruling` to the verdict list.
  - Item 2 records `pending owner ruling` only when two or more readings of the quoted AC or DoD text give different verdicts on the same evidence.
  - It states that missing evidence, access or execution alone does not qualify, that failing under every reading is a failure, and that meeting every reading is verified.
  - It puts the record in the QA evidence comment (item 5) with the item, its quoted text, each reading with its verdict and evidence, and the product owner as owner.
  - Item 5's comment sentence lists "each pending owner ruling record (item 2)".
  - Step 4 items run 1 to 5, and the two cross-references now name item 4 (evidence page) and item 5 (tracker).
- AC2:
  - The not-finished bullet says that with only `pending owner ruling` items and no failed item, QA is not finished, the story stays in `profile.tracker.states.in_deployment_review`, and the comment names each item, its owner and the ruling it waits on.
  - The finished lead-in says a failed item finishes QA even while other items are pending.
  - The `in_progress` bullet lists pending items apart as not for the engineer and writes no deployment-review AC amendment for a pending item.
- AC3:
  - A step 6 bullet says a ruling reaches QA only as the product owner's dated AC amendment on the tracker.
  - It says a new QA round, a new QA agent on an unchanged brief, then verifies the amended item against the amended text with fresh evidence.
  - The `done` bullet says never to mark done on an AC amendment alone, and never while any item is still `pending owner ruling`.
- AC4:
  - The PR adds 19 lines to the skill; 16 carry new or reworded sentences, and each is a verbatim pin, with its bullet prefix, in `tests/test_qa_pending_owner_ruling.py`.
  - The other 3 lines only renumber existing step 4 items (2 to 3, 3 to 4, 4 to 5); `test_step_4_items_stay_numbered_one_to_five` pins the numbering.
  - `git grep` over `tests/` at the parent commit finds no pin on any line the PR changes, and the PR edits no other test module, so no existing pin needed an update.
- AC5:
  - On the build, `uv run --locked pytest -q` passed (2140 passed locally).
  - `python3 scripts/vendor_shared.py --check` exited 0.
  - `skills-ref validate` at the CI ref `69ef37e` passed for all 18 skills.
  - `bash scripts/smoke-opencode.sh` discovered 18 skills in each of its 6 layouts.
  - The public leak scan exited 0; its private half runs only in CI.
  - CI run 43493927930 on the reviewed head passed `checks` (2158 tests, and the leak scan with `--require-private` and the denylist loaded) and `discovery`.
  - CI run 43495139116 on `main` passed both jobs.

Closing decision: SKL-156 moves to Done once this evidence PR merges.
