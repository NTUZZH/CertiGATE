# T3

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: primary -->

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 83.3% (15/18) | 1.756 | 31.2 | 12.5% | 33.3% | 25.0% | 0.0% | 65.4% |
| 2 | qwen3.6-27b-fp8 | - | 100.0% (18/18) | 1.817 | 31.2 | 0.0% | 7.4% | 12.5% | 0.0% | 73.1% |
| 3 | glm-4-9b | - | 66.7% (4/6) | 1.636 | 31.2 | 0.0% | 33.3% | 25.0% | 7.7% | 65.4% |
| 4 | openai | - | 83.3% (10/12) | 1.760 | 2.4 | 0.0% | 33.3% | 12.5% | 0.0% | 69.2% |
| 5 | deepseek | non_think | 0.0% (0/12) | - | - | 87.5% | 11.1% | 100.0% | 100.0% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/12) | - | - | 100.0% | 22.2% | 100.0% | 98.1% | 0.0% |
| 6 | sonnet | disabled | 100.0% (12/12) | 1.817 | 31.2 | 0.0% | 5.6% | 12.5% | 0.0% | 65.4% |
| 7 | opus | default | 100.0% (12/12) | 1.817 | 31.2 | 0.0% | 0.0% | 12.5% | 0.0% | 65.4% |
| 7 | opus | disabled | 100.0% (12/12) | 1.817 | 31.2 | 0.0% | 0.0% | 12.5% | 3.8% | 65.4% |
| 8 | sol | none | 83.3% (5/6) | 1.756 | 2.4 | 0.0% | 0.0% | 12.5% | 3.8% | 69.2% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

