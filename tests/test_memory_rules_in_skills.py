"""SKL-233: five working rules moved from agent memory into the shared capability files.

Each rule is pinned verbatim, as rendered text, at its home section and position, and its anchor
occurs only once across `shared/` and every `skills/*/SKILL.md`, so a later edit that drops,
weakens, hides, moves or duplicates it fails here.
A cross-referenced target is checked for presence only, not pinned: its text belongs to other rules.
Rendered text is the text of the CommonMark parse: inline markup, link targets and titles, HTML
tags, comments and attributes, and image alt text do not count, and a code span keeps its backticks.
Every file these tests read a rule or a cross-reference from carries no raw HTML that could hide
text: no HTML block, comment, closing tag or attribute anywhere in the file, only bare placeholder
tags such as `<name>`.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token


ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
MARKDOWN = MarkdownIt("commonmark")
EM_DASH = chr(0x2014)
# Placeholders written as tags in the files these tests read. None is an HTML element or carries an
# attribute that hides content, so each hides nothing; a new one is added here after that check.
PLACEHOLDER_TAGS = {"<model>", "<n>", "<name>", "<retained state>", "<type>"}


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def rendered(inline: Token, prose: bool = False) -> str:
    """The rendered text of an inline token, whitespace collapsed.

    In prose, a code span that holds more than one word stands for an example, not an instruction,
    and renders as `code`; a one-word code span such as `STORY_ID` keeps its text.
    """
    parts = []
    for child in inline.children or []:
        if child.type == "text":
            parts.append(child.content)
        elif child.type == "code_inline":
            code = "code" if prose and re.search(r"\s", child.content.strip()) else child.content
            parts.append(f"`{code}`")
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return collapse("".join(parts))


class _VisibleText(HTMLParser):
    """Collects the character data a browser shows: entities decoded; tags, attributes, comments,
    and script and style bodies dropped."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def html_text(html: str) -> str:
    """The text an HTML block shows."""
    parser = _VisibleText()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)


@dataclass
class Doc:
    path: Path
    headings: list[str] = field(default_factory=list)
    lists: dict[str, list[list[str]]] = field(default_factory=dict)
    paragraphs: dict[str, list[str]] = field(default_factory=dict)
    # Raw HTML other than a placeholder tag, anywhere in the file.
    html: list[str] = field(default_factory=list)
    # Every heading, paragraph and HTML block's text in document order, for counting anchors.
    flow: list[str] = field(default_factory=list)
    # Every heading and paragraph as prose (see `rendered`), in document order.
    prose: list[str] = field(default_factory=list)

    def section(self, heading: str) -> list[list[str]]:
        """The top-level bullet lists under a heading that occurs exactly once."""
        count = self.headings.count(heading)
        if count != 1:
            raise AssertionError(f"{self.path}: heading {heading!r} occurs {count} times")
        return self.lists[heading]

    def bullets(self, heading: str) -> list[str]:
        return [item for group in self.section(heading) for item in group]

    def text(self) -> str:
        return collapse(" ".join(self.flow))


PREAMBLE = ""  # the section key for content before the first heading


def parse(path: Path) -> Doc:
    """Document-level headings, the top-level bullet items under each, and every rendered paragraph.

    Every heading at document level opens a section; a heading nested in a list item or quote does
    not. A bullet item's text is its own paragraphs only, not a nested list or quote inside it.
    Content before the first heading belongs to the PREAMBLE section.
    """
    doc = Doc(path=path, lists={PREAMBLE: []}, paragraphs={PREAMBLE: []})
    current, opened, item, in_bullets = PREAMBLE, None, None, False
    for token in MARKDOWN.parse(path.read_text(encoding="utf-8")):
        if token.type == "html_block":
            doc.html.append(token.content.strip())
            doc.flow.append(html_text(token.content))
        elif token.type in ("heading_open", "paragraph_open"):
            opened = token
        elif token.type == "inline" and opened is not None:
            doc.html.extend(
                child.content for child in token.children or []
                if child.type == "html_inline" and child.content not in PLACEHOLDER_TAGS
            )
            text = rendered(token)
            doc.flow.append(text)
            doc.prose.append(rendered(token, prose=True))
            if opened.type == "heading_open" and opened.level == 0:
                current = text
                doc.headings.append(current)
                doc.lists.setdefault(current, [])
                doc.paragraphs.setdefault(current, [])
            elif opened.type == "paragraph_open":
                doc.paragraphs[current].append(text)
                if item is not None and opened.level == 2:
                    group = doc.lists[current][-1]
                    group[item] = f"{group[item]} {text}".strip()
            opened = None
        elif token.type == "bullet_list_open" and token.level == 0:
            doc.lists[current].append([])
            in_bullets = True
        elif token.type == "list_item_open" and token.level == 1 and in_bullets:
            doc.lists[current][-1].append("")
            item = len(doc.lists[current][-1]) - 1
        elif token.type == "bullet_list_close" and token.level == 0:
            item, in_bullets = None, False
    return doc


