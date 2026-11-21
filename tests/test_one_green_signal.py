"""SKL-387: the local suite run or the CI checks job is one green signal per PR head.

The rule lives in `skills/engineering-workflow/SKILL.md` (step 3 item 5, step 5 item 1 and the
step 9 "All required checks are green" bullet) and in the Definition of Done bullet
"Unit/integration tests written & passing" of `skills/linear-user-story/SKILL.md`.

The Definition of Done bullet is pinned where it lives, inside the fenced template that
`linear-user-story` copies verbatim into every filed story: that fenced text is the story's own
Definition of Done, not hidden prose.
"""

import re
from pathlib import Path

import pytest
import yaml

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

STEP3_ITEM5 = "5. Run broader validation periodically and before the PR."
STEP5_ITEM1 = (
    "1. Run the complete applicable test suite, plus the repository's formatters, linters, type checks, "
    "static analysis and build."
)
STEP9_BULLET = "- All required checks are green."
DOD_BULLET = "- [ ] Unit/integration tests written & passing"

# AC2: the changed paths that put a PR inside its own exception, and the dedup's blast radius.
EXCEPTION_PATHS = (".github/workflows/", "pyproject.toml", "pytest.ini", "uv.lock", "tests/")
PYTEST_CONFIG_FILE = "conftest.py"
DEDUPED_STEP = "`pytest -q` step only"
KEPT_REQUIRED = ("`ruff check .`", "the leak scan", "`skills-ref validate`", "`full_suite`")

NUMBERED_ITEM = re.compile(r"^(\d+)\. ")


def text_of(path: Path) -> str:
    return path.read_text()


def section(text: str, heading: str) -> str:
    marker = f"\n## {heading}\n"
    assert marker in text, f"missing section: {heading}"
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def numbered_item(text: str, number: int) -> list[str]:
    """A numbered list item and its indented continuation lines, as written."""
    lines = text.splitlines()
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
    raise AssertionError(f"no numbered item {number}")


def bullet_block(text: str, bullet: str) -> list[str]:
    """A bullet and its indented continuation lines, as written."""
    lines = text.splitlines()
    assert bullet in lines, f"missing bullet: {bullet}"
    index = lines.index(bullet)
    block = [bullet]
    for continuation in lines[index + 1 :]:
        if not continuation.startswith(" ") or not continuation.strip():
            break
        block.append(continuation)
    return block


def own_lines(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines()}


def repository_tests_run(workflow_text: str) -> list[str]:
    workflow = yaml.safe_load(workflow_text)
    return [
        step.get("run")
        for step in workflow["jobs"]["checks"]["steps"]
        if step.get("name") == "Repository tests"
    ]


# ---- AC1/AC3: the four sentences, pinned whole on their own line in both skills -----------------


@pytest.mark.parametrize("sentence", SENTENCES)
@pytest.mark.parametrize("path", SKILL_FILES)
def test_each_sentence_is_whole_on_its_own_line(path: Path, sentence: str) -> None:
    assert sentence in own_lines(text_of(path)), f"{path.name} lacks the sentence whole on its own line"


def test_rule_sits_in_step_3_item_5() -> None:
    block = numbered_item(section(text_of(ENGINEERING_WORKFLOW), "3. TDD per slice"), 5)
    assert RULE in own_lines("\n".join(block))


def test_rule_sits_in_step_5_item_1() -> None:
    block = numbered_item(section(text_of(ENGINEERING_WORKFLOW), "5. Prepare the PR"), 1)
    assert RULE in own_lines("\n".join(block))


def test_rule_sits_in_the_step_9_required_checks_bullet() -> None:
    block = bullet_block(section(text_of(ENGINEERING_WORKFLOW), "9. Merge readiness"), STEP9_BULLET)
    assert RULE in own_lines("\n".join(block))


def test_dod_bullet_states_the_rule() -> None:
    block = bullet_block(text_of(USER_STORY), DOD_BULLET)
    assert RULE in own_lines("\n".join(block))


# ---- AC3: the CI checks job still runs the locked suite ----------------------------------------


def test_checks_job_repository_tests_step_runs_the_locked_suite() -> None:
    assert repository_tests_run(text_of(CI)) == ["uv run --locked pytest -q"]


# ---- AC3: decision cases ---------------------------------------------------------------------


def local_run_required(ci_step_on_head: bool, ci_step_passing: bool) -> bool:
    """AC1's fallback: CI stands in only when its step passed on the head or a verified identical tree."""
    return not (ci_step_on_head and ci_step_passing)


def both_signals_required(changed_paths: list[str]) -> bool:
    """AC2's exception: the dedup needs both signals once the PR touches the suite's own inputs."""
    for path in changed_paths:
        if path == PYTEST_CONFIG_FILE or path.endswith("/" + PYTEST_CONFIG_FILE):
            return True
        if any(path.startswith(prefix) for prefix in EXCEPTION_PATHS):
            return True
    return False


def test_unverified_equivalence_requires_the_local_run() -> None:
    assert local_run_required(ci_step_on_head=False, ci_step_passing=False), "no CI step means the local run"
    assert local_run_required(ci_step_on_head=False, ci_step_passing=True), "a step off the head earns no credit"
    assert local_run_required(ci_step_on_head=True, ci_step_passing=False), "a failing step earns no credit"
    assert not local_run_required(ci_step_on_head=True, ci_step_passing=True), "a passing step on the head is the one signal"
    assert "current PR head or on a verified identical tree" in FALLBACK
    assert "when equivalence cannot be verified" in FALLBACK
    assert "with the tested SHA" in FALLBACK


def test_both_signals_exception_decides_the_named_paths() -> None:
    for path in (
        ".github/workflows/ci.yml",
        "tests/test_one_green_signal.py",
        "tests/conftest.py",
        "conftest.py",
        "uv.lock",
        "pyproject.toml",
        "pytest.ini",
    ):
        assert both_signals_required([path]), f"{path} must require both signals"
    for path in ("skills/engineering-workflow/SKILL.md", "docs/qa-evidence/SKL-387/README.md", "tests_free/notes.md"):
        assert not both_signals_required([path]), f"{path} stays outside the exception"


def test_exception_sentence_names_the_decided_paths_and_keeps_the_rest_required() -> None:
    for token in (*EXCEPTION_PATHS, PYTEST_CONFIG_FILE):
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


def test_guard_kills_every_mutant() -> None:
    survivors = []
    for path in (ENGINEERING_WORKFLOW, USER_STORY):
        text = text_of(path)
        for sentence in (RULE, FALLBACK, EXCEPTION, PRESERVATION):
            mutant = text.replace(sentence, "")
            if mutant == text or sentence in own_lines(mutant):
                survivors.append(f"{path.name}: sentence still present after deletion")
    for original, mutant in (
        ("run: uv run --locked pytest -q", "run: uv run --locked pytest -x"),
        ("run: uv run --locked pytest -q", "run: pytest -q"),
    ):
        mutated = text_of(CI).replace(original, mutant, 1)
        assert repository_tests_run(mutated) != ["uv run --locked pytest -q"], f"the CI pin accepted {mutant!r}"
    assert not survivors, survivors
