"""SKL-233: five working rules moved from agent memory into the shared capability files.

Each rule is pinned by its load-bearing clauses at its home section and position, only in
rendered prose (fenced blocks and HTML comments do not count), and only once across `shared/`,
so a later edit that drops, hides, moves or duplicates it fails here.
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def spaced(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def active(text: str) -> str:
    """The rendered prose of a Markdown file: HTML comments and fenced blocks removed."""
    lines, fenced = [], False
    for line in COMMENT_RE.sub("", text).splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
        elif not fenced:
            lines.append(line)
    return "\n".join(lines)


def read(path: Path) -> str:
    return active(path.read_text())


def headings(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def section(text: str, heading: str) -> str:
    parts = re.split(r"^## (.+?)[ \t]*$", text, flags=re.M)
    bodies = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
    if heading not in bodies:
        raise AssertionError(f"missing section: {heading}")
    return bodies[heading]


def bullets(body: str) -> list[str]:
    """Top-level bullets of a section body, each with its indented lines joined onto one line."""
    items: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line[2:])
        elif line.startswith("  ") and items:
            items[-1] += " " + line
    return [spaced(item) for item in items]


def index_of(items: list[str], prefix: str) -> int:
    found = [i for i, item in enumerate(items) if item.startswith(prefix)]
    if not found:
        raise AssertionError(f"no bullet starts with: {prefix}")
    return found[0]


def assert_clauses(item: str, clauses: list[str]) -> None:
    missing = [clause for clause in clauses if clause not in item]
    assert not missing, f"missing clauses {missing} in: {item}"


def shared_bullets() -> list[str]:
    return [b for md in sorted(SHARED.glob("*.md")) for b in bullets(read(md))]


def assert_once_in_shared(anchor: str) -> None:
    hits = [b for b in shared_bullets() if anchor in b]
    assert len(hits) == 1, f"{anchor!r} appears in {len(hits)} bullets of shared/"


# --- K1 and K2: shared/engineering-practice.md --------------------------------------------------

K1 = [
    "When the source pattern found by the search above has been read in this session",
    "every substitution is known (names, identifiers, paths)",
    "write the output",
    "read another file only to obtain a named missing fact, never for confirmation or completeness",
    "The full read stays when a substitution is unknown",
    "crosses a transaction, dependency-injection or credential boundary",
    "\"When mirroring a proven handler\" in \"Fix the whole class, not the first instance\"",
    "when this is the first read of the source (the porting bullet below)",
    "never limits reading an authoritative source before asserting a fact",
]

K2 = [
    "A \"why is X needed\" question is a genuine question, not an instruction to remove X.",
    "Before agreeing or removing X, state what X does and what fails without it",
    "when X is needed, say so and change nothing",
    "Remove X only when that reasoning shows it is unneeded and the removal is within what was asked.",
]


def test_k1_over_reading_follows_the_search_bullet() -> None:
    items = bullets(section(read(SHARED / "engineering-practice.md"), "Reuse and study existing code"))
    assert items[0].startswith("Before writing code for an operation"), "the search bullet must stay first"
    assert_clauses(items[1], K1)
    assert any(item.startswith("When porting") for item in items[2:]), "the porting bullet must stay below K1"
    assert_once_in_shared(K1[0])


def test_k1_has_no_contradicting_read_for_completeness_rule() -> None:
    hits = [b for b in shared_bullets() if re.search(r"for (?:completeness|confirmation)", b)]
    assert len(hits) == 1 and hits[0].startswith(K1[0]), hits


def test_k2_why_is_x_needed_follows_change_exactly_what_was_asked() -> None:
    items = bullets(section(read(SHARED / "engineering-practice.md"), "Make minimal, durable changes"))
    asked = index_of(items, "Change exactly what was asked")
    assert_clauses(items[asked + 1], K2)
    assert_once_in_shared(K2[0])


# --- K3: shared/code-review.md --------------------------------------------------------------

K3 = [
    "**Scoped sub-task:** a scoped sub-task goes to a clean, neutral agent whose self-contained prompt",
    "names the files, areas and systems it must not touch and the point where it stops",
    "never to a `fork`, because a fork inherits the whole conversation",
    "Before acting on a subagent's self-report, the delegator verifies it against ground truth "
    "(git history and refs, the PR list, run conclusions)",
    "reads the code the subagent wrote before merging it",
    "Related rules, not restated here: Clean, above; reading an automated fixer's commits, in "
    "\"Automated pre-PR gates\" below; and the coordinator's own read of each merged PR, in "
    "`story-to-done` step 2.",
]


def test_k3_delegation_sits_in_the_clean_and_neutral_block() -> None:
    body = section(read(SHARED / "code-review.md"), "Review of record")
    block = body.split("the two always go together:\n", 1)[1].split("\n1. ", 1)[0]
    items = bullets(block)
    assert items[0].startswith("**Clean:**")
    assert items[1].startswith("**Neutral:**")
    assert_clauses(items[2], K3)
    assert_once_in_shared(K3[0])


def test_k3_cross_references_resolve() -> None:
    review = read(SHARED / "code-review.md")
    assert any("fixer" in b and "commits" in b for b in bullets(section(review, "Automated pre-PR gates")))
    step2 = section(read(ROOT / "skills" / "story-to-done" / "SKILL.md"), "2. Senior engineer: implement to deployment review")
    assert "for every PR it merged, read the PR yourself" in spaced(step2)


# --- K4: shared/linear.md ---------------------------------------------------------------------

K4 = [
    ["An issue key the owner names explicitly is acted on as written",
     "also when it appears inside an instruction about a different story",
     "never treated as a typo for another key"],
    ["When the named story is not yet in the state the action needs, wait, re-read its state, "
     "and say that you are waiting",
     "when the instruction contradicts the story's state or another instruction, ask the owner before acting"],
    ["Never substitute another key.",
     "A missing key is covered by the \"never guess\" line of the `STORY_ID` argument rule of a skill "
     "that takes one, not restated here."],
]


def test_k4_named_story_keys_follows_team_resolution() -> None:
    text = read(SHARED / "linear.md")
    names = headings(text)
    assert names[names.index("Team resolution") + 1] == "Named story keys"
    items = bullets(section(text, "Named story keys"))
    assert len(items) == len(K4)
    for item, clauses in zip(items, K4):
        assert_clauses(item, clauses)
    assert_once_in_shared(K4[0][0])


# --- K5: shared/github.md ---------------------------------------------------------------------

K5 = [
    ["Presume a persistent local clone or checkout stale",
     "before citing a repo fact, run `git fetch origin` and read `git show origin/<branch>:<path>`, never the working tree"],
    ["`<branch>` is `profile.git.integration_branch`",
     "`profile.git.release_branch` for a path that exists only there",
     "for an environment's declared state, the branch that deploys that environment (`profile.environments[].branch`)"],
    ["The exception is your own uncommitted or unpushed change in your story worktree."],
    ["When the fetch or the read fails, report the limitation and never present stale content as current."],
    ["Related rules, not restated here: the fetch rule in \"Branching and worktrees\" below",
     "\"Verify running state from the primary source\" in the `infra-deploy` capability file",
     "\"Base the run on `origin/<integration branch>` after a fetch\" in \"Automated pre-PR gates\" "
     "of the `code-review` capability file"],
]


def test_k5_read_repo_facts_sits_between_tooling_and_branching() -> None:
    text = read(SHARED / "github.md")
    names = headings(text)
    at = names.index("Read repo facts from the remote")
    assert names[at - 1 : at + 2] == ["Tooling", "Read repo facts from the remote", "Branching and worktrees"]
    items = bullets(section(text, "Read repo facts from the remote"))
    assert len(items) == len(K5)
    for item, clauses in zip(items, K5):
        assert_clauses(item, clauses)
    assert_once_in_shared(K5[0][0])


def test_k5_cross_references_resolve() -> None:
    assert "Verify running state from the primary source" in headings(read(SHARED / "infra-deploy.md"))
    gates = spaced(section(read(SHARED / "code-review.md"), "Automated pre-PR gates"))
    assert "Base the run on `origin/<integration branch>` after a fetch" in gates
