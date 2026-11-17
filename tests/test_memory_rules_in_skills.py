"""SKL-233: five working rules moved from agent memory into the shared capability files.

Each rule is pinned by its key clauses at its home section and position, only in rendered prose
(the CommonMark parse, so code blocks and HTML comments do not count), and only once across
`shared/`, so a later edit that drops, hides, moves or duplicates it fails here.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
MARKDOWN = MarkdownIt("commonmark")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def spaced(text: str) -> str:
    return re.sub(r"\s+", " ", COMMENT_RE.sub(" ", text)).strip()


@dataclass
class Doc:
    headings: list[str] = field(default_factory=list)
    lists: dict[str, list[list[str]]] = field(default_factory=dict)
    prose: list[str] = field(default_factory=list)
    paragraphs: dict[str, list[str]] = field(default_factory=dict)

    def section(self, heading: str) -> list[list[str]]:
        """The top-level bullet lists under a `##` heading that occurs exactly once."""
        count = self.headings.count(heading)
        assert count == 1, f"heading {heading!r} occurs {count} times"
        return self.lists[heading]

    def bullets(self, heading: str) -> list[str]:
        return [item for group in self.section(heading) for item in group]


PREAMBLE = ""  # the section key for content before the first `##` heading


def parse(path: Path) -> Doc:
    """Document-level `##` headings, the top-level bullet items under each, and every rendered paragraph.

    Only a heading at document level opens a section; a heading nested in a list item or quote is
    text of its container. Content before the first `##` heading belongs to the PREAMBLE section.
    """
    doc = Doc(lists={PREAMBLE: []}, paragraphs={PREAMBLE: []})
    current, opened, item = PREAMBLE, None, None
    for token in MARKDOWN.parse(path.read_text()):
        if token.type in ("heading_open", "paragraph_open"):
            opened = token
        elif token.type == "inline" and opened is not None:
            text = spaced(token.content)
            if opened.type == "heading_open" and opened.tag == "h2" and opened.level == 0:
                current = token.content.strip()
                doc.headings.append(current)
                doc.lists.setdefault(current, [])
                doc.paragraphs.setdefault(current, [])
            else:
                if opened.type == "paragraph_open":
                    doc.prose.append(text)
                    doc.paragraphs[current].append(text)
                if item is not None:
                    group = doc.lists[current][-1]
                    group[item] = spaced(group[item] + " " + text)
            opened = None
        elif token.type == "bullet_list_open" and token.level == 0:
            doc.lists[current].append([])
        elif token.type == "list_item_open" and token.level == 1 and token.markup in ("-", "*", "+"):
            doc.lists[current][-1].append("")
            item = len(doc.lists[current][-1]) - 1
        elif token.type == "bullet_list_close" and token.level == 0:
            item = None
    return doc


def index_of(items: list[str], prefix: str) -> int:
    found = [i for i, item in enumerate(items) if item.startswith(prefix)]
    if not found:
        raise AssertionError(f"no bullet starts with: {prefix}")
    return found[0]


def assert_clauses(item: str, clauses: list[str]) -> None:
    missing = [clause for clause in clauses if clause not in item]
    assert not missing, f"missing clauses {missing} in: {item}"


def shared_docs() -> list[Doc]:
    return [parse(md) for md in sorted(SHARED.glob("*.md"))]


def assert_once_in_shared(anchor: str) -> None:
    hits = sum(text.count(anchor) for doc in shared_docs() for text in doc.prose)
    assert hits == 1, f"{anchor!r} occurs {hits} times in the rendered prose of shared/"


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
    items = parse(SHARED / "engineering-practice.md").bullets("Reuse and study existing code")
    assert items[0].startswith("Before writing code for an operation"), "the search bullet must stay first"
    assert_clauses(items[1], K1)
    assert any(item.startswith("When porting") for item in items[2:]), "the porting bullet must stay below K1"
    assert_once_in_shared(K1[0])


def test_k2_why_is_x_needed_follows_change_exactly_what_was_asked() -> None:
    items = parse(SHARED / "engineering-practice.md").bullets("Make minimal, durable changes")
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
    block = parse(SHARED / "code-review.md").section("Review of record")[0]
    assert block[0].startswith("**Clean:**")
    assert block[1].startswith("**Neutral:**")
    assert_clauses(block[2], K3)
    assert_once_in_shared(K3[0])


def test_k3_cross_references_resolve() -> None:
    gates = parse(SHARED / "code-review.md").bullets("Automated pre-PR gates")
    assert any("fixer" in b and "commits" in b for b in gates)
    story_to_done = parse(ROOT / "skills" / "story-to-done" / "SKILL.md")
    story_to_done.section("2. Senior engineer: implement to deployment review")
    step2 = " ".join(story_to_done.paragraphs["2. Senior engineer: implement to deployment review"])
    assert "for every PR it merged, read the PR yourself" in step2


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
    doc = parse(SHARED / "linear.md")
    doc.section("Team resolution")
    assert doc.headings[doc.headings.index("Team resolution") + 1] == "Named story keys"
    items = doc.bullets("Named story keys")
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
    ["your own uncommitted or unpushed change in your story worktree",
     "a task bound to an explicitly named commit or PR head",
     "reads that commit, in a checkout made at it or with `git show <sha>:<path>`"],
    ["When the fetch or the read fails, report the limitation and never present stale content as current."],
    ["Related rules, not restated here: the fetch rule in \"Branching and worktrees\" below",
     "\"Verify running state from the primary source\" in the `infra-deploy` capability file",
     "\"Base the run on `origin/<integration branch>` after a fetch\" in \"Automated pre-PR gates\" "
     "of the `code-review` capability file"],
]


def test_k5_read_repo_facts_sits_between_tooling_and_branching() -> None:
    doc = parse(SHARED / "github.md")
    items = doc.bullets("Read repo facts from the remote")
    at = doc.headings.index("Read repo facts from the remote")
    assert doc.headings[at - 1 : at + 2] == ["Tooling", "Read repo facts from the remote", "Branching and worktrees"]
    assert len(items) == len(K5)
    for item, clauses in zip(items, K5):
        assert_clauses(item, clauses)
    assert_once_in_shared(K5[0][0])


def test_k5_cross_references_resolve() -> None:
    parse(SHARED / "infra-deploy.md").section("Verify running state from the primary source")
    gates = parse(SHARED / "code-review.md").bullets("Automated pre-PR gates")
    assert any("Base the run on `origin/<integration branch>` after a fetch" in b for b in gates)
