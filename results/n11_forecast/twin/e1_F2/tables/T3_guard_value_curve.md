# T3

<!-- N11 Stage 3 forecast twin (l1-n11-forecast-1) -->
<!-- reading F2 -->

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 79.9% (369/462) | 0.489 | 38.0 | 5.6% | 31.2% | 32.3% | 3.7% | 59.6% |
| 2 | qwen3.6-27b-fp8 | - | 85.7% (396/462) | 0.555 | 78.3 | 0.5% | 18.5% | 21.5% | 3.7% | 77.0% |
| 3 | glm-4-9b | - | 70.1% (108/154) | 0.422 | 34.6 | 2.0% | 54.0% | 33.5% | 6.7% | 61.0% |
| 4 | openai | - | 78.6% (242/308) | 0.481 | 78.3 | 0.2% | 59.8% | 20.2% | 1.6% | 67.3% |
| 5 | deepseek | non_think | 0.0% (0/308) | 0.014 | 0.0 | 95.3% | 3.0% | 84.5% | 96.3% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/308) | - | - | 99.8% | 19.5% | 94.2% | 99.4% | 0.0% |
| 6 | sonnet | disabled | 83.1% (256/308) | 0.516 | 78.3 | 0.0% | 8.0% | 9.2% | 1.5% | 74.3% |
| 7 | opus | default | 89.6% (276/308) | 0.558 | 78.3 | 0.0% | 0.5% | 6.0% | 1.7% | 76.0% |
| 7 | opus | disabled | 89.0% (274/308) | 0.558 | 78.3 | 0.0% | 1.2% | 7.0% | 3.0% | 76.8% |
| 8 | sol | none | 83.8% (129/154) | 0.527 | 38.0 | 5.0% | 0.5% | 9.0% | 7.5% | 73.2% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

