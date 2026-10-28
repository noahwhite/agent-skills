"""The scratch directory is one per session, created inside the base directory.

`profile.workspace.scratch_dir` is a base directory, never a session directory: YAML does not
expand environment variables, so a value carrying one resolves to something else entirely, and
a fixed path under the base is shared by every concurrent session. Every instruction that needs
a scratch file goes through the one `mktemp -d` directory the session creates. See SKL-58.
"""

import json
import os
import re
import shlex
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
    """Run the documented snippet in a clean shell and return the directory it chose.

    Comment lines are dropped, as a reader copying the block into a shell effectively does; the
    block is separately parsed verbatim by `test_the_published_snippet_parses`.
    """
    script = "\n".join(
        line for line in block.splitlines() if line.strip() and not line.strip().startswith("#")
    )
    if "printf" not in script:
        script += '\nprintf "%s\\n" "$scratch"\n'
    base_env = {k: v for k, v in os.environ.items() if k != "scratch_base"}
    res = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        capture_output=True, text=True, env={**base_env, **env},
    )
    assert res.returncode == 0, res.stderr
    return Path(res.stdout.strip().splitlines()[-1])


def test_the_published_snippet_parses():
    """The block is executed as published, so it must parse as published."""
    res = subprocess.run(["bash", "-n", "-c", scratch_one_liner()], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_a_relative_base_falls_back_instead_of_escaping():
    """A relative base is refused, never resolved against the working directory."""
    block = scratch_one_liner()
    for relative in ("relative-base", ".scratch"):
        path = run_one_liner(block, {"scratch_base": relative, "TMPDIR": "/tmp"})
        assert path.parent == Path("/tmp"), f"{relative} leaked into the chosen directory: {path}"
        assert not Path(relative).exists(), f"{relative} was created in the working directory"


def test_the_snippet_falls_back_when_mktemp_inside_the_base_fails(tmp_path):
    """The last-resort branch: a base that mktemp refuses must degrade, not abort."""
    shim = tmp_path / "bin"
    shim.mkdir()
    shim_script = shim / "mktemp"
    real_mktemp = subprocess.run(
        ["bash", "-c", 'command -v mktemp'], capture_output=True, text=True, check=True,
    ).stdout.strip()
    shim_script.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'call %s\\n' \"$*\" >>\"$MARKER\"\n"
        "case \"$*\" in *session.*) exit 1 ;; esac\n"
        f"exec {shlex.quote(real_mktemp)} \"$@\"\n"
    )
    shim_script.chmod(0o755)
    marker = tmp_path / "calls"
    base = tmp_path / "base"
    base.mkdir()
    fallback_root = tmp_path / "runtime-tmp"
    fallback_root.mkdir()
    script = "\n".join(
        line for line in scratch_one_liner().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    res = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script + '\nprintf "%s\\n" "$scratch"'],
        capture_output=True, text=True,
        env={**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "MARKER": str(marker),
             "scratch_base": str(base), "TMPDIR": str(fallback_root)},
    )
    assert res.returncode == 0, res.stderr
    chosen = Path(res.stdout.strip().splitlines()[-1])
    assert chosen.parent == fallback_root, f"the fallback did not use the standalone directory: {chosen}"
    calls = marker.read_text()
    assert "session." in calls and "call " in calls, calls


def test_the_snippet_fails_loudly_when_no_directory_can_be_created(tmp_path):
    """No base and a broken temp dir: the snippet must not print an empty path and exit 0."""
    script = "\n".join(
        line for line in scratch_one_liner().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    res = subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True,
        env={k: v for k, v in os.environ.items()
             if k not in {"scratch_base"} } | {"TMPDIR": str(tmp_path / "missing-tmp")},
    )
    assert res.returncode != 0, f"the snippet silently succeeded: {res.stdout!r}"
    assert res.stdout.strip() == "", res.stdout
    # The wording is pinned on purpose: it is what the documented snippet tells the caller.
    assert "could not create a scratch directory" in res.stderr, res.stderr


def test_the_rule_no_longer_forbids_only_fixed_paths_under_tmp():
    """AC1: the old contradictory sentence must not come back."""
    assert "Never write to a fixed path under `/tmp`" not in RUNTIMES.read_text()


def test_the_snippet_prints_the_directory_it_chose():
    """The rule says to run it once and pass the printed path, so the snippet prints it."""
    code = [line.strip() for line in scratch_one_liner().splitlines()
            if line.strip() and not line.strip().startswith("#")]
    assert code and code[-1] == 'printf \'%s\\n\' "$scratch"', code


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


def test_runtimes_rule_lets_a_handed_directory_serve_as_the_session_directory():
    """SKL-44 A6: an engineer handed only its subdirectory keeps its gate dossiers inside it."""
    assert "A subagent or agent handed a directory uses it as its own session's scratch directory instead of creating another." in rule_paragraph()


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


def subagents_section() -> str:
    text = TODO_TRACKING.read_text()
    assert "\n## Subagents\n" in text, "shared/todo-tracking.md lost its Subagents section"
    return text.split("\n## Subagents\n", 1)[1].split("\n## ", 1)[0]


def test_todo_tracking_routes_every_checklist_through_the_session_directory():
    text = TODO_TRACKING.read_text()
    section = subagents_section()
    assert "requiring a checklist file at `<scratch directory>/<agent-label>/<agent-label>-todo.md`." in section
    assert "`<scratch directory>` is the one scratch directory the session created for its lifetime" in section
    assert "`<agent-label>/` is the subdirectory you create inside it for that subagent." in section
    assert "`<scratch directory>/<session-label>-todo.md`" in text
    assert "never a fixed path under the base" in text
    assert "$CLAUDE_JOB_DIR" not in text


