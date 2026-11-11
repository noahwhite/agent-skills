# SKL-245 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-245 - `cleanup` removes unlanded worktrees and branches on an explicit recorded instruction.
Build under test: `main` at `a77eb7437e4c25817666d323c37d126a72ca15fb`, the squash merge of PR 194, whose reviewed head is `845bddfefb17a7a314e5717ee889b8e747e9ca9d`.
The two files PR 194 changes are identical at that head and at the merge.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite and the text probe ran in a detached worktree of the build, and the mutation run ran in a second one.
Method: a text probe asserted each A1 to A3 sentence in `skills/cleanup/SKILL.md`, and a git probe ran the step 3 recorded-instruction commands literally against the fixture below.
Fixtures:

- A synthetic bare origin and clone with `main` as the integration branch.
- The SKL-88 shape: a linked worktree on `feature/SKL-1-abandoned` holding one unlanded commit, an untracked draft file and an untracked directory with a nested file, plus a tag with the branch's name.
- A detached HEAD worktree and a worktree with a tracked modification, for the step 1 refusal signals.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-245 as `SKL-245-qa-assertions.txt` and `SKL-245-git-probe.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| A1: recorded instruction | Verified | The text probe finds all 15 A1 sentences: the instruction definition and its scope, the five ordered steps, the inventory lines in step 2, the report sentence and the `instruction:` and `discarded:` template lines, and the refusal without an instruction. In the git probe `git worktree remove` exits 128 on the untracked entries without `--force`. The `-z` read lists `draft_test.py` and `out/`, and `git log --oneline origin/main..<tip>` lists the unlanded commit. After `rm -r --` on each entry the second read is empty and HEAD equals the inventory tip. `git worktree remove` and `git branch -D` then exit 0 and read back gone. |
| A2: what the instruction does not waive | Verified | The waiver-scope sentence and the "waives nothing else" list are present verbatim, and the Worktree rule says an instruction never lifts the detached HEAD. In the git probe a detached HEAD makes `git symbolic-ref -q HEAD` exit 1, and a tracked modification reads ` M` in the `-z` status. |
| A3: guard statement | Verified | The new guard list carries the minimum clause, token-boundary attribution, the hosting-worktree rule, the merge-evidence and detached-HEAD rule, and the remote delete rule. The every-removal list keeps no `--force`, the read-back and the second status read. The four lines PR 194 removes from the skill are each replaced by recorded-instruction wording, and no other guard line is removed. |
| A4: tests | Verified | `tests/test_cleanup.py` passes, 51 tests. Deleting each line PR 194 added to the skill, one at a time, makes `tests/test_cleanup.py` fail for 54 of 54 mutants. PR 194 notes its own mutation run, 54 of 54 and 9 of 9. |
| DoD: all acceptance criteria met | Verified | A1 to A4 above. |
| DoD: tests written and passing | Verified | CI `checks` ran `uv run --locked pytest -q` and reported 1649 passed on `845bddf` and on `a77eb74`, and CI `discovery` succeeded on both. The local QA run of `uv run pytest -q` at the build reported 1631 passed; the 18 fewer are the `tests/test_story_to_done.py` cases parametrized once per installed awk, and the QA workstation has only `mawk`. |
| DoD: independently reviewed | Verified | The PR 194 review of record names `845bddf` in its first line and as its `commit_id`. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4 Pro, with no blocking finding. |
| DoD: docs updated | Verified | PR 194 edits the Invocation section, steps 2, 3 and 6, and the Boundaries of `skills/cleanup/SKILL.md`. |
| DoD: verified in a deployed environment | Not needed | The repository deploys nothing (`environments: []`), so the delivered skill text on `main` at the build is what was verified. |
| DoD: no critical bugs or regressions | Verified | The full suite and CI on `main` pass. |

Closing decision: Done, once this evidence merges.
