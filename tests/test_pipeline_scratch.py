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
    env = {**os.environ, "TMPDIR": str(runtime_tmp)}

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
    env = {**os.environ, "TMPDIR": str(runtime_tmp)}

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
