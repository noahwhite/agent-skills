"""Contract checks for the story-to-done skill."""

import ast
import hashlib
import importlib.util
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

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "story-to-done" / "SKILL.md"
PROTOCOL = ROOT / "skills" / "story-to-done" / "references" / "metrics-protocol.md"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def visible(text: str) -> str:
    """The text a reader of the rendered Markdown sees: HTML comments removed, an unclosed one to the end."""
    return re.sub(r"<!--.*?(?:-->|\Z)", "", text, flags=re.DOTALL)


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
        "| `engineer-model` | the senior engineer's model | `profile.story_to_done.engineer` |",
        "| `engineer-effort` | the senior engineer's reasoning effort | seat effort (default high) |",
        "| `qa-model` | the QA agent's model | `profile.story_to_done.qa` |",
        "| `qa-effort` | the QA agent's reasoning effort | seat effort (default high) |",
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


# SKL-83: the engineer and QA seats resolve from the profile, never from a model id the skill
# names. Any model id or model family name in the skill text is a hard-coded default creeping back
# in; `claude-code` is a runtime name, not a model.
MODEL_NAME = re.compile(
    r"\b(claude-(?!code\b)[\w.-]+|sonnet|opus|haiku|gpt-[\w.-]+|deepseek[\w./-]*|gemini[\w.-]*|grok[\w.-]*"
    r"|glm-[\w.-]+|kimi[\w.-]*|qwen[\w.-]*|mistral[\w./-]*|llama[\w.-]*)",
    re.IGNORECASE,
)
SEAT_RULES = (
    "The engineer seat is `profile.story_to_done.engineer` and the QA seat is `profile.story_to_done.qa`, "
    "read from the profile the chain in [references/profile.md](references/profile.md) selects (Find the "
    "profile), right after step 0 creates the todo list and before step 1.",
    "Each value resolves on its own: the explicit argument, else the seat's field (`model` for a model, "
    "`effort` for an effort), else, for an effort only, `high`; a model has no default.",
    "An explicit argument overrides the seat field by field: it replaces only the value it names, and the "
    "seat's other fields still apply.",
    "When a seat argument is absent and the profile yields no usable value for it (no profile, no "
    "`profile.story_to_done` object, no `engineer` or `qa` entry, or an entry with no `model`), stop before "
    "spawning either role and ask the user for that seat's model and effort, asking only for the values the "
    "arguments left unset and the profile does not supply.",
    "The `high` effort default never answers that question: it applies only to a seat whose model resolved.",
    "A caller-supplied argument is used even when the seat entry is absent.",
    "Never fall back to a model id written in this skill, and never probe or fall back across a list of "
    "model ids.",
    "One resolved seat serves its role in every round, unchanged: the senior engineer goes back to it for "
    "each fix round, and each new QA round spawns a new agent on it.",
)
# Owner decision 2026-11-11 (SKL-83 AC 4 amendment): profile values never reach a seat command
# unchecked or unquoted, and a command seat from an unconfirmed profile needs one confirmation.
SEAT_LAUNCH_SAFETY = (
    "`command` or `codex` is a separate process launched by the shell-launched agents rule",
    "A seat entry with no `runtime` is not a usable seat (the profile schema requires one)",
    "the model must match `^[A-Za-z0-9][A-Za-z0-9._:/@-]*$`",
    "the session title is `story-to-done-<STORY_ID>-<run>-<role>-<n>` (`<run>` is the last path component of "
    "this run's scratch directory, which `mktemp -d` made unique",
    "with the effort as its `-c model_reasoning_effort=<effort>` flag.",
    "each file path must match `^/[A-Za-z0-9._/-]+$`",
    "A value that fails its check stops the skill before that launch: say which value and why; never escape, "
    "trim or rewrite it.",
    "Fill each value inside the double quotes the `command` template puts around its placeholder",
    "and the user has not confirmed in this conversation that the selected profile is trusted, show the user "
    "the profile path and each such seat's `command` text and ask once whether to run them.",
    "A yes covers every launch of those seats, with that `command` text unchanged, for the rest of the run; a "
    "no stops the skill before either role is spawned.",
    "resolving the four values never asks it.",
    "Wherever steps 2 to 4 say to spawn or resume a subagent, a `command` or `codex` seat is instead a new "
    "launch of that process with the same brief as its prompt file.",
)
SEAT_DIFFERENCES = (
    "no `family` field and no rule that the two seats sit on distinct families",
    "an explicit argument overrides the profile field by field",
    "one resolved seat is reused unchanged in every round, with QA respawned on the same seat",
    "a `command` seat launches by the shell-launched agents rule rather than as a resumed subagent",
)


def test_skill_names_no_model_id() -> None:
    text = SKILL.read_text()
    assert not MODEL_NAME.findall(text), f"hard-coded model names: {MODEL_NAME.findall(text)}"
    assert "QA on <model> at max" in text, "the plain-words example names a placeholder, not a model"


def test_model_name_guard_catches_the_removed_defaults() -> None:
    for removed in ("Sonnet 5.5 (`claude-sonnet-5-5`)", "QA on Opus 5.5 at max", "`claude-opus-5-5`",
                    "deepseek/deepseek-flash", "openai/gpt-6.2-sol", "mistral-large-4-0"):
        assert MODEL_NAME.search(removed), removed
    for allowed in ("runtime `claude-code`", "`opencode` seat", "QA on <model> at max"):
        assert not MODEL_NAME.search(allowed), allowed


def test_seats_resolve_from_the_profile() -> None:
    body = " ".join(section(SKILL.read_text(), "Arguments").split())
    for rule in SEAT_RULES:
        assert rule in body, f"seat resolution missing: {rule}"
    for difference in SEAT_DIFFERENCES:
        assert difference in body, f"difference from the refinement seats missing: {difference}"
    for phrase in (
        "`{model}`, `{effort}`, `{prompt_file}`, `{output_file}` and `{session_title}`",
        "A seat whose runtime you cannot launch",
        "stops the skill",
    ):
        assert phrase in body, f"seat launch missing: {phrase}"
    for phrase in SEAT_LAUNCH_SAFETY:
        assert phrase in body, f"seat launch safety missing: {phrase}"
    assert "Each role keeps the same model and effort in every round." not in body


def test_codex_seat_never_launches_read_only_and_needs_recorded_outer_sandbox() -> None:
    # Both roles write, commit, push and call the tracker: the shared `-s read-only` codex base command
    # cannot serve them, and `-s danger-full-access` needs the operator's recorded outer-sandbox confirmation.
    body = " ".join(section(SKILL.read_text(), "Arguments").split())
    runtimes = " ".join((ROOT / "shared" / "runtimes.md").read_text().split())
    assert "For `runtime: codex`, the base command is `codex exec -m <model> -s read-only" in runtimes
    assert "the profile or an overlay records that confirmation, and an agent never assumes it" in runtimes
    for phrase in (
        "a `codex` seat launches with `-s danger-full-access` in place of `-s read-only`, under every "
        "condition that rule sets for that flag;",
        "when the profile or an overlay does not record the operator's outer-sandbox confirmation that rule "
        "requires, stop before either role is spawned and say which seat and why.",
    ):
        assert phrase in body, f"codex seat sandbox rule missing: {phrase}"


SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
SEAT = {"name": "Engineer", "runtime": "opencode", "model": "example/strong", "effort": "high"}
COMMAND_SEAT = {
    "name": "Engineer",
    "runtime": "command",
    "model": "example/strong",
    "command": 'agent --model "{model}#{effort}" --title "{session_title}" --file "{prompt_file}" > "{output_file}"',
}


def profile_with(story_to_done) -> dict:
    return {"version": 1, "project": {"name": "Example"}, "story_to_done": story_to_done}


def schema_errors(instance: dict) -> list[str]:
    return [e.message for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(instance)]


def test_schema_accepts_a_story_to_done_seat_pair() -> None:
    assert not schema_errors(profile_with({"engineer": SEAT, "qa": COMMAND_SEAT}))
    assert not schema_errors(profile_with({"engineer": {"runtime": "codex", "model": "example/strong"}, "qa": SEAT}))
    # A '#' inside a word is not a shell comment.
    hash_in_word = 'agent --tag build#1 --model "{model}#{effort}" --title "{session_title}" --file "{prompt_file}" > "{output_file}"'
    assert not schema_errors(profile_with({"engineer": COMMAND_SEAT | {"command": hash_in_word}, "qa": SEAT}))
    effort = SCHEMA["$defs"]["story_to_done_seat"]["properties"]["effort"]
    assert effort["enum"] == ["low", "medium", "high", "xhigh", "max"]
    assert effort["default"] == "high"


@pytest.mark.parametrize("word", ["'release #1'", "'release;#1'", "release\\;#1", "release\\ #1", "'v1'#2", '"v1"#2', "release\\\n#1"])
def test_schema_accepts_a_hash_the_shell_keeps_as_text(word) -> None:
    # Single quotes, an escape or a closing quote keep the next '#' inside the word.
    command = f'agent --tag {word} --model "{{model}}#{{effort}}" --title "{{session_title}}" --file "{{prompt_file}}" > "{{output_file}}"'
    assert not schema_errors(profile_with({"engineer": COMMAND_SEAT | {"command": command}, "qa": SEAT}))


@pytest.mark.parametrize(
    "story_to_done",
    [
        {"engineer": SEAT},
        {"qa": SEAT},
        {"engineer": SEAT, "qa": SEAT, "extra": SEAT},
        {"engineer": {k: v for k, v in SEAT.items() if k != "model"}, "qa": SEAT},
        {"engineer": SEAT | {"family": "example"}, "qa": SEAT},
        {"engineer": SEAT | {"effort": "extreme"}, "qa": SEAT},
        {"engineer": SEAT | {"runtime": "shell"}, "qa": SEAT},
        {"engineer": {k: v for k, v in COMMAND_SEAT.items() if k != "command"}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model "example/strong#high"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model "{model}#high"'}, "qa": SEAT},
        {"engineer": {k: v for k, v in SEAT.items() if k != "runtime"}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"model": 'x"; touch /tmp/p; "'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"model": "$(printf INJECTED >&2)"}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"model": "-rf"}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model "{model}#{effort}" --title "{session_title}" > "{output_file}"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model "{model}#{effort}" --title "{session_title}" --file "{prompt_file}"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model "{model}#{effort}" --file "{prompt_file}" > "{output_file}"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model {model}#{effort} --title "{session_title}" --file "{prompt_file}" > "{output_file}"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model "x" --title "t" --file "f" > "o" # {model} {effort} {session_title} {prompt_file} {output_file}'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model x # "{model}" "{effort}" "{prompt_file}" "{output_file}" "{session_title}"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'agent --model {model}#{effort} --title {session_title} --file {prompt_file} > {output_file} # "{model}" "{effort}" "{prompt_file}" "{output_file}" "{session_title}"'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"command": 'printf run \\" # {model} {effort} {prompt_file} {output_file} {session_title}'}, "qa": SEAT},
        {"engineer": COMMAND_SEAT | {"model": "example/strong\n"}, "qa": SEAT},
        {"engineer": {"runtime": "codex", "model": "x; touch /tmp/p"}, "qa": SEAT},
        {"engineer": {"runtime": "codex", "model": "example/strong\n"}, "qa": SEAT},
    ],
    ids=["no-qa", "no-engineer", "extra-seat", "no-model", "family", "bad-effort", "bad-runtime",
         "command-without-command", "command-without-placeholders", "command-without-effort", "no-runtime",
         "command-model-with-shell-text", "command-model-with-substitution", "command-model-like-an-option", "command-without-prompt-file",
         "command-without-output-file", "command-without-session-title", "command-with-unquoted-model",
         "command-with-placeholders-only-in-a-comment", "command-with-quoted-placeholders-only-in-a-comment",
         "command-with-unquoted-placeholders-and-a-quoted-comment-copy", "command-with-an-escaped-quote-before-a-comment",
         "command-model-with-trailing-newline",
         "codex-model-with-shell-text", "codex-model-with-trailing-newline"],
)
def test_schema_refuses_a_malformed_story_to_done(story_to_done) -> None:
    assert schema_errors(profile_with(story_to_done))


@pytest.mark.parametrize("operator", [";", "&", "|", "<", ">", "(", ")", "`"])
def test_schema_refuses_placeholders_in_a_comment_after_a_shell_operator(operator) -> None:
    # A '#' right after a shell operator starts a comment, like one after whitespace.
    command = f'agent --model x{operator}# "{{model}}" "{{effort}}" "{{prompt_file}}" "{{output_file}}" "{{session_title}}"'
    assert schema_errors(profile_with({"engineer": COMMAND_SEAT | {"command": command}, "qa": SEAT}))


@pytest.mark.parametrize("prefix", ["printf live \\\n", "printf live;\\\n", "\\\n", "printf live \\\n\\\n"])
def test_schema_refuses_placeholders_in_a_comment_after_a_line_continuation(prefix) -> None:
    # The shell removes a backslash-newline first, so the '#' keeps whatever precedes the continuation.
    command = prefix + '# "{model}" "{effort}" "{prompt_file}" "{output_file}" "{session_title}"'
    assert schema_errors(profile_with({"engineer": COMMAND_SEAT | {"command": command}, "qa": SEAT}))


@pytest.mark.parametrize("path", [ROOT / "profile" / "example.yaml", ROOT / ".agent-skills" / "profile.yaml"],
                         ids=["example", "repository"])
def test_profiles_seat_story_to_done_on_verified_labs(path: Path) -> None:
    profile = yaml.safe_load(path.read_text())
    seats = profile["story_to_done"]
    assert not schema_errors(profile_with(seats))
    assert (seats["engineer"]["model"], seats["engineer"]["effort"]) == ("deepseek/deepseek-flash", "high")
    assert (seats["qa"]["model"], seats["qa"]["effort"]) == ("deepseek/deepseek-v4-pro", "high")
    for seat in seats.values():
        assert seat["runtime"] == "command", seat
        # The shell-launched agents rule: stdin never stays on the terminal.
        assert "< /dev/null" in seat["command"], seat["command"]
    assert profile["review"]["adjudicator"]["model"] == "deepseek/deepseek-flash"
    assert "Interim: the owner will change this again" not in path.read_text()


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
    "Continuation of the current round under step 4, and the step 0 checklist read-back resume or the resumes "
    "under the handback reference this step points to of the current round's QA agent, are the only exceptions "
    "to that sentence."
)
OLD_QA_ROUND_CLAUSE = "never resume an earlier QA agent, since it carries that round's conclusions"


def test_each_qa_round_is_a_new_agent_with_a_minimal_brief() -> None:
    body = section(visible(SKILL.read_text()), "3. QA agent: verify the deployed story")
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
    "human merge, an external deploy, a pending acceptance-basis ruling (an item QA recorded as `pending owner "
    "ruling`) - report exactly what remains and who "
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


def test_a_command_qa_seat_continues_by_a_new_launch_on_the_same_seat() -> None:
    body = " ".join(in_deployment_review_branch().split())
    assert (
        "A `command` or `codex` QA seat is never resumed, so its continuation is a new launch on the same seat "
        "whose prompt file is the step 3 brief followed by that continuation message; it is still the same "
        "round's continuation under every rule in this bullet."
    ) in body
    assert (
        "its prompt file also tells it to read that round's existing checklist in the named subdirectory and the "
        "story's open evidence PR, if any, before acting, and to continue from the first unfinished item, never "
        "rewriting the checklist or opening a second evidence PR."
    ) in body


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


