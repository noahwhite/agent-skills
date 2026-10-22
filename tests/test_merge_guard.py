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
READ_BACK_QUERY = (
    "read the PR yourself with `gh pr view <n> --json headRefOid,mergeCommit` "
    "and `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`."
)
READ_BACK = (
    "Select the review of record as the merge guard in `references/code-review.md` does "
    "(the `COMMENTED` review whose body begins with `Review of record` and has the greatest `submitted_at`).\n"
    "Compare the merged PR's `headRefOid` (its head at merge, not the merge commit) separately with that review's `commit_id` "
    "and with the full head SHA on its first line.\n"
    "Except under the explicit per-PR review waiver in The gate, a missing review, a missing SHA, or either mismatch "
    "is reported with the PR and all available SHAs, and stops the loop.\n"
    "For a waived PR, compare the merged PR's `headRefOid` with the SHA recorded when the user gave the instruction; "
    "report and stop if that SHA is missing or differs."
)
REVIEW_POLICY_SENTENCE = (
    "> The review of record is posted as one PR review with the comment event, never as an issue comment."
)
COMMENT_REVIEW = "`--comment` PR review"
SKILL_LINES = {
    "engineering-workflow": (
        "Post the review of record on the PR as one PR review with the comment event "
        "(`gh pr review <n> --comment --body-file <file>`; first line `Review of record <full head SHA>`, "
        "then findings, verdict per finding, fix commit per valid finding, the models used), "
        "never as an issue comment, **before** attempting the merge.",
        "- The review of record completed at the current head, every valid finding is fixed, "
        "and its " + COMMENT_REVIEW + " is posted and visible.",
        "- If it is `human`: tell the user the PR is merge-ready "
        "(link, head SHA, review-of-record " + COMMENT_REVIEW + " link, its `html_url`) and wait; resume at step 11 once it is merged.",
        "[scripts/pr-status.sh](scripts/pr-status.sh) prints the current branch's PR state, checks, "
        "PR reviews (including the `--comment` review of record) and issue comments.",
    ),
    "qa-verification": (
        "- Fix what the adjudicator rules valid, and post the review of record on the PR as a "
        + COMMENT_REVIEW + " before the merge, never after.",
    ),
    "persona-release-manager": (
        "- Re-run the review at the new head after any change, then post the review of record on the PR as a "
        + COMMENT_REVIEW + " before the merge.",
    ),
}


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
    assert (
        "Record each shadow's verdicts beside the adjudicator's in the review of record, "
        "under an \"Adjudicator comparison\" heading, with an agreement summary."
    ) in body


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
        assert READ_BACK_QUERY + "\n" + READ_BACK in body, f"{heading} missing the reviewed-head read-back"
    assert "comments" not in text, "story-to-done reads issue comments somewhere"
    assert "/issues/" not in text, "story-to-done reads the issues endpoint somewhere"
    done = section(text, "4. Act on the QA outcome")
    assert "the evidence PR is merged on the head its review of record covered" in done


def test_story_to_done_read_backs_open_with_their_own_lead_in() -> None:
    text = skill("story-to-done")
    assert (
        "Then, for every PR it merged, " + READ_BACK_QUERY
    ) in section(text, "2. Senior engineer: implement to deployment review")
    assert (
        "For every PR it merged, such as the evidence PR, " + READ_BACK_QUERY
    ) in section(text, "3. QA agent: verify the deployed story")


def test_story_to_done_read_backs_compare_each_sha_separately_and_fail_closed() -> None:
    text = skill("story-to-done")
    for heading in (
        "2. Senior engineer: implement to deployment review",
        "3. QA agent: verify the deployed story",
    ):
        body = section(text, heading)
        assert (
            "Compare the merged PR's `headRefOid` (its head at merge, not the merge commit) separately with that review's `commit_id` "
            "and with the full head SHA on its first line."
        ) in body, heading
        assert (
            "Except under the explicit per-PR review waiver in The gate, a missing review, a missing SHA, or either mismatch "
            "is reported with the PR and all available SHAs, and stops the loop."
        ) in body, heading


def test_story_to_done_read_backs_check_a_waived_pr_against_the_recorded_sha() -> None:
    text = skill("story-to-done")
    for heading in (
        "2. Senior engineer: implement to deployment review",
        "3. QA agent: verify the deployed story",
    ):
        assert (
            "For a waived PR, compare the merged PR's `headRefOid` with the SHA recorded when the user gave the instruction; "
            "report and stop if that SHA is missing or differs."
        ) in section(text, heading), heading


