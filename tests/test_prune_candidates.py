"""The pruning-candidates script lists retire or keep proposals and never changes the repository.

Each test builds its own git repository with dated commits, because a shallow CI checkout has
no history to measure "untouched since" against (SKL-345).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "prune_candidates.py"

OLD = "2024-01-15T12:00:00+00:00"
NEW = "2025-06-15T12:00:00+00:00"
SINCE = "2025-01-01"

STALE_RULE = (
    "- ⛔ Never frobnicate the widget before the sprocket assembly is calibrated.\n"
    "  Calibrate it first, or the widget drifts out of tolerance.\n"
)
PINNED_RULE = "- ⛔ Always label the gearbox with its owner and the date it was last oiled.\n"
FRESH_RULE = "- ⛔ Never paint the flywheel while it spins at full speed in the workshop.\n"


def git(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=env
    )
    return result.stdout


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def commit(repo: Path, date: str, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message, date=date)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")  # an inherited signing config must not break the fixture

    write(repo, "tests/test_old.py", "def test_old():\n    assert True\n")
    write(repo, "tests/test_new.py", "def test_new():\n    assert True\n")
    write(repo, "shared/README.md", "Sources for the vendored references.\n")
    write(repo, "shared/cited.md", "# Cited\n")
    write(repo, "shared/orphan.md", "# Orphan\n")
    write(repo, "shared/rules.md", "# Rules\n\n" + STALE_RULE + PINNED_RULE + "- An ordinary bullet.\n")
    write(repo, "skills/alpha/SKILL.md", "Read references/cited.md and references/rules.md.\n")
    commit(repo, OLD, "old")

    pin = "label the gearbox with its owner and the date it was last oiled"
    write(repo, "tests/test_new.py", f"PIN = {pin!r}\n\ndef test_new():\n    assert PIN\n")
    with (repo / "shared" / "rules.md").open("a") as handle:
        handle.write(FRESH_RULE)
    commit(repo, NEW, "new")
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True
    )


def snapshot(repo: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(repo)): path.read_bytes()
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }


def section(output: str, heading: str) -> list[str]:
    lines = output.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(heading))
    body = []
    for line in lines[start + 1 :]:
        if not line.startswith("- "):
            break
        body.append(line)
    return [lines[start], *body]


def test_header_names_commit_and_since(repo: Path) -> None:
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    head = git(repo, "rev-parse", "HEAD").strip()
    assert f"commit: {head}" in result.stdout
    assert f"since: {SINCE}" in result.stdout


def test_tests_untouched_since_date(repo: Path) -> None:
    lines = section(run(repo, "--since", SINCE).stdout, "tests untouched since")
    assert lines[0] == f"tests untouched since {SINCE}: 1"
    assert len(lines) == 2
    assert lines[1].startswith("- tests/test_old.py")
    assert "last change 2024-01-15" in lines[1]
    assert "proposal: keep" in lines[1]


def test_reference_files_uncited_at_commit(repo: Path) -> None:
    lines = section(run(repo, "--since", SINCE).stdout, "reference files uncited at this commit")
    assert lines[0] == "reference files uncited at this commit: 1"
    assert len(lines) == 2
    assert lines[1].startswith("- shared/orphan.md")
    assert "references/orphan.md" in lines[1]
    assert "proposal: retire" in lines[1]


def test_rules_uncited_at_commit_and_unchanged_since_date(repo: Path) -> None:
    lines = section(run(repo, "--since", SINCE).stdout, "rules uncited at this commit")
    assert lines[0] == f"rules uncited at this commit, unchanged since {SINCE}: 1"
    assert len(lines) == 2
    assert lines[1].startswith("- shared/rules.md:3")
    assert "last change 2024-01-15" in lines[1]
    assert "frobnicate the widget" in lines[1]
    assert "proposal: retire" in lines[1]


def test_zero_counts_are_explicit(repo: Path) -> None:
    output = run(repo, "--since", "2023-01-01").stdout
    assert "tests untouched since 2023-01-01: 0" in output
    assert "rules uncited at this commit, unchanged since 2023-01-01: 0" in output


def test_rule_continuation_line_counts_as_a_change(repo: Path) -> None:
    text = (repo / "shared" / "rules.md").read_text()
    text = text.replace("drifts out of tolerance", "drifts out of its tolerance band")
    (repo / "shared" / "rules.md").write_text(text)
    commit(repo, NEW, "touch the continuation line")
    lines = section(run(repo, "--since", SINCE).stdout, "rules uncited at this commit")
    assert lines[0].endswith(": 0")


def test_run_writes_nothing(repo: Path) -> None:
    before = snapshot(repo)
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    assert git(repo, "status", "--porcelain", "--untracked-files=all") == ""
    assert snapshot(repo) == before


def test_shallow_clone_is_refused(repo: Path, tmp_path: Path) -> None:
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow)],
        check=True, capture_output=True,
    )
    result = run(shallow, "--since", SINCE)
    assert result.returncode != 0
    assert "shallow" in result.stderr
    assert result.stdout == ""


def test_since_must_be_a_date(repo: Path) -> None:
    result = run(repo, "--since", "last week")
    assert result.returncode != 0
    assert "YYYY-MM-DD" in result.stderr
