# T6

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->

The certificate's tolerance tau enters the guard only as the final gap-vs-tau comparison, so the sweep is post-processing over the certificates already recorded: no replay and no model call. Every arm's curve is re-derived here with the accepted sweep's own functions, and every cell the accepted sweep already published is asserted equal to it.

The reported operating point is `tau_smallest`, the tightest gate meeting the benign false-block budget (the frozen 'largest tau' rule degenerates because the false-block rate is non-increasing in tau; the decision record, 2026-08-12). The floor column is the share of benign twins blocked at the schema or feasibility stage, which no value of tau can move.

| arm | mode | think | V3 sep @0.05 | V3 sep @0.20 | V3 sep @0.50 | false blocks @0.20 | false-block floor | tau at fb<=5% | fb<=1% reachable | in accepted E2 sweep |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 0.2% | 0.2% | 0.0% | 97.2% | 97.1% |  | no | yes |
| deepseek | M_constrained | think_high | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | yes |
| deepseek | M_free | non_think | 0.0% | 0.0% | 0.0% | 97.9% | 97.8% |  | no | yes |
| deepseek | M_free | think_high | 0.0% | 0.0% | 0.0% | 99.5% | 99.5% |  | no | yes |
| glm-4-9b | M_constrained | - | 83.6% | 72.7% | 45.0% | 8.0% | 5.4% |  | no | yes |
| glm-4-9b | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | yes |
| openai | M_constrained | - | 89.1% | 78.9% | 50.0% | 3.9% | 1.2% | 0.15 | no | yes |
| openai | M_free | - | 0.0% | 0.0% | 0.0% | 99.5% | 99.5% |  | no | yes |
| opus | M_constrained | default | 98.6% | 90.5% | 58.6% | 3.9% | 1.3% | 0.15 | no | yes |
| opus | M_constrained | disabled | 98.4% | 90.0% | 58.4% | 5.0% | 2.4% | 0.2 | no | yes |
| opus | M_free | default | 0.2% | 0.2% | 0.2% | 28.1% | 28.1% |  | no | yes |
| opus | M_free | disabled | 1.6% | 1.6% | 1.4% | 23.1% | 22.9% |  | no | yes |
| qwen3-14b | M_constrained | - | 91.8% | 82.3% | 51.8% | 4.4% | 0.2% | 0.15 | 1.0 | yes |
| qwen3-14b | M_free | - | 0.0% | 0.0% | 0.0% | 99.3% | 99.3% |  | no | yes |
| qwen3.6-27b-fp8 | M_constrained | - | 95.6% | 87.0% | 57.3% | 5.5% | 2.9% | 0.3 | no | yes |
| qwen3.6-27b-fp8 | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | yes |
| sol | M_constrained | none | 90.9% | 82.3% | 52.7% | 8.6% | 6.0% |  | no | yes |
| sonnet | M_constrained | disabled | 95.2% | 85.9% | 55.9% | 3.8% | 1.2% | 0.15 | no | yes |
| sonnet | M_free | disabled | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | yes |

