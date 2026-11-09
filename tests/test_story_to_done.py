"""Contract checks for the story-to-done skill."""

import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "story-to-done" / "SKILL.md"
PROTOCOL = ROOT / "skills" / "story-to-done" / "references" / "metrics-protocol.md"
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
    required = {"todo-tracking", "linear", "code-review", "secrets"}
    assert required <= set(MANIFEST["skills"]["story-to-done"])


def test_todo_tracking_has_seed_entry() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "- **story-to-done:**" in text


def test_readme_lists_skill_in_table() -> None:
    row = "| [`story-to-done`](skills/story-to-done/SKILL.md) |"
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
    assert found, "missing story-to-done row from the README Skills table"


def test_skill_links_to_required_references() -> None:
    text = SKILL.read_text()
    for name in ("profile", "runtimes", "todo-tracking", "linear", "code-review", "secrets", "metrics"):
        assert f"](references/{name}.md)" in text, name


def test_arguments_table_pins_each_default() -> None:
    body = section(SKILL.read_text(), "Arguments")
    for row in (
        "| `engineer-model` | the senior engineer's model | Sonnet 5.5 (`claude-sonnet-5-5`) |",
        "| `engineer-effort` | the senior engineer's reasoning effort | `high` |",
        "| `qa-model` | the QA agent's model | Opus 5.5 (`claude-opus-5-5`) |",
        "| `qa-effort` | the QA agent's reasoning effort | `high` |",
    ):
        assert row in body, f"defaults table missing: {row}"
    for phrase in (
        "`STORY_ID` is required",
        "never guess a story number",
        "An argument left out takes its default.",
        "`low`, `medium`, `high`, `xhigh`, or `max`",
        "never substitute another model or level",
    ):
        assert phrase in body, f"arguments missing: {phrase}"


def test_senior_engineer_uses_its_model_and_engineering_workflow() -> None:
    body = section(SKILL.read_text(), "2. Senior engineer: implement to deployment review")
    for phrase in (
        "Spawn a clean, neutral subagent",
        "on `engineer-model` at `engineer-effort`",
        "load and follow `engineering-workflow`",
        "`profile.tracker.states.in_deployment_review`",
        "This skill assigns merge approval to no manager",
        "read the story yourself and confirm",
    ):
        assert phrase in body, f"step 2 missing: {phrase}"


# SKL-159: the new-round sentence is pinned exactly as the story quotes it, and the one
# continuation a round may take is an exception to it. SKL-219 adds the step 0 checklist
# read-back resume of the current round's QA agent as the second and last exception.
QA_ROUND_SENTENCE = (
    "Spawn a new clean, neutral subagent on qa-model at qa-effort for every new QA round; never resume an "
    "agent from an earlier round, since it carries that round's conclusions."
)
QA_ROUND_EXCEPTION = (
    "Continuation of the current round under step 4 and the step 0 checklist read-back resume of the current "
    "round's QA agent are the only exceptions to that sentence, and neither increments the round count."
)
OLD_QA_ROUND_CLAUSE = "never resume an earlier QA agent, since it carries that round's conclusions"


def test_each_qa_round_is_a_new_agent_with_a_minimal_brief() -> None:
    body = section(SKILL.read_text(), "3. QA agent: verify the deployed story")
    assert QA_ROUND_SENTENCE in body.splitlines(), "step 3 must read the pinned new-round sentence exactly"
    assert QA_ROUND_EXCEPTION in body.splitlines(), "step 3 must scope the exception a round may take"
    assert OLD_QA_ROUND_CLAUSE not in body, "the clause that forbids resuming is replaced, not kept beside it"
    for phrase in (
        "load and follow `qa-verification`",
        "Never give it the senior engineer's handback beyond the environment",
        "an earlier round's verdicts",
        "the verdict you expect",
    ):
        assert phrase in body, f"step 3 missing: {phrase}"


# The owner-stop sentence is pinned whole: the fragment assertions this replaces let the
# owner-clear clause be deleted with the suite still green (SKL-159 QA round 1).
QA_OWNER_STOP_SENTENCE = (
    "A stop for an owner action ends the round: once the owner clears it, that round's work starts over as a "
    "new round under this step with a new QA agent, and a fix/deploy cycle or an amended acceptance basis "
    "likewise starts a new round."
)


def owner_stop_lines() -> list[str]:
    return section(SKILL.read_text(), "3. QA agent: verify the deployed story").splitlines()


def prose_lines(lines: list[str]) -> set[int]:
    """The indexes of the lines an agent reads as instructions: not in a fence, not in a comment.

    A comment can open or close anywhere in a line, so each line is scanned for both markers
    rather than only at its start, and a fence's contents are never prose.
    """
    prose: set[int] = set()
    fenced = False
    commented = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if fenced:
            if stripped.startswith(("```", "~~~")):
                fenced = False
            continue
        if not commented and stripped.startswith(("```", "~~~")):
            fenced = True
            continue
        visible = ""
        rest = line
        while rest:
            if commented:
                end = rest.find("-->")
                if end < 0:
                    rest = ""
                else:
                    rest = rest[end + 3:]
                    commented = False
            else:
                start = rest.find("<!--")
                if start < 0:
                    visible += rest
                    rest = ""
                else:
                    visible += rest[:start]
                    rest = rest[start + 4:]
                    commented = True
        if visible.strip():
            prose.add(index)
    return prose


def test_an_owner_stop_ends_the_round_so_the_next_attempt_is_a_new_round() -> None:
    lines = owner_stop_lines()
    assert QA_OWNER_STOP_SENTENCE in lines, "step 3 must read the whole owner-stop sentence exactly"
    assert SKILL.read_text().count(QA_OWNER_STOP_SENTENCE) == 1, (
        "the owner-stop sentence is stated once in the skill, not only once in step 3"
    )
    assert lines.index(QA_OWNER_STOP_SENTENCE) in prose_lines(lines), (
        "the owner-stop sentence must be operative prose, not an example in a fence or a comment"
    )


def state_bullets(body: str) -> dict[str, str]:
    """Map each `- **<label>:**` bullet in a section to its text, continuation lines included."""
    bullets: dict[str, str] = {}
    label = None
    for line in body.splitlines():
        match = re.match(r"^- \*\*(.+?):\*\*", line)
        if match:
            label = match.group(1)
            assert label not in bullets, f"duplicate bullet: {label}"
            bullets[label] = line
        elif label and line.startswith("  "):
            bullets[label] += "\n" + line
        else:
            label = None
    return bullets


def in_order(text: str, *phrases: str) -> bool:
    positions = [text.find(phrase) for phrase in phrases]
    return -1 not in positions and positions == sorted(positions)


def test_qa_outcome_has_one_branch_per_state() -> None:
    bullets = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))
    assert set(bullets) == {
        "`profile.tracker.states.done`",
        "`profile.tracker.states.in_progress`",
        "`profile.tracker.states.in_deployment_review`",
        "`profile.tracker.states.blocked`",
        "Any other state",
    }
    assert "report it and stop" in bullets["Any other state"]
    assert "report the blocking story and stop" in bullets["`profile.tracker.states.blocked`"]
    branch = " ".join(bullets["`profile.tracker.states.in_deployment_review`"].split())
    assert in_order(branch, "QA is not finished", STEP4_CLASSIFY)
    assert STEP4_OLD_SENTENCE not in branch, "the sentence that sent every outcome to a stop must be gone"


# SKL-159: the in_deployment_review branch classifies the remainder by owner, continues the
# current QA round only when every outstanding item is QA's own, and stops for anything else.
STEP4_OLD_SENTENCE = "Report exactly what remains and who owns it, and stop; resume at step 3 once it is cleared."
STEP4_OPEN = "QA is not finished: one or more items in its handback are outstanding."
STEP4_CLASSIFY = "Classify each outstanding item by its owner."
STEP4_RESUME = (
    "When at least one item is outstanding and every outstanding item is work the current QA agent itself can "
    "finish under its existing authority "
    "in the current round, such as an evidence PR it opened that is still unmerged with its review-of-record "
    "gate in flight, or a QA step still to run, step 4 resumes that same QA agent with a clean, neutral "
    "continuation message that states only that the round is unfinished and names that round's scratch "
    "subdirectory."
)
STEP4_CARRY = (
    "The continuation message carries no verdict, no expected verdict, no earlier round's conclusions, no "
    "senior engineer handback, and nothing the coordinator observed after the handback."
)
STEP4_ROUND = (
    "The continuation does not increment the QA round count, reuses that round's scratch subdirectory and "
    "checklist, and with `metrics` on is recorded as its own launch row within that same round."
)
STEP4_READBACKS = (
    "After each continuation handback, step 3's state and merged-PR review-of-record read-backs repeat in full "
    "before this step applies again."
)
STEP4_OTHER_OWNER = (
    "If any outstanding item names any other owner - the owner, a maintainer's approval or access grant, a "
    "human merge, an external deploy, a pending acceptance-basis ruling - report exactly what remains and who "
    "owns it, and stop, even when QA-owned work also remains; a mixed remainder containing both an owner "
    "action and QA's own steps is reported and stopped, never resumed."
)
STEP4_NO_RUNTIME = (
    "If the runtime cannot resume that QA session, report the limitation and stop; never substitute a new "
    "clean, neutral subagent for it as a continuation of that round."
)
STEP4_STALL = (
    "A continuation is made at most once per observed change to the remainder: when a resumed handback leaves "
    "the same remaining items with no observed progress, report the stall and stop."
)
STEP4_SENTENCES = [
    STEP4_OPEN,
    STEP4_CLASSIFY,
    STEP4_RESUME,
    STEP4_CARRY,
    STEP4_ROUND,
    STEP4_READBACKS,
    STEP4_OTHER_OWNER,
    STEP4_NO_RUNTIME,
    STEP4_STALL,
]


def in_deployment_review_branch() -> str:
    bullets = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))
    return " ".join(bullets["`profile.tracker.states.in_deployment_review`"].split())


def test_the_step_four_continuation_branch_is_pinned() -> None:
    body = in_deployment_review_branch()
    assert in_order(body, *STEP4_SENTENCES), "the continuation branch does not read its pinned sentences in order"
    assert STEP4_OLD_SENTENCE not in body, "the stop sentence this branch replaces is still stated"


def test_a_continuation_never_carries_a_verdict_or_an_earlier_conclusion() -> None:
    body = in_deployment_review_branch()
    for excluded in (
        "no verdict",
        "no expected verdict",
        "no earlier round's conclusions",
        "no senior engineer handback",
        "nothing the coordinator observed after the handback",
    ):
        assert excluded in STEP4_CARRY, f"the continuation message must exclude {excluded}"
    assert "states only that the round is unfinished and names that round's scratch subdirectory" in STEP4_RESUME
    assert STEP4_CARRY in body


def test_a_continuation_keeps_the_round_identity_and_its_own_launch_row() -> None:
    body = in_deployment_review_branch()
    assert in_order(
        body,
        "does not increment the QA round count",
        "reuses that round's scratch subdirectory and checklist",
        "with `metrics` on is recorded as its own launch row within that same round",
    ), "a continuation must keep the round, reuse its scratch subdirectory, and record its own launch row"
    assert STEP4_READBACKS in body, "the post-handback read-backs must repeat before the branch applies again"


def test_any_other_owner_stops_even_when_qa_work_remains() -> None:
    body = in_deployment_review_branch()
    assert in_order(
        body,
        "If any outstanding item names any other owner",
        "a pending acceptance-basis ruling",
        "report exactly what remains and who owns it, and stop, even when QA-owned work also remains",
        "a mixed remainder containing both an owner action and QA's own steps is reported and stopped, never resumed",
    ), "an owner action must take precedence over QA-owned work"
    assert in_order(
        body,
        STEP4_NO_RUNTIME,
        STEP4_STALL,
    ), "a runtime that cannot resume must stop without a substitute agent, and a stall must be reported"


def test_done_branch_checks_the_completion_record() -> None:
    done = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))[
        "`profile.tracker.states.done`"
    ]
    assert in_order(
        done,
        "confirm the completion record before you accept it",
        "every AC and DoD box is ticked",
        "QA's handback rules every item verified",
        "when `profile.qa.evidence_dir` is set, the evidence PR is merged",
        "go to step 5",
        "report the mismatch and stop",
    )
    close_out = section(SKILL.read_text(), "5. Close out")
    assert "with the completion record step 4 checks" in close_out


def test_failed_items_go_back_to_the_engineer_before_qa_reruns() -> None:
    reopened = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))[
        "`profile.tracker.states.in_progress`"
    ]
    assert in_order(
        reopened,
        "Those failed items are the issues to fix.",
        "Hand them back to the senior engineer",
        "add to the hand-back brief each failed item as QA recorded it",
        "fix them through `engineering-workflow` on this story",
        "Confirm that state as step 2 does",
        "run step 3 again with a new QA agent",
    )


def test_disputes_and_incidentals_are_not_ruled_in_the_loop() -> None:
    body = section(SKILL.read_text(), "4. Act on the QA outcome")
    assert "do not relay its argument to a QA agent and do not rule on it yourself" in body
    assert "are not fixed in this loop" in body


def test_orchestrator_never_sets_the_story_state() -> None:
    text = SKILL.read_text()
    phrases = (
        "move the story",
        "move it to",
        "set the story",
        "mark the story",
        "mark it done",
        "transition the story",
        "update the story",
        "update the issue",
        "update the status",
        "status to",
    )
    for heading in (
        "0. Track everything on a todo list",
        "1. Read the story and pick the starting point",
        "2. Senior engineer: implement to deployment review",
        "3. QA agent: verify the deployed story",
        "4. Act on the QA outcome",
        "5. Close out",
    ):
        body = section(text, heading).lower()
        for phrase in phrases:
            assert phrase not in body, f"{heading} tells the orchestrator to set the state: {phrase}"


def test_only_qa_moves_the_story_to_done() -> None:
    body = section(SKILL.read_text(), "Boundaries")
    assert "Only a QA agent's closing decision moves the story to Done" in body
    assert "never mark it done yourself, and never on merge alone" in body


# SKL-159: continuation grants no new authority, so the prohibition is pinned in Boundaries,
# outside the step sections the state scan reads.
BOUNDARIES_NO_NEW_AUTHORITY = (
    "The coordinator never merges a PR, including the evidence PR; never ticks an AC or DoD box; never moves "
    "the story state; never decides a QA verdict; and never bypasses a review gate."
)
BOUNDARIES_CONTINUATION_AUTHORITY = (
    "A continuation grants no new authority: it leaves that prohibition, and the single permitted tracker "
    "write above, exactly as they are."
)
STEP_SECTIONS = (
    "0. Track everything on a todo list",
    "1. Read the story and pick the starting point",
    "2. Senior engineer: implement to deployment review",
    "3. QA agent: verify the deployed story",
    "4. Act on the QA outcome",
    "5. Close out",
)


def test_boundaries_pin_the_prohibition_and_that_continuation_grants_no_authority() -> None:
    text = SKILL.read_text()
    body = " ".join(section(text, "Boundaries").split())
    assert BOUNDARIES_NO_NEW_AUTHORITY in body, "Boundaries must pin the merge, tick, state, verdict and gate prohibition"
    assert BOUNDARIES_CONTINUATION_AUTHORITY in body, "Boundaries must say a continuation grants no new authority"
    for heading in STEP_SECTIONS:
        assert BOUNDARIES_NO_NEW_AUTHORITY not in " ".join(section(text, heading).split()), (
            f"the prohibition is pinned in Boundaries, not in {heading}"
        )


