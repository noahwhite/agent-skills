# Eval suite run `deepseek-v4-pro-candidate-4f0eb79`

- Graded runs asked for per scenario (N): 3; void runs are retried up to 6 attempts.
- Skill commit (CHECKOUT): `4f0eb796d9390e77a7388aa26ce2ec1e24aa20a2`
- Harness commit: `319c558ae81d39e492bb12b0c6b231dd9852fd73`
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
| own-steps | discriminating | 4f0eb79 | 319c558 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| read-back | discriminating | 4f0eb79 | 319c558 | deepseek/deepseek-v4-pro | default | 3 | 0 | 0/3 = 0.000 | 0.000 | 0 | none |
| owner-action | control (regression pin) | 4f0eb79 | 319c558 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| new-round | control (regression pin) | 4f0eb79 | 319c558 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
| new-round-read | discriminating (further grade of new-round) | 4f0eb79 | 319c558 | deepseek/deepseek-v4-pro | default | 3 | 3 | 3/3 = 1.000 | 0.000 | 0 | none |