def read(path: Path) -> Doc:
    """Parse a file a rule or a cross-reference is read from; it must carry no raw HTML."""
    doc = parse(path)
    assert not doc.html, f"{path}: raw HTML that could hide text: {doc.html}"
    return doc


def index_of(items: list[str], prefix: str) -> int:
    found = [i for i, item in enumerate(items) if item.startswith(prefix)]
    assert len(found) == 1, f"{len(found)} bullets start with: {prefix}"
    return found[0]


def assert_rule(item: str, expected: str) -> None:
    assert EM_DASH not in expected, "a pinned rule must not carry an em dash"
    assert item == expected, f"rule text changed:\n  expected: {expected}\n  found:    {item}"


def source_docs() -> list[Doc]:
    sources = sorted(SHARED.rglob("*.md")) + sorted(ROOT.glob("skills/*/SKILL.md"))
    return [parse(md) for md in sources]


def assert_once(anchor: str) -> None:
    """The anchor occurs once in the text of all sources, however it is split across blocks."""
    hits = sum(doc.text().count(anchor) for doc in source_docs())
    assert hits == 1, f"{anchor!r} occurs {hits} times in shared/ and skills/*/SKILL.md"


# --- K1 and K2: shared/engineering-practice.md --------------------------------------------------

K1 = (
    "When the source pattern found by the search above has been read in this session and every "
    "substitution is known (names, identifiers, paths), write the output, and read another file only "
    "to obtain a named missing fact, never for confirmation or completeness. The full read stays when "
    "a substitution is unknown, when the target crosses a transaction, dependency-injection or "
    "credential boundary (\"When mirroring a proven handler\" in \"Fix the whole class, not the first "
    "instance\"), or when this is the first read of the source (the porting bullet below). This bounds "
    "re-reading a known template only, and never limits reading an authoritative source before "
    "asserting a fact."
)

K2 = (
    "A \"why is X needed\" question is a genuine question, not an instruction to remove X. Before "
    "agreeing or removing X, state what X does and what fails without it; when X is needed, say so and "
    "change nothing. Remove X only when that reasoning shows it is unneeded and the removal is within "
    "what was asked."
)


def test_k1_over_reading_follows_the_search_bullet() -> None:
    items = read(SHARED / "engineering-practice.md").bullets("Reuse and study existing code")
    assert items[0].startswith("Before writing code for an operation"), "the search bullet must stay first"
    assert_rule(items[1], K1)
    assert any(item.startswith("When porting") for item in items[2:]), "the porting bullet must stay below K1"
    assert_once(K1[:80])


def test_k1_cross_reference_resolves() -> None:
    items = read(SHARED / "engineering-practice.md").bullets("Fix the whole class, not the first instance")
    index_of(items, "When mirroring a proven handler")


def test_k2_why_is_x_needed_follows_change_exactly_what_was_asked() -> None:
    items = read(SHARED / "engineering-practice.md").bullets("Make minimal, durable changes")
    asked = index_of(items, "Change exactly what was asked")
    assert_rule(items[asked + 1], K2)
    assert_once(K2[:80])


# --- K3: shared/code-review.md --------------------------------------------------------------

K3 = (
    "Scoped sub-task: a scoped sub-task goes to a clean, neutral agent whose self-contained prompt "
    "names the files, areas and systems it must not touch and the point where it stops, never to a "
    "`fork`, because a fork inherits the whole conversation. Before acting on a subagent's "
    "self-report, the delegator verifies it against ground truth (git history and refs, the PR list, "
    "run conclusions), and it reads the code the subagent wrote before merging it. Related rules, not "
    "restated here: Clean, above; reading an automated fixer's commits, in \"Automated pre-PR gates\" "
    "below; and the coordinator's own read of each merged PR, in `story-to-done` step 2."
)


def test_k3_delegation_sits_in_the_clean_and_neutral_block() -> None:
    block = read(SHARED / "code-review.md").section("Review of record")[0]
    assert block[0].startswith("Clean:")
    assert block[1].startswith("Neutral:")
    assert_rule(block[2], K3)
    assert_once(K3[:80])


def test_k3_cross_references_resolve() -> None:
    gates = read(SHARED / "code-review.md").bullets("Automated pre-PR gates")
    assert any("fixer" in b and "commits" in b for b in gates)
    story_to_done = read(ROOT / "skills" / "story-to-done" / "SKILL.md")
    story_to_done.section("2. Senior engineer: implement to deployment review")
    step2 = " ".join(story_to_done.paragraphs["2. Senior engineer: implement to deployment review"])
    assert "for every PR it merged, read the PR yourself" in step2


# --- K4: shared/linear.md ---------------------------------------------------------------------

