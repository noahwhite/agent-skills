"""SKL-189: a profile seat may stay configured but be switched off.

AC1 covers the schema flag, AC3 the mandatory seats that may not be switched off, and AC2 the
launcher that must skip a disabled seat without launching a process or writing evidence of a run.
"""

import copy
import json
import os
import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
EXAMPLE = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
OPTIONAL_SEAT = ("review", "optional_reviewers", 0)

# Every seat a gate cannot run without (AC3). Disabling one is a profile that claims a gate it
# cannot run, so the schema refuses it instead of letting a phase report clean with no seat.
MANDATORY_SEATS = [
    ("review", "reviewer"),
    ("review", "adjudicator"),
    ("review", "pre_pr", "hunter"),
    ("review", "pre_pr", "arbiter"),
]
# Roles the refinement ceremony cannot run without either: it has no vote or tracker write without
# the product owner, and the facilitator is the orchestrating session itself.
MANDATORY_REFINEMENT_ROLES = [("refinement", "facilitator"), ("refinement", "product_owner")]


def seat(document, path):
    node = document
    for step in path:
        node = node[step]
    return node


def errors(document) -> list:
    return list(VALIDATOR.iter_errors(document))


def validation_message(document) -> str:
    return "\n".join(f"{list(e.path)}: {e.message}" for e in errors(document))


@pytest.mark.parametrize("value", [True, False])
def test_agent_accepts_an_enabled_boolean(value):
    """AC1: `enabled` is accepted on an agent entry, whichever boolean it carries."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, OPTIONAL_SEAT)["enabled"] = value
    assert not errors(document), validation_message(document)


def test_agent_enabled_is_optional_and_means_enabled_when_omitted():
    """AC1: an entry without the key passes, and the schema documents omission as enabled."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, OPTIONAL_SEAT).pop("enabled", None)
    assert not errors(document), validation_message(document)
    node = SCHEMA["$defs"]["agent"]["properties"]["enabled"]
    assert node["type"] == "boolean", node
    assert node["default"] is True, node
    assert "enabled" not in SCHEMA["$defs"]["agent"]["required"]


@pytest.mark.parametrize("value", ["false", "no", None, 0, 1])
def test_agent_rejects_a_non_boolean_enabled(value):
    """AC1: the negative controls, so a permissive schema cannot make the flag check green."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, OPTIONAL_SEAT)["enabled"] = value
    found = errors(document)
    assert found, f"the schema accepted enabled: {value!r}"
    assert any("enabled" in e.message or list(e.path)[-1:] == ["enabled"] for e in found), \
        validation_message(document)


def test_agent_still_rejects_an_unknown_key():
    """AC1: `additionalProperties: false` survives the new property, so the check is not permissive."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, OPTIONAL_SEAT)["enable"] = False
    found = errors(document)
    assert found, "the schema accepted an unknown key beside enabled"
    assert any("enable" in e.message for e in found), validation_message(document)


@pytest.mark.parametrize("path", MANDATORY_SEATS, ids=lambda p: ".".join(p))
def test_a_mandatory_seat_cannot_be_disabled(path):
    """AC3: the gate cannot run without these seats, so the schema refuses the profile outright."""
    document = copy.deepcopy(EXAMPLE)
    assert not errors(document), validation_message(document)
    seat(document, path)["enabled"] = False
    found = errors(document)
    assert found, f"the schema accepted enabled: false on the mandatory seat {'.'.join(path)}"
    assert any(list(e.path)[: len(path)] == list(path) for e in found), validation_message(document)


@pytest.mark.parametrize("path", MANDATORY_REFINEMENT_ROLES, ids=lambda p: ".".join(p))
def test_a_mandatory_refinement_role_cannot_be_disabled(path):
    """AC3: a role the ceremony cannot run without is refused rather than silently skipped."""
    document = copy.deepcopy(EXAMPLE)
    assert not errors(document), validation_message(document)
    seat(document, path)["enabled"] = False
    found = errors(document)
    assert found, f"the schema accepted enabled: false on {'.'.join(path)}"


