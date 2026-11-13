# SKL-282 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `1f6fc99c40672bed42d81c9209c2de7f6cf935d6`, the squash merge of PR 224.
Its reviewed head `2fdaf2b5a2795a386edebe3c034d320e5d8edb83` adds and removes the same lines; only blob indexes and one hunk offset differ, because SKL-237 merged between the PR base `954fb5821be7af8da2c5b16a03ee1ceec2760fa1` and the merge.
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a detached worktree of the build), GitHub and the tracker.
Fixtures: none needed; the probes read the skill and `shared/linear.md` at the build and run the repository's own tests.
The raw output is attached to SKL-282 as `SKL-282-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.
The blocker SKL-162 is Done.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: handoff after merge without a deploy | Verified | Steps 11 and 12 carry every clause; details below. |
| AC2: spike deliverables in the step 12 note | Verified | Step 12 handoff item 1; details below. |
| AC3: spike with no tracked-file change | Verified | Step 3 subsection and the step 12 spike sentences; details below. |
| AC4: gates on a spike PR | Verified | Step 3 subsection, last sentence. |
| AC5: pins | Verified | Each of 30 deletion mutants fails its own test id; details below. |
| AC6: deployed path regression | Verified | No other test module was edited, and all 13 pass on the build; details below. |
| AC7: repository guards | Verified | Every guard passed on the build and in CI; details below. |
| DoD: all acceptance criteria met | Verified | AC1 to AC7. |
| DoD: tests written and passing | Verified | AC5 to AC7. |
| DoD: independently reviewed | Verified | Review 5895855500 names `2fdaf2b5a2795a386edebe3c034d320e5d8edb83` in its first line and as its `commit_id`, the merged head. |
| DoD: docs updated | Verified | The change is the skill text and the vendored `linear.md`. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43479417494) and on `main` (run 43480403245). |

Details:

- AC1:
  - Step 11 opens with "This step runs on the `deployed` path only." and says to skip it on the `no-deployment` and `spike` paths, claiming no deploy and verifying none.
  - Step 11 also states that every step up to and including the merge runs on those paths as on `deployed`, except the steps 4 to 10 a spike with no tracked-file change skips.
  - Step 12 keeps its heading, and a new sentence states that "Only after the deployment is verified", "(never on merge alone)" and the deployed Done sentence apply to the `deployed` path only.
  - The "Handoff on the `no-deployment` and `spike` paths" subsection runs once a fetch shows the merged commit on `origin/<profile.git.integration_branch>` (`git merge-base --is-ancestor`), or, for a spike with no tracked-file change, once the AC3 condition holds.
  - Its note names the path and the merged commit, or, for a spike with no tracked-file change, the path and that there is no merged commit.
  - It moves the story to `profile.tracker.states.in_deployment_review`, and its read-back line is the deployed read-back verbatim.
  - Its closing sentence says Done comes after the acceptance criteria are verified against the merged commit, not in a deployed environment, with the AC3 variant for a spike with no tracked-file change.
  - `git diff --numstat 1f6fc99^ 1f6fc99` shows 34 added and 0 removed lines in the skill, so the existing `deployed` text of steps 11 and 12 is unchanged.
  - `shared/linear.md` Status lifecycle scopes its deploy conditions for this handoff, and `scripts/vendor_shared.py --check` exits 0.
- AC2:
  - Handoff item 1 says that on `spike` the note names each deliverable from the Deliverables section with its link and, for a tracked artifact, its commit.
- AC3:
  - The "Spike with no tracked-file change" subsection sits in step 3, before step 4.
  - It fetches `origin` and checks the working tree, the index and the commits relative to `origin/<profile.git.integration_branch>`.
  - It skips steps 4 to 10 only when all three checks show no tracked-file change, and repeats the checks immediately before step 12.
  - A tracked-file change at any point sends the spike through steps 4 to 10 with every gate and onto the merge path.
  - Step 12 runs for that spike once each deliverable is linked on the story, its note says steps 4 to 10 were skipped, and its closing sentence names the linked deliverables.
- AC4:
  - The subsection ends with "Any PR a spike produces runs every gate steps 4 to 10 define: the `spike` path changes no gate, waiver, admin override or expected-head condition."
- AC5:
  - Every non-blank line the PR adds to the skill (26) and to `shared/linear.md` (2) is a pin in `tests/test_no_deployment_path.py`, the `linear.md` pins checked in `shared/` and the `engineering-workflow` copy.
  - With the build unmutated, the module passes (77 passed).
  - Deleting each of the 30 pinned lines in turn made its own test id fail, with the failure counts the PR description's table lists.
  - The one replaced pin, `test_steps_two_to_twelve_are_unchanged`, carries a comment naming what replaced it, why, and the pins that keep its coverage, and its digest constant is unchanged.
- AC6:
  - `git grep -l engineering-workflow 954fb58 -- tests` returns the 13 modules the PR records, and the same command at `eb8ec19` returns the same 13.
  - The PR edits no test module other than `tests/test_no_deployment_path.py`.
  - Those 13 modules pass on the build (1036 passed).
- AC7:
  - On the build, `uv run --locked pytest -q` passed (2128 passed) and the public leak scan exited 0.
  - `skills-ref validate` passed for all 18 skills, including `skills/engineering-workflow/`.
  - `bash scripts/smoke-opencode.sh` discovered 18 skills in each of its 6 layouts.
  - The private-pattern half of the leak scan runs only in CI.
  - CI run 43479417494 on the reviewed head passed `checks` (with the leak scan `--require-private`) and `discovery`.
  - CI run 43480403245 on `main` passed both jobs.

Closing decision: SKL-282 moves to Done once this evidence PR merges.
