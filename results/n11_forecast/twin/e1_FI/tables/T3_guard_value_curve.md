# T3

<!-- N11 Stage 3 forecast twin (l1-n11-forecast-1) -->
<!-- reading FI -->

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 79.9% (369/462) | 0.546 | 38.5 | 7.1% | 34.2% | 34.3% | 5.6% | 59.6% |
| 2 | qwen3.6-27b-fp8 | - | 85.7% (396/462) | 0.640 | 172.2 | 2.0% | 22.0% | 23.0% | 5.5% | 77.0% |
| 3 | glm-4-9b | - | 69.5% (107/154) | 0.453 | 35.3 | 3.5% | 56.0% | 35.0% | 8.3% | 61.0% |
| 4 | openai | - | 78.6% (242/308) | 0.531 | 78.3 | 1.7% | 61.5% | 21.8% | 3.4% | 67.3% |
| 5 | deepseek | non_think | 0.0% (0/308) | 0.040 | 0.0 | 95.3% | 6.5% | 84.5% | 96.5% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/308) | - | - | 99.8% | 22.8% | 94.2% | 99.4% | 0.0% |
| 6 | sonnet | disabled | 83.1% (256/308) | 0.628 | 172.2 | 1.5% | 11.5% | 11.5% | 3.3% | 74.3% |
| 7 | opus | default | 89.6% (276/308) | 0.681 | 172.2 | 1.5% | 4.0% | 9.0% | 3.5% | 76.0% |
| 7 | opus | disabled | 89.0% (274/308) | 0.681 | 172.2 | 1.5% | 4.8% | 9.0% | 4.8% | 76.8% |
| 8 | sol | none | 83.8% (129/154) | 0.628 | 172.2 | 6.5% | 4.0% | 11.0% | 9.3% | 73.2% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

