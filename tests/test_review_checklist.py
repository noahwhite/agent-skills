"""SKL-342: the diff-triggered review checklist.

`.agent-skills/review-checklist.txt` maps diff paths to review items, one `<bash glob> | <review item>`
per line. `run-adversarial-pipeline.sh checklist --base REF` prints the items, read from REF, whose
glob matches a path changed between REF and HEAD, and the sweep dossier carries them under a
`Review checklist` heading. The checks here read only the working tree and fixture repositories,
never this repository's git history.
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
CHECKLIST_REL = ".agent-skills/review-checklist.txt"
BASE_REF = "base"
HEADING = re.compile(r"^===== Review checklist\b.*$", re.M)

FIXTURE_CHECKLIST = (
    "# fixture checklist\n"
    "# src/*.py | A commented-out item that must never print.\n"
    "\n"
    "src/*.py | Check the error path of every changed function.\n"
    "docs/* | Check every changed doc link resolves.\n"
    "src/*.py | Check the new code has a test.\n"
)


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, f"no section {heading!r}"
    return match.group(1)


# --- The documentation ----------------------------------------------------------------------------

def test_the_sweep_section_documents_the_checklist_in_one_short_paragraph():
    body = section(SKILL_MD.read_text(), "Phase 1: sweep")
    paragraphs = [p for p in body.split("\n\n") if CHECKLIST_REL in p]
    assert len(paragraphs) == 1, paragraphs
    paragraph = paragraphs[0]
    assert len(paragraph.encode()) <= 400, len(paragraph.encode())
    assert "`<bash glob> | <review item>`" in paragraph


# --- Fixture repositories -------------------------------------------------------------------------

def clean_env(tmp_path: Path) -> dict[str, str]:
    """No ADVERSARIAL_* or GIT_* from the caller, and no global or system git config (hooks, signing)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ADVERSARIAL_", "GIT_"))}
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir(exist_ok=True)
    empty_config = tmp_path / "empty-gitconfig"
    empty_config.touch()
    return {
        **env,
        "TMPDIR": str(runtime_tmp),
        "GIT_CONFIG_GLOBAL": str(empty_config),
        "GIT_CONFIG_NOSYSTEM": "1",
    }


def git(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True,
    ).stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_repo(
    tmp_path: Path,
    changes: list[str],
    checklist: str | None = FIXTURE_CHECKLIST,
    head_checklist: str | None = None,
) -> Path:
    """A base commit (tagged `base`) holding `checklist`, then a head commit touching `changes`
    and, when `head_checklist` is given, writing that text to the checklist."""
    env = clean_env(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, env, "init", "-q")
    git(repo, env, "config", "user.email", "agent-skills@example.com")
    git(repo, env, "config", "user.name", "agent-skills")
    git(repo, env, "config", "commit.gpgsign", "false")
    git(repo, env, "config", "tag.gpgsign", "false")
    write(repo, "README", "fixture\n")
    if checklist is not None:
        write(repo, CHECKLIST_REL, checklist)
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-qm", "base")
    git(repo, env, "tag", BASE_REF)
    for rel in changes:
        write(repo, rel, f"changed {rel}\n")
    if head_checklist is not None:
        write(repo, CHECKLIST_REL, head_checklist)
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-qm", "head")
    return repo