OWNER_WAIT_DEFER = (
    "That stop and its mixed-remainder sentence defer to the owner-wait verification rule below: they apply "
    "only to a remainder that contains an item verified `owner-only: yes`."
)
OWNER_WAIT_RULE = [
    "**Owner-wait verification.** This rule binds every place the coordinator reports an item as waiting on "
    "the owner: an item relayed from a handback, one from its own reading, one on step 0's resume path, one at "
    "any stop, and one in step 5's report.",
    "Before reporting it, read the item's story in the tracker yourself - its current state, its acceptance "
    "criteria, its comments, and its relations with each blocker's state - and never rely on the handback's "
    "own claim.",
    "Record two entries on your todo list, each followed by the field or relation that supports it: "
    "`owner-only: yes|no` and `coordinator-or-role-can-act: yes|no`.",
    "If the tracker read fails or is inconclusive, report the failed read and do not present the owner-wait as "
    "verified.",
    "An item is owner-only when it is an open acceptance criterion that needs input only the owner can give (a "
    "comment, a value, a credential, an access grant), a decision on what an acceptance criterion means, a "
    "maintainer's approval or access grant, a human merge, or an external deploy.",
    "An owner-approval gate written into a criterion for the story's own outcome (the owner approving or "
    "signing off on what the story delivered) is not owner-only and does not stop this skill, because the "
    "operator's request for the story is the approval for that outcome; a maintainer's approval stays "
    "owner-only.",
    "When the entries are `owner-only: no` and `coordinator-or-role-can-act: yes`, do the next step this skill "
    "defines for the story's current state, or launch or resume the role that step dispatches, writing its "
    "brief from the story's acceptance criteria, and do not report the item as waiting on the owner, in step "
    "5's report included.",
    "The at-most-once continuation and stall rules still apply: when the role hands back the same owner claim "
    "with no observed progress, report the stall, naming the tracker read it rests on, and stop.",
    "When the entries are `owner-only: no` and `coordinator-or-role-can-act: no`, report the item and who can "
    "act on it, and stop.",
    "When the entries are `owner-only: yes`, report the item and stop; the report names the story id, the "
    "exact criterion text, comment or relation read, and which owner-only category applies.",
]
DISPUTE_RULE = (
    "If the senior engineer disputes a failed verdict or an adjudicator's ruling, do not relay its argument to "
    "a QA agent and do not rule on it yourself. Stop and put the item, its evidence, and the engineer's "
    "evidence to the user, since what an AC means is the product owner's decision."
)


def test_an_owner_wait_is_verified_against_the_tracker_before_it_is_reported() -> None:
    step4 = " ".join(section(SKILL.read_text(), "4. Act on the QA outcome").split())
    assert in_order(step4, *OWNER_WAIT_RULE, DISPUTE_RULE), "the owner-wait rule must sit in step 4 before the unchanged dispute rule"
    assert in_order(in_deployment_review_branch(), STEP4_OTHER_OWNER, OWNER_WAIT_DEFER, STEP4_NO_RUNTIME), (
        "the owner-action stop and the mixed-remainder sentence must defer to the owner-wait rule"
    )


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
    "adjudicator ruled valid, except what `references/code-review.md` (Handling findings) files or records, "
    "without overturning those rulings; a separate clean, neutral arbiter on "
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
            "fixes what QA ruled not met or the adjudicator ruled valid, except what `references/code-review.md` "
            "(Handling findings) files or records, without overturning those rulings",
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
    "Write the four resolved model and effort values, the `metrics: on|off` line, the `qa-round-cap: <n>` "
    "line, and the `nested: yes|no` line at the top of your todo list and in the closing report of every end state"
)
# SKL-138: the two `nested` lines that touch metrics or say "background", pinned in METRICS_LINES.
NESTED_REASON = (
    "- The spawner states `nested=yes` because a background role launched by a subagent may report to the root "
    "session instead of the launcher."
)
NESTED_IDENTICAL = (
    "- `nested` sets only the launch mode, or that stop: briefs, role rows, and metrics rules are identical "
    "with `nested=yes` and `nested=no`."
)


def test_arguments_table_adds_the_metrics_switch_off_by_default() -> None:
    body = section(SKILL.read_text(), "Arguments")
    assert METRICS_ROW in body, "arguments table missing the metrics row and its off default"


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
    assert "the `metrics: on|off` line, the `qa-round-cap: <n>` line," in close_out


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
    "spawn in step 3, each continuation of that round in step 4, each checklist read-back resume of a QA "
    "agent under step 0, and each interim-deadline resume, naming resume and stale-checklist resume of a QA agent, "
    "taking the start immediately before that "
    "launch and the end when it returns, and record it as one row in launch order under a "
    "label unique within the invocation, with its runtime, model, effort, duration, tokens, and tool "
    "calls as `references/metrics.md` defines; `not "
    "reported` stands for any figure the runtime does not return, and a resumed role's cumulative figure is "
    "marked `cumulative`."
)
METRICS_LAUNCH_POINTS = (
    "The senior engineer's timed launches are the first launch in step 2, each checklist read-back resume "
    "of the senior engineer under step 0, each interim-deadline resume, naming resume and stale-checklist resume "
    "of the senior engineer under "
    "`references/interim-handbacks.md`, and each resume or re-spawn in step 4; each QA round is a launch "
    "row in step 3, a continuation of that round under step 4 is a further launch row within the same "
    "round, each checklist read-back resume of a QA agent is a launch row of its own within that QA agent's "
    "round, and so is each interim-deadline resume, naming resume and stale-checklist resume of a QA agent under "
    "`references/interim-handbacks.md`."
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
    "With `metrics` on, launch no command before the start form, not even to read a file or list a directory, "
    "except the scratch-directory creation that the step 0 checklist fallback needs when no todo tool exists, "
    "whose directory the start form then uses; "
    "after step 0 creates the todo list, read this skill's references and the profile with the runtime's "
    "file-read tool, which launches nothing."
)
METRICS_START = (
    "With `metrics` on, the first command launched, right after step 0 creates the todo list, is this start form, "
    "which records "
    "`invocation_start` and makes its `metrics.txt` the `<metrics file>` of every later launch, with the "
    "scratch-directory creation from `references/runtimes.md`, or `scratch='<directory you were handed>'` when "
    "you were handed one or the step 0 checklist fallback created it, in place of `<scratch creation>`:"
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
    # SKL-98: a role launch and a role's return-notice timestamp are not wrapped.
    "Launch every later command other than a role launch, which gets a role row below, the end form below, the "
    "summary post, its read-back, and a role's return-notice `date -u +%s.%N` below in this wrapper, with the command in place of "
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
    # SKL-98: a usage-after-exit role's end line is written where the next sentence sets.
    "returns, or, for a role whose usage is read only after it exits, at the point the next sentence sets, "
    f"`{METRICS_ROLE_END}`, where `<tokens>` and `<tool calls>` are written exactly as the summary's "
    "cells read: the number, `not reported`, or the number followed by ` cumulative`; a row label is unique, "
    "is neither `start` nor `end`, and no value these commands carry contains a single quote; a role row has "
    "exactly one end line, this one, even when the launch was killed, so the recovery for a killed wrapped "
    "command above never applies to a role launch."
)
# SKL-98: a role whose usage is read after it exits keeps its end timestamp at its return.
METRICS_ROLE_END_BEFORE_USAGE = (
    "When a role's usage can be read only after it exits, as for a `runtime: command` launch under "
    "`references/runtimes.md`, the launch runs exactly as the profile gives it, with nothing chained before or "
    "after it, and its end timestamp is taken before the usage read: on the runtime's notice that the role "
    "returned, the coordinator's next command is `date -u +%s.%N`, which is not a launch and gets no row, then "
    "the usage read runs in the wrapper above, and the end command carries the printed timestamp in place of "
    "`$(date -u +%s.%N)` and the figures the usage read printed, without their `tokens: ` and `tool calls: ` "
    "labels, in place of `<tokens>` and `<tool calls>`; when no usage read runs, as after a launch that did not "
    "exit successfully, the end command still carries the printed timestamp, with `not reported` for each figure "
    "not read."
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
    # SKL-98: the killed-command recovery covers wrapped commands only.
    "If a wrapped command is killed before its wrapper writes its `end` line, the coordinator's very next "
    "launch, made as "
    "soon as the kill is reported, is a wrapped command whose `<command>` is `printf 'end %s %s\\n' "
    "\"$(date -u +%s.%N)\" '<killed row label>' >> '<metrics file>'`, and the recovery command gets a row "
    "of its own."
)
METRICS_CLOSING_REPORT = (
    "Give the summary, in the template `references/metrics.md` defines, in the closing report of every end "
    "state: Done, or any stop, including a stop before step 0 or before any senior engineer or QA agent is spawned."
)
# SKL-155: a qa-round-cap stop that waits for the reply is not yet an end state for the metrics summary.
METRICS_CAP_STOP = (
    "A `qa-round-cap` stop is not an end state while the coordinator waits for the reply: its stop report "
    'carries no summary, the end form runs only when a "stop" reply ends the invocation, '
    'and after "N additional rounds" the same invocation and its metrics file go on.'
)
METRICS_NO_LAUNCHES = (
    "The summary reads `no launches` only when the coordinator launched no role and no command; otherwise it "
    "has one row for each launch in launch order, the elapsed wall-clock, and the end state or stop reason."
)
METRICS_NO_SECRETS = (
    "The closing report contains no secrets and no local or scratch paths, including where it relays a role's "
    "finding, evidence or incidental defect, which it restates without the path."
)


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
    "which launches nothing, together with `references/metrics.md`, after step 0 creates the todo list and "
    "before the first command is launched."
)
METRICS_LINES = [
    METRICS_ROW,
    '- `metrics` is given as `metrics=on` or `metrics=off`, or in plain words: "with metrics" and "metrics on" '
    'mean on, "without metrics" and "metrics off" mean off; ask the user about any other phrasing about metrics; '
    "never guess.",
    "- Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.",
    "- " + OFF_PATH,
    NESTED_REASON,
    NESTED_IDENTICAL,
    "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at any stop, including one before step 0).",
    "## Metrics",
    METRICS_OPENING + " right after step 0 creates the todo list: it is the single home for what a `story-to-done` run "
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
    # SKL-270: the step 5 report carries the `path:` line the Arguments section requires.
    "Report the story identifier, its final state, the four resolved model and effort values and the "
    "`metrics: on|off` line, the `qa-round-cap: <n>` line, the `nested: yes|no` line, the `path: <value>` line, "
    "each PR, the number of QA rounds with the items "
    "fixed in each, where QA recorded its evidence, and any incidental defects left open.",
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
    METRICS_ROLE_END_BEFORE_USAGE,
    METRICS_EXTRAS_RECORD,
    METRICS_END_INTRO,
    METRICS_SCRIPT_ONCE,
    METRICS_NO_EDIT,
    METRICS_END_VERBATIM,
    METRICS_CLOSING_REPORT,
    METRICS_CAP_STOP,
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
    assert len(rows) == 7 and "Seven arguments are optional" in body
    for stale in ("Six", "Five", "Four"):
        assert f"{stale} arguments are optional" not in body, stale


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
    return section(visible(SKILL.read_text()), "Metrics") + "\n" + visible(PROTOCOL.read_text())


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
    assert METRICS_ROLE_END_BEFORE_USAGE in body, "a usage-after-exit role's end timestamp is not taken at its return"
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

BRIEF_AUTHORING = "Brief authoring"
CITATION_NUMBER = re.compile(r":\d+")


def unpinned(line: str) -> str:
    """A line with each citation's line number blanked, so a corrected citation never edits a test."""
    return CITATION_NUMBER.sub(":NN", line)


# The brief-authoring lines that name a role's own post. Each must live in that section, like every
# other allowed line, and its citation numbers are matched without being pinned here.
BRIEF_PERMISSION_LINES = (
    "- Every role brief names what the role may do as well as what it may not: it ticks the boxes it "
    "verified, moves the states its skill assigns, opens its own PR, and posts the review of record.",
    "  The senior engineer's review of record reads \"Post the review of record on the PR as one PR "
    "review\" at `skills/engineering-workflow/SKILL.md:NN`; the QA agent's reads \"post the review of "
    "record on the PR\" at `skills/qa-verification/SKILL.md:NN`.",
)


def test_only_the_on_path_lines_tell_the_coordinator_to_post_or_comment() -> None:
    text = SKILL.read_text()
    body = text.split("\n---\n", 1)[1]
    brief_home = {unpinned(line): line for line in section(text, BRIEF_AUTHORING).splitlines()}
    brief_lines = []
    for expected in BRIEF_PERMISSION_LINES:
        found = brief_home.get(unpinned(expected))
        assert found is not None, f"a brief-authoring role-permission line left its section: {expected}"
        brief_lines.append(found)
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
    # The owner-wait rule reads the story's comments and names a comment as owner input; it posts none.
    allowed = {"- " + OFF_PATH, METRICS_POINTER, *on_path, *OWNER_WAIT_RULE, *brief_lines}
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
CASE_SCENARIOS = ("own-steps", "read-back", "owner-action", "new-round")


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
# Step 0's read-back resume message, word for word as SKILL.md prescribes it. In read-back the
# handback names its one open item, removing the round's temporary test data, with no stated
# blocker or owner, so step 0
# resumes round 1's session with this message; own-steps' one item states what it waits on, so
# step 4 continues the round instead.
READ_BACK_RESUME = ("Your checklist still has open items. Continue with them; "
                    "if one is blocked, say what blocks it")


def resume_call(message: str, session: str = "qa-round-1-session", round_number: int = 1) -> dict:
    return {"action": "resume", "session": session, "label": "qa-agent-round-1",
            "round": round_number, "message": message}


def continuation_run(tmp_path: Path, message: str, session: str = "qa-round-1-session",
                     round_number: int = 1, read: bool = True) -> Path:
    return case_run(tmp_path, resume_call(message, session, round_number), read=read)


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
    assert graded(new_round, "new-round-read").returncode == 1, "a new round that never read the checklist must not pass"


# The new-round control grades session identity alone, so a version without the read-back rule
# passes it when it launches the right session; the read is graded on the same run under
# new-round-read, which keeps every control check and adds the read.
def test_the_case_new_round_control_grades_session_identity_apart_from_the_read(tmp_path: Path) -> None:
    unread = new_round_run(tmp_path, read=False)
    control = graded(unread, "new-round")
    assert control.returncode == 0 and "checklist" not in control.stdout, control.stdout
    read = graded(unread, "new-round-read")
    assert read.returncode == 1 and ENGINEER_CHECKLIST in read.stdout, read.stdout
    assert graded(new_round_run(tmp_path), "new-round-read").returncode == 0
    for session in ("fabricated", "qa-round-1-session"):
        assert graded(new_round_run(tmp_path, session=session), "new-round-read").returncode == 1, session


# A new round follows the senior engineer's fix-cycle handback, so the checklist step 0 reads before
# it is the engineer's; QA round 1's checklist belongs to an earlier handback.
def test_the_case_new_round_requires_the_engineers_checklist_not_qa_round_1s(tmp_path: Path) -> None:
    assert graded(new_round_run(tmp_path), "new-round-read").returncode == 0
    wrong = new_round_run(tmp_path, checklist=QA_CHECKLIST)
    result = graded(wrong, "new-round-read")
    assert result.returncode == 1, "a read of QA round 1's checklist is not the engineer's handback read"
    assert ENGINEER_CHECKLIST in result.stdout, "the failing check names the checklist it wanted"
    for expectation, actions in (("own-steps", (resume_call(CLEAN_CONTINUATION),)),
                                 ("read-back", (resume_call(READ_BACK_RESUME),)),
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
    assert graded(new_round, "new-round-read").returncode == 1, "a recorded read of a missing file is no read"


def test_the_case_credits_only_a_read_of_the_rounds_own_checklist_before_the_call(tmp_path: Path) -> None:
    read = {"action": "read", "path": "qa-agent-round-1/qa-agent-round-1-todo.md"}
    for expectation, message in (("own-steps", CLEAN_CONTINUATION), ("read-back", READ_BACK_RESUME)):
        resume = resume_call(message)
        late = case_run(tmp_path, resume, read, read=False)
        assert graded(late, expectation).returncode == 1, "a read after the role call did not inform it"
        for path in ("elsewhere/qa-agent-round-1/qa-agent-round-1-todo.md", "qa-agent-round-1-todo.md",
                     "/tmp/qa-agent-round-1/qa-agent-round-1-todo.md"):
            other = case_run(tmp_path, {"action": "read", "path": path}, resume, read=False)
            assert graded(other, expectation).returncode == 1, f"a read of {path} is not round 1's checklist file"
        run = case_run(tmp_path, resume, read=False)
        (run / "actions.jsonl").write_text(
            json.dumps({"action": "read", "path": str(run / "qa-agent-round-1" / "qa-agent-round-1-todo.md")}) + "\n"
            + json.dumps(resume) + "\n")
        assert graded(run, expectation).returncode == 0, "an absolute path to the run's own checklist counts"


def test_the_case_fails_a_run_that_stops_where_the_story_must_not(tmp_path: Path) -> None:
    for expectation in ("own-steps", "read-back"):
        run = case_run(tmp_path, {"action": "stop", "reason": "QA is not finished"})
        result = graded(run, expectation)
        assert result.returncode == 1 and result.stdout.strip().endswith("FAIL"), result.stdout
        assert "was stop, and it had to be resume" in result.stdout


# Story owner ruling on SKL-219: one coordinator step acts on one handback, and a resume hands
# control back to QA, so each scenario holds one kind of open item and grades one role call.
# read-back's item names no blocker, so step 0 resumes with its prescribed message; own-steps'
# item states what it waits on, so step 4 continues the round.
def test_the_case_grades_the_read_back_resume_word_for_word(tmp_path: Path) -> None:
    result = graded(continuation_run(tmp_path, READ_BACK_RESUME), "read-back")
    assert result.returncode == 0 and result.stdout.strip().endswith("PASS"), result.stdout
    paraphrased = continuation_run(tmp_path, "Please keep going with your checklist.")
    result = graded(paraphrased, "read-back")
    assert result.returncode == 1 and "word for word" in result.stdout, result.stdout
    step_4 = continuation_run(tmp_path, CLEAN_CONTINUATION)
    assert graded(step_4, "read-back").returncode == 1, "an item with no stated blocker gets step 0's message"
    two = case_run(tmp_path, resume_call(READ_BACK_RESUME), resume_call(CLEAN_CONTINUATION))
    result = graded(two, "read-back")
    assert result.returncode == 1 and "exactly one role call" in result.stdout, result.stdout
    other_session = continuation_run(tmp_path, READ_BACK_RESUME, session="qa-round-9-session")
    assert graded(other_session, "read-back").returncode == 1, "the read-back resume names round 1's session"
    other_round = continuation_run(tmp_path, READ_BACK_RESUME, round_number=2)
    assert graded(other_round, "read-back").returncode == 1, "the read-back resume stays in round 1"
    launched = case_run(tmp_path, {"action": "launch", "session": "qa-round-2-session",
                                   "label": "qa-agent-round-2", "round": 2, "message": READ_BACK_RESUME})
    assert graded(launched, "read-back").returncode == 1, "a new agent is not a read-back resume"


def test_the_case_grades_one_step_4_continuation_in_own_steps(tmp_path: Path) -> None:
    two = case_run(tmp_path, resume_call(READ_BACK_RESUME), resume_call(CLEAN_CONTINUATION))
    result = graded(two, "own-steps")
    assert result.returncode == 1 and "exactly one role call" in result.stdout, result.stdout


def test_the_case_does_not_disqualify_the_prescribed_read_back_message(tmp_path: Path) -> None:
    """B5's own wording says items and blocked and names no subdirectory; it still passes."""
    for literal in (READ_BACK_RESUME, READ_BACK_RESUME + ".\n", f'"{READ_BACK_RESUME}"',
                    READ_BACK_RESUME.replace("; ", ";\n")):
        result = graded(continuation_run(tmp_path, literal), "read-back")
        assert result.returncode == 0, f"{literal!r}: {result.stdout}"
    leaked = continuation_run(tmp_path, "QA round 1 has open items; the gate is blocked. qa-agent-round-1.")
    assert graded(leaked, "own-steps").returncode == 1, "the step 4 continuation still carries no excluded term"
    appended = continuation_run(tmp_path, READ_BACK_RESUME + ". The PR merge waits.")
    assert graded(appended, "read-back").returncode == 1, "the read-back resume carries the prescribed text only"


def test_the_case_grader_carries_skill_md_read_back_message_word_for_word() -> None:
    tree = ast.parse(case_file("grader.py").read_text())
    constants = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "READ_BACK_RESUME" for target in node.targets)]
    assert constants == [READ_BACK_RESUME], "the grader carries step 0's message word for word"
    assert f'"{READ_BACK_RESUME}"' in SKILL.read_text(), "SKILL.md's step 0 prescribes this message"


