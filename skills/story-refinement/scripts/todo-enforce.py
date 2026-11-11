# GENERATED from shared/todo-enforce.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Claude Code hook that keeps a story-to-done or story-refinement main thread on its task list.

  python3 todo-enforce.py < <hook payload JSON>

Register it in settings.json for UserPromptSubmit, PreToolUse (matcher "*"), TaskCreated and
TaskCompleted; the README gives the exact block. It reads the event from the payload's
hook_event_name and, per session_id:

- arms the session when the main thread loads either skill: a PreToolUse Skill call naming it,
  or a UserPromptSubmit prompt that starts with its slash command;
- records each created task's owner, armed or not: "main" without agent_id, else that agent_id;
- in an armed session that has the task tools, denies a main-thread tool call outside
  TaskCreate, TaskUpdate, TaskList, TaskGet, ToolSearch, Skill and AskUserQuestion unless a
  main-owned task is in_progress, and allows it with a stderr warning when the only main-owned
  task files that exist are unreadable;
- in an armed session that has the task tools, refuses (exit 2) a main-owned task's completion
  (a task with no owner record counts as main-owned when the main thread completes it)
  from a subagent, or from the main thread unless its task file still says in_progress
  (TaskCompleted fires before the status is written) or when that file is unreadable.

A session has the task tools when the transcript at transcript_path lists TaskCreate in its
deferred_tools_delta attachments. Subagent tool calls (agent_id set) are never denied.
State lives in ${XDG_STATE_HOME:-$HOME/.local/state}/agent-skills/todo-enforce/<session_id>/
and task files are read from ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/tasks/<session_id>/.
It fails open: a malformed payload, unwritable state or any internal error is logged to
stderr and exits 0. Python 3 standard library only.
"""

import json
import os
import re
import sys

SKILLS = ("story-to-done", "story-refinement")
EXEMPT = frozenset({"TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "ToolSearch", "Skill", "AskUserQuestion"})
MAIN = "main"
SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
SLASH = re.compile(r"/(%s)(\s|$)" % "|".join(map(re.escape, SKILLS)))

NO_TASK_IN_PROGRESS = (
    "todo-enforce: {tool} was not run because no task you created is in_progress. "
    "Mark the task for this step in_progress with TaskUpdate, or create it with TaskCreate "
    "and then mark it in_progress, then retry."
)
NO_TASK_RECORDED = (
    " No task created in this session has been recorded: if you did create one, tell the user "
    "the todo-enforce TaskCreated hook may not be registered."
)
SUBAGENT_COMPLETES_MAIN = (
    "todo-enforce: task {task} belongs to the main thread, so a subagent cannot complete it. "
    "Leave it to the main thread."
)
UNREADABLE = (
    "todo-enforce: task {task} was not completed because its task file could not be read ({error}). "
    "Mark it in_progress with TaskUpdate, then complete it again."
)
NOT_IN_PROGRESS = (
    "todo-enforce: task {task} was not completed because it is {status}, not in_progress. "
    "Mark it in_progress with TaskUpdate when you start the work, then complete it when done."
)


def home_dir(var, *default):
    value = os.environ.get(var)
    return os.path.expanduser(value) if value else os.path.join(os.path.expanduser("~"), *default)


def state_dir(session):
    return os.path.join(home_dir("XDG_STATE_HOME", ".local", "state"), "agent-skills", "todo-enforce", session)


def tasks_dir(session):
    return os.path.join(home_dir("CLAUDE_CONFIG_DIR", ".claude"), "tasks", session)


def log(message):
    print("todo-enforce: " + message, file=sys.stderr)


def safe_id(value):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError("unsafe or missing id: %r" % (value,))
    return value


def agent_of(payload):
    """None on the main thread (agent_id absent or null), else the subagent's id; any other
    unusable agent_id raises."""
    agent = payload.get("agent_id")
    if agent is None:
        return None
    if not isinstance(agent, str) or not agent or agent == MAIN:
        raise ValueError("malformed agent_id: %r" % (agent,))
    return agent


def task_of(payload):
    task = payload.get("task_id")
    return safe_id(str(task) if isinstance(task, int) and not isinstance(task, bool) else task)


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
            return fh.read().strip()
    except FileNotFoundError:
        return None


def record_owner(session, task, owner):
    path = os.path.join(state_dir(session), "owners")
    os.makedirs(path, mode=0o700, exist_ok=True)
    tmp = os.path.join(path, ".%s.%d" % (task, os.getpid()))
    with open(tmp, "w") as fh:
        fh.write(owner)
    os.replace(tmp, os.path.join(path, task))


def owners_writable(session):
    """False, with a log, when no task owner could be recorded for this session."""
    path = os.path.join(state_dir(session), "owners")
    probe = os.path.join(path, ".probe.%d" % os.getpid())
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
        with open(probe, "w"):
            pass
        os.remove(probe)
    except OSError as exc:
        log("task owners cannot be recorded, the state is unwritable: %s: %s"
            % (type(exc).__name__, exc))
        return False
    return True


def task_status(session, task):
    with open(os.path.join(tasks_dir(session), task + ".json")) as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("task file is not a JSON object")
    return data.get("status")


def main_task_in_progress(session):
    """(progress, owned): progress is True, False, or None when the main-owned task files that
    exist are all unreadable; owned counts the main-owned tasks recorded."""
    try:
        tasks = os.listdir(os.path.join(state_dir(session), "owners"))
    except FileNotFoundError:
        tasks = []
    owned = readable = 0
    unreadable = None
    for task in tasks:
        if task.startswith(".") or owner_of(session, task) != MAIN:
            continue
        owned += 1
        try:
            status = task_status(session, task)
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            log("task %s file unreadable: %s: %s" % (task, type(exc).__name__, exc))
            unreadable = task
            continue
        readable += 1
        if status == "in_progress":
            return True, owned
    if unreadable is not None and not readable:
        return None, owned
    if not owned:
        log("no main-created task is recorded for this session; if one was created, "
            "check that the TaskCreated hook is registered")
    elif not readable:
        log("none of this session's %d main-created tasks has a task file under %s"
            % (owned, tasks_dir(session)))
    return False, owned


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
    except OSError as exc:
        log("transcript unreadable, treating the session as without task tools: %s: %s"
            % (type(exc).__name__, exc))
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
    if agent_of(payload) is None and isinstance(prompt, str) and SLASH.match(prompt):
        arm(session)
    return 0


def on_pre_tool_use(payload, session):
    if agent_of(payload) is not None:
        return 0
    tool = payload.get("tool_name")
    if not isinstance(tool, str) or not tool:
        raise ValueError("missing tool_name")
    if tool == "Skill":
        skill = (payload.get("tool_input") or {}).get("skill")
        if skill in SKILLS:
            arm(session)
    if tool in EXEMPT or not is_armed(session):
        return 0
    if not has_task_tools(payload.get("transcript_path")):
        return 0
    progress, owned = main_task_in_progress(session)
    if progress is None:
        log("allowing %s: a main-created task's state is unknown" % tool)
        return 0
    if progress:
        return 0
    reason = NO_TASK_IN_PROGRESS.format(tool=tool)
    if not owned:
        if not owners_writable(session):
            return 0
        reason += NO_TASK_RECORDED
    return deny(reason)


def on_task_created(payload, session):
    task = task_of(payload)
    try:
        agent = agent_of(payload)
    except ValueError as exc:
        log("%s; recording task %s as main-owned" % (exc, task))
        agent = None
    record_owner(session, task, agent or MAIN)
    return 0


def on_task_completed(payload, session):
    if not is_armed(session):
        return 0
    task = task_of(payload)
    agent = agent_of(payload)
    owner = owner_of(session, task)
    if owner not in (None, MAIN) or (owner is None and agent is not None):
        return 0
    if not has_task_tools(payload.get("transcript_path")):
        return 0
    if agent is not None:
        return refuse(SUBAGENT_COMPLETES_MAIN.format(task=task))
    try:
        status = task_status(session, task)
    except (OSError, ValueError) as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
        log("task %s file unreadable: %s" % (task, error))
        return refuse(UNREADABLE.format(task=task, error=error))
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