def test_the_continuation_leaves_the_metrics_summary_permission_unchanged() -> None:
    body = " ".join(section(SKILL.read_text(), "Boundaries").split())
    assert BOUNDARIES_ONLY_WRITE in body
    assert in_order(body, BOUNDARIES_ONLY_WRITE, BOUNDARIES_CONTINUATION_AUTHORITY), (
        "the no-new-authority sentence must leave the single permitted tracker write as it stands"
    )


def test_runtimes_maps_reasoning_effort() -> None:
    text = (ROOT / "shared" / "runtimes.md").read_text()
    assert "| Choose a subagent's reasoning effort | `effort` parameter" in text
    assert "provider/model#variant" in text
    assert "V1" in text and "`variant:`" in text
    assert "never substitute another level" in text
    assert "`CLAUDE_CODE_EFFORT_LEVEL` overrides every subagent's effort" in text
    assert "`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is an on/off flag" in text
    assert "a subagent runs on `CLAUDE_CODE_SUBAGENT_MODEL`, or on the main session's model" in text
    assert "if it differs from the effort a skill asks for, stop and say so" in text
    assert "if that model differs from the one a skill asks for, stop and say so" in text
    assert in_order(
        text,
        "a fork and a skill that runs in a subagent with `model: inherit` still run on the main session's model",
        "the built-in Explore subagent runs on its own listed model when only the flag is set",
        "never use one of these for a model-pinned role",
    )


def test_resumed_story_names_the_qa_environment() -> None:
    body = section(SKILL.read_text(), "3. QA agent: verify the deployed story")
    assert "When step 2 did not run in this engagement" in body
    assert "leave it out so `qa-verification` picks its default" in body


def test_both_roles_get_nesting_or_shell_launched_reviews() -> None:
    body = section(SKILL.read_text(), "2. Senior engineer: implement to deployment review")
    assert in_order(
        body,
        "so does the QA agent in step 3",
        "give both delegated agents nesting per that runtime map",
        "launch their review roles as shell commands",
        "does not fit this skill",
        "If neither works, stop and say so.",
    )


def test_nesting_guidance_stays_runtime_neutral() -> None:
    body = SKILL.read_text().split("\n---\n", 1)[1]
    assert "subagent_depth" not in body
    assert "grant `task`" not in body
    assert "On opencode" not in body


# SKL-50: the engineer never arbitrates the pre-PR gate; one sentence states the rule in step 2
# and the brief carries it word for word as its own bullet right after the merge-rules bullet.
ARBITRATION_RULE = (
    "The engineer never does pre-PR arbitration (`adversarial-review-pipeline` Phase 3, "
    "`engineering-workflow` step 4 Verify stage) or rules a finding valid, invalid or accepted risk or the gate "
    "converged (applying the gate's scope guard is not arbitration), and fixes what QA ruled not met or the "
    "adjudicator ruled valid without overturning those rulings; a separate clean, neutral arbiter on "
    "`profile.review.pre_pr.arbiter`, independent of engineer and coordinator, arbitrates every head."
)
STEP_2 = "2. Senior engineer: implement to deployment review"


def step_2_lines() -> list[str]:
    return section(SKILL.read_text(), STEP_2).splitlines()


def test_one_sentence_states_the_arbitration_rule_and_the_brief_repeats_it_verbatim() -> None:
    lines = step_2_lines()
    assert ARBITRATION_RULE in lines, "step 2 must state the rule as its own prose line"
    assert lines.index(ARBITRATION_RULE) in prose_lines(lines), "the rule must be operative prose"
    merge_rules = [i for i, line in enumerate(lines) if line.startswith("- The merge rules:")]
    assert len(merge_rules) == 1, "step 2's brief must carry exactly one merge-rules bullet"
    assert lines[merge_rules[0] + 1] == "- " + ARBITRATION_RULE, "the brief bullet must follow the merge rules verbatim"
    assert SKILL.read_text().count(ARBITRATION_RULE) == 2, "exactly one wording, stated once and briefed once"


def test_the_arbitration_rule_names_both_stages_and_the_profile_arbiter() -> None:
    # Read from the skill itself, so dropping a phrase from both the skill and the constant still fails.
    rules = [line.removeprefix("- ") for line in step_2_lines() if line.removeprefix("- ").startswith("The engineer never does")]
    assert len(rules) == 2, "the rule is stated once and briefed once"
    for rule in rules:
        for phrase in (
            "`adversarial-review-pipeline` Phase 3",
            "`engineering-workflow` step 4 Verify stage",
            "valid, invalid or accepted risk or the gate converged",
            "applying the gate's scope guard is not arbitration",
            "fixes what QA ruled not met or the adjudicator ruled valid without overturning those rulings",
            "a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`",
            "independent of engineer and coordinator",
            "arbitrates every head",
        ):
            assert phrase in rule, phrase


def test_no_launchable_arbiter_hands_back_blocked() -> None:
    body = section(SKILL.read_text(), STEP_2)
    hand_back = next(line for line in body.splitlines() if line.startswith("- What to hand back:"))
    assert (
        "or, if it stops, that it is blocked and why, including when no arbiter can launch; "
        "a missing arbitration is never clean or converged."
    ) in hand_back
    assert "launch their review roles as shell commands (`runtime: command`, `codex` or `opencode`)" in body
    assert "(`runtime: codex` or `runtime: command`)" not in body


def test_an_adjudicator_ruling_dispute_goes_to_the_user() -> None:
    body = section(SKILL.read_text(), "4. Act on the QA outcome")
    assert "If the senior engineer disputes a failed verdict or an adjudicator's ruling" in body
    assert "Stop and put the item, its evidence, and the engineer's evidence to the user" in body


def test_the_engineer_brief_stays_neutral_and_names_the_gate_and_branch() -> None:
    body = section(SKILL.read_text(), STEP_2)
    assert "The brief carries facts and constraints, never your expectations about the outcome." in body.splitlines()
    assert "the pre-PR gate and the PR to `profile.git.integration_branch`" in body


# SKL-48: the `metrics` switch, its off path, and its wiring.

METRICS_ROW = "| `metrics` | whether the run collects and reports run metrics | `off` |"
METRICS_LINE_SENTENCE = (
    "Write the four resolved model and effort values and the `metrics: on|off` line at the top of "
    "your todo list and in the closing report of every end state"
)


def test_arguments_table_adds_the_metrics_switch_off_by_default() -> None:
    body = section(SKILL.read_text(), "Arguments")
    assert METRICS_ROW in body, "arguments table missing the metrics row and its off default"
    assert "Five arguments are optional" in body
    assert "Four arguments are optional" not in body


def test_metrics_switch_plain_words_are_mapped_or_asked() -> None:
    body = " ".join(section(SKILL.read_text(), "Arguments").split())
    for phrase in (
        "`metrics` is given as `metrics=on` or `metrics=off`",
        '"with metrics" and "metrics on" mean on',
        '"without metrics" and "metrics off" mean off',
        "ask the user about any other phrasing about metrics; never guess",
        "Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.",
    ):
        assert phrase in body, f"arguments missing: {phrase}"


def test_metrics_line_goes_in_the_todo_list_and_every_closing_report() -> None:
    body = " ".join(section(SKILL.read_text(), "Arguments").split())
    assert METRICS_LINE_SENTENCE in body
    assert "(the step 5 report, or the report made at any stop, including one before step 0)" in body
    assert "Write the four resolved values at the top of your todo list and in the final report" not in body
    close_out = " ".join(section(SKILL.read_text(), "5. Close out").split())
    assert "the four resolved model and effort values and the `metrics: on|off` line" in close_out


