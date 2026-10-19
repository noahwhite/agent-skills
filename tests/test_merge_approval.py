"""Contract checks for the delegated merge-approval handshake."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDSHAKE = ROOT / "shared" / "merge-approval.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())
SKILLS = ROOT / "skills"


def handshake() -> str:
    return HANDSHAKE.read_text()


def test_handshake_defines_the_protocol_once() -> None:
    assert HANDSHAKE.is_file()
    text = handshake()
    for phrase in (
        "REQUEST |",
        "APPROVE |",
        "BOUNCE |",
        "request ID",
        "base-only update",
        "re-request",
        "Wake capability",
        "expected-head condition",
        "profile.review.merge_owner",
    ):
        assert phrase in text, phrase


def test_handshake_preserves_human_merge_ownership() -> None:
    text = handshake()
    assert "does not change who performs the merge" in text
    assert "when it is `human`, the engineer reports the approved PR and waits for that human to merge" in text


def test_handshake_requires_expected_head_binding() -> None:
    text = handshake()
    assert "approved full head SHA as an expected-head condition" in text
    assert "re-read the head immediately before the merge" in text


def test_base_only_update_only_requires_a_new_request_when_the_head_changes() -> None:
    text = handshake()
    section = text.split("## Base-only update rule", 1)[1].split("## Re-request rule", 1)[0]
    assert "never performs a base update that changes the head SHA after an approval without re-requesting" in section
    assert "leaves the head SHA unchanged leaves the approval standing" in section


def test_handshake_requires_missing_metadata_to_block() -> None:
    text = handshake()
    section = text.split("## When it applies", 1)[1].split("## Approvals file", 1)[0]
    assert "the brief assigns merge approval to a manager" in section
    assert "If either is missing" in section
    assert "never falls through to the autonomous merge" in section


def test_both_skills_compose_and_link_the_handshake() -> None:
    for skill in ("engineering-workflow", "persona-staff-engineer"):
        assert "merge-approval" in MANIFEST["skills"][skill]
        body = (SKILLS / skill / "SKILL.md").read_text()
        assert "[references/merge-approval.md](references/merge-approval.md)" in body, skill


def test_every_skill_that_carries_a_normative_carve_out_ships_the_handshake() -> None:
    missing = []
    for skill_dir in sorted(SKILLS.iterdir()):
        refs = skill_dir / "references"
        if not refs.is_dir():
            continue
        carries_carve_out = (refs / "github.md").is_file() or (refs / "code-review.md").is_file()
        if carries_carve_out and not (refs / "merge-approval.md").is_file():
            missing.append(skill_dir.name)
    assert not missing, missing


def test_handshake_is_registered_in_the_shared_readme() -> None:
    assert "`merge-approval.md`" in (ROOT / "shared" / "README.md").read_text()


def test_runtime_map_has_the_wake_capability() -> None:
    text = (ROOT / "shared" / "runtimes.md").read_text()
    assert "Wake the manager (merge approval)" in text
    assert "SendMessage" in text


def test_dry_run_covers_request_approve_bounce_and_changed_head() -> None:
    text = handshake()
    lines = [line for line in text.splitlines() if re.match(r"^(REQUEST|APPROVE|BOUNCE) \|", line)]
    kinds = [line.split(" | ", 1)[0] for line in lines]
    assert "REQUEST" in kinds and "APPROVE" in kinds and "BOUNCE" in kinds
    heads = {line.split(" | ")[3] for line in lines if line.startswith("REQUEST |")}
    assert len(heads) == 2, heads
