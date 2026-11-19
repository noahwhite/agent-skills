"""The pruning-candidates script lists retire or keep proposals and never changes the repository.

Each test builds its own git repository with dated commits, because a shallow CI checkout has
no history to measure "untouched since" against (SKL-345).
"""

import hashlib
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

TESTS = f"tests untouched since {SINCE}"
REFERENCES = "reference files uncited at this commit"
RULES = f"rules uncited at this commit, unchanged since {SINCE}"

# An outer git environment (GIT_DIR, GIT_INDEX_FILE) or global configuration (excludes, hooks,
# templates) must not leak into the fixture.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def git(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(ENV)
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
    path.write_text(text, encoding="utf-8")


def append(repo: Path, rel: str, text: str) -> None:
    with (repo / rel).open("a", encoding="utf-8") as handle:
        handle.write(text)


def commit(repo: Path, date: str, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message, date=date)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()
    git(repo, "init", "-q", "--template=")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")  # an inherited signing config must not break the fixture
    git(repo, "config", "core.hooksPath", str(hooks))

    write(repo, "tests/test_old.py", "def test_old():\n    assert True\n")
    write(repo, "tests/test_new.py", "def test_new():\n    assert True\n")
    write(repo, "shared/README.md", "Sources for the vendored references.\n")
    write(repo, "shared/cited.md", "# Cited\n")
    write(repo, "shared/orphan.md", "# Orphan\n")
    write(repo, "shared/rules.md", "# Rules\n\n" + STALE_RULE + PINNED_RULE + "- An ordinary bullet.\n")
    write(repo, "skills/alpha/SKILL.md", "Read references/cited.md and (references/rules.md).\n")
    commit(repo, OLD, "old")

    pin = "label the gearbox with its owner and the date it was last oiled"
    write(repo, "tests/test_new.py", f"PIN = {pin!r}\n\ndef test_new():\n    assert PIN\n")
    append(repo, "shared/rules.md", FRESH_RULE)
    commit(repo, NEW, "new")
    return repo


def run(cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True,
        env=env or ENV,
    )


def snapshot(repo: Path) -> dict[str, str]:
    """Hash every file in the repository, .git included."""
    return {
        str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(repo.rglob("*"))
        if path.is_file()
    }


def sections(output: str) -> dict[str, list[str]]:
    """Map each category heading to its count line and its rows; every block must be well formed."""
    blocks = output.split("\n\n")
    assert blocks[0].splitlines()[0].startswith("Pruning candidates")
    found = {}
    for block in blocks[1:]:
        lines = block.splitlines()
        heading, _, count = lines[0].rpartition(": ")
        assert count.isdigit(), lines[0]
        assert all(line.startswith("- ") for line in lines[1:]), block
        assert len(lines) - 1 == int(count), block
        found[heading] = lines
    assert len(found) == 3, output
    return found


def category(repo: Path, heading: str, since: str = SINCE, cwd: Path | None = None) -> list[str]:
    result = run(cwd or repo, "--since", since)
    assert result.returncode == 0, result.stderr
    return sections(result.stdout)[heading]


def test_header_names_commit_and_since(repo: Path) -> None:
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    head = git(repo, "rev-parse", "HEAD").strip()
    assert result.stdout.splitlines()[:3] == [
        "Pruning candidates (proposals only; the owner decides, nothing is removed)",
        f"commit: {head}",
        f"since: {SINCE}",
    ]


def test_tests_untouched_since_date(repo: Path) -> None:
    lines = category(repo, TESTS)
    assert lines[0] == f"{TESTS}: 1"
    assert lines[1].startswith("- tests/test_old.py")
    assert "last change 2024-01-15" in lines[1]
    assert "proposal: keep" in lines[1]


def test_reference_files_uncited_at_commit(repo: Path) -> None:
    lines = category(repo, REFERENCES)
    assert lines[0] == f"{REFERENCES}: 1"
    assert lines[1].startswith("- shared/orphan.md")
    assert "references/orphan.md" in lines[1]
    assert "proposal: retire" in lines[1]