METRICS_OPENING = "Only when `metrics` is on, read [references/metrics.md](references/metrics.md)"
# SKL-95: the closing-report summary. SKL-96 adds the engineer and QA launch rows, the extras, the
# metrics-file location, and the brief independence rules. SKL-94 adds the summary post on the story.
REMOVED_NO_POST = (
    "With `metrics` on, this skill posts no summary comment; this sentence overrides every posting rule in "
    "`references/metrics.md`."
)
REMOVED_NO_TRACKER_WRITE = "The coordinator makes no tracker write and never sets the story state."
METRICS_POST = (
    "With `metrics` on, the coordinator posts the summary as one comment on the story at the end of every "
    "invocation in which the story identifier is known, whatever the end state (Done, or any stop, including a "
    "stop before step 0 or before any senior engineer or QA agent is spawned); with no known story identifier "
    "no post is attempted."
)
METRICS_POST_BODY = (
    "The post comes after the end form and before the closing report, and the comment body is the template's "
    "heading line, a blank line, and the end form's output copied verbatim."
)
METRICS_READ_BACK = (
    "The coordinator reads the comment back, confirms its body matches what it posted, repeats the same summary "
    "in the closing report, and names the posted comment there."
)
METRICS_POST_NOT_A_LAUNCH = (
    "The summary post and its read-back are not launches: they get no row and no timestamp, there is no second "
    "`invocation_end`, and the elapsed wall-clock excludes both."
)
METRICS_POST_INTERFACE = (
    "The summary post uses the tracker interface step 1 read the story with (the `linear` CLI when step 1 did "
    "not run) and is tried once."
)
METRICS_POST_DENIED = (
    "If the summary post is denied or unavailable, including when the story cannot be read, the closing report "
    "carries the summary and names the denied or unavailable write, and no other tool or server is tried."
)
METRICS_READ_BACK_FAILED = (
    "A failed or differing read-back is not retried or reposted: the closing report carries the summary and "
    "names the failed read-back."
)
METRICS_RESUMED = "A resumed run is a new invocation and posts its own summary comment."
METRICS_POST_NO_SECRETS = (
    "The `end-state` extra is a short stop reason with no path, secret, or tool output, no other recorded extra "
    "holds a path or secret, so a failed item is recorded restated without its path, and the summary comment "
    "contains no secrets and no local or scratch paths."
)
METRICS_ONLY_WRITE = (
    "The summary comment is the coordinator's only tracker write: the senior engineer and the QA agent make "
    "their own, and failed QA items reach the senior engineer in the hand-back brief, never as a coordinator "
    "tracker write."
)
METRICS_NEVER_SETS_STATE = "The coordinator never sets the story state."
BOUNDARIES_ONLY_WRITE = (
    "- With `metrics` on, the coordinator's single permitted tracker write is the summary comment, which it "
    "reads back and repeats in the closing report; with `metrics` off it makes no tracker write."
)
METRICS_BODY_BYTES = (
    "The summary body file holds exactly the heading line, a blank line and the end form's output without the "
    "newline that ends its last line, which is no line's text, so no line is added, reworded, or left out; the "
    "closing report's summary is those same bytes."
)
METRICS_END_IS_LAST = (
    'The end form is the last launch: between it and the closing report the coordinator launches only the '
    'summary post and its read-back, and looks up no command syntax or JSON shape.'
)
METRICS_POST_ITEM = (
    "After the end form, the coordinator writes the summary body file with the runtime's file-write tool, and right "
    "after the read-back, or after a denied or unavailable post, marks the post item completed with its todo tool, "
    "or in its checklist file with the file-write tool, noting any denied post or failed read-back; neither write is "
    "a launched command."
)
METRICS_LINEAR_COMMANDS = (
    "With the `linear` CLI, the post is `linear issue comment add '<story>' --body-file '<summary body "
    "file>'`, which prints the comment's URL ending in `#comment-<id>` (a post that prints no such `<id>` "
    'is a failed read-back), and the read-back is this one command, with that `<id>` in place of '
    '`<comment id>`: `o=$(linear issue comment list \'<story>\' --json) && printf \'%s\' "$o" | jq -e --arg '
    "id '<comment id>' --rawfile body '<summary body file>' '($id | length) > 0 and ([.nodes[] | "
    "select(.id | startswith($id))] | length == 1 and .[0].body == $body)'`; with another tracker "
    'interface the read-back reads the comment by the identifier its post returns, and a post that '
    'returns no identifier is a failed read-back.'
)
METRICS_WRAPPED_WHOLE = (
    "The wrapped command is the whole launch, so the wrapper's timing covers all of it: nothing is "
    'chained before or after the wrapper in the same launch.'
)
METRICS_SCRIPT_ONCE = (
    'The summary script runs only as the end form, never as a preview, because each run that writes its row '
    'appends another `invocation_end`: it runs once per invocation, again after it reports an invalid record,'
    ' which leaves the metrics file as it was, and again after any other nonzero exit, but first the '
    "coordinator restores the metrics file, with the runtime's file-edit tool, to exactly the content it read"
    " with the runtime's file-read tool immediately before that failed launch, so the record keeps one "
    '`invocation_end`; the coordinator therefore reads the metrics file immediately before each end-form '
    'launch.'
)
METRICS_NO_EDIT = (
    'The coordinator never edits, rewrites, or deletes a line of the metrics file other than restoring it '
    'before a rerun as above, with one exception: when '
    'the end form reports an invalid record, the coordinator corrects, in place, only the value it names and '
    'keeps every other value as it was recorded: a figure or an extra slug gets only its format corrected, and '
    'a row label used twice or reserved gets a new label, under the row-label rule above, on the `start` and '
    '`end` lines of the later row that carries it.'
)
METRICS_READ_BACK_RESULT = (
    'The read-back command compares the comment body with the summary body file exactly, byte for byte, '
    'and the read-back matched the summary only when it prints `true` and exits 0; anything else it '
    'prints, any other exit status, and any parse error is a failed read-back.'
)
METRICS_READ_BACK_FINAL = (
    'A failed read-back is final: the coordinator runs no second read-back, no other filter, and no '
    'command that inspects what the read-back printed, and the closing report says the read-back failed, '
    'never that it matched.'
)
METRICS_POSTING = [
    METRICS_POST,
    METRICS_POST_BODY,
    METRICS_BODY_BYTES,
    METRICS_END_IS_LAST,
    METRICS_POST_ITEM,
    METRICS_LINEAR_COMMANDS,
    METRICS_READ_BACK_RESULT,
    METRICS_READ_BACK,
    METRICS_POST_NOT_A_LAUNCH,
    METRICS_POST_INTERFACE,
    METRICS_POST_DENIED,
    METRICS_READ_BACK_FAILED,
    METRICS_READ_BACK_FINAL,
    METRICS_RESUMED,
    METRICS_POST_NO_SECRETS,
    METRICS_ONLY_WRITE,
]
METRICS_LOCATION = (
    "- **Location:** the coordinator keeps every figure in its one metrics file, the `<metrics file>` below, "
    "in the session scratch directory, outside every role subdirectory."
)
METRICS_NEVER_NAMED = "- **Never named:** the metrics file is never named in a brief."
# SKL-132: the usage pointer to the shared procedure, with no formula of its own.
METRICS_USAGE = (
    "- **Usage:** Each launch's Tokens and Tool calls are read as the \"Read a subagent's usage\" row and the "
    "\"Usage from shell-launched agents\" rule in [references/runtimes.md](references/runtimes.md) state; this "
    "section states no usage formula of its own."
)
METRICS_TIMED_LAUNCHES = (
    "- **Timed launches:** time each senior engineer launch and each QA launch row, meaning each QA round's "
    "spawn in step 3 and each continuation of that round in step 4, taking the start immediately before that "
    "launch and the end when it returns, and record it as one row in launch order under a "
    "label unique within the invocation, with its runtime, model, effort, duration, tokens, and tool "
    "calls as `references/metrics.md` defines; `not "
    "reported` stands for any figure the runtime does not return, and a resumed role's cumulative figure is "
    "marked `cumulative`."
)
METRICS_LAUNCH_POINTS = (
    "The senior engineer's timed launches are the first launch in step 2, each checklist read-back resume "
    "of the senior engineer under step 0, and each resume or re-spawn in step 4; each QA round is a launch "
    "row in step 3, a continuation of that round under step 4 is a further launch row within the same "
    "round, and each checklist read-back resume of a QA agent under step 0 is a launch row of its own "
    "within that QA agent's round."
)
METRICS_EXTRAS = (
    "- **Extras:** take each `story-to-done` extra at the step that observes it: **Start** from the step 1 "
    "state read and whether step 2 ran; **PRs merged** from every step 2, step 3, and step 4 read of a "
    "merged PR's head and merge commit; **Time to deployment review** from the recorded invocation start "
    "to the read-back that confirms the deployment-review state; **QA rounds** at the spawn of each new "
    "round in step 3; each round's **QA round durations** entry as the sum of that round's launch rows' "
    "recorded durations, each row's figure taken as returned, which for a round holding more than one launch "
    "row is that round's duration and replaces the single-row duration `references/metrics.md` states for a "
    "round, and a row whose duration the coordinator did not capture reads `not reported`, which makes that "
    "round's entry `not reported` too since the sum never estimates a missing figure; **Failed items** from the step 4 "
    "read of "
    "each QA round's outcome, in round order; **Fix rounds** from the step 4 branch that hands the failed "
    "items back; and **End state** immediately before the end form, once the run's end state or stop reason is known."
)
METRICS_BRIEF_EXCLUSION = (
    "- **Independence:** no senior engineer or QA brief carries this invocation's figures or another role's "
    "figures from this invocation, including in a later round or a re-spawn."
)
METRICS_STEP0 = (
    "With `metrics` on, seed two more items: collect the metrics figures; then post the metrics summary on the "
    "story and read it back before giving the summary in the closing report."
)
METRICS_NOTHING_BEFORE_START = (
    "With `metrics` on, launch no command before the start form, not even to read a file or list a directory; "
    "read this skill, its references and the profile with the runtime's file-read tool, which launches nothing."
)
METRICS_START = (
    "With `metrics` on, the first command launched, before step 0, is this start form, which records "
    "`invocation_start` and makes its `metrics.txt` the `<metrics file>` of every later launch, with the "
    "scratch-directory creation from `references/runtimes.md`, or `scratch='<directory you were handed>'` when "
    "you were handed one, in place of `<scratch creation>`:"
)
METRICS_START_BLOCK = [
    "```sh",
    "s=$(date -u +%s.%N); <scratch creation>",
    "printf 'start %s start\\nend %s start\\n' \"$s\" \"$(date -u +%s.%N)\" >> \"$scratch/metrics.txt\"",
    "```",
]
METRICS_COMMAND_ROWS = (
    "From then on, record a row for each command the coordinator launches, in launch order, with its usage "
    "figures recorded under `references/metrics.md` and `not reported` for any usage the runtime does not return."
)
METRICS_WRAPPER_INTRO = (
    "Launch every later command other than the end form below, the summary post, and its read-back in this "
    "wrapper, with the command in place of "
    "`<command>`, a label unique within the invocation, other than the reserved `start` and `end`, without a "
    "single quote and naming no path, in place of `<row label>`, and "
    "the absolute path of that `metrics.txt` in place of `<metrics file>`:"
)
METRICS_WRAPPER_BLOCK = [
    "```sh",
    "f='<metrics file>'; printf 'start %s %s\\n' \"$(date -u +%s.%N)\" '<row label>' >> \"$f\"; (",
    "<command>",
    "); rc=$?; printf 'end %s %s\\n' \"$(date -u +%s.%N)\" '<row label>' >> \"$f\"; (exit $rc)",
    "```",
]
METRICS_WAITS = (
    "Waiting on a role launched in the background is not a launch and gets no row: wait for the runtime's notice "
    "that the role returned, and run every command launched while waiting in the wrapper above, including a read "
    "of the role's output file and any sleep or wait, so each gets a row of its own."
)
SUMMARY_SCRIPT = ROOT / "skills" / "story-to-done" / "scripts" / "metrics-summary.sh"
METRICS_END_LAUNCH = "sh '<skill dir>/scripts/metrics-summary.sh' '<metrics file>'"
METRICS_ROLE_START = (
    "f='<metrics file>'; printf 'start %s %s\\t%s\\t%s\\t%s\\n' \"$(date -u +%s.%N)\" '<row label>' "
    "'<runtime>' '<model>' '<effort>' >> \"$f\""
)
METRICS_ROLE_END = (
    "f='<metrics file>'; printf 'end %s %s\\t%s\\t%s\\n' \"$(date -u +%s.%N)\" '<row label>' "
    "'<tokens>' '<tool calls>' >> \"$f\""
)
METRICS_ROLE_ROW = (
    "Record a role row with two commands that are not launches, so neither runs in the wrapper above and "
    f"neither gets a row of its own: immediately before the launch, `{METRICS_ROLE_START}`, and when it "
    f"returns, `{METRICS_ROLE_END}`, where `<tokens>` and `<tool calls>` are written exactly as the summary's "
    "cells read: the number, `not reported`, or the number followed by ` cumulative`; a row label is unique, "
    "is neither `start` nor `end`, and no value these commands carry contains a single quote."
)
METRICS_EXTRA_WRITE = "f='<metrics file>'; printf 'extra %s\\t%s\\n' '<slug>' '<value>' >> \"$f\""
METRICS_EXTRAS_RECORD = (
    "Record every extra before the end form launches, with a command that is not a launch and gets no row, "
    f"each as one `extra <slug>\\t<value>` line written as `{METRICS_EXTRA_WRITE}`, where the slug is one of "
    "`qa-rounds`, `failed-items`, `fix-rounds`, `prs-merged`, `start`, `time-to-deployment-review`, "
    "`qa-round-durations` and `end-state`; a value is one physical line, a `;` inside a per-round value is "
    "written as `\\;`, a value the run did not observe is `not reported`, one the reference marks `not "
    "applicable` is that, and no value contains a single quote; a run that records any extra records all "
    "eight."
)
METRICS_END_INTRO = (
    f"Immediately before the summary post and the closing report, the last launch is the end form "
    f"`{METRICS_END_LAUNCH}`, where "
    "`<skill dir>` is the absolute directory your runtime loaded this skill from; it records `invocation_end` and "
    "prints the summary's table, the recorded extras and Totals from the metrics file, and it writes nothing and "
    "reports the line when an extra slug, a figure cell or a row label breaks this format, so fix the record and "
    "run it again."
)
METRICS_END_VERBATIM = (
    "The summary in the closing report is the template's heading line, a blank line, and then the end form's output "
    "copied verbatim: no line is added, reworded, or left out, and no duration, timestamp, or total is recomputed or "
    "converted."
)
METRICS_KILLED = (
    "If a command is killed before it writes its `end` line, the coordinator's very next launch, made as "
    "soon as the kill is reported, is a wrapped command whose `<command>` is `printf 'end %s %s\\n' "
    "\"$(date -u +%s.%N)\" '<killed row label>' >> '<metrics file>'`, and the recovery command gets a row "
    "of its own."
)
METRICS_CLOSING_REPORT = (
    "Give the summary, in the template `references/metrics.md` defines, in the closing report of every end "
    "state: Done, or any stop, including a stop before step 0 or before any senior engineer or QA agent is spawned."
)
METRICS_NO_LAUNCHES = (
    "The summary reads `no launches` only when the coordinator launched no role and no command; otherwise it "
    "has one row for each launch in launch order, the elapsed wall-clock, and the end state or stop reason."
)
METRICS_NO_SECRETS = (
    "The closing report contains no secrets and no local or scratch paths, including where it relays a role's "
    "finding, evidence or incidental defect, which it restates without the path."
)


def test_manifest_appends_metrics_to_story_to_done() -> None:
    entry = MANIFEST["skills"]["story-to-done"]
    assert entry.count("metrics") == 1, "story-to-done must list metrics exactly once"
    assert entry.index("metrics") == entry.index("secrets") + 1, "metrics is appended after secrets"


def test_vendored_metrics_reference_carries_the_not_reported_rule() -> None:
    vendored = ROOT / "skills" / "story-to-done" / "references" / "metrics.md"
    assert vendored.is_file(), "run scripts/vendor_shared.py to vendor references/metrics.md"
    assert "A figure the runtime does not return is `not reported`; it is never estimated or inferred." in (
        vendored.read_text()
    )


def test_metrics_section_opens_on_only_and_links_the_reference() -> None:
    text = SKILL.read_text()
    body = section(text, "Metrics").strip()
    assert body.startswith(METRICS_OPENING), "the Metrics section must open with its on-only condition"
    assert METRICS_POINTER in body.splitlines(), "the Metrics section must point at the on-only run rules"
    assert METRICS_POST in PROTOCOL.read_text().splitlines(), "the protocol must post the summary on the on path only"
    assert "](references/metrics.md)" not in section(text, "Read first")


OFF_PATH = (
    "With `metrics` off or omitted, read no metrics reference, collect no figure, create no metrics file, "
    "post no metrics comment, and add no metrics content to any brief, report, todo list, or tracker write, "
    "other than the `metrics: off` line."
)


# Every line of the skill that touches metrics, the closing report, or a tracker write, pinned exactly: adding, extending, or rewording
# metrics content anywhere (Arguments and Metrics included) fails until it is pinned here.
METRICS_WORDS = re.compile(r"metric|\bfigures?\b|token|tool.call|wall-clock|duration|usage|summar|total|cost|switch|\btim(?:e|ing|er|estamp)\w*|elapsed|clock|latency|closing report|tracker write|\bbackground\b", re.IGNORECASE)
METRICS_POINTER = (
    "The run rules for a `metrics=on` run - where the figures live, timed launches, extras, the start form, the "
    "command wrapper, the end form, the summary post, and the closing report - are in "
    "[references/metrics-protocol.md](references/metrics-protocol.md); read it with the runtime's file-read tool, "
    "which launches nothing, together with `references/metrics.md`, before the first command is launched."
)
METRICS_LINES = [
    METRICS_ROW,
    '- `metrics` is given as `metrics=on` or `metrics=off`, or in plain words: "with metrics" and "metrics on" '
    'mean on, "without metrics" and "metrics off" mean off; ask the user about any other phrasing about metrics; '
    "never guess.",
    "- Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.",
    "- " + OFF_PATH,
    "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at any stop, including one before step 0).",
    "## Metrics",
    METRICS_OPENING + " once the story ID is known: it is the single home for what a `story-to-done` run "
    "collects and reports, and this file does not restate it.",
    METRICS_POINTER,
    METRICS_USAGE,
    METRICS_NOTHING_BEFORE_START,
    METRICS_STEP0,
    # SKL-219: a checklist read-back resume is its own launch row.
    "With `metrics` on, each read-back resume is its own launch row.",
    # SKL-159: the step 4 continuation branch states the round-count and launch-row rule.
    "  The continuation does not increment the QA round count, reuses that round's scratch subdirectory and "
    "checklist, and with `metrics` on is recorded as its own launch row within that same round.",
    "Report the story identifier, its final state, the four resolved model and effort values and the "
    "`metrics: on|off` line, each PR, the number of QA rounds with the items fixed in each, where QA recorded "
    "its evidence, and any incidental defects left open.",
    BOUNDARIES_ONLY_WRITE,
    # SKL-159: the Boundaries sentence that leaves the permitted tracker write unchanged.
    "- A continuation grants no new authority: it leaves that prohibition, and the single permitted tracker "
    "write above, exactly as they are.",
]

PROTOCOL_LINES = [
    "# Metrics run rules (story-to-done)",
    "Read this only when `metrics` is on.",
    METRICS_LOCATION,
    METRICS_NEVER_NAMED,
    METRICS_TIMED_LAUNCHES,
    "  " + METRICS_LAUNCH_POINTS,
    METRICS_EXTRAS,
    METRICS_BRIEF_EXCLUSION,
    METRICS_START,
    *[line for line in METRICS_START_BLOCK if METRICS_WORDS.search(line)],
    METRICS_COMMAND_ROWS,
    METRICS_WRAPPER_INTRO,
    *[line for line in METRICS_WRAPPER_BLOCK if METRICS_WORDS.search(line)],
    METRICS_WAITS,
    METRICS_WRAPPED_WHOLE,
    METRICS_KILLED,
    METRICS_ROLE_ROW,
    METRICS_EXTRAS_RECORD,
    METRICS_END_INTRO,
    METRICS_SCRIPT_ONCE,
    METRICS_NO_EDIT,
    METRICS_END_VERBATIM,
    METRICS_CLOSING_REPORT,
    METRICS_NO_LAUNCHES,
    METRICS_POST,
    METRICS_POST_BODY,
    METRICS_BODY_BYTES,
    METRICS_END_IS_LAST,
    METRICS_POST_ITEM,
    METRICS_LINEAR_COMMANDS,
    METRICS_READ_BACK_RESULT,
    METRICS_READ_BACK,
    METRICS_POST_NOT_A_LAUNCH,
    METRICS_POST_INTERFACE,
    METRICS_POST_DENIED,
    METRICS_READ_BACK_FAILED,
    METRICS_READ_BACK_FINAL,
    METRICS_RESUMED,
    METRICS_POST_NO_SECRETS,
    METRICS_ONLY_WRITE,
    METRICS_NO_SECRETS,
]


def test_metrics_off_changes_nothing_but_the_metrics_line() -> None:
    text = SKILL.read_text()
    assert OFF_PATH in " ".join(section(text, "Arguments").split())
    body = text.split("\n---\n", 1)[1]
    found = [line for line in body.splitlines() if METRICS_WORDS.search(line)]
    assert found == METRICS_LINES, "metrics content outside the pinned switch, line, and on-only lines"
    assert not METRICS_WORDS.search(text.split("\n---\n", 1)[0]), "the front matter adds metrics content"
    proto = [line for line in PROTOCOL.read_text().splitlines() if METRICS_WORDS.search(line)]
    assert proto == PROTOCOL_LINES, "metrics content in the protocol reference outside the pinned lines"


def test_arguments_prose_count_matches_the_table() -> None:
    body = section(SKILL.read_text(), "Arguments")
    rows = [line for line in body.splitlines() if line.startswith("| `")]
    assert len(rows) == 5 and "Five arguments are optional" in body


def readme_row() -> str:
    rows = [
        line
        for line in (ROOT / "README.md").read_text().splitlines()
        if line.startswith("| [`story-to-done`](skills/story-to-done/SKILL.md) |")
    ]
    assert rows, "README Skills table is missing the story-to-done row"
    return rows[0]


def test_readme_row_names_the_metrics_switch_and_its_default() -> None:
    row = readme_row()
    assert "a `metrics` switch, `off` by default" in row


def metrics_section() -> str:
    """The Metrics rules: the SKILL.md stub plus the protocol reference it points at."""
    return section(SKILL.read_text(), "Metrics") + "\n" + PROTOCOL.read_text()


