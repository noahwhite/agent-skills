# SKL-145 QA evidence - round 1

Date: 2026-10-29.
Build: `5343aed97172aee2df254dcccff4c933a55c1eae` on merged `main`, read from `origin/main` after a fetch and matched against the GitHub API `commits/main`.
Environment: repository state; the repository profile has `environments: []`.
Surface: the frontmatter of `skills/story-to-done/SKILL.md` at the build above, read with git and cross-checked through the GitHub contents API.
Fixtures: none; SKL-145 is a tabletop fixture for SKL-94 C4 whose criterion is existing repository state.
There is no visual surface, so the attached assertions are the raw record, not screenshots or a hosted page.

## Evidence

- Tracker evidence: SKL-145, comment `0ffbe94d`.
- Raw evidence: attachment titled `SKL-145 QA C1 assertions (origin/main 5343aed97172aee2df254dcccff4c933a55c1eae)` on that story.

The frontmatter of `skills/story-to-done/SKILL.md` (blob `fdbf0b5e0e7cfb88f22b2964c5958d490e95df40`) spans lines 1 to 10.
Line 8 is exactly `license: Apache-2.0`, the only whole-line match inside the frontmatter.
The GitHub contents API at the same SHA returns the same line.

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| C1 `license: Apache-2.0` in the `story-to-done` frontmatter at `origin/main` | Verified. | C1 attachment |
| DoD All acceptance criteria met | Verified; C1 is the only criterion. | C1 attachment |

Decision: move SKL-145 to Done once this evidence merges through the exact-head review of record and CI.
SKL-145 has no blocking relations; its only relation is `related` to SKL-94.
No incidental defect was observed.
