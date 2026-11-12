# Eval suite run `deepseek-v4-pro-baseline-7a6cb17`

- Graded runs asked for per scenario (N): 3; void runs are retried up to 6 attempts.
- Skill commit (CHECKOUT): `7a6cb17916ef521de301c04af7a795877f353d64`
- Harness commit: `e46615c471d7bdd2c09a8ffeebaa5fdf9540b44f`
- Agent command: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro Follow the instructions in the attached file exactly.`
- n is the graded run count, k the pass count, and the pass rate is k/n.
- Variance is k/n × (1 - k/n), the variance of one run's pass or fail at the observed pass rate.
- A scenario with n = 0 reports its pass rate and variance as `n/a`.
- A scenario graded more than once has one row per grade; a further grade's row is named `<scenario>-<grade>` and counts the same runs.
- Counts and provenance only; each attempt's run record and tool-call record are under the case's `results/`.
- Scenarios short of N graded runs: none.

## qa-unfinished-own-steps (discriminating)

| Scenario | Role | Skill commit | Harness commit | Model | Reasoning effort | n | k | Pass rate k/n | Variance | Voids | Void reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| own-steps | discriminating | 7a6cb17 | e46615c | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| read-back | discriminating | 7a6cb17 | e46615c | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| owner-action | control (regression pin) | 7a6cb17 | e46615c | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| new-round | control (regression pin) | 7a6cb17 | e46615c | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| new-round-read | discriminating (further grade of new-round) | 7a6cb17 | e46615c | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
