# SKL-91 QA evidence

## Round 1, 2026-10-30

SKL-91 is a research spike, and the repository deploys nothing, so there is no environment under test.
The deliverables under test are the SKL-91 findings comment `b4511a52` and decision table comment `93d62be7`.
They were checked against Linear (`linear api`), GitHub (`gh`) and git at the research commit `aca949c7e52be5b4c8d9099cce7c4af1b85d1495`, which was also the `main` head during QA.
The comparison commit is `fb02ce8fd86e666ad98c5c5149098d0fd4ef0da3`.
No fixture was used.
There is no visual surface, so the raw assertions are the evidence; they are attached to SKL-91 as "SKL-91 QA round 1 assertions (2026-10-30)", and the QA comment is `2b5a093c`.

| Item | Verdict | Evidence |
|---|---|---|
| SC1 baseline table | Verified | The cohort query returns the stated 96 comments on 32 issues, and the 15-story cohort and its exclusions match. All 61 comment citations resolve on their stories. Head counts for all 69 linked PRs match GitHub, and every total recomputes. |
| SC2 observed vs unavailable metrics | Verified | Each unavailable metric names its missing source, limit and measuring story. Rerunning the run-metrics search finds only fixture runs. No recommendation claims a token or time saving that was not measured. |
| SC3 recommendation fields | Verified | Recommendations 1 to 7 each state the step, the saving or a measurable hypothesis, the risk, and the evidence. |
| SC4 gates preserved | Verified | No recommendation weakens the review of record, QA independence or the merge guard, and each says how it still binds. The cited story-to-done SKILL.md lines match `aca949c`. |
| SC5 overlap check | Verified | Rerunning the open-story search, plus the four named stories, gives 21 stories, and all 21 are classified with a boundary and an owner. |
| SC6 research questions | Verified | RQ1 to RQ8 are each answered. The RQ6 byte sizes match git at both commits. |
| SC7 decision table | Verified | `93d62be7` gives every recommendation a proposed Go or No-Go and a rationale. |
| Deliverable: final findings comment | Verified | `b4511a52` names `e04f5938` as superseded and gives the queries, the research date and the commit. |
| Deliverable: Limitations | Verified | Findings section 7. |
| Deliverable: ranked recommendations | Verified | Findings section 5 has story outlines, plus amendment text for SKL-150 and SKL-35. |
| Deliverable: decision table | Verified | `93d62be7`. |
| DoD: each SC met with evidence cited | Verified | The SC rows above. |
| DoD: findings documented in Linear | Verified | `b4511a52` and `93d62be7`. |
| DoD: decision table submitted for owner review | Verified | `93d62be7` is posted for owner review. |
| DoD: next steps and owners | Verified | Findings section 8. Under the story's Scope, approved recommendations are filed after owner review, once the spike has closed. |

### Incidental notes

The findings say SKL-21 AC1 specifies a "per-language header", but SKL-21 AC1 says "a generated header".
On agent-skills PRs #86, #88, #101 and #111, one review of record names an earlier head on its first line but carries a later `commit_id`, so the head total is 96 by first-line SHA and 92 by `commit_id`.
