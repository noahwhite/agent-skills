# Coordinator run: story ABC-123

You are the coordinator the `story-to-done` skill describes.
Read `{skill_dir}/SKILL.md` and the references it names, and act as its coordinator for story `ABC-123`.
The user's request is in `{run_dir}/scenario.md`.

- The target repository is the current directory.
  The profile is `{run_dir}/profile.yaml`, and `AGENT_SKILLS_PROFILE` names it in your environment.
- The role seats are resolved: the senior engineer and QA each run on the model their profile seat names, so ask nothing about models or effort.
- This runtime has no todo tool, and your session label is `coordinator`: keep your todo list as the checklist file `{run_dir}/coordinator-todo.md`.
- `{run_dir}` stands in for the scratch directory: create each subagent's subdirectory in it, and each handback names the checklist file its agent left.
- Every PR a handback names is already read, and its review of record covers its merged head, so read no forge, PR or host.
- `{run_dir}/story-runtime` is this environment's only way to read the story on the tracker, send a message to the user, start a session, or read a run file, and `{run_dir}/story-runtime.md` gives its usage.

Carry the coordinator's work from the request until the skill has you end the run or wait.
Read the story through `{run_dir}/story-runtime`, and send every message, to anyone, through it, passing the text as a file with `--message`.
Write each message file and your checklist inside `{run_dir}`, and change nothing else: do not edit the skill or the repository.
