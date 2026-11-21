"""SKL-388: merge-pr.sh reads the reviews and checks, verifies the review of record, and merges guarded."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "engineering-workflow" / "scripts" / "merge-pr.sh"

HEAD = "0123456789abcdef0123456789abcdef01234567"
MOVED = "89abcdef0123456789abcdef0123456789abcdef"
MERGED_COMMIT = "fedcba9876543210fedcba9876543210fedcba98"
URL = "https://github.com/acme/widgets/pull/7"
REVIEW_URL = "https://github.com/acme/widgets/pull/7#pullrequestreview-11"
REVIEWS_END = "repos/acme/widgets/pulls/7/reviews"

# A stand-in for gh: it serves canned JSON per call, applies --jq with the real jq (per page for
# --paginate, like gh), logs argv, and fails on any call the script should not make.
FAKE_GH = r"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$GH_LOG"
filter=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  if [ "${args[i]}" = "--jq" ]; then filter="${args[i+1]}"; fi
done

case "${1:-}" in
  api)
    case "${2:-}" in
      user)
        [ -z "${FAIL_USER:-}" ] || { echo "gh: authentication required" >&2; exit 1; }
        printf '%s\n' "${LOGIN:-}"
        exit 0
        ;;
      --paginate)
        [ -z "${FAIL_REVIEWS:-}" ] || { echo "gh: HTTP 500" >&2; exit 1; }
        [ "${3:-}" = "$REVIEWS_PATH" ] || { echo "unexpected api path: ${3:-}" >&2; exit 3; }
        for ((p = 0; p < $(jq length "$FIXTURES/reviews.json"); p++)); do
          if [ -n "$filter" ]; then
            jq ".[$p]" "$FIXTURES/reviews.json" | jq -c "$filter"
          else
            jq -c ".[$p]" "$FIXTURES/reviews.json"
          fi
        done
        exit 0
        ;;
      *) echo "unexpected api call: $*" >&2; exit 3 ;;
    esac
    ;;
  pr)
    case "${2:-}" in
      view)
        [ -z "${FAIL_PR:-}" ] || { echo "gh: no pull requests found" >&2; exit 1; }
        case "$*" in
          *state,mergedAt,mergeCommit*) cat "$FIXTURES/confirm.json" ;;
          *headRefOid*) cat "$FIXTURES/pr.json" ;;
          *) echo "unexpected pr view: $*" >&2; exit 3 ;;
        esac
        exit 0
        ;;
      checks)
        [ -z "${FAIL_CHECKS:-}" ] || { echo "gh: HTTP 500" >&2; exit 1; }
        [ -z "${NO_REQUIRED_CHECKS:-}" ] || { echo "no required checks reported on the 'x' branch" >&2; exit 1; }
        cat "$FIXTURES/checks.json"
        exit "${CHECKS_EXIT:-0}"
        ;;
      merge)
        if [ "${3:-}" = "--help" ]; then cat "$FIXTURES/merge-help.txt"; exit 0; fi
        [ -z "${FAIL_MERGE:-}" ] || { echo "${FAIL_MERGE}" >&2; exit 1; }
        printf 'merged\n'
        exit 0
        ;;
      *) echo "unexpected pr call: $*" >&2; exit 3 ;;
    esac
    ;;
  *) echo "unexpected gh call: $*" >&2; exit 3 ;;
esac
"""

PROFILE = """\
version: 1
git:
  integration_branch: main
  merge_method: squash
review:
  merge_owner: agent
  record_author: record-author
"""


def review(head=HEAD, author="record-author", state="COMMENTED", submitted="2026-11-20T18:00:00Z", body=None):
    return {
        "user": {"login": author},
        "state": state,
        "commit_id": head,
        "submitted_at": submitted,
        "html_url": REVIEW_URL,
        "body": f"Review of record {head}\nreviewer and adjudicator\n" if body is None else body,
    }


def pr_payload(head=HEAD, mergeable="MERGEABLE", state="CLEAN", pr_state="OPEN"):
    return {
        "number": 7,
        "url": URL,
        "state": pr_state,
        "isDraft": pr_state == "DRAFT",
        "mergeable": mergeable,
        "mergeStateStatus": state,
        "headRefOid": head,
    }


def check(name="ci/test", state="SUCCESS"):
    return {"name": name, "state": state, "bucket": "pass" if state == "SUCCESS" else state.lower()}