def metrics_body() -> str:
    return " ".join(metrics_section().split())


def test_metrics_start_is_timestamped_when_the_switch_resolves() -> None:
    body = metrics_body()
    assert METRICS_START in body


def metrics_blocks() -> list[list[str]]:
    lines = metrics_section().splitlines()
    fences = [i for i, line in enumerate(lines) if line.startswith("```")]
    return [lines[a : b + 1] for a, b in zip(fences[::2], fences[1::2])]


def runtimes_scratch_creation() -> str:
    text = (ROOT / "skills" / "story-to-done" / "references" / "runtimes.md").read_text()
    blocks = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
    creation = [block for block in blocks if 'scratch="$(mktemp -d' in block]
    assert len(creation) == 1, "references/runtimes.md must give exactly one scratch-directory creation"
    return "\n".join(line.strip() for line in creation[0].splitlines())


def start_form(creation: str) -> str:
    blocks = metrics_blocks()
    assert blocks[0] == METRICS_START_BLOCK, "the start form must be the first pinned block"
    return "\n".join(blocks[0][1:-1]).replace("<scratch creation>", creation)


def test_the_start_form_creates_the_scratch_directory_and_times_itself(tmp_path: Path) -> None:
    base = tmp_path / "base"
    script = f"scratch_base='{quoted(base)}'\n" + start_form(runtimes_scratch_creation())
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True)
    assert len(result.stdout.splitlines()) == 1, "the start form prints the scratch path once"
    scratch = Path(result.stdout.strip())
    assert scratch.parent == base and scratch.is_dir(), "the start form creates the scratch directory"
    rows = read_rows(scratch / "metrics.txt")
    assert [(kind, label) for kind, _, label in rows] == [("start", "start"), ("end", "start")]
    assert rows[1][1] >= rows[0][1] > 1_000_000_000, "the start row has its own ordered start and end timestamps"


