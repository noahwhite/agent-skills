"""The SKL-242 dossier-size fixture: a deterministic two-commit repository, the script commands that
accept its sweep and hunt, the arbitrate dossier they lead to, and the one normalization applied to
both the pinned baseline and the current dossier.

Shared by tests/test_pipeline_dossier_fixture.py and capture_baseline.py beside this file, so the
baseline and the ceiling are measured on the same fixture. Not a test module: pytest never collects
it (no `test_` prefix).
"""

import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The marker every text input carries: the first line, or the second after `REVIEW-RAN: yes` in a
# phase report. Defined once here; the test asserts it on every text input.
MARKER = "SYNTHETIC FIXTURE - SKL-242 - not real data"

SPEC = HERE / "spec.txt"
PHASE1_REPORT = HERE / "phase1-sweep.txt"
PHASE2_REPORT = HERE / "phase2-hunt.txt"
SOURCE_BASE = HERE / "source-base.txt"
SOURCE_HEAD = HERE / "source-head.txt"
BASELINE = HERE / "baseline-arbitrate.txt"

# Every text input of the fixture, and the ones that are phase reports (marker on the second line).
TEXT_INPUTS = (SPEC, PHASE1_REPORT, PHASE2_REPORT, SOURCE_BASE, SOURCE_HEAD)
REPORTS = (PHASE1_REPORT, PHASE2_REPORT)

PART_COUNT = 25
PART_TOKEN = "%NN%"
BASE_REF = "base"

# Lines of the head template that exist only in the head, so in the fixture diff they occur only
# inside changed hunks; one per suffix per part.
HUNK_MARKER_SUFFIXES = ("A", "B", "C")


def part_path(n: int) -> str:
    return f"ledger/part_{n:02d}.py"


def hunk_markers() -> list[str]:
    return [f"HUNK-ONLY-MARKER-{n:02d}-{s}" for n in range(1, PART_COUNT + 1) for s in HUNK_MARKER_SUFFIXES]


def render(template: Path, n: int) -> str:
    return template.read_text().replace(PART_TOKEN, f"{n:02d}")


def fixed_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """The environment of every git and script call: no user or system git config, a fixed identity
    and date, a fixed terminal width and locale, and no inherited ADVERSARIAL_* settings."""
    env = {k: v for k, v in (base_env if base_env is not None else os.environ).items()
           if not k.startswith(("ADVERSARIAL_", "GIT_"))}
    env.update({
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Fixture Author",
        "GIT_AUTHOR_EMAIL": "fixture@example.com",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
        "GIT_COMMITTER_NAME": "Fixture Author",
        "GIT_COMMITTER_EMAIL": "fixture@example.com",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
        "COLUMNS": "80",
        "LC_ALL": "C",
        "TZ": "UTC",
    })
    return env


def git(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def write_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("ascii"))


def build_repo(repo: Path, env: dict[str, str]) -> tuple[str, str]:
    """Creates the fixture repository at `repo`: a base commit (tagged `base`) holding every part
    from the base template, and a head commit holding every part from the head template.
    Returns the base and head commit IDs."""
    repo.mkdir(parents=True)
    git(repo, env, "init", "-q", "--initial-branch=main")
    git(repo, env, "config", "core.autocrlf", "false")
    git(repo, env, "config", "commit.gpgsign", "false")
    git(repo, env, "config", "tag.gpgsign", "false")
    for template, message in ((SOURCE_BASE, "base"), (SOURCE_HEAD, "head")):
        for n in range(1, PART_COUNT + 1):
            write_lf(repo / part_path(n), render(template, n))
        git(repo, env, "add", "-A")
        git(repo, env, "commit", "-q", "-m", message)
        if message == "base":
            git(repo, env, "tag", BASE_REF)
    return git(repo, env, "rev-parse", f"{BASE_REF}^{{commit}}"), git(repo, env, "rev-parse", "HEAD")


def fixture_diff(repo: Path, env: dict[str, str]) -> tuple[list[str], bytes]:
    """The derived diff the criteria measure: the files it touches and its bytes."""
    names = git(repo, env, "diff", "--no-ext-diff", "--no-renames", "--name-only",
                f"{BASE_REF}...HEAD").splitlines()
    diff = subprocess.run(["git", "diff", "--no-ext-diff", "--no-renames", "--unified=3",
                           f"{BASE_REF}...HEAD"], cwd=repo, env=env, check=True,
                          capture_output=True).stdout
    return names, diff


def run_script(script: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], cwd=script.parent, env=env,
                          capture_output=True, text=True, timeout=300)