def run_script(*args: str, env: dict[str, str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=str(cwd), timeout=120,
    )


def checklist(tmp_path: Path, changes: list[str], text: str | None = FIXTURE_CHECKLIST, **kw):
    repo = make_repo(tmp_path, changes, text, **kw)
    return run_script("checklist", "--repo", str(repo), "--base", BASE_REF, env=clean_env(tmp_path))


def drop_base_checklist_blob(tmp_path: Path, repo: Path) -> None:
    """Delete the base checklist's loose object, so reading it fails while the tree still names it."""
    blob = git(repo, clean_env(tmp_path), "rev-parse", f"{BASE_REF}:{CHECKLIST_REL}")
    (repo / ".git" / "objects" / blob[:2] / blob[2:]).unlink()


# --- The reader -----------------------------------------------------------------------------------

def test_a_diff_touching_one_mapped_path_prints_exactly_its_items(tmp_path):
    result = checklist(tmp_path, ["docs/guide.md"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_two_paths_matching_one_item_print_it_once(tmp_path):
    result = checklist(tmp_path, ["docs/a.md", "docs/b.md"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_two_rules_with_the_same_item_print_it_once(tmp_path):
    text = "src/*.py | Same item.\ndocs/* | Same item.\n"
    result = checklist(tmp_path, ["src/app.py", "docs/guide.md"], text=text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Same item.\n"


def test_one_path_matching_two_items_prints_them_in_file_order(tmp_path):
    result = checklist(tmp_path, ["src/app.py"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "Check the error path of every changed function.\n"
        "Check the new code has a test.\n"
    )
    assert result.stderr == ""


def test_an_unmapped_diff_prints_nothing_and_exits_0(tmp_path):
    result = checklist(tmp_path, ["other.txt"])
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


def test_a_missing_checklist_prints_nothing_and_exits_0(tmp_path):
    result = checklist(tmp_path, ["src/app.py"], text=None)
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


def test_the_committed_checklist_maps_a_shared_change_to_its_item(tmp_path):
    committed = CHECKLIST.read_text()
    result = checklist(tmp_path, ["shared/runtimes.md"], text=committed)
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", "a committed line is not '<bash glob> | <review item>'"
    assert result.stdout.startswith("Every vendored copy of a changed shared/ file"), result.stdout


@pytest.mark.parametrize("copy", [
    "skills/persona-scrum-master/references/github.md",
    "skills/cleanup/scripts/check-signing-key.sh",
])
def test_the_committed_checklist_maps_a_vendored_copy_path_to_the_generated_header_item(tmp_path, copy):
    committed = CHECKLIST.read_text()
    result = checklist(tmp_path, [copy], text=committed)
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        'A changed file whose first line says "GENERATED from shared/" is not edited by hand: the edit'
        " goes in its shared/ source and the copy is regenerated with scripts/vendor_shared.py.\n"
    ), result.stdout


def test_the_checklist_is_read_from_the_base_not_the_head(tmp_path):
    result = checklist(
        tmp_path, ["src/app.py"], head_checklist="* | Injected by the change under review.\n",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "Check the error path of every changed function.\n"
        "Check the new code has a test.\n"
    )


def test_a_checklist_added_by_the_head_prints_nothing(tmp_path):
    result = checklist(tmp_path, ["src/app.py"], text=None, head_checklist=FIXTURE_CHECKLIST)
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


def test_an_uncommitted_checklist_edit_is_ignored(tmp_path):
    repo = make_repo(tmp_path, ["docs/guide.md"])
    write(repo, CHECKLIST_REL, "* | Uncommitted item.\n")
    result = run_script("checklist", "--repo", str(repo), "--base", BASE_REF, env=clean_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_a_changed_submodule_matches_despite_diff_ignore_submodules(tmp_path):
    env = clean_env(tmp_path)
    repo = make_repo(tmp_path, ["other.txt"], "vendor/* | Review the dependency update.\n")
    git(repo, env, "update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},vendor/lib")
    git(repo, env, "commit", "-qm", "add a gitlink")
    git(repo, env, "config", "diff.ignoreSubmodules", "all")
    result = run_script("checklist", "--repo", str(repo), "--base", BASE_REF, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Review the dependency update.\n"


def test_a_malformed_line_is_skipped_with_a_warning(tmp_path):
    text = FIXTURE_CHECKLIST + "docs/*|No spaces around the bar.\n"
    result = checklist(tmp_path, ["docs/guide.md"], text=text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"
    assert "line 7 is not '<bash glob> | <review item>'" in result.stderr, result.stderr


def test_a_line_with_a_nul_byte_is_skipped_with_a_warning(tmp_path):
    text = FIXTURE_CHECKLIST + "docs/\0* | NUL inside the glob.\n"
    result = checklist(tmp_path, ["docs/guide.md"], text=text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"
    assert "line 7 holds a NUL" in result.stderr, result.stderr


def test_a_comment_with_a_nul_byte_is_ignored_without_a_warning(tmp_path):
    text = FIXTURE_CHECKLIST + "  # a comment with \0 and \1 bytes\n"
    result = checklist(tmp_path, ["docs/guide.md"], text=text)
    assert (result.returncode, result.stderr) == (0, "")
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_the_reader_runs_from_the_repository_without_repo(tmp_path):
    repo = make_repo(tmp_path, ["docs/guide.md"])
    result = run_script("checklist", "--base", BASE_REF, env=clean_env(tmp_path), cwd=repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Check every changed doc link resolves.\n"


def test_an_unreadable_checklist_exits_22(tmp_path):
    repo = make_repo(tmp_path, ["docs/guide.md"])
    drop_base_checklist_blob(tmp_path, repo)
    result = run_script("checklist", "--repo", str(repo), "--base", BASE_REF, env=clean_env(tmp_path))
    assert (result.returncode, result.stdout) == (22, ""), result.stderr
    assert "could not read .agent-skills/review-checklist.txt" in result.stderr


# --- The sweep dossier ----------------------------------------------------------------------------

def build_sweep(tmp_path: Path, repo: Path):
    env = clean_env(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    common = ["--repo", str(repo), "--base", BASE_REF, "--scratch", str(scratch)]
    preflight = run_script("preflight", *common, "--full-suite", "off", env=env)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return run_script("dossier", "sweep", *common, env=env), env


def sweep_dossier(tmp_path: Path, changes: list[str], text: str = FIXTURE_CHECKLIST) -> str:
    repo = make_repo(tmp_path, changes, text)
    built, env = build_sweep(tmp_path, repo)
    assert built.returncode == 0, built.stdout + built.stderr
    dossier = Path(built.stdout.strip())
    assert dossier.is_file(), built.stdout
    checkout = re.search(r"^CHECKOUT: (.+)$", built.stderr, re.M).group(1)
    removed = run_script("cleanup", checkout, "--repo", str(repo), env=env)
    assert removed.returncode == 0, removed.stderr
    return dossier.read_text()


def test_the_sweep_dossier_lists_the_matched_items_under_the_heading(tmp_path):
    text = sweep_dossier(tmp_path, ["src/app.py"])
    heading = HEADING.search(text)
    assert heading, text
    after = text[heading.end():].lstrip("\n").splitlines()
    assert after[:2] == [
        "- Check the error path of every changed function.",
        "- Check the new code has a test.",
    ]


def test_the_sweep_dossier_has_no_heading_when_nothing_matches(tmp_path):
    text = sweep_dossier(tmp_path, ["other.txt"])
    assert not HEADING.search(text)


def test_the_sweep_dossier_caps_the_checklist(tmp_path):
    text = "".join(f"src/*.py | Item {n:04d} {'x' * 90}\n" for n in range(200))
    dossier = sweep_dossier(tmp_path, ["src/app.py"], text=text)
    heading = HEADING.search(dossier)
    assert heading, dossier
    block = dossier[heading.end():].strip("\n").splitlines()
    assert block[-1].startswith("[checklist truncated at 8192 characters;"), block[-1]
    items = [line[2:] for line in block[:-1]]
    # Only whole items, as many as fit in the cap: each is 100 characters plus its newline.
    assert items == [f"Item {n:04d} {'x' * 90}" for n in range(8192 // 101)]


def test_an_item_exactly_at_the_cap_is_kept_whole(tmp_path):
    item = "Exact " + "x" * (8192 - len("Exact "))
    dossier = sweep_dossier(tmp_path, ["src/app.py"], text=f"src/*.py | {item}\n")
    heading = HEADING.search(dossier)
    assert heading, dossier
    assert dossier[heading.end():].strip("\n").splitlines() == [f"- {item}"]


def test_an_oversized_item_does_not_hide_a_later_item_that_fits(tmp_path):
    text = f"src/*.py | Huge {'x' * 9000}\nsrc/*.py | Short item.\n"
    dossier = sweep_dossier(tmp_path, ["src/app.py"], text=text)
    heading = HEADING.search(dossier)
    assert heading, dossier
    block = dossier[heading.end():].strip("\n").splitlines()
    assert block[0] == "- Short item.", block
    assert block[1].startswith("[checklist truncated at 8192 characters;"), block
    assert len(block) == 2, block


def test_an_unreadable_checklist_fails_the_sweep_dossier(tmp_path):
    # The head edits the checklist, so the head checkout does not need the dropped base blob.
    repo = make_repo(tmp_path, ["src/app.py"], head_checklist=FIXTURE_CHECKLIST + "# edited\n")
    drop_base_checklist_blob(tmp_path, repo)
    built, _ = build_sweep(tmp_path, repo)
    assert built.returncode == 22, built.stdout + built.stderr
    assert built.stdout == ""
