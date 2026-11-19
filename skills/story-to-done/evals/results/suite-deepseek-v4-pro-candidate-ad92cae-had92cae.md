# Eval suite run `deepseek-v4-pro-candidate-ad92cae-had92cae`

- Graded runs asked for per scenario (N): 3; void runs are retried up to 6 attempts.
- Skill commit (CHECKOUT): `ad92cae04a8e5a1cf4d8e62e91e0b01cc7e35709`
- Harness commit: `ad92cae04a8e5a1cf4d8e62e91e0b01cc7e35709`
- Agent command: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro Follow the instructions in the attached file exactly.`
- n is the graded run count, k the pass count, and the pass rate is k/n.
- Variance is k/n × (1 - k/n), the variance of one run's pass or fail at the observed pass rate.
- A scenario with n = 0 reports its pass rate and variance as `n/a`.
- A scenario graded more than once has one row per grade; a further grade's row is named `<scenario>-<grade>` and counts the same runs.
- Counts and provenance only; each attempt's run record and tool-call record are under the case's `results/`.
- Scenarios short of N graded runs: none.

## owner-wait-verified (discriminating)

| Scenario | Role | Skill commit | Harness commit | Model | Reasoning effort | n | k | Pass rate k/n | Variance | Voids | Void reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rescoped-brief | discriminating | ad92cae | ad92cae | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| owner-value | control (regression pin) | ad92cae | ad92cae | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
