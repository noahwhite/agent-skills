"""Contract checks for the per-story promotion mechanics in shared/github.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITHUB = ROOT / "shared" / "github.md"

# Every sentence below is load-bearing for a consumer profile selecting
# `profile.git.promotion: per-story`. The assertions are exact: deleting or
# rewording any one of them must fail this suite.
PER_STORY_SENTENCES = (
    # Branch construction from the release branch, with an explicit base ref.
    "Under `per-story`, build the promotion branch and its PR like this:",
    "Cut the promotion branch from `origin/<profile.git.release_branch>` with that explicit base ref, after `git fetch --prune origin`.",
    # Merge-method-dependent commit selection.
    "Select, from `origin/<profile.git.integration_branch>`, only the commits the promoted story's merged feature PR added.",
    "With `profile.git.merge_method` `squash` or `rebase`, select the commits whose subjects carry the story's issue key as that PR's squash or rebase commits.",
    "With `profile.git.merge_method` `merge`, select the feature PR's merge commit and cherry-pick it with `-m 1`.",
    # Carrying the selected commits onto the promotion branch.
    "Carry the selected commits onto the promotion branch by cherry-picking them in their original order, or by squash-applying them as one commit.",
    # The promotion PR, and the explicit refusal of a whole-branch PR under per-story.
    "Open the promotion PR from that branch to `profile.git.release_branch`.",
    "A whole-branch integration-to-release PR is not used under `per-story`.",
    # Fail-closed stop.
    "Stop and report instead of carrying another story's commit or merging the integration branch into the promotion when the selection finds no commit, matches more than one feature PR, or cannot apply without an un-promoted story.",
    # Story-scoped three-dot diff, split by mode.
    "Inspect a `whole-branch` promotion with a fresh three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...origin/<integration>`.",
    "The two-dot diff shows release-only files as deletions.",
    "Inspect a `per-story` promotion with its own story-scoped three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...<promotion-branch>`.",
    "Never inspect the whole integration branch for a `per-story` promotion.",
    # The per-story review-fix flow.
    "Under `per-story`, a valid review fix lands on a new feature branch to `profile.git.integration_branch`.",
    "The stale promotion PR is closed unmerged and a fresh story-scoped promotion branch is cut from the release branch, or the fix commit is cherry-picked onto the promotion branch, carrying the story's updated commits.",
    "Refresh the story's pre-production evidence against that promotion head before the merge.",
    "No back-merge of the release branch, no update-branch of the promotion PR, and no force-push of the promotion branch applies to that flow.",
)

# `none` and `whole-branch` behaviour is unchanged; these sentences stay byte-stable.
UNCHANGED_SENTENCES = (
    "- `none`: trunk-based; the integration branch is the release branch and there is no promotion PR.",
    "- `whole-branch`: one promotion PR carries the whole integration branch, opened only after every story awaiting promotion is verified in its pre-production environment.",
    "Never promote a single story on its own.",
    "- Review the promotion PR's whole cumulative diff (`references/code-review.md`).",
    "⛔ Never merge the release branch into the integration branch (no back-merges), and never update-branch a promotion PR, which does the same.",
    "Resolve promotion conflicts on a separate branch.",
    "- Under `whole-branch`, fixes for a promotion PR go on a new feature branch to the integration branch and flow into the promotion.",
)


def section(text: str, heading: str, level: str = "##") -> str:
    match = re.search(rf"^{level} {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(rf"^#{{1,{len(level)}}} ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def missing_sentences(text: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in text]


def test_promotion_section_exists() -> None:
    assert GITHUB.is_file(), f"missing {GITHUB.relative_to(ROOT)}"
    assert "per-story" in section(GITHUB.read_text(), "Promotion")


def test_per_story_promotion_sentences_are_present_verbatim() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    missing = missing_sentences(body, PER_STORY_SENTENCES)
    assert not missing, "missing per-story promotion sentences:\n" + "\n".join(missing)


def test_none_and_whole_branch_promotion_sentences_are_unchanged() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    missing = missing_sentences(body, UNCHANGED_SENTENCES)
    assert not missing, "changed none/whole-branch promotion sentences:\n" + "\n".join(missing)


def test_deleting_an_asserted_sentence_is_caught() -> None:
    body = section(GITHUB.read_text(), "Promotion")
    for sentence in PER_STORY_SENTENCES + UNCHANGED_SENTENCES:
        deleted = body.replace(sentence, "")
        assert missing_sentences(deleted, (sentence,)) == [sentence], sentence
