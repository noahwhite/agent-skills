"""The gate-integrity check that the base branch runs over a pull request's workflow files."""

import copy
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/gate_integrity.py"
GATE_BASE = ROOT / ".github/workflows/gate-base.yml"

CI = {
    "name": "ci",
    "on": {"pull_request": None, "push": {"branches": ["main"]}},
    "permissions": {"contents": "read"},
    "jobs": {
        "checks": {
            "runs-on": "ubuntu-24.04",
            "timeout-minutes": 15,
            "steps": [
                {"uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"},
                {"uses": "astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7",
                 "with": {"enable-cache": False}},
                {"name": "Repository tests", "run": "uv run --locked pytest -q"},
                {"name": "Validate skills", "run": "skills-ref validate skills/a/"},
            ],
        },
    },
}

GATE = {
    "name": "gate-base",
    "on": {"pull_request_target": None},
    "permissions": {"contents": "read", "checks": "write"},
    "jobs": {"gate": {"runs-on": "ubuntu-24.04",
                      "steps": [{"name": "Judge", "run": "python3 base/scripts/gate_integrity.py"}]}},
}

SCRIPT_TEXT = "print('judge')\n"


def write_tree(root, workflows, script=SCRIPT_TEXT):
    directory = root / ".github/workflows"
    directory.mkdir(parents=True)
    for name, workflow in workflows.items():
        (directory / name).write_text(yaml.safe_dump(workflow, sort_keys=False))
    if script is not None:
        (root / "scripts").mkdir()
        (root / "scripts/gate_integrity.py").write_text(script)
    return root


def judge(tmp_path, head_workflows, head_script=SCRIPT_TEXT):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    head = write_tree(tmp_path / "head", head_workflows, head_script)
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--base", str(base / ".github/workflows"), "--head", str(head / ".github/workflows"),
         "--base-script", str(base / "scripts/gate_integrity.py"),
         "--head-script", str(head / "scripts/gate_integrity.py")],
        capture_output=True, text=True, timeout=30,
    )


def head_with(change):
    ci = copy.deepcopy(CI)
    change(ci)
    return {"ci.yml": ci, "gate-base.yml": copy.deepcopy(GATE)}


def steps(ci):
    return ci["jobs"]["checks"]["steps"]


def test_unchanged_workflows_pass(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: None))
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_renamed_workflow_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci.update(name="ci renamed")))
    assert result.returncode == 0, result.stdout + result.stderr


ADDED_STEPS = {
    "named": {"name": "Lint", "run": "uv run ruff check"},
    "unnamed": {"run": "echo hi"},
    "same name as a base step": {"name": "Repository tests", "run": "echo more"},
}
BASE_STEP_COPY = {"name": "Repository tests", "run": "uv run --locked pytest -q"}


@pytest.mark.parametrize("step", [*ADDED_STEPS.values(), BASE_STEP_COPY], ids=[*ADDED_STEPS, "copy of a base step"])
def test_a_step_added_after_the_base_steps_passes(tmp_path, step):
    result = judge(tmp_path, head_with(lambda ci: steps(ci).append(step)))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("where", [0, 1, 2, 3], ids=["first", "between-unnamed", "after-unnamed", "before-last"])
@pytest.mark.parametrize("step", ADDED_STEPS.values(), ids=ADDED_STEPS.keys())
def test_a_step_added_before_a_base_step_fails(tmp_path, step, where):
    """A step that runs before a base step can change its execution, for example through $GITHUB_ENV."""
    result = judge(tmp_path, head_with(lambda ci: steps(ci).insert(where, step)))
    assert result.returncode != 0, result.stdout
    assert "ci.yml job 'checks'" in result.stdout


def test_a_base_step_copied_above_an_earlier_one_fails(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: steps(ci).insert(2, copy.deepcopy(steps(ci)[3]))))
    assert result.returncode != 0, result.stdout


@pytest.mark.parametrize("change", [lambda ci: steps(ci)[3].update({"if": 1}),
                                    lambda ci: ci["jobs"]["checks"].update({"timeout-minutes": 15.0}),
                                    lambda ci: steps(ci)[1]["with"].update({"enable-cache": 0})],
                         ids=["if-true-to-1", "timeout-int-to-float", "false-to-0"])
def test_a_value_that_changes_type_fails(tmp_path, change):
    ci = copy.deepcopy(CI)
    steps(ci)[3]["if"] = True
    base = write_tree(tmp_path / "base", {"ci.yml": ci, "gate-base.yml": GATE})
    head_ci = copy.deepcopy(ci)
    change(head_ci)
    head = write_tree(tmp_path / "head", {"ci.yml": head_ci, "gate-base.yml": GATE})
    result = run_dirs(base / ".github/workflows", head / ".github/workflows")
    assert result.returncode != 0, result.stdout


