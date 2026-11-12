# D2

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->

A block rate is a joint measurement: the proposer has to produce the illegal operation before the guard can refuse it. On the schema and feasibility classes the stronger arms decline to act instead, returning an empty operation list, which is correct handling and leaves the guard nothing to block. Reading a falling V1 or V2 block rate as falling guard recall would be wrong, and this table is what prevents that reading: the last column, block plus decline, is what the pair actually achieves.

| arm | class | think | items | blocked by the guard | declined (empty proposal) | refused by the model | applied with operations | blocked, declined or refused |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | V1 | - | 480 | 66.7% | 8.5% | 0.0% | 24.8% | 75.2% |
| qwen3-14b | V2 | - | 600 | 65.3% | 4.7% | 0.0% | 30.0% | 70.0% |
| qwen3.6-27b-fp8 | V1 | - | 480 | 69.4% | 18.5% | 0.0% | 12.1% | 87.9% |
| qwen3.6-27b-fp8 | V2 | - | 600 | 62.2% | 17.2% | 0.0% | 20.7% | 79.3% |
| glm-4-9b | V1 | - | 160 | 71.2% | 1.9% | 0.0% | 26.9% | 73.1% |
| glm-4-9b | V2 | - | 200 | 76.5% | 0.5% | 0.0% | 23.0% | 77.0% |
| openai | V1 | - | 320 | 71.9% | 1.6% | 0.0% | 26.6% | 73.4% |
| openai | V2 | - | 400 | 64.5% | 7.5% | 0.0% | 28.0% | 72.0% |
| deepseek | V1 | non_think | 320 | 74.4% | 25.6% | 0.0% | 0.0% | 100.0% |
| deepseek | V1 | think_high | 320 | 77.8% | 22.2% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | non_think | 400 | 62.0% | 38.0% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | think_high | 400 | 66.2% | 33.8% | 0.0% | 0.0% | 100.0% |
| sonnet | V1 | disabled | 320 | 56.2% | 29.7% | 0.0% | 14.1% | 85.9% |
| sonnet | V2 | disabled | 400 | 41.2% | 30.2% | 0.0% | 28.5% | 71.5% |
| opus | V1 | default | 320 | 23.4% | 70.9% | 0.0% | 5.6% | 94.4% |
| opus | V1 | disabled | 320 | 45.0% | 44.7% | 0.0% | 10.3% | 89.7% |
| opus | V2 | default | 400 | 8.2% | 49.2% | 0.0% | 42.5% | 57.5% |
| opus | V2 | disabled | 400 | 23.0% | 39.0% | 0.0% | 38.0% | 62.0% |
| sol | V1 | none | 160 | 31.2% | 53.1% | 0.0% | 15.6% | 84.4% |
| sol | V2 | none | 200 | 26.0% | 39.5% | 0.0% | 34.5% | 65.5% |

