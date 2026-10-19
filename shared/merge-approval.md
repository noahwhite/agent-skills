# Merge approval handshake

A delegated engineer whose manager owns merge approval requests that approval before it merges, and the manager answers the request.
This file defines the handshake once so a brief does not invent its own.
`engineering-workflow` and `persona-staff-engineer` both link here.

## When it applies

- It applies when the brief names a manager who owns merge approval and gives the engagement's approvals-file path.
- It takes precedence over the autonomous merge rule: the engineer prepares the merge, but it does not merge until the matching approval is recorded.
- It does not change a direct human merge under `profile.review.merge_owner` when no manager and approvals file were named in the brief.
- It is the delegated-approval case only; every other merge keeps the rule in `references/github.md` and `references/code-review.md`.

## Approvals file: location and ownership

- The manager names one absolute path in the brief and creates the file before delegating.
  The normal path is `<profile.workspace.scratch_dir>/<engagement>/merge-approvals.md`, where `<engagement>` is the story key and a short engagement label.
- Both sides use that exact path for the whole engagement.
- The manager owns the file and is the only writer of `APPROVE` and `BOUNCE` records.
- The engineer is the only writer of `REQUEST` records.
- The file is append-only: never edit, reorder, or delete a record.
- If the file is missing, the engineer stops and reports the engagement blocked.
  It does not create the file or invent a decision.

## Request ID

- The request ID is `REQ-<story-key>-PR<number>-<n>`, where `<n>` starts at 1 for the engagement and increases by one for every request, including a re-request.
- The request ID is unique within the engagement and is never reused.
- Every record carries the request ID and the full 40-character head SHA it concerns.

## Record formats

Write one record per line.
Separate fields with ` | `, and never put a pipe inside a field.
Write timestamps in UTC as `YYYY-MM-DDTHH:MM:SSZ`.

| Record | Format |
|---|---|
| Request | `REQUEST \| <request-id> \| <PR URL> \| <full head SHA> \| <review-of-record URL> \| <CI state> \| <timestamp>` |
| Approve | `APPROVE \| <request-id> \| <full head SHA> \| <manager identity> \| <timestamp>` |
| Bounce | `BOUNCE \| <request-id> \| <full head SHA> \| <manager identity> \| <reason> \| <timestamp>` |

- The request names the request ID, the PR, the full head SHA, the review-of-record link, and the CI state.
- The CI state is `green` only when every required check passes; the engineer only asks when the merge bar holds, so a request with `pending` or `failing` is invalid.
- The review-of-record URL is the PR comment that records the review at that head, not the PR URL alone.
- The manager identity is the manager's session label.

## Idempotency on request ID plus head SHA

- A decision is identified by its request ID and its full head SHA together.
- An identical duplicate record is ignored.
- The manager handles a request at most once per request ID and head SHA: it reads the file for an existing decision on that pair before writing, and if one exists it writes nothing and does not wake again.
- A decision whose head SHA differs from the request's head SHA is invalid and never authorizes a merge.
- If two conflicting decisions exist for one pair, the first in file order wins and the conflict is reported.

## Wake capability and its per-runtime mapping

- After appending the request, the engineer delivers the same request through the wake capability.
  The delivery names the request ID, the PR, the full head SHA, the review-of-record URL, and the CI state.
- The wake capability maps as follows:

| Runtime | Wake capability |
|---|---|
| Claude Code | `SendMessage` to the manager's session. |
| opencode | No push capability; the approvals file plus the manager's watcher is the delivery path. |
| A runtime not listed | Map to its closest push capability and say which one was used; if it has none, the approvals file plus the manager's watcher is the delivery path. |

- The file is the record; the wake is only a prompt to read it.
- A failed or unconfirmed wake never substitutes for an approval, and it never stops the request from being recorded.

## Waiting for a decision

- The engineer polls the approvals file at least every 60 seconds until a decision for its request ID and current head SHA appears.
- While it waits it does not merge, and it does not end its turn silently.
- A matching `APPROVE` authorizes the merge only after the engineer re-reads the live PR and confirms the head SHA still equals the approved head SHA, the required checks are green, and the PR is mergeable.
- A matching `BOUNCE` stops the merge; the engineer addresses the reason or hands back.
- A decision for any other request ID or head SHA is ignored.
- If the head changes while the engineer waits, it stops waiting and follows the re-request rule.
- If the runtime cannot keep the turn open, the handback states that the work is blocked on merge approval and names the request ID, the PR, and the head SHA.

## Base-only update rule

- A base-only update is updating the PR branch from its base branch without any other change.
- A base-only update that changes the head SHA invalidates any request or approval for the previous head.
  The engineer re-requests with a new request ID and the new full head SHA.
- A base-only update that leaves the head SHA unchanged leaves the approval standing.
- The engineer never merges on an approval for a different head, and it never updates the base after an approval without re-requesting.

## Re-request rule when the head changes

- Any head change after a request or an approval requires a new request: a fix push, an amend, a rebase, or a base-only update.
- The new request uses a new request ID and names the new full head SHA.
- Before re-requesting, the engineer confirms the review of record covers the new head and the required checks are green, as `references/code-review.md` requires.
- An old approval is never reused for a new head.

## Dry-run walkthrough

```
REQUEST | REQ-SKL-4-PR12-1 | https://github.com/org/repo/pull/12 | 0123456789abcdef0123456789abcdef01234567 | https://github.com/org/repo/pull/12#issuecomment-1 | green | 2026-10-19T04:20:00Z
BOUNCE | REQ-SKL-4-PR12-1 | 0123456789abcdef0123456789abcdef01234567 | staff-engineer | review of record is not posted for this head | 2026-10-19T04:20:30Z
REQUEST | REQ-SKL-4-PR12-2 | https://github.com/org/repo/pull/12 | 0123456789abcdef0123456789abcdef01234567 | https://github.com/org/repo/pull/12#issuecomment-2 | green | 2026-10-19T04:24:00Z
APPROVE | REQ-SKL-4-PR12-2 | 0123456789abcdef0123456789abcdef01234567 | staff-engineer | 2026-10-19T04:25:00Z
REQUEST | REQ-SKL-4-PR12-3 | https://github.com/org/repo/pull/12 | 89abcdef0123456789abcdef0123456789abcdef | https://github.com/org/repo/pull/12#issuecomment-3 | green | 2026-10-19T04:40:00Z
APPROVE | REQ-SKL-4-PR12-3 | 89abcdef0123456789abcdef0123456789abcdef | staff-engineer | 2026-10-19T04:41:00Z
```

- Request 1 is bounced because the review of record was not posted for that head.
- Request 2 is approved at the same head after the review of record is posted.
- A base-only update then moves the head from the first SHA to the second, so request 3 is a new request and its approval is the only one that authorizes the merge at the new head.
