"""SKL-386: the QA evidence README skeleton generator.

`shared/qa-evidence.py` writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata and
verdict table `skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts
and evidence instead of authoring the structure. The lint assertions reuse the doc-lint helpers of
`tests/test_skills.py` rather than restating them, so the skeleton stays safe as that lint grows.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import pytest
from markdown_it import MarkdownIt

from test_skills import (
    BRITISH_ARTIFACT,
    CANONICAL_RE,
    EM_DASH,
    PROFILE_REF_RE,
    RUNTIME_TERMS,
    STRAY_RE,
    profile_refs,
    resolve_schema_path,
    stray_terms,
)

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


def run_in(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the generator with `cwd` as the target repository the profile schema is resolved from."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def directory_permissions_apply() -> bool:
    """Whether this process is subject to directory permission checks (root and some sandboxes are not)."""
    return not hasattr(os, "geteuid") or os.geteuid() != 0


def load_generator():
    """The generator as a module, so a test can interpose between its checks and its write."""
    spec = importlib.util.spec_from_file_location("qa_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree_state(root: Path) -> dict[str, bytes]:
    """Every path under `root`: a file's bytes, a directory marker, or a symlink's target."""
    state = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            state[relative] = b"<link>" + os.readlink(path).encode()
        elif path.is_dir():
            state[relative] = b"<dir>"
        else:
            state[relative] = path.read_bytes()
    return state


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
    """The cells of one table row, honouring the backslash escapes the generator writes."""
    body = row.strip()
    assert body.startswith("|") and body.endswith("|"), row
    inner = body[1:-1]
    found: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(inner):
        char = inner[index]
        if char == "\\" and index + 1 < len(inner):
            current.append(inner[index + 1])
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
    for row in table_rows(text):
        assert len(SENTENCE_END.findall(row_cells(row)[0])) <= 1, row


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
        "AC1 - verified",
        "AC1 - failed",
        "AC1 - correct by design",
        "AC1 - out of scope",
        "AC1 - not covered",
        "AC1 - pending owner ruling",
    ],
    ids=[
        "empty",
        "em-dash",
        "neutral",
        "fresh-verifier",
        "verified",
        "failed",
        "correct-by-design",
        "out-of-scope",
        "not-covered",
        "pending-owner-ruling",
    ],
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


def test_a_symlinked_story_directory_is_refused_not_followed(tmp_path):
    story = tmp_path / "docs" / "qa-evidence" / "SKL-386"
    story.parent.mkdir(parents=True)
    destination = tmp_path / "elsewhere"
    destination.mkdir()
    story.symlink_to(destination, target_is_directory=True)
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(story) in res.stderr
    assert list(destination.iterdir()) == []


def test_a_readme_that_appears_before_the_write_is_never_overwritten(tmp_path, monkeypatch):
    generator = load_generator()
    concurrent = "# written by the other invocation\n"
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    real_check = generator.existing_target_problem

    def racing_check(descriptor, target):
        problem = real_check(descriptor, target)
        if problem is None:
            readme.parent.mkdir(parents=True, exist_ok=True)
            readme.write_text(concurrent, encoding="utf-8")
        return problem

    monkeypatch.setattr(generator, "existing_target_problem", racing_check)
    code = generator.main(["--key", "SKL-386", "--evidence-dir", str(tmp_path / "docs" / "qa-evidence")])
    assert code == 1
    assert readme.read_text(encoding="utf-8") == concurrent
    assert list(readme.parent.glob(".qa-evidence-*")) == []


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


def test_the_canonical_clean_neutral_phrase_is_not_a_stray_term(tmp_path):
    label = "AC5 - a clean, neutral reviewer"
    assert stray_terms(label) == []
    text = generate(tmp_path, "SKL-386", (label,)).read_text(encoding="utf-8")
    assert row_cells(table_rows(text)[0])[0] == label


@pytest.mark.parametrize(
    "label",
    [
        "AC1 - todowrite is enforced",
        "AC2 - the .opencode/agents tree is read",
        "AC3 - mcp__github is not called",
    ],
    ids=["todowrite", "opencode-path", "mcp-tool"],
)
def test_a_label_carrying_a_runtime_term_is_refused(tmp_path, label):
    assert RUNTIME_TERMS.search(label), label
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == before


def test_a_label_carrying_an_unresolvable_profile_reference_is_refused(tmp_path):
    label = "AC3 - profile.not.a.key stays unset"
    before = tree_state(tmp_path)
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == before


def test_a_label_carrying_a_resolvable_profile_reference_is_accepted(tmp_path):
    label = "AC2 - profile.qa.evidence_dir names the directory"
    assert profile_refs(label) == ["qa.evidence_dir"]
    schema = json.loads((ROOT / "profile" / "schema.json").read_text(encoding="utf-8"))
    assert "evidence_dir" in schema["properties"]["qa"]["properties"]
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0])[0] == label


def test_british_spelling_is_refused_outside_the_evidence_tree(tmp_path):
    label = "AC1 - the " + BRITISH_ARTIFACT + " path"
    assert BRITISH_ARTIFACT in label.lower()
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "tmp-evidence"))
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_british_spelling_is_accepted_inside_the_evidence_tree(tmp_path):
    label = "AC1 - the " + BRITISH_ARTIFACT + " path"
    text = generate(tmp_path, "SKL-386", (label,)).read_text(encoding="utf-8")
    assert row_cells(table_rows(text)[0])[0] == label


def test_a_verdict_word_inside_a_longer_word_is_accepted(tmp_path):
    label = "AC4 - an unverified commit is refused"
    text = generate(tmp_path, "SKL-386", (label,)).read_text(encoding="utf-8")
    assert row_cells(table_rows(text)[0])[0] == label


@pytest.mark.parametrize("key", ["FAILED-1", "VERIFIED-1", "NEUTRAL-1"])
def test_a_key_the_doc_lint_rejects_is_refused(tmp_path, key):
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", key)
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert key in res.stderr
    assert tree_state(tmp_path) == before


@pytest.mark.parametrize("value", ["", " ", "\t"])
def test_an_empty_evidence_dir_is_refused(tmp_path, value):
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "SKL-386", "--evidence-dir", value)
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == before


def test_a_failed_write_leaves_a_partial_readme_that_a_retry_refuses(tmp_path, monkeypatch):
    generator = load_generator()
    target = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"

    def failing_write(_descriptor, _data):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(generator.os, "write", failing_write)
    assert generator.publish(target, "# SKL-386 QA evidence\n") is False
    assert target.exists()
    monkeypatch.undo()
    assert generator.publish(target, "# SKL-386 QA evidence\n") is False
    target.unlink()
    assert generator.publish(target, "# SKL-386 QA evidence\n") is True
    assert target.read_text(encoding="utf-8") == "# SKL-386 QA evidence\n"


def test_an_unencodable_label_is_refused_and_nothing_is_written(tmp_path, monkeypatch, capsys):
    generator = load_generator()
    monkeypatch.chdir(tmp_path)
    assert generator.main(["--key", "SKL-386", "--item", "AC1 - \udcff"]) == 1
    err = capsys.readouterr().err
    assert len(err.splitlines()) == 1, err
    assert tree_state(tmp_path) == {}
    assert generator.main(["--key", "SKL-386", "--item", "AC1 - one generator"]) == 0
    assert (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()


def test_the_documented_equals_form_passes_one_argument(tmp_path):
    res = run(tmp_path, "--key", "SKL-386", "--item=AC1 - one generator", "--path=no-deployment")
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0]) == ["AC1 - one generator", "", ""]


def test_the_copied_lint_rules_are_the_lint_rules():
    generator = load_generator()
    assert generator.EM_DASH == EM_DASH
    assert generator.BRITISH_ARTIFACT == BRITISH_ARTIFACT
    assert generator.STRAY_RE.pattern == STRAY_RE.pattern
    assert generator.CANONICAL_RE.pattern == CANONICAL_RE.pattern
    assert generator.RUNTIME_TERMS_RE.pattern == RUNTIME_TERMS.pattern
    assert generator.PROFILE_REF_RE.pattern == PROFILE_REF_RE.pattern
    for word in VERDICT_WORDS:
        assert generator.VERDICT_RE.search(word), word


REF_PARITY_LABELS = (
    "AC1 - profile.qa.evidence_dir is set",
    "AC1 - `profile.qa.evidence_dir.` is set",
    "AC1 - profile.git.integration_branch.. is unset",
    "AC1 - **profile.git.integration_branch** is set",
    "AC1 - *profile.git.integration_branch* is set",
    "AC1 - [profile.git.integration_branch](guide.md)",
    "AC1 - [a guide](profile.not.a.key)",
    "AC1 - <img alt=\"profile.not.a.key\">",
    "AC1 - <!-- profile.not.a.key -->",
    "AC1 - ![alt profile.not.a.key](img.png)",
    "AC1 - profile.qa.evidence&#95;dir is set",
    "AC1 - profile.qa.evidence\\*_dir",
    "AC1 - profile.review.* is the section",
    "AC1 - profile.review.*[0].name is set",
    "AC1 - [profile.x] is literal",
)


@pytest.mark.parametrize("label", REF_PARITY_LABELS)
def test_reference_extraction_matches_the_doc_lint(label):
    generator = load_generator()
    cleaned = generator.clean_label(label)
    lint_sees = profile_refs(f"| {cleaned} |  |  |")
    assert generator.ref_candidates(generator.visible_text(cleaned)) == lint_sees, label


VALID_REFS = (
    "qa.evidence_dir",
    "git.branch_prefixes.feature",
    "overlays.qa-verification",
    "review.*",
    "environments[].preauthorized",
    "git.integration_branch",
)
INVALID_REFS = (
    "not.a.key",
    "extra",
    "review.*[0].name",
)


@pytest.mark.parametrize("ref", VALID_REFS)
def test_a_profile_reference_the_lint_resolves_is_accepted(tmp_path, ref):
    label = f"AC1 - profile.{ref} is set"
    assert profile_refs(label) == [ref.removesuffix(".")]
    assert resolve_schema_path(ref.removesuffix(".")) and not ref.startswith("extra")
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0])[0] == label


@pytest.mark.parametrize("ref", INVALID_REFS)
def test_a_profile_reference_the_lint_rejects_is_refused(tmp_path, ref):
    label = f"AC1 - profile.{ref} is set"
    lint_rejects = ref.startswith("extra") or not resolve_schema_path(ref)
    assert lint_rejects, ref
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_backtick_wrapped_unresolvable_reference_is_refused(tmp_path):
    label = "AC1 - `profile.not.a.key` is set"
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_dotted_identifier_inside_a_backtick_span_is_literal(tmp_path):
    label = "AC1 - `profile.qa.evidence_dir.` is set"
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0])[0] == label


def test_an_html_attribute_reference_is_refused(tmp_path):
    label = 'AC1 - <img alt="profile.not.a.key"> is set'
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_link_wrapped_reference_is_literal_text(tmp_path):
    label = "AC1 - [profile.git.integration_branch](guide.md) is set"
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_reference_in_link_syntax_is_scanned_literally(tmp_path):
    label = "AC1 - [the guide](profile.not.a.key)"
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_an_emphasis_wrapped_reference_is_literal_text(tmp_path):
    label = "AC1 - **profile.git.integration_branch** is set"
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_trailing_doubled_dot_does_not_slip_through(tmp_path):
    label = "AC1 - profile.git.integration_branch.. is unset"
    assert profile_refs(label) == ["git.integration_branch."]
    assert not resolve_schema_path("git.integration_branch.")
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_an_entity_is_rendered_literally(tmp_path):
    label = "AC1 - verif&#105;ed"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0])[0] == label


def test_a_consumer_directory_without_a_schema_accepts_a_profile_reference(tmp_path):
    label = "AC1 - profile.qa.evidence_dir is set"
    res = run_vendored(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0])[0] == label


def test_an_absolute_path_inside_the_evidence_tree_keeps_the_spelling_exemption(tmp_path):
    label = "AC1 - the " + BRITISH_ARTIFACT + " path"
    evidence = tmp_path / "docs" / "qa-evidence"
    res = run_in(tmp_path, "--key", "SKL-386", "--item", label, "--evidence-dir", str(evidence))
    assert res.returncode == 0, res.stderr
    assert (evidence / "SKL-386" / "README.md").is_file()


def test_a_dotdot_path_out_of_the_evidence_tree_loses_the_spelling_exemption(tmp_path):
    label = "AC1 - the " + BRITISH_ARTIFACT + " path"
    res = run_in(tmp_path, "--key", "SKL-386", "--item", label, "--evidence-dir", "docs/qa-evidence/../outside")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_key_with_the_british_spelling_is_refused_outside_the_evidence_tree(tmp_path):
    key = BRITISH_ARTIFACT.upper() + "-1"
    res = run_in(tmp_path, "--key", key, "--evidence-dir", "tmp-evidence")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert tree_state(tmp_path) == {}


def test_a_key_with_the_british_spelling_is_accepted_inside_the_evidence_tree(tmp_path):
    key = BRITISH_ARTIFACT.upper() + "-1"
    res = run_in(tmp_path, "--key", key)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "docs" / "qa-evidence" / key / "README.md").is_file()


def test_an_existing_readme_is_named_before_any_label_is_validated(tmp_path):
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - failed")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(readme) in res.stderr
    assert "item label" not in res.stderr


def test_a_newline_in_the_path_cannot_break_the_one_line_diagnostic(tmp_path):
    readme = tmp_path / "a\nb" / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run(tmp_path, "--key", "SKL-386", "--evidence-dir", "a\nb")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "\\n" in res.stderr
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


@pytest.mark.parametrize(
    ("label", "rendered"),
    [
        ("AC1 - a | b", "AC1 - a | b"),
        ("AC1 - a \\| b", "AC1 - a \\| b"),
        ("**AC1** - bold", "**AC1** - bold"),
    ],
    ids=["pipe", "backslash-pipe", "emphasis"],
)
def test_the_rendered_table_holds_three_cells_with_the_label_text(tmp_path, label, rendered):
    text = generate(tmp_path, "SKL-386", (label,)).read_text(encoding="utf-8")
    parser = MarkdownIt("commonmark").enable("table")
    assert any(token.type == "table_open" for token in parser.parse(text))
    html = parser.render(text)
    assert html.count("<td>") == 3, html
    assert f"<td>{rendered}</td>" in html, html


def test_a_nested_working_directory_finds_the_repository_schema(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text(
        (ROOT / "profile" / "schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    sub = tmp_path / "sub"
    sub.mkdir()
    label = "AC1 - profile.not.a.key is set"
    res = run_in(sub, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert not (tmp_path / "evidence").exists()


def test_a_nested_working_directory_resolves_the_default_evidence_dir_against_the_root(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text("{}\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    label = "AC1 - the " + BRITISH_ARTIFACT + " path"
    res = run_in(sub, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()
    assert not (sub / "docs").exists()


def test_a_nested_working_directory_detects_an_existing_readme_at_the_root(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text("{}\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run_in(sub, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(readme) in res.stderr
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


def test_a_broken_schema_is_named_instead_of_skipping_the_reference_check(tmp_path):
    (tmp_path / "profile").mkdir()
    broken = tmp_path / "profile" / "schema.json"
    broken.write_text("{not json", encoding="utf-8")
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.any.key")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "schema.json" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_an_existing_readme_is_named_before_the_key_content_lint(tmp_path):
    readme = tmp_path / "docs" / "qa-evidence" / "FAILED-1" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run(tmp_path, "--key", "FAILED-1", "--item", "AC1 - one generator")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(readme) in res.stderr
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


def test_a_multi_sentence_label_is_refused(tmp_path):
    label = "AC1 - first sentence. second sentence."
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "more than one sentence" in res.stderr
    assert tree_state(tmp_path) == before


def test_a_dotted_identifier_is_not_a_sentence_boundary(tmp_path):
    label = "AC1 - profile.qa.evidence_dir and version 1.2 are set"
    res = run_in(ROOT, "--key", "SKL-386", "--item", label, "--evidence-dir", str(tmp_path / "evidence"))
    assert res.returncode == 0, res.stderr


def test_an_option_looking_key_is_named_by_key_validation(tmp_path):
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "-oops")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "-oops" in res.stderr
    assert tree_state(tmp_path) == before


def test_a_schema_that_is_not_an_object_is_refused(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text("[]\n", encoding="utf-8")
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.any.key")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "not a JSON object" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_the_cell_renders_the_label_as_literal_text(tmp_path):
    label = "AC1 - **bold** and `code` and [link](guide.md)"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    text = (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").read_text(encoding="utf-8")
    parser = MarkdownIt("commonmark").enable("table")
    html = parser.render(text)
    assert f"<td>{label}</td>" in html, html


def test_a_dash_leading_item_reaches_validation_in_the_space_form(tmp_path):
    space = run(tmp_path, "--key", "SKL-386", "--item", "-blocked")
    assert space.returncode == 0, space.stderr
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0]) == ["-blocked", "", ""]


def test_a_dash_leading_item_matches_the_equals_form(tmp_path):
    equal = run(tmp_path, "--key", "SKL-386", "--item=-blocked", "--evidence-dir", "equal")
    space = run(tmp_path, "--key", "SKL-386", "--item", "-blocked", "--evidence-dir", "space")
    assert equal.returncode == 0, equal.stderr
    assert space.returncode == 0, space.stderr
    equal_text = (tmp_path / "equal" / "SKL-386" / "README.md").read_text(encoding="utf-8")
    space_text = (tmp_path / "space" / "SKL-386" / "README.md").read_text(encoding="utf-8")
    assert equal_text == space_text


def test_a_line_separator_in_the_path_cannot_break_the_one_line_diagnostic(tmp_path):
    evidence = "a\u2028b"
    readme = tmp_path / evidence / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run(tmp_path, "--key", "SKL-386", "--evidence-dir", evidence)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "u2028" in res.stderr.lower()
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


def test_a_symlinked_ancestor_is_refused_not_followed(tmp_path):
    destination = tmp_path / "elsewhere"
    destination.mkdir()
    (tmp_path / "docs").symlink_to(destination, target_is_directory=True)
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert str(tmp_path / "docs" / "qa-evidence" / "SKL-386") in res.stderr
    assert list(destination.rglob("*")) == []


def test_the_destination_checkout_owns_the_schema_check(tmp_path):
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    (outer / "profile").mkdir()
    (outer / "profile" / "schema.json").write_text(
        (ROOT / "profile" / "schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    inner = outer / "inner"
    (inner / ".git").mkdir(parents=True)
    label = "AC1 - profile.not.a.key is set"
    res = run_in(inner, "--key", "SKL-386", "--item", label, "--evidence-dir", str(outer / "docs" / "qa-evidence"))
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert not (outer / "docs").exists()


def test_a_tilde_pair_is_escaped_literally(tmp_path):
    label = "AC1 - ~~struck~~ text"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    text = (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").read_text(encoding="utf-8")
    assert r"\~\~struck\~\~" in text
    assert row_cells(table_rows(text)[0])[0] == label


def test_a_branching_schema_shape_does_not_raise():
    generator = load_generator()
    assert generator.deref({"allOf": [True]}, {}) == {"allOf": [True]}
    assert generator.deref({"allOf": [{"$ref": "#/$defs/gone"}]}, {}) is None


def test_a_boolean_schema_property_is_an_unresolved_reference(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text(
        json.dumps({"type": "object", "properties": {"check": True}}), encoding="utf-8"
    )
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.check[] is set")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "profile.check[]" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_a_figure_abbreviation_is_not_a_sentence_boundary(tmp_path):
    label = "AC1 - compares Fig. 2 with Fig. 3"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("separator", ["\u000b", "\u000c", "\u001c", "\u001d", "\u001e", "\u0085", "\u2029"])
def test_every_line_separator_is_escaped_in_a_path_diagnostic(tmp_path, separator):
    evidence = f"a{separator}b"
    readme = tmp_path / evidence / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run(tmp_path, "--key", "SKL-386", "--evidence-dir", evidence)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


def test_a_readme_symlink_is_named_as_a_symlink(tmp_path):
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    destination = tmp_path / "elsewhere.md"
    readme.symlink_to(destination)
    res = run(tmp_path, "--key", "SKL-386")
    assert res.returncode == 1
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert res.stderr == f"error: {readme} is a symlink; refusing to follow it\n"
    assert not destination.exists()


def test_an_abbreviation_does_not_count_as_a_sentence_boundary(tmp_path):
    label = "AC1 - set e.g. config."
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    assert row_cells(table_rows(readme.read_text(encoding="utf-8"))[0])[0] == label


def test_a_dollar_pair_is_escaped_literally(tmp_path):
    label = "AC1 - cost $x$ today"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr
    text = (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").read_text(encoding="utf-8")
    assert r"\$x\$" in text
    assert row_cells(table_rows(text)[0])[0] == label


def test_a_broken_schema_is_ignored_when_no_label_names_a_reference(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text("{not json", encoding="utf-8")
    res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()


def test_a_concurrent_writer_that_wins_the_create_is_not_overwritten(tmp_path, monkeypatch):
    generator = load_generator()
    target = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    target.parent.mkdir(parents=True)
    concurrent = "# written by the other invocation\n"
    real_check = generator.existing_target_problem

    def racing_check(descriptor, path):
        problem = real_check(descriptor, path)
        if problem is None:
            path.write_text(concurrent, encoding="utf-8")
        return problem

    monkeypatch.setattr(generator, "existing_target_problem", racing_check)
    assert generator.publish(target, "# ours\n") is False
    assert target.read_text(encoding="utf-8") == concurrent
    assert list(target.parent.glob(".qa-evidence-*")) == []


def test_a_non_utf8_path_still_reports_success(tmp_path):
    raw = os.fsencode(tmp_path) + b"/ev\xff"
    os.mkdir(raw)
    evidence = os.fsdecode(raw)
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--key", "SKL-386", "--evidence-dir", evidence],
        cwd=tmp_path,
        capture_output=True,
    )
    assert res.returncode == 0, res.stderr
    assert (Path(evidence) / "SKL-386" / "README.md").is_file()


def test_a_relative_cross_checkout_destination_uses_the_outer_schema(tmp_path):
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    (outer / "profile").mkdir()
    (outer / "profile" / "schema.json").write_text(
        (ROOT / "profile" / "schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    inner = outer / "inner"
    (inner / ".git").mkdir(parents=True)
    label = "AC1 - profile.not.a.key is set"
    res = run_in(inner, "--key", "SKL-386", "--item", label, "--evidence-dir", "../docs/qa-evidence")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert not (outer / "docs").exists()


def test_without_a_checkout_an_ancestor_schema_does_not_move_the_output(tmp_path):
    root = tmp_path / "root"
    (root / "profile").mkdir(parents=True)
    (root / "profile" / "schema.json").write_text("{}\n", encoding="utf-8")
    child = root / "child"
    child.mkdir()
    res = run_in(child, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 0, res.stderr
    assert (child / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()
    assert not (root / "docs").exists()


def test_a_dangling_schema_reference_is_refused(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text(
        json.dumps({"type": "object", "properties": {"x": {"$ref": "#/$defs/missing"}}}), encoding="utf-8"
    )
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.x is set")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "profile.x" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_an_array_reference_without_items_is_refused(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text(
        json.dumps({"type": "object", "properties": {"x": {"type": "array"}}}), encoding="utf-8"
    )
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.x[] is set")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert not (tmp_path / "docs").exists()


def test_an_unpunctuated_second_sentence_is_refused(tmp_path):
    label = "Create the file. Check the rows"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr


@pytest.mark.parametrize("ending", ["!", "?"])
def test_a_single_sentence_with_a_strong_terminator_is_accepted(tmp_path, ending):
    label = f"AC1 - one generator{ending}"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("ending", ["!", "?"])
def test_a_second_strong_terminator_is_refused(tmp_path, ending):
    label = f"AC1 - first{ending} second"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr


def test_a_regular_readme_under_a_symlinked_ancestor_is_refused_as_unsafe(tmp_path):
    destination = tmp_path / "elsewhere"
    readme = destination / "qa-evidence" / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    (tmp_path / "docs").symlink_to(destination, target_is_directory=True)
    res = run(tmp_path, "--key", "SKL-386")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert res.stderr == f"error: cannot open {tmp_path / 'docs' / 'qa-evidence' / 'SKL-386'}: a path component is a file or symlink\n"
    assert "already exists" not in res.stderr
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


def test_a_quoted_second_sentence_is_refused(tmp_path):
    label = 'AC1 - "First sentence." "Second sentence."'
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_a_profile_reference_before_a_second_sentence_does_not_hide_it(tmp_path):
    label = "AC1 - set profile.git.integration_branch. Then push."
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_an_abbreviation_before_a_second_sentence_does_not_hide_it(tmp_path):
    label = "AC1 - do this, etc. Then push."
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_a_write_only_story_directory_can_receive_the_readme(tmp_path):
    story = tmp_path / "docs" / "qa-evidence" / "SKL-386"
    story.mkdir(parents=True)
    story.chmod(0o300)
    try:
        res = run(tmp_path, "--key", "SKL-386", "--item", "AC1 - one generator")
        assert res.returncode == 0, res.stderr
        assert (story / "README.md").is_file()
    finally:
        story.chmod(0o700)


def test_a_schema_whose_properties_is_not_a_mapping_is_a_one_line_refusal(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text('{"properties": null}', encoding="utf-8")
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.any.key is set")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "profile.any.key" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_a_profile_word_that_is_not_a_reference_does_not_load_the_schema(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").write_text("{ not json", encoding="utf-8")
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - xprofile.broken and profile.md stay literal")
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()


def test_a_readme_directory_is_refused_as_a_non_regular_file(tmp_path):
    readme = tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md"
    readme.mkdir(parents=True)
    res = run(tmp_path, "--key", "SKL-386")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "is not a regular file" in res.stderr
    assert "already exists" not in res.stderr
    assert readme.is_dir()


def test_the_whole_skeleton_is_exactly_the_expected_text(tmp_path):
    readme = generate(tmp_path, "SKL-386", ("AC1 - one generator", "AC2 - exact content"), path="deployed")
    assert readme.read_text(encoding="utf-8") == (
        "# SKL-386 QA evidence\n"
        "\n"
        "## QA round 1\n"
        "\n"
        "Date:\n"
        "Fixtures:\n"
        "Path: deployed\n"
        "Environment:\n"
        "Build:\n"
        "\n"
        "| Item | Verdict | Evidence |\n"
        "| --- | --- | --- |\n"
        "| AC1 - one generator |  |  |\n"
        "| AC2 - exact content |  |  |\n"
    )


def test_an_unsupported_path_is_refused(tmp_path):
    before = tree_state(tmp_path)
    res = run(tmp_path, "--key", "SKL-386", "--path", "deployed-ish")
    assert res.returncode == 2, res.stderr
    assert tree_state(tmp_path) == before


@pytest.mark.parametrize("abbreviation", ["e.g.", "i.e."])
def test_a_two_letter_abbreviation_never_ends_a_sentence(tmp_path, abbreviation):
    label = f"AC1 - parse {abbreviation} Config maps"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr


def test_a_full_width_full_stop_separates_sentences(tmp_path):
    label = "AC1 - first sentence\u3002second sentence\u3002"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr


@pytest.mark.parametrize("terminator", ["\uff1f", "\uff01", "\u061f", "\uff61"])
def test_another_script_terminator_separates_sentences(tmp_path, terminator):
    label = f"AC1 - first{terminator}second{terminator}"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr
    assert not (tmp_path / "docs").exists()


@pytest.mark.parametrize(
    "label",
    [
        "AC1 - greet Mr. Smith.",
        "AC1 - cite J. R. Hartley.",
        "AC1 - 1. the generator writes the skeleton",
        "AC1 - step 4. the readme is refused",
        "AC1 - item 2. the table lists every label",
    ],
)
def test_a_title_in_an_initial_or_a_numbered_item_is_not_a_sentence_end(tmp_path, label):
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("control", ["\x1b", "\x07", "\x08"])
def test_a_control_character_in_a_label_is_refused(tmp_path, control):
    label = f"AC1 - the {control}[31mred button"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "control character" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_a_control_character_in_a_path_cannot_reach_the_terminal(tmp_path):
    evidence = "ev\x1b[31mRED"
    readme = tmp_path / evidence / "SKL-386" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# handwritten\n", encoding="utf-8")
    res = run(tmp_path, "--key", "SKL-386", "--evidence-dir", evidence)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "\x1b" not in res.stderr
    assert readme.read_text(encoding="utf-8") == "# handwritten\n"


def test_a_stdout_closed_at_startup_still_creates_the_readme(tmp_path):
    command = f"'{sys.executable}' '{SCRIPT}' --key SKL-386 1>&-"
    res = subprocess.run(["bash", "-c", command], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()


@pytest.mark.parametrize("label", [
    "AC1 - set profile.git.integration_branch. then push.",
    "AC1 - set profile.git.integration_branch. Then push.",
    "AC1 - set profile.git.integration_branch. 2 files",
])
def test_a_reference_keeps_its_sentence_final_dot(tmp_path, label):
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr


@pytest.mark.parametrize("mark", ["\u200b", "\ufeff", "\u00ad", "\u200c", "\u202e"])
def test_an_invisible_format_character_in_a_label_is_refused(tmp_path, mark):
    label = f"AC1 - veri{mark}fied"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "invisible format character" in res.stderr
    assert not (tmp_path / "docs").exists()


def test_a_numbered_item_that_starts_a_new_sentence_is_refused(tmp_path):
    label = "AC1 - set item 5. Then push"
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr


def test_a_figure_before_a_new_sentence_is_refused(tmp_path):
    label = "AC1 - the first part ends here Fig. The second sentence runs on."
    res = run(tmp_path, "--key", "SKL-386", "--item", label)
    assert res.returncode == 1, res.stderr
    assert "more than one sentence" in res.stderr


def test_a_symlinked_git_marker_is_not_a_checkout_root(tmp_path):
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    inner = outer / "inner"
    inner.mkdir()
    (inner / ".git").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    res = run_in(inner, "--key", "SKL-386", "--item", "AC1 - one generator")
    assert res.returncode == 0, res.stderr
    assert (outer / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()
    assert not (inner / "docs").exists()


def test_a_removed_working_directory_is_a_one_line_refusal(tmp_path):
    gone = tmp_path / "gone"
    gone.mkdir()
    command = f"cd '{gone}' && rm -rf '{gone}' && exec '{sys.executable}' '{SCRIPT}' --key SKL-386"
    res = subprocess.run(["bash", "-c", command], capture_output=True, text=True)
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr


@pytest.mark.skipif(not directory_permissions_apply(), reason="this process bypasses directory permissions")
def test_an_unsearchable_evidence_directory_is_a_one_line_refusal(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    evidence.chmod(0o600)
    try:
        res = run(tmp_path, "--key", "SKL-386", "--evidence-dir", str(evidence))
        assert res.returncode == 1, res.stderr
        assert len(res.stderr.splitlines()) == 1, res.stderr
        assert res.stderr.startswith("error: ")
    finally:
        evidence.chmod(0o700)


def test_a_non_regular_schema_path_is_refused(tmp_path):
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "schema.json").mkdir()
    res = run_in(tmp_path, "--key", "SKL-386", "--item", "AC1 - profile.any.key is set")
    assert res.returncode == 1, res.stderr
    assert len(res.stderr.splitlines()) == 1, res.stderr
    assert "not a regular file" in res.stderr
    assert not (tmp_path / "docs").exists()


@pytest.mark.skipif(not directory_permissions_apply(), reason="this process bypasses directory permissions")
def test_an_unsearchable_story_directory_is_a_one_line_refusal(tmp_path):
    story = tmp_path / "docs" / "qa-evidence" / "SKL-386"
    story.mkdir(parents=True)
    story.chmod(0o600)
    try:
        res = run(tmp_path, "--key", "SKL-386")
        assert res.returncode == 1, res.stderr
        assert len(res.stderr.splitlines()) == 1, res.stderr
    finally:
        story.chmod(0o700)


def test_a_closed_stdout_pipe_still_creates_the_readme(tmp_path):
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        res = subprocess.run(
            [sys.executable, str(SCRIPT), "--key", "SKL-386"],
            cwd=tmp_path,
            stdout=write_fd,
            stderr=subprocess.PIPE,
            text=True,
        )
    finally:
        os.close(write_fd)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "docs" / "qa-evidence" / "SKL-386" / "README.md").is_file()


def test_an_abbreviated_option_is_refused(tmp_path):
    res = run(tmp_path, "--key", "SKL-386", "--pa", "spike")
    assert res.returncode == 2, res.stderr
    assert tree_state(tmp_path) == {}
