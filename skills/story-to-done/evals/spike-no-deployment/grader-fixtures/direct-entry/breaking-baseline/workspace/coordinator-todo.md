# story-to-done coordinator checklist - ABC-123

engineer-model: example-engineer-model
engineer-effort: high
qa-model: example-qa-model
qa-effort: high
metrics: off
qa-round-cap: 3

## Step 0 - bootstrap

- [x] Create this todo list
- [x] Read the references the skill names
- [x] Read the profile and resolve the seats

## Step 1 - read the story and pick the starting point

- [x] Read the story state via story-runtime tracker-read
- [x] Pick the starting point: state is In Deployment Review, so route to step 3 (QA); skip the senior engineer because implementation already reached deployment review

## Step 2 - senior engineer implements to deployment review

- [x] Skipped: story is already in In Deployment Review, so no step 2

## Step 3 - QA agent verifies the deployed story

- [x] Create the qa-agent-round-1 subdirectory
- [x] Write the QA round 1 brief
- [x] Launch the QA agent (qa-launch, label qa-agent-round-1)
- [ ] Read back the QA agent's checklist and final state at handback (waiting: the QA session has not handed back; this runtime starts sessions and cannot resume one)

## Step 4 - act on the QA outcome

- [ ] Waiting on the QA handback, which this runtime never delivers

## Step 5 - close out

- [ ] Waiting on the QA handback
