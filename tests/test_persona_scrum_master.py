"""Contract checks for the persona-scrum-master skill and its profile keys."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "persona-scrum-master" / "SKILL.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
MANIFEST = json.loads((ROOT / "skills.json").read_text())

REQUIRED_PHRASES = [
    "sprint goal",
    "cycle description",
    "profile.tracker.velocity_window_cycles",
    "profile.tracker.standup_aging_days",
    "report-only",
    "persona-product-owner",
    "DoR",
    "DoD",
    "profile.tracker.states.ready",
    "blockers",
]


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_manifest_registers_skill() -> None:
    assert MANIFEST["skills"]["persona-scrum-master"] == [
        "linear",
        "todo-tracking",
        "github",
    ]


def test_schema_has_velocity_window_cycles() -> None:
    prop = SCHEMA["properties"]["tracker"]["properties"]["velocity_window_cycles"]
    assert prop["type"] == "integer"
    assert prop["minimum"] == 1
    assert prop["default"] == 3


def test_schema_has_standup_aging_days() -> None:
    prop = SCHEMA["properties"]["tracker"]["properties"]["standup_aging_days"]
    assert prop["type"] == "integer"
    assert prop["minimum"] == 1
    assert prop["default"] == 3


def test_example_sets_new_tracker_keys() -> None:
    tracker = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())["tracker"]
    assert tracker["velocity_window_cycles"] == 3
    assert tracker["standup_aging_days"] == 3


def test_todo_tracking_has_seed_entry() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "persona-scrum-master:" in text


def test_readme_lists_skill() -> None:
    text = (ROOT / "README.md").read_text()
    assert "skills/persona-scrum-master/SKILL.md" in text


def test_skill_links_to_required_references() -> None:
    text = SKILL.read_text()
    for name in ("profile", "todo-tracking", "linear", "github", "runtimes"):
        assert f"references/{name}.md" in text, name


def test_skill_contains_contract_phrases() -> None:
    text = SKILL.read_text()
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    assert not missing, f"missing phrases: {missing}"