def test_the_case_grader_fails_a_nul_byte_in_a_read_path_without_crashing(tmp_path: Path) -> None:
    for expectation in CASE_SCENARIOS:
        run = case_run(tmp_path, {"action": "read", "path": "qa-agent-round-1/\x00todo.md"},
                       resume_call(CLEAN_CONTINUATION), read=False)
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
    message = tmp_path / "message.txt"
    message.write_text(CLEAN_CONTINUATION + "\n")
    assert runtime_run(run, "resume", "--session", "qa-round-1-session",
                       "--label", "qa-agent-round-1", "--message", str(message)).returncode == 0
    result = graded(run, "own-steps")
    assert result.returncode == 0, "the grader must accept what the runtime recorded"


def test_the_case_runner_grades_the_new_round_control_and_its_read_apart(tmp_path: Path) -> None:
    agent = tmp_path / "agent.sh"
    agent.write_text('#!/bin/sh\nrun="$(dirname "$2")"\n'
                     'printf "the environment under test\\n" > "$run/message.txt"\n'
                     '"$run/qa-runtime" launch --label qa-agent-round-2 --message "$run/message.txt"\n')
    agent.chmod(0o755)
    run_dir = tmp_path / "run"
    result = subprocess.run(["bash", str(case_file("run.sh")), str(ROOT), "new-round", str(run_dir)],
                            capture_output=True, text=True, env={**os.environ, "EVAL_AGENT_CMD": str(agent)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert (run_dir / "grader-output.txt").read_text().strip().endswith("PASS"), "the control passes on the session"
    assert (run_dir / "grader-read-output.txt").read_text().strip().endswith("FAIL"), "the unread launch fails the read"


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
# round 1's open items are exactly the ones its handback names. own-steps' one item names what it
# waits on (the evidence PR's running gate, step 4); read-back's one item names no blocker or owner
# (removing the round's temporary test data, step 0's read-back resume); in owner-action both name what they wait on or who owns them,
# so step 4 alone decides. The new round follows the engineer's fix-cycle handback, whose
# checklist is complete.
CASE_CHECKLISTS = {
    "own-steps": {QA_CHECKLIST: 1},
    "read-back": {QA_CHECKLIST: 1},
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

@pytest.mark.parametrize("record", ["baseline-7a6cb17-harness-1f24df1", "candidate-1f24df1"])
def test_the_recorded_calls_re_grade_to_the_recorded_verdicts(tmp_path: Path, record: str) -> None:
    """The committed calls must reproduce the committed grades under the committed grader."""
    lines = [json.loads(line) for line in (CASE / "results" / f"{record}-calls.jsonl").read_text().splitlines()]
    calls: dict[str, list[dict]] = {}
    grades: dict[str, dict[str, str]] = {}
    for entry in lines:
        if "call" in entry:
            calls.setdefault(entry["run"], []).append(entry["call"])
        else:
            grades.setdefault(entry["run"], {})[entry["expectation"]] = entry["grade"]
    assert calls and set(calls) == set(grades), "every recorded run has calls and a grade"
    assert all(set(grades[name]) == ({"new-round", "new-round-read"} if name == "new-round"
                                     else {next(s for s in CASE_SCENARIOS if name.startswith(s))})
               for name in grades), "each run carries the grade of every expectation run.sh grades it on"
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
        for expectation, grade in grades[name].items():
            result = graded(run, expectation)
            assert result.stdout.strip().endswith(grade), f"{record} {name} {expectation}: {result.stdout}"

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


# SKL-254: interim senior-engineer handbacks get a deadline and a primary-source read.
INTERIM = ROOT / "skills" / "story-to-done" / "references" / "interim-handbacks.md"
INTERIM_STEP_0_POINTER = (
    "An interim handback from the senior engineer or a QA agent is classified first, before the checklist read-back "
    "below, under "
    "[references/interim-handbacks.md](references/interim-handbacks.md)."
)
STEP_0_CHECKLIST_READ = (
    "When a senior engineer or QA agent hands back, read that subagent's checklist file before acting on the result"
)
INTERIM_STEP_2_POINTER = (
    "An interim handback goes to [references/interim-handbacks.md](references/interim-handbacks.md) before the "
    "step 0 checklist read-back and every check below; any other handback continues here."
)
STEP_2_READ_BACK_FIRST = "When it hands back, do the step 0 checklist read-back first"
STEP_2_STOP_CLAUSE = "If it handed back blocked or the story is not in deployment review, stop and report why."
INTERIM_NO_RESUME = "So the awaited item gets the deadline below, never step 0's read-back resume."
INTERIM_DEFINITION = (
    "An interim handback is a handback from the senior engineer that names an awaited item of its own background "
    "work (a CI run, a deploy, a tracker move, a review in flight) and is neither a final handback nor blocked. "
    "Naming the awaited item does not make it a blocked handback or a stated blocker."
)
INTERIM_ORDER = (
    "The coordinator classifies an interim handback before step 0's checklist read-back and before step 2's "
    "deployment-review check and stop."
)
INTERIM_RECORD = (
    "On an interim handback the coordinator records on the todo list the awaited item, its primary source, its "
    "target state, and an absolute UTC deadline measured from receipt of the handback: the expected duration the "
    "handback states, or 30 minutes when it states none, plus the greater of 10 minutes and 50% of that duration."
)
INTERIM_CLEAR = (
    "If the engineer hands back again before the deadline, the coordinator clears the deadline and handles that "
    "handback."
)
INTERIM_READ = (
    "Otherwise, at the deadline the coordinator reads the awaited item's state from its primary source (for a CI "
    "run, the run's status from the forge; for a tracker move, the tracker), never from the subagent."
)
INTERIM_STOP = (
    "The stop report to the owner names the awaited item, its primary source, the state or read error observed at "
    "each missed deadline, and both missed deadlines."
)
INTERIM_WAIT = (
    "It never waits on the subagent's own wake-up alone: it reaches the deadline with a bounded foreground wait on "
    "the awaited item's primary source that returns at or before the deadline (for a CI run, a watch on the run "
    "under a timeout), repeated until the deadline."
)
INTERIM_WAIT_CAP = (
    "Each wait lasts the lesser of 90 seconds and the time left to the deadline less 5 seconds for process "
    "start-up, under a timeout that also bounds every read inside it, so it returns at or before the deadline, "
    "the runtime never moves it to the background, and a handback that arrives during a wait is handled when that "
    "wait returns."
)
INTERIM_NO_SHORT_WAIT = (
    "With 5 seconds or less left, it starts no further wait, lets the deadline pass, and only then makes the deadline "
    "read below, so that read never comes before the deadline."
)
INTERIM_RECEIPT = "Receipt is the coordinator's first clock read after the handback arrives."
INTERIM_STATED_BLOCKER = (
    "Step 0's stated-blocker sentence covers only the other handbacks, since neither an interim handback nor an "
    "unnamed waiting handback reaches the read-back."
)
INTERIM_PR_WATCH = (
    "When the awaited CI run belongs to a PR, it also watches the PR, so a new head and its new run are not missed "
    "([references/code-review.md](code-review.md), Watching the PR)."
)
INTERIM_VOCABULARY = (
    "interim", "awaited", "deadline", "minutes", "seconds", "primary source", "foreground", "timeout", "wake-up",
    "hour", "half an", "poll", "timer", "elapse", "expir", "end the run",
)
INTERIM_CLEAR_LATE = (
    "A handback that arrived before the deadline clears it even when the coordinator sees it only after the "
    "deadline."
)
INTERIM_LIMITS = (
    "This rule changes no step logic for final or blocked handbacks, and leaves step 2's stop clause, step 4's "
    "continuation content limits, mixed-owner stop, owner-action stop, and new-round rules, and the no-write and "
    "no-verdict constraints unchanged; it only comes before step 0's read-back, step 2's check and step 4's "
    "classification, and adds only the handback classes it defines, its own checklist reads, its own resumes and "
    "its own stops."
)


def interim_text() -> str:
    assert INTERIM.is_file(), f"missing {INTERIM.relative_to(ROOT)}"
    return " ".join(visible(INTERIM.read_text()).split())


def test_step_0_points_to_the_interim_handbacks_reference() -> None:
    step_0 = " ".join(section(visible(SKILL.read_text()), "0. Track everything on a todo list").split())
    assert INTERIM_STEP_0_POINTER in step_0


def test_step_0_classifies_an_interim_handback_before_reading_the_checklist() -> None:
    step_0 = " ".join(section(visible(SKILL.read_text()), "0. Track everything on a todo list").split())
    assert step_0.index(INTERIM_STEP_0_POINTER) < step_0.index(STEP_0_CHECKLIST_READ)


def test_step_2_points_to_the_interim_handbacks_reference_and_uses_none_of_its_vocabulary() -> None:
    step_2 = " ".join(section(SKILL.read_text(), "2. Senior engineer: implement to deployment review").split())
    assert INTERIM_STEP_2_POINTER in step_2
    # SKL-138: the pinned nested launch line names a launch mode, not the interim rule's foreground wait.
    rest = step_2.replace(INTERIM_STEP_2_POINTER, "").replace(NESTED_STEP_2, "").lower()
    for token in INTERIM_VOCABULARY + ("50%",):
        assert token not in rest, f"step 2 restates the interim rule ({token!r}) instead of pointing to it"
    for sentence in INTERIM.read_text().splitlines():
        sentence = " ".join(sentence.split())
        if len(sentence) > 40:
            assert sentence not in step_2, f"step 2 restates {sentence!r}"


def test_step_2_sends_an_interim_handback_on_before_the_read_back_and_the_stop() -> None:
    step_2 = " ".join(section(SKILL.read_text(), "2. Senior engineer: implement to deployment review").split())
    pointer = step_2.index(INTERIM_STEP_2_POINTER)
    assert pointer < step_2.index(STEP_2_READ_BACK_FIRST) < step_2.index(STEP_2_STOP_CLAUSE)


def test_an_interim_handback_never_gets_the_read_back_resume() -> None:
    assert INTERIM_NO_RESUME in interim_text()


def test_the_interim_rule_runs_wait_then_clear_then_read_then_stop() -> None:
    text = interim_text()
    phrases = (INTERIM_WAIT, INTERIM_WAIT_CAP, INTERIM_CLEAR, INTERIM_CLEAR_LATE, INTERIM_READ, INTERIM_STOP)
    positions = [text.index(phrase) for phrase in phrases]
    assert positions == sorted(positions)


def test_a_handback_seen_late_still_clears_a_deadline_it_beat() -> None:
    assert INTERIM_CLEAR_LATE in interim_text()


def test_a_ci_run_on_a_pr_is_watched_through_the_pr() -> None:
    assert INTERIM_PR_WATCH in interim_text()


def test_each_wait_is_capped_so_a_handback_during_it_is_handled() -> None:
    assert INTERIM_WAIT_CAP in interim_text()


def test_no_wait_starts_in_the_last_five_seconds() -> None:
    text = interim_text()
    assert text.index(INTERIM_WAIT_CAP) < text.index(INTERIM_NO_SHORT_WAIT) < text.index(INTERIM_CLEAR)


def test_the_interim_rule_limits_are_pinned() -> None:
    assert INTERIM_LIMITS in interim_text()


def test_the_interim_handback_definition_is_pinned() -> None:
    assert INTERIM_DEFINITION in interim_text()


def test_step_0_stated_blocker_sentence_never_covers_an_interim_handback() -> None:
    text = interim_text()
    assert text.index(INTERIM_DEFINITION) < text.index(INTERIM_STATED_BLOCKER)


def test_an_interim_handback_is_classified_before_the_read_back_and_the_step_2_check() -> None:
    assert INTERIM_ORDER in interim_text()


def test_an_interim_handback_records_a_deadline_with_its_default_and_margin() -> None:
    assert INTERIM_RECORD in interim_text()


def test_receipt_is_the_first_clock_read_after_the_handback() -> None:
    text = interim_text()
    assert text.index(INTERIM_RECORD) < text.index(INTERIM_RECEIPT)


def test_a_handback_before_the_deadline_clears_it() -> None:
    assert INTERIM_CLEAR in interim_text()


def test_the_deadline_reads_the_primary_source_never_the_subagent() -> None:
    assert INTERIM_READ in interim_text()


def test_the_two_miss_stop_report_names_the_item_its_source_each_state_and_both_deadlines() -> None:
    assert INTERIM_STOP in interim_text()


def test_the_deadline_is_reached_by_a_bounded_foreground_wait() -> None:
    assert INTERIM_WAIT in interim_text()


# SKL-255: a concluded awaited item resumes the engineer at the deadline instead of stopping.
INTERIM_CONCLUDED_RESUME = (
    "If the awaited item has concluded (success, failure, or cancelled), the coordinator resumes the same engineer "
    "with the awaited item and its observed conclusion, records the resume on the todo list, and handles the "
    "engineer's next handback as usual."
)
# SKL-256 replaces the first-miss stop with one re-deadline and a two-miss escalation stop.
INTERIM_MISS = (
    "A deadline is missed when the item is still pending or its primary source is unreadable; the coordinator "
    "counts the miss against that awaited item and records on the todo list the deadline, the state or read error "
    "observed, and the count."
)
INTERIM_REDEADLINE = (
    "After the first miss the coordinator records on the todo list a new deadline measured from the missed deadline "
    "by the same rule, and checks again at it exactly as at the initial deadline, including the before-deadline "
    "handback, the concluded-item resume and the no-resume stop."
)
INTERIM_TWO_MISS_STOP = (
    "After the second miss on the same awaited item the coordinator stops before setting another deadline; it "
    "launches nothing further, makes no tracker write beyond the one Boundaries permits with `metrics` on, and "
    "rules on nothing."
)
INTERIM_SAME_ITEM_NO_RESET = "A repeated interim handback on the same awaited item does not reset the count;"
INTERIM_NEW_ITEM_NEW_COUNT = "an interim handback on a different awaited item starts a new count."
INTERIM_NO_RESUME_STOP = (
    "If the runtime cannot resume the engineer, the coordinator reports the limitation and the observed state and "
    "stops; it spawns no new subagent for a deadline resume."
)
INTERIM_RESUME_CAP = "A deadline resume does not count against step 0's read-back resume cap."


def test_a_concluded_awaited_item_resumes_the_same_engineer() -> None:
    text = interim_text()
    assert text.index(INTERIM_READ) < text.index(INTERIM_CONCLUDED_RESUME)


def test_a_missed_deadline_is_counted_and_recorded_with_its_observed_state() -> None:
    text = interim_text()
    assert text.index(INTERIM_READ) < text.index(INTERIM_MISS) < text.index(INTERIM_REDEADLINE)


def test_a_first_miss_sets_one_new_deadline_from_the_missed_deadline() -> None:
    text = interim_text()
    assert text.index(INTERIM_READ) < text.index(INTERIM_REDEADLINE) < text.index(INTERIM_STOP)


def test_a_second_miss_on_the_same_item_stops_before_another_deadline_with_no_tracker_write() -> None:
    text = interim_text()
    assert text.index(INTERIM_REDEADLINE) < text.index(INTERIM_TWO_MISS_STOP) < text.index(INTERIM_STOP)


def test_a_repeated_interim_handback_on_the_same_item_does_not_reset_the_count() -> None:
    assert INTERIM_SAME_ITEM_NO_RESET in interim_text()


def test_an_interim_handback_on_a_different_item_starts_a_new_count() -> None:
    assert INTERIM_NEW_ITEM_NEW_COUNT in interim_text()


def test_a_runtime_that_cannot_resume_the_engineer_stops_without_a_new_subagent() -> None:
    assert INTERIM_NO_RESUME_STOP in interim_text()


def test_a_deadline_resume_does_not_count_against_the_read_back_resume_cap() -> None:
    assert INTERIM_RESUME_CAP in interim_text()


INTERIM_RESUME_ROW = "With `metrics` on, each deadline resume is its own launch row."
INTERIM_CONCLUDED_CATCH_ALL = (
    "An item not yet in a terminal state is pending (a CI run `requested`, `queued`, `waiting`, `pending` or "
    "`in_progress`; a tracker item still in a non-terminal state short of its target state); any terminal state "
    "counts as concluded, so a CI run `completed` with any conclusion resumes the engineer."
)
INTERIM_DEADLINE_BLOCK = (
    INTERIM_READ, INTERIM_CONCLUDED_RESUME, INTERIM_CONCLUDED_CATCH_ALL, INTERIM_NO_RESUME_STOP, INTERIM_RESUME_CAP, INTERIM_RESUME_ROW,
    INTERIM_MISS, INTERIM_REDEADLINE, INTERIM_TWO_MISS_STOP, INTERIM_SAME_ITEM_NO_RESET, INTERIM_NEW_ITEM_NEW_COUNT,
    INTERIM_STOP,
)


def test_with_metrics_on_each_deadline_resume_is_its_own_launch_row() -> None:
    assert INTERIM_RESUME_ROW in interim_text()


def test_an_unfinished_item_is_pending_and_any_terminal_state_counts_as_concluded() -> None:
    assert INTERIM_CONCLUDED_CATCH_ALL in interim_text()


def test_the_deadline_rule_states_each_outcome_once_in_one_uninterrupted_block() -> None:
    text = interim_text()
    for phrase in INTERIM_DEADLINE_BLOCK:
        assert text.count(phrase) == 1, f"{phrase!r} must appear exactly once"
    assert " ".join(INTERIM_DEADLINE_BLOCK) in text


def test_no_other_sentence_in_the_rule_stops_or_halts() -> None:
    body = " ".join(line for line in INTERIM.read_text().splitlines() if not line.startswith("#"))
    sentences = re.split(r"(?<=\.)\s+", " ".join(body.split()))
    stops = [s for s in sentences if "stop" in s.lower() or "halt" in s.lower()]
    assert stops == [
        INTERIM_ORDER, INTERIM_NO_RESUME_STOP, INTERIM_REDEADLINE, INTERIM_TWO_MISS_STOP, INTERIM_STOP,
        UNNAMED_SECOND, UNNAMED_NO_RESUME_STOP, STALE_BOUND, STALE_NO_RESUME_STOP, INTERIM_LIMITS,
    ]


# SKL-257: the interim-handback rule covers a QA agent waiting on its own background work.
INTERIM_QA_SCOPE = (
    "A QA agent's handback that names an awaited item of its own background work (for example its evidence PR's "
    "review-of-record gate or CI run) and is neither a final handback nor blocked is an interim handback too."
)
INTERIM_QA_MIXED = (
    "A QA agent's handback that also names a failed item, or an outstanding item owned by anyone other than that QA "
    "agent (an awaited item of its own background work counts as its own), is not an interim handback; it goes to "
    "step 0's checklist read-back and step 4 as usual."
)
INTERIM_QA_ORDER = (
    "The coordinator classifies a QA agent's interim handback before step 0's checklist read-back of that QA agent "
    "and before step 4's classification."
)
INTERIM_STEP_3_POINTER = (
    "A QA agent's interim handback goes to [references/interim-handbacks.md](references/interim-handbacks.md) "
    "first; any other handback continues here."
)
STEP_3_READ_BACK_FIRST = "When it hands back, do the step 0 checklist read-back first, then read the story's state yourself."
INTERIM_QA_IN_PLACE = (
    "For a QA agent's interim handback the deadline rule above applies with that QA agent in place of the engineer, "
    "except for the resume message."
)
INTERIM_QA_RESUME = (
    "At a concluded deadline the coordinator resumes the same QA agent with a message that states only that the "
    "round is unfinished and names the round's scratch subdirectory and the awaited item; it carries nothing else "
    "the coordinator observed (no conclusion, no verdict, no earlier round's conclusions, no senior engineer "
    "handback)."
)
INTERIM_QA_COUNTS = (
    "A QA deadline resume does not increment the QA round count, does not count against step 0's read-back resume "
    "cap, and does not consume step 4's \"once per observed change to the remainder\" continuation allowance."
)
INTERIM_QA_ROW = "With `metrics` on, each QA deadline resume is its own launch row within that round."
INTERIM_QA_CONCLUDED = (
    "A QA agent's handback that names an awaited item the coordinator already observed concluded at an earlier "
    "deadline of that round is not an interim handback, since that item is no longer awaited; it goes to step 0's "
    "checklist read-back and step 4 as usual, so step 0's read-back resume cap and step 4's no-progress rule bound it."
)


def test_the_interim_definition_covers_a_qa_agents_own_background_work() -> None:
    text = interim_text()
    assert text.index(INTERIM_DEFINITION) < text.index(INTERIM_QA_SCOPE) < text.index(INTERIM_STATED_BLOCKER)


def test_a_qa_handback_that_also_names_a_failed_or_foreign_owned_item_is_not_interim() -> None:
    text = interim_text()
    assert text.index(INTERIM_QA_SCOPE) < text.index(INTERIM_QA_MIXED) < text.index(INTERIM_STATED_BLOCKER)


def test_step_3_points_to_the_interim_handbacks_reference_and_restates_none_of_it() -> None:
    step_3 = " ".join(section(visible(SKILL.read_text()), "3. QA agent: verify the deployed story").split())
    assert INTERIM_STEP_3_POINTER in step_3
    assert step_3.index(INTERIM_STEP_3_POINTER) < step_3.index(STEP_3_READ_BACK_FIRST)
    # SKL-138: the pinned nested launch line names a launch mode, not the interim rule's foreground wait.
    rest = step_3.replace(INTERIM_STEP_3_POINTER, "").replace(NESTED_STEP_3, "").lower()
    for token in INTERIM_VOCABULARY + (
        "50%", "before step 4", "before the step 0", "before step 0", "round count", "increment",
    ):
        assert token not in rest, f"step 3 restates the interim rule ({token!r}) instead of pointing to it"


def test_a_qa_interim_handback_is_classified_before_the_read_back_and_step_4() -> None:
    text = interim_text()
    assert text.index(INTERIM_ORDER) < text.index(INTERIM_QA_ORDER) < text.index(INTERIM_NO_RESUME)


def test_a_qa_deadline_resume_carries_only_the_unfinished_round_its_subdirectory_and_the_awaited_item() -> None:
    text = interim_text()
    assert text.index(INTERIM_STOP) < text.index(INTERIM_QA_IN_PLACE) < text.index(INTERIM_QA_RESUME)


def test_a_qa_deadline_resume_leaves_the_round_count_and_both_resume_caps_alone() -> None:
    text = interim_text()
    assert text.index(INTERIM_QA_RESUME) < text.index(INTERIM_QA_COUNTS) < text.index(INTERIM_LIMITS)


def test_with_metrics_on_each_qa_deadline_resume_is_a_launch_row_within_its_round() -> None:
    assert INTERIM_QA_ROW in interim_text()


def test_a_qa_handback_on_an_item_already_observed_concluded_is_not_interim() -> None:
    text = interim_text()
    assert text.index(INTERIM_QA_RESUME) < text.index(INTERIM_QA_CONCLUDED) < text.index(INTERIM_LIMITS)


def test_an_unclosed_html_comment_hides_the_rest_of_the_file() -> None:
    assert visible("kept <!-- closed --> kept <!-- unclosed hides this") == "kept  kept "


def test_each_qa_interim_contract_appears_exactly_once() -> None:
    text = interim_text()
    for phrase in (
        INTERIM_QA_SCOPE, INTERIM_QA_MIXED, INTERIM_QA_ORDER, INTERIM_QA_IN_PLACE,
        INTERIM_QA_RESUME, INTERIM_QA_COUNTS, INTERIM_QA_ROW, INTERIM_QA_CONCLUDED,
    ):
        assert text.count(phrase) == 1, phrase
    skill = " ".join(visible(SKILL.read_text()).split())
    assert skill.count(INTERIM_STEP_3_POINTER) == 1
    assert skill.count(QA_ROUND_EXCEPTION) == 1


# SKL-357: a waiting handback that names no awaited item, and a checklist that stops updating.
ASSETS = ROOT / "skills" / "story-to-done" / "assets"
RENDER_BRIEF = ROOT / "skills" / "story-to-done" / "scripts" / "render-brief.py"
WAITING_BULLET = (
    "- A handback that is neither final nor blocked and waits on your own background work must name the awaited "
    "item, its primary source and its expected duration."
)
RENDER_CASES = {
    "engineer-deployed": ("--role", "engineer", "--path", "deployed"),
    "engineer-no-deployment": ("--role", "engineer", "--path", "no-deployment"),
    "engineer-spike": ("--role", "engineer", "--path", "spike"),
    "qa-deployed": ("--role", "qa", "--path", "deployed", "--round", "1", "--environment", "dev"),
    "qa-deployed-default": ("--role", "qa", "--path", "deployed", "--round", "1"),
    "qa-deployed-round-2": ("--role", "qa", "--path", "deployed", "--round", "2", "--environment", "dev"),
    "qa-no-deployment": ("--role", "qa", "--path", "no-deployment", "--round", "1", "--commit", "0" * 40),
    "qa-spike": ("--role", "qa", "--path", "spike", "--round", "1", "--link", "https://example.com/spike"),
}
UNNAMED_DEFINITION = (
    "An unnamed waiting handback is a handback from the senior engineer or a QA agent that is neither a final "
    "handback nor blocked, says it waits on the role's own background work, and names no awaited item."
)
UNNAMED_QA_EXCLUSION = (
    "A QA agent's handback that names a failed item, or an outstanding item owned by anyone other than that QA "
    "agent (an awaited item of its own background work counts as its own), is not an unnamed waiting handback; it "
    "goes to step 0's checklist read-back and step 4 as usual."
)
DELEGATION = (
    "A senior-engineer delegation is one senior-engineer subagent from its spawn until the coordinator spawns "
    "another one for the story; a resume of the same subagent stays within the delegation."
)
UNNAMED_KEEPS_DEADLINE = (
    "An unnamed waiting handback does not clear a live deadline or reset the miss count of an item already awaited "
    "from that role."
)
UNNAMED_MISS_RECORD = (
    "The coordinator records that miss on the todo list against the role, not against any awaited item, and "
    "increments no awaited item's miss count."
)
CHECKLIST_READ_FIRST = "The read comes before any resume sent on the same handback."
CHECKLIST_READ_SAVED = (
    "The coordinator saves the contents of each read in its own scratch for the invocation and compares them byte "
    "for byte with the contents saved at the previous such read."
)
UNNAMED_STALL = "An unnamed waiting handback is a stall, never an interim handback."
UNNAMED_ORDER = (
    "The coordinator classifies an unnamed waiting handback before step 0's checklist read-back, step 2's check and "
    "step 4's classification."
)
UNNAMED_RESUME = (
    "On an unnamed waiting handback the coordinator resumes that role once, asking only for the awaited item, its "
    "primary source and its expected duration."
)
UNNAMED_RESUME_COUNTS = (
    "The naming resume carries no conclusion or verdict, does not count against step 0's read-back resume cap, does "
    "not increment a QA round count or consume step 4's continuation allowance, and with `metrics` on is its own "
    "launch row."
)
UNNAMED_ANSWER = (
    "If the answer is an interim handback as defined above, the deadline rule above applies from receipt of the "
    "answer."
)
UNNAMED_SECOND = (
    "A second unnamed waiting handback from the same role after that resume, within the same senior-engineer "
    "delegation or, for a QA agent, the same QA round, counts as a missed deadline and stops the coordinator as at a "
    "second miss under the two-miss stop above; the stop report names the role and both unnamed waiting handbacks."
)
UNNAMED_NO_RESUME_STOP = (
    "If the runtime cannot resume the role for the naming resume, the coordinator reports the limitation and stops, "
    "and spawns no new subagent."
)
CHECKLIST_READ = (
    "At each interim handback and each unnamed waiting handback the coordinator reads the role's checklist file and "
    "records on the todo list the item marked `(in progress)`, or else the first `- [ ]` item, or `none` when every "
    "item is checked, or `missing or unreadable`, and whether the contents are identical to the contents read at the "
    "previous such handback from that role (`no previous read` at the first)."
)
CHECKLIST_READ_SILENT = (
    "The read sends nothing to the role, is separate from step 0's checklist read-back, and does not count against "
    "its resume cap."
)
STALE_DEFINITION = (
    "A checklist file is stale when its contents are identical, or it is missing or unreadable, at two consecutive "
    "interim or unnamed waiting handbacks from the same role within the same senior-engineer delegation or QA round."
)
STALE_RESUME = (
    "The coordinator then sends that role one stale-checklist resume asking it to update the checklist and name what "
    "blocks it."
)
STALE_BOUND = (
    "The stale-checklist resume is sent at most once per senior-engineer delegation and once per QA round, never on "
    "a handback that gets the naming resume, and never on a handback on which the coordinator stops under Unnamed "
    "waiting handbacks; that stop takes precedence over this resume, and staleness is judged again at the next such "
    "handback on which the coordinator does not stop."
)
STALE_COUNTS = (
    "It carries no conclusion or verdict, does not count against step 0's read-back resume cap, does not increment a "
    "QA round count or consume step 4's continuation allowance, changes no awaited item's deadline or miss count, and "
    "with `metrics` on is its own launch row."
)
STALE_NO_RESUME_STOP = (
    "If the runtime cannot resume the role for the stale-checklist resume, the coordinator reports the limitation and "
    "stops, and spawns no new subagent."
)
UNNAMED_SENTENCES = (
    UNNAMED_DEFINITION, UNNAMED_QA_EXCLUSION, UNNAMED_STALL, INTERIM_STATED_BLOCKER, UNNAMED_ORDER, UNNAMED_RESUME,
    UNNAMED_RESUME_COUNTS, UNNAMED_ANSWER, UNNAMED_SECOND, UNNAMED_NO_RESUME_STOP, CHECKLIST_READ,
    CHECKLIST_READ_SILENT, STALE_DEFINITION, STALE_RESUME, STALE_BOUND, STALE_COUNTS, STALE_NO_RESUME_STOP,
    DELEGATION, UNNAMED_KEEPS_DEADLINE, UNNAMED_MISS_RECORD, CHECKLIST_READ_FIRST, CHECKLIST_READ_SAVED,
)


def rendered_brief(tmp_path: Path, case: tuple[str, ...]) -> str:
    scratch = Path(os.path.realpath(tmp_path))
    if case[1] == "engineer":
        role_dir = scratch / "senior-engineer"
    else:
        role_dir = scratch / f"qa-agent-round-{case[case.index('--round') + 1]}"
    role_dir.mkdir(exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(RENDER_BRIEF), *case, "--story", "ABC-123", "--scratch", str(scratch)],
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    brief = f"{role_dir}/{role_dir.name}-brief.md"
    assert result.stdout == brief + "\n", result.stdout
    return Path(brief).read_text()


def test_the_render_cases_cover_every_role_and_path_the_renderer_accepts() -> None:
    spec = importlib.util.spec_from_file_location("render_brief", RENDER_BRIEF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    covered = {(case[case.index("--role") + 1], case[case.index("--path") + 1]) for case in RENDER_CASES.values()}
    assert covered == {(role, path) for role in module.ROLES for path in module.PATHS}


@pytest.mark.parametrize("name", ["brief-engineer.md", "brief-qa.md"])
def test_each_base_brief_requires_a_waiting_handback_to_name_its_awaited_item(name: str) -> None:
    assert visible((ASSETS / name).read_text()).splitlines().count(WAITING_BULLET) == 1


SKILL_WAITING_BULLET = (
    "- A handback that is neither final nor blocked and is waiting on your own work names what it waits on, where "
    "you read its state, and when you expect it to finish."
)


@pytest.mark.parametrize(
    "heading", ["2. Senior engineer: implement to deployment review", "3. QA agent: verify the deployed story"]
)
def test_each_brief_list_in_the_skill_carries_the_waiting_handback_bullet(heading: str) -> None:
    assert visible(section(SKILL.read_text(), heading)).splitlines().count(SKILL_WAITING_BULLET) == 1


@pytest.mark.parametrize("case", sorted(RENDER_CASES))
def test_every_rendered_brief_carries_the_waiting_handback_bullet(case: str, tmp_path: Path) -> None:
    assert visible(rendered_brief(tmp_path, RENDER_CASES[case])).splitlines().count(WAITING_BULLET) == 1


def test_the_unnamed_waiting_handback_is_defined_with_its_qa_exclusion_and_is_a_stall() -> None:
    text = interim_text()
    order = (INTERIM_QA_MIXED, UNNAMED_DEFINITION, UNNAMED_QA_EXCLUSION, UNNAMED_STALL, INTERIM_STATED_BLOCKER)
    positions = [text.index(sentence) for sentence in order]
    assert positions == sorted(positions)


def test_an_unnamed_waiting_handback_is_classified_before_the_read_back_step_2_and_step_4() -> None:
    text = interim_text()
    assert text.index(INTERIM_QA_ORDER) < text.index(UNNAMED_ORDER) < text.index(INTERIM_RECORD)


def test_an_unnamed_waiting_handback_gets_one_naming_resume_outside_every_cap() -> None:
    text = interim_text()
    order = (INTERIM_QA_CONCLUDED, UNNAMED_RESUME, UNNAMED_RESUME_COUNTS, UNNAMED_ANSWER)
    positions = [text.index(sentence) for sentence in order]
    assert positions == sorted(positions)


def test_a_second_unnamed_waiting_handback_stops_as_a_second_miss() -> None:
    text = interim_text()
    assert text.index(INTERIM_TWO_MISS_STOP) < text.index(UNNAMED_ANSWER) < text.index(UNNAMED_SECOND)


def test_a_runtime_that_cannot_make_the_naming_resume_stops_without_a_new_subagent() -> None:
    text = interim_text()
    assert text.index(UNNAMED_SECOND) < text.index(UNNAMED_NO_RESUME_STOP) < text.index(CHECKLIST_READ)


def test_each_interim_or_unnamed_waiting_handback_reads_the_checklist_without_a_resume() -> None:
    text = interim_text()
    assert text.index(CHECKLIST_READ) < text.index(CHECKLIST_READ_SILENT) < text.index(STALE_DEFINITION)


def test_a_stale_checklist_gets_one_bounded_resume_that_yields_to_the_unnamed_stop() -> None:
    text = interim_text()
    order = (STALE_DEFINITION, STALE_RESUME, STALE_BOUND, STALE_COUNTS, STALE_NO_RESUME_STOP, INTERIM_LIMITS)
    positions = [text.index(sentence) for sentence in order]
    assert positions == sorted(positions)


STEP_2_UNNAMED_MIRROR = (
    "An unnamed waiting handback, as that reference defines it, goes there too and does not continue here."
)
STEP_3_UNNAMED_MIRROR = (
    "A QA agent's unnamed waiting handback, as that reference defines it, goes there too and does not continue here."
)


def test_steps_2_and_3_send_an_unnamed_waiting_handback_to_the_reference() -> None:
    skill = visible(SKILL.read_text())
    step_2 = " ".join(section(skill, "2. Senior engineer: implement to deployment review").split())
    step_3 = " ".join(section(skill, "3. QA agent: verify the deployed story").split())
    assert step_2.count(STEP_2_UNNAMED_MIRROR) == 1
    assert step_3.count(STEP_3_UNNAMED_MIRROR) == 1
    assert step_2.index(INTERIM_STEP_2_POINTER) < step_2.index(STEP_2_UNNAMED_MIRROR) < step_2.index(
        STEP_2_READ_BACK_FIRST
    )
    assert step_3.index(INTERIM_STEP_3_POINTER) < step_3.index(STEP_3_UNNAMED_MIRROR) < step_3.index(
        STEP_3_READ_BACK_FIRST
    )


STEP_0_UNNAMED_MIRROR = (
    "So is an unnamed waiting handback as that reference defines it, which never reaches the read-back or spends "
    "its resume cap."
)


def test_step_0_classifies_an_unnamed_waiting_handback_before_the_read_back() -> None:
    step_0 = " ".join(section(visible(SKILL.read_text()), "0. Track everything on a todo list").split())
    assert step_0.count(STEP_0_UNNAMED_MIRROR) == 1
    assert step_0.index(INTERIM_STEP_0_POINTER) < step_0.index(STEP_0_UNNAMED_MIRROR) < step_0.index(
        STEP_0_CHECKLIST_READ
    )


def test_the_unnamed_section_scopes_the_delegation_and_keeps_a_live_deadline() -> None:
    text = interim_text()
    order = (INTERIM_QA_CONCLUDED, DELEGATION, UNNAMED_KEEPS_DEADLINE, UNNAMED_RESUME)
    positions = [text.index(sentence) for sentence in order]
    assert positions == sorted(positions)


def test_a_second_unnamed_waiting_handback_is_a_miss_of_the_role_not_of_an_item() -> None:
    text = interim_text()
    assert text.index(UNNAMED_SECOND) < text.index(UNNAMED_MISS_RECORD) < text.index(UNNAMED_NO_RESUME_STOP)


def test_the_checklist_read_precedes_any_resume_and_compares_saved_bytes() -> None:
    text = interim_text()
    order = (CHECKLIST_READ_SILENT, CHECKLIST_READ_FIRST, CHECKLIST_READ_SAVED, STALE_DEFINITION)
    positions = [text.index(sentence) for sentence in order]
    assert positions == sorted(positions)


def test_only_the_stale_bound_relates_the_naming_and_stale_checklist_resumes() -> None:
    body = " ".join(line for line in visible(INTERIM.read_text()).splitlines() if not line.startswith("#"))
    sentences = re.split(r"(?<=\.)\s+", " ".join(body.split()))
    both = [s for s in sentences if "naming resume" in s and "stale-checklist resume" in s]
    assert both == [STALE_BOUND]


def test_each_unnamed_and_checklist_contract_appears_exactly_once() -> None:
    text = interim_text()
    for sentence in UNNAMED_SENTENCES:
        assert text.count(sentence) == 1, sentence


# SKL-357: a digest of the whole interim-handbacks reference, so an added overriding sentence fails too.
INTERIM_SHA256 = "9918637916c5941a58bef867eb57a4590741bbb50df0ecc207808d5c13c65d5f"


def test_the_interim_handbacks_reference_is_pinned() -> None:
    assert hashlib.sha256(INTERIM.read_bytes()).hexdigest() == INTERIM_SHA256


# SKL-155: the `qa-round-cap` argument stops the loop at the cap-th counted QA round that ends in
# `in_progress`, before the hand-back, and asks the user how many further rounds to run.
QA_ROUND_CAP_ROW = (
    "| `qa-round-cap` | the number of counted QA rounds after which the loop stops and asks the user | `3` |"
)
QA_ROUND_CAP_GIVEN = (
    '- `qa-round-cap` is given as `qa-round-cap=<n>` or in plain words about capping QA rounds ("cap QA at <n> '
    'rounds" and "stop after <n> failed QA rounds" mean <n>); `python3 <skill dir>/scripts/qa-round-cap.py validate '
    'qa-round-cap=<n>` exits 2 unless <n> is a positive integer; run step 4\'s `arm` once, before the first step 3.'
)
QA_ROUND_CAP_ASK = "- Ask the user about an invalid value and about any other phrasing about the cap; never guess."
QA_ROUND_CAP_RESOLVE = "- Resolve `qa-round-cap` before step 0 creates the todo list; it sets no model or effort."
QA_ROUND_CAP_ECHO = "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at any stop, including one before step 0)."
# SKL-284: qa-round-cap.py counts the rounds; the bullet calls it and relays its stdout line.
CAP_COUNT = (
    "Arguments orders `python3 <skill dir>/scripts/qa-round-cap.py arm --story <STORY_ID> "
    "--cap <n> --in-progress '<profile.tracker.states.in_progress>' --state-dir <scratch>`; when a round ends here, "
    "run `python3 <skill dir>/scripts/qa-round-cap.py record --story <STORY_ID> --state-dir <scratch>`, relaying its "
    "stdout line, never a tracker payload."
)
CAP_STOP = "When `record` prints `reached=yes`, stop before the hand-back below and launch nothing further."
CAP_PAYLOAD = (
    "The stop report gives, per round, every failed item as QA recorded it in the tracker, re-read from the tracker "
    "rather than taken from a handback (the item, its verdict, and the evidence it cites)."
)
CAP_PR = (
    "It also gives, per PR, the link and head SHA, re-read from the tracker and the forge rather than taken from a "
    "handback, reusing the merge reads steps 2 and 3 already make."
)
CAP_ASK = (
    "The stop report asks the user how many further rounds to run or whether to stop, and waits for the reply; a "
    "reply that does not say how many rounds or that it is a stop, or that gives an invalid value, is asked about "
    "again, never guessed."
)
CAP_REARM = (
    'On "N additional rounds", run `python3 <skill dir>/scripts/qa-round-cap.py rearm --story <STORY_ID> '
    "--additional-rounds <N> --state-dir <scratch>`; on exit 0, relay its stdout line and resume the pending hand-back "
    "below with every item "
    "failed so far; the next QA round runs with a new QA agent."
)
CAP_LEFT = (
    'On "stop", end the invocation with the story left in the state QA left it: '
    "`profile.tracker.states.in_progress`, failed items outstanding, the owner deciding next."
)
CAP_HISTORY = "Each later stop report gives every round `record` counted so far, across re-arms."
CAP_REREAD = (
    "The reply never overrides the tracker state: on a `record` or `rearm` `state=` `profile.tracker.states.done`, "
    "apply the `profile.tracker.states.done` bullet above; on any other non-zero exit of the script, report its "
    "stderr line and stop."
)
CAP_NO_WRITE = (
    "In either case the coordinator writes nothing to the tracker beyond what the Boundaries permit, rules on no "
    "item, and relays no verdict of its own."
)
README_CAP_CLAUSE = (
    "a `qa-round-cap` argument, `3` by default, stops the loop and asks the owner after that many failed QA rounds; "
    "a `metrics` switch"
)


def arguments_lines() -> list[str]:
    return section(SKILL.read_text(), "Arguments").splitlines()


def in_progress_bullet() -> str:
    bullet = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))["`profile.tracker.states.in_progress`"]
    return " ".join(bullet.split())


def test_qa_round_cap_row_defaults_to_three() -> None:
    assert QA_ROUND_CAP_ROW in arguments_lines()


def test_qa_round_cap_is_given_as_key_value_or_plain_words_with_a_positive_integer() -> None:
    assert QA_ROUND_CAP_GIVEN in arguments_lines()


def test_qa_round_cap_other_phrasing_and_invalid_values_are_asked_about() -> None:
    assert QA_ROUND_CAP_ASK in arguments_lines()


def test_qa_round_cap_resolves_before_step_0_and_sets_no_model_or_effort() -> None:
    assert QA_ROUND_CAP_RESOLVE in arguments_lines()


def test_qa_round_cap_is_echoed_in_the_todo_list_and_every_closing_report() -> None:
    assert QA_ROUND_CAP_ECHO in arguments_lines()
    close_out = " ".join(section(SKILL.read_text(), "5. Close out").split())
    assert "the `qa-round-cap: <n>` line" in close_out


def test_qa_rounds_are_armed_and_recorded_by_the_script() -> None:
    assert CAP_COUNT in in_progress_bullet()


def test_the_cap_stop_is_inside_the_in_progress_bullet_before_the_hand_back_with_no_sixth_bullet() -> None:
    assert in_order(
        in_progress_bullet(),
        "Those failed items are the issues to fix.",
        CAP_STOP,
        "Hand them back to the senior engineer",
    )
    assert len(state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))) == 5


