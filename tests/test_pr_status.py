"""pr-status.sh reads the review of record from the PR reviews API, not from issue comments."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "engineering-workflow" / "scripts" / "pr-status.sh"
REVIEWS_HEADER = "=== PR reviews ==="
COMMENTS_HEADER = "=== PR issue comments ==="
HEAD = "0123456789abcdef0123456789abcdef01234567"

# A stand-in for gh: it serves canned JSON per endpoint, applies --jq with the real jq (per page for
# --paginate, like gh), logs argv, and fails on any endpoint the script should not call.
FAKE_GH = """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$GH_LOG"
filter=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  if [ "${args[i]}" = "--jq" ]; then filter="${args[i+1]}"; fi
done
if [ "$1" = "api" ]; then
  [ -z "${FAIL_API:-}" ] || { echo "gh: HTTP 500" >&2; exit 1; }
  [ "$2" = "--paginate" ] && [ "$3" = "repos/acme/widgets/pulls/7/reviews" ] || { echo "unexpected api call: $*" >&2; exit 3; }
  for ((p = 0; p < $(jq length "$FIXTURES/reviews.json"); p++)); do
    jq ".[$p]" "$FIXTURES/reviews.json" | jq -r "($filter) | if type == \\"string\\" then . else tojson end"
  done
  exit 0
elif [ "$1 $2" = "pr view" ]; then
  case "$*" in
    *--comments*) src="$FIXTURES/comments.json" ;;
    *"number,url --jq"*)
      [ -z "${FAIL_META:-}" ] || { echo "gh: no pull request found" >&2; exit 1; }
      echo "$META_LINE"
      exit 0 ;;
    *) src="$FIXTURES/pr.json" ;;
  esac
else
  echo "unexpected gh call: $*" >&2; exit 3
fi
if [ -n "$filter" ]; then
  jq -r "($filter) | if type == \\"string\\" then . else tojson end" "$src"
else
  cat "$src"
