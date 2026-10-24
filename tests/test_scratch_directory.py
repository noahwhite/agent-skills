"""The scratch directory is one per session, created inside the profile's base directory.

`profile.workspace.scratch_dir` is a base directory, never a session directory: YAML does not
expand environment variables, so a value carrying one resolves to something else entirely, and
a fixed path under the base is shared by every concurrent session. Every instruction that needs
a scratch file goes through the one `mktemp -d` directory the session creates. See SKL-58.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
RUNTIMES = SHARED / "runtimes.md"
TODO_TRACKING = SHARED / "todo-tracking.md"
PROFILE = SHARED / "profile.md"
SCHEMA = ROOT / "profile" / "schema.json"
SKILLS = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))

FENCE_RE = re.compile(r"^[ \t]*```[a-z]*\n(.*?)^[ \t]*```$", re.MULTILINE | re.DOTALL)


def fenced_blocks(text: str) -> list[str]:
    return FENCE_RE.findall(text)


def scratch_one_liner() -> str:
    """The shell snippet `shared/runtimes.md` documents for the per-session directory."""
    blocks = [block for block in fenced_blocks(RUNTIMES.read_text()) if "mktemp -d" in block]
    assert len(blocks) == 1, f"expected exactly one mktemp -d snippet in {RUNTIMES.name}, got {len(blocks)}"
    return blocks[0]


def run_one_liner(block: str, env: dict[str, str]) -> Path:
    """Run the documented snippet and print the directory it chose."""
    script = "\n".join(line for line in block.splitlines() if line.strip() and not line.strip().startswith("#"))
    script += '\nprintf "%s\\n" "$scratch"\n'
    res = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        capture_output=True, text=True, env={**os.environ, **env},
    )
    assert res.returncode == 0, res.stderr
    return Path(res.stdout.strip().splitlines()[-1])


def test_the_snippet_uses_set_u_safe_expansion():
    block = scratch_one_liner()
    assert "mktemp -d" in block
    # `set -u` is the container contract: the snippet must not dereference an unset variable.
    run_one_liner(block, {"scratch_base": ""})


def test_snippet_makes_a_distinct_dir_inside_the_base(tmp_path):
    block = scratch_one_liner()
    base = tmp_path / "scratch-base"
    base.mkdir()
    first = run_one_liner(block, {"scratch_base": str(base)})
    second = run_one_liner(block, {"scratch_base": str(base)})
    assert first != second, "two sessions must not share one scratch directory"
    for path in (first, second):
        assert path.is_dir(), f"{path} does not exist"
        assert path.parent == base, f"{path} is not directly inside the base directory"
    assert list(base.iterdir()) == sorted([first, second]) or set(base.iterdir()) == {first, second}


def test_snippet_falls_back_to_a_standalone_dir_when_the_base_is_unset(tmp_path):
    block = scratch_one_liner()
    first = run_one_liner(block, {"scratch_base": "", "TMPDIR": str(tmp_path)})
    second = run_one_liner(block, {"scratch_base": "", "TMPDIR": str(tmp_path)})
    assert first != second
    for path in (first, second):
        assert path.is_dir(), f"{path} does not exist (a standalone mktemp -d uses the temp dir)"
        assert path.parent == tmp_path, f"{path} escaped the runtime's temp directory"


def test_runtimes_rule_is_the_per_session_directory():
    text = RUNTIMES.read_text()
    rule = text.split("**Scratch files.**", 1)
    assert len(rule) == 2, "shared/runtimes.md lost its Scratch files rule"
    body = rule[1].split("\n- ", 1)[0]
    for phrase in ("`mktemp -d`", "`profile.workspace.scratch_dir`", "one", "per session",
                   "never write to a fixed", "profile.workspace.scratch_dir"):
        assert phrase.lower() in body.lower(), f"the Scratch files rule does not say {phrase!r}: {body}"
    assert "artefact" in body or "artifact" in body, "the rule must say what the directory is for"
    assert "subagent" in body.lower(), "the rule must pass the same path to subagents"


def test_runtimes_rule_keeps_the_documented_fallback():
    """AC5: the fallback stands - no base directory means a standalone `mktemp -d`."""
    body = RUNTIMES.read_text().split("**Scratch files.**", 1)[1].split("\n- ", 1)[0]
    assert "When neither the runtime nor `profile.workspace.scratch_dir` gives a directory" in body
    assert "for the whole task" in body


def test_todo_tracking_routes_the_checklist_through_the_session_directory():
    text = TODO_TRACKING.read_text()
    assert "per-session" in text or "one scratch directory" in text, \
        "shared/todo-tracking.md must state the per-session rule, not just point at the scratch directory"
    assert "$CLAUDE_JOB_DIR" not in text
    # The checklist names itself relative to the session directory, never under the base.
    assert "`<scratch directory>/<session-label>-todo.md`" in text or \
        "`<scratch directory>/<agent-label>-todo.md`" in text


def test_profile_reference_documents_the_scratch_base():
    text = PROFILE.read_text()
    assert "profile.workspace.scratch_dir" in text, "shared/profile.md must document the scratch base"
    section = text.split("## Scratch directories", 1)
    assert len(section) == 2, "shared/profile.md needs a Scratch directories section"
    body = section[1].split("\n## ", 1)[0]
    for phrase in ("base directory", "never the per-session directory", "optional", "mktemp -d"):
        assert phrase.lower() in body.lower(), f"the profile scratch section does not say {phrase!r}: {body}"


def test_schema_calls_scratch_dir_a_base_and_keeps_it_optional():
    import json

    schema = json.loads(SCHEMA.read_text())
    workspace = schema["properties"]["workspace"]
    assert "workspace" not in schema.get("required", []), "workspace must stay optional"
    assert "required" not in workspace, "the workspace keys must stay optional"
    description = workspace["properties"]["scratch_dir"]["description"]
    for phrase in ("base", "mktemp -d", "optional"):
        assert phrase.lower() in description.lower(), f"the schema description does not say {phrase!r}: {description}"
    assert "must set" not in description.lower()


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_vendored_runtimes_copies_carry_the_rule(skill):
    shared = RUNTIMES.read_text()
    vendored = (skill / "references" / "runtimes.md").read_text()
    rule = shared.split("**Scratch files.**", 1)[1].split("\n- ", 1)[0]
    assert rule in vendored, f"{skill.name} carries a stale runtimes rule; run scripts/vendor_shared.py"


def test_shared_text_names_no_fixed_scratch_path():
    """No base instruction may name a fixed file directly under the base or under /tmp."""
    offenders = []
    for md in sorted(SHARED.glob("*.md")):
        for n, line in enumerate(md.read_text().splitlines(), 1):
            for hit in re.findall(r"`(/tmp/[^`\s]+|\$[A-Z_]+/tmp/[^`\s]+)`", line):
                if "mktemp" in line:
                    continue
                offenders.append(f"{md.relative_to(ROOT)}:{n}: {hit}")
    assert not offenders, "\n".join(offenders)


def test_vendor_check_passes():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
