---
name: qa-verification
description: >-
  Verify an already-deployed Linear story's acceptance criteria and Definition of Done against a live, non-production environment, capture reproducible evidence (structured assertions, plus screenshots for anything a user sees), record it on the story and in the repository, and decide whether the story moves to Done, back to In Progress, or to Blocked.
  Use when asked to QA, verify, validate, acceptance-test, deployment-review, post-deploy check, or run QA against a story that is in deployment review, or to check whether a story's acceptance criteria hold in a deployed environment (for example "does ABC-123 pass on dev?").
  Not for building, fixing, or reviewing code (use engineering-workflow), deploying or operating infrastructure (use persona-platform-sre), or backlog and scope decisions (use persona-product-owner).
license: Apache-2.0
compatibility: Requires git, gh, and the linear CLI (schpet/linear-cli); browser automation (for example Playwright) for UI lanes.
---

# QA verification

This is the post-deploy counterpart to `engineering-workflow`, which ends at merge, deploy, and `profile.tracker.states.in_deployment_review`.
This workflow starts there: it validates a deployed story's acceptance criteria (AC) and Definition of Done (DoD) against the live environment, with reproducible evidence, then decides the story's next state.
It verifies deployed behavior; it never builds or reviews code changes.
When this workflow runs as a delegated QA agent, that agent is clean and neutral as `references/code-review.md` defines: briefed with the story identifier, the environment, and the AC and DoD only, never the implementer's view or expected verdicts.

## Read first

- [references/profile.md](references/profile.md) - find the profile and this skill's overlay before anything else.
  The overlay supplies the QA runner or workstation, each lane's access path and credentials source, fixture accounts, and any runbooks.
- [references/todo-tracking.md](references/todo-tracking.md) - required before step 1: one item per AC and per DoD box (verify, capture evidence), each lane setup, the evidence PR, and the status decision.
- [references/linear.md](references/linear.md) - steps 1, 4, and 6: status lifecycle, checkbox completion, never done on merge, and a failed deployment review reopening the story.
- [references/secrets.md](references/secrets.md) - every credential a lane uses.
- [references/code-review.md](references/code-review.md) and [references/github.md](references/github.md) - step 5: the evidence PR's review of record, signing, and merge.
- [references/runtimes.md](references/runtimes.md) - maps the capabilities named here to your runtime.

When a finding needs a code fix, hand it to `engineering-workflow` (and its [references/engineering-practice.md](references/engineering-practice.md)); QA verifies, it does not implement.

## The environment under test

- Verify against the environment the user names, else the first entry in `profile.environments` whose `production` is not true.
  Never run QA mutations against an environment with `profile.environments[].production` set.
- Confirm the deployed build before testing, with that environment's `profile.environments[].verify` value, and record the build SHA.
  If the story's merge is not in the deployed build, stop: the story is not yet testable there.
- Lanes are the surfaces you verify through.
  Typical lanes: the customer-facing UI (authenticated browser automation against `profile.environments[].url`), an operator or admin read view, backend signal (logs and traces), a payment or billing provider's sandbox, and repository and tracker state (`gh`, `linear`).
  The overlay names the lanes this project has and how each is reached.
- QA credentials are read-only where the lane allows it, come from the secrets manager at run time, and are never written to disk, argv, logs, or evidence.
  A payment lane uses the provider's sandbox only, never live.
- When logs or metrics are shared between environments, always filter by the environment label.
- If the overlay provides a smoke check across all lanes, run it first and confirm every lane is green before per-story work.

## 1. Read the story and enumerate what to verify

1. Read the story completely: every AC, the DoD, comments, earlier deployment-review notes, and linked stories.
2. List each AC and DoD item and mark it: verifiable now, already verified by its owner, or blocked.
3. **Dependency status rule.**
   When an item is annotated as delivered by, blocked on, or closing with another story, check that story's current status.
   If it has merged and deployed to the environment under test (it is in `profile.tracker.states.in_deployment_review` or `profile.tracker.states.done` there), verify the item directly.
   Flag an item blocked only when its dependency is not yet deployed to that environment.

## 2. Map each AC to a lane and pick fixtures

- Choose the lane per item: customer-facing behavior on the UI lane, operator read views on the operator lane, backend events and telemetry on logs and traces, billing on the payment sandbox, and CI or repository state on GitHub and Linear.
- Pick a fixture account whose data has the shape the item needs.
  Enumerate the fixtures the overlay lists and confirm their current shape, since fixture data drifts; do not assume the default QA account is the only one reachable.
- If no fixture has the required shape, say so, and prefer seeding a named, reusable fixture over synthesizing per-run state.

## 3. Drive the surface and capture evidence

1. Write a probe (browser automation or a lane CLI) and run it under the QA identity on the QA runner or workstation the overlay names.
   Keep probes in the scratch directory or on the runner, never in the repository.
