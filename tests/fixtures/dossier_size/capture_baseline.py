"""Regenerates baseline-arbitrate.txt: the arbitrate dossier of the pipeline script at commit
21f026593944ded43af3bd6b64f16bcae441095e (before SKL-241), run on this fixture and normalized.

Run by hand from the repository root, with that commit present locally:

    uv run --locked python tests/fixtures/dossier_size/capture_baseline.py

It checks that commit out into a temporary detached worktree, runs that version's own preflight,
dossier and record commands on the fixture, writes the normalized dossier over the committed
baseline and removes the worktree. A second run must leave `git status` clean. The test suite never
runs this file; it reads the committed baseline only.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dossier_fixture as fixture  # noqa: E402

BASELINE_COMMIT = "21f026593944ded43af3bd6b64f16bcae441095e"
ROOT = fixture.HERE.parents[2]
SCRIPT = Path("skills/adversarial-review-pipeline/scripts/run-adversarial-pipeline.sh")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name).resolve()
        old = tmp / "old"
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "-q", "--detach", str(old),
                        BASELINE_COMMIT], check=True)
        try:
            work = tmp / "work"
            work.mkdir()
            run = fixture.arbitrate_dossier(old / SCRIPT, work)
            baseline = fixture.normalize(run["dossier"], checkout=run["checkout"],
                                         run_dir=run["run_dir"], tmp_root=run["tmp_root"],
                                         commits=run["commits"])
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(old)],
                           check=True)
    fixture.BASELINE.write_bytes(baseline)
    print(f"{fixture.BASELINE.relative_to(ROOT)}: {len(baseline)} bytes")


if __name__ == "__main__":
    main()