def test_a_duplicate_key_fails(tmp_path):
    for side, extra in (("base", ""), ("head", "  pull_request_target:\n")):
        directory = tmp_path / side
        directory.mkdir()
        (directory / "ci.yml").write_text("on:\n  pull_request:\n" + extra +
                                          ("on: [pull_request]\n" if extra else "") +
                                          "jobs:\n  checks:\n    steps:\n      - run: 'true'\n")
    result = run_dirs(tmp_path / "base", tmp_path / "head")
    assert result.returncode != 0, result.stdout
    assert "duplicate" in result.stdout


@pytest.mark.parametrize("workflows_change", [
    lambda w: w.update({"lint.yml": {"on": {"pull_request": None},
                                     "jobs": {"lint": {"name": "${{ 'gate-base' }}", "steps": [{"run": "true"}]}}}}),
    lambda w: w["ci.yml"]["jobs"]["checks"].update(name="${{ 'gate-base' }}"),
    lambda w: w.update({"lint.yml": {"on": {"pull_request": None},
                                     "jobs": {"checks": {"steps": [{"run": "true"}]}}}}),
    lambda w: w["ci.yml"]["jobs"].update(lint={"name": "checks", "steps": [{"run": "true"}]}),
], ids=["expression-name-in-added-workflow", "base-job-renamed-to-expression",
        "base-check-name-in-added-workflow", "base-check-name-on-added-job"])
def test_a_head_job_that_could_report_a_required_check_name_fails(tmp_path, workflows_change):
    workflows = head_with(lambda ci: None)
    workflows_change(workflows)
    result = judge(tmp_path, workflows)
    assert result.returncode != 0, result.stdout


def test_an_unparseable_added_workflow_fails(tmp_path):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    head = write_tree(tmp_path / "head", {"ci.yml": CI, "gate-base.yml": GATE})
    (head / ".github/workflows/lint.yml").write_text("jobs:\n  gate-base:\n    with: !custom foo\n")
    result = run_dirs(base / ".github/workflows", head / ".github/workflows")
    assert result.returncode != 0, result.stdout
    assert "lint.yml" in result.stdout


def test_a_head_script_without_a_base_script_is_a_usage_error(tmp_path):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    result = run_dirs(base / ".github/workflows", base / ".github/workflows",
                      "--head-script", base / "scripts/gate_integrity.py")
    assert result.returncode == 2, result.stdout + result.stderr


def test_a_job_added_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci["jobs"].update(
        lint={"runs-on": "ubuntu-24.04", "steps": [{"run": "true"}]})))
    assert result.returncode == 0, result.stdout + result.stderr


def test_an_added_job_that_needs_a_base_job_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci["jobs"].update(
        lint={"needs": ["checks"], "runs-on": "ubuntu-24.04", "steps": [{"run": "true"}]})))
    assert result.returncode == 0, result.stdout + result.stderr


def test_an_added_reusable_workflow_job_in_a_base_workflow_fails(tmp_path):
    # GitHub rejects the caller when the called file is missing or invalid; the gate does not load it.
    result = judge(tmp_path, head_with(lambda ci: ci["jobs"].update(
        reuse={"uses": "./.github/workflows/reusable.yml", "with": {"x": 1}})))
    assert result.returncode != 0, result.stdout
    assert "reusable workflow" in result.stdout


def test_an_appended_run_step_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: steps(ci).append({"name": "More", "run": "true"})))
    assert result.returncode == 0, result.stdout


# A display name GitHub rejects stops the whole file, gate-base.yml included.
NON_STRING_NAMES = {
    "workflow": lambda ci: ci.update(name={"display": "CI"}),
    "base step": lambda ci: steps(ci)[0].update(name={"display": "x"}),
    "added step": lambda ci: steps(ci).append({"name": ["x"], "run": "true"}),
    "added job": lambda ci: ci["jobs"].update(
        lint={"name": {"x": 1}, "runs-on": "ubuntu-24.04", "steps": [{"run": "true"}]}),
}


@pytest.mark.parametrize("change", NON_STRING_NAMES.values(), ids=NON_STRING_NAMES)
def test_a_name_that_is_not_a_string_fails(tmp_path, change):
    result = judge(tmp_path, head_with(change))
    assert result.returncode != 0, result.stdout


def test_a_gate_workflow_step_name_that_is_not_a_string_fails(tmp_path):
    gate = copy.deepcopy(GATE)
    gate["jobs"]["gate"]["steps"][0]["name"] = {"display": "Judge"}
    result = judge(tmp_path, {"ci.yml": copy.deepcopy(CI), "gate-base.yml": gate})
    assert result.returncode != 0, result.stdout
    assert "not a string" in result.stdout