def test_rules_uncited_at_commit_and_unchanged_since_date(repo: Path) -> None:
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 1"
    assert lines[1].startswith("- shared/rules.md:3")
    assert "last change 2024-01-15" in lines[1]
    assert "frobnicate the widget" in lines[1]
    assert "drifts out of tolerance" in lines[1]  # the evidence carries the whole rule
    assert "proposal: retire" in lines[1]


def test_zero_counts_are_explicit(repo: Path) -> None:
    write(repo, "skills/alpha/SKILL.md", "Read references/cited.md, references/orphan.md and references/rules.md.\n")
    commit(repo, NEW, "cite every reference")
    output = run(repo, "--since", "2023-01-01").stdout
    found = sections(output)
    assert found["tests untouched since 2023-01-01"] == ["tests untouched since 2023-01-01: 0"]
    assert found[REFERENCES] == [f"{REFERENCES}: 0"]
    assert found["rules uncited at this commit, unchanged since 2023-01-01"] == [
        "rules uncited at this commit, unchanged since 2023-01-01: 0"
    ]


def test_rule_continuation_line_counts_as_a_change(repo: Path) -> None:
    text = (repo / "shared" / "rules.md").read_text()
    text = text.replace("drifts out of tolerance", "drifts out of its tolerance band")
    (repo / "shared" / "rules.md").write_text(text)
    commit(repo, NEW, "touch the continuation line")
    assert category(repo, RULES)[0] == f"{RULES}: 0"


def test_run_from_a_subdirectory_matches_the_root(repo: Path) -> None:
    root = run(repo, "--since", SINCE)
    sub = run(repo / "tests", "--since", SINCE)
    assert sub.returncode == 0, sub.stderr
    assert sub.stdout == root.stdout


def test_run_writes_nothing(repo: Path) -> None:
    before = snapshot(repo)
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    assert snapshot(repo) == before
    assert git(repo, "status", "--porcelain", "--untracked-files=all") == ""


def test_shallow_clone_is_refused(repo: Path, tmp_path: Path) -> None:
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow)],
        check=True, capture_output=True, env=ENV,
    )
    result = run(shallow, "--since", SINCE)
    assert result.returncode == 2
    assert "shallow" in result.stderr
    assert result.stdout == ""


def test_partial_clone_is_refused_without_fetching(repo: Path, tmp_path: Path) -> None:
    git(repo, "config", "uploadpack.allowFilter", "true")
    partial = tmp_path / "partial"
    subprocess.run(
        ["git", "clone", "-q", "--no-checkout", "--filter=blob:none", f"file://{repo}", str(partial)],
        check=True, capture_output=True, env=ENV,
    )
    before = snapshot(partial)
    result = run(partial, "--since", SINCE)
    assert result.returncode == 2
    assert "partial clone" in result.stderr
    assert result.stdout == ""
    assert snapshot(partial) == before


def test_a_backdated_later_commit_does_not_hide_a_change(repo: Path) -> None:
    write(repo, "tests/test_old.py", "def test_old():\n    assert 1\n")
    commit(repo, NEW, "change the old test")
    write(repo, "tests/test_old.py", "def test_old():\n    assert 2\n")
    commit(repo, OLD, "a later commit with a backdated clock")
    assert category(repo, TESTS) == [f"{TESTS}: 0"]


def test_paths_are_literal_and_unquoted(repo: Path) -> None:
    write(repo, "tests/test_x.py", "def test_x():\n    assert True\n")
    commit(repo, NEW, "a recent test")
    write(repo, "tests/test_[x].py", "def test_brackets():\n    assert True\n")
    write(repo, "tests/test_é.py", "def test_accent():\n    assert True\n")
    commit(repo, OLD, "old tests with unusual names")
    lines = category(repo, TESTS)
    assert lines[0] == f"{TESTS}: 3"
    assert sorted(line.split(" | ")[0] for line in lines[1:]) == [
        "- tests/test_[x].py", "- tests/test_old.py", "- tests/test_é.py"
    ]


