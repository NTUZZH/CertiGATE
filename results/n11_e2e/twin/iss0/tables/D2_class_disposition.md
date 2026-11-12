# D2

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

A block rate is a joint measurement: the proposer has to produce the illegal operation before the guard can refuse it. On the schema and feasibility classes the stronger arms decline to act instead, returning an empty operation list, which is correct handling and leaves the guard nothing to block. Reading a falling V1 or V2 block rate as falling guard recall would be wrong, and this table is what prevents that reading: the last column, block plus decline, is what the pair actually achieves.

| arm | class | think | items | blocked by the guard | declined (empty proposal) | refused by the model | applied with operations | blocked, declined or refused |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | V1 | - | 480 | 66.7% | 8.5% | 0.0% | 24.8% | 75.2% |
| qwen3-14b | V2 | - | 555 | 63.1% | 4.5% | 0.0% | 32.4% | 67.6% |
| qwen3.6-27b-fp8 | V1 | - | 480 | 69.4% | 18.5% | 0.0% | 12.1% | 87.9% |
| qwen3.6-27b-fp8 | V2 | - | 555 | 64.9% | 14.8% | 0.0% | 20.4% | 79.6% |
| glm-4-9b | V1 | - | 160 | 71.2% | 1.9% | 0.0% | 26.9% | 73.1% |
| glm-4-9b | V2 | - | 185 | 74.6% | 0.5% | 0.0% | 24.9% | 75.1% |
| openai | V1 | - | 320 | 71.9% | 1.6% | 0.0% | 26.6% | 73.4% |
| openai | V2 | - | 370 | 63.0% | 6.8% | 0.0% | 30.3% | 69.7% |
| deepseek | V1 | non_think | 320 | 74.4% | 25.6% | 0.0% | 0.0% | 100.0% |
| deepseek | V1 | think_high | 320 | 77.8% | 22.2% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | non_think | 370 | 67.0% | 33.0% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | think_high | 370 | 70.0% | 30.0% | 0.0% | 0.0% | 100.0% |
| sonnet | V1 | disabled | 320 | 56.2% | 29.7% | 0.0% | 14.1% | 85.9% |
| sonnet | V2 | disabled | 370 | 44.6% | 25.9% | 0.0% | 29.5% | 70.5% |
| opus | V1 | default | 320 | 23.4% | 70.9% | 0.0% | 5.6% | 94.4% |
| opus | V1 | disabled | 320 | 45.0% | 44.7% | 0.0% | 10.3% | 89.7% |
| opus | V2 | default | 370 | 8.9% | 45.1% | 0.0% | 45.9% | 54.1% |
| opus | V2 | disabled | 370 | 24.9% | 34.1% | 0.0% | 41.1% | 58.9% |
| sol | V1 | none | 160 | 31.2% | 53.1% | 0.0% | 15.6% | 84.4% |
| sol | V2 | none | 185 | 28.1% | 34.6% | 0.0% | 37.3% | 62.7% |

