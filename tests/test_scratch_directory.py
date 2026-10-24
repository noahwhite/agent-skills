"""The scratch directory is one per session, created inside the base directory.

`profile.workspace.scratch_dir` is a base directory, never a session directory: YAML does not
expand environment variables, so a value carrying one resolves to something else entirely, and
a fixed path under the base is shared by every concurrent session. Every instruction that needs
a scratch file goes through the one `mktemp -d` directory the session creates. See SKL-58.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
RUNTIMES = SHARED / "runtimes.md"
TODO_TRACKING = SHARED / "todo-tracking.md"
PROFILE = SHARED / "profile.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
EXAMPLE = ROOT / "profile" / "example.yaml"
SKILLS = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))

RULE_HEADING = "**Scratch files.**"
FENCE_RE = re.compile(r"^[ \t]*```[a-z]*\n(.*?)^[ \t]*```$", re.MULTILINE | re.DOTALL)
FENCE_STRIP_RE = re.compile(r"^[ \t]*```[a-z]*\n.*?^[ \t]*```$", re.MULTILINE | re.DOTALL)


def rule_paragraph() -> str:
    """The Scratch files bullet, without its fenced snippet."""
    text = RUNTIMES.read_text()
    assert RULE_HEADING in text, "shared/runtimes.md lost its Scratch files rule"
    bullet = text.split(RULE_HEADING, 1)[1].split("\n- ", 1)[0]
    return FENCE_STRIP_RE.sub("", bullet)


def scratch_one_liner() -> str:
    """The shell snippet the Scratch files rule documents for the per-session directory."""
    text = RUNTIMES.read_text()
    assert RULE_HEADING in text, "shared/runtimes.md lost its Scratch files rule"
    tail = text.split(RULE_HEADING, 1)[1]
    blocks = [block for block in FENCE_RE.findall(tail) if "mktemp -d" in block]
    assert blocks, "the Scratch files rule carries no mktemp -d snippet"
    return blocks[0]


def run_one_liner(block: str, env: dict[str, str]) -> Path:
    """Run the documented snippet in a clean shell and return the directory it chose."""
    script = "\n".join(
        line for line in block.splitlines() if line.strip() and not line.strip().startswith("#")
    )
    script += '\nprintf "%s\\n" "$scratch"\n'
    base_env = {k: v for k, v in os.environ.items() if k != "scratch_base"}
    res = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        capture_output=True, text=True, env={**base_env, **env},
    )
    assert res.returncode == 0, res.stderr
    return Path(res.stdout.strip().splitlines()[-1])


def test_the_snippet_runs_with_scratch_base_unset_under_set_u(tmp_path):
    """`set -u` is the container contract; the snippet must not dereference an unset variable."""
    path = run_one_liner(scratch_one_liner(), {"TMPDIR": str(tmp_path)})
    assert path.is_dir(), f"{path} was not created"
    assert path.parent == tmp_path


def test_snippet_creates_a_distinct_dir_inside_the_base(tmp_path):
    block = scratch_one_liner()
    base = tmp_path / "scratch-base"
    base.mkdir()
    paths = [run_one_liner(block, {"scratch_base": str(base)}) for _ in range(3)]
    assert len(set(paths)) == 3, f"two sessions shared a scratch directory: {paths}"
    for path in paths:
        assert path.is_dir(), f"{path} does not exist"
        assert path.parent == base, f"{path} is not directly inside the base directory"


def test_snippet_creates_a_missing_base_instead_of_failing(tmp_path):
    """A configured base that does not exist yet must be created, never abort the session."""
    base = tmp_path / "not-created-yet" / "nested"
    path = run_one_liner(scratch_one_liner(), {"scratch_base": str(base)})
    assert base.is_dir(), "the snippet did not create the configured base directory"
    assert path.is_dir() and path.parent == base


def test_snippet_falls_back_to_a_standalone_dir_when_the_base_is_unset(tmp_path):
    block = scratch_one_liner()
    paths = [run_one_liner(block, {"TMPDIR": str(tmp_path)}) for _ in range(3)]
    assert len(set(paths)) == 3
    for path in paths:
        assert path.is_dir(), f"{path} does not exist (a standalone mktemp -d uses the temp dir)"
        assert path.parent == tmp_path, f"{path} escaped the runtime's temp directory"


def test_runtimes_rule_is_the_per_session_directory():
    body = rule_paragraph()
    for phrase in ("exactly one scratch directory", "for the session's lifetime", "`mktemp -d`",
                   "base directory the runtime or the profile gives", "every scratch artefact",
                   "subagent", "shell-launched agent", "never write to a fixed file"):
        assert phrase.lower() in body.lower(), f"the Scratch files rule does not say {phrase!r}"
    assert "`profile.workspace.scratch_dir`" in body
    assert "a base only, never the directory a session works in" in body


def test_runtimes_rule_keeps_the_documented_fallback():
    """AC5: the fallback stands - no base directory means a standalone `mktemp -d`."""
    body = rule_paragraph()
    assert "When neither the runtime nor `profile.workspace.scratch_dir` gives a directory" in body
    assert "create one with a standalone `mktemp -d` and use it for the whole task" in body
    assert "A base that cannot be created or written falls back the same way." in body


def test_capability_row_calls_the_value_a_base_directory():
    row = next(line for line in RUNTIMES.read_text().splitlines() if line.startswith("| Scratch"))
    assert row.split("|")[1].strip() == "Scratch base directory", row
    assert "`$CLAUDE_JOB_DIR/tmp`" in row, "the claude background-job base entry stays"


def test_todo_tracking_routes_every_checklist_through_the_session_directory():
    text = TODO_TRACKING.read_text()
    assert "`<scratch directory>/<agent-label>-todo.md`, where `<scratch directory>` is the one scratch directory the session created for its lifetime" in text
    assert "`<scratch directory>/<session-label>-todo.md`" in text
    assert "never a fixed path under the base" in text
    assert "$CLAUDE_JOB_DIR" not in text


def test_profile_reference_documents_the_scratch_base():
    text = PROFILE.read_text()
    assert "profile.workspace.scratch_dir" in text, "shared/profile.md must document the scratch base"
    section = text.split("## Scratch directories", 1)
    assert len(section) == 2, "shared/profile.md needs a Scratch directories section"
    body = section[1].split("\n## ", 1)[0]
    for phrase in ("base directory only", "never the per-session directory", "exactly one directory",
                   "`mktemp -d`", "optional", "no skill or overlay requires it to be set",
                   "standalone `mktemp -d`"):
        assert phrase.lower() in body.lower(), f"the profile scratch section does not say {phrase!r}"


def test_schema_calls_scratch_dir_a_base_and_keeps_it_optional():
    workspace = SCHEMA["properties"]["workspace"]
    assert "workspace" not in SCHEMA.get("required", []), "workspace must stay optional"
    description = workspace["properties"]["scratch_dir"]["description"]
    for phrase in ("base directory", "mktemp -d", "optional", "standalone"):
        assert phrase.lower() in description.lower(), f"the schema description does not say {phrase!r}"
    # Optional for real: a profile with an empty workspace still validates.
    example = yaml.safe_load(EXAMPLE.read_text())
    example["workspace"] = {}
    jsonschema.validate(example, SCHEMA)
    example.pop("workspace")
    jsonschema.validate(example, SCHEMA)


def test_no_doc_states_the_profile_must_set_the_scratch_dir():
    """AC5: the key is optional everywhere, so no instruction makes it mandatory."""
    pattern = re.compile(r"must set[^.\n]*scratch_dir|scratch_dir[^.\n]*is required", re.IGNORECASE)
    offenders = [
        f"{md.relative_to(ROOT)}:{n}: {line.strip()}"
        for md in md_files()
        for n, line in enumerate(md.read_text().splitlines(), 1)
        if pattern.search(line)
    ]
    assert not offenders, "\n".join(offenders)


def test_no_doc_names_a_fixed_scratch_path_under_the_base():
    """AC2: every scratch artefact lives in the session's directory, never at a fixed path.

    The one exception is the merge-approval rendezvous: an engagement's shared file with a
    manager-created unique directory, not a session's scratch (shared/merge-approval.md).
    """
    fixed_under_base = re.compile(
        r"profile\.workspace\.scratch_dir\s*/\s*[^\s`'\"]+"
        r"|\$CLAUDE_JOB_DIR/tmp/[A-Za-z0-9_.<>-]+"
    )
    offenders = []
    for md in md_files():
        for n, line in enumerate(md.read_text().splitlines(), 1):
            if md.name == "runtimes.md":
                continue  # the capability map names the runtime's own base, and stays
            for hit in fixed_under_base.findall(line):
                offenders.append(f"{md.relative_to(ROOT)}:{n}: {hit}")
    assert not offenders, "\n".join(offenders)


def md_files() -> list[Path]:
    return sorted(
        p
        for root in (SHARED, ROOT / "skills", ROOT / "profile")
        for p in root.rglob("*.md")
        if ".git" not in p.parts and ".venv" not in p.parts
    )


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_vendored_runtimes_copies_carry_the_rule(skill):
    vendored = skill / "references" / "runtimes.md"
    assert vendored.is_file(), f"{skill.name} has no vendored references/runtimes.md"
    rule = RUNTIMES.read_text().split(RULE_HEADING, 1)[1].split("\n- ", 1)[0]
    assert rule in vendored.read_text(), f"{skill.name} carries a stale runtimes rule; run scripts/vendor_shared.py"


def test_vendor_check_passes():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