def test_non_utf8_locale_still_reports(repo: Path) -> None:
    write(repo, "tests/test_é.py", "def test_accent():\n    assert True\n")
    commit(repo, OLD, "an old test with a non-ASCII name")
    env = {k: v for k, v in ENV.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env.update(LC_ALL="C", LANG="C", PYTHONUTF8="0")
    result = run(repo, "--since", SINCE, env=env)
    assert result.returncode == 0, result.stderr
    assert "- tests/test_é.py" in result.stdout


def test_a_citation_must_name_the_whole_path(repo: Path) -> None:
    append(repo, "skills/alpha/SKILL.md", "See ../beta/references/orphan.md and references/orphan.md.bak.\n")
    commit(repo, NEW, "near-miss citations")
    lines = category(repo, REFERENCES)
    assert lines[0] == f"{REFERENCES}: 1"
    assert lines[1].startswith("- shared/orphan.md")


def test_ignore_revs_config_does_not_change_the_result(repo: Path, tmp_path: Path) -> None:
    text = (repo / "shared" / "rules.md").read_text()
    (repo / "shared" / "rules.md").write_text(text.replace("drifts out of tolerance", "drifts out of its tolerance band"))
    commit(repo, NEW, "touch the continuation line")
    ignore = tmp_path / "ignore-revs"
    ignore.write_text(git(repo, "rev-parse", "HEAD"))
    git(repo, "config", "blame.ignoreRevsFile", str(ignore))
    assert category(repo, RULES)[0] == f"{RULES}: 0"


def test_a_list_item_in_a_code_fence_is_not_a_rule(repo: Path) -> None:
    append(repo, "shared/rules.md", "\n```markdown\n- ⛔ Example only: a rule written inside a fenced code block.\n```\n")
    commit(repo, OLD, "a fenced example")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 1"
    assert lines[1].startswith("- shared/rules.md:3")


def test_nested_items_belong_to_their_rule(repo: Path) -> None:
    text = (repo / "shared" / "rules.md").read_text()
    child = "  - Check the sprocket gauge twice before you start.\n"
    (repo / "shared" / "rules.md").write_text(text.replace(STALE_RULE, STALE_RULE + child))
    commit(repo, OLD, "a nested item")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 1"
    assert "sprocket gauge twice" in lines[1]

    text = (repo / "shared" / "rules.md").read_text()
    (repo / "shared" / "rules.md").write_text(text.replace("gauge twice", "gauge three times"))
    commit(repo, NEW, "change the nested item")
    assert category(repo, RULES)[0] == f"{RULES}: 0"


@pytest.mark.parametrize(
    "rule",
    [
        "- ⛔ Lazy rule opening line.\nthe lazily continued tail of this rule carries the pinned words.\n",
        "- ⛔ Loose rule opening line.\n\n  the loosely continued tail of this rule carries the pinned words.\n",
    ],
)
def test_a_pin_on_any_continuation_line_counts(repo: Path, rule: str) -> None:
    tail = rule.splitlines()[-1].strip()
    append(repo, "shared/rules.md", "\n" + rule)
    write(repo, "tests/test_pins.py", f"PIN = {tail!r}\n")
    commit(repo, OLD, "a continued rule and its pin")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 1"
    assert lines[1].startswith("- shared/rules.md:3")


def test_window_is_exactly_forty_characters(repo: Path) -> None:
    forty = "abcdefghij klmnopqrst uvwxyzabcd efghijk"  # 40 characters of the first rule
    thirty_nine = "zyxwvutsrq ponmlkjihg fedcbazyxw vutsrq"  # 39 characters of the second
    assert (len(forty), len(thirty_nine)) == (40, 39)
    append(repo, "shared/rules.md", f"\n- ⛔ Start {forty} end.\n- ⛔ Start {thirty_nine} end.\n")
    write(repo, "tests/test_window.py", f"A = {forty!r}\nB = {thirty_nine!r}\n")
    commit(repo, OLD, "window rules")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 2"
    assert "zyxwvutsrq" in lines[2]


def test_short_and_empty_rules_are_never_cited(repo: Path) -> None:
    # A rule with no 40-character run cannot share one with a test or a skill, so even a test that
    # quotes it whole does not cite it.
    append(repo, "shared/rules.md", "\n- ⛔ Oil it.\n- ⛔\n")
    write(repo, "tests/test_short.py", "NOTE = 'Oil it.'\n")
    commit(repo, OLD, "short rules")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 3"
    assert any('"Oil it."' in line for line in lines[1:])
    assert any('""' in line for line in lines[1:])


@pytest.mark.parametrize("value", ["last week", "2026-02-30", "2026-1-9"])
def test_since_must_be_a_canonical_date(repo: Path, value: str) -> None:
    result = run(repo, "--since", value)
    assert result.returncode == 2
    assert "YYYY-MM-DD" in result.stderr
    assert result.stdout == ""


def test_real_checkout_reports_or_refuses_a_shallow_clone() -> None:
    result = run(ROOT, "--since", "2026-01-01")
    shallow = git(ROOT, "rev-parse", "--is-shallow-repository").strip() == "true"
    if shallow:
        assert result.returncode == 2 and "shallow" in result.stderr
        return
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1] == f"commit: {git(ROOT, 'rev-parse', 'HEAD').strip()}"
    sections(result.stdout)


