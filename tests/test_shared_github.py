"""Contract checks for the per-story promotion mechanics in shared/github.md."""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GITHUB = ROOT / "shared" / "github.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())

# Every sentence below is load-bearing for a consumer profile selecting
# `profile.git.promotion: per-story`. Matches are whole-line (leading whitespace
# and a list marker are allowed), and the Promotion section is also pinned line
# for line below, so deleting, rewording, extending or adding to it fails this
# suite.
PER_STORY_SENTENCES = (
    # Branch construction from the release branch, with an explicit base ref.
    "Under `per-story`, build the promotion branch and its PR like this:",
    "Cut the promotion branch from `origin/<profile.git.release_branch>` with that explicit base ref, after `git fetch --prune origin`.",
    # Merge-method-dependent commit selection, identified by the story's issue key.
    "Identify the story's merged feature PR, by its issue key, with `gh pr list --state merged --base <profile.git.integration_branch> --limit 1000 --json number,headRefName,mergeCommit,commits`, and stop when the result count reaches that limit, because the list may be truncated.",
    "Keep the PR whose head branch carries the issue key as a whole token, delimited by a non-alphanumeric character or the end of the name, and stop when that leaves zero or more than one.",
    "Select, from `origin/<profile.git.integration_branch>`, only the commits that PR added:",
    "With `profile.git.merge_method` `squash`, select that PR's squash commit.",
    "With `profile.git.merge_method` `rebase`, select the commits in `origin/<profile.git.release_branch>..origin/<profile.git.integration_branch>` whose `git patch-id --stable` id matches one of the PR's own commits, and stop when the match count differs from the PR's commit count.",
    "With `profile.git.merge_method` `merge`, select that PR's merge commit.",
    "Confirm the selection reproduces that PR's own diff, by patch id: for `squash` the squash commit against `gh pr diff <number>`, for `rebase` the selected commits against the PR's commits, and for `merge` `git diff <merge>^1 <merge>` against `gh pr diff <number>`.",
    "Stop and report when any commit of that PR, from its `commits` list, has a subject that does not carry the story's issue key, because another story's change is riding along inside that PR and a squash or merge commit would carry it unnoticed.",
    "Stop and report as well when that list holds 100 commits or more, because the list is truncated there and cannot be checked whole.",
    "Record the PR number and the selected commit SHAs in the promotion PR body.",
    "Before carrying them, confirm the story's change is still present, with its merged context, on `origin/<profile.git.integration_branch>` by reverse-applying it there, running these commands from inside the repository, with `<worktree>` and `<patch>` absolute paths, with no spaces or shell metacharacters, in an existing scratch directory outside the repository: create a throwaway worktree with `git worktree add --detach <worktree> origin/<profile.git.integration_branch>`, save the diff of each selected commit `<commit>`, in the selection's original order, to a new `<patch>` with `git diff --binary --no-ext-diff --no-textconv --no-relative --src-prefix=a/ --dst-prefix=b/ -U3 <commit>^ <commit> >> <patch>`, run `git -C <worktree> apply --check -R --cached <patch>`, and remove the worktree with `git worktree remove <worktree>` whatever the check's result; the change is confirmed present only when the check exits 0 and prints no `warning:` on stdout or stderr, and it is not confirmed when the check exits 1 or prints a `warning:`, for example after a revert, a later change to the story's lines or their context, or a later rename; stop and report the story as not confirmed present, with the check's output, for a human check, and stop and report the check as failed when it exits with any other status or another of these commands fails.",
    # Carrying the selected commits onto the promotion branch.
    "Carry the selected commits onto the promotion branch by cherry-picking them one at a time in their original order, with `-m 1` when a selected commit is a merge commit, or by applying non-merge selections with `git cherry-pick -n` in order and making one commit.",
    # The promotion PR, and the explicit refusal of a whole-branch PR under per-story.
    "Run the promotion branch's local checks, push it, then open the promotion PR from it to `profile.git.release_branch` and let its CI run.",
    "A whole-branch integration-to-release PR is not used under `per-story`.",
    # Fail-closed stop, including the un-promoted-story cases.
    "Stop and report instead of carrying another story's commit or merging the integration branch into the promotion when the selection finds no commit, matches more than one feature PR, or cannot apply without an un-promoted story.",
    "A cherry-pick conflict that needs another story's commits is that stop: report the conflicting commit and the story it needs, and do not pull that story in to clear the conflict.",
    "An empty application, because a selected commit is already on the release branch, is that stop too: report the story as already promoted.",
    "A check that fails only because another story's change is absent is that stop as well.",
    # Story-scoped three-dot diff, split by mode.
    "Inspect a `whole-branch` promotion with a fresh three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...origin/<integration>`.",
    "The two-dot diff shows release-only files as deletions.",
    "Inspect a `per-story` promotion with its own story-scoped three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...<promotion-branch>`.",
    "Never inspect the whole integration branch for a `per-story` promotion.",
    # The per-story review-fix flow.
    "Under `per-story`, a valid review fix lands on a new feature branch to `profile.git.integration_branch` and merges there before its commit is carried.",
    "The stale promotion PR is then closed unmerged, and the fix is carried in this order: cut a fresh story-scoped promotion branch from the release branch under a new branch name, carry the selection recorded in the closed PR body, then select the fix PR's own commits by `profile.git.merge_method` and cherry-pick them onto the branch in their original order, with `-m 1` when one is a merge commit.",
    "The story's updated commits, the original selection plus the fix commits, are what the branch carries.",
    "Record the fix PR number in the promotion PR body when that PR merges, and select from that recorded number instead of running the discovery again, which would match a second feature PR and stop.",
    "Open a fresh promotion PR from that branch to `profile.git.release_branch`, carrying the story's updated commits.",
    "Refresh the story's pre-production evidence against that promotion head before the merge.",
    "Do not back-merge the release branch into the promotion branch, update-branch a promotion PR, or force-push one; rebuild it instead.",
)

