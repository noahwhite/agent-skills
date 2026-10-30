"""The documented OpenCode V2 usage read for an `opencode run` launch (SKL-132).

`shared/runtimes.md` publishes one shell snippet that resolves a launch's session by its unique
title and reads Tokens and Tool calls from `opencode session export`. These tests run that
snippet as published against a stub `opencode` on PATH, the only external edge. The stub's
payloads follow the shape `opencode session list --format json` and `opencode session export`
returned on v2.2.0; the values are synthetic, and no raw export is kept in the repository.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNTIMES = ROOT / "shared" / "runtimes.md"
USAGE_BULLET = "- **Usage from shell-launched agents.**"
FENCE_RE = re.compile(r"^[ \t]*```bash\n(.*?)^[ \t]*```$", re.MULTILINE | re.DOTALL)
NOT_REPORTED = "not reported"


def usage_snippet() -> str:
    text = RUNTIMES.read_text()
    assert text.count(USAGE_BULLET) == 1, "expected exactly one usage bullet"
    bullet = text.split(USAGE_BULLET, 1)[1].split("\n- **", 1)[0].split("\n## ", 1)[0]
    blocks = [block for block in FENCE_RE.findall(bullet) if "opencode session export" in block]
    assert len(blocks) == 1, "the usage bullet must carry exactly one session-export snippet"
    return blocks[0]


def assistant(*parts: dict) -> dict:
    return {"id": "msg_a", "type": "assistant", "tokens": {"input": 1, "output": 1}, "content": list(parts)}


def tool(name: str = "read") -> dict:
    return {"type": "tool", "id": "prt_t", "name": name, "state": {"status": "completed"}}


TEXT = {"type": "text", "text": "done"}


def export(tokens: dict | None, messages: list[dict]) -> dict:
    info = {"id": "ses_x", "title": "t"}
    if tokens is not None:
        info["tokens"] = tokens
    return {"info": info, "messages": messages}


def tokens(input_: int, output: int, reasoning: int, read: int = 900, write: int = 70) -> dict:
    return {"input": input_, "output": output, "reasoning": reasoning, "cache": {"read": read, "write": write}}


# Session A: two assistant steps, three tool parts in all, plus a user message and an idle marker.
SESSION_A = export(
    tokens(3785, 69, 12),
    [
        {"id": "msg_u", "type": "user", "text": "prompt"},
        assistant(tool("read"), tool("bash")),
        assistant(TEXT, tool("subagent")),
        {"id": "msg_i", "type": "idle", "outcome": "succeeded"},
    ],
)
# Session B: one step, no tool part.
SESSION_B = export(tokens(3618, 2, 0), [{"id": "msg_u", "type": "user"}, assistant(TEXT)])


# v2.2.0 stopped `opencode session` output written to a pipe or a command substitution at this
# many bytes; the stub does the same, so a snippet that reads the export through a pipe fails.
PIPE_CUTOFF = 262144


def install_stub(
    tmp_path: Path, sessions: list[dict], exports: dict[str, object], list_exit: int = 0, interrupt: bool = False
) -> dict:
    """Put a stub opencode on PATH; `exports` maps an id to a payload or a raw (unparseable) string."""
    state = tmp_path / "state"
    state.mkdir()
    (state / "list.json").write_text(json.dumps(sessions))
    for sid, payload in exports.items():
        if isinstance(payload, str):
            (state / f"{sid}.raw").write_text(payload)
        else:
            (state / f"{sid}.json").write_text(json.dumps(payload))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "opencode"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        f"state='{state}'\n"
        f"emit() {{ if [ -p /dev/stdout ]; then head -c {PIPE_CUTOFF} \"$1\"; else cat \"$1\"; fi; }}\n"
        'if [ "$1 $2" = "session list" ]; then\n'
        '  printf "%s\\n" "$*" >> "$state/list-args"\n'
        f'  emit "$state/list.json"; exit {list_exit}\n'
        "fi\n"
        'if [ "$1 $2" = "session export" ]; then\n'
        '  if [ -f "$state/$3.json" ]; then emit "$state/$3.json"; '
        + ('kill -TERM "$PPID"; sleep 1; ' if interrupt else "")
        + 'exit 0; fi\n'
        '  if [ -f "$state/$3.raw" ]; then emit "$state/$3.raw"; exit 0; fi\n'
        '  printf "Session not found: %s\\n" "$3" >&2; exit 1\n'
        "fi\n"
        'printf "unexpected opencode call: %s\\n" "$*" >&2; exit 64\n'
    )
    stub.chmod(0o755)
    return {"state": state, "path": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def launch(stub: dict, cwd: Path, title: str, **extra: str) -> tuple[subprocess.Popen, Path]:
    """Start the published snippet as a reader pastes it: plain bash, no extra shell options."""
    scratch = cwd / "scratch"
    scratch.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k not in ("id", "resume_id")}
    env |= {"PATH": stub["path"], "title": title, "scratch": str(scratch), **extra}
    proc = subprocess.Popen(
        ["bash", "-c", usage_snippet()],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=cwd,
    )
    return proc, scratch


def collect(stub: dict, proc: subprocess.Popen, scratch: Path, expect_rc: int = 0) -> dict[str, str]:
    stdout, stderr = proc.communicate(timeout=60)
    assert proc.returncode == expect_rc, stderr
    if expect_rc:
        assert list(scratch.iterdir()) == [], "an interrupted read must still remove the export"
        return {"stderr": stderr}
    figures = dict(line.split(": ", 1) for line in stdout.strip().splitlines())
    assert set(figures) == {"tokens", "tool calls"}, stdout
    assert list(scratch.iterdir()) == [], "the list and export files must be removed"
    list_args = (stub["state"] / "list-args").read_text() if (stub["state"] / "list-args").exists() else ""
    return {**figures, "stderr": stderr, "list_args": list_args}


def run_snippet(
    tmp_path: Path, title: str, sessions: list[dict], exports: dict[str, object], list_exit: int = 0
) -> dict[str, str]:
    stub = install_stub(tmp_path, sessions, exports, list_exit)
    return collect(stub, *launch(stub, tmp_path, title))


def listed(*pairs: tuple[str, str]) -> list[dict]:
    return [{"id": sid, "title": title, "directory": "/work"} for sid, title in pairs]


def test_the_published_snippet_parses():
    res = subprocess.run(["bash", "-n", "-c", usage_snippet()], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_one_titled_session_gives_tokens_without_cache_and_each_tool_part_once(tmp_path):
    out = run_snippet(
        tmp_path, "run-a", listed(("ses_b", "run-b"), ("ses_a", "run-a")), {"ses_a": SESSION_A, "ses_b": SESSION_B}
    )
    assert out["tokens"] == str(3785 + 69 + 12)
    assert out["tool calls"] == "3"
    assert "--format json" in out["list_args"] and "--max-count 1000" in out["list_args"]


def test_a_session_with_no_tool_part_reports_zero_tool_calls(tmp_path):
    out = run_snippet(tmp_path, "run-b", listed(("ses_a", "run-a"), ("ses_b", "run-b")), {"ses_a": SESSION_A, "ses_b": SESSION_B})
    assert (out["tokens"], out["tool calls"]) == (str(3618 + 2), "0")


def test_two_concurrent_launches_each_resolve_their_own_session(tmp_path):
    stub = install_stub(tmp_path, listed(("ses_b", "run-b"), ("ses_a", "run-a")), {"ses_a": SESSION_A, "ses_b": SESSION_B})
    first = launch(stub, tmp_path / "a", "run-a")
    second = launch(stub, tmp_path / "b", "run-b")
    first_out, second_out = collect(stub, *first), collect(stub, *second)
    assert (first_out["tokens"], first_out["tool calls"]) == ("3866", "3")
    assert (second_out["tokens"], second_out["tool calls"]) == ("3620", "0")


def test_an_export_longer_than_the_pipe_cutoff_is_read_whole(tmp_path):
    padding = [assistant({"type": "text", "text": "x" * 4096}) for _ in range(80)]
    big = export(tokens(151316, 11243, 60370), [*SESSION_A["messages"], *padding])
    assert len(json.dumps(big)) > PIPE_CUTOFF
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": big})
    assert (out["tokens"], out["tool calls"]) == (str(151316 + 11243 + 60370), "3"), out["stderr"]


def test_an_empty_title_never_takes_an_untitled_session(tmp_path):
    out = run_snippet(tmp_path, "", listed(("ses_a", "")), {"ses_a": SESSION_A})
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)
    assert out["list_args"] == "", "an empty title must not reach the lookup"


def test_a_resumed_launch_exports_its_explicit_id_and_marks_both_figures_cumulative(tmp_path):
    stub = install_stub(tmp_path, listed(("ses_b", "run-a")), {"ses_a": SESSION_A, "ses_b": SESSION_B})
    out = collect(stub, *launch(stub, tmp_path, "run-a", resume_id="ses_a"))
    assert (out["tokens"], out["tool calls"]) == ("3866 cumulative", "3 cumulative")
    assert out["list_args"] == "", "a resumed launch takes no title lookup"


def test_a_resumed_launch_whose_export_fails_reports_neither_figure(tmp_path):
    stub = install_stub(tmp_path, listed(("ses_a", "run-a")), {"ses_a": SESSION_A})
    out = collect(stub, *launch(stub, tmp_path, "run-a", resume_id="ses_gone"))
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)


def test_an_inherited_id_variable_never_stands_in_for_the_lookup(tmp_path):
    stub = install_stub(tmp_path, listed(("ses_b", "other")), {"ses_a": SESSION_A})
    out = collect(stub, *launch(stub, tmp_path, "run-a", id="ses_a"))
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)


def test_an_inherited_id_variable_never_stands_in_for_an_empty_title(tmp_path):
    stub = install_stub(tmp_path, listed(("ses_a", "run-a")), {"ses_a": SESSION_A})
    out = collect(stub, *launch(stub, tmp_path, "", id="ses_a"))
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)


def test_an_interrupted_read_removes_the_export(tmp_path):
    stub = install_stub(tmp_path, listed(("ses_a", "run-a")), {"ses_a": SESSION_A}, interrupt=True)
    collect(stub, *launch(stub, tmp_path, "run-a"), expect_rc=130)


@pytest.mark.parametrize(
    "messages",
    [
        [{"id": "msg_e", "type": "assistant"}, assistant(tool(), tool())],
        [{"id": "msg_e", "type": "assistant"}],
        [{"id": "msg_e", "type": "assistant", "content": None}, assistant(tool())],
    ],
    ids=["beside-a-tool-part", "alone", "null-content"],
)
def test_an_assistant_message_without_a_content_array_reports_tool_calls_not_zero(tmp_path, messages):
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": export(tokens(1, 1, 1), messages)})
    assert (out["tokens"], out["tool calls"]) == ("3", NOT_REPORTED)


def test_an_export_with_no_messages_reports_tool_calls_not_zero(tmp_path):
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": export(tokens(2, 2, 2), [])})
    assert (out["tokens"], out["tool calls"]) == ("6", NOT_REPORTED)


def test_a_failed_list_reports_neither_figure_even_when_it_printed_a_match(tmp_path):
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": SESSION_A}, list_exit=1)
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)


@pytest.mark.parametrize(
    "sessions",
    [
        pytest.param(listed(("ses_a", "other"), ("ses_b", "another")), id="no-match-never-the-newest"),
        pytest.param(listed(("ses_a", "run-a"), ("ses_b", "run-a")), id="two-matches"),
        pytest.param([], id="empty-list"),
    ],
)
def test_anything_but_exactly_one_title_match_reports_neither_figure(tmp_path, sessions):
    out = run_snippet(tmp_path, "run-a", sessions, {"ses_a": SESSION_A, "ses_b": SESSION_B})
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)


def test_a_failed_export_reports_neither_figure(tmp_path):
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {})
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)
    assert "Session not found" in out["stderr"], "the export failure must stay visible"


def test_an_unparseable_export_reports_neither_figure(tmp_path):
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": '{"info": {"tokens": '})
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, NOT_REPORTED)


@pytest.mark.parametrize("field", ["input", "output", "reasoning"])
def test_an_absent_token_field_reports_tokens_only_and_never_zero(tmp_path, field):
    broken = tokens(3785, 69, 12)
    del broken[field]
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": export(broken, SESSION_A["messages"])})
    assert out["tokens"] == NOT_REPORTED
    assert out["tool calls"] == "3"


def test_absent_token_totals_report_tokens_only(tmp_path):
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": export(None, SESSION_A["messages"])})
    assert (out["tokens"], out["tool calls"]) == (NOT_REPORTED, "3")


def test_absent_messages_report_tool_calls_only(tmp_path):
    payload = {"info": SESSION_A["info"] | {"tokens": tokens(10, 5, 1)}}
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": payload})
    assert (out["tokens"], out["tool calls"]) == ("16", NOT_REPORTED)


def test_tool_parts_outside_assistant_messages_are_not_counted(tmp_path):
    messages = [{"id": "msg_u", "type": "user", "content": [tool()]}, assistant(tool()), {"type": "idle", "content": [tool()]}]
    out = run_snippet(tmp_path, "run-a", listed(("ses_a", "run-a")), {"ses_a": export(tokens(1, 1, 1), messages)})
    assert out["tool calls"] == "1"


# The `{session_title}` key reaches the launch (AC2), and both skills point to the shared
# procedure without restating a formula (AC12).
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
REPO_PROFILE = ROOT / ".agent-skills" / "profile.yaml"
REFINEMENT = ROOT / "skills" / "story-refinement" / "SKILL.md"
STORY_TO_DONE = ROOT / "skills" / "story-to-done" / "SKILL.md"
POINTER = (
    "Each launch's Tokens and Tool calls are read as the \"Read a subagent's usage\" row and the "
    "\"Usage from shell-launched agents\" rule in [references/runtimes.md](references/runtimes.md) "
    "state; this section states no usage formula of its own."
)
TITLE_FILL = (
    "When the command carries a `{session_title}` placeholder, the facilitator replaces it on every "
    "launch with a title unique to that launch: the story key, the word "
    "`launch`, the launch's number in this invocation, a UTC timestamp to the nanosecond taken "
    "with `date -u +%Y%m%dT%H%M%S%NZ`, and 16 random hexadecimal characters taken with "
    "`od -An -N8 -tx1 /dev/urandom | tr -d ' \\n'`, joined by `-`, which carries no secret and no path. "
    "Every launch counts toward that number, a re-launch or retry included, so no two launches of "
    "one invocation share a title, and the random part keeps launches of concurrent invocations of "
    "one story apart even when their clocks give the same timestamp."
)
TITLE_RECORD = (
    "With `metrics` on, the facilitator keeps each launch's title in the metrics file and reads "
    "that launch's usage by it."
)


def flat(text: str) -> str:
    return " ".join(text.split())


def section(path: Path, heading: str) -> str:
    text = path.read_text()
    assert text.count(f"\n{heading}\n") == 1, f"{path.name} lost {heading}"
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


def test_schema_documents_the_session_title_placeholder():
    description = SCHEMA["$defs"]["refinement_role"]["properties"]["command"]["description"]
    assert "{prompt_file}" in description and "{output_file}" in description
    assert "optional {session_title} placeholder" in description, description


def test_story_refinement_fills_the_session_title_on_every_launch():
    body = flat(REFINEMENT.read_text())
    assert flat(TITLE_FILL) in body
    assert flat(TITLE_RECORD) in flat(section(REFINEMENT, "## Metrics"))


@pytest.mark.parametrize("path", [REFINEMENT, STORY_TO_DONE], ids=["story-refinement", "story-to-done"])
def test_metrics_section_points_to_the_shared_procedure(path):
    assert flat(POINTER) in flat(section(path, "## Metrics"))


@pytest.mark.parametrize("path", [REFINEMENT, STORY_TO_DONE], ids=["story-refinement", "story-to-done"])
def test_skill_restates_no_usage_formula(path):
    body = path.read_text()
    for formula in (".info.tokens", "session export", "type: \"tool\"", "`reasoning`", "step_finish"):
        assert formula not in body, f"{path.parent.name} restates {formula}"


def opencode_run_roles() -> list[dict]:
    refinement = yaml.safe_load(REPO_PROFILE.read_text())["refinement"]
    roles = [refinement["product_owner"], *refinement["reviewers"]]
    return [role for role in roles if "opencode run" in role.get("command", "")]


def test_repo_profile_opencode_voters_carry_a_title_and_no_metrics_breaking_flag():
    roles = opencode_run_roles()
    assert len(roles) >= 2, "the repository profile lost its OpenCode voters"
    for role in roles:
        command = role["command"]
        assert '--title "{session_title}"' in command, role["name"]
        for flag in ("--standalone", "--format", "--continue", "--session", "--fork"):
            assert flag not in command, f"{role['name']} passes {flag}"
        assert not re.search(r"(^|\s)-[cs](\s|=|$)", command), f"{role['name']} resumes a session"
