# story-to-done coordinator - ABC-123

- engineer-model: example-engineer-model
- engineer-effort: high
- qa-model: example-qa-model
- qa-effort: high
- metrics: off
- qa-round-cap: 3
- path: deployed

## Reference reads

- [x] Read references/profile.md (find profile and overlay)
- [x] Read references/runtimes.md (map runtime)
- [x] Read references/todo-tracking.md (expand list)
- [x] Read references/linear.md (steps 1, 4, 5)
- [x] Read references/code-review.md (steps 2, 3)
- [x] Read references/secrets.md (every brief)
- [x] Read references/interim-handbacks.md

## Step 1 - read the story and pick the starting point

- [x] Read the story state (story-runtime tracker-read) - Ready To Work
- [x] Run select-path.py to select the path - deployed
- [x] Select starting point (step 2 vs step 3) - step 2

## Step 2 - senior engineer implements to deployment review

- [x] Create <scratch>{path} subdirectory
- [x] Spawn the senior engineer (engineer-launch)
- [x] Read the engineer's checklist and handback
- [x] Read back the story state (confirm in deployment review) - In Deployment Review

## Step 3 - QA agent verifies

- [x] Create <scratch>{path} subdirectory
- [x] Spawn QA agent round 1 (qa-launch) - session started, has not handed back
- [ ] Read QA round 1 checklist and handback - not done: the runtime cannot resume the QA session, so the run ends with QA started
- [ ] Read back the story state - not done: QA never hands back in this runtime

## Step 4 - act on the QA outcome

- [ ] Classify the outcome - not reached (no QA handback)
- [ ] Hand back failed items to the senior engineer - not reached
- [ ] Re-run QA - not reached

## Step 5 - close out

- [ ] Read the story back and confirm Done - not reached (story is In Deployment Review, QA never handed back)
- [ ] Finish the todo list and report
