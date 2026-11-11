"""SKL-242: the arbitrate dossier stays at most 40% of the pre-SKL-86 baseline on a committed
synthetic fixture.

The fixture lives in tests/fixtures/dossier_size/: the text inputs, the shared builder and
normalization (dossier_fixture.py), and the pinned baseline (baseline-arbitrate.txt), which is the
normalized arbitrate dossier of the script at 21f026593944ded43af3bd6b64f16bcae441095e on this
fixture. tests/fixtures/dossier_size/capture_baseline.py regenerates that baseline from a worktree
of that commit; this test never runs it and reads only the committed baseline.
"""

import hashlib
import importlib.util
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "dossier_size"
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"

_spec = importlib.util.spec_from_file_location("dossier_fixture", FIXTURE_DIR / "dossier_fixture.py")
fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixture)

# The one definition of the marker in this test; the fixture module's copy must agree with it.
MARKER = "SYNTHETIC FIXTURE - SKL-242 - not real data"

# Measured when the fixture was first built. A change to any of these is a change to the fixture.
PINNED_FILE_SIZES = {
    "spec.txt": 2759,
    "phase1-sweep.txt": 10869,
    "phase2-hunt.txt": 7797,
    "source-base.txt": 1250,
    "source-head.txt": 3254,
    "dossier_fixture.py": 9373,
    "capture_baseline.py": 2302,
    "baseline-arbitrate.txt": 139645,
}
# The baseline's content, not only its length: a re-capture that changes any byte changes this.
PINNED_BASELINE_SHA256 = "40a98db7b3063585e5ba9521cca3e67418951c82daae8a0a4a21406ea5be2b25"
PINNED_DIFF_FILES = 25
PINNED_DIFF_BYTES = 114450
# The fixture is fully determined (content, identity, dates), so its commit IDs are too.
PINNED_COMMITS = ("78d1d146b8fd4ba772eba3dffc7cd76152d12a80", "245b05aadf8fcd5dac4d421303765e7543bc6415")


@pytest.fixture(scope="module")
def current(tmp_path_factory):
    """The arbitrate dossier the script at this head writes on the fixture, with its normalization."""
    run = fixture.arbitrate_dossier(SCRIPT, tmp_path_factory.mktemp("dossier-size"))
    run["normalized"] = normalize_like(run, run["dossier"])
    return run


def normalize_like(run, text: bytes) -> bytes:
    return fixture.normalize(text, checkout=run["checkout"], run_dir=run["run_dir"],
                             tmp_root=run["tmp_root"], commits=run["commits"])


