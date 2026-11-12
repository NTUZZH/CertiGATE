# T3

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: primary -->

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 80.5% (372/462) | 0.710 | 39.0 | 5.6% | 31.2% | 32.3% | 3.7% | 59.6% |
| 2 | qwen3.6-27b-fp8 | - | 86.4% (399/462) | 0.851 | 172.2 | 0.5% | 18.5% | 21.5% | 3.7% | 77.0% |
| 3 | glm-4-9b | - | 70.1% (108/154) | 0.615 | 33.5 | 2.0% | 54.0% | 33.5% | 6.7% | 61.0% |
| 4 | openai | - | 79.2% (244/308) | 0.708 | 78.3 | 0.2% | 59.8% | 20.2% | 1.6% | 67.3% |
| 5 | deepseek | non_think | 0.0% (0/308) | 0.000 | 0.0 | 95.3% | 3.0% | 84.5% | 96.3% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/308) | - | - | 99.8% | 19.5% | 94.2% | 99.4% | 0.0% |
| 6 | sonnet | disabled | 83.8% (258/308) | 0.726 | 172.2 | 0.0% | 8.0% | 9.2% | 1.5% | 74.3% |
| 7 | opus | default | 90.3% (278/308) | 0.901 | 172.2 | 0.0% | 0.5% | 6.0% | 1.7% | 76.0% |
| 7 | opus | disabled | 89.6% (276/308) | 0.901 | 172.2 | 0.0% | 1.2% | 7.0% | 3.0% | 76.8% |
| 8 | sol | none | 84.4% (130/154) | 0.775 | 172.2 | 5.0% | 0.5% | 9.0% | 7.5% | 73.2% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

