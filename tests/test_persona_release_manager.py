"""Contract checks for the persona-release-manager skill."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "persona-release-manager" / "SKILL.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_manifest_registers_skill() -> None:
    required = {"github", "linear", "code-review", "todo-tracking"}
    assert required <= set(MANIFEST["skills"]["persona-release-manager"])


def test_todo_tracking_has_seed_entry() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "- **persona-release-manager:**" in text


def test_readme_lists_skill_in_table() -> None:
    text = (ROOT / "README.md").read_text()
    row = "| [`persona-release-manager`](skills/persona-release-manager/SKILL.md) |"
    assert row in text


def test_skill_links_to_required_references() -> None:
    text = SKILL.read_text()
    for name in ("profile", "todo-tracking", "github", "linear", "code-review", "runtimes"):
        assert f"](references/{name}.md)" in text, name


def test_persona_boundary_declares_each_owner() -> None:
    body = section(SKILL.read_text(), "Persona boundary").lower()
    for phrase in (
        "engineering-workflow",
        "ends at the integration environment",
        "persona-platform-sre",
        "executes deploy and rollback mechanics",
        "qa-verification",
        "owns post-deploy evidence",
        "persona-product-owner",
        "owns status transitions and closure",
        "release orchestration",
        "readiness",
        "the promotion pr",
        "production verification coordination",
        "hand-offs",
        "does not execute deploys or rollback",
    ):
        assert phrase in body, f"boundary missing: {phrase}"


def test_readiness_section_covers_each_promotion_mode() -> None:
    body = section(SKILL.read_text(), "Release readiness").lower()
    for phrase in (
        "profile.git.promotion",
        "enumerates the issues included in the promotion",
        "pre-production verification evidence",
        "last environment in `profile.environments` whose `production` is not true",
        "integration branch is the release branch",
        "each story's own deploy verification",
        "missing evidence stops the promotion and names the issue",
        "promotion head",
        "re-check",
        "stale",
    ):
        assert phrase in body, f"readiness missing: {phrase}"


def test_promotion_section_cites_and_does_not_redefine() -> None:
    body = section(SKILL.read_text(), "Promotion").lower()
    for phrase in (
        "follows `profile.git.promotion` exactly",
        "references/github.md",
        "promotion",
        "does not redefine",
        "none",
        "whole-branch",
        "per-story",
        "single story's change",
        "never open a promotion pr that carries another story",
        "three-dot diff",
        "no back-merges",
    ):
        assert phrase in body, f"promotion missing: {phrase}"


def test_review_section_covers_the_cumulative_diff_and_ownership() -> None:
    body = section(SKILL.read_text(), "Promotion review").lower()
    for phrase in (
        "review of record",
        "whole cumulative diff",
        "current head",
        "references/code-review.md",
        "owning story",
        "integration branch",
        "references/github.md",
        "promotion",
        "fresh pre-production verification",
        "review-of-record comment",
    ):
        assert phrase in body, f"review missing: {phrase}"


def test_production_verification_section_covers_evidence_and_failure() -> None:
    body = section(SKILL.read_text(), "Production verification").lower()
    for phrase in (
        "post-deploy evidence",
        "qa-verification",
        "recorded against it",
        "reopens the owning story",
        "references/linear.md",
        "no existing",
        "criterion covers the failure",
        "epic",
        "rollback",
        "persona-platform-sre",
        "each production environment it reaches",
        "every story awaiting closure",
        "evidence and status",
    ):
        assert phrase in body, f"production verification missing: {phrase}"


def test_handoffs_name_every_owning_skill() -> None:
    body = section(SKILL.read_text(), "Hand-offs").lower()
    for phrase in (
        "engineering-workflow",
        "persona-platform-sre",
        "qa-verification",
        "persona-product-owner",
        "deploy",
        "rollback",
        "post-deploy evidence",
        "status",
        "never executes either",
        "merge result",
        "deploy or rollback execution result",
    ):
        assert phrase in body, f"hand-offs missing: {phrase}"
