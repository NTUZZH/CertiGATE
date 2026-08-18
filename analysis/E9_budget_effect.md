# E9. The budget-level effect and the ordering-flip check

<!-- generated 2026-08-17 17:51:50 +0800 by e3_analyze.py (l1-e3-analysis-1) -->
<!-- E3 dedup rule: last row per (arm, budget_level, pipeline, repeat, item_id); earlier rows are superseded attempts -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- E3 slice E3-240 sha256 84b24f0232754344a4c16bcbe9e697b12aef9c707661a365c111424ee861e3e5 (240 items) -->
<!-- guard configurations: UNGUARDED b932b4a480c187968da8445242479be77d62341b7f35753f9cba7fdc3500dc89, G_FEAS 6176c8978a84adf727594d2a7a574dad6e03628e1d3cdddefbf76cfa79122390, G_CERT 52c094406252bf1ab57350d1ec4f9165f8bc4f7d83df2b99e1fb52356e829a42 -->
<!-- ladder anchors: /home/ziheng/PaperL1/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- /home/ziheng/PaperL1/results/e3_qwen14b/trajectories.jsonl sha256 604f356e6dc1625f83c816221fe87a61676a25cfcb1d7942fb70461f699c1204 -->
<!-- /home/ziheng/PaperL1/results/e3_qwen14b/calls.jsonl sha256 02b7d7d6018f16185c58c0c6db68aa04ece5e0071711ed35f388bd0eb90ff571 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen14b/verdicts.jsonl sha256 02000960325ccbef18394354273795ab22638e252eb7a1f4478a8ad26ad99606 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen14b/summary.json sha256 5db2ae0bb56ffb3cd22822db4e1535aec85967dda806639384344e9898153d5f -->
<!-- /home/ziheng/PaperL1/results/e3_qwen27b/trajectories.jsonl sha256 027f860346b1a8699699f98b05021a57f3087053d87d740770024d012bd1f278 -->
<!-- /home/ziheng/PaperL1/results/e3_qwen27b/calls.jsonl sha256 465f593d8d41de1e32fe3bf0d1e53d39936a238d38580272b2b1bf89daebe699 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen27b/verdicts.jsonl sha256 a21c32d9ff46d67068822a7b95db6bb4041d268e6816bf7351af8899ef3462de -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen27b/summary.json sha256 857e61c9e8cb14d8b1bd2b391da3a187e9917d2b47c10839898994a8779622ee -->
<!-- /home/ziheng/PaperL1/results/e3_openai/trajectories.jsonl sha256 a43366e597f6d8b2d4daffc7aebc3c05aa81bbb589a47b61e51a28054483b788 -->
<!-- /home/ziheng/PaperL1/results/e3_openai/calls.jsonl sha256 d77aca570ce5a50376931a1ae0d35fff1ed3fea87895e83b6c3a7ef8604f1136 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_openai/verdicts.jsonl sha256 168a8b20626a3b70ea16308f7a56af95abe146da4e5607fdb3d3b6f36692dfee -->
<!-- /home/ziheng/PaperL1/results/e3_replay_openai/summary.json sha256 ce1e2d5d91be629bf059f7d3c8e0efb53b698f89a07ace4fd5eb397b459fe62f -->
<!-- /home/ziheng/PaperL1/results/e3_deepseek/trajectories.jsonl sha256 4d34fcdb78f405748b1cd8b7784f4b37f059c12a59232629b059f4593d04197f -->
<!-- /home/ziheng/PaperL1/results/e3_deepseek/calls.jsonl sha256 e27dd7d19e9b1613dab14d2b85bc49c97b3471e52d4880f3e6ab8367e230b7c5 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_deepseek/verdicts.jsonl sha256 8e42a2c7a2730cee28e6de7aba54b4f96f88c87a712eb5a95c83fb8549106d4b -->
<!-- /home/ziheng/PaperL1/results/e3_replay_deepseek/summary.json sha256 71a18e38480b7f4c69cf1a64175231c5224f8361300d2f0f77b35a9f3c5b13a9 -->
<!-- /home/ziheng/PaperL1/results/e3_sonnet/trajectories.jsonl sha256 36fb12389daceec2a8b4a11779c4593c3af3bc25887c8888fb94d3aba49a129e -->
<!-- /home/ziheng/PaperL1/results/e3_sonnet/calls.jsonl sha256 951b14ebefb47a1fe40b4caffab1c97f397551ff4d921e9e4e00f47678c87753 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_sonnet/verdicts.jsonl sha256 8784318b09fb75599bb1d562cf156c3838b407833647fe82712e333b3d46ca36 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_sonnet/summary.json sha256 220adec6a82e3698c5d713681dd05f902ad4f943fd1fc8147ce427e8b319e7ed -->
<!-- /home/ziheng/PaperL1/results/e3_opus/trajectories.jsonl sha256 e8e32230b294a996e3e6cca11deae0fabf5f3d9d157707d540d628e189c27772 -->
<!-- /home/ziheng/PaperL1/results/e3_opus/calls.jsonl sha256 9e0d0e5ec13594ddb69278766aaadcff2d0e89dfb1c7bc78e422bac1a019ade6 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_opus/verdicts.jsonl sha256 9af87fa798a1aede09a82db34cadee9455d6d20b65302c16f0a4ac89b2453a17 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_opus/summary.json sha256 c4ee48fb4393dcaff42794cf3b16690777bf827faed96f0df60a48b823ccc2f1 -->
<!-- every verdict is recomputed from the trajectory log with e3_replay's own evaluation path and asserted equal to results/e3_replay_*; no number is adjusted to make an assertion pass -->