# `none` and `whole-branch` behaviour is unchanged: every pre-existing promotion
# sentence stays, and the only edits are the two `whole-branch`-only qualifications.
UNCHANGED_SENTENCES = (
    "- `none`: trunk-based; the integration branch is the release branch and there is no promotion PR.",
    "- `whole-branch`: one promotion PR carries the whole integration branch, opened only after every story awaiting promotion is verified in its pre-production environment.",
    "Never promote a single story on its own.",
    "- Review the promotion PR's whole cumulative diff (`references/code-review.md`).",
    "⛔ Never merge the release branch into the integration branch (no back-merges), and never update-branch a promotion PR, which does the same.",
    "Resolve promotion conflicts on a separate branch.",
)

WHOLE_BRANCH_QUALIFICATIONS = (
    "- Under `whole-branch`, fixes for a promotion PR go on a new feature branch to the integration branch and flow into the promotion.",
)

# The two untouched mode bullets, byte-exact including their continuation lines, so a
# sentence smuggled into `none` or `whole-branch` fails the suite as AC8 requires.
MODE_BULLETS = (
    (
        "- `none`: trunk-based; the integration branch is the release branch and there is no promotion PR.",
    ),
    (
        "- `whole-branch`: one promotion PR carries the whole integration branch, opened only after every story awaiting promotion is verified in its pre-production environment.",
        "  Never promote a single story on its own.",
    ),
)

FENCE_RE = re.compile(r"^```.*?^```[^\n]*$", re.MULTILINE | re.DOTALL)


