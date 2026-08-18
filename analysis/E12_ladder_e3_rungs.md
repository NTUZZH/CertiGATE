# E12. The T5 ladder's two agent rungs, on the E3-240 slice

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

The two rungs T5 prints as `pending E3`, computed on the E3-240 slice with `ladder_replay.summarise_profile`, which is the function that produced every other rung. The header is T5's, so the rows drop into that table unchanged; the trailing columns carry what T5 has no place for.

**Two things must be stated before these rows are read next to T5's.** First, the item set: T5's rungs run on all 2,000 suite instructions and these run on the 240-item E3 slice, so `wwt_original_vs_rule_bh` here is measured against the RULE anchor **of the same 240 items** (the `rule_scope` column says so) and `wwt_original_vs_rule_fullsuite_bh` repeats it against T5's own full-suite RULE mean for literal column compatibility. Second, the terminal convention: an empty operations list is a referral in E3 and an applied-but-inert proposal in E1, so `share_referred_to_human` here and in T5's rungs 3 to 5 are not the same quantity. `n_referred_empty_ops` counts the E3 referrals so the size of the divergence is visible.

The ladder anchors are the accepted ones (/home/ziheng/PaperL1/analysis/ladder, reconciliation 4208/4208 passed).

### The ladder on the E3-240 slice, tight budget

| step | arm | variant | items | applied+cert | applied uncert | blocked | referred | violation pass-through | of which non-empty | pass-through, content rule | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | - | - | 240 | - | - | 0.0% | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | - | - | 240 | - | 63.3% | 0.0% | 26.7% | 38.9% | 38.9% | 18.8% | 26.7% | 0.017 | +42.85 bh | +0.00 bh |
| 6. SINGLE+G | qwen14b | SINGLE+G | 480 | 35.6% | - | 13.7% | 50.6% | 25.0% | 25.0% | 17.4% | 99.0% | 0.017 | +0.71 bh | +0.00 bh |
| 7. MULTI | qwen14b | MULTI-G | 480 | 1.9% | - | 0.2% | 97.9% | 2.1% | 2.1% | 2.1% | 99.8% | 0.004 | +0.00 bh | +0.00 bh |
| 7. MULTI | qwen14b | MULTI-UG | 480 | - | 2.1% | 0.0% | 97.9% | 2.1% | 2.1% | 2.1% | 97.9% | - | +0.31 bh | +0.00 bh |
| 6. SINGLE+G | qwen14b | SINGLE-UG * | 480 | - | 45.0% | 0.0% | 50.2% | 39.2% | 39.2% | 30.9% | 50.2% | - | +37.85 bh | +0.00 bh |
| 6. SINGLE+G | qwen27b | SINGLE+G | 240 | 38.8% | - | 8.3% | 52.9% | 29.2% | 29.2% | 22.2% | 98.8% | 0.010 | -0.15 bh | +0.00 bh |
| 7. MULTI | qwen27b | MULTI-G | 240 | - | - | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | - | +0.00 bh | +0.00 bh |
| 7. MULTI | qwen27b | MULTI-UG | 240 | - | - | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | - | +0.00 bh | +0.00 bh |
| 6. SINGLE+G | qwen27b | SINGLE-UG * | 240 | - | 41.2% | 0.0% | 52.9% | 33.3% | 33.3% | 26.4% | 52.9% | - | +12.37 bh | +0.00 bh |
| 6. SINGLE+G | openai | SINGLE+G | 240 | 57.9% | - | 20.4% | 21.7% | 45.8% | 45.8% | 34.0% | 97.5% | 0.011 | +1.92 bh | +0.00 bh |
| 7. MULTI | openai | MULTI-G | 240 | 2.9% | - | 5.0% | 92.1% | 4.2% | 4.2% | 4.2% | 100.0% | 0.000 | +0.00 bh | +0.00 bh |
| 7. MULTI | openai | MULTI-UG | 240 | - | 3.3% | 0.0% | 92.1% | 4.9% | 4.9% | 4.9% | 92.1% | - | +1.95 bh | +0.00 bh |
| 6. SINGLE+G | openai | SINGLE-UG * | 240 | - | 67.1% | 0.0% | 20.4% | 60.4% | 60.4% | 47.9% | 20.4% | - | +35.45 bh | +0.00 bh |
| 6. SINGLE+G | deepseek | SINGLE+G | 240 | 6.7% | - | 7.5% | 85.8% | 4.9% | 4.9% | 4.2% | 97.1% | 0.003 | -0.00 bh | +0.00 bh |
| 7. MULTI | deepseek | MULTI-G | 240 | - | - | 0.4% | 99.6% | 0.0% | 0.0% | 0.0% | 99.6% | - | +0.00 bh | +0.00 bh |
| 7. MULTI | deepseek | MULTI-UG | 240 | - | - | 0.0% | 99.6% | 0.0% | 0.0% | 0.0% | 99.6% | - | +0.00 bh | +0.00 bh |
| 6. SINGLE+G | deepseek | SINGLE-UG * | 240 | - | - | 0.0% | 93.8% | 0.0% | 0.0% | 0.0% | 93.8% | - | +0.00 bh | +0.00 bh |
| 6. SINGLE+G | sonnet | SINGLE+G | 240 | 51.7% | - | 12.1% | 36.2% | 34.0% | 34.0% | 22.9% | 99.2% | 0.012 | +0.17 bh | +0.00 bh |
| 7. MULTI | sonnet | MULTI-G | 240 | 20.4% | - | 6.2% | 73.3% | 18.1% | 18.1% | 15.3% | 97.9% | 0.009 | +0.15 bh | +0.00 bh |
| 7. MULTI | sonnet | MULTI-UG | 240 | - | 21.7% | 0.0% | 73.3% | 20.1% | 20.1% | 17.4% | 73.3% | - | +14.51 bh | +0.00 bh |
| 6. SINGLE+G | sonnet | SINGLE-UG * | 240 | - | 60.0% | 0.0% | 36.2% | 47.2% | 47.2% | 35.4% | 36.2% | - | +33.57 bh | +0.00 bh |
| 6. SINGLE+G | opus | SINGLE+G | 240 | 55.0% | - | 14.6% | 30.4% | 33.3% | 33.3% | 16.0% | 98.3% | 0.010 | +0.32 bh | +0.00 bh |
| 7. MULTI | opus | MULTI-G | 240 | 12.5% | - | 1.7% | 85.8% | 9.7% | 9.7% | 8.3% | 99.6% | 0.009 | +0.01 bh | +0.00 bh |
| 7. MULTI | opus | MULTI-UG | 240 | - | 12.9% | 0.0% | 85.8% | 10.4% | 10.4% | 9.0% | 85.8% | - | +1.79 bh | +0.00 bh |
| 6. SINGLE+G | opus | SINGLE-UG * | 240 | - | 65.4% | 0.0% | 30.4% | 50.0% | 50.0% | 31.9% | 30.4% | - | +37.62 bh | +0.00 bh |

