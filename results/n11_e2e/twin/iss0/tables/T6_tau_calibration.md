# T6

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

The certificate's tolerance tau enters the guard only as the final gap-vs-tau comparison, so the sweep is post-processing over the certificates already recorded: no replay and no model call. Every arm's curve is re-derived here with the accepted sweep's own functions, and every cell the accepted sweep already published is asserted equal to it.

The reported operating point is `tau_smallest`, the tightest gate meeting the benign false-block budget (the frozen 'largest tau' rule degenerates because the false-block rate is non-increasing in tau; the decision record, 2026-08-12). The floor column is the share of benign twins blocked at the schema or feasibility stage, which no value of tau can move.

| arm | mode | think | V3 sep @0.05 | V3 sep @0.20 | V3 sep @0.50 | false blocks @0.20 | false-block floor | tau at fb<=5% | fb<=1% reachable | in accepted E2 sweep |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 0.3% | 0.3% | 0.0% | 96.5% | 96.3% |  | no | no |
| deepseek | M_constrained | think_high | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | no |
| deepseek | M_free | non_think | 0.0% | 0.0% | 0.0% | 97.3% | 97.1% |  | no | no |
| deepseek | M_free | think_high | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | no |
| glm-4-9b | M_constrained | - | 83.8% | 70.8% | 39.6% | 8.8% | 6.1% |  | no | no |
| glm-4-9b | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| openai | M_constrained | - | 91.2% | 79.2% | 47.1% | 4.3% | 1.6% | 0.15 | no | no |
| openai | M_free | - | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | no |
| opus | M_constrained | default | 99.4% | 89.6% | 55.8% | 4.4% | 1.7% | 0.15 | no | no |
| opus | M_constrained | disabled | 99.0% | 89.0% | 55.5% | 5.8% | 3.0% | 0.3 | no | no |
| opus | M_free | default | 0.3% | 0.3% | 0.3% | 26.7% | 26.7% |  | no | no |
| opus | M_free | disabled | 1.6% | 1.6% | 1.3% | 21.4% | 21.3% |  | no | no |
| qwen3-14b | M_constrained | - | 92.2% | 80.5% | 48.1% | 5.0% | 0.3% | 0.2 | no | no |
| qwen3-14b | M_free | - | 0.0% | 0.0% | 0.0% | 99.1% | 99.1% |  | no | no |
| qwen3.6-27b-fp8 | M_constrained | - | 96.1% | 85.7% | 53.9% | 6.4% | 3.7% | 0.3 | no | no |
| qwen3.6-27b-fp8 | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| sol | M_constrained | none | 94.2% | 83.8% | 50.6% | 9.8% | 7.1% |  | no | no |
| sonnet | M_constrained | disabled | 94.5% | 83.1% | 51.9% | 4.3% | 1.5% | 0.15 | no | no |
| sonnet | M_free | disabled | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |

