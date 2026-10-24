"""Contract checks for the per-story promotion mechanics in shared/github.md."""

import json
import re
from pathlib import Path

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
    "Identify the story's merged feature PR, by its issue key, with `gh pr list --state merged --base <profile.git.integration_branch> --limit 1000 --search \"<issue key>\" --json number,headRefName,mergeCommit,commits`, keep the one whose head branch carries the issue key, and select from `origin/<profile.git.integration_branch>` only the commits that PR added.",
    "With `profile.git.merge_method` `squash`, select that PR's squash commit.",
    "With `profile.git.merge_method` `rebase`, select the integration-branch commits whose patch id matches one of that PR's own commits.",
    "With `profile.git.merge_method` `merge`, select that PR's merge commit.",
    # Carrying the selected commits onto the promotion branch.
    "Carry the selected commits onto the promotion branch by cherry-picking them in their original order, with `-m 1` when a selected commit is a merge commit, or by squash-applying non-merge selections with `git cherry-pick -n` and one commit.",
    # The promotion PR, and the explicit refusal of a whole-branch PR under per-story.
    "Push the branch, then open the promotion PR from it to `profile.git.release_branch`.",
    "A whole-branch integration-to-release PR is not used under `per-story`.",
    # Fail-closed stop, including the un-promoted-story case.
    "Stop and report instead of carrying another story's commit or merging the integration branch into the promotion when the selection finds no commit, matches more than one feature PR, or cannot apply without an un-promoted story.",
    "A cherry-pick conflict that needs another story's commits is that stop: report the conflicting commit and the story it needs, and do not pull that story in to clear the conflict.",
    "An empty application, because a selected commit is already on the release branch, is that stop too: report the story as already promoted.",
    # Story-scoped three-dot diff, split by mode.
    "Inspect a `whole-branch` promotion with a fresh three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...origin/<integration>`.",
    "The two-dot diff shows release-only files as deletions.",
    "Inspect a `per-story` promotion with its own story-scoped three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...<promotion-branch>`.",
    "Never inspect the whole integration branch for a `per-story` promotion.",
    # The per-story review-fix flow.
    "Under `per-story`, a valid review fix lands on a new feature branch to `profile.git.integration_branch` and merges there before its commit is carried.",
    "The stale promotion PR is then closed unmerged and a fresh story-scoped promotion branch is cut from the release branch under a new branch name, or the fix commit is cherry-picked onto that branch once the story's original commits are carried again.",
    "The story's updated commits, the original selection plus the fix commit, are what that branch carries; keep that recorded selection and do not rerun the discovery after the fix PR merges, which would match a second feature PR and stop.",
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
    '2. Identify the story\'s merged feature PR, by its issue key, with `gh pr list --state merged --base <profile.git.integration_branch> --limit 1000 --search "<issue key>" --json number,headRefName,mergeCommit,commits`, keep the one whose head branch carries the issue key, and select from `origin/<profile.git.integration_branch>` only the commits that PR added.\n'
    "   With `profile.git.merge_method` `squash`, select that PR's squash commit.\n"
    "   With `profile.git.merge_method` `rebase`, select the integration-branch commits whose patch id matches one of that PR's own commits.\n"
    "   With `profile.git.merge_method` `merge`, select that PR's merge commit.\n"
    '3. Carry the selected commits onto the promotion branch by cherry-picking them in their original order, with `-m 1` when a selected commit is a merge commit, or by squash-applying non-merge selections with `git cherry-pick -n` and one commit.\n'
    '4. Push the branch, then open the promotion PR from it to `profile.git.release_branch`.\n'
    '   A whole-branch integration-to-release PR is not used under `per-story`.\n'
    "5. Stop and report instead of carrying another story's commit or merging the integration branch into the promotion when the selection finds no commit, matches more than one feature PR, or cannot apply without an un-promoted story.\n"
    "   A cherry-pick conflict that needs another story's commits is that stop: report the conflicting commit and the story it needs, and do not pull that story in to clear the conflict.\n"
    '   An empty application, because a selected commit is already on the release branch, is that stop too: report the story as already promoted.\n'
    '\n'
    'Under `per-story`, a valid review fix lands on a new feature branch to `profile.git.integration_branch` and merges there before its commit is carried.\n'
    "The stale promotion PR is then closed unmerged and a fresh story-scoped promotion branch is cut from the release branch under a new branch name, or the fix commit is cherry-picked onto that branch once the story's original commits are carried again.\n"
    "The story's updated commits, the original selection plus the fix commit, are what that branch carries; keep that recorded selection and do not rerun the discovery after the fix PR merges, which would match a second feature PR and stop.\n"
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


def test_promotion_section_is_pinned_line_for_line() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    assert body.strip("\n") == EXPECTED_PROMOTION_SECTION.strip("\n")