def quoted(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def test_a_handed_directory_with_a_single_quote_is_timed(tmp_path: Path) -> None:
    handed = tmp_path / "team's work"
    handed.mkdir()
    subprocess.run(["bash", "-c", start_form(f"scratch='{quoted(handed)}'")], check=True)
    record = handed / "metrics.txt"
    assert subprocess.run(["bash", "-c", wrapper_script(record, "true", "probe", quote=True)]).returncode == 0
    assert [(kind, label) for kind, _, label in read_rows(record)] == [
        ("start", "start"), ("end", "start"), ("start", "probe"), ("end", "probe")
    ]


def test_a_start_form_that_cannot_record_its_row_fails(tmp_path: Path) -> None:
    handed = tmp_path / "not a directory"
    handed.write_text("")
    script = start_form(f"scratch='{quoted(handed)}'")
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert "metrics.txt" in result.stderr, "the start row's write is what fails"
    assert result.returncode != 0, "a start form that writes no start row must exit non-zero"


def test_each_coordinator_command_gets_a_row_with_its_usage() -> None:
    assert METRICS_COMMAND_ROWS in metrics_body()


# SKL-96: the engineer and QA launch rows, the extras' collection points, the metrics-file location,
# the never-named statement, and the brief independence rules.


def test_engineer_and_qa_launches_are_timed_and_recorded_as_one_row_each() -> None:
    body = metrics_body()
    assert METRICS_TIMED_LAUNCHES in body, "the launch timing and its row figures are not stated"
    assert METRICS_LAUNCH_POINTS in body, "which launches are rows is not stated"


def test_each_story_to_done_extra_is_taken_at_the_step_that_observes_it() -> None:
    assert METRICS_EXTRAS in metrics_body(), "an extra's collection point is missing"


# SKL-159: a round may hold more than one launch row, so the launch points and the
# qa-round-durations derivation both have to name the continuation.
OLD_LAUNCH_POINTS = "each QA round is one launch in step 3"
OLD_QA_ROUND_DURATIONS = (
    "QA rounds** at each spawn in step 3, each with its **duration** copied from that round's launch row"
)


def test_the_metrics_launch_points_cover_a_same_round_continuation() -> None:
    body = metrics_body()
    assert METRICS_LAUNCH_POINTS in body, "which launches are rows is not stated"
    assert OLD_LAUNCH_POINTS not in body, "the one-launch-per-round sentence is replaced, not kept beside it"
    assert (
        "a continuation of that round under step 4 is a further launch row within the same round" in body
    ), "a continuation must be stated as its own launch row inside the same round"


def test_the_qa_round_durations_extra_derives_a_multi_row_round_from_its_rows() -> None:
    body = metrics_body()
    assert OLD_QA_ROUND_DURATIONS not in body, "the one-row duration sentence is replaced, not kept beside it"
    assert (
        "the sum of that round's launch rows' recorded durations, each row's figure taken as returned" in body
    ), "a round holding more than one launch row must derive its duration as the sum of its rows"


def test_the_metrics_file_lives_in_the_session_scratch_directory_outside_every_role_subdirectory() -> None:
    assert METRICS_LOCATION in metrics_body()


def test_the_metrics_file_is_never_named_in_a_brief() -> None:
    assert METRICS_NEVER_NAMED in metrics_body()


# A brief leak can be phrased without the word `metrics`, so the two brief sections are scanned for the
# vocabulary a cost figure or a comparison with another launch would use.
BRIEF_LEAK = re.compile(
    r"metric|\bfigures?\b|token|tool.call|wall-clock|duration|elapsed|usage|summar|total|cost|switch"
    r"|\btim(?:e|ing|er|estamp)\w*|\bhow long\b|\btook\b|\bprevious\b"
    r"|\bclock\b|latency|closing report|tracker write",
    re.IGNORECASE,
)


def test_no_engineer_or_qa_brief_carries_metrics_or_another_roles_figures() -> None:
    assert METRICS_BRIEF_EXCLUSION in metrics_body()
    text = SKILL.read_text()
    for heading in ("2. Senior engineer: implement to deployment review", "3. QA agent: verify the deployed story"):
        offenders = [line for line in section(text, heading).splitlines() if BRIEF_LEAK.search(line)]
        assert not offenders, f"{heading} carries metrics or another launch's figures into the brief: {offenders}"


def test_step_0_seeds_the_collect_and_post_metrics_items_only_when_the_switch_is_on() -> None:
    body = " ".join(section(SKILL.read_text(), "0. Track everything on a todo list").split())
    assert METRICS_STEP0 in body, "step 0 does not seed the collect and post metrics items"
    assert body.index("Seed it with at least") < body.index(METRICS_STEP0), (
        "the collect metrics item must follow the shared seed sentence as an on-only sentence of its own"
    )
    assert METRICS_STEP0.startswith("With `metrics` on, "), "the seed item must apply only when the switch is on"


def test_step_0_adds_no_unconditional_collect_metrics_instruction() -> None:
    body = " ".join(section(SKILL.read_text(), "0. Track everything on a todo list").split())
    assert METRICS_STEP0 in body
    # SKL-219: the read-back launch-row sentence is on-only too, so it is not an unconditional instruction.
    read_back_row = "With `metrics` on, each read-back resume is its own launch row."
    assert read_back_row in body
    rest = " ".join(body.replace(METRICS_STEP0, "").replace(read_back_row, "").split()).lower()
    for phrase in ("metric", "seed the same", "same item", " off "):
        assert phrase not in rest, f"step 0 adds an unconditional collect-metrics instruction: {phrase!r}"


def test_every_launch_runs_in_the_start_form_or_the_timing_wrapper() -> None:
    body = metrics_body()
    assert METRICS_WRAPPER_INTRO in body
    assert METRICS_END_INTRO in body
    assert METRICS_END_VERBATIM in body
    assert METRICS_KILLED in body


def skill_wrapper() -> str:
    blocks = metrics_blocks()
    assert len(blocks) == 2, "the Metrics section gives exactly the start form and one wrapper"
    assert blocks[1] == METRICS_WRAPPER_BLOCK, "the timing wrapper must be the pinned block"
    return "\n".join(blocks[1][1:-1])


def wrapper_script(record: Path, command: str, label: str, quote: bool = False) -> str:
    script = skill_wrapper().replace("<command>", command, 1)
    return script.replace("<row label>", label).replace("<metrics file>", quoted(record) if quote else str(record))


def run_wrapper(record: Path, command: str, label: str = "probe") -> int:
    return subprocess.run(["bash", "-c", wrapper_script(record, command, label)]).returncode


def read_rows(record: Path) -> list[tuple[str, float, str]]:
    rows = [line.split(" ", 2) for line in record.read_text().splitlines()]
    return [(kind, float(stamp), label) for kind, stamp, label in rows]


def test_the_timing_wrapper_takes_distinct_start_and_end_timestamps_around_the_command(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    for label in ("start command", "probe"):
        assert run_wrapper(record, "sleep 0.2", label) == 0
    rows = read_rows(record)
    assert [(kind, label) for kind, _, label in rows] == [
        ("start", "start command"), ("end", "start command"), ("start", "probe"), ("end", "probe")
    ], "each launch writes a start line before its command and an end line after it"
    for (_, start, _), (_, end, _) in (rows[0:2], rows[2:4]):
        assert end - start >= 0.2, "the start and end timestamps must bracket the command"


def test_the_timing_wrapper_keeps_the_command_exit_status(tmp_path: Path) -> None:
    cases = (("true", 0), ("false", 1), ("sh -c 'exit 7'", 7), ("exit 3", 3), ("set -e; false; true", 1))
    record = tmp_path / "metrics.txt"
    for count, (command, status) in enumerate(cases, start=1):
        assert run_wrapper(record, command) == status, f"{command} must keep exit status {status}"
        assert [kind for kind, _, _ in read_rows(record)][-2:] == ["start", "end"], f"{command}: both lines"
        assert len(read_rows(record)) == 2 * count


def test_no_command_can_lose_or_corrupt_its_row(tmp_path: Path) -> None:
    (tmp_path / "a b").mkdir()
    record = tmp_path / "a b" / "metrics.txt"
    commands = [
        "true # a trailing comment",
        "true;",
        "sleep 0.1 & wait",
        "s=0; f=/dev/null; rc=0",
        "date() { printf 0; }; printf() { :; }",
        "PATH=/nonexistent",
        "exec true",
        "cd /",
        "trap 'exit 9' EXIT",
    ]
    for count, command in enumerate(commands, start=1):
        run_wrapper(record, command, "row $(printf injected) <command>")
        rows = read_rows(record)
        assert len(rows) == 2 * count, f"{command}: one start and one end line per launch"
        (start_kind, start, start_label), (end_kind, end, end_label) = rows[-2:]
        assert (start_kind, end_kind) == ("start", "end"), f"{command}: start line, then end line"
        assert start_label == end_label == "row $(printf injected) <command>", f"{command}: the label is literal"
        assert end >= start > 1_000_000_000, f"{command}: both timestamps are real and ordered"


def test_a_failed_metrics_write_shows_an_error_and_keeps_the_exit_status(tmp_path: Path) -> None:
    blocker = tmp_path / "not a directory"
    blocker.write_text("")
    record = blocker / "metrics.txt"
    for command, status in (("true", 0), ("exit 4", 4)):
        script = wrapper_script(record, command, "probe")
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        assert result.returncode == status, f"{command}: the wrapper keeps the command's exit status"
        errors = [line for line in result.stderr.splitlines() if str(record) in line]
        assert len(errors) == 2, f"{command}: the failed start and end writes each show an error naming the file"


def test_the_metrics_section_says_how_a_role_row_is_recorded() -> None:
    body = metrics_body()
    assert METRICS_ROLE_ROW in body, "the role row's own start and end lines are not stated"
    assert METRICS_EXTRAS_RECORD in body, "the extras' recording lines are not stated"


def test_the_end_form_runs_the_summary_script() -> None:
    assert METRICS_END_INTRO in metrics_body()
    assert SUMMARY_SCRIPT.is_file(), "the end form's script must ship with the skill"


def end_form(record: Path) -> str:
    skill_dir = quoted(SUMMARY_SCRIPT.parent.parent)
    return METRICS_END_LAUNCH.replace("<skill dir>", skill_dir).replace("<metrics file>", quoted(record))


AWKS = sorted({os.path.realpath(path) for name in ("awk", "gawk", "mawk", "nawk") if (path := shutil.which(name))})


def run_end_form(record: Path, awk: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "awk-bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "awk"
    link.unlink(missing_ok=True)
    link.symlink_to(awk)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True, env=env)


def recorded(record: Path) -> dict[tuple[str, str], str]:
    rows = {}
    for line in record.read_text().splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[0] in ("start", "end"):
            rows[(parts[0], parts[2].split("\t", 1)[0])] = parts[1]
    return rows


def seconds(start: str, end: str) -> str:
    return f"{Decimal(end) - Decimal(start):.9f}s"


def expected_summary(rows: list[tuple[str, str]], start: str, end: str, elapsed: str) -> str:
    table = [
        "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |",
        "|---|---|---|---|---|---|---|",
        *[f"| {label} | command | not set | not set | {duration} | not reported | not reported |" for label, duration in rows],
    ]
    totals = [
        "Totals",
        f"- Elapsed wall-clock: {elapsed} ({start} to {end})",
        f"- Tokens: not reported [partial: {len(rows)} not reported, 0 cumulative]",
        f"- Tool calls: not reported [partial: {len(rows)} not reported, 0 cumulative]",
    ]
    return "\n".join([*table, "", *totals]) + "\n"


@pytest.mark.parametrize("awk", AWKS)
def test_the_end_form_times_itself_last_and_prints_the_summary(tmp_path: Path, awk: str) -> None:
    handed = tmp_path / "team's session"
    handed.mkdir()
    subprocess.run(["bash", "-c", start_form(f"scratch='{quoted(handed)}'")], check=True)
    record = handed / "metrics.txt"
    for label in ("read story state", "probe"):
        assert subprocess.run(["bash", "-c", wrapper_script(record, "sleep 0.1", label, quote=True)]).returncode == 0
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    assert [(kind, label) for kind, _, label in read_rows(record)][-2:] == [("start", "end"), ("end", "end")]
    labels = ("start", "read story state", "probe", "end")
    rows = [(label, seconds(stamps["start", label], stamps["end", label])) for label in labels]
    assert all(Decimal(duration[:-1]) > 0 for _, duration in rows), "every row has distinct start and end timestamps"
    start, end = stamps["start", "start"], stamps["end", "end"]
    assert result.stdout == expected_summary(rows, start, end, seconds(start, end)), (
        "the end form prints every row, the exact elapsed, the recorded timestamps, and the partial note"
    )


@pytest.mark.parametrize("awk", AWKS)
def test_the_end_form_names_lost_rows(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.722929459 start\n"
        "end 1793218211.000000001 start\n"
        "start 1793218212.5 killed\n"
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [("start", "0.277070542s"), ("killed", "lost"), ("end", seconds(stamps["start", "end"], end))]
    assert result.stdout == expected_summary(rows, "1793218210.722929459", end, seconds("1793218210.722929459", end))


@pytest.mark.parametrize("awk", AWKS)
def test_a_run_that_stops_after_the_start_form_has_two_rows(tmp_path: Path, awk: str) -> None:
    subprocess.run(["bash", "-c", start_form(f"scratch='{quoted(tmp_path)}'")], check=True)
    record = tmp_path / "metrics.txt"
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    rows = [(label, seconds(stamps["start", label], stamps["end", label])) for label in ("start", "end")]
    start, end = stamps["start", "start"], stamps["end", "end"]
    assert result.stdout == expected_summary(rows, start, end, seconds(start, end))


# SKL-96 round 2: a role launch's row carries its runtime, model and effort on its start line and its usage
# cells on its end line, the extras are recorded as `extra` lines, and the end form prints both.

EXTRA_LABELS = {
    "qa-rounds": "QA rounds",
    "failed-items": "Failed items",
    "fix-rounds": "Fix rounds",
    "prs-merged": "PRs merged",
    "start": "Start",
    "time-to-deployment-review": "Time to deployment review",
    "qa-round-durations": "QA round durations",
    "end-state": "End state",
}


def row_line(kind: str, stamp: str, label: str, *fields: str) -> str:
    line = f"{kind} {stamp} {label}"
    return (f"{line}\t" + "\t".join(fields) if fields else line) + "\n"


def role_start(stamp: str, label: str, runtime: str, model: str, effort: str) -> str:
    return row_line("start", stamp, label, runtime, model, effort)


def role_end(stamp: str, label: str, tokens: str, calls: str) -> str:
    return row_line("end", stamp, label, tokens, calls)


def extra_line(slug: str, value: str) -> str:
    return f"extra {slug}\t{value}\n"


ROLE_PLACEHOLDERS = {
    "label": "<row label>",
    "runtime": "<runtime>",
    "model": "<model>",
    "effort": "<effort>",
    "tokens": "<tokens>",
    "calls": "<tool calls>",
}


def documented(command: str, record: Path, **values: str) -> str:
    """Fill the SKILL's documented command with real values, so the test runs what the skill tells a coordinator."""
    filled = command.replace("<metrics file>", str(record))
    for name, value in values.items():
        assert ROLE_PLACEHOLDERS[name] in filled, f"{command} carries no {ROLE_PLACEHOLDERS[name]}"
        filled = filled.replace(ROLE_PLACEHOLDERS[name], value)
    return filled


def summary(rows: list[tuple[str, ...]], totals: tuple[str, str], start: str | None, end: str,
            extras: list[tuple[str, str]] | None = None) -> str:
    table = [
        "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |",
        "|---|---|---|---|---|---|---|",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]
    lines = [*table, ""]
    for slug, value in extras or []:
        lines.append(f"{EXTRA_LABELS[slug]}: {value}")
    if extras:
        lines.append("")
    lines.append("Totals")
    if start is None:
        lines.append(f"- Elapsed wall-clock: not reported (not recorded to {end})")
    else:
        lines.append(f"- Elapsed wall-clock: {seconds(start, end)} ({start} to {end})")
    lines.extend([f"- Tokens: {totals[0]}", f"- Tool calls: {totals[1]}"])
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("awk", AWKS)
def test_a_role_row_carries_its_runtime_model_effort_and_usage(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + role_start("1793218300.000000000", "senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high")
        + role_end("1793218900.000000000", "senior-engineer-1", "120000", "41")
        + role_start("1793219000.000000000", "qa-agent-round-1", "opencode", "deepseek/deepseek-flash", "high")
        + role_end("1793219200.000000000", "qa-agent-round-1", "not reported", "not reported")
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [
        ("start", "command", "not set", "not set", "0.100000000s", "not reported", "not reported"),
        ("senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high", "600.000000000s", "120000", "41"),
        ("qa-agent-round-1", "opencode", "deepseek/deepseek-flash", "high", "200.000000000s", "not reported", "not reported"),
        ("end", "command", "not set", "not set", seconds(stamps["start", "end"], end), "not reported", "not reported"),
    ]
    totals = ("120000 [partial: 3 not reported, 0 cumulative]", "41 [partial: 3 not reported, 0 cumulative]")
    assert result.stdout == summary(rows, totals, "1793218210.500000000", end)


@pytest.mark.parametrize("awk", AWKS)
def test_the_documented_role_row_commands_record_what_the_summary_then_shows(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    start = documented(METRICS_ROLE_START, record, label="engineer 1", runtime="opencode",
                       model="vendor/model%x|1", effort="high")
    end = documented(METRICS_ROLE_END, record, label="engineer 1", tokens="120000", calls="41 cumulative")
    for command in (start, "sleep 0.05", end):
        assert subprocess.run(["bash", "-c", command], capture_output=True, text=True).returncode == 0
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    assert stamps["start", "engineer 1"] and stamps["end", "engineer 1"]
    rows = [
        ("engineer 1", "opencode", "vendor/model%x\\|1", "high", seconds(stamps["start", "engineer 1"], stamps["end", "engineer 1"]), "120000", "41 cumulative"),
        ("end", "command", "not set", "not set", seconds(stamps["start", "end"], stamps["end", "end"]), "not reported", "not reported"),
    ]
    totals = ("120000 [partial: 1 not reported, 0 cumulative]", "not reported [partial: 1 not reported, 1 cumulative]")
    assert result.stdout == summary(rows, totals, None, stamps["end", "end"])


@pytest.mark.parametrize("awk", AWKS)
def test_a_cumulative_figure_is_marked_and_excluded_per_figure(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + role_start("1793218300.000000000", "senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high")
        + role_end("1793218900.000000000", "senior-engineer-1", "260000 cumulative", "5")
        + role_start("1793219000.000000000", "qa-agent-round-1", "opencode", "deepseek/deepseek-flash", "high")
        + role_end("1793219200.000000000", "qa-agent-round-1", "not reported", "not reported")
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [
        ("start", "command", "not set", "not set", "0.100000000s", "not reported", "not reported"),
        ("senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high", "600.000000000s", "260000 cumulative", "5"),
        ("qa-agent-round-1", "opencode", "deepseek/deepseek-flash", "high", "200.000000000s", "not reported", "not reported"),
        ("end", "command", "not set", "not set", seconds(stamps["start", "end"], end), "not reported", "not reported"),
    ]
    totals = ("not reported [partial: 3 not reported, 1 cumulative]", "5 [partial: 3 not reported, 0 cumulative]")
    assert result.stdout == summary(rows, totals, "1793218210.500000000", end)


@pytest.mark.parametrize("awk", AWKS)
def test_a_role_row_missing_its_fields_says_not_reported_not_command(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\n"
        + role_start("1793218300.000000000", "engineer", "", "", "")
        + role_end("1793218400.000000000", "engineer", "10", "2")
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert "| engineer | not reported | not reported | not reported | 100.000000000s | 10 | 2 |" in result.stdout


@pytest.mark.parametrize("awk", AWKS)
def test_a_blank_line_is_not_a_row(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n\n"
        + role_start("1793218300.000000000", "engineer", "opencode", "m", "high")
        + role_end("1793218400.000000000", "engineer", "10", "2")
        + "injected continuation line\n"
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    rows = [line for line in result.stdout.splitlines() if line.startswith("| ")][1:]
    assert [row.split(" | ")[0] for row in rows] == ["| start", "| engineer", "| end"], (
        "a blank line or a stray continuation line must not become a row"
    )
    assert "lost" not in result.stdout


@pytest.mark.parametrize("awk", AWKS)
def test_a_run_without_an_invocation_start_says_not_reported(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(role_start("1793218300.000000000", "engineer", "opencode", "m", "high")
                      + role_end("1793218400.000000000", "engineer", "10", "2"))
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    assert f"- Elapsed wall-clock: not reported (not recorded to {stamps['end', 'end']})" in result.stdout


@pytest.mark.parametrize("awk", AWKS)
def test_the_recorded_extras_print_one_line_each_in_the_reference_order(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    values = {
        "qa-rounds": "2",
        "failed-items": "round 1: 2; round 2: 0",
        "fix-rounds": "1",
        "prs-merged": "2",
        "start": "In Progress, implementation ran",
        "time-to-deployment-review": "1h 12m",
        "qa-round-durations": "round 1: 200.000000000s; round 2: 90.000000000s",
        "end-state": "In Deployment Review",
    }
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + "".join(extra_line(slug, values[slug]) for slug in reversed(list(EXTRA_LABELS)))
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [
        ("start", "command", "not set", "not set", "0.100000000s", "not reported", "not reported"),
        ("end", "command", "not set", "not set", seconds(stamps["start", "end"], end), "not reported", "not reported"),
    ]
    totals = ("not reported [partial: 2 not reported, 0 cumulative]",) * 2
    extras = [(slug, values[slug]) for slug in EXTRA_LABELS]
    assert result.stdout == summary(rows, totals, "1793218210.500000000", end, extras)


@pytest.mark.parametrize("awk", AWKS)
def test_the_documented_extra_command_writes_a_line_the_summary_prints(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    command = METRICS_EXTRA_WRITE.replace("<metrics file>", str(record))
    command = command.replace("<slug>", "failed-items").replace("<value>", "round 1: 2|3; round 2: 0")
    assert subprocess.run(["bash", "-c", command], capture_output=True, text=True).returncode == 0
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert "Failed items: round 1: 2|3; round 2: 0\n" in result.stdout, (
        "an extra value is not a table cell, so its pipes print as written"
    )


def test_the_extra_labels_and_their_order_match_the_vendored_reference() -> None:
    text = (ROOT / "skills" / "story-to-done" / "references" / "metrics.md").read_text()
    block = text.split("### `story-to-done` extras", 1)[1].split("\n### ", 1)[0]
    assert re.findall(r"^- \*\*(.+?):\*\*", block, re.MULTILINE) == list(EXTRA_LABELS.values())


@pytest.mark.parametrize("awk", AWKS)
def test_an_end_line_without_its_start_line_is_lost_not_a_fabricated_duration(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text("end 1793218500.000000000 orphan\t5\t6\n")
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert "| orphan | not reported | not reported | not reported | lost | 5 | 6 |" in result.stdout


def test_a_reused_role_label_fails_the_end_form(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        role_start("1793218300.000000000", "qa-round-1", "opencode", "m", "high")
        + role_end("1793218400.000000000", "qa-round-1", "1", "2")
        + role_start("1793218500.000000000", "qa-round-1", "opencode", "m", "high")
        + role_end("1793218650.000000000", "qa-round-1", "3", "4")
    )
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode != 0 and result.stdout == "", "a reused label must not print a summary"
    assert "the label qa-round-1 is used twice" in result.stderr
    lines = record.read_text().splitlines(keepends=True)
    for later in (2, 3):
        lines[later] = lines[later].replace(" qa-round-1\t", " qa-round-2\t", 1)
    record.write_text("".join(lines))
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode == 0 and result.stderr == "", "relabelling the later row recovers the record"
    assert "| qa-round-1 | opencode | m | high | 100.000000000s | 1 | 2 |" in result.stdout
    assert "| qa-round-2 | opencode | m | high | 150.000000000s | 3 | 4 |" in result.stdout


def test_a_role_row_may_not_take_the_reserved_start_or_end_label(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(role_start("1793218300.000000000", "start", "opencode", "m", "high"))
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode != 0 and result.stdout == ""
    assert "the reserved label start" in result.stderr


def test_a_command_row_labelled_end_fails_the_end_form_and_is_relabelled(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218100.000000000 start\nend 1793218101.000000000 start\n"
        "start 1793218102.000000000 end\nend 1793218110.000000000 end\n"
    )
    before = record.read_text()
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode != 0 and result.stdout == "", "a command row labelled end must not print a summary"
    assert "the reserved label end" in result.stderr
    assert record.read_text() == before, "an invalid-record report leaves the metrics file as it was"
    record.write_text(before.replace(" end\n", " push-branch\n"))
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode == 0 and result.stderr == "", "relabelling the command row recovers the record"
    assert "| push-branch | command | not set | not set | 8.000000000s | not reported | not reported |" in result.stdout


def test_a_role_row_labelled_end_survives_the_cleanup_and_is_relabelled(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        role_start("1793218300.000000000", "eng", "opencode", "m", "high")
        + role_end("1793218400.000000000", "eng", "1", "2")
        + role_start("1793218500.000000000", "end", "opencode", "m", "high")
        + role_end("1793218650.000000000", "end", "3", "4")
    )
    before = record.read_text()
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode != 0 and result.stdout == ""
    assert "the reserved label end" in result.stderr
    assert record.read_text() == before, "an invalid-record report leaves the metrics file as it was"
    lines = before.splitlines(keepends=True)
    for later in (2, 3):
        lines[later] = lines[later].replace(" end\t", " qa-round-1\t", 1)
    record.write_text("".join(lines))
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode == 0 and result.stderr == "", "relabelling the reserved row recovers the record"
    assert "| qa-round-1 | opencode | m | high | 150.000000000s | 3 | 4 |" in result.stdout


@pytest.mark.parametrize("awk", AWKS)
def test_an_empty_extra_value_reads_not_reported(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(extra_line("fix-rounds", ""))
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    lines = [line for line in result.stdout.splitlines() if ": " in line and not line.startswith("- ")]
    assert lines == [f"{label}: not reported" for label in EXTRA_LABELS.values()], (
        "recording one extra records all eight, and an empty value reads not reported"
    )


def test_a_figure_outside_the_cell_grammar_fails_the_end_form(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(role_start("1793218300.000000000", "eng", "opencode", "m", "high")
                      + role_end("1793218400.000000000", "eng", "1,204", "2"))
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode != 0 and result.stdout == "", "a bad cell must not print a summary"
    assert "the figure 1,204" in result.stderr


def test_an_unknown_extra_slug_fails_the_end_form(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(extra_line("qa-round", "2"))
    result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
    assert result.returncode != 0 and result.stdout == "", "an unknown slug must not print a summary"
    assert "unknown extra slug qa-round" in result.stderr


@pytest.mark.parametrize("awk", AWKS)
def test_an_extra_keeps_its_escaped_semicolon_and_a_pipe_is_escaped_in_the_cells(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + role_start("1793218300.000000000", "engineer|one", "opencode", "m", "high")
        + role_end("1793218400.000000000", "engineer|one", "1", "2")
        + extra_line("failed-items", "round 1: a\\;b")
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert "| engineer\\|one | opencode | m | high | 100.000000000s | 1 | 2 |" in result.stdout
    assert "Failed items: round 1: a\\;b\n" in result.stdout


def end_form_program() -> str:
    script = SUMMARY_SCRIPT.read_text()
    return script[script.rindex("awk '") + 5 : script.rindex("' \"$1\"")]


def test_the_end_form_works_out_durations_exactly() -> None:
    assert AWKS, "no awk to run the end form with"
    stamps = "start 1793218198.999999999 start\nend 1793218200.000000001 start\nstart 1793218225.1 end\nend 1793218225.2 end\n"
    rows = [("start", "1.000000002s"), ("end", "0.100000000s")]
    expected = expected_summary(rows, "1793218198.999999999", "1793218225.2", "26.200000001s")
    for awk in AWKS:
        result = subprocess.run([awk, end_form_program()], input=stamps, capture_output=True, text=True, check=True)
        assert result.stdout == expected, awk


def end_form_after_failed_print(record: Path, awk: str, tmp_path: Path) -> None:
    bin_dir = tmp_path / "awk-bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "awk"
    link.unlink(missing_ok=True)
    link.symlink_to(awk)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    failed = subprocess.run(["bash", "-c", end_form(record) + " >/dev/full"], capture_output=True, text=True, env=env)
    assert failed.returncode != 0, "an end form whose summary cannot be written exits nonzero"


@pytest.mark.skipif(not Path("/dev/full").exists(), reason="needs /dev/full to make the summary write fail")
@pytest.mark.parametrize("awk", AWKS)
@pytest.mark.parametrize("left", ["whole row", "start line only", "start line and a cut end line", "cut start line"])
def test_restoring_the_file_read_before_a_failed_end_form_keeps_one_invocation_end(tmp_path: Path, awk: str, left: str) -> None:
    assert METRICS_SCRIPT_ONCE in metrics_lines()
    record = tmp_path / "metrics.txt"
    before = "start 1793218198.0 start\nend 1793218199.0 start\n"
    record.write_text(before)
    end_form_after_failed_print(record, awk, tmp_path)
    whole = record.read_text()
    assert [line.split(" ")[0] + " " + line.split(" ")[2] for line in whole.splitlines()[-2:]] == ["start end", "end end"]
    start_line = whole.splitlines(keepends=True)[-2]
    record.write_text(before + {
        "whole row": whole[len(before):],
        "start line only": start_line,
        "start line and a cut end line": start_line + "end 17932",
        "cut start line": start_line[:9],
    }[left])
    assert record.read_text() != before
    record.write_text(before)
    rerun = run_end_form(record, awk, tmp_path)
    assert rerun.returncode == 0 and rerun.stderr == ""
    assert [(kind, label) for kind, _, label in read_rows(record)] == [
        ("start", "start"), ("end", "start"), ("start", "end"), ("end", "end")
    ], "the record keeps one invocation_end"
    stamps = recorded(record)
    start, end = stamps["start", "start"], stamps["end", "end"]
    rows = [(label, seconds(stamps["start", label], stamps["end", label])) for label in ("start", "end")]
    assert rerun.stdout == expected_summary(rows, start, end, seconds(start, end))


def test_compatibility_names_jq_for_the_linear_cli_read_back() -> None:
    compatibility = next(line for line in SKILL.read_text().splitlines() if line.startswith("compatibility:"))
    assert "the linear CLI (schpet/linear-cli) with jq, or the Linear MCP server" in compatibility
    assert "| jq -e " in METRICS_LINEAR_COMMANDS


def test_an_end_form_that_cannot_record_its_row_fails(tmp_path: Path) -> None:
    blocker = tmp_path / "not a directory"
    blocker.write_text("")
    read_only = tmp_path / "metrics.txt"
    read_only.write_text("start 1793218198.0 start\nend 1793218199.0 start\n")
    read_only.chmod(0o444)
    for record in (blocker / "metrics.txt", read_only):
        result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
        assert "metrics.txt" in result.stderr and result.stdout == "", "a failed end form prints no summary"
        assert result.returncode != 0, "an end form that writes no row must exit non-zero"


def test_a_killed_command_keeps_its_start_line(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    process = subprocess.Popen(["bash", "-c", wrapper_script(record, "sleep 30", "killed")], start_new_session=True)
    deadline = time.monotonic() + 10
    while not (record.exists() and record.read_text().endswith("\n")) and time.monotonic() < deadline:
        time.sleep(0.05)
    os.killpg(process.pid, signal.SIGKILL)
    process.wait()
    assert [kind for kind, _, _ in read_rows(record)] == ["start"], "the start line is written before the command"
    recoveries = re.findall(r"`(printf 'end [^`]*)`", metrics_body())
    assert len(recoveries) == 1, "the Metrics section must give exactly one recovery command"
    recovery = recoveries[0].replace("<killed row label>", "killed").replace("<metrics file>", str(record))
    assert run_wrapper(record, recovery, "recovery") == 0
    assert [(kind, label) for kind, _, label in read_rows(record)] == [
        ("start", "killed"), ("start", "recovery"), ("end", "killed"), ("end", "recovery")
    ], "the recovery writes the killed row's end line and gets a row of its own"


def test_closing_report_of_every_end_state_gives_the_summary_in_the_template() -> None:
    assert METRICS_CLOSING_REPORT in metrics_body()


def test_summary_reads_no_launches_only_without_any_launch() -> None:
    assert METRICS_NO_LAUNCHES in metrics_body()


def metrics_lines() -> list[str]:
    return metrics_section().splitlines()


def test_the_old_no_post_and_no_tracker_write_sentences_are_gone() -> None:
    text = SKILL.read_text()
    assert REMOVED_NO_POST not in text, "the sentence that forbids the summary post is still in the skill"
    assert REMOVED_NO_TRACKER_WRITE not in text, "the sentence that forbids every tracker write is still in the skill"


def test_the_summary_is_posted_as_one_comment_at_the_end_of_every_invocation_with_a_known_story() -> None:
    assert METRICS_POST in metrics_lines(), "the end-of-invocation post on every end state is not stated"


def test_the_post_follows_the_end_form_and_its_body_is_the_heading_and_the_end_form_output() -> None:
    lines = metrics_lines()
    assert METRICS_POST_BODY in lines, "the post's place and its verbatim body are not stated"
    assert lines.index(METRICS_END_INTRO) < lines.index(METRICS_POST_BODY), "the post is stated before the end form"


def test_the_comment_is_read_back_and_named_in_the_closing_report() -> None:
    assert METRICS_READ_BACK in metrics_lines(), "the read-back, the closing-report repeat or the named comment is missing"
    assert METRICS_READ_BACK_RESULT in metrics_lines()


def test_the_post_and_its_read_back_are_no_launch_and_take_no_second_invocation_end() -> None:
    assert METRICS_POST_NOT_A_LAUNCH in metrics_lines()
    assert METRICS_WRAPPER_INTRO in metrics_body(), "the wrapper sentence does not except the post and its read-back"
    assert METRICS_SCRIPT_ONCE in metrics_lines()


def test_the_post_uses_the_step_1_tracker_interface_once() -> None:
    assert METRICS_POST_INTERFACE in metrics_lines()


def test_a_denied_or_unavailable_post_is_named_in_the_closing_report_with_no_other_tool() -> None:
    assert METRICS_POST_DENIED in metrics_lines()


def test_a_failed_read_back_is_named_and_never_reposted() -> None:
    assert METRICS_READ_BACK_FAILED in metrics_lines()
    assert METRICS_READ_BACK_FINAL in metrics_lines()


def test_a_resumed_run_posts_its_own_comment() -> None:
    assert METRICS_RESUMED in metrics_lines()


def test_the_comment_and_the_end_state_extra_carry_no_secret_or_path() -> None:
    assert METRICS_POST_NO_SECRETS in metrics_lines()


def test_the_comment_is_the_coordinators_only_tracker_write_and_it_never_sets_the_state() -> None:
    lines = metrics_lines()
    assert METRICS_ONLY_WRITE in lines, "the single coordinator tracker write is not stated"
    assert METRICS_NEVER_SETS_STATE in lines, "the coordinator's no-state-change rule is missing"


def test_boundaries_state_the_single_permitted_tracker_write() -> None:
    body = section(SKILL.read_text(), "Boundaries")
    assert BOUNDARIES_ONLY_WRITE in body.splitlines(), "Boundaries do not state the single permitted write"
    assert BOUNDARIES_ONLY_WRITE.startswith("- With `metrics` on, "), "the Boundaries sentence must open on-only"


def test_closing_report_carries_no_secrets_or_paths() -> None:
    assert METRICS_NO_SECRETS in metrics_body()


README_POSTED = (
    "a `metrics` switch, `off` by default, turns on run metrics, with the run summary posted on the story, read "
    "back, and given in the closing report"
)


def test_readme_row_says_the_summary_is_posted_read_back_and_given_in_the_closing_report() -> None:
    row = readme_row()
    assert README_POSTED in row, "the README row does not say the summary is posted on the story"
    assert "with the run summary given in the closing report" not in row
    assert row.endswith(README_POSTED + ". |"), "the README row adds text after the posted-summary clause"


POST_WORDS = re.compile(r"\bpost(?:s|ed|ing)?\b|\bcomments?\b", re.IGNORECASE)


def test_only_the_on_path_lines_tell_the_coordinator_to_post_or_comment() -> None:
    text = SKILL.read_text()
    body = text.split("\n---\n", 1)[1]
    on_path = {
        METRICS_WRAPPER_INTRO: "Metrics",
        METRICS_END_INTRO: "Metrics",
        **{line: "Metrics" for line in METRICS_POSTING},
        METRICS_STEP0: "0. Track everything on a todo list",
        BOUNDARIES_ONLY_WRITE: "Boundaries",
    }
    for line, heading in on_path.items():
        home = metrics_section() if heading == "Metrics" else section(text, heading)
        assert line in home.splitlines(), f"an on-path post line left its section: {line}"
    allowed = {"- " + OFF_PATH, METRICS_POINTER, *on_path}
    merge_rule = "needs a delta review posted before merging"
    for line in [*body.splitlines(), *PROTOCOL.read_text().splitlines()]:
        if line in allowed:
            continue
        assert not POST_WORDS.search(line.replace(merge_rule, "")), (
            f"a line tells the coordinator to post or comment: {line}"
        )


STORY_WRITE_WORDS = re.compile(r"\b(?:on|to) the story\b", re.IGNORECASE)


def test_only_the_summary_post_and_the_hand_back_brief_name_content_on_the_story() -> None:
    body = SKILL.read_text().split("\n---\n", 1)[1]
    protocol = PROTOCOL.read_text().splitlines()
    found = [line.strip() for line in [*body.splitlines(), *protocol] if STORY_WRITE_WORDS.search(line)]
    assert METRICS_POST in protocol
    assert found == [
        METRICS_STEP0,
        next(line.strip() for line in body.splitlines() if "add to the hand-back brief each failed item" in line),
        METRICS_POST,
    ], "a line outside the summary post and the hand-back brief puts content on the story"

# SKL-159 AC 4: the qa-unfinished-own-steps case ships its prompt, case.yaml, grader and rerun
# instructions, records a baseline and a candidate run, and grades tool-call evidence.
CASE = ROOT / "skills" / "story-to-done" / "evals" / "qa-unfinished-own-steps"
CASE_SCENARIOS = ("own-steps", "owner-action", "new-round")


def case_file(name: str) -> Path:
    path = CASE / name
    assert path.is_file(), f"the case is missing {name}"
    return path


def test_the_qa_unfinished_own_steps_case_ships_its_parts() -> None:
    for name in ("prompt.md", "case.yaml", "grader.py", "run.sh", "rerun.md"):
        case_file(name)
    case = yaml.safe_load(case_file("case.yaml").read_text())
    assert case["case"] == "qa-unfinished-own-steps"
    assert case["baseline"]["commit"] == "7a6cb17", "the baseline commit is recorded"
    assert case["runtime"]["model"] == "deepseek/deepseek-v4-pro", "the runtime and model are recorded"
    assert [scenario["name"] for scenario in case["scenarios"]] == list(CASE_SCENARIOS)
    for scenario in CASE_SCENARIOS:
        assert (CASE / "scenarios" / scenario / "scenario.md").is_file(), scenario
        assert (CASE / "scenarios" / scenario / "qa-round-1.json").is_file(), scenario
    assert (CASE / "runtime" / "qa-runtime").is_file()
    baseline = sorted(path for path in (CASE / "results").glob("baseline-*.md"))
    candidate = sorted(path for path in (CASE / "results").glob("candidate-*.md"))
    assert baseline and candidate, "a baseline run and a candidate run are recorded"
    current = [path for path in candidate if "Superseded" not in path.read_text().splitlines()[0]]
    assert current, "one candidate record is current, and the rest are marked superseded"
    for path in current:
        recorded = path.read_text()
        assert "deepseek/deepseek-v4-pro" in recorded, "a current candidate record names its configuration"
        assert re.search(r"`[0-9a-f]{7,40}`", recorded), "a current candidate record names the commit it graded"
        calls = path.with_name(path.stem + "-calls.jsonl")
        assert calls.is_file(), f"{calls.name} carries the calls its verdicts were read from"
        grades = [json.loads(line) for line in calls.read_text().splitlines() if '"grade"' in line]
        assert grades and {entry["grade"] for entry in grades} <= {"PASS", "FAIL"}, "the calls file records each grade"


def test_the_case_prompt_states_the_harness_without_steering_the_run() -> None:
    steer = re.compile(r"(?i)\bresume\b|same session|new round|start a new|\bexpect(?:ed)?\b|\bshould\b")
    for name in ("prompt.md", *(f"scenarios/{scenario}/scenario.md" for scenario in CASE_SCENARIOS)):
        found = steer.findall(case_file(name).read_text())
        assert not found, f"{name} steers the run: {found}"
    prompt = case_file("prompt.md").read_text()
    assert "{skill_dir}" in prompt and "{run_dir}" in prompt


# The checklist of the handback each scenario acts on: QA round 1's for a continuation or a stop,
# and the senior engineer's for the new round that follows its fix-cycle handback.
QA_CHECKLIST = "qa-agent-round-1/qa-agent-round-1-todo.md"
ENGINEER_CHECKLIST = "senior-engineer/senior-engineer-todo.md"


def case_run(tmp_path: Path, *actions: dict, session: str = "qa-round-1-session",
             subdirectory: str = "qa-agent-round-1", read: bool = True, checklist: str | None = None) -> Path:
    run = Path(tempfile.mkdtemp(dir=tmp_path))
    (run / "qa-round-1.json").write_text(json.dumps({
        "session": session,
        "label": "qa-agent-round-1",
        "scratch_subdirectory": subdirectory,
        "round": 1,
    }))
    for shipped in (f"{subdirectory}/{subdirectory}-todo.md", ENGINEER_CHECKLIST):
        (run / shipped).parent.mkdir(parents=True, exist_ok=True)
        (run / shipped).write_text("- [x] done\n")
    records = []
    if read:
        records.append({"action": "read", "path": checklist or f"{subdirectory}/{subdirectory}-todo.md"})
    records.extend(actions)
    (run / "actions.jsonl").write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records))
    return run


def graded(run: Path, expectation: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(case_file("grader.py")), "--run-dir", str(run), "--expectation", expectation],
        capture_output=True, text=True,
    )


CLEAN_CONTINUATION = "QA round 1 is unfinished. Its scratch subdirectory is qa-agent-round-1."
# Step 0's read-back resume message, word for word as SKILL.md prescribes it. In own-steps the
# undone DoD check names no blocker, so step 0 resumes QA with it before step 4 continues the
# round for the evidence PR whose gate is still running: two resumes of round 1's session.
READ_BACK_RESUME = ("Your checklist still has open items. Continue with them; "
                    "if one is blocked, say what blocks it")


def resume_call(message: str, session: str = "qa-round-1-session", round_number: int = 1) -> dict:
    return {"action": "resume", "session": session, "label": "qa-agent-round-1",
            "round": round_number, "message": message}


def continuation_run(tmp_path: Path, message: str, session: str = "qa-round-1-session",
                     round_number: int = 1, read: bool = True, read_back: str | None = READ_BACK_RESUME) -> Path:
    calls = [resume_call(message, session, round_number)]
    if read_back is not None:
        calls.insert(0, resume_call(read_back, session, round_number))
    return case_run(tmp_path, *calls, read=read)


def new_round_run(tmp_path: Path, session: str = "qa-round-2-session", message: str = "the environment under test",
                  checklist: str = ENGINEER_CHECKLIST, read: bool = True) -> Path:
    run = case_run(tmp_path, {"action": "launch", "session": session, "label": "qa-agent-round-2", "round": 2,
                              "message": message}, read=read, checklist=checklist)
    (run / "sessions.json").write_text(json.dumps({
        "sessions": [{"session": "qa-round-1-session", "label": "qa-agent-round-1", "round": 1},
                     {"session": "qa-round-2-session", "label": "qa-agent-round-2", "round": 2}],
        "next_round": 3,
    }))
    return run


def test_the_case_grades_the_same_round_continuation_on_session_identity(tmp_path: Path) -> None:
    result = graded(continuation_run(tmp_path, CLEAN_CONTINUATION), "own-steps")
    assert result.returncode == 0 and result.stdout.strip().endswith("PASS"), result.stdout


# SKL-219: step 0 reads the QA checklist before acting, so the grader must not credit a
# continuation or an owner stop that never recorded that read.
def test_the_case_requires_the_checklist_read_before_crediting_the_call(tmp_path: Path) -> None:
    unread = continuation_run(tmp_path, CLEAN_CONTINUATION, read=False)
    result = graded(unread, "own-steps")
    assert result.returncode == 1 and result.stdout.strip().endswith("FAIL"), result.stdout
    assert "checklist" in result.stdout, "the failing check names the missing checklist read"
    owner = case_run(tmp_path, {"action": "stop", "reason": "the evidence PR gate is still running and a "
                                                            "maintainer's approval is the owner's to grant"},
                     read=False)
    assert graded(owner, "owner-action").returncode == 1, "an owner stop that never read the checklist must not pass"
    new_round = new_round_run(tmp_path, read=False)
    assert graded(new_round, "new-round").returncode == 1, "a new round that never read the checklist must not pass"


# A new round follows the senior engineer's fix-cycle handback, so the checklist step 0 reads before
# it is the engineer's; QA round 1's checklist belongs to an earlier handback.
def test_the_case_new_round_requires_the_engineers_checklist_not_qa_round_1s(tmp_path: Path) -> None:
    assert graded(new_round_run(tmp_path), "new-round").returncode == 0
    wrong = new_round_run(tmp_path, checklist=QA_CHECKLIST)
    result = graded(wrong, "new-round")
    assert result.returncode == 1, "a read of QA round 1's checklist is not the engineer's handback read"
    assert ENGINEER_CHECKLIST in result.stdout, "the failing check names the checklist it wanted"
    for expectation, actions in (("own-steps", (resume_call(READ_BACK_RESUME), resume_call(CLEAN_CONTINUATION))),
                                 ("owner-action", ({"action": "stop", "reason": "the evidence PR gate is still running "
                                                   "and a maintainer's approval is the owner's to grant"},))):
        engineer_only = case_run(tmp_path, *actions, checklist=ENGINEER_CHECKLIST)
        assert graded(engineer_only, expectation).returncode == 1, f"{expectation} acts on QA's handback"


def test_the_case_states_what_it_grades_and_that_the_new_round_brief_is_not_graded() -> None:
    case = yaml.safe_load(case_file("case.yaml").read_text())
    assert any("checklist" in entry for entry in case["graded_on"]), "the checklist read is a graded assertion"
    assert any("new round's launch brief" in entry for entry in case["not_graded_on"]), \
        "the new round's brief text is outside the case, so it claims no brief coverage"
    assert "new round's launch brief is not graded" in case_file("grader.py").read_text()


def test_the_case_credits_no_read_of_a_checklist_that_is_not_there(tmp_path: Path) -> None:
    run = continuation_run(tmp_path, CLEAN_CONTINUATION)
    (run / QA_CHECKLIST).unlink()
    assert graded(run, "own-steps").returncode == 1, "a recorded read of a missing file is no read"
    new_round = new_round_run(tmp_path)
    (new_round / ENGINEER_CHECKLIST).unlink()
    assert graded(new_round, "new-round").returncode == 1, "a recorded read of a missing file is no read"


def test_the_case_credits_only_a_read_of_the_rounds_own_checklist_before_the_call(tmp_path: Path) -> None:
    read_back, resume = resume_call(READ_BACK_RESUME), resume_call(CLEAN_CONTINUATION)
    read = {"action": "read", "path": "qa-agent-round-1/qa-agent-round-1-todo.md"}
    late = case_run(tmp_path, read_back, resume, read, read=False)
    assert graded(late, "own-steps").returncode == 1, "a read after the role calls did not inform them"
    between = case_run(tmp_path, read_back, read, resume, read=False)
    assert graded(between, "own-steps").returncode == 1, "a read after the first role call did not inform it"
    for path in ("elsewhere/qa-agent-round-1/qa-agent-round-1-todo.md", "qa-agent-round-1-todo.md",
                 "/tmp/qa-agent-round-1/qa-agent-round-1-todo.md"):
        other = case_run(tmp_path, {"action": "read", "path": path}, read_back, resume, read=False)
        assert graded(other, "own-steps").returncode == 1, f"a read of {path} is not round 1's checklist file"
    run = case_run(tmp_path, read_back, resume, read=False)
    (run / "actions.jsonl").write_text(
        json.dumps({"action": "read", "path": str(run / "qa-agent-round-1" / "qa-agent-round-1-todo.md")}) + "\n"
        + json.dumps(read_back) + "\n" + json.dumps(resume) + "\n")
    assert graded(run, "own-steps").returncode == 0, "an absolute path to the run's own checklist counts"


def test_the_case_fails_a_run_that_stops_where_the_story_must_not(tmp_path: Path) -> None:
    run = case_run(tmp_path, {"action": "stop", "reason": "QA is not finished"})
    result = graded(run, "own-steps")
    assert result.returncode == 1 and result.stdout.strip().endswith("FAIL"), result.stdout
    assert "was stop, and it had to be resume" in result.stdout


# Story owner ruling on SKL-219: own-steps leaves one item with a stated blocker (the evidence PR's
# gate is running), which step 4 continues, and one with none (the DoD check not yet run), which
# step 0 resumes with its prescribed message first. The case grades both calls, in that order.
def test_the_case_grades_the_read_back_resume_then_the_step_4_continuation(tmp_path: Path) -> None:
    assert graded(continuation_run(tmp_path, CLEAN_CONTINUATION), "own-steps").returncode == 0
    only_continuation = continuation_run(tmp_path, CLEAN_CONTINUATION, read_back=None)
    result = graded(only_continuation, "own-steps")
    assert result.returncode == 1 and "exactly 2 role calls" in result.stdout, result.stdout
    only_read_back = case_run(tmp_path, resume_call(READ_BACK_RESUME))
    assert graded(only_read_back, "own-steps").returncode == 1, "the step 4 continuation is missing"
    reversed_order = case_run(tmp_path, resume_call(CLEAN_CONTINUATION), resume_call(READ_BACK_RESUME))
    assert graded(reversed_order, "own-steps").returncode == 1, "step 0's read-back resume comes before step 4"
    paraphrased = continuation_run(tmp_path, CLEAN_CONTINUATION, read_back="Please keep going with your checklist.")
    result = graded(paraphrased, "own-steps")
    assert result.returncode == 1 and "word for word" in result.stdout, result.stdout
    third = case_run(tmp_path, resume_call(READ_BACK_RESUME), resume_call(CLEAN_CONTINUATION),
                     resume_call(CLEAN_CONTINUATION))
    assert graded(third, "own-steps").returncode == 1, "a third role call is outside the routing"
    other_session = case_run(tmp_path, resume_call(READ_BACK_RESUME, session="qa-round-9-session"),
                             resume_call(CLEAN_CONTINUATION))
    assert graded(other_session, "own-steps").returncode == 1, "the read-back resume names round 1's session"


def test_the_case_does_not_disqualify_the_prescribed_read_back_message(tmp_path: Path) -> None:
    """B5's own wording says items and blocked and names no subdirectory; it still passes."""
    for literal in (READ_BACK_RESUME, READ_BACK_RESUME + ".\n", f'"{READ_BACK_RESUME}"',
                    READ_BACK_RESUME.replace("; ", ";\n")):
        run = continuation_run(tmp_path, CLEAN_CONTINUATION, read_back=literal)
        result = graded(run, "own-steps")
        assert result.returncode == 0, f"{literal!r}: {result.stdout}"
    leaked = continuation_run(tmp_path, "QA round 1 has open items; the gate is blocked. qa-agent-round-1.")
    assert graded(leaked, "own-steps").returncode == 1, "the step 4 continuation still carries no excluded term"
    appended = continuation_run(tmp_path, CLEAN_CONTINUATION, read_back=READ_BACK_RESUME + ". The PR merge waits.")
    assert graded(appended, "own-steps").returncode == 1, "the read-back resume carries the prescribed text only"


def test_the_case_grader_carries_skill_md_read_back_message_word_for_word() -> None:
    tree = ast.parse(case_file("grader.py").read_text())
    constants = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "READ_BACK_RESUME" for target in node.targets)]
    assert constants == [READ_BACK_RESUME], "the grader carries step 0's message word for word"
    assert f'"{READ_BACK_RESUME}"' in SKILL.read_text(), "SKILL.md's step 0 prescribes this message"


def test_the_case_grader_fails_a_nul_byte_in_a_read_path_without_crashing(tmp_path: Path) -> None:
    for expectation in CASE_SCENARIOS:
        run = case_run(tmp_path, {"action": "read", "path": "qa-agent-round-1/\x00todo.md"},
                       resume_call(READ_BACK_RESUME), resume_call(CLEAN_CONTINUATION), read=False)
        result = graded(run, expectation)
        assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr
        assert "record is unreadable" in result.stdout and "ValueError" in result.stdout, result.stdout
    run = continuation_run(tmp_path, CLEAN_CONTINUATION)
    round_one = json.loads((run / "qa-round-1.json").read_text())
    (run / "qa-round-1.json").write_text(json.dumps({**round_one, "scratch_subdirectory": "qa\x00round"}))
    result = graded(run, "own-steps")
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr
    assert "record is unreadable" in result.stdout, result.stdout


def test_the_case_fails_a_continuation_that_carries_substance_or_the_wrong_session(tmp_path: Path) -> None:
    leaked = continuation_run(
        tmp_path,
        "The QA round is unfinished. Your handback left two items outstanding and the merge rules still apply. "
        "Your scratch subdirectory is qa-agent-round-1.",
    )
    assert graded(leaked, "own-steps").returncode == 1, "a continuation must not restate the handback or the rules"
    substituted = case_run(tmp_path, {"action": "launch", "session": "qa-round-2-session",
                                      "label": "qa-agent-round-2", "round": 2, "message": CLEAN_CONTINUATION})
    assert graded(substituted, "own-steps").returncode == 1, "a new agent is not a continuation"
    wrong = continuation_run(tmp_path, CLEAN_CONTINUATION, session="qa-round-9-session")
    assert graded(wrong, "own-steps").returncode == 1, "the continuation must name the round's own session"
    other_round = continuation_run(tmp_path, CLEAN_CONTINUATION, round_number=2)
    assert graded(other_round, "own-steps").returncode == 1, "the continuation must stay in the round it continues"
    unnamed = continuation_run(tmp_path, "Continue your work.")
    assert graded(unnamed, "own-steps").returncode == 1, "the message must name the round's scratch subdirectory"


def test_the_case_controls_grade_the_owner_stop_and_the_new_round(tmp_path: Path) -> None:
    owner = case_run(tmp_path, {"action": "stop", "reason": "the evidence PR and its gate remain, and a maintainer's "
                                                            "approval only the story owner can grant"})
    assert graded(owner, "owner-action").returncode == 0
    unnamed_owner = case_run(tmp_path, {"action": "stop", "reason": "QA unfinished"})
    assert graded(unnamed_owner, "owner-action").returncode == 1, "the stop must name the owner action it leaves"
    resumed = continuation_run(tmp_path, CLEAN_CONTINUATION)
    assert graded(resumed, "owner-action").returncode == 1, "an owner action must stop, never continue"
    assert graded(new_round_run(tmp_path), "new-round").returncode == 0
    fabricated = new_round_run(tmp_path, session="fabricated")
    assert graded(fabricated, "new-round").returncode == 1, "the launched session must be one this run started"
    reused = new_round_run(tmp_path, session="qa-round-1-session")
    assert graded(reused, "new-round").returncode == 1, "a new round must not reuse an earlier session"


def test_the_case_grader_reports_a_malformed_record_instead_of_crashing(tmp_path: Path) -> None:
    run = case_run(tmp_path, {"action": "launch", "label": "qa-agent-round-2"})
    result = graded(run, "new-round")
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr
    broken = Path(tempfile.mkdtemp(dir=tmp_path))
    assert graded(broken, "own-steps").returncode == 1, "a run with no record is a graded FAIL"


def runtime_run(run: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(run / "qa-runtime"), *argv], capture_output=True, text=True)


def runtime_case(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    for name in ("qa-runtime", "qa-runtime.md"):
        shutil.copy(CASE / "runtime" / name, run / name)
    shutil.copy(CASE / "scenarios" / "own-steps" / "qa-round-1.json", run / "qa-round-1.json")
    return run


def test_the_case_runtime_records_a_launch_a_continuation_and_a_stop(tmp_path: Path) -> None:
    run = runtime_case(tmp_path)
    message = tmp_path / "message.txt"
    message.write_text("The round is unfinished; scratch qa-agent-round-1.\n")
    launched = runtime_run(run, "launch", "--label", "qa-agent-round-2", "--message", str(message))
    assert launched.returncode == 0 and "qa-round-2-session" in launched.stdout
    resumed = runtime_run(run, "resume", "--session", "qa-round-1-session",
                          "--label", "qa-agent-round-1", "--message", str(message))
    assert resumed.returncode == 0, resumed.stderr
    refused = runtime_run(run, "resume", "--session", "qa-round-7-session",
                          "--label", "qa-agent-round-1", "--message", str(message))
    assert refused.returncode != 0 and "started no session" in refused.stderr
    assert runtime_run(run, "stop", "--reason", "a maintainer's approval is outstanding").returncode == 0
    recorded = [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines()]
    assert [entry["action"] for entry in recorded] == ["launch", "resume", "stop"]
    assert [(entry.get("session"), entry.get("round")) for entry in recorded] == [
        ("qa-round-2-session", 2), ("qa-round-1-session", 1), (None, None)
    ]


def test_the_case_runtime_records_a_checklist_read(tmp_path: Path) -> None:
    run = runtime_case(tmp_path)
    checklist = run / "qa-agent-round-1" / "qa-agent-round-1-todo.md"
    checklist.parent.mkdir(exist_ok=True)
    checklist.write_text("- [ ] Merge the evidence PR\n")
    result = runtime_run(run, "read", "--path", str(checklist))
    assert result.returncode == 0, result.stderr
    assert "- [ ] Merge the evidence PR" in result.stdout, "the read prints the file it read"
    recorded = [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines()]
    assert len(recorded) == 1 and recorded[0]["action"] == "read", recorded
    assert recorded[0]["path"] == "qa-agent-round-1/qa-agent-round-1-todo.md", \
        "a read inside the run directory is recorded relative to it, so a committed record re-grades anywhere"
    outside = tmp_path / "qa-agent-round-1-todo.md"
    outside.write_text("- [ ] elsewhere\n")
    assert runtime_run(run, "read", "--path", str(outside)).returncode == 0
    recorded = [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines()]
    assert recorded[1]["path"] == str(outside.resolve()), "a read outside the run directory keeps its absolute path"
    missing = runtime_run(run, "read", "--path", str(run / "absent.md"))
    assert missing.returncode != 0 and "no file" in missing.stderr


def test_the_case_runtime_records_nothing_when_it_cannot_read_the_message(tmp_path: Path) -> None:
    run = runtime_case(tmp_path)
    failed = runtime_run(run, "launch", "--label", "qa-agent-round-2", "--message", str(tmp_path / "absent.txt"))
    assert failed.returncode != 0 and "no message file" in failed.stderr
    assert not (run / "actions.jsonl").exists(), "a launch that cannot read its message records no call"
    message = tmp_path / "message.txt"
    message.write_text("the environment under test\n")
    assert runtime_run(run, "launch", "--label", "qa-agent-round-2", "--message", str(message)).returncode == 0
    assert "qa-round-2-session" in (run / "sessions.json").read_text(), "a failed launch must not consume a round"


def test_the_case_runtime_and_grader_agree_end_to_end(tmp_path: Path) -> None:
    run = runtime_case(tmp_path)
    checklist = run / "qa-agent-round-1" / "qa-agent-round-1-todo.md"
    checklist.parent.mkdir(exist_ok=True)
    checklist.write_text("- [ ] Merge the evidence PR\n")
    assert runtime_run(run, "read", "--path", str(checklist)).returncode == 0
    for name, text in (("read-back.txt", READ_BACK_RESUME), ("message.txt", CLEAN_CONTINUATION)):
        message = tmp_path / name
        message.write_text(text + "\n")
        assert runtime_run(run, "resume", "--session", "qa-round-1-session",
                           "--label", "qa-agent-round-1", "--message", str(message)).returncode == 0
    result = graded(run, "own-steps")
    assert result.returncode == 0, "the grader must accept what the runtime recorded"


def test_the_case_runner_refuses_a_void_run_and_a_reused_directory(tmp_path: Path) -> None:
    script = case_file("run.sh").read_text()
    assert "HARNESS: the agent command exited" in script, "a failed agent command must not be graded"
    assert "git -C \"$checkout_real\" status --porcelain" in script, "a checkout the agent changed voids the run"
    assert "is not empty; give each run its own directory" in script, "a reused run directory must be refused"


def test_the_multi_row_duration_rule_names_the_single_row_reference_it_replaces() -> None:
    reference = (ROOT / "skills" / "story-to-done" / "references" / "metrics.md").read_text()
    assert "each QA round's duration, which is its launch row's duration" in reference
    protocol = " ".join(PROTOCOL.read_text().split())
    assert (
        "replaces the single-row duration `references/metrics.md` states for a round" in protocol
    ), "the protocol must say its sum replaces the reference's single-row rule for a multi-row round"

# SKL-159: the sentences this change replaces must stay gone from the whole bundle, not only from
# the section that carries their replacement.
REPLACED_SENTENCES = [
    "never resume an earlier QA agent, since it carries that round's conclusions",
    "Report exactly what remains and who owns it, and stop; resume at step 3 once it is cleared",
    "each QA round is one launch in step 3",
    "QA rounds at each spawn in step 3, each with its duration copied from that round's launch row",
]


def test_no_replaced_sentence_survives_anywhere_in_the_bundle() -> None:
    text = f"{SKILL.read_text()}\n{PROTOCOL.read_text()}".lower()
    for sentence in REPLACED_SENTENCES:
        assert sentence.lower() not in text, f"the replaced sentence is back: {sentence}"


def test_the_case_runner_voids_a_failed_agent_command_without_grading(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(ROOT), "own-steps", str(run_dir)],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": "false"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "nothing was graded" in result.stderr
    assert not (run_dir / "grader-output.txt").exists(), "a void run records no grade"


# SKL-219: step 0 reads the checklist of each handback and treats a missing one as open items, so
# each scenario ships the checklists its subagents left, at the paths their briefs give them. QA
# round 1's open items are exactly the ones its handback names. In own-steps one names a blocker
# (the evidence PR's running gate, step 4) and one names none (the DoD check, step 0's read-back
# resume); in owner-action both name what they wait on or who owns them, so step 4 alone decides.
# The new round follows the engineer's fix-cycle handback, whose checklist is complete.
CASE_CHECKLISTS = {
    "own-steps": {QA_CHECKLIST: 2},
    "owner-action": {QA_CHECKLIST: 2},
    "new-round": {QA_CHECKLIST: 0, ENGINEER_CHECKLIST: 0},
}


@pytest.mark.parametrize("scenario", CASE_SCENARIOS)
def test_the_case_runner_places_each_checklist_where_the_brief_puts_it(tmp_path: Path, scenario: str) -> None:
    shipped_dir = CASE / "scenarios" / scenario / "checklists"
    shipped = {str(path.relative_to(shipped_dir)): path.read_text()
               for path in shipped_dir.rglob("*") if path.is_file()}
    assert {name: sum(line.startswith("- [ ] ") for line in text.splitlines())
            for name, text in shipped.items()} == CASE_CHECKLISTS[scenario], scenario
    run_dir = tmp_path / "run"
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(ROOT), scenario, str(run_dir)],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": "false"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    for name, text in shipped.items():
        assert (run_dir / name).read_text() == text, name
    scenario_text = case_file(f"scenarios/{scenario}/scenario.md").read_text()
    for name in shipped:
        assert f"`{name}`" in scenario_text, f"{scenario}: scenario.md names the checklist {name}"


def test_the_case_runner_voids_a_scenario_without_its_checklists(tmp_path: Path) -> None:
    case = tmp_path / "case"
    shutil.copytree(CASE, case)
    shutil.rmtree(case / "scenarios" / "own-steps" / "checklists")
    result = subprocess.run(["bash", str(case / "run.sh"), str(ROOT), "own-steps", str(tmp_path / "run")],
                            capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": "false"})
    assert result.returncode == 2 and "no checklists" in result.stderr, result.stdout + result.stderr


def test_the_case_runner_refuses_an_unknown_scenario_and_a_reused_directory(tmp_path: Path) -> None:
    unknown = subprocess.run(["bash", str(case_file("run.sh")), str(ROOT), "some-other-case", str(tmp_path / "x")],
                             capture_output=True, text=True)
    assert unknown.returncode == 2 and "unknown scenario" in unknown.stderr
    reused = tmp_path / "reused"
    reused.mkdir()
    (reused / "actions.jsonl").write_text("{}\n")
    result = subprocess.run(["bash", str(case_file("run.sh")), str(ROOT), "own-steps", str(reused)],
                            capture_output=True, text=True)
    assert result.returncode == 2 and "not empty" in result.stderr
    inside = subprocess.run(["bash", str(case_file("run.sh")), str(ROOT), "own-steps",
                             str(ROOT / "skills" / "story-to-done" / "evals" / "inside-run")],
                            capture_output=True, text=True)
    assert inside.returncode == 2 and "must sit outside CHECKOUT" in inside.stderr


def test_the_case_grader_survives_a_ledger_of_the_wrong_shape(tmp_path: Path) -> None:
    run = continuation_run(tmp_path, CLEAN_CONTINUATION)
    (run / "sessions.json").write_text("[]")
    result = graded(run, "own-steps")
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr
    assert "record is unreadable" in result.stdout
    other = case_run(tmp_path, {"action": "launch", "session": "qa-round-2-session", "label": "qa-agent-round-2",
                                "round": 2, "message": "the environment under test"})
    (other / "sessions.json").write_text("7")
    result = graded(other, "new-round")
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr


def test_the_case_fails_a_continuation_that_leaks_in_other_words_or_at_length(tmp_path: Path) -> None:
    vague = continuation_run(
        tmp_path,
        "Round 1 is unfinished. Everything we discussed earlier still stands. "
        "Scratch subdirectory qa-agent-round-1.",
    )
    assert graded(vague, "own-steps").returncode == 1, "a message may not carry an earlier discussion"
    long_message = continuation_run(tmp_path, "QA round 1 is unfinished. " + "note. " * 80 + "qa-agent-round-1")
    assert graded(long_message, "own-steps").returncode == 1, "a continuation states two facts, not a brief"
    near_miss = continuation_run(tmp_path, "The round is unfinished; scratch subdirectory qa-agent-round-1-copy.")
    assert graded(near_miss, "own-steps").returncode == 1, "the message must name that round's own directory"

def test_the_case_owner_stop_must_name_the_owner_action_and_what_remains(tmp_path: Path) -> None:
    vague = case_run(tmp_path, {"action": "stop", "reason": "owner review"})
    assert graded(vague, "owner-action").returncode == 1, "a bare noun does not report what remains"
    both = case_run(tmp_path, {"action": "stop", "reason": "the evidence PR gate is still running and a "
                                                          "maintainer's approval is the owner's to grant"})
    assert graded(both, "owner-action").returncode == 0, "naming both sides passes the control"


def test_the_case_grader_refuses_a_session_of_the_wrong_type(tmp_path: Path) -> None:
    wrong = case_run(tmp_path, {"action": "launch", "session": [], "label": "qa-agent-round-2",
                                "round": 2, "message": "the environment under test"})
    result = graded(wrong, "new-round")
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr


def test_the_case_runner_detects_a_second_change_to_an_already_dirty_file(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    tracked = checkout / "tracked.txt"
    tracked.write_text("first\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@example.com",
                    "commit", "-q", "-m", "base"], cwd=checkout, check=True)
    tracked.write_text("first\nsecond\n")
    agent = tmp_path / "agent.sh"
    agent.write_text(f"#!/bin/sh\nprintf 'third\\n' >> {tracked}\n")
    agent.chmod(0o755)
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(checkout), "own-steps", str(tmp_path / "run")],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": str(agent)},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "the agent changed" in result.stderr, result.stderr

@pytest.mark.parametrize("record", ["baseline-7a6cb17-harness-f591f0f", "candidate-f591f0f"])
def test_the_recorded_calls_re_grade_to_the_recorded_verdicts(tmp_path: Path, record: str) -> None:
    """The committed calls must reproduce the committed grades under the committed grader."""
    lines = [json.loads(line) for line in (CASE / "results" / f"{record}-calls.jsonl").read_text().splitlines()]
    calls: dict[str, list[dict]] = {}
    grades: dict[str, str] = {}
    for entry in lines:
        if "call" in entry:
            calls.setdefault(entry["run"], []).append(entry["call"])
        else:
            grades[entry["run"]] = entry["grade"]
    assert calls and set(calls) == set(grades), "every recorded run has calls and a grade"
    for name, run_calls in calls.items():
        run = Path(tempfile.mkdtemp(dir=tmp_path))
        (run / "qa-round-1.json").write_text(json.dumps({
            "session": "qa-round-1-session", "label": "qa-agent-round-1",
            "scratch_subdirectory": "qa-agent-round-1", "round": 1}))
        (run / "actions.jsonl").write_text("".join(json.dumps(call, sort_keys=True) + "\n" for call in run_calls))
        for checklist in (QA_CHECKLIST, ENGINEER_CHECKLIST):
            (run / checklist).parent.mkdir(parents=True)
            (run / checklist).write_text("- [x] done\n")
        sessions = [{"session": "qa-round-1-session", "label": "qa-agent-round-1", "round": 1}]
        sessions += [{"session": call["session"], "label": call["label"], "round": call.get("round")}
                     for call in run_calls if call["action"] == "launch"]
        (run / "sessions.json").write_text(json.dumps({"sessions": sessions, "next_round": 3}))
        expectation = "owner-action" if name == "owner-action" else "new-round" if name == "new-round" else "own-steps"
        result = graded(run, expectation)
        assert result.stdout.strip().endswith(grades[name]), f"{record} {name}: {result.stdout}"

def test_the_case_owner_stop_must_name_what_remains_and_not_a_bare_noun(tmp_path: Path) -> None:
    bare = case_run(tmp_path, {"action": "stop", "reason": "owner item"})
    assert graded(bare, "owner-action").returncode == 1, "a bare noun pair does not report what remains"
    named = case_run(tmp_path, {"action": "stop", "reason": "the evidence PR gate is still running; "
                                                           "a maintainer's approval is the owner's to grant"})
    assert graded(named, "owner-action").returncode == 0


def test_the_case_runner_detects_a_change_to_an_already_untracked_file(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    (checkout / "tracked.txt").write_text("first\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@example.com",
                    "commit", "-q", "-m", "base"], cwd=checkout, check=True)
    scratch = checkout / "scratch.txt"
    scratch.write_text("first\n")
    agent = tmp_path / "agent.sh"
    agent.write_text(f"#!/bin/sh\nprintf 'second\\n' >> {scratch}\n")
    agent.chmod(0o755)
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(checkout), "own-steps", str(tmp_path / "run")],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": str(agent)},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "the agent changed" in result.stderr, result.stderr

def test_the_case_owner_stop_must_name_the_action_the_scenario_gives_the_owner(tmp_path: Path) -> None:
    terse = case_run(tmp_path, {"action": "stop", "reason": "owner PR"})
    assert graded(terse, "owner-action").returncode == 1, "a two-word reason does not report what remains"
    full = case_run(tmp_path, {"action": "stop", "reason": "the evidence PR's gate is still running; a "
                                                           "maintainer's approval is the owner's to grant"})
    assert graded(full, "owner-action").returncode == 0


def test_the_case_runner_survives_an_unreadable_untracked_entry(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    (checkout / "tracked.txt").write_text("first\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@example.com",
                    "commit", "-q", "-m", "base"], cwd=checkout, check=True)
    (checkout / "dangling").symlink_to("nowhere")
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(checkout), "own-steps", str(tmp_path / "run")],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": "true"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "the agent changed" not in result.stderr, "a dangling untracked link is not an agent change"

def test_the_case_runner_detects_a_retargeted_untracked_link(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    (checkout / "tracked.txt").write_text("first\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@example.com",
                    "commit", "-q", "-m", "base"], cwd=checkout, check=True)
    (checkout / "relink").symlink_to("nowhere")
    agent = tmp_path / "agent.sh"
    agent.write_text("#!/bin/sh\nln -sfn somewhere-else " + str(checkout / "relink") + "\n")
    agent.chmod(0o755)
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(checkout), "own-steps", str(tmp_path / "run")],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": str(agent)},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "the agent changed" in result.stderr, result.stderr

def test_the_case_runner_detects_a_change_made_through_an_untracked_link(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    (checkout / ".gitignore").write_text("ignored.txt\n")
    (checkout / "tracked.txt").write_text("first\n")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@example.com",
                    "commit", "-q", "-m", "base"], cwd=checkout, check=True)
    (checkout / "ignored.txt").write_text("original\n")
    (checkout / "alias").symlink_to("ignored.txt")
    agent = tmp_path / "agent.sh"
    agent.write_text(f"#!/bin/sh\nprintf 'changed\\n' >> {checkout / 'alias'}\n")
    agent.chmod(0o755)
    result = subprocess.run(
        ["bash", str(case_file("run.sh")), str(checkout), "own-steps", str(tmp_path / "run")],
        capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": str(agent)},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "the agent changed" in result.stderr, result.stderr
