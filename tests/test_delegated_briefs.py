"""SKL-219: keep-going, real-check, scope and no-self-review text in the delegated briefs, and the
coordinator's checklist read-back, in story-to-done, persona-staff-engineer and persona-staff-devops."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STORY_TO_DONE = ROOT / "skills" / "story-to-done" / "SKILL.md"
STAFF_ENGINEER = ROOT / "skills" / "persona-staff-engineer" / "SKILL.md"
STAFF_DEVOPS = ROOT / "skills" / "persona-staff-devops" / "SKILL.md"

KEEP_GOING = (
    "Keep working until everything the brief asks for is done, and only stop to ask when you can't go on "
    "without the coordinator or before a risky step."
)
SCOPE = (
    "When the work in the brief is done, stop and report. Don't add features, tests, files, docs or "
    "refactors the brief or the story's acceptance criteria don't call for."
)
NO_SELF_REVIEW = (
    "Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this "
    "brief and the skills it tells you to load define."
)
RESUME_MESSAGE = (
    '"Your checklist still has open items. Continue with them; if one is blocked, say what blocks it"'
)

# Each B2 requirement, as the brief states it.
REAL_CHECK = (
    "report a change done only with the output of a real check that exercises it (tests, type-checker, "
    "build, the changed command, or for infrastructure a plan or dry run against the target)",
    "a syntax-only check, or a check that failed to start, does not count",
    "Install declared dependencies only with the project's own package manager and lockfile, never with "
    "sudo or the system package manager.",
    "If no real check can run, the report names the check not run and why.",
)
SCOPE_TESTS = "The tests the real-check rule needs are called for by this brief."
GATES_ALLOWED = "The pre-PR gate and the review of record that `engineering-workflow` defines stay allowed."

# The stop points each brief already defined, restated beside the keep-going sentence.
STOP_POINTS = {
    "senior-engineer (story-to-done)": "The stop this brief already defines still holds: if you must stop, "
    "hand back blocked and say why.",
    "qa-agent (story-to-done)": "The stop this brief already defines still holds: hand back any item left "
    "outstanding with its owner.",
    "senior-engineer (persona-staff-engineer)": "The merge-approval handshake above still holds: do not merge "
    "until a matching `APPROVE` is recorded, and hand back blocked with the request ID, the PR, and the head "
    "SHA if you must stop.",
    "platform-engineer (persona-staff-devops)": "The stop before merge above still holds: stop once the PR has "
    "a completed review of record at its head, and do not merge yet.",
}

READ_BACK = (
    "read that subagent's checklist file before acting on the result; a missing or unreadable checklist "
    "counts as open items.",
    "If items remain open with no stated blocker, resume that subagent with " + RESUME_MESSAGE
    + ", at most twice per subagent, and then record the remaining items in your report.",
    "The tracker state remains the record of completion; the checklist is never evidence that work is done.",
    "If the runtime cannot resume the subagent, record the open items and continue with this skill's existing "
    "step logic; spawn no new subagent for the read-back.",
)
READ_BACK_QA = (
    "A read-back resume of the QA agent happens before step 4 handling, carries no verdict, does not "
    "increment the round count, and has a cap separate from step 4's \"once per observed change to the "
    "remainder\"."
)
READ_BACK_METRICS = "With `metrics` on, each read-back resume is its own launch row."
READ_BACK_HANDBACK = {
    STORY_TO_DONE: "When a senior engineer or QA agent hands back, ",
    STAFF_ENGINEER: "When the senior engineer hands back, ",
    STAFF_DEVOPS: "When the platform engineer hands back, ",
}
MIRRORING = "read it from there and mirror it into your list whenever you check on the subagent."
SEED_ITEM = "the checklist read-back at each handback"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def bullets_after(body: str, intro: str) -> str:
    """The contiguous bullet list that follows the intro line: the brief itself."""
    lines = body.splitlines()
    start = lines.index(intro) + 1
    while lines[start] == "":
        start += 1
    brief = []
    for line in lines[start:]:
        if not (line.startswith("- ") or line.startswith("  ")):
            break
        brief.append(line)
    assert brief, f"no brief follows {intro!r}"
    return "\n".join(brief)


def briefs() -> dict[str, str]:
    story = STORY_TO_DONE.read_text()
    return {
        "senior-engineer (story-to-done)": bullets_after(
            section(story, "2. Senior engineer: implement to deployment review"), "It must include:"),
        "qa-agent (story-to-done)": bullets_after(
            section(story, "3. QA agent: verify the deployed story"), "Brief it as a QA agent, with only:"),
        "senior-engineer (persona-staff-engineer)": bullets_after(
            section(STAFF_ENGINEER.read_text(), "3. Delegate implementation to a senior engineer"),
            "It must include:"),
        "platform-engineer (persona-staff-devops)": bullets_after(
            section(STAFF_DEVOPS.read_text(), "3. Delegate execution to a platform/SRE engineer"),
            "It must include:"),
    }


ALL_BRIEFS = list(STOP_POINTS)
ENGINEER_BRIEFS = [name for name in ALL_BRIEFS if not name.startswith("qa-agent")]


@pytest.mark.parametrize("name", ALL_BRIEFS)
def test_keep_going_sentence_appears_once_with_the_brief_stop_point_beside_it(name: str) -> None:
    brief = briefs()[name]
    assert brief.count(KEEP_GOING) == 1, f"{name}: the keep-going sentence must appear exactly once"
    bullet = next(line for line in brief.splitlines() if KEEP_GOING in line)
    assert bullet == f"- {KEEP_GOING} {STOP_POINTS[name]}", f"{name}: the stop point is the next sentence"


@pytest.mark.parametrize("name", ALL_BRIEFS)
def test_no_self_started_review_sentence_appears_once_and_keeps_the_workflow_gates(name: str) -> None:
    brief = briefs()[name]
    assert brief.count(NO_SELF_REVIEW) == 1, f"{name}: the review sentence must appear exactly once"
    assert f"- {NO_SELF_REVIEW} {GATES_ALLOWED}" in brief.splitlines(), name


@pytest.mark.parametrize("name", ENGINEER_BRIEFS)
def test_engineer_briefs_carry_the_scope_sentence_once(name: str) -> None:
    brief = briefs()[name]
    assert brief.count(SCOPE) == 1, f"{name}: the scope sentence must appear exactly once"
    assert f"- {SCOPE} {SCOPE_TESTS}" in brief.splitlines(), name


@pytest.mark.parametrize("name", ENGINEER_BRIEFS)
def test_engineer_briefs_carry_every_real_check_requirement(name: str) -> None:
    brief = briefs()[name]
    for requirement in REAL_CHECK:
        assert brief.count(requirement) == 1, f"{name}: missing or repeated: {requirement}"


def test_the_qa_brief_is_out_of_the_real_check_and_scope_rules() -> None:
    brief = briefs()["qa-agent (story-to-done)"]
    assert SCOPE not in brief and SCOPE_TESTS not in brief
    for requirement in REAL_CHECK:
        assert requirement not in brief


@pytest.mark.parametrize("path", [STORY_TO_DONE, STAFF_ENGINEER, STAFF_DEVOPS])
def test_each_sentence_lives_only_in_the_briefs(path: Path) -> None:
    text = path.read_text()
    named = [brief for name, brief in briefs().items() if brief in text]
    for sentence in (KEEP_GOING, NO_SELF_REVIEW, SCOPE, *REAL_CHECK):
        in_briefs = sum(brief.count(sentence) for brief in named)
        assert text.count(sentence) == in_briefs, f"{path.parent.name}: {sentence!r} appears outside a brief"


@pytest.mark.parametrize("path", [STAFF_ENGINEER, STAFF_DEVOPS])
def test_none_of_it_reaches_the_shadow_adjudicator_spawn_text(path: Path) -> None:
    text = path.read_text()
    gate = next(heading for heading in re.findall(r"^## (4\..*)$", text, re.MULTILINE))
    shadow = section(text, gate)
    for phrase in (KEEP_GOING, NO_SELF_REVIEW, SCOPE, SCOPE_TESTS, GATES_ALLOWED, *REAL_CHECK, *READ_BACK,
                   RESUME_MESSAGE, *STOP_POINTS.values()):
        assert phrase not in shadow, f"{path.parent.name}: {phrase!r} is in the shadow adjudicator text"


@pytest.mark.parametrize("path", [STORY_TO_DONE, STAFF_ENGINEER, STAFF_DEVOPS])
def test_step_0_states_the_read_back_once_beside_the_mirroring_sentence(path: Path) -> None:
    text = path.read_text()
    step_0 = section(text, "0. Track everything on a todo list").splitlines()
    mirroring = next(i for i, line in enumerate(step_0) if line.endswith(MIRRORING))
    first = READ_BACK_HANDBACK[path] + READ_BACK[0]
    assert step_0[mirroring + 1] == first, f"{path.parent.name}: the read-back follows the mirroring sentence"
    assert step_0[mirroring + 2: mirroring + 2 + len(READ_BACK) - 1] == list(READ_BACK[1:]), path.parent.name
    for sentence in (first, *READ_BACK[1:]):
        assert text.count(sentence) == 1, f"{path.parent.name}: stated more than once: {sentence!r}"
    assert text.count(RESUME_MESSAGE) == 1, f"{path.parent.name}: the resume message is stated once"


@pytest.mark.parametrize("path", [STORY_TO_DONE, STAFF_ENGINEER, STAFF_DEVOPS])
def test_step_0_seeds_a_todo_item_for_the_read_back(path: Path) -> None:
    step_0 = section(path.read_text(), "0. Track everything on a todo list")
    seed = next(line for line in step_0.splitlines() if line.startswith("Seed it with at least:"))
    assert SEED_ITEM in seed, f"{path.parent.name}: step 0 seeds no read-back item"


def test_story_to_done_scopes_the_qa_read_back_apart_from_the_step_4_continuation() -> None:
    step_0 = section(STORY_TO_DONE.read_text(), "0. Track everything on a todo list").splitlines()
    last = step_0.index(READ_BACK[-1])
    assert step_0[last + 1] == READ_BACK_QA
    assert step_0[last + 2] == READ_BACK_METRICS
    assert STORY_TO_DONE.read_text().count(READ_BACK_QA) == 1


@pytest.mark.parametrize("path", [STAFF_ENGINEER, STAFF_DEVOPS])
def test_the_personas_carry_no_story_to_done_qa_or_metrics_read_back_rule(path: Path) -> None:
    text = path.read_text()
    assert READ_BACK_QA not in text and READ_BACK_METRICS not in text


def test_the_vendored_references_are_unchanged() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
