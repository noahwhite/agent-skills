"""Every gate artefact lives in the session's scratch directory, never directly under the base.

The pipeline script is handed the session's scratch directory with `--scratch`; its dossiers and
throwaway checkouts belong under that directory (SKL-58, AC2), and a supplied directory is never
used as the directory itself, so two runs cannot overwrite each other's dossiers.
"""

import os
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


def test_gate_artefacts_stay_inside_the_supplied_session_directory(tmp_path):
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-58.\n")
    env = {**os.environ, "TMPDIR": str(runtime_tmp)}

    marker = tmp_path / "suite-cwd.txt"
    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD",
        "--test-cmd", f"pwd > {marker}", "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    assert marker.is_file(), "the suite never ran, so the checkout location was not observed"
    suite_cwd = Path(marker.read_text().strip())
    assert scratch in suite_cwd.parents, \
        f"the preflight checkout escaped the session scratch directory: {suite_cwd}"

    dossier = run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--spec", str(spec),
        "--scratch", str(scratch), env=env,
    )
    assert dossier.returncode == 0, dossier.stdout + dossier.stderr
    written = Path(dossier.stdout.strip().splitlines()[-1])
    assert written.is_file(), f"the dossier was not written: {written}"
    assert scratch in written.parents, f"{written} is not inside the session scratch directory"

    second = run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--spec", str(spec),
        "--scratch", str(scratch), env=env,
    )
    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(second.stdout.strip().splitlines()[-1]) != written, \
        "two runs shared one dossier path inside the session directory"
