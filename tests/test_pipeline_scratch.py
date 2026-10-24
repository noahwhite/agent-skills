"""Every gate artefact lives in the session's scratch directory, never directly under the base.

The pipeline script is handed the session's scratch directory with `--scratch`; its dossiers and
throwaway checkouts belong under that directory (SKL-58, AC2), inside a per-run directory so two
runs cannot overwrite each other. Without `--scratch` it falls back to a standalone directory and
never writes inside the checkout under review.
"""

import os
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "agent-skills@example.com"],
        ["git", "config", "user.name", "agent-skills"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    (repo / "tracked.txt").write_text("one\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The test's own environment: the gate's ADVERSARIAL_* variables must never leak in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ADVERSARIAL_")}
    return {**env, **(extra or {})}


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


def dossier_path(result: subprocess.CompletedProcess) -> Path:
    assert result.returncode == 0, result.stdout + result.stderr
    return Path(result.stdout.strip().splitlines()[-1])


def test_gate_artefacts_stay_inside_the_supplied_session_directory(tmp_path):
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-58.\n")
    marker = tmp_path / "suite-cwd.txt"
    env = clean_env({"TMPDIR": str(runtime_tmp)})

    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD",
        "--test-cmd", f"pwd > {shlex.quote(str(marker))}", "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    assert marker.is_file(), "the suite never ran, so the checkout location was not observed"
    suite_cwd = Path(marker.read_text().strip())
    assert scratch in suite_cwd.parents, \
        f"the preflight checkout escaped the session scratch directory: {suite_cwd}"
    assert suite_cwd.parent.name.startswith("adversarial-preflight."), suite_cwd

    first = dossier_path(run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--spec", str(spec),
        "--scratch", str(scratch), env=env,
    ))
    assert first.is_file(), f"the dossier was not written: {first}"
    assert scratch in first.parents, f"{first} is not inside the session scratch directory"
    assert first.parent.name.startswith("run."), \
        f"the dossier is not inside a per-run directory: {first}"

    second = dossier_path(run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--spec", str(spec),
        "--scratch", str(scratch), env=env,
    ))
    assert second != first, "two runs shared one dossier path inside the session directory"

    checkout = run_script(
        "checkout", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    assert checkout.returncode == 0, checkout.stdout + checkout.stderr
    worktree = Path(checkout.stdout.strip().splitlines()[-1])
    assert worktree.is_dir(), f"the throwaway checkout was not created: {worktree}"
    assert scratch in worktree.parents, f"the throwaway checkout escaped the session directory: {worktree}"
    assert worktree.parent.name.startswith("adversarial-checkout."), \
        f"the throwaway checkout reused the session directory itself: {worktree}"
    cleanup = run_script("cleanup", str(worktree), "--repo", str(repo), env=env)
    assert cleanup.returncode == 0, cleanup.stdout + cleanup.stderr


def test_without_scratch_the_run_stays_out_of_the_checkout(tmp_path):
    repo = make_repo(tmp_path)
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-58.\n")
    env = clean_env({"TMPDIR": str(runtime_tmp)})

    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true", env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr

    written = dossier_path(run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--spec", str(spec), env=env,
    ))
    assert written.is_file(), f"the dossier was not written: {written}"
    assert runtime_tmp in written.parents, \
        f"without --scratch the run must use a standalone directory, got {written}"
    assert repo not in written.parents, f"the dossier was written inside the checkout: {written}"


def test_a_relative_scratch_path_is_refused_before_any_phase_runs(tmp_path):
    repo = make_repo(tmp_path)
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    result = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", "relative-scratch", env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "absolute path" in result.stderr, result.stderr
    assert not (repo / "relative-scratch").exists(), "a relative scratch path dirtied the checkout"


def test_a_scratch_path_that_is_a_file_is_refused_without_clobbering_the_phase_report(tmp_path):
    repo = make_repo(tmp_path)
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    first = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    report = Path(first.stderr.strip().splitlines()[-1].split(" -> ")[-1])
    assert report.is_file() and "PASS" in report.read_text()

    unusable = tmp_path / "not-a-directory"
    unusable.write_text("x\n")
    rejected = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(unusable), env=env,
    )
    assert rejected.returncode == 2, rejected.stdout + rejected.stderr
    assert "must be a directory" in rejected.stderr, rejected.stderr
    assert "PASS" in report.read_text(), "the refused run clobbered the accepted phase report"


def test_the_phase_agent_receives_the_session_scratch_directory(tmp_path):
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr

    agent = (
        '{ printf "REVIEW-RAN: yes\\n"; '
        'printf "scratch=%s\\n" "${ADVERSARIAL_SESSION_SCRATCH:-none}"; '
        'printf "cwd=%s\\n" "$PWD"; } > {output_file}'
    )
    sweep = run_script(
        "run", "sweep", "--repo", str(repo), "--base", "HEAD",
        "--scratch", str(scratch), "--agent-cmd", agent, env=env,
    )
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    report = Path(sweep.stderr.strip().splitlines()[-1].split(" -> ")[-1])
    lines = report.read_text().splitlines()
    assert f"scratch={scratch}" in lines, f"the agent did not get the session directory: {lines}"
    cwd = next(line for line in lines if line.startswith("cwd=")).removeprefix("cwd=")
    assert scratch in Path(cwd).parents, f"the run checkout is outside the session directory: {cwd}"
    dossier = next(p for p in scratch.rglob("sweep-dossier.md"))
    assert str(scratch) in dossier.read_text(), \
        "the dossier does not carry the session scratch directory for a subagent-driven phase"


def test_a_scratch_directory_inside_the_repository_is_refused(tmp_path):
    repo = make_repo(tmp_path)
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    inside = repo / "scratch"
    result = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(inside), env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "outside the repository" in result.stderr, result.stderr
    assert not inside.exists(), "a refused scratch path was created inside the checkout"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores a 0500 directory mode (CAP_DAC_OVERRIDE)")
def test_read_only_scratch_is_refused_before_any_phase_report_is_written(tmp_path):
    repo = make_repo(tmp_path)
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    first = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    report = Path(first.stderr.strip().splitlines()[-1].split(" -> ")[-1])
    scratch.chmod(0o500)
    try:
        rejected = run_script(
            "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
            "--scratch", str(scratch), env=env,
        )
    finally:
        scratch.chmod(0o700)
    assert rejected.returncode == 2, rejected.stdout + rejected.stderr
    assert "not writable" in rejected.stderr, rejected.stderr
    assert "PASS" in report.read_text(), "the refused run discarded the accepted phase report"


def test_an_empty_scratch_value_is_refused(tmp_path):
    repo = make_repo(tmp_path)
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    result = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", "", env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "needs a directory value" in result.stderr, result.stderr


def test_a_refused_dossier_keeps_the_accepted_phase_report(tmp_path):
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    report = Path(preflight.stderr.strip().splitlines()[-1].split(" -> ")[-1])

    refused = run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD",
        "--scratch", str(repo / "badscratch"), env=env,
    )
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert "PASS" in report.read_text(), "a refused dossier discarded the accepted preflight report"


def test_an_ambient_adversarial_scratch_cannot_redirect_the_run(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    ambient = tmp_path / "ambient-scratch"
    monkeypatch.setenv("ADVERSARIAL_SCRATCH", str(ambient))
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-58.\n")
    env = clean_env({"TMPDIR": str(runtime_tmp)})

    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    written = dossier_path(run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--spec", str(spec),
        "--scratch", str(scratch), env=env,
    ))
    assert scratch in written.parents, written
    assert not ambient.exists(), "the ambient ADVERSARIAL_SCRATCH redirected the run"
