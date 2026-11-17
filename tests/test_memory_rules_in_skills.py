"""SKL-233: five working rules moved from agent memory into the shared capability files.

Each rule is pinned in its home section and at its position there, so a later edit that
drops it or moves it out of the section it governs fails here.
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"


def spaced(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section(text: str, heading: str) -> str:
    assert f"\n## {heading}\n" in text, f"missing section: {heading}"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def bullets(body: str) -> list[str]:
    """Top-level bullets of a section body, each joined onto one line."""
    items: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("  ") and items:
            items[-1] += " " + line.strip()
    return [spaced(item) for item in items]


def headings(text: str) -> list[str]:
    return [line[3:] for line in text.splitlines() if line.startswith("## ")]


# --- K1 and K2: shared/engineering-practice.md --------------------------------------------------

K1 = (
    "When the source pattern found by the search above has been read in this session and every "
    "substitution is known (names, identifiers, paths), write the output, and read another file only "
    "to obtain a named missing fact, never for confirmation or completeness. "
    "The full read stays when a substitution is unknown, when the target crosses a transaction, "
    "dependency-injection or credential boundary (\"When mirroring a proven handler\" in "
    "\"Fix the whole class, not the first instance\"), or when this is the first read of the source "
    "(the porting bullet below). "
    "This bounds re-reading a known template only, and never limits reading an authoritative source "
    "before asserting a fact."
)

K2 = (
    "A \"why is X needed\" question is a genuine question, not an instruction to remove X. "
    "Before agreeing or removing X, state what X does and what fails without it; when X is needed, "
    "say so and change nothing. "
    "Remove X only when that reasoning shows it is unneeded and the removal is within what was asked."
)


def test_k1_over_reading_follows_the_search_bullet() -> None:
    items = bullets(section((SHARED / "engineering-practice.md").read_text(), "Reuse and study existing code"))
    assert items[0].startswith("Before writing code for an operation"), "the search bullet must stay first"
    assert items[1] == K1


def test_k2_why_is_x_needed_follows_change_exactly_what_was_asked() -> None:
    items = bullets(section((SHARED / "engineering-practice.md").read_text(), "Make minimal, durable changes"))
    asked = next(i for i, item in enumerate(items) if item.startswith("Change exactly what was asked"))
    assert items[asked + 1] == K2


# --- K3: shared/code-review.md --------------------------------------------------------------

K3 = (
    "**Scoped sub-task:** a scoped sub-task goes to a clean, neutral agent whose self-contained prompt names the files, "
    "areas and systems it must not touch and the point where it stops, never to a `fork`, because a fork "
    "inherits the whole conversation. "
    "Before acting on a subagent's self-report, the delegator verifies it against ground truth (git history "
    "and refs, the PR list, run conclusions), and it reads the code the subagent wrote before merging it. "
    "Related rules, not restated here: Clean, above; reading an automated fixer's commits, in "
    "\"Automated pre-PR gates\" below; and the coordinator's own read of each merged PR, in "
    "`story-to-done` step 2."
)


def test_k3_delegation_sits_in_the_clean_and_neutral_block() -> None:
    body = section((SHARED / "code-review.md").read_text(), "Review of record")
    block = body.split("the two always go together:\n", 1)[1].split("\n1. ", 1)[0]
    items = bullets(block)
    assert items[0].startswith("**Clean:**")
    assert items[1].startswith("**Neutral:**")
    assert items[2] == K3


# --- K4: shared/linear.md ---------------------------------------------------------------------

K4 = [
    "An issue key the owner names explicitly is acted on as written, also when it appears inside an "
    "instruction about a different story, and is never treated as a typo for another key.",
    "When the named story is not yet in the state the action needs, wait, re-read its state, and say that "
    "you are waiting; when the instruction contradicts the story's state or another instruction, ask the "
    "owner before acting.",
    "Never substitute another key. "
    "A missing key is covered by the \"never guess\" line of each skill's `STORY_ID` argument rule, "
    "not restated here.",
]


def test_k4_named_story_keys_follows_team_resolution() -> None:
    text = (SHARED / "linear.md").read_text()
    names = headings(text)
    assert names[names.index("Team resolution") + 1] == "Named story keys"
    assert bullets(section(text, "Named story keys")) == K4


# --- K5: shared/github.md ---------------------------------------------------------------------

K5 = [
    "Presume a persistent local clone or checkout stale: before citing a repo fact, run `git fetch origin` "
    "and read `git show origin/<branch>:<path>`, never the working tree.",
    "`<branch>` is `profile.git.integration_branch`; `profile.git.release_branch` for a path that exists "
    "only there; or, for an environment's declared state, the branch that deploys that environment "
    "(`profile.environments[].branch`).",
    "The exception is your own uncommitted or unpushed change in your story worktree.",
    "When the fetch or the read fails, report the limitation and never present stale content as current.",
    "Related rules, not restated here: the fetch rule in \"Branching and worktrees\" below; "
    "\"Verify running state from the primary source\" in the `infra-deploy` capability file; and "
    "\"Base the run on `origin/<integration branch>` after a fetch\" in \"Automated pre-PR gates\" "
    "of the `code-review` capability file.",
]


def test_k5_read_repo_facts_sits_between_tooling_and_branching() -> None:
    text = (SHARED / "github.md").read_text()
    names = headings(text)
    at = names.index("Read repo facts from the remote")
    assert names[at - 1 : at + 2] == ["Tooling", "Read repo facts from the remote", "Branching and worktrees"]
    assert bullets(section(text, "Read repo facts from the remote")) == K5