The tight and loose budgets side by side, per arm. `subject_kind` `variant` rows carry one system's value at each level; `ordering` rows carry the SINGLE-minus-MULTI (and guarded-minus-unguarded) difference at each level, so `ordering_flips` is true exactly when the sign of that difference changes between the two budgets, which is the flip condition Tran & Kiela's result turns on.

A flip needs both signs to be non-zero; a difference that is exactly zero at one level is recorded as `0` and is not counted as a flip.

### Cap binding and cost by level

| arm | variant | cap binds (tight) | cap binds (loose) | median variant tokens (tight) | median variant tokens (loose) | mean WWT vs RULE (tight) | mean WWT vs RULE (loose) | warranted (tight) | warranted (loose) |
|---|---|---|---|---|---|---|---|---|---|
| qwen14b | SINGLE+G | 57.1% | 3.8% | 3005 | 4434 | +0.71 | +0.78 | 99.0% | 99.6% |
| qwen14b | MULTI-G | 100.0% | 4.2% | 3646 | 10284 | +0.00 | +2.62 | 99.8% | 99.6% |
| qwen14b | MULTI-UG | 100.0% | 4.2% | 3646 | 9986 | +0.31 | +41.83 | 97.9% | 9.4% |
| qwen14b | SINGLE-UG * | 57.1% | 3.8% | 3000 | 3954 | +37.85 | +42.23 | 50.2% | 15.0% |
| qwen27b | SINGLE+G | 52.5% | 5.8% | 2932 | 3704 | -0.15 | +2.09 | 98.8% | 98.8% |
| qwen27b | MULTI-G | 100.0% | 13.3% | 2838 | 9698 | +0.00 | +2.82 | 100.0% | 97.9% |
| qwen27b | MULTI-UG | 100.0% | 13.3% | 2838 | 8526 | +0.00 | +39.61 | 100.0% | 20.4% |
| qwen27b | SINGLE-UG * | 52.5% | 5.8% | 2932 | 3157 | +12.37 | +37.99 | 52.9% | 17.5% |
| openai | SINGLE+G | 35.0% | 2.9% | 3009 | 3660 | +1.92 | +3.23 | 97.5% | 99.6% |
| openai | MULTI-G | 100.0% | 4.6% | 2540 | 6702 | +0.00 | +4.62 | 100.0% | 99.6% |
| openai | MULTI-UG | 100.0% | 4.6% | 2540 | 6430 | +1.95 | +42.70 | 92.1% | 4.6% |
| openai | SINGLE-UG * | 35.0% | 2.9% | 2994 | 3486 | +35.45 | +48.02 | 20.4% | 7.1% |
| deepseek | SINGLE+G | 72.9% | 24.6% | 3410 | 5036 | -0.00 | +0.23 | 97.1% | 100.0% |
| deepseek | MULTI-G | 100.0% | 16.7% | 3408 | 8519 | +0.00 | +0.03 | 99.6% | 100.0% |
| deepseek | MULTI-UG | 100.0% | 16.7% | 3408 | 6332 | +0.00 | +0.00 | 99.6% | 100.0% |
| deepseek | SINGLE-UG * | 72.9% | 24.6% | 3304 | 3398 | +0.00 | +0.00 | 93.8% | 100.0% |
| sonnet | SINGLE+G | 39.2% | 2.1% | 5022 | 5866 | +0.17 | +0.17 | 99.2% | 100.0% |
| sonnet | MULTI-G | 100.0% | 2.9% | 3913 | 10316 | +0.14 | +0.35 | 97.9% | 100.0% |
| sonnet | MULTI-UG | 100.0% | 2.9% | 3913 | 10049 | +14.51 | +40.82 | 73.3% | 23.8% |
| sonnet | SINGLE-UG * | 39.2% | 2.1% | 5022 | 5666 | +33.57 | +41.60 | 36.2% | 21.7% |
| opus | SINGLE+G | 41.2% | 1.7% | 5936 | 6238 | +0.32 | +3.14 | 98.3% | 100.0% |
| opus | MULTI-G | 100.0% | 3.3% | 5200 | 13247 | +0.01 | +3.04 | 99.6% | 99.6% |
| opus | MULTI-UG | 100.0% | 3.3% | 5200 | 13029 | +1.79 | +47.38 | 85.8% | 25.8% |
| opus | SINGLE-UG * | 41.2% | 1.7% | 5936 | 6093 | +37.62 | +48.01 | 30.4% | 22.9% |