def test_skills_name_the_comment_pr_review() -> None:
    for name, lines in SKILL_LINES.items():
        text = skill(name)
        for line in lines:
            assert line in text.splitlines(), f"{name} missing: {line}"


def test_review_policy_says_the_review_of_record_is_a_pr_review() -> None:
    for name in ("linear-user-story", "linear-bug"):
        block = [l for l in skill(name).splitlines() if l.startswith("> ")]
        assert REVIEW_POLICY_SENTENCE in block, f"{name} Review Policy missing the format sentence"
        policy = block.index(next(l for l in block if l.startswith("> **Review Policy**")))
        assert block.index(REVIEW_POLICY_SENTENCE) == policy + 2, f"{name} sentence not in the Review Policy block"


# Phrases that name the review of record as a comment, and the negated uses that stay legal.
COMMENT_NAMES = (
    r"(?:\bPR[- ]comment\b|\bpull[- ]request comment\b|\bissue comment\b"
    r"|\breview[- ]of[- ]record comment\b|\bas (?:one|a) comment\b)"
)
COMMENT_NAMES_RE = re.compile(COMMENT_NAMES, re.IGNORECASE)
# "never as an issue comment", "do not post it as a PR comment", "not a PR comment URL": a negation word, then only
# words from a closed list of plain fillers, then the name. Any other word ("delay", "skip", a comma) ends the span, so
# a reversal such as "do not delay posting ... as a PR comment" is still flagged.
NEGATION_FILLERS = (
    r"(?:as|an?|the|one|it|this|that|its|on|to|fall|back|post(?:ed|ing)?|use|treat|call|send|submit|write|name"
    r"|review-of-record|review|of|record|PR|pull|request)"
)
NEGATED_NAME_RE = re.compile(
    r"\b(?:never|not|no)\b(?:\s+" + NEGATION_FILLERS + r"\b){0,8}?\s+" + COMMENT_NAMES,
    re.IGNORECASE,
)
UNRELATED_COMMENT_RE = re.compile(r"linear issue comment", re.IGNORECASE)
ABOUT_RECORD = re.compile(r"review[- ]of[- ]record", re.IGNORECASE)
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def scanned_files() -> list[Path]:
    return sorted(
        [*SHARED.glob("*.md"), *SKILLS.glob("*/SKILL.md"), *SKILLS.glob("*/references/*.md")]
    )


def text_units(text: str) -> list[str]:
    """Paragraphs, list items and blockquotes, each with its hard-wrapped lines joined into one unit."""
    units: list[list[str]] = [[]]
    for line in text.splitlines():
        if not line.strip():
            units.append([])
            continue
        if LIST_ITEM.match(line) and units[-1]:
            units.append([])
        units[-1].append(re.sub(r"^\s*>\s?", "", line).strip())
    return [" ".join(unit) for unit in units if unit]


def comment_naming_sentences(text: str) -> list[str]:
    """Units about the review of record that call it a comment, minus unrelated and negated uses.

    The unit is a whole paragraph, list item or blockquote (hard-wrapped lines joined), so a follow-on such as
    "Post it as an issue comment." keeps its context. The scan fails closed: an unrelated issue comment in the same
    paragraph as a review-of-record sentence is flagged, and goes in its own paragraph or list item instead.
    """
    hits = []
    for unit in text_units(text):
        if not ABOUT_RECORD.search(unit):
            continue
        cleaned = UNRELATED_COMMENT_RE.sub("", unit)
        cleaned = NEGATED_NAME_RE.sub("", cleaned)
        if COMMENT_NAMES_RE.search(cleaned):
            hits.append(unit)
    return hits


def test_wording_scan_covers_the_shared_and_skill_files() -> None:
    names = {str(path.relative_to(ROOT)) for path in scanned_files()}
    assert "shared/code-review.md" in names
    assert "skills/engineering-workflow/SKILL.md" in names
    assert "skills/story-to-done/SKILL.md" in names
    assert "skills/linear-bug/references/code-review.md" in names
    assert len(names) >= 20


def test_no_sentence_calls_the_review_of_record_a_comment() -> None:
    offenders = {
        str(path.relative_to(ROOT)): hits
        for path in scanned_files()
        if (hits := comment_naming_sentences(path.read_text()))
    }
    assert not offenders, f"the review of record is a PR review, not a comment: {offenders}"


