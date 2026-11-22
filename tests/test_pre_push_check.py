"""Behavioural tests for scripts/pre-push-check.sh (SKL-384).

Each test builds its own git repository and stubs `uv`, the vendor check and, where needed, `date`,
so the suite needs no network and no credentials. The script under test is copied in unchanged.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pre-push-check.sh"

# An outer git environment (GIT_DIR, GIT_INDEX_FILE) or global configuration (excludes, hooks,
# templates) must not leak into the fixture.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

UV_STUB = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$STUB_LOG"
if [ -n "${PYTEST_ADDOPTS:-}" ]; then printf 'addopts:%s\\n' "$PYTEST_ADDOPTS" >> "$STUB_LOG"; fi
if [ "$1" = "run" ] && [ "$3" = "python" ]; then
  shift 3
  exec python3 "$@"
fi
if [ -n "${STUB_ADVANCE:-}" ] && [[ "$*" == *"--version"* ]]; then
  git commit --allow-empty -qm "advanced during the run"
fi
if [ -n "${STUB_START_FAIL:-}" ] && [[ "$*" == *"$STUB_START_FAIL"* ]]; then
  echo "error: Failed to spawn: pytest"
  exit 127
fi
if [ -n "${STUB_GREP:-}" ] && [[ "$*" == *" -q "* ]] && [ -n "${STUB_GREP_FILE:-}" ] && grep -qF -- "$STUB_GREP" "$STUB_GREP_FILE"; then
  echo "stub: found the forbidden text in $STUB_GREP_FILE"
  exit 1
fi
if [ -n "${STUB_FAIL:-}" ] && [[ "$*" == *"$STUB_FAIL"* ]]; then
  echo "stub failure on $STUB_FAIL"
  exit "${STUB_FAIL_STATUS:-1}"
fi
echo "stub ran: $*"
exit 0
"""

VENDOR_STUB = """#!/usr/bin/env python3
import os
from pathlib import Path

with Path(os.environ["STUB_LOG"]).open("a") as log:
    log.write("vendor-check\\n")
raise SystemExit(int(os.environ.get("STUB_VENDOR_STATUS", "0")))
"""

DATE_STUB = """#!/usr/bin/env bash
printf '123N\\n'
"""

DOC_CHECKS = [
    "run --locked pytest -q tests/test_skills.py::test_no_em_dash",
    "run --locked pytest -q tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase",
]
VENDOR = "run --locked python scripts/vendor_shared.py --check"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=ENV
    )
    return result.stdout


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()
    git(repo, "init", "-q", "--template=", "-b", "main")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "core.hooksPath", str(hooks))

    (repo / "scripts").mkdir()
    (repo / "scripts" / "pre-push-check.sh").write_text(SCRIPT.read_text(), encoding="utf-8")
    write(repo, "scripts/vendor_shared.py", VENDOR_STUB)
    write(repo, "scripts/gate_integrity.py", "# fixture\n")
    write(repo, "scripts/leak_scan.py", "# fixture\n")
    write(repo, "tests/test_skills.py", "def test_fixture():\n    assert True\n")
    write(repo, "tests/test_gate_integrity.py", "def test_fixture():\n    assert True\n")
    write(repo, "skills/x.md", "clean line\n")
    write(repo, "LICENSE", "fixture license\n")
    write(repo, "README.md", "# fixture\n")
    commit(repo, "fixture")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(UV_STUB, encoding="utf-8")
    uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
    return repo


