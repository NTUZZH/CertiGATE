# D2

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: primary -->

A block rate is a joint measurement: the proposer has to produce the illegal operation before the guard can refuse it. On the schema and feasibility classes the stronger arms decline to act instead, returning an empty operation list, which is correct handling and leaves the guard nothing to block. Reading a falling V1 or V2 block rate as falling guard recall would be wrong, and this table is what prevents that reading: the last column, block plus decline, is what the pair actually achieves.

| arm | class | think | items | blocked by the guard | declined (empty proposal) | refused by the model | applied with operations | blocked, declined or refused |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | V1 | - | 24 | 62.5% | 12.5% | 0.0% | 25.0% | 75.0% |
| qwen3-14b | V2 | - | 21 | 71.4% | 0.0% | 0.0% | 28.6% | 71.4% |
| qwen3.6-27b-fp8 | V1 | - | 24 | 62.5% | 25.0% | 0.0% | 12.5% | 87.5% |
| qwen3.6-27b-fp8 | V2 | - | 21 | 57.1% | 14.3% | 0.0% | 28.6% | 71.4% |
| glm-4-9b | V1 | - | 8 | 50.0% | 12.5% | 0.0% | 37.5% | 62.5% |
| glm-4-9b | V2 | - | 7 | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| openai | V1 | - | 16 | 62.5% | 0.0% | 0.0% | 37.5% | 62.5% |
| openai | V2 | - | 14 | 71.4% | 0.0% | 0.0% | 28.6% | 71.4% |
| deepseek | V1 | non_think | 16 | 75.0% | 25.0% | 0.0% | 0.0% | 100.0% |
| deepseek | V1 | think_high | 16 | 75.0% | 25.0% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | non_think | 14 | 78.6% | 21.4% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | think_high | 14 | 57.1% | 42.9% | 0.0% | 0.0% | 100.0% |
| sonnet | V1 | disabled | 16 | 56.2% | 18.8% | 0.0% | 25.0% | 75.0% |
| sonnet | V2 | disabled | 14 | 28.6% | 42.9% | 0.0% | 28.6% | 71.4% |
| opus | V1 | default | 16 | 25.0% | 62.5% | 0.0% | 12.5% | 87.5% |
| opus | V1 | disabled | 16 | 50.0% | 37.5% | 0.0% | 12.5% | 87.5% |
| opus | V2 | default | 14 | 14.3% | 50.0% | 0.0% | 35.7% | 64.3% |
| opus | V2 | disabled | 14 | 28.6% | 42.9% | 0.0% | 28.6% | 71.4% |
| sol | V1 | none | 8 | 50.0% | 37.5% | 0.0% | 12.5% | 87.5% |
| sol | V2 | none | 7 | 0.0% | 57.1% | 0.0% | 42.9% | 57.1% |

