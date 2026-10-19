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
    assert "gh pr merge --match-head-commit" in text
    assert "stop and report the merge blocked instead of merging unguarded" in text


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


def test_engineering_workflow_step_10_requires_the_handshake() -> None:
    body = (SKILLS / "engineering-workflow" / "SKILL.md").read_text()
    section = body.split("## 10. Merge", 1)[1].split("## 11.", 1)[0]
    for phrase in (
        "If the brief assigns merge approval to a manager, follow [references/merge-approval.md](references/merge-approval.md) before any merge.",
        "stop and report the engagement blocked on the missing metadata; do not fall through to autonomous merge",
        "Record a `REQUEST`",
        "do not merge until an `APPROVE` for that request ID and the current full head SHA is recorded",
        "expected-head condition",
        "when it is `human`, tell the user the PR is approved and merge-ready and wait for that human to merge",
    ):
        assert phrase in section, phrase


def test_staff_engineer_brief_and_watcher_require_the_handshake() -> None:
    body = (SKILLS / "persona-staff-engineer" / "SKILL.md").read_text()
    brief = body.split("## 3. Delegate implementation", 1)[1].split("## 4.", 1)[0]
    watcher = body.split("### Merge-approval watcher", 1)[1].split("## 5.", 1)[0]
    for phrase in (
        "The merge-approval handshake: name `references/merge-approval.md`, name yourself as the manager, give the engagement's approvals-file path and the wake address the runtime needs",
        "record a `REQUEST` and deliver it through the wake capability before merging",
        "hand back blocked with the request ID, the PR, and the head SHA",
    ):
        assert phrase in brief, phrase
    for phrase in (
        "otherwise keep the engagement active and poll the file at least every five minutes until delegation ends",
        "The watcher stays active after a blocked handback as well",
        "Verify the live PR head SHA, the required CI state, and the review of record for that head.",
        "Append `APPROVE` or `BOUNCE` in the format in `references/merge-approval.md`, idempotently on request ID plus head SHA.",
    ):
        assert phrase in watcher, phrase


def test_shared_merge_rules_carry_the_delegated_carve_out() -> None:
    github = (ROOT / "shared" / "github.md").read_text()
    merging = github.split("## Merging", 1)[1].split("## Promotion", 1)[0]
    assert "does not merge until the matching `APPROVE` is recorded for the current head SHA" in merging
    assert "`profile.review.merge_owner` still decides who performs the merge" in merging
    code_review = (ROOT / "shared" / "code-review.md").read_text()
    owner = code_review.split("## Merge owner", 1)[1].split("## Handling findings", 1)[0]
    assert "does not merge on `agent` alone" in owner
    assert "When `profile.review.merge_owner` is `human`, the human still performs the merge" in owner