def test_the_guard_covers_exactly_the_seats_that_may_not_be_disabled():
    """AC3: the guard is one rule, so a seat swapped to a plain agent entry fails this check."""
    guarded = set()

    def walk(node, path=()):
        """Every property path whose entry is guarded, through `properties` and array `items`."""
        if not isinstance(node, dict):
            return
        ref = node.get("$ref", "")
        if ref.endswith("required_agent") or ref.endswith("required_refinement_role"):
            guarded.add(".".join(path))
        for key, value in node.get("properties", {}).items():
            walk(value, (*path, key))
        if "items" in node:
            walk(node["items"], (*path, "[]"))

    walk(SCHEMA)
    expected = {".".join(path) for path in MANDATORY_SEATS + MANDATORY_REFINEMENT_ROLES}
    assert guarded == expected, (sorted(guarded), sorted(expected))


@pytest.mark.parametrize("path", MANDATORY_SEATS, ids=lambda p: ".".join(p))
def test_a_mandatory_seat_still_accepts_being_explicitly_enabled(path):
    """AC3: the guard refuses only the disabled value, so an explicit true stays valid."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, path)["enabled"] = True
    assert not errors(document), validation_message(document)


def test_a_list_seat_may_be_disabled():
    """AC3: the guard covers the mandatory slots only; the non-blocking seats are the point of it."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, ("review", "optional_reviewers", 0))["enabled"] = False
    seat(document, ("review", "shadow_adjudicators", 0))["enabled"] = False
    assert not errors(document), validation_message(document)


def test_the_pipeline_skill_names_a_disabled_mandatory_seat_as_a_blocked_gate():
    """AC3: the skill states the stop as well, so a reader knows a disabled seat is not a clean gate."""
    text = (ROOT / "skills" / "adversarial-review-pipeline" / "SKILL.md").read_text()
    assert "A mandatory seat with `enabled: false`" in text, (
        "the pipeline skill does not name a disabled mandatory seat as a blocked gate")


def test_refinement_reviewer_accepts_the_flag():
    """AC2: a refinement voter is a list seat too, so its role entry carries the same flag."""
    document = copy.deepcopy(EXAMPLE)
    seat(document, ("refinement", "reviewers", 0))["enabled"] = False
    assert not errors(document), validation_message(document)
    node = SCHEMA["$defs"]["refinement_role"]["properties"]["enabled"]
    assert node["type"] == "boolean" and node["default"] is True, node


# ---------------------------------------------------------------------------
# AC2: the launcher a skill calls for a list seat skips a disabled entry without launching.
# ---------------------------------------------------------------------------

LAUNCHER = ROOT / "skills" / "engineering-workflow" / "scripts" / "batched-diff-review.sh"


@pytest.fixture()
def reviewed_repo(tmp_path):
    """A repository with one changed file against a base commit, the launcher's minimum input."""
    repo = tmp_path / "reviewed"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True,
                       env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
                            "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(tmp_path)})

    git("init", "-q", "-b", "main")
    (repo / "a.txt").write_text("one\n")
    git("add", "a.txt")
    git("commit", "-q", "-m", "base")
    (repo / "a.txt").write_text("two\n")
    git("add", "a.txt")
    git("commit", "-q", "-m", "head")
    return repo


def launch(repo, *args, name="glm-seat"):
    """The launcher's own calls, with the spy standing in for the reviewer."""
    return subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(repo), "--base", "HEAD~1", "--name", name, *args],
        cwd=repo, capture_output=True, text=True,
    )


def spy_command(spy: Path) -> str:
    """A stand-in reviewer that records its own launch and answers every file with PASS."""
    return f"printf '%s\\n' \"${{1:-launched}}\" >> {spy} && printf '### FILE: a.txt\\n### FILE VERDICT: PASS\\n'"


def test_a_disabled_seat_launches_nothing_and_writes_no_report(tmp_path, reviewed_repo):
    """AC2: zero launches, no process, no report file - and one disabled evidence line."""
    spy = tmp_path / "spy.log"
    result = launch(reviewed_repo, "--enabled", "false", "--agent-cmd", spy_command(spy))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "glm-seat: disabled", result.stdout
    assert not spy.exists(), "a disabled seat launched a process"
    report_dir = reviewed_repo / ".git" / "batched-review" / "glm-seat"
    assert not report_dir.exists(), f"a disabled seat wrote evidence: {sorted(report_dir.rglob('*'))}"