def section(text: str, heading: str, level: str = "##") -> str:
    """The section body, with fenced code blocks removed so a `#` line cannot spoof a heading."""
    text = FENCE_RE.sub("", text)
    match = re.search(rf"^{level} {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(rf"^#{{1,{len(level)}}} ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def has_sentence(text: str, sentence: str) -> bool:
    """True only when the sentence occupies a whole line (leading whitespace and a list marker allowed)."""
    pattern = rf"^[ \t]*(?:\d+\. |- )?{re.escape(sentence)}$"
    return re.search(pattern, text, re.MULTILINE) is not None


def missing_sentences(text: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if not has_sentence(text, sentence)]


def bullet(lines: list[str], first: str) -> list[str]:
    """The bullet whose first line is `first`, plus its indented continuation lines."""
    for index, line in enumerate(lines):
        if line == first:
            block = [line]
            for follow in lines[index + 1:]:
                if not follow.startswith("  "):
                    break
                block.append(follow)
            return block
    raise AssertionError(f"missing bullet: {first}")


def test_promotion_section_exists() -> None:
    assert GITHUB.is_file(), f"missing {GITHUB.relative_to(ROOT)}"
    assert "per-story" in section(GITHUB.read_text(), "Promotion")


def test_per_story_promotion_sentences_are_present_verbatim() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    missing = missing_sentences(body, PER_STORY_SENTENCES)
    assert not missing, "missing per-story promotion sentences:\n" + "\n".join(missing)


def test_none_and_whole_branch_promotion_sentences_are_unchanged() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    missing = missing_sentences(body, UNCHANGED_SENTENCES + WHOLE_BRANCH_QUALIFICATIONS)
    assert not missing, "changed none/whole-branch promotion sentences:\n" + "\n".join(missing)


def test_none_and_whole_branch_bullets_are_byte_exact() -> None:
    lines = section(GITHUB.read_text(), "Promotion").splitlines()
    for expected in MODE_BULLETS:
        assert bullet(lines, expected[0]) == list(expected)


def test_every_merge_method_value_has_a_selection_rule() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    values = SCHEMA["properties"]["git"]["properties"]["merge_method"]["enum"]
    assert values, "profile.git.merge_method has no enum"
    for value in values:
        pattern = rf"^[ \t]*With `profile\.git\.merge_method` `{re.escape(value)}`, select "
        assert re.search(pattern, body, re.MULTILINE), f"no per-story selection rule for merge_method {value}"


def test_fenced_heading_does_not_truncate_the_section() -> None:
    text = GITHUB.read_text()
    spoofed = text.replace(
        "## Promotion\n\n", "## Promotion\n\n```\n# Attribution\n```\n\n", 1
    )
    assert spoofed != text, "anchor missing"
    body = section(spoofed, "Promotion")
    assert not missing_sentences(body, PER_STORY_SENTENCES)


def test_deleting_or_extending_an_asserted_sentence_is_caught() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    for sentence in PER_STORY_SENTENCES + UNCHANGED_SENTENCES + WHOLE_BRANCH_QUALIFICATIONS:
        assert missing_sentences(body.replace(sentence, ""), (sentence,)) == [sentence], sentence
        line = next(line for line in body.splitlines() if line.endswith(sentence))
        appended = body.replace(line, line + " Unless a whole-branch PR is simpler.")
        assert missing_sentences(appended, (sentence,)) == [sentence], sentence

# The Promotion section pinned line for line: a smuggled bullet, a renumbered
# step, a re-indented line or an added continuation sentence fails here, which
# is what AC8's "no other promotion text changes" and the step order require.
EXPECTED_PROMOTION_SECTION = (
    '`profile.git.promotion` decides how `profile.git.integration_branch` reaches `profile.git.release_branch`:\n'
    '\n'
    '- `none`: trunk-based; the integration branch is the release branch and there is no promotion PR.\n'
    '- `whole-branch`: one promotion PR carries the whole integration branch, opened only after every story awaiting promotion is verified in its pre-production environment.\n'
    '  Never promote a single story on its own.\n'
    '- `per-story`: promote each story individually after its feature PR merges, deploy, then close the story; never batch stories.\n'
    '\n'
    'Under `per-story`, build the promotion branch and its PR like this:\n'
    '\n'
    '1. Cut the promotion branch from `origin/<profile.git.release_branch>` with that explicit base ref, after `git fetch --prune origin`.\n'
    "2. Identify the story's merged feature PR, by its issue key, with `gh pr list --state merged --base <profile.git.integration_branch> --limit 1000 --json number,headRefName,mergeCommit,commits`, and stop when the result count reaches that limit, because the list may be truncated.\n"
    '   Keep the PR whose head branch carries the issue key as a whole token, delimited by a non-alphanumeric character or the end of the name, and stop when that leaves zero or more than one.\n'
    '   Select, from `origin/<profile.git.integration_branch>`, only the commits that PR added:\n'
    "   With `profile.git.merge_method` `squash`, select that PR's squash commit.\n"
    "   With `profile.git.merge_method` `rebase`, select the commits in `origin/<profile.git.release_branch>..origin/<profile.git.integration_branch>` whose `git patch-id --stable` id matches one of the PR's own commits, and stop when the match count differs from the PR's commit count.\n"
    "   With `profile.git.merge_method` `merge`, select that PR's merge commit.\n"
    "   Confirm the selection reproduces that PR's own diff, by patch id: for `squash` the squash commit against `gh pr diff <number>`, for `rebase` the selected commits against the PR's commits, and for `merge` `git diff <merge>^1 <merge>` against `gh pr diff <number>`.\n"
    "   Stop and report when any commit of that PR, from its `commits` list, has a subject that does not carry the story's issue key, because another story's change is riding along inside that PR and a squash or merge commit would carry it unnoticed.\n"
    '   Stop and report as well when that list holds 100 commits or more, because the list is truncated there and cannot be checked whole.\n'
    '   Record the PR number and the selected commit SHAs in the promotion PR body.\n'
    "   Before carrying them, confirm the story's change is still present, with its merged context, on `origin/<profile.git.integration_branch>` by reverse-applying it there, running these commands from inside the repository, with `<worktree>` and `<patch>` absolute paths, with no spaces or shell metacharacters, in an existing scratch directory outside the repository: create a throwaway worktree with `git worktree add --detach <worktree> origin/<profile.git.integration_branch>`, save the diff of each selected commit `<commit>`, in the selection's original order, to a new `<patch>` with `git diff --binary --no-ext-diff --no-textconv --no-relative --src-prefix=a/ --dst-prefix=b/ -U3 <commit>^ <commit> >> <patch>`, run `git -C <worktree> apply --check -R --cached <patch>`, and remove the worktree with `git worktree remove <worktree>` whatever the check's result; the change is confirmed present only when the check exits 0 and prints no `warning:` on stdout or stderr, and it is not confirmed when the check exits 1 or prints a `warning:`, for example after a revert, a later change to the story's lines or their context, or a later rename; stop and report the story as not confirmed present, with the check's output, for a human check, and stop and report the check as failed when it exits with any other status or another of these commands fails.\n"
    '3. Carry the selected commits onto the promotion branch by cherry-picking them one at a time in their original order, with `-m 1` when a selected commit is a merge commit, or by applying non-merge selections with `git cherry-pick -n` in order and making one commit.\n'
    "4. Run the promotion branch's local checks, push it, then open the promotion PR from it to `profile.git.release_branch` and let its CI run.\n"
    '   A whole-branch integration-to-release PR is not used under `per-story`.\n'
    "5. Stop and report instead of carrying another story's commit or merging the integration branch into the promotion when the selection finds no commit, matches more than one feature PR, or cannot apply without an un-promoted story.\n"
    "   A cherry-pick conflict that needs another story's commits is that stop: report the conflicting commit and the story it needs, and do not pull that story in to clear the conflict.\n"
    '   An empty application, because a selected commit is already on the release branch, is that stop too: report the story as already promoted.\n'
    "   A check that fails only because another story's change is absent is that stop as well.\n"
    '\n'
    'Under `per-story`, a valid review fix lands on a new feature branch to `profile.git.integration_branch` and merges there before its commit is carried.\n'
    "The stale promotion PR is then closed unmerged, and the fix is carried in this order: cut a fresh story-scoped promotion branch from the release branch under a new branch name, carry the selection recorded in the closed PR body, then select the fix PR's own commits by `profile.git.merge_method` and cherry-pick them onto the branch in their original order, with `-m 1` when one is a merge commit.\n"
    "The story's updated commits, the original selection plus the fix commits, are what the branch carries.\n"
    'Record the fix PR number in the promotion PR body when that PR merges, and select from that recorded number instead of running the discovery again, which would match a second feature PR and stop.\n'
    "Open a fresh promotion PR from that branch to `profile.git.release_branch`, carrying the story's updated commits.\n"
    "Refresh the story's pre-production evidence against that promotion head before the merge.\n"
    'Do not back-merge the release branch into the promotion branch, update-branch a promotion PR, or force-push one; rebuild it instead.\n'
    '\n'
    'For any promotion:\n'
    '\n'
    "- Review the promotion PR's whole cumulative diff (`references/code-review.md`).\n"
    '- Inspect a `whole-branch` promotion with a fresh three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...origin/<integration>`.\n'
    '  The two-dot diff shows release-only files as deletions.\n'
    '- Inspect a `per-story` promotion with its own story-scoped three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...<promotion-branch>`.\n'
    '  Never inspect the whole integration branch for a `per-story` promotion.\n'
    '- ⛔ Never merge the release branch into the integration branch (no back-merges), and never update-branch a promotion PR, which does the same.\n'
    '  Resolve promotion conflicts on a separate branch.\n'
    '- Under `whole-branch`, fixes for a promotion PR go on a new feature branch to the integration branch and flow into the promotion.\n'
)


def test_promotion_section_carries_no_code_fence() -> None:
    raw = GITHUB.read_text()
    match = re.search(r"^## Promotion\s*$", raw, re.MULTILINE)
    rest = raw[match.end():]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    assert not re.search(r"^\s*```", rest[:nxt.start()], re.MULTILINE), \
        "Promotion must not hide text in a code fence"


def test_promotion_section_is_pinned_line_for_line() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    assert body.strip("\n") == EXPECTED_PROMOTION_SECTION.strip("\n")


def test_promotion_no_longer_prescribes_git_grep() -> None:
    # `git grep` has no `-x` switch: it exits 129 with "unknown switch `x'".
    body = section(GITHUB.read_text(), "Promotion")
    assert not re.search(r"\bgit grep\b", body), "Promotion prescribes git grep again"


REVERSE_APPLY_PREFIXES = ("git worktree add ", "git diff ", "git -C <worktree> apply ", "git worktree remove ")
# The fixture ignores the user's global and system git config, so only the hostile config it sets applies.
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def reverse_apply_commands() -> list[str]:
    """The four commands the presence check prescribes, pinned to the order the sentence gives them."""
    lines = [
        line for line in section(GITHUB.read_text(), "Promotion").splitlines()
        if "Before carrying them, confirm the story's change" in line
    ]
    assert len(lines) == 1, "the presence check sentence is missing from Promotion"
    commands = [span for span in re.findall(r"`([^`]+)`", lines[0]) if span.startswith(REVERSE_APPLY_PREFIXES)]
    order = [next(prefix for prefix in REVERSE_APPLY_PREFIXES if command.startswith(prefix)) for command in commands]
    assert order == list(REVERSE_APPLY_PREFIXES), commands
    return commands


class PromotionRepo:
    """A fixture repository whose story is two selected commits with another story's commit between them."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.runs = 0
        self.repo = root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "agent-skills@example.com")
        self.git("config", "user.name", "agent-skills")
        self.git("config", "commit.gpgsign", "false")
        docs = self.repo / "docs"
        docs.mkdir()
        doc = docs / "f.md"
        lines = ["top"] + [f"filler {n}" for n in range(12)] + ["one", "old line", "two", "end"]
        tool = self.repo / "tool.sh"
        blob = docs / "blob.bin"

        def write(changes: dict[str, str]) -> None:
            doc.write_text("\n".join(changes.get(line, line) for line in lines) + "\n")

        write({})
        tool.write_text("echo tool\n")
        tool.chmod(0o644)
        blob.write_bytes(b"\x00base\n")
        (self.repo / ".gitattributes").write_text("*.md diff=hostile\n")
        (docs / "old name.md").write_text("renamed by the story\n")
        (docs / "other.md").write_text("other story\n")
        (docs / "gone.md").write_text("deleted by the story\n")
        (docs / "no-newline.md").write_text("no newline")
        self.commit("base")
        # First story commit: change a line and a binary file, add a file, rename a file whose name has a space.
        write({"old line": "new line"})
        blob.write_bytes(b"\x00story\n")
        (docs / "added.md").write_text("added by the story\n")
        (docs / "old name.md").rename(docs / "new;name.md")
        first = self.commit("story 1")
        # Another story's commit lands between the two selected commits.
        (docs / "other.md").write_text("other story, changed\n")
        other = self.commit("other story")
        # Second story commit, selected as its merge commit (merge_method merge): another hunk of the
        # same file, a mode change, a deleted file and a file without a trailing newline.
        story = {"old line": "new line", "filler 3": "filler 3, story"}
        write(story)
        tool.chmod(0o755)
        (docs / "gone.md").unlink()
        (docs / "no-newline.md").write_text("no newline, story")
        second = self.commit("story 2")
        self.git("checkout", "-q", "--detach", other)
        self.git("merge", "-q", "--no-ff", "--no-edit", second)
        self.selection = [first, self.git("rev-parse", "HEAD")]
        # A later change far from the story's lines keeps the story's merged context intact.
        write({**story, "top": "top, later"})
        later = self.commit("later")
        refs = {"present": later}
        for name, reverted in (("other-reverted", other), ("first-reverted", first), ("second-reverted", second)):
            self.git("checkout", "-q", "--detach", later)
            self.git("revert", "--no-edit", reverted)
            refs[name] = self.git("rev-parse", "HEAD")
        variants = {
            "substring": lambda: write({**story, "top": "top, later", "old line": "new line, extended"}),
            "context-changed": lambda: write({**story, "top": "top, later", "filler 11": "filler 11, later"}),
            "renamed-later": lambda: doc.rename(doc.with_name("g.md")),
            "mode-reverted": lambda: tool.chmod(0o644),
        }
        for name, change in variants.items():
            self.git("checkout", "-q", "--detach", later)
            change()
            refs[name] = self.commit(name)
        self.git("checkout", "-q", "--detach", later)
        for name, sha in refs.items():
            self.git("update-ref", f"refs/remotes/origin/{name}", sha)
        # Hostile config the prescribed commands must ignore, set after the commits so they record the
        # mode change: an external diff driver, a textconv driver, zero context lines, no or relative
        # path prefixes (the commands run from a subdirectory), and no file modes.
        for key, value in (
            ("diff.external", "true"),
            ("diff.hostile.textconv", "tr a-z A-Z"),
            ("diff.context", "0"),
            ("diff.noprefix", "true"),
            ("diff.mnemonicPrefix", "true"),
            ("diff.relative", "true"),
            ("core.fileMode", "false"),
        ):
            self.git("config", key, value)

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True, env=GIT_ENV
        ).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def run(self, command: str, branch: str, name: str, commit: str = "") -> subprocess.CompletedProcess:
        """Run one prescribed command, placeholders filled, from a subdirectory of the repository.

        `<worktree>` and `<patch>` sit outside the repository; the command runs as argv, not through a shell,
        and a trailing `>> <patch>` appends its output to the patch.
        """
        command = command.replace("origin/<profile.git.integration_branch>", branch).replace("<commit>", commit)
        command = command.replace("<worktree>", str(self.root / f"wt-{name}"))
        command = command.replace("<patch>", str(self.root / f"{name}.patch"))
        assert not re.search(r"<[a-z]", command), command
        argv, redirect, target = command.partition(" >> ")
        cwd = self.repo / "docs"
        if redirect:
            with open(target, "a") as out:
                return subprocess.run(shlex.split(argv), cwd=cwd, stdout=out, stderr=subprocess.PIPE, text=True, env=GIT_ENV)
        return subprocess.run(shlex.split(argv), cwd=cwd, capture_output=True, text=True, env=GIT_ENV)

    def presence(self, name: str) -> subprocess.CompletedProcess:
        """The check's result against `origin/<name>`, after running every prescribed step around it."""
        add, diff, check, remove = reverse_apply_commands()
        branch = f"origin/{name}"
        self.runs += 1
        name = f"{name}-{self.runs}"  # a new <patch> and <worktree> for every check
        added = self.run(add, branch, name)
        assert added.returncode == 0, added.stderr
        for commit in self.selection:
            saved = self.run(diff, branch, name, commit)
            assert saved.returncode == 0, saved.stderr
        result = self.run(check, branch, name)
        removed = self.run(remove, branch, name)
        assert removed.returncode == 0, removed.stderr
        return result


@pytest.fixture(scope="module")
def promotion_repo(tmp_path_factory: pytest.TempPathFactory) -> PromotionRepo:
    return PromotionRepo(tmp_path_factory.mktemp("promotion"))


def confirmed(result: subprocess.CompletedProcess) -> bool:
    """The sentence's verdict: confirmed only on exit 0 with no `warning:`; not confirmed on exit 1 or a warning."""
    output = result.stdout + result.stderr
    assert result.returncode in (0, 1), output
    assert "usage:" not in output, output
    return result.returncode == 0 and "warning:" not in output


@pytest.mark.parametrize(
    ("name", "present"),
    [
        ("present", True),
        ("other-reverted", True),
        ("first-reverted", False),
        ("second-reverted", False),
        ("substring", False),
        ("context-changed", False),
        ("renamed-later", False),
        ("mode-reverted", False),
    ],
)
def test_prescribed_reverse_apply_check_reports_presence(promotion_repo: PromotionRepo, name: str, present: bool) -> None:
    result = promotion_repo.presence(name)
    assert confirmed(result) is present, result.stdout + result.stderr


def test_prescribed_reverse_apply_check_warns_on_stderr_for_a_reverted_mode(promotion_repo: PromotionRepo) -> None:
    # The warning branch of the verdict: exit 0, and the `warning:` is on stderr only.
    result = promotion_repo.presence("mode-reverted")
    assert result.returncode == 0, result.stderr
    assert "warning:" in result.stderr and "warning:" not in result.stdout, result.stdout + result.stderr


def test_prescribed_reverse_apply_check_cleans_up_and_fails_closed(promotion_repo: PromotionRepo) -> None:
    status_before = promotion_repo.git("status", "--porcelain", "--untracked-files=all")
    assert confirmed(promotion_repo.presence("present"))
    # The throwaway worktree is gone and the repository's own tree is untouched.
    worktrees = [
        line.removeprefix("worktree ")
        for line in promotion_repo.git("worktree", "list", "--porcelain").splitlines()
        if line.startswith("worktree ")
    ]
    assert worktrees == [str(promotion_repo.repo)]
    assert promotion_repo.git("status", "--porcelain", "--untracked-files=all") == status_before
    # A missing integration ref fails the worktree step instead of passing the check.
    add = reverse_apply_commands()[0]
    assert promotion_repo.run(add, "origin/missing", "missing").returncode != 0