@pytest.mark.parametrize("name", ["${{ }}", "Judge ${{ github.sha }}"])
def test_a_step_renamed_to_an_expression_fails(tmp_path, name):
    # GitHub rejects a malformed expression, which would stop the whole file.
    gate = copy.deepcopy(GATE)
    gate["jobs"]["gate"]["steps"][0]["name"] = name
    result = judge(tmp_path, {"ci.yml": copy.deepcopy(CI), "gate-base.yml": gate})
    assert result.returncode != 0, result.stdout
    assert "expression" in result.stdout


# GitHub rejects a whole workflow file with an invalid job or step, so an addition like
# these stops every base job in that file from running.
INVALID_ADDITIONS = {
    "job without runs-on or uses": lambda ci: ci["jobs"].update(lint={"steps": [{"run": "true"}]}),
    "job with runs-on and uses": lambda ci: ci["jobs"].update(
        lint={"runs-on": "ubuntu-24.04", "uses": "./x.yml", "steps": [{"run": "true"}]}),
    "reusable call with steps": lambda ci: ci["jobs"].update(lint={"uses": "./x.yml", "steps": [{"run": "true"}]}),
    "job without steps": lambda ci: ci["jobs"].update(lint={"runs-on": "ubuntu-24.04"}),
    "job with an unknown key": lambda ci: ci["jobs"].update(
        lint={"runs-on": "ubuntu-24.04", "stepz": [], "steps": [{"run": "true"}]}),
    "job that is not a mapping": lambda ci: ci["jobs"].update(lint="ubuntu-24.04"),
    "appended step without run or uses": lambda ci: steps(ci).append({"name": "Nothing"}),
    "appended step with run and uses": lambda ci: steps(ci).append({"run": "true", "uses": "x/y@v1"}),
    "appended step with an unknown key": lambda ci: steps(ci).append({"run": "true", "runs": "x"}),
    "appended step that is not a mapping": lambda ci: steps(ci).append("echo hi"),
    # An action's pre hook runs at job start, before every base step.
    "appended uses step": lambda ci: steps(ci).append({"uses": "o/a@0123456789abcdef0123456789abcdef01234567"}),
}


@pytest.mark.parametrize("change", INVALID_ADDITIONS.values(), ids=INVALID_ADDITIONS)
def test_an_addition_github_rejects_fails(tmp_path, change):
    result = judge(tmp_path, head_with(change))
    assert result.returncode != 0, result.stdout
    assert "added" in result.stdout


# GitHub rejects a whole workflow file whose `needs` names a missing job or forms a cycle,
# so an added job like this stops every base job in that file from running.
BROKEN_NEEDS = {
    "missing job": {"lint": {"needs": "nonexistent", "steps": [{"run": "true"}]}},
    "cycle": {"a": {"needs": ["b"], "steps": [{"run": "true"}]},
              "b": {"needs": "a", "steps": [{"run": "true"}]}},
    "self": {"a": {"needs": "a", "steps": [{"run": "true"}]}},
    "not a job id": {"a": {"needs": [{"job": "checks"}], "steps": [{"run": "true"}]}},
}


@pytest.mark.parametrize("jobs", BROKEN_NEEDS.values(), ids=BROKEN_NEEDS)
def test_an_added_job_with_needs_github_rejects_fails(tmp_path, jobs):
    result = judge(tmp_path, head_with(lambda ci: ci["jobs"].update(copy.deepcopy(jobs))))
    assert result.returncode != 0, result.stdout
    assert "needs" in result.stdout


def test_a_workflow_added_passes(tmp_path):
    workflows = head_with(lambda ci: None)
    workflows["extra.yml"] = {"on": {"push": None}, "permissions": {"contents": "read"},
                              "jobs": {"x": {"runs-on": "ubuntu-24.04", "steps": [{"run": "true"}]}}}
    result = judge(tmp_path, workflows)
    assert result.returncode == 0, result.stdout + result.stderr


# A job that can write check runs could post a gate-base check run of its own, or overwrite
# the gate's, on the PR head.
CHECK_WRITERS = {
    "workflow checks write": ({"checks": "write"}, None),
    "workflow write-all": ("write-all", None),
    "job checks write": ({"contents": "read"}, {"checks": "write"}),
    "job write-all": ({"contents": "read"}, "write-all"),
    "no permissions anywhere": (None, None),
    "unreadable permissions": ("${{ inputs.p }}", None),
}


@pytest.mark.parametrize("workflow_permissions, job_permissions", CHECK_WRITERS.values(), ids=CHECK_WRITERS)
def test_an_added_job_that_could_write_check_runs_fails(tmp_path, workflow_permissions, job_permissions):
    job = {"runs-on": "ubuntu-24.04", "steps": [{"run": "gh api repos/o/r/check-runs -f name=gate-base"}]}
    if job_permissions is not None:
        job["permissions"] = job_permissions
    added = {"on": {"pull_request": None}, "jobs": {"post": job}}
    if workflow_permissions is not None:
        added["permissions"] = workflow_permissions
    workflows = head_with(lambda ci: None)
    workflows["post.yaml"] = added
    result = judge(tmp_path, workflows)
    assert result.returncode != 0, result.stdout
    assert "post.yaml job 'post'" in result.stdout