### Orderings that flip between the budgets

21 outcome ordering(s) and 16 cost ordering(s) change sign. Only the outcome rows answer the flip question; a cost ordering flips whenever a pipeline that cannot finish inside the tight cap spends the cap instead of its natural need.

| arm | subject | metric | kind | tight | loose |
|---|---|---|---|---|---|
| qwen14b | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | 0.707582 | -1.847558 |
| qwen14b | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | 0.707582 | -1.847558 |
| qwen14b | SINGLE+G minus MULTI-G | violation_pass_through | outcome | 0.229167 | -0.086806 |
| qwen14b | SINGLE+G minus MULTI-G | violation_pass_through_strict | outcome | 0.152778 | -0.086806 |
| qwen27b | SINGLE+G minus MULTI-G | all_tokens_median | cost | 94.500000 | -5995.000000 |
| qwen27b | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 94.500000 | -5995.000000 |
| qwen27b | SINGLE+G minus MULTI-G | warranted_outcome_rate | outcome | -0.012500 | 0.008333 |
| qwen27b | SINGLE+G minus MULTI-G | false_block_rate | outcome | 0.031250 | -0.020833 |
| openai | SINGLE+G minus MULTI-G | all_tokens_median | cost | 469.000000 | -3042.000000 |
| openai | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 469.000000 | -3042.000000 |
| openai | SINGLE+G minus MULTI-G | variant_tokens_mean | cost | 389.137500 | -3286.325000 |
| openai | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | 1.924478 | -1.388597 |
| openai | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | 1.924478 | -1.388597 |
| openai | SINGLE+G minus MULTI-G | violation_pass_through | outcome | 0.416667 | -0.013889 |
| openai | SINGLE+G minus MULTI-G | violation_pass_through_strict | outcome | 0.298611 | -0.013889 |
| openai | SINGLE+G minus MULTI-G | certified_gap_median | outcome | 0.010924 | -0.000936 |
| deepseek | SINGLE+G minus MULTI-G | cap_binding_share | cost | -0.270833 | 0.079167 |
| deepseek | SINGLE+G minus MULTI-G | all_tokens_median | cost | 1.500000 | -3483.000000 |
| deepseek | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 1.500000 | -3483.000000 |
| deepseek | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | -0.003907 | 0.192245 |
| deepseek | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | -0.003907 | 0.192245 |
| deepseek | SINGLE+G minus MULTI-G | violation_pass_through | outcome | 0.048611 | -0.090278 |
| deepseek | SINGLE+G minus MULTI-G | violation_pass_through_strict | outcome | 0.041667 | -0.097222 |
| sonnet | SINGLE+G minus MULTI-G | all_tokens_median | cost | 1109.000000 | -4450.000000 |
| sonnet | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 1109.000000 | -4450.000000 |
| sonnet | SINGLE+G minus MULTI-G | variant_tokens_mean | cost | 310.191667 | -4735.595833 |
| sonnet | SINGLE+G minus MULTI-G | usd_total | cost | 0.466588 | -1.509325 |
| sonnet | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | 0.022430 | -0.179548 |
| sonnet | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | 0.022430 | -0.179548 |
| sonnet | SINGLE+G minus MULTI-G | certified_gap_median | outcome | 0.003413 | -0.002940 |
| opus | SINGLE+G minus MULTI-G | all_tokens_median | cost | 737.000000 | -7009.500000 |
| opus | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 737.000000 | -7009.500000 |
| opus | SINGLE+G minus MULTI-G | variant_tokens_mean | cost | 574.854167 | -6214.508333 |
| opus | SINGLE+G minus MULTI-G | usd_total | cost | 3.065330 | -4.643163 |
| opus | SINGLE+G minus MULTI-G | warranted_outcome_rate | outcome | -0.012500 | 0.004167 |
| opus | SINGLE+G minus MULTI-G | false_block_rate | outcome | 0.031250 | -0.010417 |
| opus | SINGLE+G minus MULTI-G | certified_gap_median | outcome | 0.001236 | -0.003300 |

