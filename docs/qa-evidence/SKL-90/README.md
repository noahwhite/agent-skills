# SKL-90 QA round 1

- Date: 2026-10-31 UTC.
- Story: SKL-90 in the project tracker.
- Environment: Linear tracker deliverables and read-only repository source, not a deployed service.
- Build SHA: not applicable; research source SHA `f7453b3b22feec7e3d1f5928790e9bb23f9f6baf`.
- Fixtures: QA independently captured 167 SKL issues and 792 team-filtered comments before posting its own findings, and separately inspected the two research scripts attached to the story.
- Surface: CLI/API assertions and source records; no visual UI or screenshot applies.
- Outcome: not met; reopen the existing spike to In Progress for correction.
- QA evidence comment `f906f047` on SKL-90 includes the source references and ownership; use `linear issue comment list SKL-90` to retrieve it.
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

## QA round 2 - 2026-10-31 UTC

This section preserves round 1 above and records verification of findings revision 3, comment `0eb9afe4`.
The environment is the Linear tracker and read-only repository source, with research SHA `f7453b3b22feec7e3d1f5928790e9bb23f9f6baf`; there is no application build, deployment, visual surface or screenshot.
Fixtures are an independent fully paginated capture of 167 SKL issues and 797 team-filtered comments, the corrected attached analysis scripts, and freshly fetched source at the research SHA.
The comment count is snapshot-specific and grows when evidence is posted.
The attached script reproduces 65 ceremonies, 54 stories, 254 record comments, 78 accept rounds, 65 pointing rounds, 64 re-votes, 5 voids and 1372 modeled launches, but its round judgments are hard-coded and arithmetic reproduction does not validate their truth.
QA checked those judgments against source records, all 26 cited guard names and all eight source byte sizes.
The outcome is not met; the existing spike must return to In Progress, not Blocked.

The round 2 evidence comment `089106b4` on SKL-90 links the tracker attachment titled "SKL-90 QA round 2 assertions and source records": 30 assertions, 27 passed and 3 failed.
Retrieve the comment with `linear issue comment list SKL-90`.
The attachment is the raw evidence behind every row below.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: complete baseline | Not met | SKL-16 `9ef600ea` records actual rounds 1-4, while revision 3 and its script count 5 pointing rounds and 5 re-votes; five was the permitted cap, not the rounds run. |
| AC2: number classes | Met | Labels separate observed, modeled, measured and unavailable quantities; SKL-153 `e10dc49a` independently sums to 20 launch rows, 1855.9 seconds, 805365 tokens and 204 tool calls. |
| AC3: recommendation contracts | Met | R1-R10 state their steps, launch and write savings, risks, guards and evidence; all 26 named tests exist at the research SHA. |
| AC4: exhaustive overlaps | Met | Independent scan reproduces 50 title/description matches and 16 open matches; excluding SKL-90 itself, all 15 other open matches and named issues are classified and owned, including SKL-114. |
| AC5: full-cycle timing | Not met | The 67% attribution belongs to SKL-167 C1 (28.56/42.48 minutes), not its C2 no-consensus cycle; C2 is 11.18/24.40 minutes (46%) through Step 1 or 14.12/24.40 (58%) through its first accept result. |
| AC6: proposed decisions | Met | R1-R10 and the rejected concurrent-preflight option have proposed decisions, risks and rationales for owner review. |
| Deliverable 1: final reproducible findings | Not met | Supersession, queries, date, SHA and byte sizes verify, but source-false rounds and phase attribution remain. |
| Deliverable 2: limitations | Met | Findings identify 61 unmeasured ceremonies, partial usage, complete command-seat usage and proposed S6/R10 as measurement owner. |
| Deliverable 3: follow-up outlines | Not met | S1-S6 declare blockers and 3-5 draft ACs each, but S3-S6 jump directly from their titles to ACs without the required one-paragraph summaries. |
| Deliverable 4: decision table | Met | Same verified proposed table as AC6. |
| DoD1: criteria evidenced or explicitly unmet | Not met | The findings criteria-status table incorrectly claims AC1 and AC5 met. |
| DoD2: findings in Linear | Met | Findings revision 3 is posted on SKL-90. |
| DoD3: owner-review submission | Met | The decision table explicitly awaits owner review; owner approval is not a spike closure gate. |
| DoD4: next steps and owners | Met | Existing owners and proposed S1-S6 are named; approved recommendations are filed only after owner review. |

