"""Contract checks binding every merge to the head its review of record covered."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_REVIEW = ROOT / "shared" / "code-review.md"
GITHUB = ROOT / "shared" / "github.md"
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


def test_code_review_defines_the_merge_guard_in_order() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge guard")
    steps = (
        "Every merge, by any role, runs this guard immediately before the merge command.",
        "1. Read the live PR head SHA (`gh pr view <n> --json headRefOid`).",
        "2. Read the head SHA named in the latest review-of-record comment on the PR.",
        "3. If they differ, do not merge: review the delta since the reviewed head (Rounds), "
        "post that review of record, and start again at step 1.",
        "4. Merge with " + EXPECTED_HEAD,
        MATCH_HEAD,
        "If the merge command cannot carry an expected-head condition, " + UNGUARDED_STOP + " instead of merging unguarded.",
    )
    positions = [body.find(step) for step in steps]
    assert -1 not in positions, f"merge guard missing: {steps[positions.index(-1)]}"
    assert positions == sorted(positions), "merge guard steps out of order"


def test_merge_guard_binds_a_user_waiver_to_its_head() -> None:
    body = section(CODE_REVIEW.read_text(), "Merge guard")
    assert (
        "When the user gave the explicit per-PR instruction to skip the review (The gate), "
        "there is no review-of-record comment: step 2 reads the head SHA the PR had when the user gave that instruction, "
        "and step 4 carries that full SHA."
    ) in body
    assert (
        "Record that full SHA (`gh pr view <n> --json headRefOid`) as soon as the user gives the instruction, "
        "unless the user named it; if a push could have landed between the instruction and that read, "
        "confirm the SHA with the user before relying on it."
    ) in body
    assert "The waiver covers only that head; if the head has changed since, do not merge, and ask the user again." in body


def test_review_of_record_names_the_full_head_sha() -> None:
    body = section(CODE_REVIEW.read_text(), "Review of record")
    assert "Post the review of record as one PR comment: the full 40-character head SHA reviewed," in body


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
