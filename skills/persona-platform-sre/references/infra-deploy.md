<!-- GENERATED from shared/infra-deploy.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->

# Infrastructure, CI/CD, and deploy discipline

Read this before IaC work, dispatching workflows, deploying, or changing hosts.
Environments come from `profile.environments`; the consumer overlay supplies the project's stacks, workflows, hosts, and runbooks (see `references/profile.md`).

## Plan before apply

- Run a plan for every IaC change and read it before any apply: every replace, destroy, and changed attribute must be expected.
  A plan that replaces something you did not intend to touch stops the change.
- ⛔ Never auto-apply to an environment marked `profile.environments[].production` outside the approved promotion and its gate.
  When a production apply or cutover is the clear next step of an approved promotion, call it out explicitly before doing it.
- Some attributes force replacement (for example a server's user data), so an innocent-looking template change can rebuild a machine.
  Look for forced replacements in the plan.
- ⛔ Destroy a stack before deleting its definition; deleting the file first orphans both the cloud resource and its state.
  Sequence: destroy, confirm it is gone at the provider, then delete and commit.
  If the file is already gone, restore it, destroy, and delete again.
- Empty storage buckets before destroying them when the provider has no force-destroy; otherwise the destroy fails or retries forever.
- If the repo scaffolds stacks from templates, change the template and the matching live stack together; a stale template scaffolds broken stacks.
- Every new IaC module ships its provider version constraints and its unit tests in the same PR, never in a follow-up.

## Verify running state from the primary source

- ⛔ Never infer running infrastructure from IaC alone: IaC presence is not "running", and IaC absence is not "not running".
  Cross-check what is declared against what the provider, the orchestrator, or live telemetry reports.
- Read what is declared for an environment from the branch that deploys it (`profile.environments[].branch`, with `git show origin/<branch>:<path>`), never from a feature branch that may legitimately lack it.
- ⛔ Before writing an alert rule, an acceptance criterion, or a feasibility claim on a metric, confirm the metric exists and is flowing, and that the comparison is buildable from real series.
  Never assume a metric from its name.

## Dispatch and wait

- Deploy to each environment in `profile.environments` as its `profile.environments[].deploy` says, in promotion order, and confirm with its `profile.environments[].verify`.
  A dispatched run is not a deploy until it has concluded successfully and the verify step shows the expected build.
- After dispatching, find the run it created, wait for it to conclude, and read its logs on failure; never report a dispatch as done.
- Deploys to an environment with `profile.environments[].preauthorized` set to true are part of the work; every other environment needs an explicit go from the user.
  Either way, check the workflow, environment, inputs, and data guards before dispatching.
- ⛔ Never dispatch provisioning or deploy steps that the user runs through their own tooling unless asked; it bypasses the validation they may be testing.
  Check what has already run (`gh run list`, or ask) before triggering the next step.
- A CI watch pinned to one SHA misses a PR going behind its base and the new head an update creates; watch the PR (`references/code-review.md`, Watching the PR).
- Open a retrigger or drift-fix PR in the repo where the drift occurred, against that repo's integration branch.

## Host operations

- Rebuild hosts only through the project's one sanctioned rebuild path (the consumer overlay names it); other deploy paths may skip the steps that make a rebuilt host rejoin safely.
- Before rebuilding a host that carries live workloads, put up maintenance for every affected workload; take it down only after verification.
- Verify that the origin serves stably, several times, before declaring a workload up; "container healthy" is not enough, since an app can still be booting behind it.

## Container gotchas

- Busybox `sh` (Alpine) does not accept `set -o pipefail`; use `set -eu` with `#!/usr/bin/env sh` there, and keep `set -euo pipefail` for bash.
- When adding `entrypoint:` to a Compose service, also set `command:` to the image's original CMD; Compose clears CMD on an entrypoint override, and the container then exits 0 silently.
  Read the original with `docker inspect <image> --format '{{.Config.Cmd}} {{.Config.Entrypoint}}'`.