The timing assertions use source comments `8fd5ba23`, `22d83f40`, `92750d81`, `ebf177bb`, `fb92fcd8`, `b9584831` and `f03f2149`, whose full IDs, bodies and timestamps are in the tracker attachment.
These are observed tracker intervals, not measured launch durations.
The SKL-90 senior engineer owns correcting the actual-round count and affected totals, assigning the timing percentage to the right invocation, supplying S3-S6 summaries, and updating the findings criteria-status table before re-verification.
No external blocking story is recorded; related SKL-91 is Done.
Incidental non-blocking defects: SKL-158 already owns malformed nanosecond timestamps, and the blanket claim that spans understate measured cycles needs its labelled SKL-130 exception because that metric covers only resumed invocation 2.
This evidence change implements no recommendation and deploys nothing.

## QA round 3 - 2026-10-31 UTC

This section preserves both earlier rounds and verifies findings revision 4, comment `6f64a66c-cde7-4f2f-bc69-99132649bd5b` on SKL-90.
The environment is Linear tracker deliverables and read-only source at research SHA `f7453b3b22feec7e3d1f5928790e9bb23f9f6baf`; no deployed build, UI fixture, screenshot or hosted page applies.
Fixtures are an independent fully paginated CLI capture of 167 SKL issues and 802 team-filtered comments, the attached revision-4 baseline script, and freshly fetched repository source.
The comment count is snapshot-specific.
QA reproduced all 65 published ceremony rows across the independently identified 54-story population, checked their evidence IDs against the source issues, and inspected the round-2 correction sources.
The baseline reproduces 254 record comments, 78 accept rounds, 64 pointing rounds, 63 re-votes, 5 voids and 1,363 modeled launches.
Arithmetic reproduction alone does not establish the script's hard-coded round judgments; the corrected SKL-16 source explicitly records rounds 1-4 under a five-round cap.
The outcome is met for all six acceptance criteria, four deliverables and four DoD items; closure additionally requires this evidence change to merge.

The QA evidence comment `b7c67227` on SKL-90 links the tracker attachment titled "SKL-90 QA round 3 assertions and source records".
Retrieve it with `linear issue comment list SKL-90`.
The attachment contains 25 passing structured assertions, reproduced baseline rows, authoritative source excerpts with full IDs and timestamps, and the final findings text.
It is the raw evidence behind every row below.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: complete baseline | Met | Independent population is 54 stories; all 65 ceremony rows and their totals reproduce; SKL-16 `9ef600ea` now contributes four actual pointing rounds and re-votes rather than the five-round cap. |
| AC2: number classes | Met | Observed, modeled, measured and unavailable figures are labelled; SKL-153 `e10dc49a` independently sums to 20 rows, 1,855.9 seconds, 805,365 tokens and 204 tool calls; unmeasured savings are explicit. |
| AC3: recommendation contracts | Met | R1-R10 state steps, launch/write effects, risks, guard tests and evidence; all 26 named tests exist at the research SHA. |
| AC4: exhaustive overlap | Met | Independent search reproduces 50 matches and 16 open matches; all 15 other open issues plus named issues are classified and owned, including SKL-114. |
| AC5: full-cycle timing | Met | SKL-167 source timestamps give C1 Step 1 28.56/42.48 minutes (67%); C2 gives 11.18/24.40 (46%), or 14.12/24.40 (58%) through first accept result; revision 4 attributes them correctly as tracker intervals, supplies four measured cycles and phase limits, and names S6/R10 for residual measurement. |
| AC6: proposed decisions | Met | R1-R10 and the rejected concurrent-preflight option carry proposed decisions with rationale for owner review. |
| Deliverable 1: reproducible findings | Met | Final supersession, research date and SHA, queries, counting rules, corrected baseline and all eight source byte sizes verify. |
| Deliverable 2: limitations | Met | Complete command-seat usage, partial earlier runs and 61 ceremonies without metrics are distinguished; S6/R10 owns future measurement. |
| Deliverable 3: follow-up outlines | Met | S1-S6 each contain a one-paragraph summary, 3-5 draft ACs and dependency declarations; SKL-60 and SKL-21 amendments are specified. |
| Deliverable 4: decision table | Met | Same verified table as AC6. |
| DoD1: criteria evidenced | Met | Criteria-status table cites corrected evidence for all six ACs and four deliverables. |
| DoD2: findings in Linear | Met | Revision 4 is stored on SKL-90. |
| DoD3: owner-review submission | Met | The proposed decision table is explicitly for owner review; an owner response is not this spike's closure gate. |
| DoD4: next steps and owners | Met | S1-S6 and existing owners are explicit; approved recommendations are filed after owner review. |

The three round-2 gaps are corrected: actual-round count, SKL-167 cycle attribution and S3-S6 summaries.
The earlier blanket span-understates-cycle claim now explicitly exempts SKL-130's resumed invocation.
No research correction or external blocker remains; related SKL-91 is Done.
Incidental non-blocking defect: malformed nanosecond timestamps are already owned by SKL-158 and disclosed in the findings.
This round changes only QA evidence, not implementation or deployment.