def test_an_added_job_in_a_base_workflow_with_checks_write_fails(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci["jobs"].update(
        post={"runs-on": "ubuntu-24.04", "permissions": {"checks": "write"}, "steps": [{"run": "true"}]})))
    assert result.returncode != 0, result.stdout
    assert "check runs" in result.stdout


def test_a_renamed_step_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: steps(ci)[3].update(name="Validate the skills")))
    assert result.returncode == 0, result.stdout + result.stderr


def test_an_unnamed_step_given_a_name_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: steps(ci)[0].update(name="Checkout")))
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_renamed_job_passes(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci["jobs"]["checks"].update(name="Checks")))
    assert result.returncode == 0, result.stdout + result.stderr


def run_dirs(base, head, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base), "--head", str(head), *map(str, extra)],
        capture_output=True, text=True, timeout=30)


def test_a_quoted_on_key_matches_a_bare_on_key(tmp_path):
    for side, key in (("base", "on"), ("head", "'on'")):
        directory = tmp_path / side
        directory.mkdir()
        (directory / "ci.yml").write_text(f"{key}:\n  pull_request:\n  push:\n    branches: [main]\n"
                                          "jobs:\n  checks:\n    steps:\n      - run: 'true'\n")
    result = run_dirs(tmp_path / "base", tmp_path / "head")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("key", ["true", "True", "yes", "'true'"])
def test_a_trigger_key_github_does_not_read_as_on_fails(tmp_path, key):
    # GitHub reads workflow YAML with the YAML 1.2 core schema: only the key `on` (bare or
    # quoted) declares triggers, so a head that respells it loses every trigger.
    for side, on in (("base", "on"), ("head", key)):
        directory = tmp_path / side
        directory.mkdir()
        (directory / "ci.yml").write_text(f"{on}:\n  pull_request:\n"
                                          "jobs:\n  checks:\n    steps:\n      - run: 'true'\n")
    result = run_dirs(tmp_path / "base", tmp_path / "head")
    assert result.returncode != 0, result.stdout
    assert "trigger" in result.stdout


@pytest.mark.parametrize("head_on", ["{pull_request: {}}", "[pull_request]", "pull_request"])
def test_equivalent_trigger_spellings_match(tmp_path, head_on):
    for side, on in (("base", "{pull_request: null}"), ("head", head_on)):
        directory = tmp_path / side
        directory.mkdir()
        (directory / "ci.yml").write_text(f"on: {on}\njobs:\n  checks:\n    steps:\n      - run: 'true'\n")
    result = run_dirs(tmp_path / "base", tmp_path / "head")
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_trigger_types_filter_added_fails(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci["on"].update(pull_request={"types": ["opened"]})))
    assert result.returncode != 0
    assert "trigger" in result.stdout


def drop_named(name):
    return lambda ci: steps(ci).remove(next(s for s in steps(ci) if s.get("name") == name))


VIOLATIONS = {
    "step removed": (drop_named("Validate skills"), "Validate skills"),
    "unnamed step removed": (lambda ci: steps(ci).pop(0), "step 1"),
    "step text changed": (lambda ci: steps(ci)[2].update(run="true"), "Repository tests"),
    "if false on a base step": (lambda ci: steps(ci)[3].update({"if": False}), "Validate skills"),
    "continue-on-error on a base step": (
        lambda ci: steps(ci)[2].update({"continue-on-error": True}), "Repository tests"),
    "with changed on an unnamed step": (
        lambda ci: steps(ci)[1]["with"].update({"enable-cache": True}), "step 2"),
    "step renamed and changed": (
        lambda ci: steps(ci)[2].update(name="Tests", run="true"), "Repository tests"),
    "env added to a base step": (
        lambda ci: steps(ci)[2].update(env={"PYTEST_ADDOPTS": "-k nothing"}), "Repository tests"),
    "base steps reordered": (
        lambda ci: steps(ci).insert(2, steps(ci).pop(3)), "order"),
    "unnamed base steps reordered": (
        lambda ci: steps(ci).insert(0, steps(ci).pop(1)), "order"),
    "trigger narrowed": (lambda ci: ci["on"].pop("push"), "trigger"),
    "push branches narrowed": (
        lambda ci: ci["on"]["push"].update(branches=["release"]), "trigger"),
    "job removed": (lambda ci: ci["jobs"].pop("checks"), "checks"),
    "job if false": (lambda ci: ci["jobs"]["checks"].update({"if": False}), "checks"),
    "job continue-on-error": (
        lambda ci: ci["jobs"]["checks"].update({"continue-on-error": True}), "checks"),
    "job timeout changed": (
        lambda ci: ci["jobs"]["checks"].update({"timeout-minutes": 1}), "checks"),
    "workflow permissions changed": (
        lambda ci: ci.update(permissions={"contents": "write"}), "permissions"),
    "workflow env added": (lambda ci: ci.update(env={"CI": "false"}), "env"),
}


