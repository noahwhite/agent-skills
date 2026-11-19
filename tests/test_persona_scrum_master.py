"""Contract checks for the persona-scrum-master skill and its profile keys."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "persona-scrum-master" / "SKILL.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())

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
    "unpointed count",
    "mean completed points",
    "state history",
    "last update",
    "next action",
    "exception",
    "every unmet box",
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


def test_report_only_boundary_overrides_capability_instructions() -> None:
    text = SKILL.read_text()
    assert re.search(r"report-only boundary\s+always\s+overrides", text, re.I)


def test_gate_covers_both_checklists_at_both_checkpoints() -> None:
    text = SKILL.read_text()
    assert "At sprint planning" in text
    assert "At close" in text
    assert "each story or epic" in text
    assert text.count("both the DoR and the DoD") >= 2


def test_shared_linear_documents_cycle_write_and_completed_points() -> None:
    text = (ROOT / "shared" / "linear.md").read_text()
    assert "cycle field" in text
    assert "completed-cycle points" in text


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_sprint_review_section_covers_done_issues_and_evidence() -> None:
    body = section(SKILL.read_text(), "Sprint review").lower()
    for phrase in (
        "profile.tracker.states.done",
        "cycle under review",
        "cycle listing",
        "merged pr",
        "profile.qa.evidence_dir",
        "accept evidence attached",
        "linked by issue key",
        "post the review report",
        "say so",
        "not as shipped",
    ):
        assert phrase in body, f"sprint review missing: {phrase}"


def test_retro_section_files_only_action_items() -> None:
    body = section(SKILL.read_text(), "Retro").lower()
    for phrase in (
        "went-well",
        "did-not-go-well",
        "action item",
        "linear-",
        "duplicate search",
        "linear-user-story",
        "linear-bug",
        "linear-spike",
        "linear-investigation",
        "tracker's issue-create",
        "report it to `persona-product-owner`",
        "dated record",
        "owner in the body",
        "profile.tracker.assignee",
        "profile.tracker.labels.improvement",
        "no issue for a went-well or a did-not-go-well",
    ):
        assert phrase in body, f"retro missing: {phrase}"


def test_retro_proposes_checklist_items_from_repeated_misses() -> None:
    body = section(SKILL.read_text(), "Retro")
    bullets = [b for b in body.split("\n- ") if b.startswith("Propose review checklist items from repeated misses:")]
    assert len(bullets) == 1, "no single top-level Retro bullet proposes review checklist items"
    bullet = bullets[0]
    assert "review-checklist.txt" in bullet
    for phrase in (
        "since the previous retro",
        "every PR review marked `Review of record <sha>`, delta reviews included",
        "a miss its verdict ruled valid once per distinct PR, except a confirmed `pre-existing` finding",
        "arbiter reports in PR bodies",
        "`profile.git.host`",
        "once per distinct PR",
        "two or more PRs",
        "count only a review or PR body whose author has write access to the repository",
        "exclude scratch arbiter reports",
        "on the retro issue",
        "`<bash glob> | <review item>`",
        "citing the review links",
        "edits no file",
    ):
        assert phrase in bullet, f"retro checklist step missing: {phrase}"


def test_retro_checklist_items_need_owner_approval() -> None:
    body = section(SKILL.read_text(), "Retro")
    bullets = [b for b in body.split("\n- ") if b.startswith("Propose review checklist items from repeated misses:")]
    assert len(bullets) == 1, "no single top-level Retro bullet proposes review checklist items"
    bullet = bullets[0]
    for phrase in (
        "enters the checklist only through an engineer PR that links the owner's approval comment on the retro issue",
        "never adds the item itself",
    ):
        assert phrase in bullet, f"retro owner approval missing: {phrase}"


def pruning_bullet() -> str:
    """Return the Retro list item that starts the pruning routine, continuation lines included."""
    lines = section(SKILL.read_text(), "Retro").splitlines()
    starts = [
        n for n, line in enumerate(lines)
        if line.startswith("- If the repository provides a pruning-candidates script")
    ]
    assert len(starts) == 1, "the pruning routine must be one separate Retro bullet"
    end = starts[0] + 1
    while end < len(lines) and lines[end].startswith("  ") and lines[end].strip():
        end += 1
    return " ".join(" ".join(lines[starts[0] : end]).split())


PRUNING_CONDITION = (
    "- If the repository provides a pruning-candidates script, run it with `--since` set to "
    "the previous retro's date, and record each candidate in the retro record with its "
    "retire or keep proposal. Each retire proposal becomes an action item under these Retro rules"
)
PRUNING_APPROVAL = ", and nothing is removed until the owner approves it in a comment on the retro issue."


def test_retro_runs_the_pruning_routine_only_when_the_repository_provides_it() -> None:
    assert pruning_bullet().startswith(PRUNING_CONDITION)


def test_retro_pruning_removes_nothing_without_owner_approval() -> None:
    # The whole bullet is pinned, so nothing can be inserted between the condition and the approval.
    assert pruning_bullet() == PRUNING_CONDITION + PRUNING_APPROVAL


def test_velocity_and_burnup_section_covers_flow_metrics() -> None:
    body = section(SKILL.read_text(), "Velocity and burnup").lower()
    for phrase in (
        "velocity",
        "burnup",
        "profile.tracker.velocity_window_cycles",
        "post the velocity and burnup report",
        "sum of the estimates",
        "done user-story and rtb",
        "unpointed",
        "missing an estimate",
        "scope history",
        "issuecounthistory",
        "completedissuecounthistory",
        "scopehistory",
        "completedscopehistory",
        "usable non-zero history",
        "all zeros",
        "say when fewer completed cycles exist",
        "dated reason comment",
        "carry-over",
        "burn-down",
    ):
        assert phrase in body, f"velocity and burnup missing: {phrase}"


def test_not_in_this_slice_section_is_gone() -> None:
    text = SKILL.read_text()
    assert not re.search(r"^## Not in this slice\s*$", text, re.MULTILINE)


def test_report_only_boundary_permits_only_ceremony_writes() -> None:
    text = SKILL.read_text()
    for phrase in (
        "set the `cycle` field on eligible issues during sprint planning",
        "only field it may change on an issue that existed before the ceremony",
        "create new issues and project documents for ceremony records",
        "add comments to the project (epic) and existing issues",
        "velocity/burnup",
        "complete the initialization of an issue it created during the ceremony",
        "closing or canceling a test issue this ceremony created",
        "never ticks a box, changes a state, closes an issue, or edits any other field on an issue that existed before the ceremony",
        "report it to `persona-product-owner`; do not amend that issue",
    ):
        assert phrase in text, f"boundary missing: {phrase}"


def test_boundary_allows_applying_po_authored_writes_under_the_story_refinement_fallback() -> None:
    text = " ".join(SKILL.read_text().split())
    assert "and applying product-owner-authored writes under the denied tracker writes fallback in `story-refinement`" in text
    assert (
        "- Under the denied tracker writes fallback in `story-refinement`, it applies tracker writes the product owner "
        "authored, verbatim, and reads each back; it authors none of them."
    ) in text


def test_boundary_exceptions_are_cross_referenced() -> None:
    text = " ".join(SKILL.read_text().split())
    assert "that is the only field it may change on an issue that existed before the ceremony, except under the denied tracker writes fallback below." in text
    assert "on an issue that existed before the ceremony, except as the next bullet allows." in text


def test_boundary_exception_list_is_well_formed() -> None:
    text = " ".join(SKILL.read_text().split())
    assert "closing or canceling a test issue this ceremony created, and applying product-owner-authored writes" in text
    assert "created, and closing or canceling" not in text
