"""Contract checks binding every merge to the head its review of record covered."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_REVIEW = ROOT / "shared" / "code-review.md"
GITHUB = ROOT / "shared" / "github.md"
MERGE_APPROVAL = ROOT / "shared" / "merge-approval.md"
TODO_TRACKING = ROOT / "shared" / "todo-tracking.md"
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"

GUARD = "run the merge guard in `references/code-review.md`"
EXPECTED_HEAD = "the reviewed full head SHA as the expected-head condition"
MATCH_HEAD = "--match-head-commit <full reviewed SHA>"
UNGUARDED_STOP = "stop and report the merge blocked"
UPDATE_QUALIFIER = "even when CI is green and the base changes touch none of the PR's files."
MERGE_RULES = (
    "The merge rules: a review of record binds only to the exact head it reviewed, "
    "so any change to the head, including an update-branch, needs a delta review posted before merging; "
    "every merge must " + GUARD + " and carry " + EXPECTED_HEAD
    + " (on GitHub, `gh pr merge <n> " + MATCH_HEAD + "`)."
)
READ_BACK_QUERY = "read the PR yourself (`gh pr view <n> --json headRefOid,mergeCommit,comments`)"
READ_BACK = (
    "compare each merged PR's head at merge (`headRefOid`, not the merge commit) "
    "with the head SHA in its last review-of-record comment; "
    "if they differ, report the PR and both SHAs, and stop"
)


def section(text: str, heading: str, level: str = "##") -> str:
    match = re.search(rf"^{level} {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(rf"^#{{1,{len(level)}}} ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


REVIEWS_READ = (
    "2. Read the PR's reviews with `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`, "
    "select the latest submitted review in state `COMMENTED` whose body begins with `Review of record`, "
    "and take both its `commit_id` and the full head SHA on its first line."
)
FAIL_CLOSED = (
    "3. Except under the explicit per-PR review waiver in The gate, "
    "if no such review exists, either SHA is missing, or either differs from the live head, do not merge: "
    "review the delta since the reviewed head (Rounds), post that review of record, and start again at step 1."
)


def test_code_review_defines_the_merge_guard_in_order() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge guard")
    steps = (
        "Every merge, by any role, runs this guard immediately before the merge command.",
        "1. Read the live PR head SHA (`gh pr view <n> --json headRefOid`).",
        REVIEWS_READ,
        FAIL_CLOSED,
        "4. Merge with " + EXPECTED_HEAD,
        MATCH_HEAD,
        "If the merge command cannot carry an expected-head condition, " + UNGUARDED_STOP + " instead of merging unguarded.",
    )
    positions = [body.find(step) for step in steps]
    assert -1 not in positions, f"merge guard missing: {steps[positions.index(-1)]}"
    assert positions == sorted(positions), "merge guard steps out of order"


def test_merge_guard_selects_the_latest_review_by_submission_time() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge guard")
    assert "The latest review is the one with the greatest `submitted_at`, not the last in the list." in body


def test_merge_guard_no_longer_reads_a_comment() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge guard")
    assert "gh pr view <n> --json headRefOid,mergeCommit,comments" not in body
    assert "review-of-record comment" not in body


def test_merge_guard_binds_a_user_waiver_to_its_head() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge guard")
    assert (
        "When the user gave the explicit per-PR instruction to skip the review (The gate), "
        "there is no review of record on the PR: step 2 reads the head SHA the PR had when the user gave that instruction, "
        "and step 4 carries that full SHA."
    ) in body
    assert (
        "Record that full SHA (`gh pr view <n> --json headRefOid`) as soon as the user gives the instruction, "
        "unless the user named it; if a push could have landed between the instruction and that read, "
        "confirm the SHA with the user before relying on it."
    ) in body
    assert "The waiver covers only that head; if the head has changed since, do not merge, and ask the user again." in body
    assert (
        "Under that waiver, use the head SHA recorded when the user gave the instruction, "
        "as the paragraph below specifies."
    ) in body


def test_review_of_record_is_posted_as_a_comment_pr_review() -> None:
    body = section(CODE_REVIEW.read_text(), "Review of record")
    lines = (
        "Post the review of record as one PR review with the comment event, at the reviewed head, never as an issue comment: "
        "on GitHub, `gh pr review <n> --comment --body-file <file>`, with the body file in the scratch directory, never in the checkout.",
        "The body's first line is `Review of record <full 40-character head SHA>`, followed by the reviewer and adjudicator names and models, "
        "the reviewer's findings, the verdict per finding, and the fix commit for each valid one.",
        "Each delta round posts a new review; never edit an earlier one.",
        "If the host denies the post, do not fall back to an issue comment: report the exact command and the denial, and stop.",
        "Post it, confirm it landed, and only then move to merging.",
    )
    positions = [body.find(line) for line in lines]
    assert -1 not in positions, f"review of record step 4 missing: {lines[positions.index(-1)]}"
    assert positions == sorted(positions), "review of record step 4 out of order"
    assert "Post the review of record as one PR comment" not in body


def test_gate_requires_the_review_of_record_as_a_pr_review() -> None:
    body = section(CODE_REVIEW.read_text(), "The gate")
    assert (
        "Never attempt a merge until the review of record is posted on the PR as a PR review, "
        "except under the explicit per-PR review waiver in The gate."
    ) in body


def test_shadow_verdicts_go_in_the_review_of_record() -> None:
    body = section(CODE_REVIEW.read_text(), "Shadow adjudicators", "###")
    assert "beside the adjudicator's in the review of record, under an \"Adjudicator comparison\" heading" in body


def test_update_branch_is_a_head_change_that_needs_a_delta_review() -> None:
    text = CODE_REVIEW.read_text()
    assert (
        "An update-branch that changes the head SHA creates a new head that needs a delta review before the PR merges, "
        + UPDATE_QUALIFIER
    ) in section(text, "Merge guard")
    assert (
        "After an update that changes the head SHA, the review of record is stale until a delta review covers "
        "the new head (Merge guard), " + UPDATE_QUALIFIER
    ) in section(text, "Watching the PR")


def test_merge_owner_points_at_the_guard() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge owner")
    assert "merge without asking, through the merge guard below" in body


def test_github_never_merges_green_alone() -> None:
    body = section(GITHUB.read_text(), "Merging")
    assert "merge whichever PR is green immediately" not in body
    assert "merge a PR as soon as it is green and its review of record covers its current head" in body
    assert "the merge guard in `references/code-review.md` passes" in body
    assert (
        "After any merge, update the remaining PRs except promotion PRs (Promotion) and re-arm their watches; "
        "each update that changes the head SHA needs a delta review before that PR merges."
    ) in body


def test_github_merge_bar_requires_the_comment_review_with_a_waiver_exception() -> None:
    body = section(GITHUB.read_text(), "Merging")
    for sentence in (
        "Except under the explicit per-PR review waiver in The gate, the merge bar requires a completed review of record at the current head.",
        "Post it as a `--comment` PR review and confirm its state is `COMMENTED` and its `commit_id` matches that head before any merge attempt.",
        "Under the waiver, use the head SHA recorded when the user gave the instruction and run the merge guard.",
    ):
        assert sentence in body, f"github.md Merging missing: {sentence}"
    assert "review-of-record comment" not in body


def test_merge_approval_url_is_the_review_html_url() -> None:
    text = MERGE_APPROVAL.read_text()
    assert (
        "The review-of-record URL is the review's `html_url` from the reviews API (`#pullrequestreview-<id>`), "
        "not a PR comment URL and not the PR URL alone."
    ) in text
    assert "#issuecomment-" not in text
    assert "#pullrequestreview-1 |" in text


def test_todo_tracking_names_the_review_of_record() -> None:
    text = TODO_TRACKING.read_text()
    assert "each review round and finding, the review of record, the merge," in text
    assert "review-of-record comment" not in text


def test_shared_files_no_longer_call_the_review_of_record_a_comment() -> None:
    for path in sorted(SHARED.glob("*.md")):
        text = path.read_text()
        assert "review-of-record comment" not in text, path.name
        assert "as one PR comment" not in text, path.name


def test_engineering_workflow_merge_uses_the_guard() -> None:
    body = section(skill("engineering-workflow"), "10. Merge")
    autonomous = next(l for l in body.splitlines() if l.startswith("- If `profile.review.merge_owner` is `agent`:"))
    assert GUARD in autonomous
    assert EXPECTED_HEAD in autonomous
    assert MATCH_HEAD in autonomous
    approved = next(l for l in body.splitlines() if l.startswith("4. Re-read the live PR,"))
    assert "run the merge guard in `references/code-review.md`" in approved
    assert UNGUARDED_STOP + " instead of merging unguarded" in approved


def test_qa_evidence_merge_uses_the_guard() -> None:
    text = skill("qa-verification")
    line = next(l for l in text.splitlines() if "Merge only on the exact final head" in l)
    assert GUARD in line
    assert EXPECTED_HEAD in line
    assert MATCH_HEAD in line
    assert "if the merge command cannot carry it, " + UNGUARDED_STOP in line


def test_story_to_done_briefs_carry_the_merge_rules() -> None:
    text = skill("story-to-done")
    for heading in (
        "2. Senior engineer: implement to deployment review",
        "3. QA agent: verify the deployed story",
    ):
        assert MERGE_RULES in section(text, heading), f"{heading} brief missing the merge rules"


def test_story_to_done_reads_back_the_reviewed_head() -> None:
    text = skill("story-to-done")
    engineer = section(text, "2. Senior engineer: implement to deployment review")
    assert "the head SHA each PR's review of record covered" in engineer
    for heading in (
        "2. Senior engineer: implement to deployment review",
        "3. QA agent: verify the deployed story",
    ):
        body = section(text, heading)
        assert READ_BACK_QUERY + " and " + READ_BACK in body, f"{heading} missing the reviewed-head read-back"
    done = section(text, "4. Act on the QA outcome")
    assert "the evidence PR is merged on the head its review of record covered" in done
