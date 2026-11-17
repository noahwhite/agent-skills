"""Source-document contracts; generated references are checked after vendoring."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIMES = ROOT / "shared" / "runtimes.md"


def test_runtime_map_distinguishes_v2_and_legacy_v1() -> None:
    text = RUNTIMES.read_text()
    assert "V2" in text and "V1" in text
    assert "legacy, untested" in text
    assert "supported legacy fields" in text.lower()
    assert "translated" in text.lower()
    assert "SKL-23 settles" not in text
    for topic in ("agents", "config", "migrate-v1", "cli"):
        assert f"https://opencode.ai/v2/docs/{topic}" in text


def test_native_v2_nesting_example_has_depth_and_ordered_permissions() -> None:
    text = RUNTIMES.read_text()
    examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", text, re.S)]
    nested = next(example for example in examples if example.get("experimental", {}).get("subagent_depth") == 2)
    assert "subagent_depth" not in nested
    assert nested["$schema"] == "https://opencode.ai/config.json"
    child = nested["agents"]["delegated-engineer"]
    assert child["mode"] == "subagent"
    assert "#" in child["model"]
    assert isinstance(child["permissions"], list)
    assert {"action": "subagent", "resource": "*", "effect": "allow"} in child["permissions"]
    assert "top-level `subagent_depth` is ignored with a warning" in text
    assert "built-in `general` cannot launch children" in text
    assert "last matching rule wins" in text


def test_v2_invocation_separates_automation_and_interactive_model_selection() -> None:
    text = RUNTIMES.read_text()
    assert "opencode run --agent ID --model provider/model#variant" in text
    assert "root TUI rejects `--agent` and `--model`" in text
    assert "Selecting a primary agent does not change the session model" in text
    assert "OPENCODE_CONFIG_CONTENT" in text and "private server" in text
    assert "command frontmatter" in text
    # A root `model` default keeps its #variant on fresh sessions (verified against 2.1.3);
    # what it cannot do is pin a session that already exists.
    assert "root `model` default can retain its `#variant`" in text
    assert "does not retain a `#variant`" not in text


DELEGATED_DIRECTORY_MARKER = "- **Delegated working directory.**"
DELEGATED_DIRECTORY_CLAUSES = (
    "A delegated agent (a subagent) starts in the working directory of the session that spawns it, and no runtime in "
    "the map lets the delegating session set that directory to a chosen path.",
    "The delegating session therefore creates the per-story worktree itself before the spawn and names its absolute "
    "path in the brief, and the delegated agent addresses every file and git command to that path, by absolute path "
    "or `git -C <path>`.",
    "A runtime's own worktree isolation does not replace the per-story worktree, because it chooses its own branch, "
    "base and lifetime.",
    "Removing the worktree is not part of the spawn and stays with the existing branch and worktree rules and the "
    "`cleanup` skill.",
)


def delegated_directory_bullet() -> list[str]:
    """The SKL-70 bullet under "Rules that follow from the map", one physical line per entry."""
    rules = RUNTIMES.read_text(encoding="utf-8").split("## Rules that follow from the map\n", 1)[1]
    lines = rules.split("\n## ", 1)[0].splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(DELEGATED_DIRECTORY_MARKER)]
    assert len(starts) == 1, "expected one delegated working directory bullet under the map rules"
    # The bullet runs to the next bullet or blank line, so an unindented (lazy) continuation line is
    # part of it and fails the clause comparison instead of escaping it.
    bullet = [lines[starts[0]]]
    for line in lines[starts[0] + 1:]:
        if not line.strip() or line.startswith("- "):
            break
        bullet.append(line)
    return bullet


def test_delegated_agent_works_in_the_worktree_the_delegating_session_creates() -> None:
    bullet = delegated_directory_bullet()
    first = bullet[0].removeprefix(DELEGATED_DIRECTORY_MARKER + " ")
    assert [first, *(line.removeprefix("  ") for line in bullet[1:])] == list(DELEGATED_DIRECTORY_CLAUSES), (
        "one clause per physical line, continuation lines indented exactly two spaces, and nothing else"
    )


def test_delegated_directory_bullet_names_no_path_helper_or_memory_rule() -> None:
    text = "\n".join(delegated_directory_bullet())
    assert not re.search(r"memory|retir", text, re.IGNORECASE)
    # A `references/<name>.md` mention would vendor that file into every runtimes.md copy.
    assert not re.search(r"[\w.-]+/[\w./-]+|\.md\b|\.py\b|\.sh\b", text), "the bullet names no file path"
    assert "opencode-worktree" not in text, "the bullet names no helper tool"


def test_todo_is_optional_tool_not_optional_tracking() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "primary session" in text
    assert "checklist file" in text
    assert "Do not block" in text
    assert "Subagents have no todo list." not in text
    # Version- and configuration-specific facts live in the runtime map, not in the
    # runtime-neutral capability file (see the C27/C29 arbitration finding).
    runtimes = (ROOT / "shared" / "runtimes.md").read_text()
    assert "off by default" in runtimes
    assert "experimental.todo" in runtimes
    assert "experimental.todo" not in text
    assert "opencode" not in text.lower()
