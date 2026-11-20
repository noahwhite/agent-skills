"""SKL-386: the QA evidence README skeleton generator.

`shared/qa-evidence.py` writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata and
verdict table `skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts
and evidence instead of authoring the structure. The lint assertions reuse the doc-lint helpers of
`tests/test_skills.py` rather than restating them, so the skeleton stays safe as that lint grows.
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_skills import BRITISH_ARTIFACT, EM_DASH, stray_terms

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "shared" / "qa-evidence.py"
VENDORED = ROOT / "skills" / "qa-verification" / "scripts" / "qa-evidence.py"

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


def run_vendored(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VENDORED), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def load_generator():
    """The generator as a module, so a test can interpose between its checks and its write."""
    spec = importlib.util.spec_from_file_location("qa_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_state(root: Path) -> dict[str, bytes]:
    """Every file under `root`, by relative path, with its bytes."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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


def row_cells(row: str) -> list[str]:
    """The cells of one table row, honouring the escaped `\\|` the generator writes."""
    body = row.strip()
    assert body.startswith("|") and body.endswith("|"), row
    inner = body[1:-1]
    found: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(inner):
        char = inner[index]
        if char == "\\" and index + 1 < len(inner) and inner[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if char == "|":
            found.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    found.append("".join(current).strip())
    return found


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
    (tmp_path / "docs" / "notes.txt").write_text("untouched\n", encoding="utf-8")
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(readme) in res.stderr
    assert tree_state(tmp_path) == before


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
    text = generate(tmp_path, "SKL-386", ("AC1 - one generator", "DoD 1 - a label", "AC2 - a | b"), path=path).read_text(
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


@pytest.mark.parametrize(
    ("label", "rendered"),
    [
        ("AC1 - a | b", "AC1 - a | b"),
        ("AC1 - a multiline\nlabel", "AC1 - a multiline label"),
        ("AC1  -  three   spaces", "AC1 - three spaces"),
    ],
    ids=["pipe", "newline", "whitespace"],
)
def test_an_item_label_renders_as_exactly_one_cell(tmp_path, label, rendered):
    text = generate(tmp_path, "SKL-386", (label,)).read_text(encoding="utf-8")
    rows = table_rows(text)
    assert len(rows) == 1
    assert row_cells(rows[0]) == [rendered, "", ""]
    assert "## QA round 2" not in text
    assert len(rows[0].replace("\\|", "").split("|")) == 5


@pytest.mark.parametrize(
    "label",
    [
        "",
        "AC1 \u2014 a dash",
        "AC1 - neutral path",
        "AC1 - a fresh verifier",
        "DoD 1 - verified",
        "DoD 2 - out of scope",
    ],
    ids=["empty", "em-dash", "neutral", "fresh-verifier", "verified", "out-of-scope"],
)
def test_a_label_the_doc_lint_rejects_is_refused_and_nothing_is_written(tmp_path, label):
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert res.stderr.startswith("error: item label "), res.stderr
    assert tree_state(tmp_path) == before


STRAY_LABELS = (
    "then a separate clean-context adjudicator.",
    "A fresh verifier tries to refute each finding.",
    "The brief is neutral: facts only.",
    "Spawn a clean subagent in its own context.",
)


@pytest.mark.parametrize("label", STRAY_LABELS)
def test_every_label_the_stray_term_lint_rejects_is_refused(tmp_path, label):
    assert stray_terms(label), label
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert sorted(tmp_path.rglob("*")) == []


def test_a_dangling_symlink_readme_is_refused_not_followed(tmp_path):
    link = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    link.parent.mkdir(parents=True)
    destination = tmp_path / "elsewhere.md"
    link.symlink_to(destination)
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(link) in res.stderr
    assert link.is_symlink()
    assert not destination.exists()


def test_a_readme_that_appears_before_the_write_is_never_overwritten(tmp_path, monkeypatch):
    generator = load_generator()
    concurrent = "# written by the other invocation\n"
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"

    def write_concurrently(*_args, **_kwargs):
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(concurrent, encoding="utf-8")
        return "skeleton\n"

    monkeypatch.setattr(generator, "skeleton", write_concurrently)
    code = generator.main(["--key", "SKL-386", "--evidence-dir", str(tmp_path / "docs" / "qa-evidence")])
    assert code == 1
    assert readme.read_text(encoding="utf-8") == concurrent


def test_the_vendored_entry_point_creates_and_refuses_from_a_consumer_directory(tmp_path):
    manifest = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
    assert "qa-evidence.py" in manifest["executables"]["qa-verification"]
    args = ("--key", "SKL-386", "--item", "AC1 - one generator", "--path", "no-deployment")
    first = run_vendored(tmp_path, *args)
    assert first.returncode == 0, first.stderr
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    before = readme.read_bytes()
    assert metadata_lines(before.decode()) == ["Date:", "Fixtures:", "Path: no-deployment", "Target:"]
    second = run_vendored(tmp_path, *args)
    assert second.returncode == 1
    assert len(second.stderr.splitlines()) == 1, second.stderr
    assert readme.read_bytes() == before