def test_the_stop_report_gives_every_failed_item_per_round() -> None:
    assert CAP_PAYLOAD in in_progress_bullet()


def test_the_stop_report_gives_each_pr_link_and_head_sha_from_the_tracker_and_forge() -> None:
    assert CAP_PR in in_progress_bullet()


def test_the_cap_stop_asks_and_waits_and_offers_re_arm_or_stop() -> None:
    bullet = in_progress_bullet()
    assert in_order(bullet, CAP_STOP, CAP_ASK, CAP_REARM, "Hand them back to the senior engineer")


def test_a_cap_stop_waiting_for_the_reply_defers_the_metrics_summary_to_the_end_of_the_invocation() -> None:
    lines = PROTOCOL.read_text().splitlines()
    assert METRICS_CAP_STOP in lines
    assert lines.index(METRICS_CAP_STOP) == lines.index(METRICS_CLOSING_REPORT) + 1


def test_a_re_arm_acts_on_the_state_rearm_reads_before_resuming_the_hand_back() -> None:
    assert in_order(in_progress_bullet(), CAP_REARM, CAP_REREAD, "Hand them back to the senior engineer")


def test_a_re_arm_keeps_numbering_rounds_and_every_later_stop_report_gives_them_all() -> None:
    assert in_order(in_progress_bullet(), CAP_REARM, CAP_HISTORY, "Hand them back to the senior engineer")