@pytest.mark.parametrize("change,mentions", VIOLATIONS.values(), ids=VIOLATIONS.keys())
def test_each_violation_fails(tmp_path, change, mentions):
    result = judge(tmp_path, head_with(change))
    assert result.returncode != 0, result.stdout + result.stderr
    assert mentions in result.stdout + result.stderr


def test_gate_base_removed_fails(tmp_path):
    result = judge(tmp_path, {"ci.yml": copy.deepcopy(CI)})
    assert result.returncode != 0
    assert "gate-base.yml" in result.stdout + result.stderr


def test_gate_base_trigger_changed_fails(tmp_path):
    gate = copy.deepcopy(GATE)
    gate["on"] = {"pull_request": None}
    result = judge(tmp_path, {"ci.yml": copy.deepcopy(CI), "gate-base.yml": gate})
    assert result.returncode != 0
    assert "trigger" in result.stdout + result.stderr


GATE_CHANGES = {
    "step added": lambda gate: gate["jobs"]["gate"]["steps"].insert(0, {"run": "echo tamper"}),
    "step appended": lambda gate: gate["jobs"]["gate"]["steps"].append({"run": "echo tamper"}),
    "job added": lambda gate: gate["jobs"].update(evil={"runs-on": "ubuntu-24.04", "steps": [{"run": "true"}]}),
    "job renamed": lambda gate: gate["jobs"]["gate"].update(name="gate-base"),
}


def test_a_gate_workflow_step_rename_passes(tmp_path):
    gate = copy.deepcopy(GATE)
    gate["jobs"]["gate"]["steps"][0]["name"] = "Judge the head"
    result = judge(tmp_path, {"ci.yml": copy.deepcopy(CI), "gate-base.yml": gate})
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("change", GATE_CHANGES.values(), ids=GATE_CHANGES.keys())
def test_any_change_to_the_gate_workflow_jobs_fails(tmp_path, change):
    gate = copy.deepcopy(GATE)
    change(gate)
    result = judge(tmp_path, {"ci.yml": copy.deepcopy(CI), "gate-base.yml": gate})
    assert result.returncode != 0, result.stdout
    assert "gate-base.yml" in result.stdout


@pytest.mark.parametrize("job", [{"gate-base": {"steps": [{"run": "true"}]}},
                                 {"lint": {"name": "gate-base", "steps": [{"run": "true"}]}}],
                         ids=["job-id", "job-name"])
def test_a_head_job_that_reports_as_gate_base_fails(tmp_path, job):
    workflows = head_with(lambda ci: None)
    workflows["lint.yml"] = {"on": {"pull_request": None}, "jobs": job}
    result = judge(tmp_path, workflows)
    assert result.returncode != 0, result.stdout
    assert "lint.yml" in result.stdout


def test_a_symlinked_head_workflow_directory_fails(tmp_path):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    (tmp_path / "head/.github").mkdir(parents=True)
    (tmp_path / "head/.github/workflows").symlink_to(base / ".github/workflows")
    result = run_dirs(base / ".github/workflows", tmp_path / "head/.github/workflows")
    assert result.returncode != 0, result.stdout
    assert "symlink" in result.stdout


def test_a_missing_base_script_is_a_usage_error(tmp_path):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    head = write_tree(tmp_path / "head", {"ci.yml": CI, "gate-base.yml": GATE}, script="print('pass')\n")
    result = run_dirs(base / ".github/workflows", head / ".github/workflows",
                      "--base-script", tmp_path / "missing.py",
                      "--head-script", head / "scripts/gate_integrity.py")
    assert result.returncode == 2, result.stdout + result.stderr


@pytest.mark.parametrize("base_text,head_text", [("jobs: [a, b]\n", "jobs: [a]\n"),
                                                ("on: &a [*a]\njobs: {}\n", "on: &a [*a]\njobs: {}\n")],
                         ids=["jobs-list", "recursive"])
def test_a_malformed_base_still_yields_a_verdict(tmp_path, base_text, head_text):
    for side, text in (("base", base_text), ("head", head_text)):
        (tmp_path / side).mkdir()
        (tmp_path / side / "ci.yml").write_text(text)
    result = run_dirs(tmp_path / "base", tmp_path / "head")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "gate-base: FAIL" in result.stdout