def test_todo_tracking_hands_each_delegated_role_only_its_own_subdirectory():
    """SKL-44 A6: a voter, engineer, or QA gets its own subdirectory, and its checklist lives there."""
    section = subagents_section()
    assert (
        "Hand a voter, engineer, or QA agent only its own subdirectory, never the session's scratch "
        "directory or another role's files (`references/runtimes.md`, Scratch files); "
        "its checklist lives in that subdirectory."
    ) in section
    assert "read that file from the subagent's subdirectory and mirror it into your own todo list" in section
    assert (
        "The brief gives the checklist's full path, and the subagent writes it exactly there, "
        "without adding `<agent-label>/` to the directory it was handed."
    ) in section, "a handed subagent could nest its checklist one level deeper than the coordinator reads"
    assert "`<scratch directory>/<agent-label>-todo.md`" not in section, "the checklist moved into the subagent's subdirectory"


# (skill, its delegation section, the delegated role's label). The coordinator creates the
# role's subdirectory, hands it only that, and reads the checklist from inside it (SKL-44 A6).
DELEGATED_ROLES = [
    ("story-to-done", "## 2. Senior engineer: implement to deployment review", "senior-engineer"),
    ("story-to-done", "## 3. QA agent: verify the deployed story", "qa-agent-round-<n>"),
    ("persona-staff-engineer", "## 3. Delegate implementation to a senior engineer", "senior-engineer"),
    ("persona-staff-devops", "## 3. Delegate execution to a platform/SRE engineer", "platform-engineer"),
]


def skill_section(skill: str, heading: str) -> str:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text()
    assert text.count(f"\n{heading}\n") == 1, f"{skill} lost its section {heading!r}"
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("skill,heading,label", DELEGATED_ROLES, ids=lambda v: str(v))
def test_delegation_briefs_hand_each_role_only_its_own_subdirectory(skill, heading, label):
    section = skill_section(skill, heading)
    brief_item = (
        f"- Its own subdirectory of the scratch directory, `<scratch>/{label}/`, which you create "
        "and hand it in place of the scratch directory itself, never another role's files."
    )
    assert brief_item in section.splitlines(), f"{skill} {heading} does not hand {label} only its own subdirectory"
    assert f"`<scratch>/{label}/{label}-todo.md`" in section, f"{skill} {heading} keeps the checklist outside the subdirectory"
    assert re.search(rf"checklist file at the full path you give it[^`]*`<scratch>/{re.escape(label)}/{re.escape(label)}-todo\.md`", section), (
        f"{skill} {heading} does not give {label} the checklist's full path"
    )
    assert f"`<scratch>/{label}-todo.md`" not in section, f"{skill} {heading} still names the session-level checklist"


@pytest.mark.parametrize("skill", ["story-to-done", "persona-staff-engineer", "persona-staff-devops"])
def test_coordinators_read_each_checklist_from_the_subagent_subdirectory(skill):
    section = skill_section(skill, "## 0. Track everything on a todo list")
    assert (
        "requires a checklist file in that subagent's own subdirectory of the scratch directory; "
        "read it from there and mirror it into your list whenever you check on the subagent."
    ) in section, f"{skill} step 0 does not read the checklist from the subagent's subdirectory"


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
    pattern = re.compile(
        r"must set[^.\n]*scratch_dir"
        r"|scratch_dir[^.\n]*must be set"
        r"|require[sd]?[^.\n]*scratch_dir"
        r"|scratch_dir[^.\n]*(?:is|are) required"
        r"|scratch_dir[^.\n]*must be (?:set|non-empty|configured)"
        r"|configure[^.\n]*scratch_dir"
        r"|set[^.\n]*workspace\.scratch_dir",
        re.IGNORECASE,
    )
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
        r"profile\.workspace\.scratch_dir[}>]?\s*/\s*[^\s`'\"]+"
        r"|\$CLAUDE_JOB_DIR/tmp/[A-Za-z0-9_.<>-]+"
        r"|<(?:scratch base|base)>/[^\s`'\"]+"
        r"|scratch_base[}>\"]?\s*/\s*[^\s`'\"]+"
        r"|/tmp/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.(?:md|txt|json|log)"
    )
    offenders = []
    for md in md_files():
        for n, line in enumerate(md.read_text().splitlines(), 1):
            # The capability map names the runtime's own base and stays; only that token is exempt.
            scanned = line.replace("`$CLAUDE_JOB_DIR/tmp`", "")
            for hit in fixed_under_base.findall(scanned):
                offenders.append(f"{md.relative_to(ROOT)}:{n}: {hit}")
    assert not offenders, "\n".join(offenders)


OWNED_TREES = (SHARED, ROOT / "skills", ROOT / "profile")


def md_files() -> list[Path]:
    """The repository's own Markdown: the top level plus the trees this story owns.

    Deliberately not a recursive walk of the whole checkout, so a dependency or build tree
    that happens to carry a README cannot fail the suite.
    """
    return sorted(
        [p for p in ROOT.glob("*.md")]
        + [p for tree in OWNED_TREES for p in tree.rglob("*.md")]
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


def test_snippet_falls_back_when_the_base_cannot_be_used(tmp_path):
    """An unusable base (here, a regular file) must degrade, never abort the session."""
    unusable = tmp_path / "scratch-base"
    unusable.write_text("not a directory\n")
    fallback_root = tmp_path / "runtime-tmp"
    fallback_root.mkdir()
    path = run_one_liner(scratch_one_liner(), {"scratch_base": str(unusable), "TMPDIR": str(fallback_root)})
    assert path.is_dir()
    assert path.parent == fallback_root, f"{path} did not fall back to the standalone directory"
    assert unusable.read_text() == "not a directory\n", "the unusable base was overwritten"
