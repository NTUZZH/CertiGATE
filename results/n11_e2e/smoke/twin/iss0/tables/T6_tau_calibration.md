# T6

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

The certificate's tolerance tau enters the guard only as the final gap-vs-tau comparison, so the sweep is post-processing over the certificates already recorded: no replay and no model call. Every arm's curve is re-derived here with the accepted sweep's own functions, and every cell the accepted sweep already published is asserted equal to it.

The reported operating point is `tau_smallest`, the tightest gate meeting the benign false-block budget (the frozen 'largest tau' rule degenerates because the false-block rate is non-increasing in tau; the decision record, 2026-08-12). The floor column is the share of benign twins blocked at the schema or feasibility stage, which no value of tau can move.

| arm | mode | think | V3 sep @0.05 | V3 sep @0.20 | V3 sep @0.50 | false blocks @0.20 | false-block floor | tau at fb<=5% | fb<=1% reachable | in accepted E2 sweep |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| deepseek | M_constrained | think_high | 0.0% | 0.0% | 0.0% | 98.1% | 98.1% |  | no | no |
| deepseek | M_free | non_think | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| deepseek | M_free | think_high | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| glm-4-9b | M_constrained | - | 66.7% | 66.7% | 66.7% | 7.7% | 7.7% |  | no | no |
| glm-4-9b | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| openai | M_constrained | - | 83.3% | 83.3% | 83.3% | 0.0% | 0.0% | 0.02 | 0.02 | no |
| openai | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| opus | M_constrained | default | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 0.02 | 0.02 | no |
| opus | M_constrained | disabled | 100.0% | 100.0% | 100.0% | 3.8% | 3.8% | 0.02 | no | no |
| opus | M_free | default | 0.0% | 0.0% | 0.0% | 21.2% | 21.2% |  | no | no |
| opus | M_free | disabled | 8.3% | 8.3% | 8.3% | 21.2% | 21.2% |  | no | no |
| qwen3-14b | M_constrained | - | 83.3% | 83.3% | 83.3% | 0.0% | 0.0% | 0.02 | 0.02 | no |
| qwen3-14b | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| qwen3.6-27b-fp8 | M_constrained | - | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 0.02 | 0.02 | no |
| qwen3.6-27b-fp8 | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| sol | M_constrained | none | 83.3% | 83.3% | 66.7% | 3.8% | 3.8% | 0.02 | no | no |
| sonnet | M_constrained | disabled | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 0.02 | 0.02 | no |
| sonnet | M_free | disabled | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |

