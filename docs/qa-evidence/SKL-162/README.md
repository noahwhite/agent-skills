# SKL-162 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `77abaf1ab8f767d46db078910e52d1f9b25fd7c8`, the squash merge of PR 222, whose reviewed head `a86ec897ed2b642c20eb8169c2549963a4d18ee9` has an identical tree.
Base: `7ae1b94118bc711cb050a27586a939d741a9f4a8`, the parent of the merge.
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a standalone clone of the build and a detached worktree for mutants), GitHub and the tracker.
Fixtures: none needed; the probes read `skills/engineering-workflow/SKILL.md` at the base and at the build, and run the repository's own tests.
The raw output is attached to SKL-162 as `SKL-162-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: path selection | Verified | Step 1 item 6 and "Select the path" carry every clause; details below. |
| AC2: ask cases | Verified | The skill lists exactly the four ask cases, before the selection; details below. |
| AC3: scope boundary | Verified | Only step 1 of the skill changed; details below. |
| AC4: deployed path regression | Verified | No existing test module was edited, and all of them pass on the build; details below. |
| AC5: pins | Verified | Each of 19 deletion mutants fails the test ids the PR table lists; details below. |
| AC6: repository guards | Verified | Every guard passed on the build and in CI; details below. |
| DoD: all acceptance criteria met | Verified | AC1 to AC6. |
| DoD: tests written and passing | Verified | AC5 and AC6. |
| DoD: independently reviewed | Verified | Review 5893193451 names `a86ec897ed2b642c20eb8169c2549963a4d18ee9` in its first line and as its `commit_id`, the merged head. |
| DoD: docs updated | Verified | The change is the skill text itself. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43447078547) and on `main` (run 43448057634). |

Details:

- AC1:
  - Step 1 item 6 says to select the run's path as "Select the path" states, before any later step runs.
  - Item 6 sits directly before item 7, the move to In Progress.
  - The "Select the path" subsection sits inside step 1 and names the three paths.
  - It states that a path a brief states governs, that no ask case then applies, and that the path is never reselected.
  - Without a brief, it selects `spike` on the spike label under the differing-team rule in `references/linear.md` "Team resolution".
  - Otherwise it selects `no-deployment` when `profile.environments` is present and `[]`, and otherwise `deployed` when an entry's `branch` equals the integration branch, in that order.
  - It ends with "The selected path governs the whole run.".
- AC2:
  - The ask intro says to ask for the path and run no later step until answered, "in exactly these cases".
  - The block under it is exactly the four AC2 cases, in the AC's order.
  - "An ask case takes precedence over the selection conditions below." sits between the ask block and the selection block.
  - The answer is one of the three paths and replaces the selection.
  - The skill says never to infer a path from prose and to ask nothing else about the path.
- AC3:
  - `git diff --name-status 7ae1b94 77abaf1` lists only `M skills/engineering-workflow/SKILL.md` and `A tests/test_no_deployment_path.py`.
  - The text before step 1, steps 2 to 12, and the text from "Operational rules" to the end are byte-identical to the base.
  - The only removed line is the old item 6, "6. Move it to ...", which is now item 7.
- AC4:
  - The PR records `git grep -l -e engineering-workflow 7ae1b94118bc711cb050a27586a939d741a9f4a8 -- "tests/*.py"` and its output, and the same command returns the same 12 modules here.
  - The PR edits no existing test module.
  - Those 12 modules pass on the build (880 passed).
  - No pin was replaced, so no replacement comment applies.
- AC5:
  - `tests/test_no_deployment_path.py` is new at the build and absent at the base.
  - Each of the 19 non-blank lines the PR adds to the skill is a pin in the module.
  - With the skill unmutated, the module passes (46 passed).
  - Deleting each pinned line in turn made its `test_step_one_pins_path_selection_sentence[<pin>]` fail.
  - The failing ids match the PR description's table row for every pin.
- AC6:
  - On the build, `uv run --locked pytest -q` passed (2018 passed) and the public leak scan exited 0.
  - `skills-ref validate` passed for all 18 skills, including `skills/engineering-workflow/`.
  - `bash scripts/smoke-opencode.sh` discovered 18 skills in each of its 6 layouts.
  - The private-pattern half of the leak scan runs only in CI.
  - CI run 43447078547 on the reviewed head passed `checks` (with the leak scan `--require-private`) and `discovery`.
  - CI run 43448057634 on `main` passed both jobs.

Closing decision: SKL-162 moves to Done once this evidence PR merges.
