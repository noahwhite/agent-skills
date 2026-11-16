# story-to-done coordinator checklist: ABC-123

engineer-model: example-engineer-model
engineer-effort: high
qa-model: example-qa-model
qa-effort: high
metrics: off
qa-round-cap: 3
path: no-deployment

## Steps

- [x] Read the story and its state from the tracker (story-runtime tracker-read): In Deployment Review
- [x] Select the run's path with select-path.py: no-deployment
- [x] Pick the starting point from the story state: In Deployment Review -> step 3 (QA)
- [x] Skip the senior engineer (implementation already reached deployment review)
- [x] QA round 1: spawn the QA agent (label qa-agent-round-1, no-deployment brief, target commit 4e1c2a9b7d3f5e6a8c0b1d2e3f4a5b6c7d8e9f01 on main)
- [ ] Read back the QA agent's checklist and final state at handback (waiting for the QA session to hand back)
- [ ] Act on the QA outcome (Done / In Progress / In Deployment Review)
- [ ] Close out: confirm Done and report
