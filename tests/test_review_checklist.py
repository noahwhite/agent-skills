"""SKL-342: the diff-triggered review checklist.

`.agent-skills/review-checklist.txt` maps diff paths to review items, one `<bash glob> | <review item>`
per line. `run-adversarial-pipeline.sh checklist --base REF` prints the items whose glob matches a
path changed between REF and HEAD, and the sweep dossier carries them under a `Review checklist`
heading. The checks here read only the working tree and fixture repositories, never this
repository's git history.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST = ROOT / ".agent-skills" / "review-checklist.txt"
SKILL_DIR = ROOT / "skills" / "adversarial-review-pipeline"
SCRIPT = SKILL_DIR / "scripts" / "run-adversarial-pipeline.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
BASE_REF = "base"
LINE = re.compile(r"^(?P<glob>[^|]*\S[^|]*?) \| (?P<item>\S.*)$")

FIXTURE_CHECKLIST = (
    "# fixture checklist\n"
    "\n"
    "src/*.py | Check the error path of every changed function.\n"
    "docs/* | Check every changed doc link resolves.\n"
    "src/*.py | Check the new code has a test.\n"
)


def item_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, f"no section {heading!r}"
    return match.group(1)


# --- The committed checklist and its documentation ----------------------------------------------

def test_the_committed_checklist_has_items_in_the_documented_format():
    items = item_lines(CHECKLIST.read_text())
    assert items, "the checklist holds no item"
    for line in items:
        assert LINE.match(line), f"not '<bash glob> | <review item>': {line!r}"


def test_the_sweep_section_documents_the_checklist_in_one_short_paragraph():
    body = section(SKILL_MD.read_text(), "Phase 1: sweep")
    paragraphs = [p for p in body.split("\n\n") if ".agent-skills/review-checklist.txt" in p]
    assert len(paragraphs) == 1, paragraphs
    paragraph = paragraphs[0]
    assert len(paragraph.encode()) <= 400, len(paragraph.encode())
    assert "`<bash glob> | <review item>`" in paragraph


# --- The reader and the sweep dossier on fixture repositories -----------------------------------

def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_repo(tmp_path: Path, changes: list[str], checklist: str | None = FIXTURE_CHECKLIST) -> Path:
    """A base commit (tagged `base`) holding the checklist, then a head commit touching `changes`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "tag.gpgsign", "false")
    write(repo, "README", "fixture\n")
    if checklist is not None:
        write(repo, ".agent-skills/review-checklist.txt", checklist)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "tag", BASE_REF)
    for rel in changes:
        write(repo, rel, f"changed {rel}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "head")
    return repo


def clean_env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ADVERSARIAL_")}
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir(exist_ok=True)
    return {**env, "TMPDIR": str(runtime_tmp)}


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


def checklist(tmp_path: Path, changes: list[str], text: str | None = FIXTURE_CHECKLIST):
    repo = make_repo(tmp_path, changes, text)
    return run_script("checklist", "--repo", str(repo), "--base", BASE_REF, env=clean_env(tmp_path))


def test_a_diff_touching_one_mapped_path_prints_exactly_its_items(tmp_path):
    result = checklist(tmp_path, ["docs/guide.md"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_two_paths_matching_one_item_print_it_once(tmp_path):
    result = checklist(tmp_path, ["docs/a.md", "docs/b.md"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_one_path_matching_two_items_prints_them_in_file_order(tmp_path):
    result = checklist(tmp_path, ["src/app.py"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "Check the error path of every changed function.\n"
        "Check the new code has a test.\n"
    )


def test_an_unmapped_diff_prints_nothing_and_exits_0(tmp_path):
    result = checklist(tmp_path, ["other.txt"])
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


def test_a_missing_checklist_prints_nothing_and_exits_0(tmp_path):
    result = checklist(tmp_path, ["src/app.py"], text=None)
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


def sweep_dossier(tmp_path: Path, changes: list[str]) -> str:
    repo = make_repo(tmp_path, changes)
    env = clean_env(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    common = ["--repo", str(repo), "--base", BASE_REF, "--scratch", str(scratch)]
    preflight = run_script("preflight", *common, "--full-suite", "off", env=env)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    built = run_script("dossier", "sweep", *common, env=env)
    assert built.returncode == 0, built.stdout + built.stderr
    text = Path(built.stdout.strip()).read_text()
    checkout = re.search(r"^CHECKOUT: (.+)$", built.stderr, re.M).group(1)
    removed = run_script("cleanup", checkout, "--repo", str(repo), env=env)
    assert removed.returncode == 0, removed.stderr
    return text


def test_the_sweep_dossier_lists_the_matched_items_under_the_heading(tmp_path):
    text = sweep_dossier(tmp_path, ["src/app.py"])
    heading = re.search(r"^===== Review checklist\b.*$", text, re.M)
    assert heading, text
    after = text[heading.end():].lstrip("\n").splitlines()
    assert after[:2] == [
        "Check the error path of every changed function.",
        "Check the new code has a test.",
    ]


def test_the_sweep_dossier_has_no_heading_when_nothing_matches(tmp_path):
    text = sweep_dossier(tmp_path, ["other.txt"])
    assert "Review checklist" not in text
    assert "===== DIFF" in text  # the dossier itself was written
