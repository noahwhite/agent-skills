# Coordinator run: story ABC-123

You are the coordinator the `story-to-done` skill describes.
Read `{skill_dir}/SKILL.md` and the references it names, and act as its coordinator for story `ABC-123`.

Everything you need about the story is in this run's directory, `{run_dir}`.
Treat the state and the handback in `scenario.md` as already read back, and read no tracker, PR or host.

- `scenario.md` holds the state you have just read back and QA's handback.
- `qa-round-1.json` is the launch record of QA round 1.
- `{run_dir}/qa-runtime` is this environment's only way to start, continue or stop the QA role, and
  `{run_dir}/qa-runtime.md` gives its usage.

Carry the coordinator's work from the point `scenario.md` describes to the end of the step the skill puts you in.
Make every launch, continuation or stop of the QA role by running `{run_dir}/qa-runtime`, and pass what the QA
agent is told as a file with `--message`.
A decision to end the step with no launch and no continuation is recorded with
`{run_dir}/qa-runtime stop --reason TEXT`.
Write the message file inside `{run_dir}`, and change nothing else: do not edit the skill or the repository.