@pytest.mark.parametrize("name", ["ci.yaml", "ci.YML"])
def test_only_dot_yml_base_files_are_gate_files(tmp_path, name):
    # D3: gate files are .github/workflows/*.yml.
    (tmp_path / "base").mkdir()
    (tmp_path / "head").mkdir()
    (tmp_path / "base" / name).write_text("on: push\njobs: {}\n")
    result = run_dirs(tmp_path / "base", tmp_path / "head")
    assert result.returncode == 0, result.stdout


def test_a_workflow_over_githubs_file_size_limit_fails(tmp_path):
    workflows = head_with(lambda ci: None)
    head = write_tree(tmp_path / "head", workflows)
    ci = head / ".github/workflows/ci.yml"
    ci.write_text(ci.read_text() + "#" * 500_000 + "\n")
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    result = run_dirs(base / ".github/workflows", head / ".github/workflows")
    assert result.returncode != 0, result.stdout
    assert "500 KB" in result.stdout


def judge_timeouts(tmp_path, base_value, head_value):
    for side, value in (("base", base_value), ("head", head_value)):
        directory = tmp_path / side
        directory.mkdir()
        (directory / "ci.yml").write_text(f"on: push\njobs:\n  checks:\n    timeout-minutes: {value}\n"
                                          "    runs-on: x\n    steps:\n      - run: 'true'\n")
    return run_dirs(tmp_path / "base", tmp_path / "head")


# GitHub reads YAML 1.2 core: 017 is 17, 1:30 and a date are strings, 0o17 is 15.
@pytest.mark.parametrize("base_value, head_value", [("15", "017"), ("90", "1:30"), ("15", "15.0")])
def test_a_scalar_github_reads_differently_fails(tmp_path, base_value, head_value):
    result = judge_timeouts(tmp_path, base_value, head_value)
    assert result.returncode != 0, result.stdout


@pytest.mark.parametrize("base_value, head_value", [("15", "0o17"), ("'2026-01-01'", "2026-01-01")])
def test_a_scalar_github_reads_the_same_passes(tmp_path, base_value, head_value):
    result = judge_timeouts(tmp_path, base_value, head_value)
    assert result.returncode == 0, result.stdout


def test_swapped_step_names_fail(tmp_path):
    def swap(ci):
        steps(ci)[2]["name"], steps(ci)[3]["name"] = steps(ci)[3]["name"], steps(ci)[2]["name"]
    result = judge(tmp_path, head_with(swap))
    assert result.returncode != 0, result.stdout
    assert "takes the name of another base step" in result.stdout


def test_a_multiline_head_name_cannot_start_a_runner_command(tmp_path):
    result = judge(tmp_path, head_with(lambda ci: ci.update({"x\n::error::forged": 1})))
    assert result.returncode != 0
    assert all(line.startswith("gate-base: ") for line in result.stdout.splitlines()), result.stdout


@pytest.mark.parametrize("key", ["##[error]forged", "###[warning]forged", "x ##[notice]forged"])
def test_a_head_name_cannot_carry_a_legacy_runner_command(tmp_path, key):
    # The runner's legacy parser finds `##[` anywhere in a line.
    result = judge(tmp_path, head_with(lambda ci: ci.update({key: 1})))
    assert result.returncode != 0
    assert "##[" not in result.stdout, result.stdout


def test_the_two_directory_interface_judges_the_base_checkouts_script(tmp_path):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    head = write_tree(tmp_path / "head", head_with(lambda ci: None), script="print('weaker')\n")
    result = run_dirs(base / ".github/workflows", head / ".github/workflows")
    assert result.returncode != 0, result.stdout
    assert "scripts/gate_integrity.py differs from base" in result.stdout


def test_ci_workflow_removed_fails(tmp_path):
    result = judge(tmp_path, {"gate-base.yml": copy.deepcopy(GATE)})
    assert result.returncode != 0
    assert "ci.yml" in result.stdout + result.stderr


@pytest.mark.parametrize("script", ["print('pass')\n", None], ids=["changed", "removed"])
def test_a_head_gate_script_that_differs_from_base_fails(tmp_path, script):
    result = judge(tmp_path, head_with(lambda ci: None), head_script=script)
    assert result.returncode != 0
    assert "gate_integrity.py" in result.stdout + result.stderr


def test_unparseable_head_workflow_fails(tmp_path):
    workflows = head_with(lambda ci: None)
    head = write_tree(tmp_path / "head", workflows)
    (head / ".github/workflows/ci.yml").write_text("jobs: [unclosed\n")
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base / ".github/workflows"),
         "--head", str(head / ".github/workflows")],
        capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "ci.yml" in result.stdout + result.stderr


def test_a_symlinked_head_workflow_fails(tmp_path):
    base = write_tree(tmp_path / "base", {"ci.yml": CI, "gate-base.yml": GATE})
    head = write_tree(tmp_path / "head", {"gate-base.yml": GATE})
    (head / ".github/workflows/ci.yml").symlink_to(base / ".github/workflows/ci.yml")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base / ".github/workflows"),
         "--head", str(head / ".github/workflows")],
        capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "ci.yml" in result.stdout + result.stderr


