# GENERATED from shared/todo-enforce.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Claude Code hook that keeps a story-to-done or story-refinement main thread on its task list.

  python3 todo-enforce.py < <hook payload JSON>

Register it in settings.json for UserPromptSubmit, PreToolUse (matcher "*"), TaskCreated,
TaskCompleted and Stop (no matcher); the README gives the exact block. It reads the event from the
payload's hook_event_name and, per session_id:

- arms the session when the main thread loads either skill: a PreToolUse Skill call naming it,
  or a UserPromptSubmit prompt that starts with its slash command;
- records each created task's owner, armed or not: "main" without agent_id, else that agent_id;
- in an armed session that has the task tools, denies a main-thread tool call outside
  TaskCreate, TaskUpdate, TaskList, TaskGet, ToolSearch, Skill and AskUserQuestion unless a
  main-owned task is in_progress, and allows it with a stderr warning when a main-owned task
  file that exists is unreadable;
- in an armed session that has the task tools, refuses (exit 2) a main-owned task's completion
  (a task with no owner record counts as main-owned when the main thread completes it)
  from a subagent, or from the main thread unless its task file still says in_progress
  (TaskCompleted fires before the status is written) or when that file is unreadable;
- report gate: in an armed session that has the task tools, blocks a Stop (stdout
  {"decision": "block", ...}, exit 0) whose last_assistant_message has a line matching
  ^report: final\\s*$ while a main-owned task whose file reads pending or in_progress is not
  named on a line containing "not done" and its #<id>; a Stop without that line, or carrying
  agent_id, is allowed, and a missing or non-string last_assistant_message, unreadable state or an
  unreadable task file allows it with a stderr warning;
- loop guard: the report gate blocks at most REPORT_BLOCK_LIMIT consecutive times, then allows with
  a stderr line; the count lives in the state directory, increments only when a block is emitted,
  and resets on any Stop the gate allows and on a main-thread UserPromptSubmit, and
  stop_hook_active is not used.

The report gate does nothing, silently, in a session that is not armed, has no task tools, or
whose report has no signal line; it logs to stderr when it allows a report because the state, the
owner records or a task file cannot be read.