### The ladder on the E3-240 slice, loose budget

| step | arm | variant | items | applied+cert | applied uncert | blocked | referred | violation pass-through | of which non-empty | pass-through, content rule | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | - | - | 240 | - | - | 0.0% | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | - | - | 240 | - | 63.3% | 0.0% | 26.7% | 38.9% | 38.9% | 18.8% | 26.7% | 0.017 | +42.85 bh | +0.00 bh |
| 6. SINGLE+G | qwen14b | SINGLE+G | 480 | 66.2% | - | 2.1% | 31.7% | 47.2% | 47.2% | 36.8% | 99.6% | 0.010 | +0.78 bh | +0.00 bh |
| 7. MULTI | qwen14b | MULTI-G | 480 | 70.0% | - | 1.5% | 28.5% | 55.9% | 55.9% | 45.5% | 99.6% | 0.005 | +2.62 bh | +0.00 bh |
| 7. MULTI | qwen14b | MULTI-UG | 480 | - | 81.7% | 0.0% | 9.4% | 73.6% | 73.6% | 62.5% | 9.4% | - | +41.83 bh | +15.21 bh |
| 6. SINGLE+G | qwen14b | SINGLE-UG * | 480 | - | 78.3% | 0.0% | 15.0% | 66.0% | 66.0% | 54.9% | 15.0% | - | +42.23 bh | +15.21 bh |
| 6. SINGLE+G | qwen27b | SINGLE+G | 240 | 69.2% | - | 4.6% | 26.2% | 51.4% | 51.4% | 38.2% | 98.8% | 0.008 | +2.09 bh | +0.00 bh |
| 7. MULTI | qwen27b | MULTI-G | 240 | 66.2% | - | 8.3% | 25.4% | 50.0% | 50.0% | 38.2% | 97.9% | 0.008 | +2.82 bh | +0.00 bh |
| 7. MULTI | qwen27b | MULTI-UG | 240 | - | 73.8% | 0.0% | 20.4% | 62.5% | 62.5% | 50.0% | 20.4% | - | +39.61 bh | +15.21 bh |
| 6. SINGLE+G | qwen27b | SINGLE-UG * | 240 | - | 75.8% | 0.0% | 17.5% | 62.5% | 62.5% | 48.6% | 17.5% | - | +37.99 bh | +0.00 bh |
| 6. SINGLE+G | openai | SINGLE+G | 240 | 76.7% | - | 2.1% | 21.2% | 61.8% | 61.8% | 49.3% | 99.6% | 0.008 | +3.23 bh | +0.00 bh |
| 7. MULTI | openai | MULTI-G | 240 | 77.1% | - | 3.3% | 19.6% | 63.2% | 63.2% | 50.7% | 99.6% | 0.009 | +4.62 bh | +0.00 bh |
| 7. MULTI | openai | MULTI-UG | 240 | - | 84.6% | 0.0% | 4.6% | 75.0% | 75.0% | 61.8% | 4.6% | - | +42.70 bh | +15.21 bh |
| 6. SINGLE+G | openai | SINGLE-UG * | 240 | - | 83.3% | 0.0% | 7.1% | 72.2% | 72.2% | 59.0% | 7.1% | - | +48.02 bh | +15.21 bh |
| 6. SINGLE+G | deepseek | SINGLE+G | 240 | 43.8% | - | 1.7% | 54.6% | 27.1% | 27.1% | 18.8% | 100.0% | 0.010 | +0.23 bh | +0.00 bh |
| 7. MULTI | deepseek | MULTI-G | 240 | 50.4% | - | 0.4% | 49.2% | 36.1% | 36.1% | 28.5% | 100.0% | 0.012 | +0.03 bh | +0.00 bh |
| 7. MULTI | deepseek | MULTI-UG | 240 | - | - | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | - | +0.00 bh | +0.00 bh |
| 6. SINGLE+G | deepseek | SINGLE-UG * | 240 | - | - | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | - | +0.00 bh | +0.00 bh |
| 6. SINGLE+G | sonnet | SINGLE+G | 240 | 68.3% | - | 1.2% | 30.4% | 47.9% | 47.9% | 33.3% | 100.0% | 0.005 | +0.17 bh | +0.00 bh |
| 7. MULTI | sonnet | MULTI-G | 240 | 65.0% | - | 1.7% | 33.3% | 43.8% | 43.8% | 29.2% | 100.0% | 0.008 | +0.35 bh | +0.00 bh |
| 7. MULTI | sonnet | MULTI-UG | 240 | - | 73.8% | 0.0% | 23.8% | 58.3% | 58.3% | 43.1% | 23.8% | - | +40.82 bh | +15.21 bh |
| 6. SINGLE+G | sonnet | SINGLE-UG * | 240 | - | 75.4% | 0.0% | 21.7% | 59.7% | 59.7% | 44.4% | 21.7% | - | +41.60 bh | +0.00 bh |
| 6. SINGLE+G | opus | SINGLE+G | 240 | 65.8% | - | 0.0% | 34.2% | 43.8% | 43.8% | 25.0% | 100.0% | 0.005 | +3.14 bh | +0.00 bh |
| 7. MULTI | opus | MULTI-G | 240 | 63.7% | - | 0.8% | 35.4% | 41.7% | 41.7% | 22.2% | 99.6% | 0.008 | +3.04 bh | +0.00 bh |
| 7. MULTI | opus | MULTI-UG | 240 | - | 70.8% | 0.0% | 25.8% | 54.9% | 54.9% | 34.7% | 25.8% | - | +47.38 bh | +15.21 bh |
| 6. SINGLE+G | opus | SINGLE-UG * | 240 | - | 73.3% | 0.0% | 22.9% | 57.6% | 57.6% | 38.2% | 22.9% | - | +48.01 bh | +15.21 bh |