def committed_files() -> list[Path]:
    return sorted(p for p in FIXTURE_DIR.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


# --- Fixture inputs ---------------------------------------------------------------------------

def test_every_text_input_carries_the_marker():
    assert fixture.MARKER == MARKER
    for path in fixture.TEXT_INPUTS:
        lines = path.read_text().splitlines()
        if path in fixture.REPORTS:
            assert lines[:2] == ["REVIEW-RAN: yes", MARKER], path.name
        else:
            assert lines[0] == MARKER, path.name


def test_no_fixture_file_is_collectable_by_pytest():
    collectable = [p.name for p in committed_files() if re.fullmatch(r"test_.*\.py|.*_test\.py", p.name)]
    assert collectable == []


def test_the_fixture_files_are_ascii_and_lf_only():
    for path in committed_files():
        data = path.read_bytes()
        assert data.isascii(), path.name
        assert b"\r" not in data, path.name


def test_the_fixture_file_sizes_are_pinned():
    sizes = {p.relative_to(FIXTURE_DIR).as_posix(): len(p.read_bytes()) for p in committed_files()}
    assert sizes == PINNED_FILE_SIZES


def test_the_baseline_content_is_pinned():
    assert hashlib.sha256(fixture.BASELINE.read_bytes()).hexdigest() == PINNED_BASELINE_SHA256


def test_the_spec_and_reports_are_in_their_size_ranges():
    assert 2000 <= len(fixture.SPEC.read_bytes()) <= 4000
    assert 10500 <= len(fixture.PHASE1_REPORT.read_bytes()) <= 11100
    assert 7400 <= len(fixture.PHASE2_REPORT.read_bytes()) <= 8000


# --- Deterministic fixture repository ---------------------------------------------------------

def test_the_fixture_environment_is_fixed():
    env = fixture.fixed_env({"GIT_DIR": "/elsewhere", "ADVERSARIAL_MODEL": "x", "PATH": "/bin"})
    assert "GIT_DIR" not in env and "ADVERSARIAL_MODEL" not in env
    assert env["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_ATTR_NOSYSTEM"] == "1"
    assert (env["GIT_CONFIG_COUNT"], env["GIT_CONFIG_KEY_0"], env["GIT_CONFIG_VALUE_0"]) == (
        "1", "core.attributesFile", "/dev/null")
    assert env["COLUMNS"] == "80"
    for role in ("AUTHOR", "COMMITTER"):
        assert env[f"GIT_{role}_DATE"] == "2026-01-01T00:00:00+0000"


def test_the_fixture_repository_has_two_commits_and_the_pinned_diff(current):
    repo, env = current["repo"], current["env"]
    base, head = current["commits"]
    assert base != head
    assert (base, head) == PINNED_COMMITS
    assert fixture.git(repo, env, "rev-list", "--count", "HEAD") == "2"
    assert fixture.git(repo, env, "config", "core.autocrlf") == "false"
    names, diff = fixture.fixture_diff(repo, env)
    assert names == [fixture.part_path(n) for n in range(1, fixture.PART_COUNT + 1)]
    assert len(names) == PINNED_DIFF_FILES
    assert len(diff) == PINNED_DIFF_BYTES
    assert len(diff) >= 100_000


# --- Accepted predecessors through the script -------------------------------------------------

def test_the_predecessors_hold_the_committed_reports(current):
    """The arbitrate dossier exists only because `record sweep` and `record hunt` accepted the
    committed reports; the artifacts they accepted are those reports, unchanged."""
    paths = fixture.artifact_paths(SCRIPT, current["env"], current["repo"])
    assert paths["sweep"].read_bytes() == fixture.PHASE1_REPORT.read_bytes()
    assert paths["hunt"].read_bytes() == fixture.PHASE2_REPORT.read_bytes()


# --- Normalization ----------------------------------------------------------------------------

def test_normalization_is_idempotent(current):
    baseline = fixture.BASELINE.read_bytes()
    assert normalize_like(current, current["normalized"]) == current["normalized"]
    assert normalize_like(current, baseline) == baseline


def test_no_temporary_path_or_fixture_commit_survives_normalization(current):
    leftovers = [current["tmp_root"], current["run_dir"], *current["commits"]]
    if current["checkout"]:
        leftovers.append(current["checkout"])
    for text in (current["normalized"], fixture.BASELINE.read_bytes()):
        for value in leftovers:
            assert value.encode() not in text
        assert not re.search(rb"\b[0-9a-f]{40}\b", text)
    assert current["checkout"] and current["tmp_root"] in current["checkout"]
    assert current["dossier"] != current["normalized"]


def test_normalization_leaves_spec_report_and_diff_content_unchanged(current):
    _, diff = fixture.fixture_diff(current["repo"], current["env"])
    for content in (fixture.SPEC.read_bytes(), fixture.PHASE1_REPORT.read_bytes(),
                    fixture.PHASE2_REPORT.read_bytes(), diff):
        assert normalize_like(current, content) == content
    for content in (fixture.SPEC.read_bytes(), fixture.PHASE1_REPORT.read_bytes(),
                    fixture.PHASE2_REPORT.read_bytes()):
        assert content in current["normalized"]


def test_normalization_replaces_each_value_with_its_placeholder():
    base, head = "a" * 40, "b" * 40
    text = (f"checkout /t/run/co/x\nrun /t/run/r\ntmp /t/s\nbase {base}\nhead {head}\n").encode()
    normalized = fixture.normalize(text, checkout="/t/run/co/x", run_dir="/t/run/r", tmp_root="/t",
                                   commits=(base, head))
    commit = fixture.COMMIT_PLACEHOLDER
    assert normalized == (f"checkout <CHECKOUT>\nrun <RUN-DIR>\ntmp <TMP-ROOT>/s\n"
                          f"base {commit}\nhead {commit}\n").encode()
    assert len(commit) == 40


def test_normalization_rejects_a_value_that_is_not_a_commit_id():
    with pytest.raises(ValueError):
        fixture.normalize(b"", checkout=None, run_dir="/r", tmp_root="/t", commits=("abc",))


# --- Ceiling ----------------------------------------------------------------------------------

def test_the_arbitrate_dossier_is_at_most_40_percent_of_the_baseline(current):
    baseline = fixture.BASELINE.read_bytes()
    assert len(current["normalized"]) <= math.floor(0.40 * len(baseline))


def test_the_dossier_carries_no_line_that_exists_only_inside_a_changed_hunk(current):
    _, diff = fixture.fixture_diff(current["repo"], current["env"])
    added = b"\n".join(line for line in diff.splitlines() if line.startswith(b"+"))
    baseline = fixture.BASELINE.read_bytes()
    inputs = b"".join(p.read_bytes() for p in (fixture.SPEC, *fixture.REPORTS))
    for marker in fixture.hunk_markers():
        encoded = marker.encode()
        assert encoded in added, marker
        assert encoded in baseline, marker
        assert encoded not in inputs, marker
        assert encoded not in current["normalized"], marker