STORY_ID_SKILLS = ("persona-staff-devops", "persona-staff-engineer", "story-refinement", "story-to-done")

K4 = [
    "An issue key the owner names explicitly is acted on as written, also when it appears inside an "
    "instruction about a different story, and is never treated as a typo for another key.",
    "When the named story is not yet in the state the action needs, wait, re-read its state, and say "
    "that you are waiting; when the instruction contradicts the story's state or another instruction, "
    "ask the owner before acting.",
    "Never substitute another key. A missing key is covered by the \"never guess\" line of the "
    "`STORY_ID` argument rule of a skill that takes one, not restated here.",
]


def test_k4_named_story_keys_follows_team_resolution() -> None:
    doc = read(SHARED / "linear.md")
    doc.section("Team resolution")
    items = doc.bullets("Named story keys")
    assert doc.headings[doc.headings.index("Team resolution") + 1] == "Named story keys", (
        f"{doc.path}: \"Named story keys\" must directly follow \"Team resolution\""
    )
    assert len(items) == len(K4)
    for item, expected in zip(items, K4):
        assert_rule(item, expected)
    assert_once(K4[0][:80])


def test_k4_cross_reference_resolves() -> None:
    """Every skill that takes a `STORY_ID` has exactly one `STORY_ID` argument rule, and it carries
    the "never guess" line K4 points to. The skills that take one today are named, so deleting a
    whole argument rule cannot drop a skill from the check."""
    declaration = re.compile(r"This skill takes one argument, `STORY_ID`:|`STORY_ID` is required:")
    never_guess = re.compile(
        r" If none was given, ask the (user|owner) for one before doing anything else; "
        r"never guess (a story number|an issue key)\."
    )
    skills = sorted(
        {ROOT / "skills" / name / "SKILL.md" for name in STORY_ID_SKILLS}
        | {md for md in ROOT.glob("skills/*/SKILL.md") if "STORY_ID" in md.read_text(encoding="utf-8")}
    )
    problems = []
    for md in skills:
        doc = read(md)
        declared = sum(len(declaration.findall(unit)) for unit in doc.prose)
        rules = [unit for unit in doc.prose if declaration.search(unit)]
        if declared != 1:
            problems.append(f"{md.parent.name}: {declared} `STORY_ID` argument declarations")
        elif not never_guess.search(rules[0]):
            problems.append(f"{md.parent.name}: argument rule without the never-guess line")
    assert not problems, problems


# --- K5: shared/github.md ---------------------------------------------------------------------

K5 = [
    "Presume a persistent local clone or checkout stale: before citing a repo fact, run `git fetch "
    "origin +refs/heads/<branch>:refs/remotes/origin/<branch>` and read `git show "
    "origin/<branch>:<path>`, never the working tree. The explicit refspec also refreshes a branch "
    "outside the clone's configured fetch refspec, which a bare `git fetch origin` leaves stale "
    "without an error.",
    "`<branch>` is `profile.git.integration_branch`; `profile.git.release_branch` for a path that "
    "exists only there; or, for an environment's declared state, the branch that deploys that "
    "environment (`profile.environments[].branch`).",
    # The two exceptions of the amended AC K5.
    "The exceptions are your own uncommitted or unpushed change in your story worktree, and a task "
    "bound to an explicitly named commit or PR head (a review or a verification at that SHA), which "
    "reads that commit, with `git show <sha>:<path>` or in a checkout made at it that has no local "
    "changes.",
    "When the fetch or the read fails, report the limitation and never present stale content as current.",
    "Related rules, not restated here: the fetch rule in \"Branching and worktrees\" below; \"Verify "
    "running state from the primary source\" in the `infra-deploy` capability file; and \"Base the run "
    "on `origin/<integration branch>` after a fetch\" in \"Automated pre-PR gates\" of the "
    "`code-review` capability file.",
]


def test_k5_read_repo_facts_sits_between_tooling_and_branching() -> None:
    doc = read(SHARED / "github.md")
    items = doc.bullets("Read repo facts from the remote")
    at = doc.headings.index("Read repo facts from the remote")
    assert doc.headings[at - 1 : at + 2] == ["Tooling", "Read repo facts from the remote", "Branching and worktrees"], (
        f"{doc.path}: \"Read repo facts from the remote\" must sit between \"Tooling\" and \"Branching and worktrees\""
    )
    assert len(items) == len(K5)
    for item, expected in zip(items, K5):
        assert_rule(item, expected)
    assert_once(K5[0][:80])


def test_k5_cross_references_resolve() -> None:
    read(SHARED / "infra-deploy.md").section("Verify running state from the primary source")
    gates = read(SHARED / "code-review.md").bullets("Automated pre-PR gates")
    assert any(b.startswith("Base the run on `origin/<integration branch>` after a fetch") for b in gates)
