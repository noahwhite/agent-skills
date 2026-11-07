"""Contract checks for the one-simple-command-with-literal-values rule (SKL-207)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITHUB = ROOT / "shared" / "github.md"
PHRASE = "one simple command with literal values"

GIT_C_BULLET = "- Prefer `git -C <path> ...` over `cd <path> && git ...`; compound commands can trigger permission prompts."

EXPECTED_SKILL_FILES = {
    "engineering-workflow",
    "persona-staff-devops",
    "persona-staff-engineer",
    "story-to-done",
}

EXPECTED_VENDORED = {
    "adversarial-review-pipeline",
    "cleanup",
    "engineering-workflow",
    "linear-bug",
    "linear-user-story",
    "persona-architect",
    "persona-platform-sre",
    "persona-release-manager",
    "persona-scrum-master",
    "persona-staff-devops",
    "persona-staff-engineer",
    "qa-verification",
    "story-to-done",
}

# Consumer-specific literals the added text must not carry (S3).
CONSUMER_LITERALS = ("GH_TOKEN", "GITHUB_", "GHCR", "noahwhite", "officina", "@", "OFF-")


def bullet_block(lines: list[str], index: int) -> list[str]:
    """The bullet starting at `index`, plus its indented continuation lines."""
    block = [lines[index]]
    for follow in lines[index + 1:]:
        if not follow.startswith("  "):
            break
        block.append(follow)
    return block


def base_bullet() -> list[str]:
    lines = GITHUB.read_text().splitlines()
    first = lines.index(GIT_C_BULLET)
    following = first + 1
    assert PHRASE in lines[following], "the rule bullet must directly follow the `git -C` bullet"
    return bullet_block(lines, following)


def test_base_bullet_directly_follows_git_c_bullet_with_phrase_on_one_line() -> None:
    block = base_bullet()
    assert block[0].startswith("- ")
    assert PHRASE in block[0]
    assert block[0].count(". ") == 0 and block[0].endswith("."), "first line is one sentence"


def test_base_bullet_names_the_three_forms_and_their_replacements() -> None:
    text = "\n".join(base_bullet())
    assert "W=<path>; git -C $W" in text
    assert "SHA=$(...) && gh api .../$SHA" in text
    assert 'VAR="$SECRET" cmd' in text
    assert "writes the literal path" in text
    assert "runs the inner command as its own call and uses its literal output in the next call" in text
    assert "its stored auth" in text and "never sets a credential per command" in text
    assert "permission checker cannot verify" in text and "manual prompt" in text


def test_base_bullet_covers_only_the_three_forms() -> None:
    text = "\n".join(base_bullet()).lower()
    for other in ("heredoc", "pipe", "cd <path>", "chain"):
        assert other not in text, other
    assert len(base_bullet()) == 4, "one lead sentence plus one line per form"


def test_base_bullet_names_no_consumer_literal() -> None:
    text = "\n".join(base_bullet())
    for literal in CONSUMER_LITERALS:
        assert literal not in text, literal


def skill_lines(name: str) -> list[str]:
    return (ROOT / "skills" / name / "SKILL.md").read_text().splitlines()


def test_phrase_appears_in_exactly_the_four_skill_files() -> None:
    found = {
        path.parent.name
        for path in (ROOT / "skills").glob("*/SKILL.md")
        if PHRASE in path.read_text()
    }
    assert found == EXPECTED_SKILL_FILES


def test_story_to_done_carries_the_phrase_once_per_list() -> None:
    assert (ROOT / "skills" / "story-to-done" / "SKILL.md").read_text().count(PHRASE) == 2


def phrase_lines(name: str) -> list[int]:
    return [i for i, line in enumerate(skill_lines(name)) if PHRASE in line]


def test_brief_bullets_sit_directly_after_the_secrets_bullet() -> None:
    expected = {
        "story-to-done": ("- The secrets rule (never write secrets to files or argv) and the attribution rule", "- The secrets rule and a \"Track your work\" paragraph"),
        "persona-staff-engineer": ("- The secrets rule (never write secrets to files or argv) and the attribution rule",),
        "persona-staff-devops": ("- The secrets rule (never write secrets to files or argv) and the attribution rule",),
    }
    for name, prefixes in expected.items():
        lines = skill_lines(name)
        hits = phrase_lines(name)
        assert len(hits) == len(prefixes), name
        for hit, prefix in zip(hits, prefixes):
            assert lines[hit - 1].startswith(prefix), f"{name}: line {hit + 1}"
            assert lines[hit].startswith("- "), name
            assert hit + 1 >= len(lines) or not lines[hit + 1].startswith("  "), f"{name}: bullet must be one physical line"


def test_brief_bullets_name_the_three_forms_without_consumer_literals() -> None:
    for name in ("story-to-done", "persona-staff-engineer", "persona-staff-devops"):
        lines = skill_lines(name)
        for hit in phrase_lines(name):
            line = lines[hit]
            assert "W=<path>; git -C $W" in line, name
            assert "$(...)" in line, name
            assert 'VAR="$SECRET"' in line, name
            for literal in CONSUMER_LITERALS:
                assert literal not in line, (name, literal)


def test_fix_stage_tells_the_orchestrator_to_pass_the_rule_to_the_fixer() -> None:
    lines = skill_lines("engineering-workflow")
    hits = phrase_lines("engineering-workflow")
    assert len(hits) == 1
    start = next(i for i, line in enumerate(lines) if line.startswith("3. **Fix.**"))
    end = next(i for i in range(start + 1, len(lines)) if not lines[i].startswith("   "))
    assert start < hits[0] < end, "the sentence belongs to the Fix stage"
    assert "fixer" in lines[hits[0]] and "prompt file" in lines[hits[0]]
    assert "references/github.md" in lines[hits[0]]


def test_vendored_copies_carry_the_base_bullet() -> None:
    found = {
        path.parent.parent.name
        for path in (ROOT / "skills").glob("*/references/github.md")
        if PHRASE in path.read_text()
    }
    assert found == EXPECTED_VENDORED


def test_phrase_is_not_in_other_files_of_the_shared_tree() -> None:
    hits = [p.name for p in (ROOT / "shared").glob("*.md") if PHRASE in p.read_text()]
    assert hits == ["github.md"]
    assert re.search(r"\bsimple command\b", GITHUB.read_text())


def test_accelerator_fixer_prompt_carries_the_rule() -> None:
    script = (ROOT / "skills" / "engineering-workflow" / "scripts" / "adversarial-review-loop.workflow.js").read_text()
    assert script.count(PHRASE) == 1, "the rule is defined once, as SHELL_RULE"
    definition = next(line for line in script.splitlines() if line.startswith("const SHELL_RULE = '"))
    assert PHRASE in definition
    assert "W=<path>; git -C $W" in definition and "$(...)" in definition and 'VAR="$SECRET"' in definition
    fix_prompt = script[script.index("function fixPrompt(") : script.index("function lensProblem(")]
    assert "${SHELL_RULE}" in fix_prompt