def test_a_promisor_remote_spelled_yes_is_still_refused(repo: Path, tmp_path: Path) -> None:
    git(repo, "config", "uploadpack.allowFilter", "true")
    partial = tmp_path / "partial"
    subprocess.run(
        ["git", "clone", "-q", "--no-checkout", "--filter=blob:none", f"file://{repo}", str(partial)],
        check=True, capture_output=True, env=ENV,
    )
    assert "extensions.partialclone" not in git(partial, "config", "--list").lower()  # only the remote marks it
    git(partial, "config", "remote.origin.promisor", "yes")
    before = snapshot(partial)
    result = run(partial, "--since", SINCE)
    assert result.returncode == 2
    assert "partial clone" in result.stderr
    assert snapshot(partial) == before


def test_log_follow_config_does_not_change_the_result(repo: Path) -> None:
    write(repo, "tests/test_source.py", "def test_source():\n    assert True\n")
    commit(repo, NEW, "a recent test")
    git(repo, "mv", "tests/test_source.py", "tests/test_renamed.py")
    commit(repo, OLD, "a backdated rename")
    expected = run(repo, "--since", SINCE).stdout
    assert "- tests/test_renamed.py |" in expected  # the path, not its rename history, is measured
    git(repo, "config", "log.follow", "true")
    git(repo, "config", "log.showSignature", "true")
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected


def test_a_change_merged_from_a_side_branch_counts(repo: Path) -> None:
    main = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    git(repo, "checkout", "-qb", "side")
    write(repo, "tests/test_old.py", "def test_old():\n    assert 'side'\n")
    commit(repo, NEW, "change on side")
    git(repo, "checkout", "-q", main)
    git(repo, "merge", "-q", "-s", "ours", "--no-edit", "side", date=OLD)
    assert category(repo, TESTS) == [f"{TESTS}: 0"]


def test_a_change_at_exactly_the_cutoff_is_not_before_it(repo: Path) -> None:
    write(repo, "tests/test_old.py", "def test_old():\n    assert 3\n")
    commit(repo, "2025-01-01T00:00:00+00:00", "a change at the cutoff")
    assert category(repo, TESTS) == [f"{TESTS}: 0"]
    later = "tests untouched since 2025-01-02"
    assert category(repo, later, since="2025-01-02")[0] == f"{later}: 1"


