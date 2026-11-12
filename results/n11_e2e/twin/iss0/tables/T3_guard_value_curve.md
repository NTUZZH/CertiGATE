# T3

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 80.5% (372/462) | 0.490 | 38.5 | 6.0% | 7.0% | 12.0% | 5.0% | 59.6% |
| 2 | qwen3.6-27b-fp8 | - | 85.7% (396/462) | 0.546 | 172.2 | 3.0% | 4.0% | 5.0% | 6.4% | 77.0% |
| 3 | glm-4-9b | - | 70.8% (109/154) | 0.376 | 35.3 | 4.5% | 19.5% | 14.0% | 8.8% | 61.0% |
| 4 | openai | - | 79.2% (244/308) | 0.483 | 78.3 | 3.2% | 17.8% | 4.8% | 4.3% | 67.3% |
| 5 | deepseek | non_think | 0.3% (1/308) | 0.048 | 0.3 | 95.3% | 6.5% | 84.5% | 96.5% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/308) | - | - | 99.8% | 22.8% | 91.2% | 99.4% | 0.0% |
| 6 | sonnet | disabled | 83.1% (256/308) | 0.516 | 172.2 | 3.0% | 3.5% | 3.2% | 4.3% | 74.3% |
| 7 | opus | default | 89.6% (276/308) | 0.567 | 172.2 | 3.0% | 3.5% | 3.0% | 4.4% | 76.0% |
| 7 | opus | disabled | 89.0% (274/308) | 0.567 | 172.2 | 3.0% | 3.5% | 3.0% | 5.8% | 76.8% |
| 8 | sol | none | 83.8% (129/154) | 0.516 | 172.2 | 6.5% | 3.5% | 3.0% | 9.8% | 73.2% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

