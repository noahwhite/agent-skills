# SKL-243 QA evidence

## Round 1

Date: 2026-11-10 UTC, independent QA round 1.
Story: SKL-243 - `cleanup` removes a landed worktree that holds only regenerable ignored entries.
Build under test: `main` at `1034263a24aaba91488470f8350a9329fde17146`, the squash merge of PR 186, whose reviewed head is `81ee470bbaa02965403955c156e6639eadc0cbff`.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite and the repository reads ran in a detached worktree of the build; the probes ran against the fixtures below.
Method: a probe ran the step 3 rule of `skills/cleanup/SKILL.md` literally, from the status read through `git worktree remove` and its read-back.
Fixtures:

- The real `feature/SKL-243-cleanup-regenerable-ignored-entries` worktree, at PR 186's head, probed read-only with no deletion.
- A local clone with a worktree at PR 186's head `81ee470`, holding real `uv` and `pytest` output: `.pytest_cache/`, `.venv/`, `scripts/__pycache__/` and `tests/__pycache__/`.
  These are the four entries for which `/cleanup SKL-88` refused its worktree, as the SKL-243 story records.
- 19 synthetic repositories, one per refusal or pass case, each with merge evidence assumed.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-243 as `SKL-243-a1-real-skl243-worktree-readonly.txt`, `SKL-243-a1-manual-trace-execute.txt`, `SKL-243-a1-a2-a4-fixtures-execute.txt`, `SKL-243-a5-mutation-spot-check.txt`, `SKL-243-dod2-pytest-1034263a.txt` and `SKL-243-repo-lane-a4-dod.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| A1: regenerable ignored entries | Verified | On the real worktree all four entries classify as `remove` and pass the listing and content checks. On the clone, `rm -r --` deletes all four, the second status read is empty, `git worktree remove` exits 0, and `git worktree list` no longer shows the worktree. A nested `.git`, a bare repository, `.venv` without `pyvenv.cfg`, a non-`.pyc` file in `__pycache__`, `.mypy_cache` without `CACHEDIR.TAG`, and a failed deletion each refuse the worktree. All seven names pass together, including a stray file inside a passing `.venv`. |
| A2: other entries still refuse | Verified | An ignored `.env`, an untracked file, an untracked directory, a tracked modification, a staged addition, a symlink named `.venv`, a regular file named `node_modules`, and an untracked `__pycache__/` each refuse the worktree with every entry still on disk. A directory that holds only a cache is reported by git as its ignored parent and refuses, which is the safe direction PR 186 documents. |
| A3: report by exact path | Verified | The inventory and the report name each entry by exact path, such as `scripts/__pycache__/`. A failed deletion reports the path, the `rm` error and the paths that remain, and lists the entry deleted before it. |
| A4: existing guards unchanged | Verified | A detached HEAD, a locked worktree and the main working tree are refused. The merge-evidence, session-hosting and read-back sentences are present at the build. No command uses `--force`: two mentions forbid it, and the third notes that git offers no checked removal short of it. At the merge parent the rule refused any ignored file, so a worktree holding those four entries was refused before this change. |
| A5: tests | Verified | Deleting each of 17 A1 to A3 sentences from `skills/cleanup/SKILL.md`, one at a time, makes `tests/test_cleanup.py` fail 17 of 17 times. |
| DoD: all acceptance criteria met | Verified | A1 to A5 above. |
| DoD: tests written and passing | Verified | `uv run --locked pytest -q` reports 1573 passed at the build. CI `checks` and `discovery` succeeded on `81ee470` and on `1034263`. |
| DoD: independently reviewed | Verified | The PR 186 review of record names `81ee470` in its first line and as its `commit_id`, which is the merged head. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4 Pro, with no open blocking finding. |
| DoD: docs updated | Verified | PR 186 edits steps 2, 3 and 6 of `skills/cleanup/SKILL.md`. |
| DoD: verified in a deployed environment | Not needed | The repository deploys nothing (`environments: []`), so the delivered skill text on `main` at the build is what was verified. |
| DoD: no critical bugs or regressions | Verified | The A2 and A4 refusals hold and the full suite passes. |

Closing decision: Done, once this evidence merges.
