# T6

<!-- N11 Stage 3, late reading t_d' = t_start -->

The certificate's tolerance tau enters the guard only as the final gap-vs-tau comparison, so the sweep is post-processing over the certificates already recorded: no replay and no model call. Every arm's curve is re-derived here with the accepted sweep's own functions, and every cell the accepted sweep already published is asserted equal to it.

The reported operating point is `tau_smallest`, the tightest gate meeting the benign false-block budget (the frozen 'largest tau' rule degenerates because the false-block rate is non-increasing in tau; the decision record, 2026-08-12). The floor column is the share of benign twins blocked at the schema or feasibility stage, which no value of tau can move.

| arm | mode | think | V3 sep @0.05 | V3 sep @0.20 | V3 sep @0.50 | false blocks @0.20 | false-block floor | tau at fb<=5% | fb<=1% reachable | in accepted E2 sweep |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 0.0% | 0.0% | 0.0% | 96.3% | 96.3% |  | no | no |
| deepseek | M_constrained | think_high | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | no |
| deepseek | M_free | non_think | 0.0% | 0.0% | 0.0% | 97.1% | 97.1% |  | no | no |
| deepseek | M_free | think_high | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | no |
| glm-4-9b | M_constrained | - | 79.2% | 70.1% | 54.5% | 6.7% | 6.7% |  | no | no |
| glm-4-9b | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| openai | M_constrained | - | 87.7% | 79.2% | 62.0% | 2.1% | 2.1% | 0.02 | no | no |
| openai | M_free | - | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | no |
| opus | M_constrained | default | 97.4% | 90.3% | 72.1% | 1.7% | 1.7% | 0.02 | no | no |
| opus | M_constrained | disabled | 96.8% | 89.6% | 71.8% | 3.0% | 3.0% | 0.02 | no | no |
| opus | M_free | default | 0.3% | 0.3% | 0.3% | 26.7% | 26.7% |  | no | no |
| opus | M_free | disabled | 1.6% | 1.6% | 1.6% | 21.3% | 21.3% |  | no | no |
| qwen3-14b | M_constrained | - | 89.0% | 80.5% | 62.3% | 3.9% | 3.9% | 0.02 | no | no |
| qwen3-14b | M_free | - | 0.0% | 0.0% | 0.0% | 99.1% | 99.1% |  | no | no |
| qwen3.6-27b-fp8 | M_constrained | - | 92.9% | 86.4% | 68.8% | 3.7% | 3.7% | 0.02 | no | no |
| qwen3.6-27b-fp8 | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |
| sol | M_constrained | none | 90.9% | 84.4% | 66.2% | 7.5% | 7.5% |  | no | no |
| sonnet | M_constrained | disabled | 90.9% | 83.8% | 66.9% | 1.6% | 1.6% | 0.02 | no | no |
| sonnet | M_free | disabled | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | no |

