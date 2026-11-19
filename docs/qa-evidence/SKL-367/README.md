# SKL-367 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `8aa4e13ecee3738e53005ba1300bf450bfe065d1` on `main`, which is the current `origin/main` after a fetch.
Fixtures: none; the criterion is a repository fact read with `git show` from the target commit.
The raw output is attached to SKL-367 as "SKL-367 QA round 1 assertions"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| C1: at `origin/main`, the frontmatter of `skills/story-to-done/SKILL.md` contains the line `license: Apache-2.0` | Verified | `git merge-base --is-ancestor 8aa4e13ecee3738e53005ba1300bf450bfe065d1 origin/main` exits 0 and `git rev-parse origin/main` equals that commit. `git show origin/main:skills/story-to-done/SKILL.md \| grep -n '^license: Apache-2.0$'` returns exactly `8:license: Apache-2.0`, and line 8 sits between the opening `---` at line 1 and the closing `---` at line 10 of the frontmatter. |
| DoD: all acceptance criteria met | Verified | C1 above. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
