"""SKL-206: the base git guidance and every delegation brief tell agents to commit with the configured identity."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GITHUB = ROOT / "shared" / "github.md"
SKILLS = ROOT / "skills"

# The stable phrase of the S1 text. It appears in the base rule and in every brief.
PHRASE = "with the git identity already configured"

# The one sentence every brief restates (S3). The fixer prose and the list bullets carry it verbatim.
COMMON = (
    "run every commit-creating git command with the git identity already configured "
    "and, when `profile.git.signed_commits` is true, the signing already configured; "
    "never pass `-c user.name`, `-c user.email`, `--author`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, "
    "never write `user.name` or `user.email` with `git config`, "
    "and when signing is on never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`; "
    "a missing identity, a failed signing check or a pushed commit whose "
    "`.commit.verification.verified` is false is a configuration fault, so stop, "
    "do not override per command or write git config, make no further commits, and report it to the user"
)
BULLET = "- The git rule: " + COMMON + "."
FIXER_PROSE = "Brief the fixer with the git rule: " + COMMON + "."

BRIEF_FILES = (
    "skills/story-to-done/SKILL.md",
    "skills/persona-staff-engineer/SKILL.md",
    "skills/persona-staff-devops/SKILL.md",
    "skills/engineering-workflow/SKILL.md",
)
SECRETS_BULLET_PREFIX = "- The secrets rule"


def commits_and_signing() -> list[str]:
    lines = GITHUB.read_text().splitlines()
    start = lines.index("## Commits and signing")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    return lines[start:end]


def split_blocks() -> tuple[list[str], list[str]]:
    """The 'When signed_commits is true:' block and the 'Always:' block of the section."""
    lines = commits_and_signing()
    signed = lines.index("When `profile.git.signed_commits` is true:")
    always = lines.index("Always:")
    assert signed < always
    return lines[signed + 1 : always], lines[always + 1 :]


# ---- S1: base rule --------------------------------------------------------------------------

ALWAYS_BULLET = (
    "- Run every commit-creating git command (`commit`, `commit --amend`, `merge`, `rebase`, `cherry-pick`, `revert`, `am`) "
    "with the git identity already configured, whether or not `profile.git.signed_commits` is true.",
    "  Never pass `-c user.name` or `-c user.email`, never pass `--author`, never set `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, "
    "and never write `user.name` or `user.email` with `git config` at any scope.",
    "  Ordinary commit options such as `-m` and `-F` stay permitted, and workflow files that create commits are out of scope.",
)
SIGNED_BULLET = (
    "- Never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign` to a commit-creating git command; "
    "rely on the configured signing."
)


def test_always_block_states_the_identity_rule_whether_or_not_signing_is_on():
    _, always = split_blocks()
    for line in ALWAYS_BULLET:
        assert always.count(line) == 1, line
    assert always.index(ALWAYS_BULLET[0]) + 1 == always.index(ALWAYS_BULLET[1])
    assert always.index(ALWAYS_BULLET[1]) + 1 == always.index(ALWAYS_BULLET[2])
    for command in ("commit", "commit --amend", "merge", "rebase", "cherry-pick", "revert", "am"):
        assert f"`{command}`" in ALWAYS_BULLET[0]


def test_signed_block_forbids_signing_overrides_and_relies_on_configured_signing():
    signed, always = split_blocks()
    assert signed.count(SIGNED_BULLET) == 1
    assert SIGNED_BULLET not in always


def test_the_stable_phrase_is_in_the_base_rule_once():
    assert GITHUB.read_text().count(PHRASE) == 1


# ---- S2: fault path -------------------------------------------------------------------------

def test_a_missing_identity_is_a_configuration_fault_under_always():
    _, always = split_blocks()
    assert always.count("- A missing configured identity is a configuration fault.") == 1


def test_the_fault_path_stops_and_reports():
    _, always = split_blocks()
    line = (
        "- On any configuration fault, stop: do not override per command, do not write git config, "
        "make no further commits, and report the fault to the user."
    )
    assert always.count(line) == 1


def test_a_non_zero_signing_check_is_a_configuration_fault_and_the_old_line_is_reworded():
    signed, _ = split_blocks()
    text = "\n".join(signed)
    assert "On a non-zero exit, stop and fix the configuration." not in text
    assert "  A non-zero exit is a configuration fault, handled as the Always list below says." in signed
    # The key-override prohibition is kept.
    assert "  Never commit with a per-commit key override, and never fall back to another key." in signed


def test_an_unverified_pushed_commit_is_a_configuration_fault():
    signed, _ = split_blocks()
    check = "- Check the result after push: `gh api repos/<owner>/<repo>/commits/<sha> --jq '.commit.verification'`."
    assert signed.count(check) == 1
    follow = signed[signed.index(check) + 1]
    assert follow == (
        "  A pushed commit whose `.commit.verification.verified` is false is a configuration fault, "
        "handled as the Always list below says."
    )


def test_no_line_tells_the_agent_to_fix_git_config_itself():
    text = "\n".join(commits_and_signing())
    assert not re.search(r"fix the configuration", text)


# ---- S3: briefs -----------------------------------------------------------------------------

def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_exactly_the_four_skills_carry_the_phrase():
    carriers = sorted(
        str(p.relative_to(ROOT)) for p in SKILLS.glob("*/SKILL.md") if PHRASE in p.read_text()
    )
    assert carriers == sorted(BRIEF_FILES)


def test_story_to_done_carries_it_once_per_list():
    lines = [line for line in read("skills/story-to-done/SKILL.md").splitlines() if PHRASE in line]
    assert len(lines) == 2


@pytest.mark.parametrize(
    "rel,intro",
    [
        ("skills/story-to-done/SKILL.md", "It must include:"),
        ("skills/story-to-done/SKILL.md", "Brief it as a QA agent, with only:"),
        ("skills/persona-staff-engineer/SKILL.md", "It must include:"),
        ("skills/persona-staff-devops/SKILL.md", "It must include:"),
    ],
)
def test_each_brief_list_gains_one_bullet_next_to_the_secrets_rule(rel, intro):
    lines = read(rel).splitlines()
    start = lines.index(intro)
    while not lines[start + 1].strip():
        start += 1
    end = start + 1
    while end < len(lines) and lines[end].strip():
        end += 1
    block = lines[start + 1 : end]
    assert block.count(BULLET) == 1
    secrets = [i for i, line in enumerate(block) if line.startswith(SECRETS_BULLET_PREFIX)]
    assert len(secrets) == 1
    assert abs(block.index(BULLET) - secrets[0]) == 1


def test_the_fixer_spawn_prose_carries_the_same_sentence_and_no_list_is_added():
    text = read("skills/engineering-workflow/SKILL.md")
    assert text.splitlines().count(FIXER_PROSE) == 1
    assert BULLET not in text
    assert "It must include:" not in text


def test_the_accelerator_fixer_prompt_carries_the_same_sentence():
    script = read("skills/engineering-workflow/scripts/adversarial-review-loop.workflow.js")
    rule = COMMON[0].upper() + COMMON[1:] + "."
    assert f"const GIT_RULE = '{rule}'" in script
    fix_prompt = script[script.index("function fixPrompt(") : script.index("function lensProblem(")]
    assert "${GIT_RULE}" in fix_prompt


# ---- S4: no consumer literal ----------------------------------------------------------------

LITERAL = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|SHA256:[A-Za-z0-9+/]{43}|ssh-(ed25519|rsa) AAAA"
)


def test_the_added_text_names_no_account_email_or_key():
    for added in (*ALWAYS_BULLET, SIGNED_BULLET, BULLET, FIXER_PROSE):
        assert not LITERAL.search(added), added


# ---- S5: vendored copies in step ------------------------------------------------------------

def test_exactly_the_thirteen_generated_copies_carry_the_base_rule():
    copies = sorted(p for p in SKILLS.glob("*/references/github.md") if PHRASE in p.read_text())
    assert len(copies) == 13
    assert all(copy.read_text().startswith("<!-- GENERATED from shared/github.md") for copy in copies)


def test_vendor_check_passes():
    result = subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
