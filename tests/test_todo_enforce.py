"""SKL-246: the todo enforcer hook for story-to-done and story-refinement main threads.

The payloads and transcript lines in tests/fixtures/todo_enforce/ are copied from the SKL-246 AC2
probe sessions; payloads.json records the Claude Code version they came from. Each test runs the
enforcer as Claude Code does, one process per event, against temporary state and task directories.
"""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "shared" / "todo-enforce.py"
FIXTURES = ROOT / "tests" / "fixtures" / "todo_enforce"
FIXTURE = json.loads((FIXTURES / "payloads.json").read_text())
PAYLOADS = FIXTURE["payloads"]
SKILLS = ("story-to-done", "story-refinement")
EXEMPT = ("TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "ToolSearch", "Skill", "AskUserQuestion")
SESSION = "test-session"


def test_the_fixtures_record_the_claude_code_version_they_came_from():
    assert FIXTURE["claude_code_version"] == "2.1.322"
    for name in ("with-task-tools", "without-task-tools"):
        for line in (FIXTURES / f"transcript-{name}.jsonl").read_text().splitlines():
            assert json.loads(line)["version"] == "2.1.322"


def test_the_fixtures_carry_no_home_paths_session_ids_or_account_details():
    text = "\n".join(p.read_text() for p in sorted(FIXTURES.iterdir()))
    assert "/home/" not in text and "/Users/" not in text
    assert "mcp__" not in text
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    assert not re.search(r"\ba[0-9a-f]{16}\b", text)
    assert "@" not in text


class Rig:
    def __init__(self, tmp_path, script=SOURCE):
        self.script = script
        self.state = tmp_path / "state"
        self.config = tmp_path / "config"
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.transcript = tmp_path / "transcript.jsonl"
        self.use_transcript("with-task-tools")

    def use_transcript(self, name):
        shutil.copyfile(FIXTURES / f"transcript-{name}.jsonl", self.transcript)

    def env(self):
        env = {k: v for k, v in os.environ.items() if k not in ("XDG_STATE_HOME", "CLAUDE_CONFIG_DIR")}
        env.update(HOME=str(self.home), XDG_STATE_HOME=str(self.state), CLAUDE_CONFIG_DIR=str(self.config))
        return env

    def payload(self, name, **changes):
        data = copy.deepcopy(PAYLOADS[name]["payload"])
        data["session_id"] = SESSION
        data["transcript_path"] = str(self.transcript)
        data.update(changes)
        return data

    def raw(self, stdin):
        return subprocess.run(
            [sys.executable, "-I", str(self.script)],
            input=stdin, env=self.env(), capture_output=True, text=True, timeout=30,
        )

    def send(self, name, **changes):
        return self.raw(json.dumps(self.payload(name, **changes)))

    def task(self, task_id, status):
        folder = self.config / "tasks" / SESSION
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{task_id}.json").write_text(json.dumps({
            "id": task_id, "subject": "s", "description": "d", "status": status, "blocks": [], "blockedBy": [],
        }))

    def arm(self):
        assert_allowed(self.send("user_prompt_slash_story_to_done"))

    def tool(self, tool_name="Bash", **changes):
        if tool_name == "Bash":
            return self.send("main_pre_tool_use_bash", **changes)
        return self.send("main_pre_tool_use_bash", tool_name=tool_name, tool_input={}, **changes)

    def main_task(self, task_id, status):
        assert_allowed(self.send("main_task_created", task_id=task_id))
        self.task(task_id, status)

    def subagent_task(self, task_id, status):
        assert_allowed(self.send("subagent_task_created", task_id=task_id))
        self.task(task_id, status)


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


def is_denied(res):
    if res.returncode != 0 or not res.stdout:
        return False
    out = json.loads(res.stdout)["hookSpecificOutput"]
    return out["hookEventName"] == "PreToolUse" and out["permissionDecision"] == "deny"


def assert_allowed(res):
    assert (res.returncode, res.stdout) == (0, ""), res