def test_a_disabled_seat_is_never_recorded_as_passed_skipped_or_clean(tmp_path, reviewed_repo):
    """AC2: the only line a disabled seat produces is the disabled one, so no verdict can be read."""
    spy = tmp_path / "spy.log"
    result = launch(reviewed_repo, "--enabled", "false", "--agent-cmd", spy_command(spy),
                    name="seat")
    text = (result.stdout + result.stderr).lower()
    for word in ("verdict", "pass", "fail", "incomplete", "skipped"):
        assert word not in text, f"the disabled seat recorded `{word}`: {result.stdout}{result.stderr}"


def test_a_disabled_seat_needs_no_launcher_and_no_base(tmp_path, reviewed_repo):
    """AC2: a switched-off seat costs nothing, so it does not require a diff or a command either."""
    spy = tmp_path / "spy.log"
    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(reviewed_repo), "--name", "glm-seat",
         "--enabled", "false"],
        cwd=reviewed_repo, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "glm-seat: disabled", result.stdout
    assert not spy.exists()


def test_an_entry_without_the_flag_launches(tmp_path, reviewed_repo):
    """AC1/AC2: omission means enabled, so an existing profile keeps the review it configures."""
    spy = tmp_path / "spy.log"
    result = launch(reviewed_repo, "--agent-cmd", spy_command(spy))
    assert result.returncode == 0, result.stderr
    assert spy.exists(), "an entry without `enabled` did not launch"
    assert "### VERDICT\nPASS" in result.stdout, result.stdout


def test_an_explicitly_enabled_entry_launches(tmp_path, reviewed_repo):
    """AC2: the re-enable path is the same one-word edit, and it launches again."""
    spy = tmp_path / "spy.log"
    result = launch(reviewed_repo, "--enabled", "true", "--agent-cmd", spy_command(spy))
    assert result.returncode == 0, result.stderr
    assert spy.exists(), "an entry with `enabled: true` did not launch"


def test_disabling_a_seat_removes_the_report_an_earlier_run_left(tmp_path, reviewed_repo):
    """AC2: a switched-off seat leaves no report behind, not even one from an earlier head."""
    spy = tmp_path / "spy.log"
    first = launch(reviewed_repo, "--agent-cmd", spy_command(spy))
    assert first.returncode == 0, first.stderr
    report_dir = reviewed_repo / ".git" / "batched-review" / "glm-seat"
    assert (report_dir / "report.md").is_file(), "the enabled run wrote no report to remove"
    second = launch(reviewed_repo, "--enabled", "false", "--agent-cmd", spy_command(spy))
    assert second.returncode == 0, second.stderr
    assert second.stdout.strip() == "glm-seat: disabled", second.stdout
    assert not report_dir.exists(), f"a stale report survived the disabled run: {sorted(report_dir.rglob('*'))}"


def test_the_cleanup_removes_the_named_repositorys_report_not_the_callers(tmp_path, reviewed_repo):
    """AC2: `--repo` names the repository whose evidence is cleaned, wherever the caller stands.

    The launcher is run from a second repository, so a repo-relative report path would delete the
    caller's evidence and leave the target's stale report in place.
    """
    spy = tmp_path / "spy.log"
    first = launch(reviewed_repo, "--agent-cmd", spy_command(spy))
    assert first.returncode == 0, first.stderr
    target = reviewed_repo / ".git" / "batched-review" / "glm-seat"
    assert (target / "report.md").is_file()

    caller = tmp_path / "caller"
    caller.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=caller, check=True,
                   capture_output=True, env={**os.environ, "HOME": str(tmp_path)})
    own = caller / ".git" / "batched-review" / "glm-seat"
    own.mkdir(parents=True)
    (own / "report.md").write_text("# Overall\n\n### VERDICT\nPASS\n")

    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(reviewed_repo), "--name", "glm-seat",
         "--enabled", "false", "--agent-cmd", spy_command(spy)],
        cwd=caller, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "glm-seat: disabled", result.stdout
    assert not target.exists(), "the target repository's stale report survived"
    assert (own / "report.md").is_file(), "the caller's evidence was deleted"