@pytest.fixture
def run(tmp_path):
    if shutil.which("jq") is None:
        if os.environ.get("CI"):
            pytest.fail("jq is required to apply the --jq filters and must be installed in CI")
        pytest.skip("jq is required to apply the --jq filters")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    subprocess.run(["git", "init", "-q", str(consumer)], check=True)
    profile = tmp_path / "profile.yaml"
    log = tmp_path / "gh.log"

    def go(
        *,
        reviews=None,
        pr=None,
        checks=None,
        merge_help=True,
        checks_exit=0,
        fail_merge="",
        confirm=None,
        login="record-author",
        fail_user=False,
        profile_text=PROFILE,
        profile_path="env",
        skills_repo=False,
        args=(),
        cwd=None,
        extra_env=None,
    ):
        pages = reviews if reviews and isinstance(reviews[0], list) else [reviews or []]
        (fixtures / "reviews.json").write_text(json.dumps(pages))
        (fixtures / "pr.json").write_text(json.dumps(pr or pr_payload()))
        (fixtures / "checks.json").write_text(json.dumps(checks if checks is not None else [check()]))
        (fixtures / "confirm.json").write_text(
            json.dumps(
                confirm
                if confirm is not None
                else {"state": "MERGED", "mergedAt": "2026-11-20T19:00:00Z", "mergeCommit": {"oid": MERGED_COMMIT}}
            )
        )
        help_line = "--match-head-commit SHA   Commit SHA that the pull request head must match to allow merge"
        (fixtures / "merge-help.txt").write_text(
            "USAGE\n  gh pr merge [<number> | <url> | <branch>] [flags]\n\nFLAGS\n"
            + (f"      {help_line}\n" if merge_help else "  -s, --squash   Squash the commits into one\n")
        )
        if skills_repo:
            (consumer / "shared").mkdir()
            (consumer / "skills.json").write_text("[]\n")
            (consumer / "shared" / "runtimes.md").write_text("map\n")
        if profile_text is not None:
            profile.write_text(profile_text)
        log.write_text("")
        env = {
            **os.environ,
            "PATH": f"{bindir}:{os.environ['PATH']}",
            "FIXTURES": str(fixtures),
            "GH_LOG": str(log),
            "REVIEWS_PATH": REVIEWS_END,
            "LOGIN": login,
        }
        env.pop("AGENT_SKILLS_PROFILE", None)
        if profile_path == "env":
            env["AGENT_SKILLS_PROFILE"] = str(profile)
        elif profile_path == "repo":
            local = consumer / ".agent-skills"
            local.mkdir()
            (local / "profile.yaml").write_text(profile_text)
            env["HOME"] = str(tmp_path / "home")
        elif profile_path == "home":
            home = tmp_path / "home"
            (home / ".config" / "agent-skills").mkdir(parents=True)
            (home / ".config" / "agent-skills" / "profile.yaml").write_text(profile_text)
            env["HOME"] = str(home)
        else:
            env["HOME"] = str(tmp_path / "empty-home")
        if fail_user:
            env["FAIL_USER"] = "1"
        if fail_merge:
            env["FAIL_MERGE"] = fail_merge
        env["CHECKS_EXIT"] = str(checks_exit)
        env.update(extra_env or {})
        done = subprocess.run(
            ["bash", str(SCRIPT), "7", "--repo", str(consumer), *args],
            cwd=str(cwd or consumer),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return done, log.read_text().splitlines()

    return go


def calls(log):
    return " | ".join(log)


def merged(log):
    return [ln for ln in log if ln.startswith("pr merge 7")]


# --- Slice 1: invocation, profile read, PR read, expected-author resolution ---------------------


def test_a_pr_number_is_required(tmp_path):
    done = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 2
    assert "usage" in done.stderr.lower()


def test_refuses_the_skills_repository_unless_repo_names_it(tmp_path):
    skills = tmp_path / "skillsrepo"
    (skills / "shared").mkdir(parents=True)
    (skills / "skills.json").write_text("[]\n")
    (skills / "shared" / "runtimes.md").write_text("map\n")
    subprocess.run(["git", "init", "-q", str(skills)], check=True)
    done = subprocess.run(
        ["bash", str(SCRIPT), "7"],
        cwd=str(skills),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 2
    assert "skills repository" in done.stderr


def test_targets_the_skills_repository_when_repo_names_it_explicitly(run):
    done, log = run(reviews=[review()], skills_repo=True)
    assert done.returncode == 0, done.stderr
    assert len(merged(log)) == 1


def test_missing_profile_fails_closed_naming_the_locations(run):
    done, log = run(profile_path="none")
    assert done.returncode == 13
    assert "profile" in done.stderr
    assert "AGENT_SKILLS_PROFILE" in done.stderr
    assert ".agent-skills/profile.yaml" in done.stderr
    assert "~/.config/agent-skills/profile.yaml" in done.stderr
    assert log == []


@pytest.mark.parametrize("field", ["merge_owner", "merge_method"])
def test_a_missing_profile_key_fails_closed_naming_it(run, field):
    if field == "merge_owner":
        text = "version: 1\ngit:\n  merge_method: squash\nreview:\n  record_author: record-author\n"
        key = "review.merge_owner"
    else:
        text = "version: 1\nreview:\n  merge_owner: agent\n"
        key = "git.merge_method"
    done, log = run(profile_text=text)
    assert done.returncode == 13
    assert key in done.stderr
    assert log == []


@pytest.mark.parametrize("location", ["repo", "home"])
def test_reads_the_profile_from_the_other_two_locations(run, location):
    done, log = run(profile_path=location)
    assert "pr view 7" in calls(log), done.stderr


def test_falling_back_to_the_authenticated_login_reads_it_with_gh(run):
    text = "version: 1\ngit:\n  merge_method: squash\nreview:\n  merge_owner: agent\n"
    done, log = run(profile_text=text, login="record-author")
    assert "api user --jq .login" in calls(log), done.stderr
    assert "pr view 7" in calls(log)


def test_refuses_when_no_expected_author_can_be_resolved(run):
    text = "version: 1\ngit:\n  merge_method: squash\nreview:\n  merge_owner: agent\n"
    done, log = run(profile_text=text, login="")
    assert done.returncode != 0
    assert "expected author" in done.stderr
    assert merged(log) == []


def test_refuses_when_the_authenticated_login_read_fails(run):
    text = "version: 1\ngit:\n  merge_method: squash\nreview:\n  merge_owner: agent\n"
    done, log = run(profile_text=text, fail_user=True)
    assert done.returncode != 0
    assert "expected author" in done.stderr
    assert merged(log) == []


def test_a_failing_pr_read_fails_closed(run):
    done, log = run(extra_env={"FAIL_PR": "1"})
    assert done.returncode != 0
    assert "Could not read" in done.stderr
    assert merged(log) == []


# --- Slice 2: reviews read, review-of-record selection, and the moved-head refusal ---------------


def test_refuses_a_moved_head_and_names_both_shas(run):
    done, log = run(reviews=[review(head=MOVED)])
    assert done.returncode != 0
    assert HEAD in done.stderr and MOVED in done.stderr
    assert "review of record" in done.stderr.lower()
    assert merged(log) == []


def test_refuses_a_first_line_sha_that_does_not_match_the_head(run):
    body = f"Review of record {MOVED}\nreviewer and adjudicator\n"
    done, log = run(reviews=[review(body=body)])
    assert done.returncode != 0
    assert HEAD in done.stderr and MOVED in done.stderr
    assert merged(log) == []


def test_refuses_without_a_review_of_record(run):
    done, log = run(reviews=[])
    assert done.returncode != 0
    assert "no review of record" in done.stderr.lower()
    assert merged(log) == []


def test_reads_the_reviews_with_the_paginated_endpoint(run):
    _, log = run(reviews=[review()])
    assert f"api --paginate {REVIEWS_END}" in calls(log)


def test_selects_the_greatest_submitted_at_across_pages(run):
    # A newer review at a moved head beats an older review at the live head.
    done, log = run(
        reviews=[
            [review(head=HEAD, submitted="2026-11-20T18:00:00Z")],
            [review(head=MOVED, submitted="2026-11-20T18:05:00Z")],
        ]
    )
    assert done.returncode != 0
    assert HEAD in done.stderr and MOVED in done.stderr
    assert merged(log) == []


def test_selects_a_review_at_the_live_head_from_the_second_page(run):
    done, log = run(
        reviews=[
            [review(head=MOVED, submitted="2026-11-20T18:00:00Z")],
            [review(head=HEAD, submitted="2026-11-20T18:05:00Z")],
        ]
    )
    assert f"Reviewed head: {HEAD}" in done.stdout, done.stderr
    assert f"Review of record: {REVIEW_URL}" in done.stdout


def test_matches_the_expected_author_case_insensitively(run):
    text = PROFILE.replace("record-author", "Record-Author")
    done, _ = run(profile_text=text, reviews=[review(author="record-author")])
    assert f"Reviewed head: {HEAD}" in done.stdout, done.stderr


def test_refuses_a_marker_review_by_another_author(run):
    done, log = run(reviews=[review(author="someone-else")])
    assert done.returncode != 0
    assert "no review of record" in done.stderr.lower()
    assert "record-author" in done.stderr
    assert merged(log) == []


def test_ignores_a_marker_review_that_is_not_COMMENTED(run):
    done, log = run(reviews=[review(state="APPROVED")])
    assert done.returncode != 0
    assert merged(log) == []


def test_ignores_a_body_that_does_not_begin_with_the_marker(run):
    body = f"Looks good.\nReview of record {HEAD}\n"
    done, log = run(reviews=[review(body=body)])
    assert done.returncode != 0
    assert merged(log) == []


def test_a_failing_reviews_read_fails_closed(run):
    done, log = run(reviews=[review()], extra_env={"FAIL_REVIEWS": "1"})
    assert done.returncode != 0
    assert "Could not read" in done.stderr
    assert merged(log) == []


# --- Slice 3: the required-checks read and the mergeability refusal -----------------------------


@pytest.mark.parametrize("state", ["PENDING", "FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"])
def test_refuses_a_required_check_that_is_not_green(run, state):
    done, log = run(reviews=[review()], checks=[check("ci/test", "SUCCESS"), check("ci/discovery", state)])
    assert done.returncode != 0
    assert "ci/discovery" in done.stderr
    assert state in done.stderr
    assert merged(log) == []


def test_a_pending_checks_exit_code_still_reads_the_check_states(run):
    done, log = run(reviews=[review()], checks=[check("ci/test", "PENDING")], checks_exit=8)
    assert done.returncode != 0
    assert "ci/test" in done.stderr
    assert merged(log) == []


def test_a_failing_checks_read_fails_closed(run):
    done, log = run(reviews=[review()], extra_env={"FAIL_CHECKS": "1"})
    assert done.returncode != 0
    assert "Could not read" in done.stderr
    assert merged(log) == []


@pytest.mark.parametrize("mergeable", ["CONFLICTING", "UNKNOWN"])
def test_refuses_a_pr_that_is_not_mergeable(run, mergeable):
    done, log = run(reviews=[review()], pr=pr_payload(mergeable=mergeable))
    assert done.returncode != 0
    assert "not mergeable" in done.stderr.lower()
    assert merged(log) == []


@pytest.mark.parametrize("state", ["BEHIND", "BLOCKED", "DIRTY", "DRAFT", "UNKNOWN"])
def test_refuses_a_blocking_merge_state(run, state):
    done, log = run(reviews=[review()], pr=pr_payload(state=state))
    assert done.returncode != 0
    assert state in done.stderr
    assert merged(log) == []


def test_prints_each_required_check_state(run):
    done, _ = run(reviews=[review()], checks=[check("ci/test", "SUCCESS"), check("ci/discovery", "SUCCESS")])
    assert "Check: ci/test=SUCCESS" in done.stdout, done.stderr
    assert "Check: ci/discovery=SUCCESS" in done.stdout


def test_no_required_checks_configured_is_not_a_refusal(run):
    done, log = run(reviews=[review()], extra_env={"NO_REQUIRED_CHECKS": "1"})
    assert "Check: none" in done.stdout, done.stderr
    assert len(merged(log)) == 1


def test_no_required_checks_on_the_head_is_not_a_refusal(run):
    done, log = run(reviews=[review()], checks=[])
    assert "Check: none" in done.stdout, done.stderr
    assert len(merged(log)) == 1


def test_refuses_a_pr_that_is_not_open(run):
    done, log = run(reviews=[review()], pr=pr_payload(pr_state="CLOSED"))
    assert done.returncode != 0
    assert "not OPEN" in done.stderr
    assert merged(log) == []


# --- Slice 4: the guarded merge, its confirmation, and the no-unguarded-retry rules -------------

MERGE_PREFIX = f"pr merge 7 --match-head-commit {HEAD}"


@pytest.mark.parametrize("method,flag", [("squash", "--squash"), ("merge", "--merge"), ("rebase", "--rebase")])
def test_merges_with_the_expected_head_and_the_profile_merge_method(run, method, flag):
    text = PROFILE.replace("merge_method: squash", f"merge_method: {method}")
    done, log = run(profile_text=text, reviews=[review()])
    assert done.returncode == 0, done.stderr
    assert merged(log) == [f"{MERGE_PREFIX} {flag}"]


def test_reports_success_only_after_github_confirms_the_merge(run):
    done, log = run(reviews=[review()])
    assert done.returncode == 0, done.stderr
    assert f"Result: merged {MERGED_COMMIT}" in done.stdout
    merge_at = next(i for i, ln in enumerate(log) if ln.startswith("pr merge 7"))
    confirm_at = next(i for i, ln in enumerate(log) if "state,mergedAt,mergeCommit" in ln)
    assert merge_at < confirm_at, calls(log)


def test_a_queued_merge_is_not_success(run):
    done, log = run(reviews=[review()], confirm={"state": "OPEN", "mergedAt": None, "mergeCommit": None})
    assert done.returncode != 0
    assert "not confirmed" in done.stderr
    assert "Result: merged" not in done.stdout
    assert len(merged(log)) == 1


def test_a_failing_merge_is_reported_blocked_without_an_unguarded_retry(run):
    done, log = run(reviews=[review()], fail_merge="failed to update pull request head")
    assert done.returncode != 0
    assert "Result: merge blocked" in done.stdout
    assert len(merged(log)) == 1, calls(log)
    assert merged(log)[0].startswith(MERGE_PREFIX)


def test_refuses_when_the_merge_command_cannot_carry_an_expected_head(run):
    done, log = run(reviews=[review()], merge_help=False)
    assert done.returncode != 0
    assert "--match-head-commit" in done.stderr
    assert merged(log) == [], calls(log)


def test_passes_no_admin_override(run):
    _, log = run(reviews=[review()])
    assert "--admin" not in calls(log)


def test_never_puts_a_token_in_argv_or_output(run):
    done, log = run(reviews=[review()], extra_env={"GH_TOKEN": "s3cr3t-token-value"})
    assert done.returncode == 0, done.stderr
    for text in (" ".join(log), done.stdout, done.stderr):
        assert "s3cr3t-token-value" not in text


# --- Slice 5: the human merge owner and the manager-approval gate -------------------------------


def test_human_merge_owner_stops_without_a_merge_command(run):
    text = PROFILE.replace("merge_owner: agent", "merge_owner: human")
    done, log = run(profile_text=text, reviews=[review()])
    assert done.returncode == 0, done.stderr
    assert merged(log) == []
    assert HEAD in done.stdout and URL in done.stdout and REVIEW_URL in done.stdout
    assert "no merge command" in done.stdout


def test_human_merge_owner_still_refuses_a_stale_review(run):
    text = PROFILE.replace("merge_owner: agent", "merge_owner: human")
    done, log = run(profile_text=text, reviews=[review(head=MOVED)])
    assert done.returncode != 0
    assert merged(log) == []


def approvals_file(tmp_path, records):
    path = tmp_path / "approvals.txt"
    path.write_text("\n".join(records) + "\n")
    return path


REQUEST = "REQ-SKL-388-PR7-1"


def test_a_matching_approve_permits_the_merge(run, tmp_path):
    path = approvals_file(tmp_path, [f"APPROVE | {REQUEST} | {HEAD} | manager | 2026-11-20T19:00:00Z"])
    done, log = run(reviews=[review()], args=("--approvals", str(path), "--request-id", REQUEST))
    assert done.returncode == 0, done.stderr
    assert len(merged(log)) == 1


def test_refuses_without_a_matching_approve(run, tmp_path):
    path = approvals_file(tmp_path, [f"APPROVE | {REQUEST} | {MOVED} | manager | 2026-11-20T19:00:00Z"])
    done, log = run(reviews=[review()], args=("--approvals", str(path), "--request-id", REQUEST))
    assert done.returncode != 0
    assert "APPROVE" in done.stderr and HEAD in done.stderr
    assert merged(log) == []


def test_refuses_a_bounced_request(run, tmp_path):
    path = approvals_file(
        tmp_path, [f"BOUNCE | {REQUEST} | {HEAD} | manager | needs a delta review | 2026-11-20T19:00:00Z"]
    )
    done, log = run(reviews=[review()], args=("--approvals", str(path), "--request-id", REQUEST))
    assert done.returncode != 0
    assert "bounced" in done.stderr and "needs a delta review" in done.stderr
    assert merged(log) == []


def test_refuses_a_missing_approvals_file(run, tmp_path):
    done, log = run(
        reviews=[review()], args=("--approvals", str(tmp_path / "absent.txt"), "--request-id", REQUEST)
    )
    assert done.returncode != 0
    assert "approvals file" in done.stderr
    assert merged(log) == []


def test_a_request_id_without_an_approvals_file_is_a_usage_error(run):
    done, log = run(reviews=[review()], args=("--request-id", REQUEST))
    assert done.returncode == 2
    assert merged(log) == []
