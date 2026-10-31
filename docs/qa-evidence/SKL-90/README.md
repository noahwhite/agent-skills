# SKL-90 QA round 1

- Date: 2026-10-31 UTC.
- Story: [SKL-90](https://linear.app/officina-pub/issue/SKL-90/spike-improve-story-refinement-speed-cost-and-accuracy).
- Environment: Linear tracker deliverables and read-only repository source, not a deployed service.
- Build SHA: not applicable; research source SHA `f7453b3b22feec7e3d1f5928790e9bb23f9f6baf`.
- Fixtures: QA independently captured 167 SKL issues and 792 team-filtered comments before posting its own findings, and separately inspected the two research scripts attached to the story.
- Surface: CLI/API assertions and source records; no visual UI or screenshot applies.
- Outcome: not met; reopen the existing spike to In Progress for correction.
- [QA evidence comment](https://linear.app/officina-pub/issue/SKL-90/spike-improve-story-refinement-speed-cost-and-accuracy#comment-f906f047) includes the source references and ownership.
- Raw assertions and source output are attached as `qa-assertions.txt` and linked from the QA evidence comment; 23 assertions, 14 passed and 9 failed.
- Timing assertions are attached separately as `timing-assertions.json` and linked from the same QA evidence comment.

QA's independent capture used `linear api` with the two queries below, following `pageInfo.endCursor` until `hasNextPage` was false and counting all returned nodes.
The 792 count comes from this team-filtered QA query, not from the research author's unfiltered workspace comment fetch; current counts can change after the captured snapshot.

```graphql
query($after: String) {
  issues(first: 100, after: $after, filter: {team: {key: {eq: "SKL"}}}) {
    nodes { id }
    pageInfo { hasNextPage endCursor }
  }
}
query($after: String) {
  comments(first: 100, after: $after, filter: {issue: {team: {key: {eq: "SKL"}}}}) {
    nodes { id }
    pageInfo { hasNextPage endCursor }
  }
}
```

| Item | Verdict | Evidence |
|---|---|---|
| AC1: complete per-ceremony baseline | Not met | Findings merge separate SKL-44 ceremonies (`6b00505f`, `3864a3b6`), omit SKL-47 pointing outcomes (`a79df3b0`, `59c03f5f`), and count SKL-48 C2 as two accept rounds despite terminal round 4 in `83d20f7a`; rows lack records-posted counts, and SKL-72's four pointing records are omitted from its script record count. |
| AC2: observed/modeled/unavailable figures | Not met | SKL-153 `e10dc49a`, posted before research, contains 20 command launch rows, 805365 tokens and 204 tool calls, contradicting the three-run/no-complete-token limitation. |
| AC3: recommendation contracts | Not met | Named guards exist at the research SHA, but R2/R5/R8 omit explicit tracker-write savings; projected concurrency savings are not measured results. |
| AC4: exhaustive overlap and owners | Not met | R8 omits open SKL-114's effort-schema and story-refinement-consumer overlap; no exhaustive search/classification record is supplied, and R3 uses `related` rather than the specified categories. |
| AC5: full-cycle wall clock | Not met | SKL-167's 28.6-minute Step 1, 42.5-minute first record span and 24.4-minute second span reproduce, but the baseline supplies partial spans, incorrectly groups ceremonies and omits SKL-153's 50m17s measured run. |
| AC6: proposed decision table | Met | Final findings `58c94de5` cover R1-R9 and the preflight rejection, with proposed decisions and rationale in the ranked entries. |
| Deliverable 1: final findings and reproduction | Not met | Supersession, SHA and source byte sizes verify; baseline errors remain, attached `rows.py` is path-bound, and the fetch script labels a workspace-wide comments query as team comments. |
| Deliverable 2: limitations | Not met | Limitations name SKL-44/47/92 but are contradicted by SKL-153's earlier measured usage and SKL-132's already-delivered command-export capability. |
| Deliverable 3: follow-up outlines/amendments | Met | Five proposed Backlog outlines with draft criteria and dependencies plus SKL-60/SKL-21 amendments are present. |
| Deliverable 4: decision table | Met | Same verified table as AC6. |
| DoD1: criteria evidenced or explicitly unmet | Not met | Failed criteria are pre-ticked as met, without their gaps recorded as unmet in the findings. |
| DoD2: findings in Linear | Met | Final findings comment `58c94de5` is stored on SKL-90. |
| DoD3: submitted for owner review | Met | The final findings explicitly submit the proposed decision table; owner response is outside the spike's closure gate. |
| DoD4: next steps and proposed owners | Met | Proposed stories and SKL-60/SKL-21 owners are named; filing approved work waits for owner review. |

The SKL-90 senior engineer owns correcting the existing findings, baseline, metrics provenance, overlap check and explicit write-saving statements before another QA round.
There is no external dependency blocking those research corrections.
Incidental defect: SKL-153's glued nanosecond timestamps are already tracked by SKL-158, not an additional implementation prerequisite for SKL-90.
No implementation PR or deployment forms part of this QA round.
