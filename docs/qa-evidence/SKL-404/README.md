# SKL-404 QA evidence

- Story: [SKL-404](https://linear.app/officina-pub/issue/SKL-404/user-story-shard-the-pre-pr-hunt-so-each-request-covers-a-candidate)
- Path: `no-deployment`
- Target: `c39558c9f4c57c0eb36fb711d8410c599eaed3c4`, confirmed on `origin/main`
- Implementation: [PR #398](https://github.com/noahwhite/agent-skills/pull/398), reviewed head `68f8bde8612b199d1132dd3ece54d7802dc1e986`
- Evidence: [QA comment and raw assertion attachments](https://linear.app/officina-pub/issue/SKL-404/user-story-shard-the-pre-pr-hunt-so-each-request-covers-a-candidate#comment-1ac401b6)

QA inspected the merged artifacts and ran isolated stand-in reports without starting a model or creating any fixture commits.
The story was returned to In Progress because AC1 failed.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1: shard invocation | Failed | Switching between explicit `--shard 1/1` and an omitted flag between dossier and record exits 0 and stamps the report in both directions, despite the exact same-flag requirement. |
| AC5: stop contract | Pending owner ruling | The failure exits 17 and leaves its sibling stamp unchanged; arbitration refuses shard `1/2` with exit 13, but the reciprocal scope note on SKL-383 is absent and AC5 and Additional Context give different readings of when it is due. |
| AC6: stand-in tests | Verified | The landed test module covers the listed cases; the PR records 43 focused passes and 3,922 full-suite passes. |
| AC8: guards | Verified | The PR records the local guards and [exact-head checks and discovery](https://github.com/noahwhite/agent-skills/actions/runs/45044072463) passed, including the repository suite and the private leak scan. |
| DoD: all acceptance criteria met | Failed | The AC1 same-flag mismatch is reproducible at the merged target. |
| DoD: tests written and passing | Verified | Both required signals are recorded on the implementation PR head: the full local suite and CI Repository tests. |
| DoD: independently reviewed | Failed under the clean-gate policy | The [posted review](https://github.com/noahwhite/agent-skills/pull/398#pullrequestreview-6013287825) is at the correct head and used two seats, but deferred a valid in-scope Low without a fix. |
| DoD: docs updated | Verified | The script header and the skill document shard usage, names, resets, and the driver stop and record rules. |
| DoD: verified in a deployed environment | Correct by design | No environment exists on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified in scope | None surfaced in the independent review, exact-head CI, or isolated runtime probes. |

The deferred Low is unbounded plan growth for very large valid shard counts.
The probe also found no model sidecar after accepting a named-model shard; AC1 lists the file and points to AC4, whose model provenance behavior belongs to SKL-408.