def assert_denied(res, tool="Bash"):
    assert is_denied(res), res
    reason = json.loads(res.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert tool in reason and "in_progress" in reason


def assert_refused(res, *fragments):
    assert (res.returncode, res.stdout) == (2, ""), res
    for fragment in fragments:
        assert fragment in res.stderr


# --- (a) sessions that loaded neither skill --------------------------------------------------


@pytest.mark.parametrize("prompt", ["user_prompt_plain", "user_prompt_agent_message"])
def test_a_session_that_loaded_neither_skill_is_never_denied(rig, prompt):
    assert_allowed(rig.send(prompt))
    assert_allowed(rig.tool())
    assert_allowed(rig.send("main_task_created"))
    rig.task("1", "pending")
    assert_allowed(rig.tool("Read"))
    assert_allowed(rig.send("main_task_completed"))
    assert not (rig.state / "agent-skills" / "todo-enforce" / SESSION / "armed").exists()


@pytest.mark.parametrize("skill", ["persona-staff-engineer", "story-to-done-extra"])
def test_loading_another_skill_does_not_arm(rig, skill):
    assert_allowed(rig.send("main_pre_tool_use_skill_story_to_done", tool_input={"skill": skill}))
    assert_allowed(rig.send("user_prompt_slash_story_to_done", prompt=f"/{skill} X-1"))
    assert_allowed(rig.tool())


# --- (b) arming through each AC2 activation signal --------------------------------------------


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("signal", ["slash-typed prompt", "Skill tool call"])
def test_each_activation_signal_arms_the_session(rig, signal, skill):
    assert_allowed(rig.tool())
    if signal == "slash-typed prompt":
        assert_allowed(rig.send("user_prompt_slash_story_to_done", prompt=f"/{skill} PROBE-0"))
    else:
        assert_allowed(rig.send("main_pre_tool_use_skill_story_to_done", tool_input={"skill": skill, "args": "X-1"}))
    assert_denied(rig.tool())


def test_a_bare_slash_command_arms_the_session(rig):
    assert_allowed(rig.send("user_prompt_slash_story_to_done", prompt="/story-refinement"))
    assert_denied(rig.tool())


def test_a_subagent_loading_the_skill_does_not_arm_the_main_thread(rig):
    assert_allowed(rig.send("subagent_pre_tool_use_bash", tool_name="Skill", tool_input={"skill": "story-to-done"}))
    assert_allowed(rig.tool())


# --- (c) the main thread needs a main-owned in_progress task ----------------------------------


def deny_without_any_task(rig):
    rig.arm()
    return is_denied(rig.tool())


def deny_with_a_pending_main_task(rig):
    rig.arm()
    rig.main_task("1", "pending")
    return is_denied(rig.tool("Read"))


def test_an_armed_session_with_no_task_denies_a_tool_call(rig):
    rig.arm()
    assert not (rig.config / "tasks").exists()
    res = rig.tool()
    assert_denied(res)
    assert "TaskCreated hook" in res.stderr
    assert "TaskCreated hook" in json.loads(res.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    rig.main_task("1", "pending")
    res = rig.tool()
    assert_denied(res)
    assert "TaskCreated" not in res.stdout


def test_an_armed_session_with_a_pending_main_task_denies_and_allows_once_it_is_in_progress(rig):
    rig.arm()
    rig.main_task("1", "pending")
    assert_denied(rig.tool("Read"), "Read")
    rig.task("1", "in_progress")
    assert_allowed(rig.tool("Read"))
    rig.task("1", "completed")
    assert_denied(rig.tool("Read"), "Read")


def test_a_main_task_with_no_task_file_does_not_count(rig):
    rig.arm()
    assert_allowed(rig.send("main_task_created", task_id="7"))
    res = rig.tool()
    assert_denied(res)
    assert "has a task file under" in res.stderr


@pytest.mark.parametrize("tool", EXEMPT)
def test_the_task_tools_and_skill_loading_are_never_denied(rig, tool):
    rig.arm()
    assert_allowed(rig.tool(tool))


def test_the_probe_task_tool_calls_pass_while_nothing_is_in_progress(rig):
    rig.arm()
    for name in ("main_pre_tool_use_tool_search", "main_pre_tool_use_task_create", "main_pre_tool_use_task_update"):
        assert_allowed(rig.send(name))


# --- (d) a subagent's in_progress task does not satisfy the main thread -----------------------


def deny_with_only_a_subagent_task_in_progress(rig):
    rig.arm()
    rig.subagent_task("2", "in_progress")
    return is_denied(rig.tool())


def test_a_subagent_owned_in_progress_task_does_not_satisfy_the_main_thread(rig):
    rig.arm()
    rig.subagent_task("2", "in_progress")
    assert_denied(rig.tool())
    rig.main_task("1", "in_progress")
    assert_allowed(rig.tool())


def test_a_task_created_before_the_session_was_armed_is_main_owned(rig):
    rig.main_task("1", "in_progress")
    rig.arm()
    assert_allowed(rig.tool())
    rig.task("1", "pending")
    assert_refused(rig.send("main_task_completed", task_id="1"), "task 1", "pending")


# --- (e) subagent tool calls -------------------------------------------------------------------


def test_a_subagent_tool_call_passes_in_an_armed_session_with_no_task(rig):
    rig.arm()
    assert_denied(rig.tool())
    assert_allowed(rig.send("subagent_pre_tool_use_bash"))


# --- (f) main-thread completion needs in_progress first ---------------------------------------


def refuse_main_completion_of_a_pending_task(rig):
    rig.arm()
    rig.main_task("1", "pending")
    return rig.send("main_task_completed", task_id="1").returncode == 2


def test_the_main_thread_cannot_complete_a_pending_task(rig):
    rig.arm()
    rig.main_task("1", "pending")
    assert_refused(rig.send("main_task_completed", task_id="1"), "task 1", "pending", "in_progress")


def test_the_main_thread_completes_an_in_progress_task(rig):
    rig.arm()
    rig.main_task("1", "in_progress")
    assert_allowed(rig.send("main_task_completed", task_id="1"))


def test_main_completion_of_a_task_the_enforcer_did_not_record_is_checked(rig):
    rig.arm()
    rig.task("9", "pending")
    assert_refused(rig.send("main_task_completed", task_id="9"), "task 9", "pending")
    rig.task("9", "in_progress")
    assert_allowed(rig.send("main_task_completed", task_id="9"))
    rig.task("8", "pending")
    assert_allowed(rig.send("subagent_task_completed", task_id="8"))


# --- (g) a subagent cannot complete a main-owned task -----------------------------------------


def refuse_subagent_completion_of_a_main_task(rig):
    rig.arm()
    rig.main_task("1", "in_progress")
    return rig.send("subagent_task_completed", task_id="1").returncode == 2


def test_a_subagent_cannot_complete_a_main_owned_task(rig):
    rig.arm()
    rig.main_task("1", "in_progress")
    assert_refused(rig.send("subagent_task_completed", task_id="1"), "task 1", "main thread")


def test_a_subagent_completes_its_own_task(rig):
    rig.arm()
    rig.subagent_task("2", "pending")
    assert_allowed(rig.send("subagent_task_completed", task_id="2"))


# --- (h) sessions without the task tools -------------------------------------------------------


def test_an_armed_session_without_the_task_tools_is_never_denied(rig):
    rig.use_transcript("without-task-tools")
    rig.arm()
    assert_allowed(rig.tool())
    assert_allowed(rig.send("main_pre_tool_use_skill_story_to_done"))
    assert_allowed(rig.tool("Read"))


def test_an_armed_session_without_the_task_tools_never_refuses_a_completion(rig):
    rig.use_transcript("without-task-tools")
    rig.arm()
    rig.main_task("1", "pending")
    assert_allowed(rig.send("main_task_completed", task_id="1"))
    assert_allowed(rig.send("subagent_task_completed", task_id="1"))


def test_task_tools_removed_later_in_the_transcript_count_as_absent(rig):
    with rig.transcript.open("a") as fh:
        fh.write(json.dumps({"type": "attachment", "attachment": {
            "type": "deferred_tools_delta", "addedNames": [], "removedNames": ["TaskCreate"], "readdedNames": []}}) + "\n")
    rig.arm()
    assert_allowed(rig.tool())


def test_a_quoted_delta_that_is_not_an_attachment_does_not_count(rig):
    rig.use_transcript("without-task-tools")
    with rig.transcript.open("a") as fh:
        fh.write(json.dumps({"type": "user", "message": {"content": json.dumps(
            {"type": "attachment", "attachment": {"type": "deferred_tools_delta", "addedNames": ["TaskCreate"]}})}}) + "\n")
    rig.arm()
    assert_allowed(rig.tool())


@pytest.mark.parametrize("transcript", ["missing", "", None])
def test_an_unreadable_transcript_counts_as_no_task_tools(rig, transcript):
    rig.arm()
    path = str(rig.transcript.parent / "absent.jsonl") if transcript == "missing" else transcript
    res = rig.tool(transcript_path=path)
    assert_allowed(res)
    if transcript == "missing":
        assert "transcript unreadable" in res.stderr


# --- (i) fail open ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stdin",
    ["", "not json", "[]", "null", json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"}),
     json.dumps({"hook_event_name": "PreToolUse", "session_id": "../escape", "tool_name": "Bash"}),
     json.dumps({"hook_event_name": "PreToolUse", "session_id": 7, "tool_name": "Bash"}),
     json.dumps({"hook_event_name": "PreToolUse", "session_id": SESSION}),
     json.dumps({"hook_event_name": "PreToolUse", "session_id": SESSION, "tool_name": "Bash", "agent_id": ""})],
    ids=["empty", "not-json", "list", "null", "no-session", "path-session", "number-session", "no-tool",
         "empty-agent"],
)
def test_a_malformed_payload_exits_zero_and_logs(rig, stdin):
    rig.arm()
    res = rig.raw(stdin)
    assert_allowed(res)
    assert "todo-enforce" in res.stderr


def test_an_unknown_event_is_ignored(rig):
    rig.arm()
    assert_allowed(rig.send("main_pre_tool_use_bash", hook_event_name="Stop"))


def test_unwritable_state_exits_zero(tmp_path):
    rig = Rig(tmp_path)
    rig.state.write_text("a file where the state directory should be")
    res = rig.send("user_prompt_slash_story_to_done")
    assert_allowed(res)
    assert "todo-enforce" in res.stderr
    assert_allowed(rig.tool())


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_an_unwritable_owners_directory_after_arming_does_not_deny(rig):
    rig.arm()
    owners = rig.state / "agent-skills" / "todo-enforce" / SESSION / "owners"
    owners.mkdir()
    owners.chmod(0o500)
    try:
        res = rig.send("main_task_created", task_id="1")
        assert_allowed(res)
        assert "todo-enforce" in res.stderr
        rig.task("1", "in_progress")
        res = rig.tool()
        assert_allowed(res)
        assert "unwritable" in res.stderr
    finally:
        owners.chmod(0o700)


@pytest.mark.parametrize("content", ["{broken", "[]"], ids=["not-json", "not-an-object"])
def test_an_unreadable_main_task_file_allows_tool_calls_and_refuses_its_completion(rig, content):
    rig.arm()
    rig.main_task("1", "pending")
    (rig.config / "tasks" / SESSION / "1.json").write_text(content)
    res = rig.tool()
    assert_allowed(res)
    assert "task 1 file unreadable" in res.stderr
    res = rig.send("main_task_completed", task_id="1")
    assert_refused(res, "task 1", "could not be read")


def test_an_unreadable_main_task_file_does_not_hide_a_readable_pending_one(rig):
    rig.arm()
    rig.main_task("1", "pending")
    rig.main_task("2", "pending")
    (rig.config / "tasks" / SESSION / "1.json").write_text("{broken")
    assert_denied(rig.tool())


def test_completing_a_main_task_with_no_task_file_is_refused(rig):
    rig.arm()
    assert_allowed(rig.send("main_task_created", task_id="7"))
    assert_refused(rig.send("main_task_completed", task_id="7"), "task 7", "could not be read")


def test_an_owner_file_with_a_trailing_newline_still_reads_as_main(rig):
    rig.arm()
    rig.main_task("1", "pending")
    owner = rig.state / "agent-skills" / "todo-enforce" / SESSION / "owners" / "1"
    owner.write_text("main\n")
    assert_refused(rig.send("main_task_completed", task_id="1"), "task 1", "pending")


def refuse_main_completion_of_an_unreadable_task(rig):
    rig.arm()
    rig.main_task("1", "pending")
    (rig.config / "tasks" / SESSION / "1.json").write_text("{broken")
    return rig.send("main_task_completed", task_id="1").returncode == 2


@pytest.mark.parametrize("task_id", ["../1", "", None])
def test_an_unsafe_task_id_exits_zero(rig, task_id):
    rig.arm()
    payload = {} if task_id is None else {"task_id": task_id}
    created = rig.payload("main_task_created", **payload)
    completed = rig.payload("main_task_completed", **payload)
    if task_id is None:
        del created["task_id"], completed["task_id"]
    for res in (rig.raw(json.dumps(created)), rig.raw(json.dumps(completed))):
        assert_allowed(res)
        assert "todo-enforce" in res.stderr
    owners = rig.state / "agent-skills" / "todo-enforce" / SESSION / "owners"
    assert not owners.exists() or not any(owners.iterdir())


@pytest.mark.parametrize("agent_id", ["", 7, None], ids=["empty", "number", "null"])
def test_a_task_created_without_a_usable_agent_id_is_main_owned(rig, agent_id):
    rig.arm()
    res = rig.send("subagent_task_created", task_id="2", agent_id=agent_id)
    assert_allowed(res)
    assert ("agent_id" in res.stderr) == (agent_id is not None)
    assert (rig.state / "agent-skills" / "todo-enforce" / SESSION / "owners" / "2").read_text() == "main"
    rig.task("2", "in_progress")
    assert_allowed(rig.tool())


def test_a_tilde_in_the_state_root_is_expanded(tmp_path):
    rig = Rig(tmp_path)
    env = rig.env()
    env["XDG_STATE_HOME"] = "~/state"
    res = subprocess.run([sys.executable, "-I", str(rig.script)], input=json.dumps(rig.payload("user_prompt_slash_story_to_done")),
                         env=env, capture_output=True, text=True, timeout=30)
    assert_allowed(res)
    assert (rig.home / "state" / "agent-skills" / "todo-enforce" / SESSION / "armed").is_file()


# --- mutation proof: removing each deny or refuse branch fails its test ---------------------------

BRANCHES = {
    "deny without a main in_progress task": (
        "    return deny(reason)\n",
        [deny_without_any_task, deny_with_a_pending_main_task, deny_with_only_a_subagent_task_in_progress],
    ),
    "only main-owned tasks count": (
        "or owner_of(session, task) != MAIN:",
        [deny_with_only_a_subagent_task_in_progress],
    ),
    "refuse a subagent completing a main task": (
        "        return refuse(SUBAGENT_COMPLETES_MAIN.format(task=task))\n",
        [refuse_subagent_completion_of_a_main_task],
    ),
    "refuse completing a task that is not in_progress": (
        "        return refuse(NOT_IN_PROGRESS.format(task=task, status=status))\n",
        [refuse_main_completion_of_a_pending_task],
    ),
    "refuse completing a task whose file is unreadable": (
        "        return refuse(UNREADABLE.format(task=task, error=error))\n",
        [refuse_main_completion_of_an_unreadable_task],
    ),
}
NEUTRAL = {
    "    return deny(reason)\n": "    return 0\n",
    "or owner_of(session, task) != MAIN:": "or owner_of(session, task) is None:",
    "        return refuse(SUBAGENT_COMPLETES_MAIN.format(task=task))\n": "        pass\n",
    "        return refuse(NOT_IN_PROGRESS.format(task=task, status=status))\n": "        return 0\n",
    "        return refuse(UNREADABLE.format(task=task, error=error))\n": "        return 0\n",
}


@pytest.mark.parametrize("branch", BRANCHES)
def test_each_deny_or_refuse_branch_is_needed(tmp_path, branch):
    snippet, scenarios = BRANCHES[branch]
    source = SOURCE.read_text()
    assert source.count(snippet) == 1, branch
    mutant = tmp_path / "mutant.py"
    mutant.write_text(source.replace(snippet, NEUTRAL[snippet]))
    for i, scenario in enumerate(scenarios):
        real, mutated = tmp_path / f"real-{i}", tmp_path / f"mutant-{i}"
        real.mkdir()
        mutated.mkdir()
        assert scenario(Rig(real)), scenario.__name__
        assert not scenario(Rig(mutated, script=mutant)), scenario.__name__


# --- vendoring (AC8) ---------------------------------------------------------------------------

HEADER = (
    b"# GENERATED from shared/todo-enforce.py by scripts/vendor_shared.py. "
    b"Edit the source, then rerun the script.\n"
)
COPIES = [ROOT / "skills" / skill / "scripts" / "todo-enforce.py" for skill in SKILLS]


def test_the_manifest_vendors_the_enforcer_into_both_skills_only():
    executables = json.loads((ROOT / "skills.json").read_text())["executables"]
    assert sorted(s for s, names in executables.items() if "todo-enforce.py" in names) == sorted(SKILLS)
    assert sorted(ROOT.glob("skills/*/scripts/todo-enforce.py")) == sorted(COPIES)


@pytest.mark.parametrize("copy_path", COPIES, ids=SKILLS)
def test_each_copy_is_the_header_plus_the_source_and_not_executable(copy_path):
    assert copy_path.read_bytes() == HEADER + SOURCE.read_bytes()
    assert not copy_path.stat().st_mode & 0o111


@pytest.mark.parametrize("copy_path", COPIES, ids=SKILLS)
def test_a_vendored_copy_enforces_like_the_source(tmp_path, copy_path):
    rig = Rig(tmp_path, script=copy_path)
    rig.arm()
    assert_denied(rig.tool())
    rig.main_task("1", "in_progress")
    assert_allowed(rig.tool())


@pytest.fixture
def repo_copy(tmp_path):
    """The generator, its manifest, shared/ and skills/ copied so a run cannot touch the checkout."""
    tree = tmp_path / "tree"
    for part in ("scripts", "shared", "skills"):
        shutil.copytree(ROOT / part, tree / part)
    shutil.copyfile(ROOT / "skills.json", tree / "skills.json")
    return tree


def vendor(tree, *args):
    return subprocess.run(
        [sys.executable, "-I", str(tree / "scripts" / "vendor_shared.py"), *args],
        cwd=tree, capture_output=True, text=True, timeout=60,
    )


def snapshot(tree):
    return {p: p.read_bytes() for p in sorted((tree / "skills").rglob("*")) if p.is_file()}


def test_a_second_vendoring_run_changes_nothing(repo_copy):
    assert vendor(repo_copy).returncode == 0
    before = snapshot(repo_copy)
    assert vendor(repo_copy).returncode == 0
    assert snapshot(repo_copy) == before
    assert (vendor(repo_copy, "--check").returncode, vendor(repo_copy, "--check").stdout) == (0, "")


@pytest.mark.parametrize("skill", SKILLS)
def test_the_vendoring_check_fails_when_a_copy_drifts(repo_copy, skill):
    copy_path = repo_copy / "skills" / skill / "scripts" / "todo-enforce.py"
    copy_path.write_bytes(copy_path.read_bytes().replace(b"in_progress", b"in-progress", 1))
    res = vendor(repo_copy, "--check")
    assert res.returncode == 1
    assert f"stale or missing: skills/{skill}/scripts/todo-enforce.py" in res.stdout.splitlines()


def test_no_skill_frontmatter_has_a_hooks_key():
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        front = skill_md.read_text().split("---", 2)[1]
        assert "hooks" not in yaml.safe_load(front), skill_md


# --- the README settings block (AC10) ----------------------------------------------------------


def test_the_readme_block_registers_the_enforcer_for_the_four_events():
    readme = (ROOT / "README.md").read_text()
    section = readme.split("### Todo enforcer hook (Claude Code)", 1)[1].split("\n## ", 1)[0]
    block = json.loads(section.split("```json\n", 1)[1].split("\n```", 1)[0])
    hooks = block["hooks"]
    assert set(hooks) == {"UserPromptSubmit", "PreToolUse", "TaskCreated", "TaskCompleted"}
    assert hooks["PreToolUse"][0]["matcher"] == "*"
    for event, entries in hooks.items():
        (entry,) = entries
        (hook,) = entry["hooks"]
        assert hook["type"] == "command", event
        assert hook["command"] == "python3 ~/.claude/skills/story-to-done/scripts/todo-enforce.py", event
    assert (ROOT / "skills" / "story-to-done" / "scripts" / "todo-enforce.py").is_file()