def test_an_inherited_git_dir_cannot_redirect_the_cleanup(tmp_path, reviewed_repo):
    """AC2: `GIT_DIR` in the environment outranks `-C`, so the launcher must ignore it.

    A wrapper that exports `GIT_DIR` (a hook, a CI step) would otherwise point every path at the
    caller's repository and delete its evidence instead of the named one's.
    """
    spy = tmp_path / "spy.log"
    assert launch(reviewed_repo, "--agent-cmd", spy_command(spy)).returncode == 0
    target = reviewed_repo / ".git" / "batched-review" / "glm-seat"
    assert (target / "report.md").is_file()

    caller = tmp_path / "caller"
    caller.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=caller, check=True,
                   capture_output=True, env={**os.environ, "HOME": str(tmp_path)})
    own = caller / ".git" / "batched-review" / "glm-seat"
    own.mkdir(parents=True)
    (own / "report.md").write_text("# Overall\n\n### VERDICT\nPASS\n")

    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(reviewed_repo), "--name", "glm-seat",
         "--enabled", "false"],
        cwd=caller, capture_output=True, text=True,
        env={**os.environ, "GIT_DIR": str(caller / ".git")},
    )
    assert result.returncode == 0, result.stderr
    assert not target.exists(), "the named repository's stale report survived an inherited GIT_DIR"
    assert (own / "report.md").is_file(), "an inherited GIT_DIR made the launcher delete the caller's report"


def test_an_inherited_git_dir_cannot_redirect_the_report(tmp_path, reviewed_repo):
    """The enabled path writes its report into the repository `--repo` names, not the caller's."""
    spy = tmp_path / "spy.log"
    caller = tmp_path / "caller"
    caller.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=caller, check=True,
                   capture_output=True, env={**os.environ, "HOME": str(tmp_path)})
    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(reviewed_repo), "--base", "HEAD~1",
         "--name", "glm-seat", "--agent-cmd", spy_command(spy)],
        cwd=caller, capture_output=True, text=True,
        env={**os.environ, "GIT_DIR": str(caller / ".git")},
    )
    assert result.returncode == 0, result.stderr
    assert (reviewed_repo / ".git" / "batched-review" / "glm-seat" / "report.md").is_file()
    assert not (caller / ".git" / "batched-review").exists(), "the report landed in the caller's repository"


def test_a_discovery_ceiling_cannot_skip_the_cleanup(tmp_path, reviewed_repo):
    """AC2: a subdirectory target is still resolved, so the stale evidence is still removed.

    `GIT_CEILING_DIRECTORIES` stops Git walking up from a subdirectory, which would silently skip the
    cleanup and leave a report behind a switched-off seat.
    """
    spy = tmp_path / "spy.log"
    assert launch(reviewed_repo, "--agent-cmd", spy_command(spy)).returncode == 0
    target = reviewed_repo / ".git" / "batched-review" / "glm-seat"
    assert (target / "report.md").is_file()
    subdir = reviewed_repo / "a-subdirectory"
    subdir.mkdir()

    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(subdir), "--name", "glm-seat", "--enabled", "false"],
        cwd=subdir, capture_output=True, text=True,
        env={**os.environ, "GIT_CEILING_DIRECTORIES": str(reviewed_repo)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "glm-seat: disabled", result.stdout
    assert not target.exists(), "a discovery ceiling left the stale report in place"


def test_a_symlinked_report_directory_is_never_removed_through(tmp_path, reviewed_repo):
    """AC2: removing a stale report must never delete content the repository does not own.

    A repository whose `.git/batched-review` is a symlink elsewhere would otherwise have the
    link target's `<name>/` directory deleted by a switched-off seat.
    """
    spy = tmp_path / "spy.log"
    external = tmp_path / "external"
    (external / "glm-seat").mkdir(parents=True)
    (external / "glm-seat" / "keep.txt").write_text("not this repository's file\n")
    (external / "keep.txt").write_text("nor this one\n")
    report_dir = reviewed_repo / ".git" / "batched-review"
    report_dir.symlink_to(external)

    result = launch(reviewed_repo, "--enabled", "false", "--agent-cmd", spy_command(spy))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "glm-seat: disabled", result.stdout
    assert (external / "glm-seat" / "keep.txt").is_file(), (
        "the cleanup deleted content through a symlinked report directory")
    assert (external / "keep.txt").is_file()


def test_a_dot_name_is_refused(tmp_path, reviewed_repo):
    """A name that would make the cleanup remove a whole directory is refused."""
    for name in (".", ".."):
        result = launch(reviewed_repo, "--enabled", "false", name=name)
        assert result.returncode == 2, (name, result.returncode, result.stdout)
        assert "--name" in result.stderr, result.stderr


def test_the_environment_can_enable_a_seat_explicitly(tmp_path, reviewed_repo):
    """The env equivalent carries the same two literals as the flag."""
    spy = tmp_path / "spy.log"
    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(reviewed_repo), "--base", "HEAD~1",
         "--name", "glm-seat", "--agent-cmd", spy_command(spy)],
        cwd=reviewed_repo, capture_output=True, text=True,
        env={**os.environ, "REVIEW_ENABLED": "true"},
    )
    assert result.returncode == 0, result.stderr
    assert spy.exists(), "an explicitly enabled seat through the environment did not launch"


