# Coordinator todo - story-to-done ABC-123

engineer-model: example-engineer-model
engineer-effort: high
qa-model: example-qa-model
qa-effort: high
metrics: off
qa-round-cap: 3
path: spike

- [x] Read the story and its state, labels (step 1)
- [x] Select the path via select-path.py (step 1)
- [x] Create `<scratch>{path}` subdirectory and write the step 2 brief
- [x] Spawn the senior engineer (step 2)
- [x] Check the senior engineer's checklist until it hands back
- [x] Read back the senior engineer's checklist at handback (resume count 0)
- [x] Read back the story state and confirm deployment review
- [x] Create `<scratch>{path}` and write the step 3 brief
- [x] Spawn QA agent round 1 (step 3)
- [ ] Check the QA agent's checklist until it hands back (in progress - waiting on QA handback)
- [ ] Read back the QA round 1 checklist at handback
- [ ] Read back the story state after QA round 1
- [ ] Act on the QA outcome (step 4)
- [ ] Close out and report (step 5)
