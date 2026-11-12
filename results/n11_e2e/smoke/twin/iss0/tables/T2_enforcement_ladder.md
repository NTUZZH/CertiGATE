# T2

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

The enforcement axis, ordered by what the wire actually enforces: `none` (M_free, no enforcement field), `json_object` (reply with a JSON object, no schema; DeepSeek's only constrained mode), and the two real schema enforcements, `json_schema` (provider-side strict outputs) and `xgrammar` (local grammar-guided decoding). Shape drift is the share of completions that do not parse as a proposal about this instance; the silent no-op column is what that drift costs when nothing gates, because the lenient repair drops the operations it cannot read and executes what remains, which is often nothing.

| enforcement | arm | mode | think | items | JSON invalid | wrong shape | schema valid | G-CERT blocked at schema | UNGUARDED silent no-op | benign translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| none | qwen3-14b | M_free | - | 216 | 5.09% | 86.57% | 8.33% | 91.7% | 94.9% | 0.0% |
| none | qwen3.6-27b-fp8 | M_free | - | 216 | 0.00% | 86.11% | 13.89% | 86.1% | 100.0% | 0.0% |
| none | glm-4-9b | M_free | - | 72 | 100.00% | 0.00% | 0.00% | 100.0% | 100.0% | 0.0% |
| none | openai | M_free | - | 144 | 0.00% | 92.36% | 7.64% | 92.4% | 99.3% | 0.0% |
| none | deepseek | M_free | non_think | 144 | 0.00% | 82.64% | 17.36% | 82.6% | 100.0% | 0.0% |
| none | deepseek | M_free | think_high | 144 | 1.39% | 79.86% | 18.75% | 81.2% | 99.3% | 0.0% |
| none | sonnet | M_free | disabled | 144 | 11.11% | 76.39% | 12.50% | 87.5% | 100.0% | 0.0% |
| none | opus | M_free | default | 144 | 0.00% | 17.36% | 6.25% | 17.4% | 23.6% | 0.0% |
| none | opus | M_free | disabled | 144 | 0.00% | 15.97% | 3.47% | 16.0% | 17.4% | 0.0% |
| json_object | deepseek | M_constrained | non_think | 144 | 0.00% | 82.64% | 17.36% | 82.6% | 100.0% | 0.0% |
| json_object | deepseek | M_constrained | think_high | 144 | 2.78% | 79.86% | 17.36% | 82.6% | 97.2% | 0.0% |
| xgrammar | qwen3-14b | M_constrained | - | 216 | 0.00% | 0.00% | 100.00% | 8.3% | 8.3% | 65.4% |
| xgrammar | qwen3.6-27b-fp8 | M_constrained | - | 216 | 0.00% | 0.00% | 100.00% | 6.9% | 13.9% | 73.1% |
| xgrammar | glm-4-9b | M_constrained | - | 72 | 0.00% | 0.00% | 100.00% | 9.7% | 4.2% | 65.4% |
| json_schema | openai | M_constrained | - | 144 | 0.00% | 0.00% | 100.00% | 8.3% | 4.2% | 69.2% |
| json_schema | sonnet | M_constrained | disabled | 144 | 0.00% | 0.00% | 100.00% | 6.2% | 17.4% | 65.4% |
| json_schema | opus | M_constrained | default | 144 | 0.00% | 0.00% | 100.00% | 2.8% | 27.8% | 65.4% |
| json_schema | opus | M_constrained | disabled | 144 | 0.00% | 0.00% | 100.00% | 5.6% | 23.6% | 65.4% |
| json_schema | sol | M_constrained | none | 72 | 0.00% | 0.00% | 100.00% | 4.2% | 23.6% | 69.2% |