def test_an_empty_environment_value_is_refused_rather_than_read_as_enabled(tmp_path, reviewed_repo):
    """A value rendered from a profile as empty must fail closed, not launch the seat."""
    spy = tmp_path / "spy.log"
    result = subprocess.run(
        ["bash", str(LAUNCHER), "--repo", str(reviewed_repo), "--base", "HEAD~1",
         "--name", "glm-seat", "--agent-cmd", spy_command(spy)],
        cwd=reviewed_repo, capture_output=True, text=True,
        env={**os.environ, "REVIEW_ENABLED": ""},
    )
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert "--enabled" in result.stderr, result.stderr
    assert not spy.exists(), "an empty value launched the seat"


@pytest.mark.parametrize("value", ["maybe", "0", "", "FALSE "])
def test_an_unrecognised_enabled_value_is_refused(tmp_path, reviewed_repo, value):
    """A value that is neither true nor false stops the run rather than guessing the seat's state."""
    spy = tmp_path / "spy.log"
    result = launch(reviewed_repo, "--enabled", value, "--agent-cmd", spy_command(spy))
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert "--enabled" in result.stderr, result.stderr
    assert not spy.exists(), "an unrecognised value still launched"


MIXED_SEATS = {
    "review": {
        "optional_reviewers": [
            {"name": "underfunded-seat", "runtime": "command", "model": "example/family-b",
             "enabled": False},
            {"name": "funded-seat", "runtime": "command", "model": "example/family-c"},
        ]
    }
}


def run_step(document: dict, repo: Path, spy: Path) -> dict[str, subprocess.CompletedProcess]:
    """Step 6 of engineering-workflow: one launcher call per entry, with the entry's own value."""
    results = {}
    for entry in document["review"]["optional_reviewers"]:
        enabled = str(entry.get("enabled", True)).lower()
        results[entry["name"]] = launch(
            repo, "--enabled", enabled, "--agent-cmd", spy_command(spy), name=entry["name"])
    return results


def test_one_disabled_seat_leaves_the_rest_of_the_step_running(tmp_path, reviewed_repo):
    """AC5: on a fixture profile, the step skips one seat and still runs the other, then re-enables."""
    spy = tmp_path / "spy.log"
    document = copy.deepcopy(MIXED_SEATS)

    first = run_step(document, reviewed_repo, spy)
    assert first["underfunded-seat"].returncode == 0, first["underfunded-seat"].stderr
    assert first["underfunded-seat"].stdout.strip() == "underfunded-seat: disabled", \
        first["underfunded-seat"].stdout
    assert first["funded-seat"].returncode == 0, first["funded-seat"].stderr
    assert spy.read_text().splitlines() == ["launched"], "the disabled seat broke the iteration"
    review_dir = reviewed_repo / ".git" / "batched-review"
    assert not (review_dir / "underfunded-seat").exists()
    assert (review_dir / "funded-seat" / "report.md").is_file()

    # The re-enable path is the same one-word edit, exercised in the same run.
    document["review"]["optional_reviewers"][0]["enabled"] = True
    second = run_step(document, reviewed_repo, spy)
    assert second["underfunded-seat"].returncode == 0, second["underfunded-seat"].stderr
    assert "disabled" not in second["underfunded-seat"].stdout
    assert len(spy.read_text().splitlines()) == 3, "both seats should have launched after re-enable"
    assert (review_dir / "underfunded-seat" / "report.md").is_file()