def test_a_stop_leaves_the_story_in_progress_for_the_owner_and_the_coordinator_writes_nothing() -> None:
    bullet = in_progress_bullet()
    assert in_order(bullet, CAP_REARM, CAP_LEFT, CAP_NO_WRITE, "Hand them back to the senior engineer")


def test_readme_row_names_the_qa_round_cap_and_its_default_before_the_metrics_clause() -> None:
    assert README_CAP_CLAUSE in readme_row()


# SKL-296: step 4 puts each `pending owner ruling` item (qa-verification step 4, SKL-156) to the user,
# keeps it out of every engineer hand-back, lists it apart in the cap stop report, and the done
# read-back rejects a completion with a pending item or one set on an AC amendment alone.
# Each pin is a whole source line with its bullet indentation.
STEP_4_HEADING = "4. Act on the QA outcome"
FAILED_ITEMS_LINE = "  Those failed items are the issues to fix."
PENDING_IN_PROGRESS = (
    "  Items QA listed apart as `pending owner ruling` are not failed items: put each to the user as the "
    "`profile.tracker.states.in_deployment_review` bullet below does, while the hand-back below goes on with the "
    "failed items alone."
)
PENDING_CAP_REPORT = (
    "  It lists apart, per round, each item QA recorded as `pending owner ruling`, with the AC or DoD text QA "
    "quoted and each reading with its verdict, as QA recorded them in the tracker, never among the failed items."
)
HAND_BACK_LINE = (
    "  Hand them back to the senior engineer: resume the same subagent if the runtime can, else spawn a new clean, "
    "neutral one on the same seat with the step 2 brief."
)
HAND_BACK_BRIEF_LINE = (
    "  Either way, add to the hand-back brief each failed item as QA recorded it on the story (the item, its "
    "verdict, and the evidence it cites), and instruct the engineer to fix them through `engineering-workflow` on "
    "this story and take it back to `profile.tracker.states.in_deployment_review`."
)
PENDING_HAND_BACK_OMITTED = (
    "  Leave out of every hand-back brief each item still `pending owner ruling` in QA's latest record, including "
    "one carried from an earlier failed round."
)
PENDING_REPORT = (
    "  For each item QA recorded as `pending owner ruling`, that report puts the item to the user with the AC or "
    "DoD text QA quoted and each reading with its verdict, as QA recorded them in the tracker."
)
PENDING_NO_RULING = (
    "  The coordinator rules on none of those items and relays none of them to the senior engineer or a QA agent; "
    "a ruling reaches QA only as the product owner's dated AC amendment in the tracker, followed by a new QA round."
)
DONE_READ_BACK_LINE = (
    "  On read-back every AC and DoD box is ticked, QA's handback rules every item verified, and, when "
    "`profile.qa.evidence_dir` is set, the evidence PR is merged on the head its review of record covered."
)
DONE_NO_AMENDMENT = (
    "  Done is never set on an AC amendment alone, so the record also needs no item still `pending owner ruling` "
    "in QA's handback or its record in the tracker, and a verified verdict, from a new QA round (a new QA agent on "
    "the unchanged step 3 brief) run after the product owner's dated AC amendment, for each item that amendment "
    "ruled on."
)
DONE_ALL_HOLD = "  If all of these hold, go to step 5; if any does not, report the mismatch and stop."
# The line DONE_ALL_HOLD replaces: the done read-back now checks more than three conditions.
DONE_OLD_ALL_HOLD = "  If all three hold, go to step 5; if any does not, report the mismatch and stop."
CONTINUATION_LINES = (
    "  " + STEP4_RESUME,
    "  " + STEP4_CARRY,
    "  A `command` or `codex` QA seat is never resumed, so its continuation is a new launch on the same seat "
    "whose prompt file is the step 3 brief followed by that continuation message; it is still the same round's "
    "continuation under every rule in this bullet.",
    "  Because the new process carries none of the earlier one's working state, its prompt file also tells it to "
    "read that round's existing checklist in the named subdirectory and the story's open evidence PR, if any, "
    "before acting, and to continue from the first unfinished item, never rewriting the checklist or opening a "
    "second evidence PR.",
)
# The pending owner ruling record's shape: the ruling itself, a competing reading, a reading with its
# verdict, QA's quoted text, or a pending item. The bare word "reading" is not the shape.
RECORD_SHAPE = re.compile(
    r"pending owner ruling|\brulings?\b|\bcompeting readings?\b|\breadings? with (?:its|their|the) verdicts?\b"
    r"|\bquoted (?:AC or DoD )?text\b|\btext QA quoted\b|\bpending items?\b",
    re.IGNORECASE,
)


