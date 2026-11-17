# SKL-334 QA evidence

## QA round 1

Date: 2026-11-17 UTC, independent QA round 1.
Path: `spike`, selected by `select-path.py` with the label `Spike` and the recorded `path: spike` line, so no environment or build SHA applies.
Target: the deliverables the handoff note links, the "SKL-334 gap table" comment on SKL-334 (SKL-334, comment `e567e01c`) and the "Go/No-Go" section inside it.
Neither deliverable is a tracked file, so neither has a commit.
The gap table reviews agent-skills at `ee17dfb64b44a59f4a5886177e3354ff5817e85c`, which `git merge-base --is-ancestor` confirmed on `origin/main`.
Fixtures: none; QA made no model call and changed no repository setting.
The raw output is attached to SKL-334 as "SKL-334 QA round 1 assertions"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| SC1: source record and the article section of every practice | Verified | An independent fetch of the article gave the same title, author and publication date. Every row's section is in the source record's section list and matches the article heading of that recommendation. |
| SC2: practices listed once with stable IDs, team examples apart, merged repeats noted | Verified | 21 rows, P1 to P21 in order. "Merged repeats" and "Team examples in the article" are present, and every fetched recommendation maps to one practice or a listed team example. |
| SC3: every practice rated at one revision with one evidence pointer, intent or observed | Verified | All 21 ratings use the allowed scale and no pointer or intent-or-observed cell is empty. All 27 pointed files, with each named section, step or function, exist at `ee17dfb`. The one not applicable rating (P8) names the repository property, reproduced through the ruleset and file reads; there is no unknown rating. |
| SC4: every behavioural finding names one artifact and the one command or record behind it | Verified | QA re-ran the named commands of E1 (2977 tests collected), E2 to E9 and E11 to E13 and read the E10 record; every output matches the comment. |
| SC5: one proposed change with a primary target per partly or not met practice | Verified | 17 practices are partly or not met, and each row has a change and a target from tests, skills, CI or review process. |
| SC6: research questions 1 to 6 answered | Verified | All six are answered with practice IDs and file or workflow evidence; QA re-checked the cited QA round cap, two-lens round cap, vendoring check and eval case status. |
| Deliverable: one "SKL-334 gap table" comment with no attachment | Verified | Exactly one comment carries the heading, it holds no upload, and its table has the eight specified columns, the source record, the revision, the answers and the unknown items. |
| Deliverable: Go/No-Go in the same comment | Verified | Go, with the rule stated and met; the 11 proposed stories each have a title, boundary and practice IDs, cover all 17 gap practices, and are proposed for SKL with the reason none is for OFF. |
| DoD: every success criterion marked pass or fail | Verified | All six are marked pass. |
| DoD: findings in the single findings comment | Verified | The other comments that mention the gap table are the handoff note and the refinement record. |
| DoD: Go/No-Go recorded with the rule applied | Verified | The "Rule applied" line states the Go rule. |
| DoD: next steps defined | Verified | The 11 proposed stories, with filing as the owner's next step. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