# ---------------------------------------------------------------------------
# AC2: the skills that iterate a list seat say the same thing the launcher does.
# ---------------------------------------------------------------------------

WORKFLOW = ROOT / "skills" / "engineering-workflow" / "SKILL.md"
CODE_REVIEW = ROOT / "shared" / "code-review.md"
REFINEMENT = ROOT / "skills" / "story-refinement" / "SKILL.md"
DISABLED_EVIDENCE = '"<name>: disabled"'
NEVER_A_RESULT = "never recorded as passed, skipped for failure, or clean"


def section(text: str, heading: str) -> str:
    """The body of one Markdown heading, up to the next heading of the same or a higher level."""
    lines = text.splitlines()
    start = next((n for n, line in enumerate(lines)
                  if line.strip().lower() == heading.lower()), None)
    assert start is not None, f"no `{heading}` heading"
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    body = []
    for line in lines[start + 1:]:
        if line.startswith("#") and len(line) - len(line.lstrip("#")) <= level:
            break
        body.append(line)
    return "\n".join(body)


def test_the_optional_reviewer_step_skips_a_disabled_seat():
    """AC2: step 6 of engineering-workflow is the skill that iterates the optional reviewers."""
    body = section(WORKFLOW.read_text(), "## 6. Optional reviewers (never blocking)")
    assert "`enabled`" in body and "`false`" in body, body
    assert DISABLED_EVIDENCE in body, body
    assert NEVER_A_RESULT in body, body
    assert "--enabled" in body, "step 6 does not hand the entry's value to the launcher"
    assert "Omission means enabled" in body, body


def test_the_shadow_adjudicator_step_skips_a_disabled_seat():
    """AC2: shadow seats are spawned as subagents, so the rule has to be in the prose too."""
    body = section(WORKFLOW.read_text(), "## 7. Review of record (required)")
    assert "`enabled`" in body and DISABLED_EVIDENCE in body, body


def test_the_capability_file_covers_both_list_seats():
    """AC2: code-review.md is vendored into every skill that touches these seats."""
    text = CODE_REVIEW.read_text()
    optional = section(text, "### Optional reviewers")
    shadows = section(text, "### Shadow adjudicators")
    for name, body in (("Optional reviewers", optional), ("Shadow adjudicators", shadows)):
        assert "`enabled`" in body, name
        assert DISABLED_EVIDENCE in body, name
        assert "launch" in body.lower(), name
    assert NEVER_A_RESULT in optional, optional
    assert "never" in shadows.lower() and "disabled" in shadows.lower(), shadows


def test_the_refinement_voters_count_the_enabled_entries():
    """AC2: a disabled voter is skipped, and the two-voter rule is evaluated over the enabled set."""
    body = section(REFINEMENT.read_text(), "## Roles")
    assert DISABLED_EVIDENCE in body, body
    assert "fewer than two engineer voters are enabled" in body, (
        "the enabled-voter count rule is missing from the roles")
    assert "with a named error" in body, (
        "a disabled facilitator or product owner needs its own stop")
    assert "blocks the ceremony until that seat is re-enabled" in body, (
        "the two-entry voter list makes a disabled voter block the ceremony; the prose has to say so")


@pytest.mark.parametrize("skill", ["persona-staff-engineer", "persona-staff-devops"])
def test_the_personas_skip_a_disabled_shadow(skill):
    """AC2: the two personas that run every configured shadow carry the same exception."""
    text = (ROOT / "skills" / skill / "SKILL.md").read_text()
    assert DISABLED_EVIDENCE in text, text
    assert "An entry whose `enabled` is `false`" in text, text


def test_the_profile_documentation_states_what_a_disabled_entry_costs():
    """AC4: a disabled entry is still read, and the toggle is priced against the alternatives."""
    body = section((ROOT / "README.md").read_text(), "### Switching a seat off")
    assert "read as text" in body, body
    for alternative in ("tokens", "deleting the entry", "commenting it out"):
        assert alternative in body, alternative
    assert "one-word edit" in body, body
    assert "costs more than deleting the entry" in body, body
    assert "about the same as commenting the entry out" in body, body
    # Commenting out is legal YAML, so the honest difference is the unset seat, not a parse error.
    assert "invalid to parse" not in body, body
    assert "unset rather than disabled" in body, body
