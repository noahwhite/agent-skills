# SKL-226 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Target: `main` at `ff4716dd7d929a7dcb29a2612933332aec7591ef`, the squash merge of PR 297, whose reviewed head is `8d5b523d6ee7f5df86051ce12b77dd1de55f6a2f`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none; the deliverable is skill text and its contract tests.
The raw output is attached to SKL-226 as "QA round 1: SKL-226 raw assertion output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: short path and its conditions | Verified | `skills/story-refinement/SKILL.md` gains `## Short path`. It is evaluated right after Step 1 item 1 with the item 3 type check inside it, before item 2, any voter launch, preflight comment or tracker write, and Step 1 item 1 ends Steps 1 to 4 on each short-path outcome. Conditions (a) to (d) match the AC text word for word. Condition (e) reads "its assignee is `profile.tracker.assignee`" where the AC says "assignee ... set"; that is the assignee the promotion rule cited under AC2 requires (`persona-product-owner/SKILL.md` line 36), so the path cannot move a story that rule forbids. The skip list and the closing lines `short path: moved to ready`, `exemplars: not looked up` and `anchors: not looked up` match the AC. |
| AC2: PO writes on the path | Verified | The section states that the PO verifies every clause of the named box from the relation list and the recorded backlog search, ticks it, moves the story to ready, reads back the box and the state, and posts the Triage record with the read-back priority. An unverifiable clause makes no write and runs the normal ceremony. The path cites the promotion rule in `persona-product-owner/SKILL.md` and no sentence of `SKILL.md` restates it. |
| AC3: only when all conditions hold | Verified | A backlog story failing any of (a) to (e) runs the normal ceremony, and one with a blocker not done stays out of ready. A Bug, an Investigation, a Spike and a template with no blocker box never take the path. A ready story takes no write and reports `short path: already ready`; an in-progress or later story takes no write and reports `short path: excluded`. |
| AC4: existing write rules hold | Verified | The PO authors every write, and the differing-team rule confirms the ready and backlog states and each label before a write. A denied or failed write stops with `needs input` under Denied tracker writes and is never retried through another tool. "Does not ask" never overrides that stop, and an unset priority fails (e) so the Triage priority stop applies. |
| AC5: test | Verified | `uv run --locked pytest -q tests/test_story_refinement.py` passes 571 at the target. The file asserts the section's conditions, skips, PO writes, read-backs and the AC4 carve-out, and `SHORT_PATH_CASES` holds the five cases (takes the path, unrefined, unpointed, blocker not done, already ready). A QA probe removed each condition phrase from a copy of `SKILL.md` in turn: (a) and (e) each fail 4 and 3 tests, and (b), (c) and (d) each fail 4 tests including their own table case (`unrefined`, `unpointed`, `blocker not done`). |
| AC6: vendored copies | Verified | The merged commit changes no file under `shared/`, and `python3 scripts/vendor_shared.py --check` exits 0 at the target. |
| DoD: all acceptance criteria met | Verified | AC1 to AC6 above. |
| DoD: tests written and passing | Verified | At the target the story's test file passes 571 and the full suite passes 2801 locally, and main CI run 43829173688 on `ff4716dd` passed `checks` and `discovery`. |
| DoD: independently reviewed | Verified | PR 297's review of record is `COMMENTED` at `8d5b523d6ee7f5df86051ce12b77dd1de55f6a2f`, the PR head at merge, with that SHA on its first line, naming Codex `gpt-6-sol` as reviewer and DeepSeek V4 Pro as adjudicator, with blocking count 0. |
| DoD: docs updated | Verified | The skill text is the documentation: `SKILL.md`, the Triage record template and the `Not looked up` vocabulary in `references/refinement-record.md`, and the moved guard check in `references/repository-guards.md`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path; verified against the merged commit. |
| DoD: no critical bugs or regressions | Verified | The full suite passes locally at the target and in main CI, the public-pattern leak scan exits 0 locally and the private scan passes in CI, pinned `skills-ref validate` passes for all 18 skills, the `SKILL.md` body is 497 lines under the 500-line cap, and the guard items moved to `references/repository-guards.md` match the removed `SKILL.md` text apart from link paths and one added skip sentence. |

Closing decision: Done, once this evidence merges.