def step_4_lines() -> list[str]:
    return section(SKILL.read_text(), STEP_4_HEADING).splitlines()


def bullet_lines(label: str) -> list[str]:
    return state_bullets(section(SKILL.read_text(), STEP_4_HEADING))[label].splitlines()


def follows(lines: list[str], before: str, after: str) -> bool:
    return before in lines and after in lines and lines.index(after) == lines.index(before) + 1


def test_in_deployment_review_report_puts_each_pending_item_to_the_user_and_rules_on_none() -> None:
    lines = bullet_lines("`profile.tracker.states.in_deployment_review`")
    assert follows(lines, "  " + STEP4_OTHER_OWNER, PENDING_REPORT), (
        "the report-and-stop must put each pending item to the user right after it is stated"
    )
    assert follows(lines, PENDING_REPORT, PENDING_NO_RULING), "the coordinator must rule on and relay no pending item"


def test_in_progress_puts_pending_items_to_the_user_while_the_hand_back_goes_on() -> None:
    lines = bullet_lines("`profile.tracker.states.in_progress`")
    assert follows(lines, FAILED_ITEMS_LINE, PENDING_IN_PROGRESS), (
        "pending items must be set apart from the failed items before the cap and the hand-back"
    )
    assert lines.index(PENDING_IN_PROGRESS) < lines.index("  " + CAP_STOP) < lines.index(HAND_BACK_LINE)


def test_every_hand_back_brief_leaves_out_pending_items_from_every_round() -> None:
    lines = bullet_lines("`profile.tracker.states.in_progress`")
    assert follows(lines, HAND_BACK_BRIEF_LINE, PENDING_HAND_BACK_OMITTED)
    assert lines.index("  " + CAP_REARM) < lines.index(PENDING_HAND_BACK_OMITTED), (
        "the omission must cover the hand-back a re-arm resumes with every item failed so far"
    )


def test_the_cap_stop_report_lists_pending_items_apart() -> None:
    lines = bullet_lines("`profile.tracker.states.in_progress`")
    assert follows(lines, "  " + CAP_PAYLOAD, PENDING_CAP_REPORT)


def test_the_done_read_back_rejects_a_pending_item_and_a_completion_on_an_amendment_alone() -> None:
    lines = bullet_lines("`profile.tracker.states.done`")
    assert follows(lines, DONE_READ_BACK_LINE, DONE_NO_AMENDMENT)
    assert follows(lines, DONE_NO_AMENDMENT, DONE_ALL_HOLD)
    assert DONE_OLD_ALL_HOLD not in step_4_lines(), "the three-condition line DONE_ALL_HOLD replaces is still stated"


def test_the_record_shape_pattern_matches_the_record_and_not_the_bare_word_reading() -> None:
    for line in (PENDING_REPORT, PENDING_CAP_REPORT, PENDING_NO_RULING, "a competing reading of AC 2"):
        assert RECORD_SHAPE.search(line), f"the record shape pattern misses: {line}"
    for line in ("QA is reading the story", "the step 0 read-back", "each reading of the checklist"):
        assert not RECORD_SHAPE.search(line), f"the record shape pattern matches the bare word: {line}"


# QA's brief is unchanged by a ruling: a ruling reaches QA only as the product owner's dated AC amendment
# in the tracker. A record-shape scan cannot catch every paraphrase of a ruling or of a pending item, so the
# step 3 section and the two step 4 bullets that brief QA and the engineer are also pinned whole; change a
# digest only together with a reviewed change to the text it covers.
STEP_3_HEADING = "3. QA agent: verify the deployed story"
# SKL-138 re-baselined this digest for the step 3 nested launch line (NESTED_STEP_3), which carries no ruling.
# SKL-357 re-pinned it for the step 3 unnamed-waiting-handback pointer and the plural "resumes" exception.
# SKL-35 re-pinned it for the step 3 read-back's expected-author selection rule, which carries no ruling.
STEP_3_SHA256 = "0fbe54d0c798f259a1dff5063bdd8c20ddf87eacd01933ffc1f87d2e0245652f"
# SKL-138 re-pinned IN_PROGRESS_SHA256 for the step 4 nested launch line (NESTED_STEP_4), which carries no pending item.
# SKL-346 re-pinned IN_PROGRESS_SHA256 for the arbitration ledger hand-back lines, which carry no pending item.
IN_PROGRESS_SHA256 = "40f0ab4f13d839dfa464e93be4b26b108ce82ec862e6e16bac48cae91ce2281c"
# SKL-356 re-pinned IN_DEPLOYMENT_REVIEW_SHA256 for the owner-wait deferral line (OWNER_WAIT_DEFER), which carries no pending item.
IN_DEPLOYMENT_REVIEW_SHA256 = "6ed2ebf62b1e00190b69f18eb7e619a5c1e973ce3b7ff64b76e6daf2b50e7955"
# The only lines of a state bullet that may state the pending owner ruling record.
IN_DEPLOYMENT_REVIEW_RECORD_LINES = ("  " + STEP4_OTHER_OWNER, PENDING_REPORT, PENDING_NO_RULING)
IN_PROGRESS_RECORD_LINES = (PENDING_IN_PROGRESS, PENDING_CAP_REPORT, PENDING_HAND_BACK_OMITTED)


def record_shape_offenders(lines: list[str], allowed: tuple[str, ...]) -> list[str]:
    return [line for line in lines if line not in allowed and RECORD_SHAPE.search(line)]


