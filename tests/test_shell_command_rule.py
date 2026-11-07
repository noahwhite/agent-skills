"""SKL-207: the base shell guidance and every delegation brief tell agents to run each shell step as one simple command with literal values."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITHUB = ROOT / "shared" / "github.md"
SKILLS = ROOT / "skills"
SCRIPT = SKILLS / "engineering-workflow" / "scripts" / "adversarial-review-loop.workflow.js"
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

# The three forbidden forms and the prohibitive marker each statement must carry.
# The brief bullets and the accelerator sentence state all of these in one line.
PROHIBITIONS = (
    "never assign a variable and use it in the same command",
    "never feed a `$(...)` result into a later argument of the same command",
    'never prefix a command with an inline `VAR="$SECRET"` assignment',
    "never set a credential per command",
)

# Shapes of consumer identity the added text must not carry (S3). The names themselves live only in
# the private denylist that CI's leak scan loads, never in this tracked file.
LITERAL = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}"
    r"|SHA256:[A-Za-z0-9+/]{43}"
    r"|ssh-(ed25519|rsa) AAAA"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}"
)

BRIEF_LISTS = (
    ("story-to-done", "It must include:"),
    ("story-to-done", "Brief it as a QA agent, with only:"),
    ("persona-staff-engineer", "It must include:"),
    ("persona-staff-devops", "It must include:"),
)
SECRETS_BULLET_PREFIX = "- The secrets rule"
BRIEF_PREFIX = "- The shell rule: "


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def skill_lines(name: str) -> list[str]:
    return (SKILLS / name / "SKILL.md").read_text().splitlines()


def list_block(name: str, intro: str) -> list[str]:
    """The bullet list that follows `intro` in a skill: lines up to the next blank line."""
    lines = skill_lines(name)
    assert lines.count(intro) >= 1, f"{name}: no list introduced by {intro!r}"
    start = lines.index(intro)
    while not lines[start + 1].strip():
        start += 1
    end = start + 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return lines[start + 1 : end]


def base_bullet() -> list[str]:
    lines = GITHUB.read_text().splitlines()
    assert GIT_C_BULLET in lines, "the `git -C` bullet moved: update the anchor"
    following = lines.index(GIT_C_BULLET) + 1
    assert PHRASE in lines[following], "the rule bullet must directly follow the `git -C` bullet"
    block = [lines[following]]
    for follow in lines[following + 1 :]:
        if not follow.startswith("  "):
            break
        block.append(follow)
    return block


# ---- S1: base rule ---------------------------------------------------------------------------


def test_base_bullet_directly_follows_git_c_bullet_with_phrase_on_one_line() -> None:
    block = base_bullet()
    assert block[0].startswith("- ")
    assert PHRASE in block[0]
    assert block[0].count(". ") == 0 and block[0].endswith("."), "first line is one sentence"


def test_base_bullet_prohibits_the_three_forms_and_gives_their_replacements() -> None:
    block = base_bullet()
    assert len(block) == 4, "one lead sentence plus one line per form"
    forms = (
        ("W=<path>; git -C $W", "writes the literal path"),
        ("SHA=$(...) && gh api .../$SHA", "runs the inner command as its own call and uses its literal output in the next call"),
        ('VAR="$SECRET" cmd', "never sets a credential per command"),
    )
    for line, (example, replacement) in zip(block[1:], forms):
        assert line.startswith("  It never "), line
        assert example in line and replacement in line, line
    assert "its stored auth" in block[3]
    assert "permission checker cannot verify" in block[0] and "manual prompt" in block[0]


def test_base_bullet_covers_only_the_three_forms() -> None:
    text = "\n".join(base_bullet()).lower()
    for other in ("heredoc", "pipe", "cd <path>"):
        assert other not in text, other


def test_base_bullet_names_no_consumer_identity() -> None:
    assert not LITERAL.search("\n".join(base_bullet()))


# ---- S2: the briefs carry it -------------------------------------------------------------------


def test_phrase_appears_in_exactly_the_four_skill_files_and_twice_in_story_to_done() -> None:
    found = {path.parent.name for path in SKILLS.glob("*/SKILL.md") if PHRASE in path.read_text()}
    assert found == EXPECTED_SKILL_FILES
    assert (SKILLS / "story-to-done" / "SKILL.md").read_text().count(PHRASE) == 2


def shell_bullets(block: list[str]) -> list[str]:
    return [line for line in block if line.startswith(BRIEF_PREFIX)]


def test_each_brief_list_gains_one_shell_bullet_directly_after_its_secrets_bullet() -> None:
    for name, intro in BRIEF_LISTS:
        block = list_block(name, intro)
        bullets = shell_bullets(block)
        assert len(bullets) == 1, (name, intro)
        bullet = bullets[0]
        position = block.index(bullet)
        assert block[position - 1].startswith(SECRETS_BULLET_PREFIX), (name, intro)
        assert PHRASE in bullet and bullet.endswith("."), (name, intro)
        assert not LITERAL.search(bullet), (name, intro)
        for prohibition in PROHIBITIONS:
            assert prohibition in bullet, (name, intro, prohibition)


def test_fix_stage_tells_the_orchestrator_to_pass_the_rule_to_the_fixer() -> None:
    lines = skill_lines("engineering-workflow")
    hits = [i for i, line in enumerate(lines) if PHRASE in line]
    assert len(hits) == 1
    starts = [i for i, line in enumerate(lines) if line.startswith("3. **Fix.**")]
    assert len(starts) == 1
    start = starts[0]
    end = next(i for i in range(start + 1, len(lines)) if not lines[i].startswith("   "))
    assert start < hits[0] < end, "the sentence belongs to the Fix stage"
    sentence = lines[hits[0]]
    assert "fixer" in sentence and "prompt file" in sentence and "references/github.md" in sentence


# ---- S4: vendored copies and the accelerator ------------------------------------------------------


def test_vendored_copies_carry_the_base_bullet() -> None:
    found = {
        path.parent.parent.name for path in SKILLS.glob("*/references/github.md") if PHRASE in path.read_text()
    }
    assert found == EXPECTED_VENDORED


def test_phrase_is_in_no_other_shared_file() -> None:
    hits = [str(p.relative_to(ROOT)) for p in (ROOT / "shared").rglob("*.md") if PHRASE in p.read_text()]
    assert hits == ["shared/github.md"]


def accelerator_rule() -> str:
    script = SCRIPT.read_text()
    assert script.count(PHRASE) == 1, "the rule is defined once, as SHELL_RULE"
    definitions = [line for line in script.splitlines() if line.startswith("const SHELL_RULE = '")]
    assert len(definitions) == 1
    return definitions[0][len("const SHELL_RULE = '") : -1].replace("\\'", "'")


def test_accelerator_fixer_prompt_carries_the_rule() -> None:
    rule = accelerator_rule()
    for prohibition in PROHIBITIONS:
        assert prohibition in rule, prohibition
    script = SCRIPT.read_text()
    assert script.count("function fixPrompt(") == 1 and script.count("function lensProblem(") == 1
    fix_prompt = script[script.index("function fixPrompt(") : script.index("function lensProblem(")]
    assert fix_prompt.count("${SHELL_RULE}") == 1
    assert not re.search(r"^\s*return\b", fix_prompt.split("return `")[0], re.MULTILINE), "no early return before the prompt"


def test_accelerator_sentence_is_the_brief_sentence() -> None:
    """The accelerator restates the briefs' sentence verbatim, so the two cannot drift apart."""
    rule = accelerator_rule()
    for name, intro in BRIEF_LISTS:
        bullet = shell_bullets(list_block(name, intro))[0]
        assert bullet[len(BRIEF_PREFIX) :] == rule[0].lower() + rule[1:], (name, intro)
