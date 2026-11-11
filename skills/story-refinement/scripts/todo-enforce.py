# GENERATED from shared/todo-enforce.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Claude Code hook that keeps a story-to-done or story-refinement main thread on its task list.

  python3 todo-enforce.py < <hook payload JSON>

Register it in settings.json for UserPromptSubmit, PreToolUse (matcher "*"), TaskCreated and
TaskCompleted; the README gives the exact block. It reads the event from the payload's
hook_event_name and, per session_id:

- arms the session when the main thread loads either skill: a PreToolUse Skill call naming it,
  or a UserPromptSubmit prompt that starts with its slash command;
- records each created task's owner: "main" without agent_id, else that agent_id;
- in an armed session that has the task tools, denies a main-thread tool call outside the
  task tools, ToolSearch and Skill unless a main-owned task is in_progress;
- in an armed session, refuses (exit 2) a main-owned task's completion from a subagent, or
  from the main thread unless its task file still says in_progress (TaskCompleted fires
  before the status is written).

A session has the task tools when the transcript at transcript_path lists TaskCreate in its
deferred_tools_delta attachments. Subagent tool calls (agent_id set) are never denied.
State lives in ${XDG_STATE_HOME:-$HOME/.local/state}/agent-skills/todo-enforce/<session_id>/
and task files are read from ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/tasks/<session_id>/.
It fails open: a malformed payload, unreadable state or any internal error is logged to
stderr and exits 0. Python 3 standard library only.
"""

import json
import os
import re
import sys

SKILLS = ("story-to-done", "story-refinement")
EXEMPT = frozenset({"TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "ToolSearch", "Skill"})
MAIN = "main"
SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
SLASH = re.compile(r"/(%s)(\s|$)" % "|".join(map(re.escape, SKILLS)))

NO_TASK_IN_PROGRESS = (
    "todo-enforce: {tool} was not run because no task you created is in_progress. "
    "Mark the task for this step in_progress with TaskUpdate, or create it with TaskCreate "
    "and then mark it in_progress, then retry."
)
SUBAGENT_COMPLETES_MAIN = (
    "todo-enforce: task {task} belongs to the main thread, so a subagent cannot complete it. "
    "Leave it to the main thread."
)
NOT_IN_PROGRESS = (
    "todo-enforce: task {task} was not completed because it is {status}, not in_progress. "
    "Mark it in_progress with TaskUpdate when you start the work, then complete it when done."
)


def home_dir(var, *default):
    return os.environ.get(var) or os.path.join(os.path.expanduser("~"), *default)


def state_dir(session):
    return os.path.join(home_dir("XDG_STATE_HOME", ".local", "state"), "agent-skills", "todo-enforce", session)


def tasks_dir(session):
    return os.path.join(home_dir("CLAUDE_CONFIG_DIR", ".claude"), "tasks", session)


def safe_id(value):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError("unsafe or missing id: %r" % (value,))
    return value


def is_armed(session):
    return os.path.isfile(os.path.join(state_dir(session), "armed"))


def arm(session):
    path = state_dir(session)
    os.makedirs(path, mode=0o700, exist_ok=True)
    with open(os.path.join(path, "armed"), "w"):
        pass


def owner_of(session, task):
    try:
        with open(os.path.join(state_dir(session), "owners", task)) as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def record_owner(session, task, owner):
    path = os.path.join(state_dir(session), "owners")
    os.makedirs(path, mode=0o700, exist_ok=True)
    tmp = os.path.join(path, ".%s.%d" % (task, os.getpid()))
    with open(tmp, "w") as fh:
        fh.write(owner)
    os.replace(tmp, os.path.join(path, task))


def task_status(session, task):
    with open(os.path.join(tasks_dir(session), task + ".json")) as fh:
        return json.load(fh).get("status")


def main_task_in_progress(session):
    try:
        tasks = os.listdir(os.path.join(state_dir(session), "owners"))
    except FileNotFoundError:
        return False
    for task in tasks:
        if task.startswith(".") or owner_of(session, task) != MAIN:
            continue
        try:
            if task_status(session, task) == "in_progress":
                return True
        except (OSError, ValueError):
            continue
    return False


def has_task_tools(transcript):
    """True when the transcript's deferred_tools_delta attachments leave TaskCreate available."""
    if not isinstance(transcript, str) or not transcript:
        return False
    names = set()
    try:
        with open(os.path.expanduser(transcript), "rb") as fh:
            for line in fh:
                if b"deferred_tools_delta" not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "attachment":
                    continue
                delta = entry.get("attachment")
                if not isinstance(delta, dict) or delta.get("type") != "deferred_tools_delta":
                    continue
                names |= set(delta.get("addedNames") or []) | set(delta.get("readdedNames") or [])
                names -= set(delta.get("removedNames") or [])
    except OSError:
        return False
    return "TaskCreate" in names


def deny(reason):
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}, sys.stdout)
    return 0


def refuse(reason):
    print(reason, file=sys.stderr)
    return 2


def on_user_prompt(payload, session):
    prompt = payload.get("prompt")
    if not payload.get("agent_id") and isinstance(prompt, str) and SLASH.match(prompt):
        arm(session)
    return 0


def on_pre_tool_use(payload, session):
    if payload.get("agent_id"):
        return 0
    tool = payload.get("tool_name")
    if tool == "Skill":
        skill = (payload.get("tool_input") or {}).get("skill")
        if skill in SKILLS:
            arm(session)
    if tool in EXEMPT or not is_armed(session):
        return 0
    if not has_task_tools(payload.get("transcript_path")):
        return 0
    if main_task_in_progress(session):
        return 0
    return deny(NO_TASK_IN_PROGRESS.format(tool=tool))


def on_task_created(payload, session):
    if is_armed(session):
        record_owner(session, safe_id(str(payload.get("task_id"))), payload.get("agent_id") or MAIN)
    return 0


def on_task_completed(payload, session):
    if not is_armed(session):
        return 0
    task = safe_id(str(payload.get("task_id")))
    if owner_of(session, task) != MAIN:
        return 0
    if payload.get("agent_id"):
        return refuse(SUBAGENT_COMPLETES_MAIN.format(task=task))
    status = task_status(session, task)
    if status != "in_progress":
        return refuse(NOT_IN_PROGRESS.format(task=task, status=status))
    return 0


HANDLERS = {
    "UserPromptSubmit": on_user_prompt,
    "PreToolUse": on_pre_tool_use,
    "TaskCreated": on_task_created,
    "TaskCompleted": on_task_completed,
}


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("payload is not a JSON object")
        handler = HANDLERS.get(payload.get("hook_event_name"))
        if handler is None:
            return 0
        return handler(payload, safe_id(payload.get("session_id")))
    except Exception as exc:  # fail open: never block a session because of the enforcer itself
        print("todo-enforce: allowing, internal error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
