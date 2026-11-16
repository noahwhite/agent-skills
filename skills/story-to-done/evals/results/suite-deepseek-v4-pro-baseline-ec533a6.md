# Eval suite run `deepseek-v4-pro-baseline-ec533a6`

- Graded runs asked for per scenario (N): 3; void runs are retried up to 6 attempts.
- Skill commit (CHECKOUT): `ec533a60237fe34a39468b564d8e093f37673354`
- Harness commit: `2271eb9d230eb0cc2d61fbdce44bde959c3c12f6`
- Agent command: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro Follow the instructions in the attached file exactly.`
- n is the graded run count, k the pass count, and the pass rate is k/n.
- Variance is k/n × (1 - k/n), the variance of one run's pass or fail at the observed pass rate.
- A scenario with n = 0 reports its pass rate and variance as `n/a`.
- A scenario graded more than once has one row per grade; a further grade's row is named `<scenario>-<grade>` and counts the same runs.
- Counts and provenance only; each attempt's run record and tool-call record are under the case's `results/`.
- Scenarios short of N graded runs: none.

## spike-no-deployment (discriminating)

| Scenario | Role | Skill commit | Harness commit | Model | Reasoning effort | n | k | Pass rate k/n | Variance | Voids | Void reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| spike | discriminating | ec533a6 | 2271eb9 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| no-deployment | discriminating | ec533a6 | 2271eb9 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| deployed | control (regression pin) | ec533a6 | 2271eb9 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| deployed-path | discriminating (further grade of deployed) | ec533a6 | 2271eb9 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| conflict | discriminating | ec533a6 | 2271eb9 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 3 | attempt 1: run.sh exited 2: void; attempt 2: run.sh exited 2: void; attempt 5: run.sh exited 2: void |
| direct-entry | discriminating | ec533a6 | 2271eb9 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