def digest(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def test_the_qa_brief_source_carries_no_pending_ruling_record() -> None:
    body = section(SKILL.read_text(), STEP_3_HEADING)
    offenders = [line for line in body.splitlines() if RECORD_SHAPE.search(line)]
    assert not offenders, f"the QA brief source carries a ruling, a competing reading or a pending item: {offenders}"
    assert hashlib.sha256(body.encode()).hexdigest() == STEP_3_SHA256, (
        "the step 3 QA brief source changed; a ruling must never reach QA through it"
    )


def test_the_continuation_message_carries_no_pending_ruling_record() -> None:
    lines = bullet_lines("`profile.tracker.states.in_deployment_review`")
    for line in CONTINUATION_LINES + IN_DEPLOYMENT_REVIEW_RECORD_LINES:
        assert line in lines, f"the pinned line moved or changed: {line}"
    offenders = record_shape_offenders(lines, IN_DEPLOYMENT_REVIEW_RECORD_LINES)
    assert not offenders, f"a line outside the owner report carries the pending record: {offenders}"
    assert digest(lines) == IN_DEPLOYMENT_REVIEW_SHA256, (
        "the `in_deployment_review` bullet changed; no line of it may carry a pending item into a continuation"
    )


def test_the_engineer_hand_back_instruction_carries_no_pending_item() -> None:
    lines = bullet_lines("`profile.tracker.states.in_progress`")
    for line in (HAND_BACK_LINE, HAND_BACK_BRIEF_LINE, "  " + CAP_REARM) + IN_PROGRESS_RECORD_LINES:
        assert line in lines, f"the pinned line moved or changed: {line}"
    offenders = record_shape_offenders(lines, IN_PROGRESS_RECORD_LINES)
    assert not offenders, f"a hand-back line carries a pending item: {offenders}"
    assert digest(lines) == IN_PROGRESS_SHA256, (
        "the `in_progress` bullet changed; no line of it may carry a pending item into a hand-back"
    )


# SKL-270: step 1 selects the run's path with select-path.py after the terminal-state stops and
# before the starting point, and the `path:` line goes in the todo list and every end-state report.
# SKL-270 AC7: the recorded step 12 `path:` line is passed in every state step 1 routes to a role,
# not only in_deployment_review, so a reopened story keeps its path.
RECORDED_PATH_LINE = (
    "In every state that routes to step 2 or step 3 below, add `--recorded-path` with the value of "
    "the latest `engineering-workflow` step 12 note line whose whole text is exactly "
    "`path: spike`, `path: no-deployment` or `path: deployed`, whenever such a step 12 note exists, and add "
    "nothing otherwise, so a reopened story, spike included, keeps its path."
)
# SKL-270 AC8: a role's `ask:` handback keeps the path step 1 selected; `path: unresolved` is only
# for a run that stops before selection.
ROLE_ASK_LINE = (
    "When a spawned role's handback reports an `ask:` line, stop, and quote that line in the report of that "
    "end state with the `path: <value>` line, `<value>` being the path this step selected."
)
UNRESOLVED_LINE = (
    "Report `path: unresolved` only for a run that stops before this step selects a path, in this step or an "
    "earlier one; in this step that is an `ask:` line the user does not answer with one of the three values, "
    "or exit 16 or any other nonzero exit status."
)
# The closing report of every end state, which the role-ask rule writes to at a stop.
CLOSING_REPORT_PHRASE = "the step 5 report, or the report made at any stop, including one before step 0"
STEP_1_PATH_LINES = [
    "- `profile.tracker.states.done`: report that there is nothing to do and stop.",
    "- `profile.tracker.states.blocked`, `profile.tracker.states.canceled`, or "
    "`profile.tracker.states.duplicate`: report the state and stop.",
    "Otherwise select the run's path before any role is spawned.",
    "From inside the target repository, run `python3 <skill dir>/scripts/select-path.py --title='<story title>'`, "
    "where `<skill dir>` is the absolute directory your runtime loaded this skill from.",
    "Add `--label='<name>'` for each label name the story carries as read from the tracker, under the "
    "differing-team rule in [references/linear.md](references/linear.md) \"Team resolution\"; the script "
    "compares names only.",
    "Write each `'` inside the title or a label as `'\\''`, so the shell expands nothing in either.",
    RECORDED_PATH_LINE,
    "The script prints one line, the path or an `ask:` line, and exits 0; any other exit status is no path: "
    "stop and report its stderr line.",
    "On an `ask:` line, ask the user, accept only `spike`, `no-deployment` or `deployed` as the answer, which "
    "is the path, and spawn no role until answered.",
    "Never infer a path from prose, and read one only from an exact `path:` line as above.",
    ROLE_ASK_LINE,
    UNRESOLVED_LINE,
    "The selected path governs the whole run.",
    "Then pick the starting point:",
    "- `profile.tracker.states.in_deployment_review`: implementation already reached deployment review; "
    "go to step 3.",
    "- Any other state: go to step 2.",
]
PATH_ARGUMENT_LINE = (
    "- Write the `path: <value>` line step 1 selects in the same two places, as `path: unresolved` until "
    "step 1 selects it, including in the end-state report of a run that stops before then."
)


def step_1_lines() -> list[str]:
    return section(SKILL.read_text(), "1. Read the story and pick the starting point").splitlines()


def test_step_1_selects_the_path_with_the_script_in_order() -> None:
    lines = step_1_lines()
    positions = []
    for line in STEP_1_PATH_LINES:
        assert line in lines, f"the pinned step 1 line moved or changed: {line}"
        positions.append(lines.index(line))
    assert positions == sorted(positions), "step 1's path lines are out of order"


# Step 1 holds no unpinned addition and no duplicated pin: each pinned line occurs once, and its
# non-blank lines other than STEP_1_PATH_LINES hash to this value, so a sentence that contradicts
# or repeats a pinned path rule cannot be added without updating the test.
STEP_1_UNPINNED_SHA256 = "e27c716c4306ab46aee1a3f1c57357003d656fbcc3dc808bc6d6c03c40726ca6"


def test_step_1_has_no_unpinned_or_repeated_line() -> None:
    lines = step_1_lines()
    repeated = [line for line in STEP_1_PATH_LINES if lines.count(line) != 1]
    assert not repeated, f"a pinned step 1 line is repeated: {repeated}"
    rest = [line for line in lines if line.strip() and line not in STEP_1_PATH_LINES]
    assert digest(rest) == STEP_1_UNPINNED_SHA256, "step 1 gained, lost or changed an unpinned line"


def test_the_path_line_goes_in_the_todo_list_and_every_end_state_report() -> None:
    assert PATH_ARGUMENT_LINE in section(SKILL.read_text(), "Arguments").splitlines()


STATES_ROUTED_TO_A_ROLE = ("triage", "backlog", "ready", "in_progress", "in_review", "in_deployment_review")
STEP_12 = "engineering-workflow step 12 note"


def recorded_path_argument(state: str, notes: list[tuple[str, str]]) -> str | None:
    """Apply step 1's `--recorded-path` rule as SKILL.md states it to a story in `state`.

    `notes` are (kind, body) pairs, oldest first. A rule that names a `profile.tracker.states.<key>`
    passes the note only in that state; the value is the latest line of a step 12 note whose whole
    text is exactly one of the three path lines, and a `path:` line in any other note never counts.
    """
    rules = [line for line in step_1_lines() if "--recorded-path" in line]
    assert len(rules) == 1, "step 1 must state one `--recorded-path` rule"
    assert "`engineering-workflow` step 12 note line" in rules[0], "the rule must read only the step 12 note"
    gates = re.findall(r"`profile\.tracker\.states\.(\w+)`", rules[0])
    if gates and state not in gates:
        return None
    found = None
    for kind, body in notes:
        for line in body.splitlines():
            if kind == STEP_12 and line in ("path: spike", "path: no-deployment", "path: deployed"):
                found = line.removeprefix("path: ")
    return found


def select_for_step_1(tmp_path: Path, title: str, labels: list[str], recorded: str | None, envs: str) -> str:
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        "tracker:\n  labels:\n    spike: Spike\ngit:\n  integration_branch: main\n" f"environments: {envs}\n"
    )
    args = [sys.executable, str(ROOT / "skills" / "story-to-done" / "scripts" / "select-path.py"), f"--title={title}"]
    args += [f"--label={label}" for label in labels]
    if recorded is not None:
        args.append(f"--recorded-path={recorded}")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["AGENT_SKILLS_PROFILE"] = str(profile)
    result = subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout


def reopened_story_notes(path: str) -> list[tuple[str, str]]:
    return [
        ("implementation note", "Implementation note.\n\nMerged abc123.\npath: deployed is not a line of its own here"),
        (STEP_12, f"Step 12 note.\n\nMerged def456.\npath: {path}"),
        ("refinement proposal", "Refinement proposal (not an AC).\n\npath: deployed"),
        ("QA comment", "QA reopened the story: back to In Progress."),
    ]


@pytest.mark.parametrize("state", STATES_ROUTED_TO_A_ROLE)
@pytest.mark.parametrize("path", ["spike", "no-deployment", "deployed"])
def test_the_recorded_path_is_passed_in_every_state_routed_to_a_role(state: str, path: str) -> None:
    assert recorded_path_argument(state, reopened_story_notes(path)) == path
    assert recorded_path_argument(state, reopened_story_notes(path)[:1] + reopened_story_notes(path)[2:]) is None


# A reopened story moved back to in_progress keeps the step 12 note from its first landing; the
# recorded path wins over a reselection that would now differ.
@pytest.mark.parametrize(
    ("title", "labels", "note_path", "envs", "reselected"),
    [
        ("[User Story] Ship X", [], "no-deployment", "[{name: dev, branch: main}]", "deployed"),
        ("[User Story] Ship X", [], "deployed", "[]", "no-deployment"),
        ("[Spike] Probe X", [], "spike", "[]", "ask: spike-title-without-label"),
    ],
    ids=["no-deployment-after-environments-added", "deployed-after-environments-removed", "spike-after-label-removed"],
)
def test_a_reopened_story_in_progress_passes_its_recorded_path(
    tmp_path: Path, title: str, labels: list[str], note_path: str, envs: str, reselected: str
) -> None:
    recorded = recorded_path_argument("in_progress", reopened_story_notes(note_path))
    assert recorded == note_path
    assert select_for_step_1(tmp_path, title, labels, None, envs) == f"{reselected}\n"
    assert select_for_step_1(tmp_path, title, labels, recorded, envs) == f"{note_path}\n"


def test_a_role_ask_handback_keeps_the_selected_path_in_the_closing_report() -> None:
    lines = step_1_lines()
    assert ROLE_ASK_LINE in lines
    assert lines.index("Otherwise select the run's path before any role is spawned.") < lines.index(ROLE_ASK_LINE)
    # "the report of that end state" is the closing report the Arguments section defines for a stop.
    assert CLOSING_REPORT_PHRASE in section(SKILL.read_text(), "Arguments")


# SKL-278 AC2: a final engineer handback with no merged PR never passes the merged-PR read-back by
# running it zero times, and no path weakens a PR gate.
NO_MERGED_PR_STOP = (
    "A final handback from the senior engineer that reports no merged PR stops the run on `deployed` and "
    "`no-deployment`; on `spike` the run continues to step 3 only when the `engineering-workflow` step 12 note "
    "says the spike had no tracked-file change, and otherwise stops."
)
NO_PATH_WAIVER = "No path adds a waiver, an admin override, or a change to the expected-head condition."


def test_a_final_handback_with_no_merged_pr_stops_except_a_spike_with_no_tracked_file_change() -> None:
    lines = step_2_lines()
    assert NO_MERGED_PR_STOP in lines, "step 2 must state the no-merged-PR stop exactly"
    assert lines.index(NO_MERGED_PR_STOP) in prose_lines(lines), "the stop must be operative prose"
    assert SKILL.read_text().count(NO_MERGED_PR_STOP) == 1, "the no-merged-PR stop is stated once"
    waived = next((line for line in lines if line.startswith("For a waived PR, compare")), None)
    assert waived is not None, "step 2 must keep the waived-PR read-back the stop follows"
    assert lines.index(waived) < lines.index(NO_MERGED_PR_STOP), "the stop follows the merged-PR read-back"


def test_no_path_weakens_a_pr_gate() -> None:
    lines = step_2_lines()
    assert NO_PATH_WAIVER in lines, "step 2 must state that no path adds a waiver"
    assert lines.index(NO_PATH_WAIVER) in prose_lines(lines), "the no-waiver rule must be operative prose"
    assert SKILL.read_text().count(NO_PATH_WAIVER) == 1, "the no-waiver rule is stated once"


def test_path_unresolved_is_reported_only_for_a_stop_before_selection() -> None:
    sources = [SKILL, *sorted((SKILL.parent / "references").glob("*.md"))]
    unresolved = [line for source in sources for line in source.read_text().splitlines() if "path: unresolved" in line]
    assert unresolved == [PATH_ARGUMENT_LINE, UNRESOLVED_LINE], (
        "`path: unresolved` may appear only in the Arguments line and step 1's before-selection rule"
    )
    # Both lines cover every stop before selection, in step 1 or earlier, so they agree.
    assert "until step 1 selects it" in PATH_ARGUMENT_LINE
    assert "before this step selects a path, in this step or an earlier one" in UNRESOLVED_LINE


# SKL-70 AC2: the delegating session creates the story worktree before the spawn, because a subagent
# starts in its spawner's directory, and names its path in the brief.
WORKTREE_CREATE = (
    "Before you spawn the senior engineer, fetch the base the branch rule in `references/github.md` selects "
    "(`<profile.git.integration_branch>` by default) with the explicit refspec `git fetch origin "
    "+refs/heads/<base>:refs/remotes/origin/<base>` and, when the story has no unmerged story worktree and no "
    "open PR, run `git worktree add --no-track -b <branch> <absolute path> origin/<base>` to create the story "
    "worktree on a new story branch cut from that base, `<branch>` being a name the branch-naming rule gives "
    "that no local or remote branch already carries, per the branch and worktree rules in "
    "`references/github.md`; the branch has no upstream until its first push, `git push -u origin <branch>`."
)
WORKTREE_LATER_PR = (
    "A later PR for the same story, opened after an earlier one merged, gets a fresh worktree under the existing "
    "worktree rule in `references/github.md`, which you create the same way and name in the `worktree:` line of "
    "every later brief, including the brief or message with which step 4 resumes or relaunches the senior engineer, "
    "and the hand-back reports its path too."
)
WORKTREE_EXISTING = (
    "A story with an existing unmerged story worktree or an open PR reuses that worktree or its branch and "
    "names it in the `worktree:` line, per the existing PR or branch rule in `references/github.md`: with an "
    "open PR, the branch reused is that PR's head branch, and an existing story worktree is named only when it "
    "holds that branch; with no open PR, name an existing story worktree whose branch has not merged and create "
    "nothing; when no worktree holds the open PR's head branch, fetch it with `git fetch origin "
    "+refs/heads/<branch>:refs/remotes/origin/<branch>` and run `git worktree add --no-track -b <branch> "
    "<absolute path> origin/<branch>`, or `git worktree add <absolute path> <branch>` when a local branch of "
    "that name exists, to create the story worktree on that branch; with an open PR, before every spawn or "
    "resume, stop and report instead when `git -C <absolute path> rev-parse HEAD` differs from the PR's "
    "`headRefOid` from `gh pr view`, and never fetch into, merge into or reset that worktree, since reconciling "
    "its commits with the PR is the engineer's work; a branch whose PR merged is never reused, so a later PR "
    "gets the fresh worktree above."
)
WORKTREE_BRIEF_LINE = (
    "- The line `worktree: <absolute path>`, whose whole text is exactly that, `<absolute path>` being the story "
    "worktree you created, distinct from the `path: <value>` line."
)
WORKTREE_HANDBACK = "- That the hand-back also returns each worktree path it worked in."


def test_step_2_creates_the_story_worktree_before_the_spawn() -> None:
    lines = step_2_lines()
    for sentence in (WORKTREE_CREATE, WORKTREE_LATER_PR, WORKTREE_EXISTING):
        assert sentence in lines, f"step 2 must state: {sentence}"
        assert lines.index(sentence) in prose_lines(lines), "the worktree rule must be operative prose"
        assert SKILL.read_text().count(sentence) == 1, "each worktree sentence is stated once"
    spawn = next(i for i, line in enumerate(lines) if line.startswith("Spawn a clean, neutral subagent"))
    assert lines.index(WORKTREE_CREATE) < spawn, "the worktree exists before the engineer spawns"


def test_step_2_brief_names_the_worktree_and_the_hand_back_returns_it() -> None:
    lines = step_2_lines()
    path_line = next(i for i, line in enumerate(lines) if line.startswith("- The line `path: <value>`"))
    assert lines[path_line + 1] == WORKTREE_BRIEF_LINE, "the brief names the worktree right after the path line"
    handback = next(i for i, line in enumerate(lines) if line.startswith("- What to hand back:"))
    assert lines[handback + 1] == WORKTREE_HANDBACK, "the hand-back item is followed by the worktree paths"
    for line in (WORKTREE_BRIEF_LINE, WORKTREE_HANDBACK):
        assert SKILL.read_text().count(line) == 1, "each brief item is stated once"


