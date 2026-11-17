"""SKL-70 AC6: engineering-workflow step 2 works in a worktree the brief names instead of cutting another."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "engineering-workflow" / "SKILL.md"

CUT_SENTENCE = (
    "Cut a branch and worktree per `references/github.md`, from `origin/<integration branch>` (the integration "
    "branch is `profile.git.integration_branch`) after a fetch."
)
WORKTREE_CLAUSE = (
    "When the brief names a `worktree:` path, work in that worktree and cut no other, after confirming that its "
    "branch is based on `origin/<profile.git.integration_branch>` and recutting it per the worktree rule in "
    "`references/github.md` if it is not; without a `worktree:` line, cut the branch and worktree as the sentence "
    "above states."
)


def step_2_lines() -> list[str]:
    text = SKILL.read_text(encoding="utf-8")
    match = re.search(r"^## 2\. Plan slices\n", text, re.MULTILINE)
    assert match, "missing step 2"
    rest = text[match.end():]
    return rest[: re.search(r"^## ", rest, re.MULTILINE).start()].splitlines()


def test_step_2_works_in_the_briefed_worktree_and_otherwise_cuts_one() -> None:
    lines = step_2_lines()
    assert CUT_SENTENCE in lines, "without a `worktree:` line step 2 still cuts the branch and worktree"
    assert WORKTREE_CLAUSE in lines, "step 2 must accept the worktree the brief names"
    assert lines.index(WORKTREE_CLAUSE) == lines.index(CUT_SENTENCE) + 1, "the clause follows the cut sentence"
    assert SKILL.read_text(encoding="utf-8").count(WORKTREE_CLAUSE) == 1, "the clause is stated once"
