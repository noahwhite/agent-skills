"""SKL-387: the local suite run or the CI checks job is one green signal per PR head.

The rule lives in `skills/engineering-workflow/SKILL.md` (step 3 item 5, step 5 item 1 and the
step 9 "All required checks are green" bullet) and in the Definition of Done bullet
"Unit/integration tests written & passing" of `skills/linear-user-story/SKILL.md`.

The Definition of Done bullet is pinned where it lives, inside the fenced template that
`linear-user-story` copies verbatim into every filed story: that fenced text is the story's own
Definition of Done, not hidden prose.
"""

import copy
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
ENGINEERING_WORKFLOW = ROOT / "skills" / "engineering-workflow" / "SKILL.md"
USER_STORY = ROOT / "skills" / "linear-user-story" / "SKILL.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"

# AC1/AC3: the four sentences, each whole on its own line in both changed skill files.
RULE = (
    'Full-suite evidence is satisfied once per PR head, by the local `uv run --locked pytest -q` run or by that '
    'head\'s passing CI "Repository tests" step, never both.'
)
FALLBACK = (
    "Credit the CI step only when it ran on the current PR head or on a verified identical tree: record the head "
    "and either the local result or the CI run link with the tested SHA, and run the local suite when equivalence "
    "cannot be verified."
)
EXCEPTION = (
    "Both signals are required when the PR changes `.github/workflows/`, the pytest configuration "
    "(`pyproject.toml`'s pytest section, `pytest.ini`, a `conftest.py`), `uv.lock`, or any file under `tests/`; "
    "the dedup covers the `pytest -q` step only, so `ruff check .`, the leak scan and `skills-ref validate` stay "
    "required and the preflight `full_suite` setting is untouched."
)
PRESERVATION = (
    "Required GitHub checks, focused tests, the pre-PR preflight, and any story criterion requiring both signals "
    "are unchanged: no required check is added or removed, and this rewrites no acceptance criterion on any other "
    "story."
)
SENTENCES = (
    pytest.param(RULE, id="rule"),
    pytest.param(FALLBACK, id="fallback"),
    pytest.param(EXCEPTION, id="exception"),
    pytest.param(PRESERVATION, id="preservation"),
)
SKILL_FILES = (
    pytest.param(ENGINEERING_WORKFLOW, id="engineering-workflow"),
    pytest.param(USER_STORY, id="linear-user-story"),
)

STEP9_BULLET = "- All required checks are green."
DOD_BULLET = "- [ ] Unit/integration tests written & passing"

# AC2: the changed paths that put a PR inside its own exception, and the dedup's blast radius.
EXCEPTION_PREFIXES = (".github/workflows/", "tests/")
EXCEPTION_PATHS = ("uv.lock", "pytest.ini")
PYPROJECT = "pyproject.toml"
PYTEST_CONFIG_FILE = "conftest.py"
DEDUPED_STEP = "`pytest -q` step only"
KEPT_REQUIRED = ("`ruff check .`", "the leak scan", "`skills-ref validate`", "`full_suite`")

NUMBERED_ITEM = re.compile(r"^(\d+)\. ")