# SKL-138: the spawner states `nested`; a nested coordinator launches its roles in the foreground.
NESTED_ROW = "| `nested` | whether the spawner started this run as a subagent | `no` |"
NESTED_GIVEN = (
    '- `nested` is given as `nested=yes` or `nested=no`, or in plain words: "you are running as a subagent" means '
    'yes, "you are the top-level session" and "you are not running as a subagent" mean no; ask the user about any '
    'other phrasing about nesting, "not nested" and "non-nested" included; never guess, and if nobody can answer, '
    "stop and report."
)
NESTED_RESOLVE = "- Resolve `nested` before step 0 creates the todo list; it sets no model or effort."
NESTED_NEVER_INFER = "- Never infer nesting from the environment, the tool list, or a failed handback."
NESTED_UNRESOLVED = (
    "- The one exception: a stop while an ambiguous `nested` value is unanswered reports `nested: unresolved` in "
    "place of `nested: yes|no`."
)
NESTED_EVERY_LAUNCH = (
    "- With `nested=yes`, every other launch or resume of a role you make, such as step 0's read-back resume, step "
    "4's continuation of the QA agent, and a resume under `references/interim-handbacks.md`, is also made in the "
    "foreground."
)
NESTED_NO_FOREGROUND_STOP = (
    "- With `nested=yes`, once seat resolution has decided each seat's launch, stop and report before any role is "
    "launched when a seat launches as a subagent and `references/runtimes.md` gives a nested coordinator no "
    "foreground subagent launch on that runtime; a `command` or `codex` seat is a process you wait on and never "
    "needs one."
)
DEFAULT_MODE = "with `nested=no`, make it in the runtime's default mode."
NESTED_STEP_2 = (
    "With `nested=yes`, make this launch in the foreground, so the call returns the engineer's handback to you; "
    + DEFAULT_MODE
)
NESTED_STEP_3 = (
    "With `nested=yes`, make each QA launch in the foreground, so the call returns the QA agent's handback to you; "
    + DEFAULT_MODE
)
NESTED_STEP_4 = (
    "  With `nested=yes`, make each resume or re-spawn of the senior engineer in the foreground, so the call "
    "returns its handback to you; " + DEFAULT_MODE
)
README_NESTED_CLAUSE = (
    "a `nested` argument, `no` by default, makes a coordinator that its spawner started as a subagent launch its roles "
    "in the foreground"
)
RUNTIMES_NESTED_LINES = [
    "  A coordinator started as a subagent cannot tell that it is one: the runtime documentation read for this rule "
    "gives no in-agent signal that identifies a subagent in every mode.",
    "  A signal observed on one runtime or mode is recorded with its version and date and is not relied on; for "
    "example, a nested coordinator called the `SubagentHandback` tool in the SKL-95 run "
    "(`docs/qa-evidence/SKL-95/raw-output-round-2.txt`).",
    "  So a spawner that starts a coordinator as a subagent states so in the brief, and a nested coordinator whose "
    "skill takes that input (for `story-to-done`, `nested=yes`) launches its roles in the foreground, so each call "
    "returns the role's handback to it; where this map gives it no foreground subagent launch, it stops and reports "
    "rather than launching a role as a subagent.",
    "  A role launched by the shell-launched agents rule below (`runtime: command` or `runtime: codex`) is a process "
    "the coordinator waits on, so it needs no foreground subagent launch and that stop never applies to it.",
    "  Claude Code: the fork-mode gate decides whether a nested coordinator can launch in the foreground.",
    "  `CLAUDE_CODE_FORK_SUBAGENT` is on by default (from v2.1.302; interactive terminal from v2.1.232); set it to "
    "`0` to turn it off.",
    "  While it is on, the main conversation cannot wait for a subagent in interactive terminal, VS Code or desktop "
    "sessions; in `claude -p` and the Agent SDK it can.",
    "  So with fork mode on in an interactive terminal, VS Code or desktop session, a nested coordinator has no "
    "foreground subagent launch.",
    "  The docs also say that in an interactive terminal a spawning subagent waits for its background nested subagents, "
    "and that under `claude -p` and the Agent SDK a background nested subagent may report to the main conversation "
    "if it outlasts the spawning subagent.",
    "  `SubagentHandback` is documented as a delivery tool, provided only in auto mode to local non-fork subagents "
    "(v2.1.271 or later), not as a way to detect being a subagent.",
    "  Sources, read 2026-10-30: [sub-agents](https://code.claude.com/docs/en/sub-agents.md), "
    "[env-vars](https://code.claude.com/docs/en/env-vars.md), "
    "[tools-reference](https://code.claude.com/docs/en/tools-reference.md).",
    "  Observed on Claude Code v2.1.312, 2026-10-30: with fork mode on, a nested launch with no background flag "
    "returned asynchronously, and the `Agent` tool schema had no `run_in_background` parameter.",
    "  Observed in SKL-94 QA round 1 Run 1 (`docs/qa-evidence/SKL-94/README.md`): a nested Claude Code coordinator "
    "launched QA in the background, its turn ended before QA handed back, and QA's handback never reached it; one "
    "run, recorded, not a general rule.",
    "  OpenCode V2: [Tools](https://opencode.ai/v2/docs/tools) (read 2026-11-17, with the CLI at the version in "
    "`.opencode-version`; the page names no version) documents no foreground form of the `subagent` call: \"Subagents always run in "
    "the background\", and the parent receives a `<subagent>` message when the child goes idle.",
    "  So a nested coordinator on OpenCode V2 has no foreground subagent launch.",
    "  OpenCode V2 depth: [Config](https://opencode.ai/v2/docs/config) says `subagent_depth` \"Defaults to `1`, so a "
    "subagent cannot start another subagent\", so each hop below the primary session takes one level.",
    "  A top-level spawner -> coordinator -> role -> reviewer chain needs `experimental.subagent_depth: 3`; when the "
    "spawner is itself a subagent, add one level per hop above it (4 when the spawner is a direct child of the "
    "primary session).",
    "  The depth-2 example below stays for its use: a top-level coordinator whose delegated agent runs reviewers.",
]
RUNTIMES_TOOLS_REFERENCE = "- [Tools](https://opencode.ai/v2/docs/tools): the `subagent` call and its launch mode."


def test_nested_row_defaults_to_no() -> None:
    assert NESTED_ROW in arguments_lines()


def test_nested_is_given_by_key_value_or_a_closed_plain_words_map_and_otherwise_asked_or_stopped() -> None:
    assert NESTED_GIVEN in arguments_lines()


def resolve_nested(phrase: str) -> str:
    """Apply the Arguments plain-words map as SKILL.md states it: an exact phrase maps, anything else is asked."""
    line = next((line for line in arguments_lines() if line.startswith("- `nested` is given as")), None)
    assert line is not None, "Arguments carries no `nested` is given as ... line"
    head = line.split("; ask the user", 1)[0]
    assert "or in plain words: " in head and " means yes, " in head, "the plain-words map is not stated as yes then no"
    words = head.split("or in plain words: ", 1)[1]
    yes_part, no_part = words.split(" means yes, ", 1)
    mapping = {p: "yes" for p in re.findall(r'"([^"]+)"', yes_part)}
    mapping |= {p: "no" for p in re.findall(r'"([^"]+)"', no_part)}
    return mapping.get(phrase, "ask")


@pytest.mark.parametrize(
    ("phrase", "value"),
    [
        ("you are running as a subagent", "yes"),
        ("you are the top-level session", "no"),
        ("you are not running as a subagent", "no"),
        ("not nested", "ask"),
        ("non-nested", "ask"),
        ("nested", "ask"),
    ],
)
def test_the_plain_words_map_is_closed_and_a_negation_is_asked_never_guessed(phrase: str, value: str) -> None:
    assert resolve_nested(phrase) == value
    if value == "ask":
        assert f'"{phrase}"' not in NESTED_GIVEN.split("; ask the user", 1)[0]


def test_nested_resolves_before_step_0_and_sets_no_model_or_effort() -> None:
    assert NESTED_RESOLVE in arguments_lines()


def test_nesting_is_never_inferred() -> None:
    assert NESTED_NEVER_INFER in arguments_lines()
    assert SKILL.read_text().count("Never infer nesting") == 1


def test_steps_2_3_and_4_launch_in_the_foreground_when_nested() -> None:
    assert NESTED_STEP_2 in step_2_lines()
    assert NESTED_STEP_3 in section(SKILL.read_text(), STEP_3_HEADING).splitlines()
    assert NESTED_STEP_4 in bullet_lines("`profile.tracker.states.in_progress`")
    assert follows(bullet_lines("`profile.tracker.states.in_progress`"), HAND_BACK_LINE, NESTED_STEP_4)


def test_every_other_role_launch_is_foreground_and_a_runtime_without_one_stops() -> None:
    assert NESTED_EVERY_LAUNCH in arguments_lines()
    assert NESTED_NO_FOREGROUND_STOP in arguments_lines()


def test_every_nested_line_is_visible_when_rendered() -> None:
    rendered = visible(SKILL.read_text()).splitlines()
    for line in [
        NESTED_ROW,
        NESTED_GIVEN,
        NESTED_RESOLVE,
        NESTED_NEVER_INFER,
        NESTED_REASON,
        NESTED_EVERY_LAUNCH,
        NESTED_NO_FOREGROUND_STOP,
        NESTED_IDENTICAL,
        NESTED_UNRESOLVED,
        NESTED_STEP_2,
        NESTED_STEP_3,
        NESTED_STEP_4,
    ]:
        assert line in rendered, f"hidden from the rendered skill: {line[:60]}"


def test_a_launch_under_nested_no_keeps_the_runtime_default_mode() -> None:
    launches = [line for line in SKILL.read_text().splitlines() if "With `nested=yes`, make" in line]
    assert launches == [NESTED_STEP_2, NESTED_STEP_3, NESTED_STEP_4]
    assert all(line.endswith(DEFAULT_MODE) for line in launches)


def test_the_reason_is_stated_once_and_is_the_only_background_line() -> None:
    assert NESTED_REASON in arguments_lines()
    body = SKILL.read_text().split("\n---\n", 1)[1]
    assert [line for line in body.splitlines() if re.search(r"\bbackground\b", line, re.IGNORECASE)] == [NESTED_REASON]


def test_nested_changes_no_brief_role_row_or_metrics_rule() -> None:
    assert NESTED_IDENTICAL in arguments_lines()
    nested_lines = [line for line in SKILL.read_text().splitlines() if "nested" in line]
    assert nested_lines == [
        NESTED_ROW,
        NESTED_GIVEN,
        NESTED_RESOLVE,
        NESTED_REASON,
        NESTED_EVERY_LAUNCH,
        NESTED_NO_FOREGROUND_STOP,
        NESTED_IDENTICAL,
        "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at any stop, including one before step 0).",
        NESTED_UNRESOLVED,
        NESTED_STEP_2,
        NESTED_STEP_3,
        NESTED_STEP_4,
        next(line for line in SKILL.read_text().splitlines() if line.startswith("Report the story identifier")),
    ], "`nested` appears outside its Arguments lines, the three launch lines, and the step 5 report"
    assert "nested" not in SKILL.read_text().split("\n---\n", 1)[0], "the front matter names `nested`"


def test_nested_is_echoed_in_the_arguments_bullet_and_the_step_5_report() -> None:
    assert "the `nested: yes|no` line" in METRICS_LINE_SENTENCE
    assert "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at any stop, including one before step 0)." in arguments_lines()
    assert "the `nested: yes|no` line" in " ".join(section(SKILL.read_text(), "5. Close out").split())
    assert NESTED_UNRESOLVED in arguments_lines()


def test_runtimes_nesting_rule_covers_both_runtimes() -> None:
    lines = (ROOT / "shared" / "runtimes.md").read_text().splitlines()
    rule = lines.index("- **Nested subagents.** A delegated agent that runs a review gate spawns subagents of its own.")
    end = next(i for i in range(rule + 1, len(lines)) if not lines[i].startswith("  "))
    block = lines[rule + 1:end]
    assert RUNTIMES_NESTED_LINES[0] in block, "the nesting lines are not inside the Nested subagents rule"
    start = block.index(RUNTIMES_NESTED_LINES[0])
    assert block[start:start + len(RUNTIMES_NESTED_LINES)] == RUNTIMES_NESTED_LINES
    assert RUNTIMES_TOOLS_REFERENCE in lines
    assert sum(line.startswith("- **Nested subagents.**") for line in lines) == 1


def test_readme_row_names_nested_and_its_default_before_the_metrics_clause() -> None:
    row = readme_row()
    assert README_NESTED_CLAUSE in row
    assert row.index(README_NESTED_CLAUSE) < row.index(README_POSTED)


# SKL-346: the step 2 and step 4 handbacks carry a per-PR arbitration ledger, the brief templates and
# both steps of the skill document it, the escalation verifier names the head and itself, and the step 2
# brief passes the arbiter's model verbatim to `--model`.
LEDGER_HEADING = "`## Arbitration ledger`"
LEDGER_HEADER_ROW = "`| round | kind | head | engineer | reviewer agent | reviewer model | report |`"
LEDGER_COLUMNS = ("round", "kind", "head", "engineer", "reviewer agent", "reviewer model", "report")
LEDGER_EMPTY = "`No rounds yet.`"
LEDGER_KINDS = ("`arbitration`", "`escalation-verification`")
LEDGER_MISSING_STOP = (
    "When you hold no ledger for a PR that has earlier rounds, stop and report the missing ledger before you "
    "launch the engineer again."
)
ARBITER_MODEL_FLAG = "passes `profile.review.pre_pr.arbiter.model` verbatim to `--model`"
VERIFIED_HEAD_LINE = "`VERIFIED-HEAD: <full head SHA>`"
VERIFIER_LINE = "`VERIFIER: <agent name> <model id>`"
ENGINEER_PATH_TEMPLATES = ("brief-engineer-deployed.md", "brief-engineer-no-deployment.md", "brief-engineer-spike.md")
WORKFLOW_SKILL = ROOT / "skills" / "engineering-workflow" / "SKILL.md"


def ledger_sources() -> dict[str, str]:
    """Every place AC 4 names for the ledger clause, flattened to one line each."""
    skill = visible(SKILL.read_text())
    sources = {
        "SKILL.md step 2": section(skill, STEP_2),
        "SKILL.md step 4": section(skill, STEP_4_HEADING),
    }
    for name in ENGINEER_PATH_TEMPLATES:
        sources[name] = visible((ASSETS / name).read_text())
    return {name: " ".join(text.split()) for name, text in sources.items()}


@pytest.mark.parametrize("name", ["SKILL.md step 2", "SKILL.md step 4", *ENGINEER_PATH_TEMPLATES])
def test_the_brief_carries_the_ledger_heading_columns_and_empty_line(name: str) -> None:
    text = ledger_sources()[name]
    assert LEDGER_HEADING in text
    assert LEDGER_HEADER_ROW in text
    row = re.search(r"`\|( round \|[^`]*)\|`", text)
    assert row, "no ledger header row in the text"
    assert tuple(cell.strip() for cell in row.group(1).split("|")) == LEDGER_COLUMNS
    assert LEDGER_EMPTY in text
    for kind in LEDGER_KINDS:
        assert kind in text, kind


@pytest.mark.parametrize("name", ["SKILL.md step 2", *ENGINEER_PATH_TEMPLATES])
def test_the_brief_defines_rounds_provenance_reports_and_numbering(name: str) -> None:
    text = ledger_sources()[name]
    for phrase in (
        "a re-run at an unchanged head is a new round",
        "a step 4 fix, a rebase, a merge or a force-push",
        "numbered contiguously from 1 per PR",
        "the absolute path of the retained per-round report",
        "the absolute path or `https://` URL of the verifier's report",
        "`ARBITER-AGENT:` and `ARBITER-MODEL:` lines",
        "the `VERIFIER:` line of the verifier's report",
        "never from your text",
        "the absolute directory that holds the retained per-round reports",
        "return its entries unchanged",
        "no new-head review or verification is waived",
    ):
        assert phrase in text, phrase


@pytest.mark.parametrize("name", ["SKILL.md step 2", *ENGINEER_PATH_TEMPLATES])
def test_the_step_2_brief_passes_the_arbiter_model_verbatim(name: str) -> None:
    assert ARBITER_MODEL_FLAG in ledger_sources()[name]


def test_step_2_has_the_coordinator_fill_the_identity_cells_from_the_seat_and_the_reports() -> None:
    text = ledger_sources()["SKILL.md step 2"]
    for phrase in (
        "the seat you launched it on",
        "copying the `ARBITER-AGENT:` and `ARBITER-MODEL:` lines of the retained report",
        "the `VERIFIER:` line of the verifier's report",
        "never from the engineer's text",
    ):
        assert phrase in text, phrase


def test_step_4_puts_the_ledger_in_every_hand_back_and_stops_without_one() -> None:
    text = ledger_sources()["SKILL.md step 4"]
    assert LEDGER_HEADING in text
    assert LEDGER_MISSING_STOP in text
    assert in_order(
        in_progress_bullet(),
        "Hand them back to the senior engineer",
        LEDGER_HEADING,
        LEDGER_MISSING_STOP,
        "Confirm that state as step 2 does",
    )


def test_step_2_puts_the_held_ledger_in_the_brief_and_stops_without_one() -> None:
    text = ledger_sources()["SKILL.md step 2"]
    stop = text.index(LEDGER_MISSING_STOP)
    assert text.index("put the `## Arbitration ledger` you hold for each of its PRs into the brief") < stop
    assert stop < text.index("Spawn a clean, neutral subagent")


@pytest.mark.parametrize("case", ["engineer-deployed", "engineer-no-deployment", "engineer-spike"])
def test_every_rendered_engineer_brief_carries_the_ledger_clause(case: str, tmp_path: Path) -> None:
    text = " ".join(rendered_brief(tmp_path, RENDER_CASES[case]).split())
    for anchor in (LEDGER_HEADING, LEDGER_HEADER_ROW, LEDGER_EMPTY, ARBITER_MODEL_FLAG):
        assert text.count(anchor) == 1, anchor


def test_the_escalation_verify_stage_has_the_verifier_name_the_head_and_itself() -> None:
    escalation = section(WORKFLOW_SKILL.read_text(), "4. Pre-PR adversarial gate (required)")
    verify = next(line for line in escalation.splitlines() if line.startswith("2. **Verify.**"))
    stage = escalation[escalation.index(verify):escalation.index("3. **Fix.**")]
    assert VERIFIED_HEAD_LINE in stage
    assert VERIFIER_LINE in stage
    assert "each on its own line of its report" in stage