def test_wording_scan_flags_each_old_sentence() -> None:
    mutants = (
        "Post the review of record as one PR comment: the full 40-character head SHA reviewed, "
        "reviewer and adjudicator names and models, the reviewer's findings, the verdict per finding, "
        "and the fix commit for each valid one.",
        "Post the review of record on the PR as one comment (head SHA, findings, verdict per finding, "
        "fix commit per valid finding, the models used) **before** attempting the merge.",
        "- Re-run the review at the new head after any change, then post the review-of-record comment on the PR before the merge.",
        "- If it is `human`: tell the user the PR is merge-ready (link, head SHA, review-of-record comment) and wait.",
        "The review of record is posted as an issue comment on the PR.",
        "Skip it. Post the review of record as a PR comment when the run ends.",
    )
    for mutant in mutants:
        assert comment_naming_sentences(mutant), f"scan missed: {mutant}"


def test_wording_scan_ignores_unrelated_and_negated_uses() -> None:
    clean = (
        'linear issue comment add <ID> --body "Worked by agent <session label>"',
        "Post the QA evidence comment that cites the attachment.",
        "Post the review of record as one PR review with the comment event, never as an issue comment: on GitHub, `gh pr review <n> --comment`.",
        "The review-of-record URL is the review's `html_url`, not a PR comment URL and not the PR URL alone.",
        "Post the standup report as a comment on the project.",
    )
    for sentence in clean:
        assert comment_naming_sentences(sentence) == [], f"scan flagged: {sentence}"


def test_wording_scan_flags_wrapped_follow_on_and_variant_names() -> None:
    mutants = (
        "Post the review of record on the PR as one\ncomment before attempting the merge.",
        "Post the review of record before the merge.\nIt is posted as a PR comment.",
        "- Post the review of record as a pull request comment.",
        "- Post the review of record as a PR-comment.",
        "Post the review of record, not the QA report, as one PR comment.",
        "Do not skip it. Post the review of record as an issue comment.",
        "Do not skip posting the review of record as a PR comment.",
        "Never fail to post the review of record as an issue comment.",
        "Do not delay posting the review of record as a PR comment.",
        "Do not wait; post the review of record as a PR comment.",
        "Do not post it, post the review of record as a PR comment.",
        "Do not fall back, post the review of record as an issue comment.",
        "The review of record is a PR review. Post it as an issue comment.",
        "Post the review of record before the merge. Then post it as a PR comment.",
        "Post the review of record before the merge. Its format is one PR comment.",
        "The review of record is posted on the PR. Post one PR comment with the verdicts.",
        "Post the review of record e.g. Codex output. As a PR comment.",
        "Post the review of record (head SHA etc.). Use one PR comment for it.",
        "Post the review of record before the merge. **It** is posted as a PR comment.",
        "The review of record is a PR review. The QA evidence is posted as an issue comment.",
        "The review of record: do not post it, post it as a PR comment.",
        "Post the review of record. It is not a PR review but a PR comment.",
    )
    for mutant in mutants:
        assert comment_naming_sentences(mutant), f"scan missed: {mutant!r}"


def test_wording_scan_accepts_varied_negations() -> None:
    clean = (
        "Post the review of record as a PR review, never as an issue comment.",
        "Do not post the review of record as an issue comment.",
        "If the host denies the review of record, do not fall back to an issue comment: report the exact command and the denial.",
        "The review of record is not a PR comment.",
        "Never post the review of record as a pull request comment.",
        "The review-of-record URL is the review's `html_url`, not a PR comment URL.",
        "Post the review of record as one PR review with the comment event,\nnever as an issue comment.",
        "> The review of record is posted as one PR review with the comment event, never as\n> an issue comment.",
        "> The review of record is posted as one PR review with the comment event, never as an issue comment.",
    )
    for sentence in clean:
        assert comment_naming_sentences(sentence) == [], f"scan flagged: {sentence!r}"


def test_wording_scan_keeps_separate_list_items_and_commands_apart() -> None:
    clean = (
        "- Post the review of record as a PR review.\n- Post the QA evidence as an issue comment.",
        "1. Post the review of record as a PR review.\n2. Post the QA evidence as a PR comment.",
        "- Post the review of record as a PR review\n- Post the QA evidence as an issue comment",
        'Post the review of record as a PR review, then run `linear issue comment add <ID> --body "done"`.',
        "The review of record is a PR review.\n\nThe QA evidence is posted as an issue comment.",
        "Post the review of record as a PR review.\n\nThen post the QA report as a PR comment.",
    )
    for text in clean:
        assert comment_naming_sentences(text) == [], f"scan flagged: {text!r}"
