"""Contract checks for the persona-architect skill, its template, and its profile keys."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "persona-architect" / "SKILL.md"
TEMPLATE = ROOT / "skills" / "persona-architect" / "assets" / "decision-record.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
MANIFEST = json.loads((ROOT / "skills.json").read_text())


def test_schema_has_decisions_dir() -> None:
    decisions = SCHEMA["properties"]["decisions"]
    assert decisions["type"] == "object"
    assert decisions["additionalProperties"] is False
    assert decisions["required"] == ["dir"]
    assert decisions["properties"]["dir"]["type"] == "string"


def test_example_sets_decisions_dir() -> None:
    profile = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
    assert profile["decisions"]["dir"] == "docs/decisions"


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_template_file_exists() -> None:
    assert TEMPLATE.is_file(), f"missing {TEMPLATE.relative_to(ROOT)}"


def test_template_has_required_fields() -> None:
    text = TEMPLATE.read_text()
    for field in ("Status", "Context", "Options considered", "Decision", "Consequences", "Supersedes"):
        assert field in text, f"template missing: {field}"
    for status in ("accepted", "superseded"):
        assert status in text, f"template missing status: {status}"


REQUIRED_PHRASES = [
    "profile.decisions.dir",
    "stop and ask",
    "writes no record outside",
    "assets/decision-record.md",
    "options considered",
    "consequences",
    "accepted",
    "superseded",
    "supersedes",
    "superseded by <new record filename>",
    "predecessor",
    "both files",
    "never delete",
    "both links in place",
    "Go/No-Go",
    "warrants a design decision",
    "link it from the spike issue",
    "persona-product-owner",
    "owns closure",
    "review of record",
    "references/code-review.md",
    "current head",
    "never commits a record directly to the integration branch",
    "delivering story's or spike's PR",
    "umbrella container",
    "linear-epic",
    "deliverable of its story or spike",
    "references/engineering-practice.md",
    "applicable existing records",
]


def test_skill_links_to_required_references() -> None:
    text = SKILL.read_text()
    for name in (
        "profile",
        "todo-tracking",
        "linear",
        "github",
        "code-review",
        "engineering-practice",
        "runtimes",
    ):
        assert f"references/{name}.md" in text, name
    assert "assets/decision-record.md" in text


def test_skill_contains_contract_phrases() -> None:
    text = SKILL.read_text()
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    assert not missing, f"missing phrases: {missing}"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_writing_section_requires_the_profile_directory() -> None:
    body = section(SKILL.read_text(), "Writing a decision record").lower()
    for phrase in (
        "profile.decisions.dir",
        "stop and ask",
        "writes no record outside",
        "assets/decision-record.md",
        "context",
        "options considered",
        "decision",
        "consequences",
        "status",
        "accepted",
    ):
        assert phrase in body, f"writing missing: {phrase}"


def test_superseding_section_keeps_both_records_and_links() -> None:
    body = section(SKILL.read_text(), "Superseding").lower()
    for phrase in (
        "supersedes",
        "superseded by <new record filename>",
        "predecessor exists",
        "both files",
        "never delete",
        "both links in place",
    ):
        assert phrase in body, f"superseding missing: {phrase}"


def test_spike_handoff_keeps_closure_with_the_product_owner() -> None:
    body = section(SKILL.read_text(), "Spike outcome to decision").lower()
    for phrase in (
        "go/no-go",
        "warrants a design decision",
        "link it from the spike issue",
        "persona-product-owner",
        "owns closure",
        "review of record",
        "merged",
        "no-go",
        "does not edit `linear-spike`",
    ):
        assert phrase in body, f"spike hand-off missing: {phrase}"


def test_records_ship_through_a_pr_with_the_review_of_record() -> None:
    body = section(SKILL.read_text(), "Decision records ship through a PR").lower()
    for phrase in (
        "delivering story's or spike's pr",
        "references/code-review.md",
        "current head",
        "never commits a record directly to the integration branch",
    ):
        assert phrase in body, f"pr rule missing: {phrase}"


def test_epic_boundary_is_cited_not_restated() -> None:
    body = section(SKILL.read_text(), "Epic boundary").lower()
    for phrase in ("umbrella container", "linear-epic", "deliverable of its story or spike"):
        assert phrase in body, f"epic boundary missing: {phrase}"


def test_engineering_practice_rule_is_cited() -> None:
    body = section(SKILL.read_text(), "Before deciding").lower()
    for phrase in ("references/engineering-practice.md", "applicable existing records", "cite"):
        assert phrase in body, f"engineering-practice citation missing: {phrase}"


def test_manifest_registers_skill() -> None:
    assert MANIFEST["skills"]["persona-architect"] == [
        "linear",
        "todo-tracking",
        "github",
        "code-review",
        "engineering-practice",
    ]


def test_todo_tracking_has_seed_entry() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "persona-architect:" in text


def test_readme_lists_skill() -> None:
    text = (ROOT / "README.md").read_text()
    assert "skills/persona-architect/SKILL.md" in text
