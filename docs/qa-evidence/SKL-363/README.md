# SKL-363 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `9e65dd3e24b10076bd04237971c4f3974164c56a` on `main`, which is the current `origin/main` after a fetch.
Fixtures: none; the criterion is a repository fact read with `git show` from the target commit.
The raw output is attached to SKL-363 as "SKL-363 QA round 1 assertions"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| C1: at `origin/main`, the frontmatter of `skills/story-to-done/SKILL.md` contains the line `license: Apache-2.0` | Verified | `git merge-base --is-ancestor 9e65dd3e24b10076bd04237971c4f3974164c56a origin/main` exits 0 and `git rev-parse origin/main` equals that commit. `git show origin/main:skills/story-to-done/SKILL.md \| grep -n '^license:'` returns exactly `8:license: Apache-2.0`, and line 8 sits between the opening and closing `---` of the frontmatter. |
| DoD: all acceptance criteria met | Verified | C1 above. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
