# D2

<!-- N11 Stage 3 forecast twin (l1-n11-forecast-1) -->
<!-- reading F2 -->

A block rate is a joint measurement: the proposer has to produce the illegal operation before the guard can refuse it. On the schema and feasibility classes the stronger arms decline to act instead, returning an empty operation list, which is correct handling and leaves the guard nothing to block. Reading a falling V1 or V2 block rate as falling guard recall would be wrong, and this table is what prevents that reading: the last column, block plus decline, is what the pair actually achieves.

| arm | class | think | items | blocked by the guard | declined (empty proposal) | refused by the model | applied with operations | blocked, declined or refused |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | V1 | - | 480 | 66.0% | 9.2% | 0.0% | 24.8% | 75.2% |
| qwen3-14b | V2 | - | 555 | 66.3% | 5.0% | 0.0% | 28.6% | 71.4% |
| qwen3.6-27b-fp8 | V1 | - | 480 | 68.8% | 19.2% | 0.0% | 12.1% | 87.9% |
| qwen3.6-27b-fp8 | V2 | - | 555 | 63.2% | 15.3% | 0.0% | 21.4% | 78.6% |
| glm-4-9b | V1 | - | 160 | 71.2% | 1.9% | 0.0% | 26.9% | 73.1% |
| glm-4-9b | V2 | - | 185 | 74.1% | 0.5% | 0.0% | 25.4% | 74.6% |
| openai | V1 | - | 320 | 71.6% | 1.6% | 0.0% | 26.9% | 73.1% |
| openai | V2 | - | 370 | 61.1% | 7.0% | 0.0% | 31.9% | 68.1% |
| deepseek | V1 | non_think | 320 | 74.4% | 25.6% | 0.0% | 0.0% | 100.0% |
| deepseek | V1 | think_high | 320 | 77.8% | 22.2% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | non_think | 370 | 65.4% | 34.6% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | think_high | 370 | 68.9% | 31.1% | 0.0% | 0.0% | 100.0% |
| sonnet | V1 | disabled | 320 | 55.9% | 30.0% | 0.0% | 14.1% | 85.9% |
| sonnet | V2 | disabled | 370 | 42.4% | 27.0% | 0.0% | 30.5% | 69.5% |
| opus | V1 | default | 320 | 22.5% | 71.9% | 0.0% | 5.6% | 94.4% |
| opus | V1 | disabled | 320 | 44.1% | 45.6% | 0.0% | 10.3% | 89.7% |
| opus | V2 | default | 370 | 5.7% | 46.2% | 0.0% | 48.1% | 51.9% |
| opus | V2 | disabled | 370 | 21.9% | 35.1% | 0.0% | 43.0% | 57.0% |
| sol | V1 | none | 160 | 37.5% | 53.8% | 0.0% | 8.8% | 91.2% |
| sol | V2 | none | 185 | 25.4% | 35.7% | 0.0% | 38.9% | 61.1% |

