# T3

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 82.3% (543/660) | 0.524 | 52.0 | 6.1% | 7.0% | 12.0% | 4.4% | 59.3% |
| 2 | qwen3.6-27b-fp8 | - | 87.0% (574/660) | 0.603 | 172.2 | 2.7% | 4.0% | 5.0% | 5.5% | 73.3% |
| 3 | glm-4-9b | - | 72.7% (160/220) | 0.456 | 52.0 | 4.1% | 19.5% | 14.0% | 8.0% | 60.8% |
| 4 | openai | - | 78.9% (347/440) | 0.502 | 78.3 | 3.0% | 17.8% | 4.8% | 3.9% | 65.4% |
| 5 | deepseek | non_think | 0.2% (1/440) | 0.048 | 0.3 | 93.4% | 6.5% | 84.5% | 97.2% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/440) | - | - | 99.1% | 22.8% | 91.2% | 99.4% | 0.0% |
| 6 | sonnet | disabled | 85.9% (378/440) | 0.586 | 172.2 | 2.7% | 3.5% | 3.2% | 3.8% | 70.4% |
| 7 | opus | default | 90.5% (398/440) | 0.619 | 172.2 | 2.7% | 3.5% | 3.0% | 3.9% | 72.4% |
| 7 | opus | disabled | 90.0% (396/440) | 0.619 | 172.2 | 2.7% | 3.5% | 3.0% | 5.0% | 72.6% |
| 8 | sol | none | 82.3% (181/220) | 0.585 | 172.2 | 7.7% | 3.5% | 3.0% | 8.6% | 69.1% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