def test_the_repository_workflows_pass_against_themselves():
    workflows = ROOT / ".github/workflows"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(workflows), "--head", str(workflows),
         "--base-script", str(SCRIPT), "--head-script", str(SCRIPT)],
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


# The gate-base workflow itself.

def gate_workflow():
    return yaml.safe_load(GATE_BASE.read_text())


def all_steps(workflow):
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


def test_gate_base_triggers_only_on_pull_request_target_without_a_paths_filter():
    workflow = gate_workflow()
    # yaml.safe_load reads the bare key `on` as the boolean True, and a quoted 'on' as a string.
    [on] = [workflow[key] for key in (True, "on") if key in workflow]
    assert list(on) == ["pull_request_target"]
    trigger = on["pull_request_target"] or {}
    assert "paths" not in trigger and "paths-ignore" not in trigger
    # Every push to the PR and a change of its base branch get a fresh verdict.
    assert set(trigger.get("types", [])) == {"opened", "synchronize", "reopened", "edited"}


def test_gate_base_permissions_are_exactly_contents_read_and_checks_write():
    workflow = gate_workflow()
    assert workflow["permissions"] == {"contents": "read", "checks": "write"}
    assert all("permissions" not in job for job in workflow["jobs"].values())


def test_every_checkout_is_pinned_by_sha_without_persisted_credentials():
    checkouts = [s for s in all_steps(gate_workflow()) if s.get("uses", "").startswith("actions/checkout@")]
    assert len(checkouts) == 2
    for step in checkouts:
        assert re.fullmatch(r"actions/checkout@[0-9a-f]{40}", step["uses"]), step["uses"]
        assert step["with"]["persist-credentials"] is False


def test_every_action_is_pinned_by_sha():
    for step in all_steps(gate_workflow()):
        if "uses" in step:
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", step["uses"]), step["uses"]


def test_no_cache_is_enabled():
    for step in all_steps(gate_workflow()):
        uses = step.get("uses", "")
        assert not uses.startswith("actions/cache"), uses
        inputs = step.get("with", {})
        assert "cache" not in inputs
        if uses.startswith("astral-sh/setup-uv@"):
            # setup-uv caches by default on GitHub-hosted runners.
            assert inputs.get("enable-cache") is False


def test_no_secret_is_referenced():
    assert "secrets." not in GATE_BASE.read_text()


def test_exactly_one_job_with_id_gate_and_no_name():
    jobs = gate_workflow()["jobs"]
    assert list(jobs) == ["gate"]
    assert "name" not in jobs["gate"]


def test_the_head_is_checked_out_as_data_at_the_pr_head_sha():
    checkouts = {s["with"]["path"]: s for s in all_steps(gate_workflow())
                 if s.get("uses", "").startswith("actions/checkout@")}
    assert set(checkouts) == {"base", "head"}
    assert checkouts["base"]["with"]["ref"] == "${{ github.sha }}"
    head = checkouts["head"]["with"]
    assert head["ref"] == "${{ github.event.pull_request.head.sha }}"
    assert head["repository"] == "${{ github.event.pull_request.head.repo.full_name }}"
    # actions/checkout refuses a fork head under pull_request_target unless told the head is
    # wanted; without this a fork PR fails gate-base before the judge runs.
    assert head["allow-unsafe-pr-checkout"] is True
    # Nothing under head/ is executed: a head path appears only as a data argument of the gate.
    # The coreutils `head` command, which takes an option, is not a path.
    for step in all_steps(gate_workflow()):
        words = shlex.split(step.get("run", ""))
        for i, word in enumerate(words):
            if word == "head" and words[i + 1:i + 2] and words[i + 1].startswith("-"):
                continue
            if re.match(r"(\./)?head(/|$)", word):
                assert i > 0 and words[i - 1] in ("--head", "--head-script"), word


def test_the_base_gate_script_judges_the_head_workflows():
    [judge_step] = [s for s in all_steps(gate_workflow()) if s.get("id") == "judge"]
    run = judge_step["run"]
    assert "base/scripts/gate_integrity.py" in run
    assert "--base base/.github/workflows" in run
    assert "--head head/.github/workflows" in run
    assert "--base-script base/scripts/gate_integrity.py" in run
    assert "--head-script head/scripts/gate_integrity.py" in run


# GitHub runs a `run` step with no `shell` key as `bash -e {0}`, and `shell: bash` as
# `bash --noprofile --norc -eo pipefail {0}`.
RUNNER_SHELLS = {None: ["bash", "-e"], "bash": ["bash", "--noprofile", "--norc", "-eo", "pipefail"]}