fi
"""

REVIEWS = [
    {
        "user": {"login": "noahwhite"},
        "state": "COMMENTED",
        "commit_id": HEAD,
        "submitted_at": "2026-10-22T18:00:00Z",
        "html_url": "https://github.com/acme/widgets/pull/7#pullrequestreview-11",
        "body": f"Review of record {HEAD}\nReviewer: Codex\nAdjudicator: Opus",
    },
    {
        "user": {"login": "other"},
        "state": "APPROVED",
        "commit_id": HEAD,
        "submitted_at": "2026-10-22T18:05:00Z",
        "html_url": "https://github.com/acme/widgets/pull/7#pullrequestreview-12",
        "body": "",
    },
]
COMMENTS = {
    "comments": [
        {
            "author": {"login": "noahwhite"},
            "body": "CI note, not a review",
            "createdAt": "2026-10-22T17:00:00Z",
            "url": "https://github.com/acme/widgets/pull/7#issuecomment-5",
        }
    ]
}
PR = {"number": 7, "url": "https://github.com/acme/widgets/pull/7", "state": "OPEN"}
META = "7 https://github.com/acme/widgets/pull/7"


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
    log = tmp_path / "gh.log"

    def go(reviews=REVIEWS, fail_api=False, fail_meta=False, meta=META, comments=COMMENTS):
        pages = reviews if reviews and isinstance(reviews[0], list) else [reviews]
        (fixtures / "reviews.json").write_text(json.dumps(pages))
        (fixtures / "comments.json").write_text(json.dumps(comments))
        (fixtures / "pr.json").write_text(json.dumps(PR))
        log.write_text("")
        env = {
            **os.environ,
            "PATH": f"{bindir}:{os.environ['PATH']}",
            "FIXTURES": str(fixtures),
            "GH_LOG": str(log),
            "META_LINE": meta,
        }
        if fail_api:
            env["FAIL_API"] = "1"
        if fail_meta:
            env["FAIL_META"] = "1"
        done = subprocess.run(
            ["bash", str(SCRIPT)], cwd=consumer, env=env, capture_output=True, text=True, timeout=30
        )
        return done, log.read_text().splitlines()

    return go


def split_sections(stdout: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in stdout.splitlines():
        if line.startswith("=== "):
            current = line
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def test_prints_pr_reviews_before_issue_comments(run) -> None:
    done, _ = run()
    assert done.returncode == 0, done.stderr
    headers = [l for l in done.stdout.splitlines() if l.startswith("=== ")]
    assert headers == [REVIEWS_HEADER, COMMENTS_HEADER]


def test_reviews_section_lists_author_state_commit_time_and_body(run) -> None:
    done, _ = run()
    rows = [json.loads(l) for l in split_sections(done.stdout)[REVIEWS_HEADER] if l.strip()]
    assert [r["author"] for r in rows] == ["noahwhite", "other"]
    record = rows[0]
    assert record["state"] == "COMMENTED"
    assert record["commit_id"] == HEAD
    assert record["submitted_at"] == "2026-10-22T18:00:00Z"
    assert record["body"].splitlines()[0] == f"Review of record {HEAD}"
    assert record["html_url"].endswith("#pullrequestreview-11")


def test_reviews_come_from_the_paginated_reviews_endpoint(run) -> None:
    _, log = run()
    assert "api --paginate repos/acme/widgets/pulls/7/reviews" in " | ".join(log)


def test_issue_comments_keep_their_own_section_without_the_reviews(run) -> None:
    done, _ = run()
    comments = "\n".join(split_sections(done.stdout)[COMMENTS_HEADER])
    assert "CI note, not a review" in comments
    assert "Review of record" not in comments


def test_no_reviews_prints_an_empty_reviews_section(run) -> None:
    done, _ = run(reviews=[])
    assert done.returncode == 0, done.stderr
    assert [l for l in split_sections(done.stdout)[REVIEWS_HEADER] if l.strip()] == []


def test_reviews_api_failure_fails_the_script(run) -> None:
    done, _ = run(fail_api=True)
    assert done.returncode != 0
    assert COMMENTS_HEADER not in done.stdout


def test_reviews_across_pages_are_all_listed(run) -> None:
    second = {**REVIEWS[1], "user": {"login": "third"}, "html_url": "https://github.com/acme/widgets/pull/7#pullrequestreview-13"}
    done, _ = run(reviews=[REVIEWS, [second]])
    assert done.returncode == 0, done.stderr
    rows = [json.loads(l) for l in split_sections(done.stdout)[REVIEWS_HEADER] if l.strip()]
    assert [r["author"] for r in rows] == ["noahwhite", "other", "third"]


def test_pr_url_with_a_trailing_slash_resolves_the_same_endpoint(run) -> None:
    done, log = run(meta="7 https://github.com/acme/widgets/pull/7/")
    assert done.returncode == 0, done.stderr
    assert "api --paginate repos/acme/widgets/pulls/7/reviews" in " | ".join(log)


@pytest.mark.parametrize(
    "meta",
    [
        "",
        "7",
        "7 not-a-url",
        "x https://github.com/acme/widgets/pull/7",
        "7 https://github.com/acme/widgets/issues/7",
        "7 https://github.com/acme/widgets/pull/8",
        "x https://github.com/acme/widgets/pull/x",
    ],
)
def test_unparseable_pr_metadata_fails_closed(run, meta) -> None:
    done, log = run(meta=meta)
    assert done.returncode == 12
    assert "Could not derive owner/repo and number" in done.stderr
    assert not any(l.startswith("api ") for l in log)
    assert REVIEWS_HEADER not in done.stdout


def test_failing_pr_metadata_call_fails_closed(run) -> None:
    done, log = run(fail_meta=True)
    assert done.returncode == 12
    assert "Could not read the current PR's number and URL" in done.stderr
    assert not any(l.startswith("api ") for l in log)


def test_zero_issue_comments_still_prints_the_section(run) -> None:
    done, _ = run(comments={"comments": []})
    assert done.returncode == 0, done.stderr
    assert COMMENTS_HEADER in done.stdout
    assert [l for l in split_sections(done.stdout)[COMMENTS_HEADER] if l.strip()] == []


def test_script_no_longer_says_the_review_of_record_is_an_issue_comment() -> None:
    text = SCRIPT.read_text()
    assert "review of record is posted as an issue comment" not in text
    assert "=== PR comments" not in text
    assert REVIEWS_HEADER in text
    assert COMMENTS_HEADER in text
    assert "gh api --paginate" in text
    assert "/pulls/${NUMBER}/reviews" in text
