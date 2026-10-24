"""Contract checks for the cleanup skill.

The skill is the last step of a story's life: it removes the artefacts a session created for a
story and moves the evidence it hosted onto the story. These checks pin the registration the
repository contract-tests for every skill, and then the behaviour the acceptance criteria name.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "cleanup" / "SKILL.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())


def text() -> str:
    return SKILL.read_text()


def section(body: str, heading: str) -> str:
    """One `## ` section, without its heading or the next heading."""
    match = re.search(rf"^## {re.escape(heading)}\s*$", body, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = body[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_manifest_registers_skill_with_its_capabilities() -> None:
    assert {"todo-tracking", "linear", "github"} <= set(MANIFEST["skills"]["cleanup"])


def test_vendored_bundle_carries_every_linked_capability() -> None:
    for name in ("profile", "runtimes", "todo-tracking", "linear", "github"):
        assert (SKILL.parent / "references" / f"{name}.md").is_file(), name


def test_readme_lists_skill_in_table() -> None:
    row = "| [`cleanup`](skills/cleanup/SKILL.md) |"
    in_fence = False
    in_skills = False
    found = False
    for line in (ROOT / "README.md").read_text().splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if line.startswith("## "):
            in_skills = line.strip() == "## Skills"
            continue
        if in_skills and not in_fence and line.startswith(row):
            found = True
    assert found, "missing cleanup row from the README Skills table"


def test_todo_tracking_has_seed_entry() -> None:
    assert "- **cleanup:**" in (ROOT / "shared" / "todo-tracking.md").read_text()


def test_invocation_takes_one_or_more_story_keys_and_pins_the_usage_line() -> None:
    body = section(text(), "Invocation")
    assert [line.strip() for line in body.splitlines() if line.strip() == "/cleanup <story-key> [<story-key> ...]"]
    assert "prints `usage: /cleanup <story-key> [<story-key> ...]` and stops without touching anything" in body
    for phrase in (
        "never infers a story from ambient context",
        "from the current branch",
        "from a worktree path",
    ):
        assert phrase in body, phrase


def test_every_key_is_resolved_against_the_tracker_before_anything_is_touched() -> None:
    body = section(text(), "1. Resolve every key against the tracker")
    for phrase in (
        "before anything is touched",
        "Resolve each key with `linear issue view <story-key>`",
        "`profile.tracker.team_key`",
        "Report an unresolved key as `unresolved` and skip it",
        "The other keys still run",
        "Never invent, guess, or shorten a key",
    ):
        assert phrase in body, phrase