@pytest.mark.parametrize("judge_exit", [1, 2])
def test_a_failing_judge_fails_the_judge_step(tmp_path, judge_exit):
    """The step outcome sets the check-run conclusion, so the judge's exit must survive the log pipe."""
    [judge_step] = [s for s in all_steps(gate_workflow()) if s.get("id") == "judge"]
    shell = RUNNER_SHELLS[judge_step.get("shell")]
    (tmp_path / "uv").write_text(f"#!/bin/sh\necho 'gate-base: FAIL' >&2\nexit {judge_exit}\n")
    (tmp_path / "uv").chmod(0o755)
    script = tmp_path / "step.sh"
    script.write_text(judge_step["run"])
    result = subprocess.run([*shell, str(script)], capture_output=True, text=True, timeout=30,
                            env={"PATH": f"{tmp_path}:/usr/bin:/bin", "RUNNER_TEMP": str(tmp_path)})
    assert result.returncode != 0
    assert "gate-base: FAIL" in (tmp_path / "gate.log").read_text()


def run_report_step(tmp_path, log_text, gh_failures, marker="status=completed"):
    """Run the step posting `marker` with a stub gh that fails gh_failures times, then records its summary."""
    [report] = [s for s in all_steps(gate_workflow()) if marker in s.get("run", "")]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "sleep").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "gh").write_text(
        "#!/bin/sh\n"
        f"n=$(cat {tmp_path}/calls 2>/dev/null || echo 0); n=$((n + 1)); echo $n > {tmp_path}/calls\n"
        f"[ $n -le {gh_failures} ] && exit 1\n"
        f"for a in \"$@\"; do case $a in 'output[summary]=@'*) cp \"${{a#*@}}\" {tmp_path}/posted;; esac; done\n")
    for tool in ("sleep", "gh"):
        (bin_dir / tool).chmod(0o755)
    (tmp_path / "gate.log").write_text(log_text)
    (tmp_path / "step.sh").write_text(report["run"])
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "RUNNER_TEMP": str(tmp_path), "OUTCOME": "failure",
           "REPO": "o/r", "HEAD_SHA": "0" * 40}
    return subprocess.run([*RUNNER_SHELLS[report.get("shell")], str(tmp_path / "step.sh")],
                          capture_output=True, text=True, timeout=30, env=env)


def test_the_report_step_retries_and_caps_the_summary(tmp_path):
    result = run_report_step(tmp_path, "gate-base: x ```\n" * 20000, gh_failures=2)
    assert result.returncode == 0, result.stderr
    posted = (tmp_path / "posted").read_text()
    assert len(posted) <= 65535
    # Head-controlled text cannot close the fence the log sits in.
    assert posted.count("```") == 2


def test_the_report_step_fails_when_the_check_run_cannot_be_created(tmp_path):
    result = run_report_step(tmp_path, "gate-base: FAIL\n", gh_failures=99)
    assert result.returncode != 0


def test_the_judge_step_times_out_before_the_job():
    workflow = gate_workflow()
    [judge_step] = [s for s in all_steps(workflow) if s.get("id") == "judge"]
    assert judge_step["timeout-minutes"] < workflow["jobs"]["gate"]["timeout-minutes"]


def test_an_in_progress_gate_base_run_replaces_an_earlier_verdict_before_the_judge_runs():
    # After a retarget the head SHA is unchanged, so its earlier success would otherwise stand
    # until this run reports.
    first = all_steps(gate_workflow())[0]
    assert "name=gate-base" in first["run"] and "status=in_progress" in first["run"]
    assert '"head_sha=$HEAD_SHA"' in first["run"]
    assert first["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert "if" not in first and "continue-on-error" not in first


@pytest.mark.parametrize("gh_failures, ok", [(2, True), (99, False)])
def test_the_in_progress_step_retries_and_fails_closed(tmp_path, gh_failures, ok):
    result = run_report_step(tmp_path, "", gh_failures, marker="status=in_progress")
    assert (result.returncode == 0) is ok, result.stderr


def test_a_newer_run_for_the_pr_cancels_the_older_before_it_reports():
    # A verdict judged against an earlier base must not land after the current one.
    workflow = gate_workflow()
    assert workflow["concurrency"] == {"group": "gate-base-${{ github.event.pull_request.number }}",
                                       "cancel-in-progress": True}


def test_the_check_run_gate_base_is_created_on_the_pr_head_sha():
    [report] = [s for s in all_steps(gate_workflow()) if "status=completed" in s.get("run", "")]
    # It reports a failed judge too, but not from a run a newer one cancelled.
    assert report["if"] == "${{ !cancelled() }}"
    assert "name=gate-base" in report["run"]
    assert '"head_sha=$HEAD_SHA"' in report["run"]
    assert report["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert report["env"]["OUTCOME"] == "${{ steps.judge.outcome }}"
    assert report["env"]["GH_TOKEN"] == "${{ github.token }}"