def text_of(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"\n## {heading}\n"
    count = text.count(marker)
    assert count == 1, f"the {heading!r} heading must appear once, found {count}"
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def active_lines(text: str) -> list[str]:
    """The lines a reader sees as Markdown: nothing inside a fenced block or an HTML comment."""
    lines: list[str] = []
    fenced = False
    in_comment = False
    for line in text.splitlines():
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if "<!--" in line:
            in_comment = "-->" not in line.split("<!--", 1)[1]
            line = line.split("<!--", 1)[0]
        lines.append(line)
    return lines


def rendered_items(text: str) -> list[str]:
    """Each top-level rendered list item, as the text a CommonMark reader sees."""
    items: list[str] = []
    depth = 0
    current: list[str] = []
    for token in MarkdownIt().parse(text):
        if token.type == "list_item_open":
            depth += 1
            if depth == 1:
                current = []
        elif token.type == "list_item_close":
            depth -= 1
            if depth == 0:
                items.append(" ".join(" ".join(current).split()))
        elif depth == 1 and token.type == "inline":
            current.append("".join(child.content for child in token.children or () if child.type != "html_inline"))
    return items


LIST_MARKER = re.compile(r"^(?:\d+\.|[-*+])\s+")
TASK_MARKER = re.compile(r"^\[[ x]\]\s*")


def plain(text: str) -> str:
    """Text with inline code markers dropped, so a rendered item is compared with the sentence it carries."""
    return TASK_MARKER.sub("", text.replace("`", ""))


def rendered_rule_in_item(text: str, first_line: str) -> bool:
    """True when exactly one rendered list item starts with first_line and states the whole rule."""
    lead = plain(LIST_MARKER.sub("", first_line))
    items = [item for item in (plain(item) for item in rendered_items(text)) if item.startswith(lead)]
    return len(items) == 1 and all(plain(sentence) in items[0] for sentence in (RULE, FALLBACK, EXCEPTION, PRESERVATION))


def numbered_item(text: str, number: int) -> list[str]:
    """A numbered list item and its indented continuation lines, as a reader sees them."""
    lines = active_lines(text)
    for index, line in enumerate(lines):
        match = NUMBERED_ITEM.match(line)
        if not match or match.group(1) != str(number):
            continue
        block = [line]
        for continuation in lines[index + 1 :]:
            if not continuation.startswith(" ") or not continuation.strip():
                break
            block.append(continuation)
        return block
    raise AssertionError(f"no active numbered item {number}")


def bullet_block(text: str, bullet: str) -> list[str]:
    """A bullet and its indented continuation lines, as a reader sees them."""
    lines = active_lines(text)
    assert bullet in lines, f"missing active bullet: {bullet}"
    index = lines.index(bullet)
    block = [bullet]
    for continuation in lines[index + 1 :]:
        if not continuation.startswith(" ") or not continuation.strip():
            break
        block.append(continuation)
    return block


def own_lines(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines()}


def fenced_template(text: str) -> str:
    """The story template under `## Template (the description)` that linear-user-story copies into a story."""
    section_text = section(text, "Template (the description)")
    opener = "\n```markdown\n"
    openers = section_text.count(opener)
    assert openers == 1, f"the story template section must hold one fenced template, found {openers}"
    body = section_text.split(opener, 1)[1]
    end = body.find("\n```\n")
    assert end != -1, "the story template fence is never closed"
    template = body[:end]
    assert DOD_BULLET in template, "the story template ends before its Definition of Done bullet"
    return template


def repository_tests_run(workflow_text: str) -> list[str]:
    workflow = yaml.safe_load(workflow_text)
    jobs = workflow.get("jobs") or {}
    assert "checks" in jobs, "the CI workflow no longer has a `checks` job"
    steps = jobs["checks"].get("steps") or []
    return [step.get("run") for step in steps if step.get("name") == "Repository tests"]


def expected_block(first_line: str, indent: str) -> list[str]:
    """The four sentences as the exact continuation lines of one named item, in order."""
    return [first_line, *(indent + sentence for sentence in (RULE, FALLBACK, EXCEPTION, PRESERVATION))]


STEP3_ITEM5 = "5. Run broader validation periodically and before the PR."
STEP5_ITEM1 = (
    "1. Run the complete applicable test suite, plus the repository's formatters, linters, type checks, "
    "static analysis and build."
)


def expected_blocks() -> dict[str, list[str]]:
    return {
        "step 3 item 5": expected_block(STEP3_ITEM5, "   "),
        "step 5 item 1": expected_block(STEP5_ITEM1, "   "),
        "step 9 bullet": expected_block(STEP9_BULLET, "  "),
        "dod bullet": expected_block(DOD_BULLET, "  "),
    }


def located_blocks(engineering: str, user_story: str) -> dict[str, list[str]]:
    """The block found at each location AC1 names, by the same locators the tests and the guard use."""
    return {
        "step 3 item 5": numbered_item(section(engineering, "3. TDD per slice"), 5),
        "step 5 item 1": numbered_item(section(engineering, "5. Prepare the PR"), 1),
        "step 9 bullet": bullet_block(section(engineering, "9. Merge readiness"), STEP9_BULLET),
        "dod bullet": bullet_block(fenced_template(user_story), DOD_BULLET),
    }


# ---- AC1/AC3: the four sentences, pinned whole on their own line in both skills -----------------


@pytest.mark.parametrize("sentence", SENTENCES)
@pytest.mark.parametrize("path", SKILL_FILES)
def test_each_sentence_is_whole_on_its_own_line(path: Path, sentence: str) -> None:
    skill = f"{path.parent.name}/{path.name}"
    assert sentence in own_lines(text_of(path)), f"{skill} lacks the sentence whole on its own line"


def test_rule_sits_in_step_3_item_5() -> None:
    located = located_blocks(text_of(ENGINEERING_WORKFLOW), text_of(USER_STORY))
    assert located["step 3 item 5"] == expected_blocks()["step 3 item 5"]


def test_rule_sits_in_step_5_item_1() -> None:
    located = located_blocks(text_of(ENGINEERING_WORKFLOW), text_of(USER_STORY))
    assert located["step 5 item 1"] == expected_blocks()["step 5 item 1"]


def test_rule_sits_in_the_step_9_required_checks_bullet() -> None:
    located = located_blocks(text_of(ENGINEERING_WORKFLOW), text_of(USER_STORY))
    assert located["step 9 bullet"] == expected_blocks()["step 9 bullet"]


def test_dod_bullet_states_the_whole_rule() -> None:
    located = located_blocks(text_of(ENGINEERING_WORKFLOW), text_of(USER_STORY))
    assert located["dod bullet"] == expected_blocks()["dod bullet"]


def test_the_rule_is_rendered_where_ac1_names_it() -> None:
    engineering = text_of(ENGINEERING_WORKFLOW)
    for first_line in (STEP3_ITEM5, STEP5_ITEM1, STEP9_BULLET):
        assert rendered_rule_in_item(engineering, first_line), (
            f"a CommonMark reader does not see the whole rule at {first_line!r}"
        )
    template = fenced_template(text_of(USER_STORY))
    assert rendered_rule_in_item(template, DOD_BULLET), (
        "a filed story's Definition of Done does not render the whole rule"
    )


# ---- AC3: the CI checks job still runs the locked suite ----------------------------------------


def test_checks_job_repository_tests_step_runs_the_locked_suite() -> None:
    assert repository_tests_run(text_of(CI)) == ["uv run --locked pytest -q"]


# ---- AC3: decision cases ---------------------------------------------------------------------


@dataclass(frozen=True)
class ChangedFile:
    """A repository-relative path the PR changes, with the TOML tables it edits when it is a pyproject.toml."""

    path: str
    toml_sections: frozenset[str] = frozenset()


def local_run_required(*, ci_step_passing: bool, ci_step_on_head: bool = False, ci_step_tree_verified: bool = False) -> bool:
    """AC1's fallback: a passing CI step stands in on the head or on a verified identical tree, never otherwise."""
    return not (ci_step_passing and (ci_step_on_head or ci_step_tree_verified))


def both_signals_required(changed: tuple[ChangedFile, ...]) -> bool:
    """AC2's exception: the dedup needs both signals once the PR touches the suite's own inputs."""
    for item in changed:
        name = item.path.rsplit("/", 1)[-1]
        if any(item.path.startswith(prefix) for prefix in EXCEPTION_PREFIXES):
            return True
        if name in EXCEPTION_PATHS or name == PYTEST_CONFIG_FILE:
            return True
        if name == PYPROJECT and any(
            section == "pytest" or section == "tool.pytest" or section.startswith("tool.pytest.")
            for section in item.toml_sections
        ):
            return True
    return False


def local_evidence_required(
    changed: tuple[ChangedFile, ...],
    *,
    ci_step_passing: bool,
    ci_step_on_head: bool = False,
    ci_step_tree_verified: bool = False,
) -> bool:
    """AC1 and AC2 together: the exception forces the local run even when the CI step earns credit."""
    return both_signals_required(changed) or local_run_required(
        ci_step_passing=ci_step_passing, ci_step_on_head=ci_step_on_head, ci_step_tree_verified=ci_step_tree_verified
    )


def test_unverified_equivalence_requires_the_local_run() -> None:
    assert local_run_required(ci_step_passing=False), "no CI step means the local run"
    assert local_run_required(ci_step_passing=True), "a passing step on an unverified tree means the local run"
    assert local_run_required(ci_step_passing=False, ci_step_on_head=True), "a failing step earns no credit"
    assert not local_run_required(ci_step_passing=True, ci_step_on_head=True), "a passing step on the head is the one signal"
    assert not local_run_required(ci_step_passing=True, ci_step_tree_verified=True), "a verified identical tree earns credit"
    assert "current PR head or on a verified identical tree" in FALLBACK
    assert "when equivalence cannot be verified" in FALLBACK
    assert "with the tested SHA" in FALLBACK


def test_both_signals_exception_decides_the_named_paths() -> None:
    for changed in (
        ChangedFile(".github/workflows/ci.yml"),
        ChangedFile("tests/test_one_green_signal.py"),
        ChangedFile("tests/conftest.py"),
        ChangedFile("conftest.py"),
        ChangedFile("uv.lock"),
        ChangedFile("pytest.ini"),
        ChangedFile(PYPROJECT, frozenset({"tool.pytest.ini_options"})),
        ChangedFile("service/" + PYPROJECT, frozenset({"tool.pytest.ini_options", "tool.ruff"})),
    ):
        assert both_signals_required((changed,)), f"{changed.path} must require both signals"
    for changed in (
        ChangedFile("skills/engineering-workflow/SKILL.md"),
        ChangedFile("docs/qa-evidence/SKL-387/README.md"),
        ChangedFile("tests_free/notes.md"),
        ChangedFile(PYPROJECT, frozenset({"tool.ruff"})),
        ChangedFile(PYPROJECT, frozenset({"tool.pytest_helper"})),
        ChangedFile("pyproject.toml.bak"),
        ChangedFile("pytest.ini.example"),
        ChangedFile("uv.lock.bak"),
    ):
        assert not both_signals_required((changed,)), f"{changed.path} stays outside the exception"


def test_combined_decision_keeps_a_suite_change_on_both_signals() -> None:
    skill_change = (ChangedFile("skills/engineering-workflow/SKILL.md"),)
    suite_change = (ChangedFile("tests/test_one_green_signal.py"),)
    passing_head = {"ci_step_passing": True, "ci_step_on_head": True}
    assert not local_evidence_required(skill_change, **passing_head), "the green CI step is the one signal for a skill change"
    assert local_evidence_required(suite_change, **passing_head), "the exception still requires the local run for a suite change"
    assert local_evidence_required(skill_change, ci_step_passing=False), "no CI step means the local run"


def test_exception_sentence_names_the_decided_paths_and_keeps_the_rest_required() -> None:
    for token in (*EXCEPTION_PREFIXES, *EXCEPTION_PATHS, PYPROJECT, PYTEST_CONFIG_FILE):
        assert token in EXCEPTION, f"the exception sentence does not name {token}"
    assert DEDUPED_STEP in EXCEPTION
    for kept in KEPT_REQUIRED:
        assert kept in EXCEPTION, f"the dedup no longer preserves {kept}"


def test_rule_and_preservation_say_once_per_head_and_nothing_else_changes() -> None:
    assert "satisfied once per PR head" in RULE
    assert "never both" in RULE
    assert "no required check is added or removed" in PRESERVATION
    assert "rewrites no acceptance criterion on any other story" in PRESERVATION


# ---- mutation tests --------------------------------------------------------------------------


def pin_fails(engineering: str, user_story: str, name: str, block: list[str]) -> bool:
    """True when the named location pin rejects this text, whether by a wrong block or a locator error."""
    try:
        return located_blocks(engineering, user_story)[name] != block
    except AssertionError:
        return True


def test_guard_kills_every_mutant() -> None:
    engineering = text_of(ENGINEERING_WORKFLOW)
    user_story = text_of(USER_STORY)
    expected = expected_blocks()
    assert located_blocks(engineering, user_story) == expected
    for name, block in expected.items():
        original = "\n".join(block)
        for sentence in (RULE, FALLBACK, EXCEPTION, PRESERVATION):
            broken = "\n".join(line for line in block if line.strip() != sentence)
            engineering_mutant = engineering.replace(original, broken, 1) if name != "dod bullet" else engineering
            user_story_mutant = user_story.replace(original, broken, 1) if name == "dod bullet" else user_story
            assert pin_fails(engineering_mutant, user_story_mutant, name, block), (
                f"the {name} pin accepted a mutant without {sentence[:40]!r}"
            )
    fenced = engineering.replace(
        "\n".join(expected["step 3 item 5"]), "```text\n" + "\n".join(expected["step 3 item 5"]) + "\n```", 1
    )
    assert pin_fails(fenced, user_story, "step 3 item 5", expected["step 3 item 5"]), "the pin accepted a fenced rule"
    commented = user_story.replace(
        "\n".join(expected["dod bullet"]), "<!--\n" + "\n".join(expected["dod bullet"]) + "\n-->", 1
    )
    assert pin_fails(engineering, commented, "dod bullet", expected["dod bullet"]), "the pin accepted a commented rule"
    duplicate_heading = user_story.replace(
        "\n## Template (the description)\n", "\n## Template (the description)\n\n## Template (the description)\n", 1
    )
    assert pin_fails(engineering, duplicate_heading, "dod bullet", expected["dod bullet"]), (
        "the pin accepted a duplicate template heading"
    )
    hidden_block = "\n".join(expected["step 3 item 5"])
    for opener, closer in (("```text", "```"), ("~~~text", "~~~"), ("<pre>", "</pre>")):
        hidden = engineering.replace(hidden_block, opener + "\n" + hidden_block + "\n" + closer, 1)
        assert not rendered_rule_in_item(hidden, STEP3_ITEM5), f"the rendered pin accepted a {opener!r} wrapper"
    workflow = yaml.safe_load(text_of(CI))
    mutants = []
    for mutant_run in ("uv run --locked pytest -x", "pytest -q", "uv run --locked pytest"):
        mutated = copy.deepcopy(workflow)
        for step in mutated["jobs"]["checks"]["steps"]:
            if step.get("name") == "Repository tests":
                step["run"] = mutant_run
        mutants.append((mutant_run, mutated))
    renamed = copy.deepcopy(workflow)
    for step in renamed["jobs"]["checks"]["steps"]:
        if step.get("name") == "Repository tests":
            step["name"] = "Project tests"
    mutants.append(("a renamed step", renamed))
    removed = copy.deepcopy(workflow)
    removed["jobs"]["checks"]["steps"] = [
        step for step in removed["jobs"]["checks"]["steps"] if step.get("name") != "Repository tests"
    ]
    mutants.append(("a removed step", removed))
    for label, mutated in mutants:
        assert repository_tests_run(yaml.safe_dump(mutated)) != ["uv run --locked pytest -q"], (
            f"the CI pin accepted {label!r}"
        )