A session has the task tools when the transcript at transcript_path lists TaskCreate in its
deferred_tools_delta attachments. Subagent tool calls (agent_id set) are never denied.
State lives in ${XDG_STATE_HOME:-$HOME/.local/state}/agent-skills/todo-enforce/<session_id>/
and task files are read from ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/tasks/<session_id>/.
It fails open: a malformed payload, unwritable state or any internal error is logged to
stderr and exits 0. Python 3 standard library only.
"""

import contextlib
import json
import os
import re
import stat
import sys

try:
    import fcntl
except ImportError:  # no flock on this platform: the loop guard runs unlocked
    fcntl = None

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
OPEN_ITEMS = (
    "todo-enforce: this final report was held back because these tasks you created are still open: {items}. "
    "For each one, mark it in_progress with TaskUpdate if it is pending, then complete it, or name it "
    "on a line with \"not done\", its #<id> and the reason in the same text block as the report: final "
    "line, then report again."
)
NO_SUBJECT = "(no subject)"

IN_PROGRESS = "in_progress"
OPEN = ("pending", IN_PROGRESS)
REPORT_BLOCK_LIMIT = 3
REPORT_SIGNAL = re.compile(r"^report: final\s*$")


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
    """False when the armed marker is absent, and, with a log, when the state cannot be read."""
    try:
        return stat.S_ISREG(os.stat(os.path.join(state_dir(session), "armed")).st_mode)
    except FileNotFoundError:
        return False
    except OSError as exc:
        log("treating the session as not armed, the state is unreadable: %s: %s"
            % (type(exc).__name__, exc))
        return False


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


def task_file(session, task):
    with open(os.path.join(tasks_dir(session), task + ".json")) as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("task file is not a JSON object")
    return data


def task_status(session, task):
    return task_file(session, task).get("status")


def main_owned_tasks(session):
    """Yields the ids of the tasks the owner records mark main, reading each record only when the
    caller asks for the next id; none when no owner is recorded."""
    try:
        tasks = os.listdir(os.path.join(state_dir(session), "owners"))
    except FileNotFoundError:
        return
    for task in tasks:
        if task.startswith(".") or owner_of(session, task) != MAIN:
            continue
        yield task


def log_no_main_task():
    log("no main-created task is recorded for this session; if one was created, "
        "check that the TaskCreated hook is registered")


def main_task_in_progress(session):
    """(progress, owned): progress is True, False, or None when no main-owned task is
    in_progress and one that exists is unreadable; owned counts the main-owned tasks recorded."""
    owned = readable = 0
    unreadable = None
    for task in main_owned_tasks(session):
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
        if status == IN_PROGRESS:
            return True, owned
    if unreadable is not None:
        return None, owned
    if not owned:
        log_no_main_task()
    elif not readable:
        log("none of this session's %d main-created tasks has a task file under %s"
            % (owned, tasks_dir(session)))
    return False, owned


def read_tools_cache(path, transcript):
    """(offset, names) an earlier call saved for this transcript, else (0, empty set)."""
    try:
        with open(path) as fh:
            data = json.load(fh)
        if data["transcript"] == transcript:
            return int(data["offset"]), set(data["names"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return 0, set()


def write_tools_cache(path, transcript, offset, names):
    tmp = "%s.%d" % (path, os.getpid())
    try:
        with open(tmp, "w") as fh:
            json.dump({"transcript": transcript, "offset": offset, "names": sorted(names)}, fh)
        os.replace(tmp, path)
    except OSError as exc:
        log("transcript scan position not saved: %s: %s" % (type(exc).__name__, exc))


def has_task_tools(session, transcript):
    """True when the transcript's deferred_tools_delta attachments leave TaskCreate available.

    The transcript only grows, so each call reads only the complete lines past the offset an
    earlier call saved; a transcript shorter than that offset is read again from the start."""
    if not isinstance(transcript, str) or not transcript:
        return False
    cache = os.path.join(state_dir(session), "tools.json")
    offset, names = read_tools_cache(cache, transcript)
    try:
        with open(os.path.expanduser(transcript), "rb") as fh:
            if fh.seek(0, os.SEEK_END) < offset:
                offset, names = 0, set()
            fh.seek(offset)
            for line in fh:
                if not line.endswith(b"\n"):
                    break
                offset += len(line)
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
    write_tools_cache(cache, transcript, offset, names)
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


def block(reason):
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.stdout.flush()
    return 0


def report_blocks_path(session):
    return os.path.join(state_dir(session), "report-blocks")


@contextlib.contextmanager
def report_blocks_lock(session):
    """Holds an exclusive lock on the block count, so overlapping Stops count one at a time."""
    if fcntl is None:
        yield
        return
    with open(report_blocks_path(session) + ".lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def reset_report_blocks(session):
    """Removes the block count under the count's lock; a session with no state directory has
    no count to reset."""
    if not os.path.isdir(state_dir(session)):
        return
    try:
        with report_blocks_lock(session):
            os.remove(report_blocks_path(session))
    except FileNotFoundError:
        pass
    except OSError as exc:
        log("report block count not reset: %s: %s" % (type(exc).__name__, exc))


def read_report_blocks(session):
    """The consecutive report blocks emitted so far: 0 when none is recorded, and a stored value
    outside 0..REPORT_BLOCK_LIMIT is clamped into that range with a log."""
    try:
        with open(report_blocks_path(session)) as fh:
            blocks = int(fh.read())
    except FileNotFoundError:
        return 0
    if not 0 <= blocks <= REPORT_BLOCK_LIMIT:
        log("report block count %d is outside 0..%d, clamped" % (blocks, REPORT_BLOCK_LIMIT))
        blocks = max(0, min(blocks, REPORT_BLOCK_LIMIT))
    return blocks


def write_report_blocks(session, blocks):
    path = report_blocks_path(session)
    tmp = "%s.%d" % (path, os.getpid())
    with open(tmp, "w") as fh:
        fh.write(str(blocks))
    os.replace(tmp, path)


def open_main_items(session):
    """[(id, subject)] of the main-owned tasks whose task file reads pending or in_progress;
    an unreadable task file raises."""
    tasks = list(main_owned_tasks(session))
    if not tasks:
        log_no_main_task()
    items = []
    for task in tasks:
        try:
            data = task_file(session, task)
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            raise ValueError("task %s file unreadable: %s: %s" % (task, type(exc).__name__, exc))
        if data.get("status") in OPEN:
            subject = data.get("subject")
            subject = " ".join(subject.split()) if isinstance(subject, str) else ""
            items.append((task, subject or NO_SUBJECT))
    return sorted(items, key=lambda item: (len(item[0]), item[0]))


def named_not_done(task, lines):
    mention = re.compile(r"(?<!\w)#%s(?!\d)" % re.escape(task))
    return any("not done" in line.lower() and mention.search(line) for line in lines)


def report_gate(payload, session):
    """The block reason for a final report that leaves an open item unnamed, else None."""
    if agent_of(payload) is not None or not is_armed(session):
        return None
    text = payload.get("last_assistant_message")
    if not isinstance(text, str):
        log("allowing the stop: last_assistant_message is missing or not a string")
        return None
    lines = text.splitlines()
    if not any(REPORT_SIGNAL.match(line) for line in lines):
        return None
    if not has_task_tools(session, payload.get("transcript_path")):
        return None
    try:
        items = open_main_items(session)
    except ValueError as exc:
        log("allowing the report: %s" % exc)
        return None
    unnamed = ["#%s %s" % item for item in items if not named_not_done(item[0], lines)]
    if not unnamed:
        return None
    return OPEN_ITEMS.format(items="; ".join(unnamed))


def on_stop(payload, session):
    try:
        reason = report_gate(payload, session)
    except (OSError, ValueError) as exc:
        log("allowing the stop, the report gate could not read the payload or the state: %s: %s"
            % (type(exc).__name__, exc))
        reason = None
    if reason is None:
        reset_report_blocks(session)
        return 0
    try:
        with report_blocks_lock(session):
            blocks = read_report_blocks(session)
            if blocks < REPORT_BLOCK_LIMIT:
                write_report_blocks(session, blocks + 1)
                return block(reason)
        log("allowing the report: the report gate already blocked %d consecutive times "
            "(REPORT_BLOCK_LIMIT = %d)" % (blocks, REPORT_BLOCK_LIMIT))
    except (OSError, ValueError) as exc:
        log("allowing the report, the report gate state is unreadable or unwritable or the block "
            "could not be written: %s: %s" % (type(exc).__name__, exc))
    reset_report_blocks(session)
    return 0


def on_user_prompt(payload, session):
    prompt = payload.get("prompt")
    if agent_of(payload) is None:
        reset_report_blocks(session)
        if isinstance(prompt, str) and SLASH.match(prompt):
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
    if not has_task_tools(session, payload.get("transcript_path")):
        return 0
    progress, owned = main_task_in_progress(session)
    if progress is None:
        log("allowing %s: a main-created task's state is unknown" % tool)
        return 0
    if progress:
        return 0
    if not owners_writable(session):
        return 0
    reason = NO_TASK_IN_PROGRESS.format(tool=tool)
    if not owned:
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
    if not has_task_tools(session, payload.get("transcript_path")):
        return 0
    if agent is not None:
        return refuse(SUBAGENT_COMPLETES_MAIN.format(task=task))
    try:
        status = task_status(session, task)
    except (OSError, ValueError) as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
        log("task %s file unreadable: %s" % (task, error))
        return refuse(UNREADABLE.format(task=task, error=error))
    if status != IN_PROGRESS:
        return refuse(NOT_IN_PROGRESS.format(task=task, status=status))
    return 0


HANDLERS = {
    "UserPromptSubmit": on_user_prompt,
    "PreToolUse": on_pre_tool_use,
    "TaskCreated": on_task_created,
    "TaskCompleted": on_task_completed,
    "Stop": on_stop,
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