2. Capture structured assertions for every item (text or selectors present, counts, status codes, command output).
   For an item a user sees, add a screenshot: assertions make pass or fail legible, and the screenshot lets a human check the pixels.
   For an item with no visual surface (an API, a job, a CLI), the assertions and their raw output are the evidence; do not invent a screenshot.
3. **Never perform a mutating confirm merely to reach a read-only check.**
   Preview and read are safe; create, pay, provision, and delete are not.
   If the item under test is itself a mutation, exercise it only in a sandbox, only when explicitly authorized, and prefer a reversible fixture.
4. Be picky about the UI: alignment, spacing, truncation, and interactive affordances.
   Note any visible defect, even an incidental one.
5. **Fault injection stays read-only.**
   To exercise a timeout, degraded, or error-path item without touching the backend, intercept the client request in the browser (for example Playwright's `page.route(...)`) and abort it, or hold it past the latency budget and then abort it, and confirm the UI's fallback renders.
   A delayed or aborted read request changes nothing server-side.
   Check first that the value really comes from a client request: a value resolved server-side inside another response has nothing to intercept, and its fallback is a unit or integration test concern, not this lane.

## 4. Adjudicate and record

1. Map every AC and DoD item to its evidence with a verdict: verified, correct by design, out of scope (naming the owning story), or not covered.
2. **Spot-check self-reported coverage claims.**
   If an earlier QA pass left a gap as unit-only or not reproducible live, and a later PR claims to close it, read the merged diff and confirm the new test drives the guarded code path through a realistic caller and asserts the specific failure the gap described.
   This is a diff read, not a rebuild: rerunning or mutating the suite is `engineering-workflow`'s job, and a green local run says nothing about what runs in the environment under test.
   If the diff does not hold up, the gap stays open.
3. Post a concise QA evidence comment on the story: build SHA, environment, fixtures used, per-item verdict, and any gaps.
4. If the runtime can publish a hosted page, publish an evidence page with the screenshots and per-item verdicts and give the user the link; also deliver the raw screenshots to the user directly.
   Every screenshot on the page must be zoomable: click opens it full screen at natural resolution, Esc or a click outside closes it.
   An evidence page with screenshots scaled to cards is incomplete.

## 5. Check the evidence into the repository

Commit the evidence for every story you QA, not only when asked, under `profile.qa.evidence_dir` in a directory named for the story identifier.
If `profile.qa.evidence_dir` is unset, the project does not keep in-repo evidence; skip this step and say so in the report.

- The evidence directory holds only a short `README.md` (metadata, fixtures, per-item verdict table, one sentence per line) and the screenshots it cites.
  No probe scripts, scratch files, or bulk captures.
- Ship it through the normal branch and PR flow in `references/github.md`, signed when `profile.git.signed_commits` is true, and verify the signature after pushing.
- **Never merge the evidence PR before its review of record is complete at the current head.**
  The review of record is `profile.review.reviewer`, then a separate clean, neutral `profile.review.adjudicator`, as `references/code-review.md` defines.
  Never hand the reviewer or the adjudicator your QA verdicts.
  A docs-only diff, green checks, a long wait, or user frustration do not waive the gate; if you cannot get a review, hold and say so.
- Fix what the adjudicator rules valid, and post the review-of-record comment on the PR before the merge, never after.
- Merge only on the exact final head with CI finished, never by an admin override over pending checks, and per `profile.review.merge_owner` (hand the merge to the user when it is `human`).
- Evidence counts as checked in only once the PR is merged; an open PR is not checked in.

## 6. Decide status

- **QA not finished: stay in `profile.tracker.states.in_deployment_review`.**
  A pending owner action, a live trigger still to run, or missing access means QA is in flight, not that the story failed.
  State exactly what remains and who owns it, and finish the verification when it is done.
- Once QA is finished, the story ends in exactly one state:
  - **`profile.tracker.states.done`**: every AC and DoD item is verified as met, and the evidence PR is merged (when in-repo evidence is kept).
    Tick the boxes you verified.
    Never mark done on merge alone, and never split or reword a story to close it.
  - **`profile.tracker.states.in_progress`**: an item failed because the delivered work did not meet it.
    Reopen this story per `references/linear.md`, amend the AC with a dated deployment-review note, and hand the fix to `engineering-workflow`; never file a new bug for it.
  - **`profile.tracker.states.blocked`**: the story is blocked by another story that must complete first.
    Record the blocking story in the body.

## Operating rules

- Verify, do not assert: state results from probe output, not from expectation.
- Report faithfully: if a lane is red or an item could not be exercised, say so and why.
- Keep the user informed at major steps, not at every command.

## Completion summary

Report: the story and its final state; each AC and DoD verdict with its evidence; the fixtures and build SHA used; the evidence page link and evidence PR; and any item left outstanding with its owning story.
