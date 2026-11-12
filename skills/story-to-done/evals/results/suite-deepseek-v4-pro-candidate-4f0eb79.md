# Eval suite run `deepseek-v4-pro-candidate-4f0eb79`

- Graded runs asked for per scenario (N): 3; void runs are retried up to 6 attempts.
- Skill commit (CHECKOUT): `4f0eb796d9390e77a7388aa26ce2ec1e24aa20a2`
- Harness commit: `77620d3eb08a0cde87d7654ea660e5d3c10217cd`
- Agent command: EVAL_AGENT_CMD override
- n is the graded run count, k the pass count, and the pass rate is k/n.
- Variance is k/n × (1 - k/n), the variance of one run's pass or fail at the observed pass rate.
- A scenario with n = 0 reports its pass rate and variance as `n/a`.
- Counts and provenance only; each attempt's run record and tool-call record are under the case's `results/`.

## qa-unfinished-own-steps (discriminating)

| Scenario | Role | Skill commit | Harness commit | Model | Reasoning effort | n | k | Pass rate k/n | Variance | Voids | Void reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| own-steps | discriminating | 4f0eb79 | 77620d3 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| read-back | discriminating | 4f0eb79 | 77620d3 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| owner-action | control (regression pin) | 4f0eb79 | 77620d3 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| new-round | control (regression pin) | 4f0eb79 | 77620d3 | deepseek/deepseek-v4-pro | default | 3 | 2 | 2/3 = 0.667 | 0.222 | 0 | none |