def test_a_submodule_under_tests_is_skipped(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{head},tests/submodule")
    git(repo, "commit", "-qm", "a submodule entry", date=OLD)
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    sections(result.stdout)


def test_odd_paths_stay_on_one_row(repo: Path, tmp_path: Path) -> None:
    write(repo, "tests/test_new\nline.py", "def test_newline():\n    assert True\n")
    commit(repo, OLD, "a test name with a newline")
    lines = category(repo, TESTS)
    assert lines[0] == f"{TESTS}: 2"
    assert any(line.startswith("- tests/test_new\\x0aline.py |") for line in lines[1:])

    spaced = tmp_path / "clone "
    subprocess.run(["git", "clone", "-q", f"file://{repo}", str(spaced)], check=True, capture_output=True, env=ENV)
    result = run(spaced, "--since", SINCE)
    assert result.returncode == 0, result.stderr


def test_a_non_utf8_path_is_read(repo: Path) -> None:
    os.makedirs(repo / "tests", exist_ok=True)
    (repo / os.fsdecode(b"tests/test_\xff.py")).write_text("def test_byte():\n    assert True\n")
    commit(repo, OLD, "a test name that is not UTF-8")
    lines = category(repo, TESTS)
    assert lines[0] == f"{TESTS}: 2"


def test_citation_boundaries(repo: Path) -> None:
    write(
        repo, "skills/alpha/SKILL.md",
        "Read references/cited.md and (./references/rules.md).\n"
        "Not citations: references/orphan.md/other, orphan.md, skills/alpha/references/orphan.md.\n",
    )
    write(repo, "skills/alpha/references/notes.md", "See references/orphan.md.\n")
    commit(repo, NEW, "near-miss citations")
    lines = category(repo, REFERENCES)
    assert lines[0] == f"{REFERENCES}: 1"
    assert lines[1].startswith("- shared/orphan.md")


def test_a_fence_closes_only_on_its_own_delimiter(repo: Path) -> None:
    append(
        repo, "shared/rules.md",
        "\n~~~markdown\n```\n- ⛔ Example only: still inside the tilde fence here.\n```\n~~~\n",
    )
    commit(repo, OLD, "a mixed fence")
    assert category(repo, RULES)[0] == f"{RULES}: 1"


def test_a_stop_sign_after_a_nested_item_is_not_lost(repo: Path) -> None:
    append(
        repo, "shared/rules.md",
        "\n- Parent opening line with no marker.\n  - A plain child item.\n\n"
        "  ⛔ The parent's own continuation after the child carries the marker.\n",
    )
    commit(repo, OLD, "a marker after a child")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 2"
    # The blank line ends the child, so the rule is the parent's and starts on the parent's line.
    assert any(
        line.startswith("- shared/rules.md:9 |") and '| "Parent opening line' in line
        and "continuation after the child carries the marker" in line
        for line in lines[1:]
    )


def test_a_nested_rule_under_a_plain_parent_is_its_own_rule(repo: Path) -> None:
    append(
        repo, "shared/rules.md",
        "\n- A plain parent item about the gearbox.\n  - ⛔ Never open the nested gearbox cover while powered.\n",
    )
    commit(repo, OLD, "a nested rule")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 2"
    assert any(line.startswith("- shared/rules.md:") and "| \"Never open the nested" in line for line in lines[1:])


def test_a_rule_shorter_than_the_window_is_never_cited(repo: Path) -> None:
    forty = "Exactly forty characters in this rule!!."
    short = "Only thirty-nine characters in a rule!."
    assert (len(forty), len(short)) == (40, 39)
    append(repo, "shared/rules.md", f"\n- ⛔ {forty}\n- ⛔ {short}\n")
    write(repo, "tests/test_forty.py", f"A = 'x{forty}x'\nB = 'x{short}x'\n")
    commit(repo, OLD, "boundary rules")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 2"  # the 40-character rule is a 40-character run of the test
    assert not any('"Exactly forty' in line for line in lines[1:])
    assert any('"Only thirty-nine' in line for line in lines[1:])


def test_since_is_required_and_accepts_year_one(repo: Path) -> None:
    missing = run(repo)
    assert missing.returncode == 2
    assert "--since" in missing.stderr
    early = run(repo, "--since", "0001-01-01")
    assert early.returncode == 0, early.stderr
    assert "since: 0001-01-01" in early.stdout


def test_an_outer_git_environment_does_not_redirect_the_run(repo: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "--template=")
    write(other, "tests/test_wrong.py", "def test_wrong():\n    assert True\n")
    git(other, "add", "-A")
    git(other, "-c", "user.name=o", "-c", "user.email=o@example.com", "commit", "-qm", "other", date=OLD)
    expected = run(repo, "--since", SINCE).stdout
    env = dict(
        ENV, GIT_DIR=str(other / ".git"), GIT_WORK_TREE=str(other), GIT_INDEX_FILE=str(other / ".git" / "index")
    )
    result = run(repo, "--since", SINCE, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected


def test_a_unicode_line_separator_does_not_shift_line_numbers(repo: Path) -> None:
    append(
        repo, "shared/rules.md",
        "\n- ⛔ A rule with a line separator inside it, written long ago.\n- ⛔ The rule after it.\n",
    )
    commit(repo, OLD, "a rule with a line separator")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 3"
    assert any(line.startswith("- shared/rules.md:10 |") and "The rule after it." in line for line in lines[1:])


def test_replaced_and_grafted_history_is_ignored(repo: Path) -> None:
    expected = run(repo, "--since", SINCE).stdout
    head = git(repo, "rev-parse", "HEAD").strip()
    tree = git(repo, "rev-parse", "HEAD~1^{tree}").strip()
    substitute = git(repo, "commit-tree", tree, "-m", "substitute", date=OLD).strip()
    git(repo, "replace", head, substitute)
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected
    git(repo, "replace", "-d", head)

    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "grafts").write_text(f"{head}\n")
    result = run(repo, "--since", SINCE)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected


def test_a_citation_ends_at_a_delimiter(repo: Path) -> None:
    write(
        repo, "skills/alpha/SKILL.md",
        "Read references/cited.md: and references/rules.md#rules.\n"
        "Not citations: references/orphan.md+backup, references/orphan.md~, x+references/orphan.md.\n",
    )
    commit(repo, NEW, "delimited citations")
    lines = category(repo, REFERENCES)
    assert lines[0] == f"{REFERENCES}: 1"
    assert lines[1].startswith("- shared/orphan.md")


def test_a_rule_in_the_shared_readme_is_a_rule(repo: Path) -> None:
    append(repo, "shared/README.md", "\n- ⛔ Never vendor a shared source by hand into a skill directory.\n")
    commit(repo, OLD, "a rule in the README")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 2"
    assert any(line.startswith("- shared/README.md:3 |") for line in lines[1:])
    assert category(repo, REFERENCES)[0] == f"{REFERENCES}: 1"  # the README is still no reference file


def test_an_unclosed_fence_ends_with_its_list_item(repo: Path) -> None:
    append(
        repo, "shared/rules.md",
        "\n- A plain item with code:\n\n    ```\n    unclosed\n\n- ⛔ A top-level rule after the item that holds the fence.\n",
    )
    commit(repo, OLD, "an unclosed fence in an item")
    lines = category(repo, RULES)
    assert lines[0] == f"{RULES}: 2"
    assert any("A top-level rule after the item" in line for line in lines[1:])


def test_a_missing_ignore_revs_file_is_refused_before_the_report(repo: Path) -> None:
    git(repo, "config", "blame.ignoreRevsFile", "missing-ignore-revs.txt")
    result = run(repo, "--since", SINCE)
    assert result.returncode == 2
    assert "blame.ignoreRevsFile" in result.stderr and "missing-ignore-revs.txt" in result.stderr
    assert result.stdout == ""


def test_git_trace_settings_write_no_file(repo: Path, tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    env = dict(
        ENV, GIT_TRACE=str(traces / "trace"), GIT_TRACE2=str(traces / "trace2"),
        GIT_TRACE2_EVENT=str(traces / "event"), GIT_TRACE_PERFORMANCE=str(traces / "performance"),
    )
    result = run(repo, "--since", SINCE, env=env)
    assert result.returncode == 0, result.stderr
    assert list(traces.iterdir()) == []


def test_a_carriage_return_is_kept_in_paths_and_text(repo: Path) -> None:
    write(repo, "tests/test_a\r.py", "def test_cr():\n    assert True\n")
    write(
        repo, "shared/cr.md",
        "# Title\rstill line one\n\n- ⛔ Never let a carriage return shift this rule off its line.\n",
    )
    commit(repo, OLD, "carriage returns")
    assert any(line.startswith("- tests/test_a\\x0d.py |") for line in category(repo, TESTS)[1:])
    assert any(line.startswith("- shared/cr.md:3 |") for line in category(repo, RULES)[1:])


def test_punctuation_inside_a_file_name_ends_no_citation(repo: Path) -> None:
    write(
        repo, "skills/alpha/SKILL.md",
        "Read references/cited.md, then (references/rules.md).\n"
        "Not citations: references/orphan.md:backup.md, references/orphan.md,v2 and references/orphan.md!x.\n",
    )
    commit(repo, NEW, "punctuation inside names")
    lines = category(repo, REFERENCES)
    assert lines[0] == f"{REFERENCES}: 1"
    assert lines[1].startswith("- shared/orphan.md")
