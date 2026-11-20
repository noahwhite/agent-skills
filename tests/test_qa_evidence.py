"""SKL-386: the QA evidence README skeleton generator.

`shared/qa-evidence.py` writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata and
verdict table `skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts
and evidence instead of authoring the structure. The lint assertions reuse the doc-lint helpers of
`tests/test_skills.py` rather than restating them, so the skeleton stays safe as that lint grows.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_skills import BRITISH_ARTIFACT, EM_DASH, stray_terms

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "shared" / "qa-evidence.py"

DEFAULT_EVIDENCE_DIR = "docs/qa-evidence"
TABLE_HEADER = "| Item | Verdict | Evidence |"
TABLE_SEPARATOR = "| --- | --- | --- |"
# The verdict values qa-verification records; the skeleton must never pre-fill one.
VERDICT_WORDS = (
    "verified",
    "failed",
    "correct by design",
    "out of scope",
    "not covered",
    "pending owner ruling",
)
SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def generate(
    tmp_path: Path,
    key: str,
    items: tuple[str, ...] = (),
    path: str | None = None,
    evidence_dir: str | None = None,
) -> Path:
    args = ["--key", key]
    for item in items:
        args += ["--item", item]
    if path is not None:
        args += ["--path", path]
    if evidence_dir is not None:
        args += ["--evidence-dir", evidence_dir]
    res = run(tmp_path, *args)
    assert res.returncode == 0, res.stderr
    return tmp_path / (evidence_dir or DEFAULT_EVIDENCE_DIR) / key / "README.md"


def metadata_lines(text: str) -> list[str]:
    """The metadata lines between the round heading and the verdict table."""
    lines = text.splitlines()
    start = lines.index("## QA round 1") + 1
    end = lines.index(TABLE_HEADER)
    return [line for line in lines[start:end] if line.strip()]


def table_rows(text: str) -> list[str]:
    """The rows under the verdict table's header and separator, in order."""
    lines = text.splitlines()
    header = lines.index(TABLE_HEADER)
    assert lines[header + 1] == TABLE_SEPARATOR, lines[header + 1]
    return lines[header + 2:]


def cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip("|").split("|")]


def test_creates_the_readme_under_the_default_evidence_dir(tmp_path):
    readme = generate(tmp_path, "SKL-386")
    assert readme == tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    assert readme.is_file()
    lines = readme.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# SKL-386 QA evidence"
    assert lines[2] == "## QA round 1"


def test_a_directory_without_a_readme_receives_one(tmp_path):
    (tmp_path / "docs" / "qa-evidence" / "SKL-59").mkdir(parents=True)
    readme = generate(tmp_path, "SKL-59")
    assert readme.is_file()
    assert readme.read_text(encoding="utf-8").startswith("# SKL-59 QA evidence\n")


def test_refuses_an_existing_readme_and_leaves_it_byte_identical(tmp_path):
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    original = "# handwritten\n\n- Verified: 2026-11-20\n"
    readme.write_bytes(original.encode())
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(readme) in res.stderr
    assert readme.read_bytes() == original.encode()
    created = sorted(p.relative_to(tmp_path) for p in readme.parent.rglob("*"))
    assert created == [Path("docs/qa-evidence/SKL-386/README.md")]


@pytest.mark.parametrize("key", ["../escape", "SKL-abc", "skl-1"])
def test_rejects_a_key_that_is_not_a_story_key_and_writes_nothing(tmp_path, key):
    res = run(tmp_path, "--key", key, "--item", "AC1")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert key in res.stderr
    assert sorted(tmp_path.rglob("*")) == []


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (None, ["Date:", "Fixtures:"]),
        ("deployed", ["Date:", "Fixtures:", "Path: deployed", "Environment:", "Build:"]),
        ("no-deployment", ["Date:", "Fixtures:", "Path: no-deployment", "Target:"]),
        ("spike", ["Date:", "Fixtures:", "Path: spike", "Target:"]),
    ],
    ids=["no-path", "deployed", "no-deployment", "spike"],
)
def test_metadata_lines_follow_the_path(tmp_path, path, expected):
    text = generate(tmp_path, "SKL-386", path=path).read_text(encoding="utf-8")
    assert metadata_lines(text) == expected


def test_no_row_without_an_item(tmp_path):
    text = generate(tmp_path, "SKL-386").read_text(encoding="utf-8")
    assert table_rows(text) == []


def test_one_ordered_row_per_item_with_empty_verdict_and_evidence(tmp_path):
    items = (
        "AC1 - one generator",
        "AC2 - skeleton content",
        "DoD 2 - tests written and passing",
    )
    text = generate(tmp_path, "SKL-386", items).read_text(encoding="utf-8")
    rows = table_rows(text)
    assert [cells(row) for row in rows] == [[item, "", ""] for item in items]


def test_a_non_default_evidence_dir_is_used(tmp_path):
    readme = generate(tmp_path, "SKL-1", evidence_dir="tmp-evidence")
    assert readme == tmp_path / "tmp-evidence" / "SKL-1" / "README.md"
    assert readme.is_file()
    assert not (tmp_path / "docs").exists()


@pytest.mark.parametrize("path", [None, "deployed", "no-deployment", "spike"])
def test_the_skeleton_is_lint_safe(tmp_path, path):
    text = generate(tmp_path, "SKL-386", ("AC1 - one generator", "DoD 1 - a label"), path=path).read_text(
        encoding="utf-8"
    )
    assert EM_DASH not in text
    assert BRITISH_ARTIFACT not in text.lower()
    offenders = [line for line in text.splitlines() if stray_terms(line)]
    assert not offenders, offenders
    lower = text.lower()
    assert [word for word in VERDICT_WORDS if word in lower] == []


@pytest.mark.parametrize("path", [None, "deployed", "no-deployment", "spike"])
def test_each_prose_line_holds_one_sentence(tmp_path, path):
    text = generate(tmp_path, "SKL-386", ("AC1 - one generator",), path=path).read_text(encoding="utf-8")
    prose = [line for line in text.splitlines() if line.strip() and not line.startswith(("#", "|"))]
    for line in prose:
        assert len(SENTENCE_END.findall(line)) <= 1, line
