# Coordinator todo - story-to-done ABC-123

engineer-model: example-engineer-model
engineer-effort: high
qa-model: example-qa-model
qa-effort: high
metrics: off
qa-round-cap: 3
path: unresolved

## Bootstrap (from SKILL.md only)

- [x] Read references/profile.md (find profile and overlay)
- [x] Read references/runtimes.md (map runtime)
- [x] Read references/todo-tracking.md (step 0)
- [x] Read references/linear.md (steps 1, 4, 5)
- [x] Read references/code-review.md (steps 2, 3)
- [x] Read references/secrets.md (every brief)
- [x] Read references/interim-handbacks.md (steps 2, 3)

## Step 1: read the story and pick the path

- [x] Read the story state (tracker-read): Ready To Work, labels User Story
- [x] Run select-path.py -> ask: spike-title-without-label
- [x] Ask the user to choose spike / no-deployment / deployed
- [ ] Wait for the user's path answer; spawn no role until answered

## Later steps (blocked on the path answer)

- [ ] Step 2: senior engineer implement to deployment review
- [ ] Step 3: QA agent verify deployed story
- [ ] Step 4: act on QA outcome
- [ ] Step 5: close out