def _checked(result: subprocess.CompletedProcess, what: str) -> subprocess.CompletedProcess:
    if result.returncode != 0:
        raise RuntimeError(f"{what} exited {result.returncode}:\n{result.stdout}\n{result.stderr}")
    return result


def artifact_paths(script: Path, env: dict[str, str], repo: Path) -> dict[str, Path]:
    listed = _checked(run_script(script, env, "paths", "--repo", str(repo), "--base", BASE_REF), "paths")
    return {name: Path(path) for name, _, path in
            (line.partition(" ") for line in listed.stdout.splitlines()) if path}


def arbitrate_dossier(script: Path, tmp: Path) -> dict:
    """Builds the fixture under `tmp`, accepts the preflight, sweep and hunt through `script`'s own
    commands, and writes the arbitrate dossier. Returns the dossier bytes and every value the
    normalization needs: the checkout (None when the script names none), the run directory, the
    temporary root and the fixture commit IDs."""
    tmp = tmp.resolve()
    env = fixed_env()
    runtime_tmp = tmp / "runtime-tmp"
    runtime_tmp.mkdir()
    env["TMPDIR"] = str(runtime_tmp)
    repo = tmp / "repo"
    base_sha, head_sha = build_repo(repo, env)
    scratch = tmp / "session-scratch"
    scratch.mkdir()
    spec = tmp / "spec.txt"
    spec.write_bytes(SPEC.read_bytes())
    common = ["--repo", str(repo), "--base", BASE_REF, "--spec", str(spec), "--scratch", str(scratch)]
    _checked(run_script(script, env, "preflight", "--repo", str(repo), "--base", BASE_REF,
                        "--test-cmd", "true", "--scratch", str(scratch)), "preflight")
    paths = artifact_paths(script, env, repo)
    for phase, report in (("sweep", PHASE1_REPORT), ("hunt", PHASE2_REPORT)):
        _checked(run_script(script, env, "dossier", phase, *common), f"dossier {phase}")
        paths[phase].write_bytes(report.read_bytes())
        _checked(run_script(script, env, "record", phase, "--repo", str(repo), "--base", BASE_REF,
                            "--spec", str(spec)), f"record {phase}")
    result = _checked(run_script(script, env, "dossier", "arbitrate", *common), "dossier arbitrate")
    dossier = Path(result.stdout.strip().splitlines()[-1])
    checkouts = [line[len("CHECKOUT: "):] for line in result.stderr.splitlines()
                 if line.startswith("CHECKOUT: ")]
    return {
        "dossier": dossier.read_bytes(),
        "checkout": checkouts[0] if checkouts else None,
        "run_dir": str(paths["arbitrate"].parent),
        "tmp_root": str(tmp),
        "commits": (base_sha, head_sha),
        "repo": repo,
        "env": env,
    }


# Fixed-width placeholders: each is a constant string, so the normalized size never depends on the
# length of a temporary path; a commit ID becomes a 40-character placeholder, the width it replaces.
CHECKOUT_PLACEHOLDER = "<CHECKOUT>"
RUN_DIR_PLACEHOLDER = "<RUN-DIR>"
TMP_ROOT_PLACEHOLDER = "<TMP-ROOT>"
COMMIT_PLACEHOLDER = "<COMMIT-ID" + "-" * 29 + ">"
COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")


def normalize(text: bytes, *, checkout: str | None, run_dir: str, tmp_root: str,
              commits: tuple[str, ...]) -> bytes:
    """The one normalization of the baseline and of the current dossier. It replaces, in this
    order and nothing else:
      1. the phase's checkout path, with <CHECKOUT>;
      2. the run directory, with <RUN-DIR>;
      3. the temporary root every fixture path lives under, with <TMP-ROOT>;
      4. each fixture commit ID (40 lowercase hexadecimal characters), with a 40-character placeholder.
    Longer paths go first because the later ones are their prefixes. Every placeholder is free of
    the values it replaces, so a second pass changes nothing."""
    for commit in commits:
        if not COMMIT_ID.match(commit):
            raise ValueError(f"not a 40-character commit ID: {commit!r}")
    for value, placeholder in ((checkout, CHECKOUT_PLACEHOLDER), (run_dir, RUN_DIR_PLACEHOLDER),
                               (tmp_root, TMP_ROOT_PLACEHOLDER)):
        if value:
            text = text.replace(value.encode(), placeholder.encode())
    for commit in commits:
        text = text.replace(commit.encode(), COMMIT_PLACEHOLDER.encode())
    return text
