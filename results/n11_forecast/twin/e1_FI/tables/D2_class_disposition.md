# D2

<!-- N11 Stage 3 forecast twin (l1-n11-forecast-1) -->
<!-- reading FI -->

A block rate is a joint measurement: the proposer has to produce the illegal operation before the guard can refuse it. On the schema and feasibility classes the stronger arms decline to act instead, returning an empty operation list, which is correct handling and leaves the guard nothing to block. Reading a falling V1 or V2 block rate as falling guard recall would be wrong, and this table is what prevents that reading: the last column, block plus decline, is what the pair actually achieves.

| arm | class | think | items | blocked by the guard | declined (empty proposal) | refused by the model | applied with operations | blocked, declined or refused |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | V1 | - | 480 | 67.3% | 8.5% | 0.0% | 24.2% | 75.8% |
| qwen3-14b | V2 | - | 555 | 67.4% | 5.0% | 0.0% | 27.6% | 72.4% |
| qwen3.6-27b-fp8 | V1 | - | 480 | 69.4% | 18.5% | 0.0% | 12.1% | 87.9% |
| qwen3.6-27b-fp8 | V2 | - | 555 | 64.3% | 15.3% | 0.0% | 20.4% | 79.6% |
| glm-4-9b | V1 | - | 160 | 71.9% | 1.9% | 0.0% | 26.2% | 73.8% |
| glm-4-9b | V2 | - | 185 | 75.1% | 0.5% | 0.0% | 24.3% | 75.7% |
| openai | V1 | - | 320 | 71.9% | 1.6% | 0.0% | 26.6% | 73.4% |
| openai | V2 | - | 370 | 62.7% | 7.0% | 0.0% | 30.3% | 69.7% |
| deepseek | V1 | non_think | 320 | 74.4% | 25.6% | 0.0% | 0.0% | 100.0% |
| deepseek | V1 | think_high | 320 | 77.8% | 22.2% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | non_think | 370 | 66.5% | 33.5% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | think_high | 370 | 69.5% | 30.5% | 0.0% | 0.0% | 100.0% |
| sonnet | V1 | disabled | 320 | 56.2% | 29.7% | 0.0% | 14.1% | 85.9% |
| sonnet | V2 | disabled | 370 | 44.1% | 26.5% | 0.0% | 29.5% | 70.5% |
| opus | V1 | default | 320 | 23.4% | 70.9% | 0.0% | 5.6% | 94.4% |
| opus | V1 | disabled | 320 | 45.0% | 44.7% | 0.0% | 10.3% | 89.7% |
| opus | V2 | default | 370 | 8.4% | 45.7% | 0.0% | 45.9% | 54.1% |
| opus | V2 | disabled | 370 | 24.3% | 34.6% | 0.0% | 41.1% | 58.9% |
| sol | V1 | none | 160 | 38.1% | 53.1% | 0.0% | 8.8% | 91.2% |
| sol | V2 | none | 185 | 27.6% | 35.1% | 0.0% | 37.3% | 62.7% |

