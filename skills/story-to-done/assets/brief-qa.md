# QA brief: {{story}}, round {{round}}

You are the QA agent for the story {{story}}, QA round {{round}}.

path: {{path}}

- Load and follow `qa-verification` for the story, including its evidence and its closing status decision.
- What to hand back: the story's final state, the verdict and evidence for each AC and DoD item, any item left outstanding with its owner, any incidental defect it noted, and each PR it merged with the head SHA its review of record covered.
- Keep working until everything the brief asks for is done, and only stop to ask when you can't go on without the coordinator or before a risky step. The stop this brief already defines still holds: hand back any item left outstanding with its owner.
- Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this brief and the skills it tells you to load define. The pre-PR gate and the review of record that `engineering-workflow` defines, and the evidence PR's review of record that `qa-verification` defines, stay allowed.
- The secrets rule (never write secrets to files or argv).
- Your own subdirectory of the scratch directory is `{{scratch}}/qa-agent-round-{{round}}/`; use it in place of the scratch directory itself, and never touch another role's files.
- Track your work: before starting, write a fine-grained checklist file at the full path `{{scratch}}/qa-agent-round-{{round}}/qa-agent-round-{{round}}-todo.md` (`- [ ]` and `- [x]` items, the current step marked `(in progress)`) and update it at every step.