@pytest.fixture
def run(repo: Path, tmp_path: Path):
    log = tmp_path / "stub.log"
    env = dict(ENV)
    env["PATH"] = f"{tmp_path / 'bin'}{os.pathsep}{env['PATH']}"
    env["STUB_LOG"] = str(log)
    env["HOME"] = str(tmp_path / "home")

    def call(*args: str, **extra: str) -> subprocess.CompletedProcess:
        run_env = dict(env)
        run_env.update(extra)
        return subprocess.run(
            ["bash", "scripts/pre-push-check.sh", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            env=run_env,
            timeout=120,
        )

    call.log = log
    call.path = tmp_path
    return call


def stage(repo: Path, rel: str, text: str = "changed\n") -> None:
    write(repo, rel, text)
    git(repo, "add", rel)


def topic(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "topic")


def invariants(result: subprocess.CompletedProcess) -> None:
    """The per-check report lines always end with a total line."""
    assert result.stdout.strip().splitlines()[-1].startswith("total: "), result.stdout


# Change set


def test_change_set_staged_only(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "change set:" in result.stdout
    assert "scripts/gate_integrity.py" in result.stdout
    assert "tests/test_gate_integrity.py" in result.stdout


def test_change_set_branch_diff_only(repo, run):
    topic(repo)
    stage(repo, "scripts/leak_scan.py")
    commit(repo, "topic change")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "scripts/leak_scan.py" in result.stdout
    assert "tests/test_leak_scan.py" in result.stdout


def test_change_set_is_the_union_of_staged_and_committed(repo, run):
    topic(repo)
    stage(repo, "scripts/leak_scan.py")
    commit(repo, "topic change")
    stage(repo, "scripts/gate_integrity.py")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "scripts/leak_scan.py" in result.stdout
    assert "scripts/gate_integrity.py" in result.stdout
    assert result.stdout.count("tests/test_leak_scan.py") == 1
    assert result.stdout.count("tests/test_gate_integrity.py") == 1


def test_default_base_is_origin_main(repo, run):
    topic(repo)
    stage(repo, "scripts/leak_scan.py")
    commit(repo, "topic change")
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    result = run("--list")
    assert result.returncode == 0, result.stderr
    assert "scripts/leak_scan.py" in result.stdout
    assert "tests/test_leak_scan.py" in result.stdout


def test_base_equals_form_is_accepted(repo, run):
    result = run("--list", "--base=main")
    assert result.returncode == 0, result.stderr
    assert "change set: empty" in result.stdout


def test_unstaged_tracked_modification_is_refused_by_name(repo, run):
    write(repo, "scripts/gate_integrity.py", "unstaged edit\n")
    result = run("--list", "--base", "main")
    assert result.returncode == 2
    assert "pre-push-check: error: unstaged modifications to tracked files" in result.stderr
    assert "scripts/gate_integrity.py" in result.stderr
    assert "total: " not in result.stdout


def test_assume_unchanged_entry_is_refused_by_name(repo, run):
    write(repo, "scripts/gate_integrity.py", "hidden edit\n")
    git(repo, "update-index", "--assume-unchanged", "scripts/gate_integrity.py")
    result = run("--list", "--base", "main")
    assert result.returncode == 2
    assert "assume-unchanged or skip-worktree entries" in result.stderr
    assert "scripts/gate_integrity.py" in result.stderr


def test_unresolvable_base_names_the_ref(repo, run):
    result = run("--list", "--base", "nosuchref")
    assert result.returncode == 2
    assert "pre-push-check: error: unresolvable base ref nosuchref" in result.stderr
    assert "total: " not in result.stdout


def test_empty_change_set_runs_only_the_doc_and_vendor_checks(repo, run):
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert f"HEAD: {git(repo, 'rev-parse', 'HEAD').strip()}" in result.stdout
    assert "change set: empty" in result.stdout
    invariants(result)
    assert run.log.read_text().splitlines() == [
        "run --locked pytest --version",
        *DOC_CHECKS,
        VENDOR,
        "vendor-check",
    ]


# Mapping table, the test-module rule, fallback and --list


def test_mapped_path_selects_its_module_and_unmapped_path_takes_the_fallback(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    stage(repo, "LICENSE")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "tests/test_gate_integrity.py" in result.stdout
    assert "focused: no module for LICENSE" in result.stdout
    assert "fallback: tests/test_skills.py" in result.stdout


def test_unmapped_path_is_named_during_a_run(repo, run):
    stage(repo, "LICENSE")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert "focused: no module for LICENSE" in result.stdout
    assert "run --locked pytest -q tests/test_skills.py\n" in run.log.read_text()


def test_a_committed_unmapped_path_takes_the_fallback_in_a_run(repo, run):
    topic(repo)
    write(repo, "README.md", "# changed\n")
    commit(repo, "change the readme")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert "focused: no module for README.md" in result.stdout
    assert "run --locked pytest -q tests/test_skills.py\n" in run.log.read_text()


def test_list_runs_nothing(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert not run.log.exists() or run.log.read_text() == ""
    assert "total: " not in result.stdout


def test_list_reports_the_staged_state(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "note: the index differs from HEAD" in result.stdout


def test_list_empty_change_set(repo, run):
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "change set: empty" in result.stdout
    assert "selected modules:\n  none" in result.stdout
    assert "fallback: none" in result.stdout


def test_a_changed_test_module_runs_itself(repo, run):
    stage(repo, "tests/test_skills.py", "def test_fixture():\n    assert True\n\n\ndef test_extra():\n    assert True\n")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "tests/test_skills.py" in result.stdout
    assert "fallback: none" in result.stdout


def test_a_new_test_module_maps_to_itself(repo, run):
    stage(repo, "tests/test_new_probe.py", "def test_new_probe():\n    assert False\n")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "  tests/test_new_probe.py" in result.stdout


def test_a_non_ascii_test_module_is_selected_and_runs(repo, run):
    topic(repo)
    write(repo, "tests/test_caf\u00e9.py", "def test_cafe():\n    assert False\n")
    commit(repo, "add a non-ascii test module")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert "tests/test_caf\u00e9.py" in result.stdout
    assert "run --locked pytest -q tests/test_caf\u00e9.py\n" in run.log.read_text()
    assert "caf\\303\\251" not in result.stdout


def test_workflow_and_profile_paths_map_to_their_guards(repo, run):
    stage(repo, ".agent-skills/profile.yaml", "version: 1\n")
    stage(repo, ".github/workflows/ci.yml", "jobs: {}\n")
    result = run("--list", "--base", "main")
    assert result.returncode == 0, result.stderr
    assert "tests/test_profiles.py" in result.stdout
    assert "tests/test_gate_integrity.py" in result.stdout


def test_a_committed_deletion_of_a_module_skips_it(repo, run):
    topic(repo)
    git(repo, "rm", "-q", "tests/test_gate_integrity.py")
    commit(repo, "delete the module")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert "focused: module tests/test_gate_integrity.py is not present" in result.stdout
    assert "run --locked pytest -q tests/test_gate_integrity.py\n" not in run.log.read_text()


def test_a_committed_rename_selects_the_old_path_module(repo, run):
    topic(repo)
    git(repo, "mv", "scripts/gate_integrity.py", "scripts/gate_renamed.py")
    commit(repo, "rename the script")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert "scripts/gate_integrity.py" in result.stdout
    assert "scripts/gate_renamed.py" in result.stdout
    assert "run --locked pytest -q tests/test_gate_integrity.py\n" in run.log.read_text()


# Checks, reporting and exit statuses


def test_passing_run_prints_each_check_line_and_a_total(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert any(line.startswith("ok tests/test_skills.py::test_no_em_dash (") for line in lines)
    assert any(
        line.startswith("ok tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase (")
        for line in lines
    )
    assert any(
        line.startswith("ok vendor: uv run --locked python scripts/vendor_shared.py --check (")
        for line in lines
    )
    assert any(line.startswith("ok tests/test_gate_integrity.py (") for line in lines)
    invariants(result)
    assert "4 checks" in lines[-1]
    assert "0 failed" in lines[-1]


def test_checks_run_in_order(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main")
    assert result.returncode == 0, result.stderr
    assert run.log.read_text().splitlines() == [
        "run --locked pytest --version",
        *DOC_CHECKS,
        VENDOR,
        "vendor-check",
        "run --locked pytest -q tests/test_gate_integrity.py",
    ]


def test_failure_names_the_check_and_reports_command_and_output(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main", STUB_FAIL="test_no_em_dash")
    assert result.returncode == 1
    assert "FAIL tests/test_skills.py::test_no_em_dash (" in result.stdout
    assert "command: uv run --locked pytest -q tests/test_skills.py::test_no_em_dash" in result.stdout
    assert "stub failure on test_no_em_dash" in result.stdout
    invariants(result)
    assert "1 failed" in result.stdout.splitlines()[-1]
    # The other checks still run after a failure.
    assert "ok tests/test_gate_integrity.py" in result.stdout


def test_a_pytest_exit_status_two_is_a_failed_check_not_a_startup_error(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main", STUB_FAIL="test_no_em_dash", STUB_FAIL_STATUS="2")
    assert result.returncode == 1
    assert "FAIL tests/test_skills.py::test_no_em_dash" in result.stdout
    assert "cannot start" not in result.stderr


def test_two_failures_print_both_fail_lines(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main", STUB_FAIL="pytest -q tests/test_skills.py")
    assert result.returncode == 1
    fail_lines = [line for line in result.stdout.splitlines() if line.startswith("FAIL ")]
    assert len(fail_lines) == 2, result.stdout
    assert "2 failed" in result.stdout.splitlines()[-1]


def test_vendor_failure_names_the_vendor_check(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main", STUB_VENDOR_STATUS="1")
    assert result.returncode == 1
    assert "FAIL vendor: uv run --locked python scripts/vendor_shared.py --check (" in result.stdout
    assert "command: uv run --locked python scripts/vendor_shared.py --check" in result.stdout


def test_check_that_cannot_start_is_a_named_error(repo, run):
    stage(repo, "scripts/gate_integrity.py")
    result = run("--base", "main", STUB_START_FAIL="pytest")
    assert result.returncode == 2
    assert "pre-push-check: error: cannot start the pytest checks" in result.stderr
    assert "failed to spawn" in result.stderr.lower()
    assert "FAIL " not in result.stdout


def test_a_missing_doc_lint_module_is_a_named_error(repo, run):
    topic(repo)
    git(repo, "rm", "-q", "tests/test_skills.py")
    commit(repo, "delete the doc lint module")
    result = run("--base", "main")
    assert result.returncode == 2
    assert "cannot start the doc lint checks" in result.stderr
    assert "tests/test_skills.py" in result.stderr


def test_inherited_pytest_addopts_is_scrubbed(repo, run):
    stage(repo, "scripts/gate_integrity.py", "def test_fixture():\n    assert False\n")
    result = run("--base", "main", PYTEST_ADDOPTS="--collect-only")
    assert result.returncode == 0, result.stderr
    assert "addopts:" not in run.log.read_text()


def test_head_moving_during_the_run_is_a_named_error(repo, run):
    result = run("--base", "main", STUB_ADVANCE="1")
    assert result.returncode == 2
    assert "HEAD moved from" in result.stderr
    assert "re-run the check for the new HEAD" in result.stderr
    invariants(result)


def test_an_unsupported_date_is_a_named_error_and_help_still_works(repo, run):
    date = run.path / "bin" / "date"
    date.write_text(DATE_STUB, encoding="utf-8")
    date.chmod(date.stat().st_mode | stat.S_IEXEC)
    assert run("--help").returncode == 0
    result = run("--list")
    assert result.returncode == 2
    assert "pre-push-check: error: GNU date with +%s%N is required" in result.stderr


# The exact-HEAD guarantee


def test_a_staged_correction_does_not_certify_head(repo, run):
    write(repo, "skills/x.md", "a line with an em dash \u2014 in it\n")
    commit(repo, "head carries the em dash")
    write(repo, "skills/x.md", "a corrected line\n")
    git(repo, "add", "skills/x.md")
    result = run("--base", "HEAD~1", STUB_GREP="\u2014", STUB_GREP_FILE="skills/x.md")
    assert result.returncode == 1, result.stdout
    assert "note: the index differs from HEAD" in result.stdout
    assert "FAIL tests/test_skills.py::test_no_em_dash" in result.stdout


def test_a_pass_covers_head_not_the_staged_content(repo, run):
    write(repo, "skills/x.md", "a line with an em dash \u2014 in it\n")
    git(repo, "add", "skills/x.md")
    result = run("--base", "HEAD", STUB_GREP="\u2014", STUB_GREP_FILE="skills/x.md")
    assert result.returncode == 0, result.stdout
    assert "note: the index differs from HEAD" in result.stdout
    assert "0 failed" in result.stdout.splitlines()[-1]


# --help


def test_help_states_checks_change_set_table_fallback_and_exit_codes(repo, run):
    result = run("--help")
    assert result.returncode == 0, result.stderr
    text = result.stdout
    assert "tests/test_skills.py::test_no_em_dash" in text
    assert "tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase" in text
    assert "uv run --locked python scripts/vendor_shared.py --check" in text
    assert "git diff --cached --name-only" in text
    assert "git diff --name-only <merge-base>...HEAD" in text
    assert "scripts/gate_integrity.py" in text
    assert "tests/test_gate_integrity.py" in text
    assert "a changed tests/test_*.py path maps to itself" in text
    assert "fallback module tests/test_skills.py" in text
    assert "Exit status: 0" in text
    assert "1 at least one check failed" in text
    assert "2 an error" in text
    assert "origin/main" in text
    assert "first push" in text
    assert "Stray files in the checkout can affect the doc lint" in text
    assert "exact HEAD being pushed" in text
    assert "clean snapshot of HEAD" in text
    assert "bash 4.4 or newer and GNU date" in text
    assert "assume-unchanged" in text


def test_invalid_option_is_a_named_error(repo, run):
    result = run("--bogus")
    assert result.returncode == 2
    assert "pre-push-check: error: unknown option --bogus" in result.stderr


def test_base_without_a_ref_is_a_named_error(repo, run):
    result = run("--base")
    assert result.returncode == 2
    assert "pre-push-check: error: --base needs a ref" in result.stderr


def test_empty_base_value_is_a_named_error(repo, run):
    result = run("--base=")
    assert result.returncode == 2
    assert "pre-push-check: error: --base needs a ref" in result.stderr


def test_unexpected_argument_is_a_named_error(repo, run):
    result = run("extra")
    assert result.returncode == 2
    assert "pre-push-check: error: unexpected argument extra" in result.stderr
