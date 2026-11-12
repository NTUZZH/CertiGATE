# T2

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: primary -->

The enforcement axis, ordered by what the wire actually enforces: `none` (M_free, no enforcement field), `json_object` (reply with a JSON object, no schema; DeepSeek's only constrained mode), and the two real schema enforcements, `json_schema` (provider-side strict outputs) and `xgrammar` (local grammar-guided decoding). Shape drift is the share of completions that do not parse as a proposal about this instance; the silent no-op column is what that drift costs when nothing gates, because the lenient repair drops the operations it cannot read and executes what remains, which is often nothing.

| enforcement | arm | mode | think | items | JSON invalid | wrong shape | schema valid | G-CERT blocked at schema | UNGUARDED silent no-op | benign translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| none | qwen3-14b | M_free | - | 5169 | 6.56% | 84.56% | 8.88% | 91.8% | 92.6% | 0.0% |
| none | qwen3.6-27b-fp8 | M_free | - | 5169 | 0.00% | 87.99% | 12.01% | 88.6% | 99.2% | 0.0% |
| none | glm-4-9b | M_free | - | 1723 | 98.37% | 1.63% | 0.00% | 100.0% | 99.3% | 0.0% |
| none | openai | M_free | - | 3446 | 0.00% | 94.37% | 5.63% | 94.6% | 99.3% | 0.2% |
| none | deepseek | M_free | non_think | 3446 | 0.00% | 80.85% | 19.15% | 81.1% | 99.6% | 0.0% |
| none | deepseek | M_free | think_high | 3446 | 1.28% | 82.82% | 15.90% | 84.4% | 98.6% | 0.0% |
| none | sonnet | M_free | disabled | 3446 | 9.05% | 77.02% | 13.93% | 86.4% | 99.2% | 0.0% |
| none | opus | M_free | default | 3446 | 0.12% | 16.54% | 7.49% | 16.7% | 22.9% | 1.3% |
| none | opus | M_free | disabled | 3446 | 0.23% | 13.23% | 7.72% | 13.8% | 16.4% | 5.1% |
| json_object | deepseek | M_constrained | non_think | 3446 | 0.00% | 78.87% | 21.13% | 78.9% | 99.8% | 0.0% |
| json_object | deepseek | M_constrained | think_high | 3446 | 2.21% | 81.78% | 16.02% | 84.3% | 97.2% | 0.0% |
| xgrammar | qwen3-14b | M_constrained | - | 5169 | 0.35% | 0.00% | 99.65% | 16.5% | 8.2% | 59.6% |
| xgrammar | qwen3.6-27b-fp8 | M_constrained | - | 5169 | 0.00% | 0.00% | 100.00% | 10.9% | 11.7% | 77.0% |
| xgrammar | glm-4-9b | M_constrained | - | 1723 | 0.00% | 0.00% | 100.00% | 18.0% | 1.6% | 61.0% |
| json_schema | openai | M_constrained | - | 3446 | 0.00% | 0.00% | 100.00% | 16.1% | 4.2% | 67.3% |
| json_schema | sonnet | M_constrained | disabled | 3446 | 0.00% | 0.00% | 100.00% | 7.2% | 17.6% | 74.3% |
| json_schema | opus | M_constrained | default | 3446 | 0.00% | 0.00% | 99.94% | 2.8% | 26.9% | 76.0% |
| json_schema | opus | M_constrained | disabled | 3446 | 0.00% | 0.00% | 99.94% | 5.0% | 23.1% | 76.8% |
| json_schema | sol | M_constrained | none | 1723 | 1.22% | 0.00% | 98.78% | 6.4% | 22.8% | 73.2% |

