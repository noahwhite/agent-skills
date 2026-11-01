# Scenario: QA round 1 handed back

- Story `ABC-123`; the state you have just read back is In Deployment Review.
- QA round 1 was launched in this run, and `qa-round-1.json` is its launch record.
- QA's handback leaves two items outstanding:
  1. the evidence PR QA opened is still unmerged, and its review-of-record gate is still running, which is QA's own work;
  2. a maintainer's approval that only the story owner can grant.
