# DG18: cluster-aware inferential tests for the E3 agent-layer comparison

Section 5.4 reports rates with a cluster bootstrap over the replayed scheduling instances, on the stated ground that instructions written on the same instance are not independent, and then reports every agent-layer p-value from an exact McNemar or Wilcoxon test that treats each item as its own draw. This file removes that inconsistency. It re-runs the whole declared family of 96 tests with the paired sign flipped at the instance level rather than at the item level, re-runs the Holm correction on the result, and maps every number the manuscript cites from its published p-value to its cluster-aware one.

## Headline

- **Every p-value the manuscript prints keeps its verdict.** The loose-budget null result, the smallest uncorrected p behind it, the five-of-six guard result and the tight-budget separation all survive.
- 2 of the 96 tests in the declared family change their Holm-corrected verdict, and neither is printed as a p-value in the paper. Both are the guard's effect on violation pass-through (MULTI-G against MULTI-UG at the loose budget), which the manuscript reports as a rate change and uses to set the equivalence margins, never as a significance claim.
- 0 of 96 change their uncorrected verdict at the 5 percent level.
- Holm-significant over the family of 96: 20 tests item-level, 18 tests cluster-aware. Reading the exact cluster p-values instead of the Monte Carlo ones gives the same 18 and the same two changes, so nothing here turns on the resample count.
- Under the pass-through content rule, the reading Table tab:e3-rd's risk differences use, 2 of 96 change their Holm-corrected verdict, and they are the same two cells.
- 62 of the 96 tests have at most one differing item per instance. For those there is no within-instance dependence to correct for, and the cluster test returns the item-level p-value exactly; the script asserts that identity rather than assuming it.

## The numbers the manuscript reads off these tests

| Manuscript claim | Published (item-level) | Cluster-aware | Verdict |
| --- | --- | --- | --- |
| Table 6 column 'S vs M Holm p' and Section 6.4, no SINGLE+G against MULTI-G contrast at the loose budget is significant (`\eThreeAgentHolmMin` = 1.00 over 24 cells) | min Holm p = 1.00 | min Holm p = 1.00 | holds |
| App. E, the smallest uncorrected p over the same 24 cells is 0.092 (`\eThreeAgentRawPLooseMin`) | min raw p = 0.09229 | min raw p = 0.09229 exact (0.0912 by Monte Carlo) | holds |
| Table 6 column 'Guard at fixed architecture / Holm p' and Section 6.4, the guard's effect on executed-schedule quality is Holm-significant on five of six arms (`\eThreeGuardSignificantArmsWord`) | 5 of 6 arms | 5 of 6 arms | holds |
| Section 6.4, the two architectures separate at the tight budget | 9 of 24 cells Holm-significant | 9 of 24 | holds |

### Loose budget, SINGLE+G against MULTI-G: the paper's null result

These 24 cells carry Table 6's 'S vs M Holm p' column and the Section 6.4 sentence about no detectable advantage. A Holm p of 1.00 in both the published and the cluster-aware column means the null result does not depend on the exchangeable unit. The largest move is on end-task quality, where the published test ranks the differences and the declared cluster statistic averages them; the rank column is the like-for-like comparison there. Over these 24 cells the exact cluster-aware uncorrected p-value is 0.80 to 1.48 times the published one, the extremes being wilcoxon quality on Claude Sonnet 5 and wilcoxon quality on Qwen3-14B.

| Arm | Test | Instances used | Item p | Cluster p | Cluster p exact | Cluster p exact, rank | Hier. boot p | Item Holm | Cluster Holm | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-14B | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | catch | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.729 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | violation passthrough | 6 of 52 | 0.219 | 0.218 | 0.219 | 0.219 | 0.192 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | quality | 10 of 55 | 0.199 | 0.292 | 0.295 | 0.211 | 0.373 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | false block | 2 of 52 | 0.5 | 0.498 | 0.5 | 0.5 | 0.363 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | catch | 13 of 52 | 0.0923 | 0.0912 | 0.0923 | 0.0923 | 0.117 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | violation passthrough | 4 of 52 | 0.625 | 0.63 | 0.625 | 0.625 | 0.489 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | quality | 1 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 0.988 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | catch | 2 of 52 | 0.5 | 0.505 | 0.5 | 0.5 | 0.502 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | violation passthrough | 8 of 52 | 0.754 | 0.731 | 0.727 | 0.727 | 0.681 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | quality | 6 of 55 | 0.0938 | 0.095 | 0.0938 | 0.0938 | 0.088 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | catch | 4 of 52 | 0.125 | 0.125 | 0.125 | 0.125 | 0.0706 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | violation passthrough | 16 of 52 | 0.143 | 0.168 | 0.168 | 0.168 | 0.179 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | quality | 8 of 55 | 0.426 | 0.436 | 0.438 | 0.445 | 0.54 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | catch | 2 of 52 | 0.5 | 0.504 | 0.5 | 0.5 | 0.358 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | violation passthrough | 8 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | quality | 5 of 55 | 0.156 | 0.128 | 0.125 | 0.125 | 0.119 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | false block | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.724 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | catch | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.722 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | violation passthrough | 4 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | quality | 1 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 0.997 | 1.00 | 1.00 | unchanged |

### Loose budget, MULTI-G against MULTI-UG on end-task quality: the paper's positive result

These 6 cells carry Table 6's last column and the five-of-six claim. They are the cells where moving the draw to the instance could have cost a positive finding, and it does not: the effect is spread over 16 to 22 distinct instances on the five significant arms, so clustering costs the test resolution but not the verdict. The Monte Carlo column sits on its own floor of 1/(20000+1) on four arms; the exact column is the one to quote there. Over these 6 cells the exact cluster-aware uncorrected p-value is 1.22 to 128.00 times the published one, the extremes being wilcoxon quality on DeepSeek V4-Pro and wilcoxon quality on Qwen3-14B.

| Arm | Test | Instances used | Item p | Cluster p | Cluster p exact | Cluster p exact, rank | Hier. boot p | Item Holm | Cluster Holm | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-14B | quality | 18 of 55 | 5.96e-08 | 5e-05 | 7.63e-06 | 7.63e-06 | 0.0001 | 5.3e-06 | 0.0048 | unchanged |
| Qwen3.6-27B-FP8 | quality | 16 of 55 | 4.77e-07 | 0.00015 | 3.05e-05 | 3.05e-05 | 0.0001 | 4.15e-05 | 0.0123 | unchanged |
| GPT-5.4-mini | quality | 20 of 55 | 5.96e-08 | 5e-05 | 1.91e-06 | 1.91e-06 | 0.0001 | 5.3e-06 | 0.0048 | unchanged |
| DeepSeek V4-Pro | quality | 12 of 55 | 0.772 | 0.942 | 0.941 | 0.798 | 0.962 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | quality | 21 of 55 | 1.49e-08 | 5e-05 | 9.54e-07 | 9.54e-07 | 0.0001 | 1.36e-06 | 0.0048 | unchanged |
| Claude Opus 5 | quality | 22 of 55 | 7.45e-09 | 5e-05 | 4.77e-07 | 4.77e-07 | 0.0001 | 6.93e-07 | 0.0048 | unchanged |

### Loose budget, MULTI-G against MULTI-UG on the binary outcomes: where the two verdicts that change sit

None of these p-values is printed in the manuscript. The pass-through column is the reference effect the equivalence margins of Section 5.4 are a fraction of, and that is an effect size rather than a significance claim, so the two changes below do not reach any sentence in the paper. They are reported because a family-wide correction is only meaningful if every member of the family is reported. Over these 18 cells the exact cluster-aware uncorrected p-value is 1.00 to 10.92 times the published one, the extremes being false block on Qwen3-14B and violation passthrough on Claude Opus 5.

| Arm | Test | Instances used | Item p | Cluster p | Cluster p exact | Hier. boot p | Item Holm | Cluster Holm | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-14B | false block | 1 of 52 | 1.00 | 1.00 | 1.00 | 0.734 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | catch | 2 of 52 | 0.5 | 0.501 | 0.5 | 0.348 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | violation passthrough | 22 of 52 | 3.03e-06 | 5e-05 | 9.54e-06 | 0.0001 | 0.000258 | 0.0048 | unchanged |
| Qwen3.6-27B-FP8 | false block | 5 of 52 | 0.0625 | 0.0617 | 0.0625 | 0.0263 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | catch | 14 of 52 | 6.1e-05 | 0.0001 | 0.000122 | 0.0001 | 0.00488 | 0.0084 | unchanged |
| Qwen3.6-27B-FP8 | violation passthrough | 15 of 52 | 0.000121 | 0.001 | 0.000732 | 0.0007 | 0.00945 | 0.078 | CHANGES |
| GPT-5.4-mini | false block | 1 of 52 | 1.00 | 1.00 | 1.00 | 0.734 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | catch | 6 of 52 | 0.0312 | 0.0327 | 0.0312 | 0.0118 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | violation passthrough | 17 of 52 | 0.000855 | 0.00145 | 0.00166 | 0.0031 | 0.065 | 0.112 | unchanged |
| DeepSeek V4-Pro | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | catch | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | violation passthrough | 27 of 52 | 1.86e-09 | 5e-05 | 1.49e-08 | 0.0001 | 1.77e-07 | 0.0048 | unchanged |
| Claude Sonnet 5 | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | catch | 4 of 52 | 0.125 | 0.125 | 0.125 | 0.0581 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | violation passthrough | 23 of 52 | 0.000104 | 0.0002 | 0.000332 | 0.001 | 0.00819 | 0.0162 | unchanged |
| Claude Opus 5 | false block | 1 of 52 | 1.00 | 1.00 | 1.00 | 0.74 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | catch | 1 of 52 | 1.00 | 1.00 | 1.00 | 0.73 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | violation passthrough | 21 of 52 | 0.000311 | 0.0039 | 0.00339 | 0.0025 | 0.0239 | 0.289 | CHANGES |

### Tight budget, SINGLE+G against MULTI-G

Not printed as p-values, but these are the members of the family that carry most of the correction, and Section 6.4 reads the tight budget as a difference in how often a system finishes off them. Nine cells are Holm-significant before and after. Over these 24 cells the exact cluster-aware uncorrected p-value is 0.61 to 256.00 times the published one, the extremes being wilcoxon quality on GPT-5.4-mini and violation passthrough on GPT-5.4-mini.

| Arm | Test | Instances used | Item p | Cluster p | Cluster p exact | Cluster p exact, rank | Hier. boot p | Item Holm | Cluster Holm | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-14B | false block | 3 of 52 | 0.25 | 0.25 | 0.25 | 0.25 | 0.172 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | catch | 24 of 52 | 3.73e-09 | 5e-05 | 1.19e-07 | 1.19e-07 | 0.0001 | 3.5e-07 | 0.0048 | unchanged |
| Qwen3-14B | violation passthrough | 16 of 52 | 3.81e-06 | 0.00025 | 3.05e-05 | 3.05e-05 | 0.0001 | 0.00032 | 0.02 | unchanged |
| Qwen3-14B | quality | 7 of 55 | 0.238 | 0.153 | 0.156 | 0.312 | 0.164 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | false block | 3 of 52 | 0.25 | 0.249 | 0.25 | 0.25 | 0.157 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | catch | 17 of 52 | 1.53e-05 | 5e-05 | 1.53e-05 | 1.53e-05 | 0.0001 | 0.00126 | 0.0048 | unchanged |
| Qwen3.6-27B-FP8 | violation passthrough | 17 of 52 | 1.91e-06 | 5e-05 | 1.53e-05 | 1.53e-05 | 0.0001 | 0.000164 | 0.0048 | unchanged |
| Qwen3.6-27B-FP8 | quality | 9 of 55 | 0.552 | 0.392 | 0.395 | 0.672 | 0.31 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | false block | 6 of 52 | 0.0312 | 0.0316 | 0.0312 | 0.0312 | 0.0106 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | catch | 26 of 52 | 1.02e-08 | 5e-05 | 2.98e-08 | 2.98e-08 | 0.0001 | 9.42e-07 | 0.0048 | unchanged |
| GPT-5.4-mini | violation passthrough | 28 of 52 | 2.91e-11 | 5e-05 | 7.45e-09 | 7.45e-09 | 0.0001 | 2.79e-09 | 0.0048 | unchanged |
| GPT-5.4-mini | quality | 9 of 55 | 0.293 | 0.178 | 0.18 | 0.52 | 0.184 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | false block | 8 of 52 | 0.0703 | 0.0686 | 0.0703 | 0.0703 | 0.0733 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | catch | 10 of 52 | 0.000977 | 0.00205 | 0.00195 | 0.00195 | 0.0003 | 0.0732 | 0.156 | unchanged |
| DeepSeek V4-Pro | violation passthrough | 4 of 52 | 0.125 | 0.126 | 0.125 | 0.125 | 0.0772 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | quality | 2 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | false block | 5 of 52 | 0.375 | 0.369 | 0.375 | 0.375 | 0.335 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | catch | 17 of 52 | 2.1e-05 | 0.0003 | 0.000229 | 0.000229 | 0.0002 | 0.0017 | 0.0237 | unchanged |
| Claude Sonnet 5 | violation passthrough | 19 of 52 | 0.00258 | 0.0037 | 0.00384 | 0.00384 | 0.0065 | 0.191 | 0.277 | unchanged |
| Claude Sonnet 5 | quality | 10 of 55 | 0.0541 | 1.00 | 1.00 | 0.0664 | 0.808 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | false block | 3 of 52 | 0.25 | 0.252 | 0.25 | 0.25 | 0.154 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | catch | 22 of 52 | 1.49e-08 | 5e-05 | 4.77e-07 | 4.77e-07 | 0.0001 | 1.36e-06 | 0.0048 | unchanged |
| Claude Opus 5 | violation passthrough | 22 of 52 | 1.52e-05 | 0.0001 | 9.54e-06 | 9.54e-06 | 0.0003 | 0.00126 | 0.0084 | unchanged |
| Claude Opus 5 | quality | 10 of 55 | 0.796 | 0.55 | 0.547 | 0.836 | 0.627 | 1.00 | 1.00 | unchanged |

### Tight budget, MULTI-G against MULTI-UG

The guard barely moves anything at the tight budget, because the multi-agent pipeline mostly does not finish. Nothing here is significant under either reading. Over these 24 cells the exact cluster-aware uncorrected p-value is 1.00 to 1.00 times the published one, the extremes being false block on Qwen3-14B and wilcoxon quality on Claude Opus 5.

| Arm | Test | Instances used | Item p | Cluster p | Cluster p exact | Cluster p exact, rank | Hier. boot p | Item Holm | Cluster Holm | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-14B | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | catch | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | violation passthrough | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3-14B | quality | 0 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | catch | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | violation passthrough | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Qwen3.6-27B-FP8 | quality | 0 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | false block | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | catch | 7 of 52 | 0.0156 | 0.0155 | 0.0156 | 0.0156 | 0.0078 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | violation passthrough | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.988 | 1.00 | 1.00 | unchanged |
| GPT-5.4-mini | quality | 1 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | false block | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.73 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | catch | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | violation passthrough | 0 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| DeepSeek V4-Pro | quality | 0 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | false block | 5 of 52 | 0.0625 | 0.0635 | 0.0625 | 0.0625 | 0.0253 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | catch | 7 of 52 | 0.0156 | 0.0144 | 0.0156 | 0.0156 | 0.0042 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | violation passthrough | 3 of 52 | 0.25 | 0.253 | 0.25 | 0.25 | 0.21 | 1.00 | 1.00 | unchanged |
| Claude Sonnet 5 | quality | 3 of 55 | 0.25 | 0.248 | 0.25 | 0.25 | 0.259 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | false block | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.731 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | catch | 3 of 52 | 0.25 | 0.251 | 0.25 | 0.25 | 0.12 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | violation passthrough | 1 of 52 | 1.00 | 1.00 | 1.00 | 1.00 | 0.942 | 1.00 | 1.00 | unchanged |
| Claude Opus 5 | quality | 1 of 55 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | unchanged |

## The verdicts that change, in full

**MULTI-G vs MULTI-UG / qwen27b / loose / mcnemar_violation_passthrough.** The paired difference is -18.75 percentage points over 96 pairs, 22 of them discordant, but the discordant pairs sit on only 15 of the 52 instances, with as many as 3 of them on one instance. The item-level exact McNemar p-value is 0.0001211 and its Holm-corrected value 0.00945; flipping the sign at the instance level gives 0.0007324 and 0.078. The finding survives as a rate change and as the reference effect behind the equivalence margins, and it is not printed as a significance claim anywhere in the manuscript. The effect is still significant before correction under the cluster-aware test (0.0007324 against a 5 percent level); what it no longer clears is the family-wide correction over 96.

**MULTI-G vs MULTI-UG / opus / loose / mcnemar_violation_passthrough.** The paired difference is -19.79 percentage points over 96 pairs, 27 of them discordant, but the discordant pairs sit on only 21 of the 52 instances, with as many as 3 of them on one instance. The item-level exact McNemar p-value is 0.0003107 and its Holm-corrected value 0.0239; flipping the sign at the instance level gives 0.003394 and 0.289. The finding survives as a rate change and as the reference effect behind the equivalence margins, and it is not printed as a significance claim anywhere in the manuscript. The effect is still significant before correction under the cluster-aware test (0.003394 against a 5 percent level); what it no longer clears is the family-wide correction over 96.

## Methods, in a form the paper can use

The E3 items are not independent of one another: several instructions are written on the same replayed scheduling instance, and two systems compared on those instructions share whatever the instance makes easy or hard. The exact McNemar and Wilcoxon tests treat each item as its own draw, so their p-values are re-derived here with the draw taken at the instance level. Under the paired null the sign of a difference is exchangeable, and clustering means the signs of all differences on one instance flip together rather than separately; the reference distribution of the mean paired difference is therefore built by drawing one sign per instance, 20,000 times at a fixed seed, and the two-sided p-value is the share of draws whose statistic is at least as large in absolute value as the observed one. On the binary outcomes this is McNemar's sign test with the discordant pairs grouped by instance, and on end-task quality it is the signed-rank test with the same grouping. A hierarchical bootstrap that resamples instances and then items within instance, 20,000 replicates at the same seed, gives a second p-value by inverting the percentile interval. Instances whose differences cancel within the instance carry no information about a difference and are not counted among the draws, which is the clustered form of dropping concordant pairs. Holm correction is then applied over the same declared family of 96 agent-layer tests.

## How to read the columns

- `n_clusters_used` is the number of replayed instances whose paired differences do not cancel to zero inside the instance. Only those instances carry information about a difference, so they are the draws the permutation null randomises. It is the clustered counterpart of the discordant-pair count in McNemar's test and of the non-zero difference count in Wilcoxon's, and it is the honest denominator to quote beside a cluster-aware p-value.
- `p_cluster_perm` is the Monte Carlo sign-flip p-value at 20,000 draws, with the observed configuration counted in both numerator and denominator, so its floor is 5.0e-05 rather than zero. `p_cluster_perm_share` is the bare share of draws at least as extreme, which is the quantity the design declares and which can be exactly zero.
- `p_cluster_perm_exact` enumerates the same sign-flip null instead of sampling it, so it has no resolution floor. The two agree wherever the Monte Carlo value is above its floor; where they disagree, the exact column is the one to quote.
- `p_cluster_rank_perm` and `p_cluster_rank_exact` flip the same instance-level signs on Wilcoxon's signed ranks rather than on the raw differences. On the binary outcomes the two statistics are the same test, because every non-zero difference has the same magnitude and therefore the same rank, and the script asserts that. On end-task quality they differ, and the rank version is the direct analogue of the published Wilcoxon test, while the mean version is the statistic the design declares.
- `p_hier_boot` resamples instances and then items within instance, and reads the p-value by inverting the two-sided percentile interval. It is a secondary check on the permutation rather than a replacement: it is conservative wherever a large share of the resampled differences land exactly on zero, which on these binary outcomes is the common case.
- `reduces_to_item_test` is true when no instance holds more than one differing item.
- `reading` is `e8_disposition` for the pass-through predicate every published p-value was computed on, and `content_rule` for the V4/V6 reading behind Table tab:e3-rd's risk differences and every DG6 interval. The two agree on false block, on catch and on quality, which the script asserts.

## Self-check

24382 of 24382 assertions passed. No cluster-aware number is computed until every 2x2 cell, every item-level p-value and both Holm corrections in analysis/E8_adjudication.csv have been reproduced from results/e3_replay_*/verdicts.jsonl and the quality rebuild.

- `stage3c` (the item-level reproduction): 12273 assertions, 0 failed.
- `stage3d` (the cluster stage): 270 assertions, 0 failed.
- `stage4` (the join back into DG6): 48 assertions, 0 failed.

## Provenance

- generated 2026-08-23 11:35:46 +0800 by e3_intervals.py (l1-dg18-cluster-1)
- cluster sign-flip permutation: 20000 draws, numpy default_rng seeded [20260814, 1800000 + cell index]; the exchangeable unit is the replayed scheduling instance, so all paired differences on one instance flip sign together
- hierarchical bootstrap: 20000 replicates, numpy default_rng seeded [20260814, 2700000 + cell index]; instances resampled with replacement, then items within each drawn instance, with the p-value read by inverting the two-sided percentile interval
- exact columns enumerate the same sign-flip null instead of sampling it (full enumeration up to 24 contributing instances, an integer dynamic program above that where the cluster sums are integers), so they have no Monte Carlo resolution floor
- self-check: no cluster-aware number is computed until all 72 2x2 tables over both contrasts, all 96 item-level p-values, and both Holm corrections in analysis/E8_adjudication.csv are reproduced from results/e3_replay_*/verdicts.jsonl and the quality rebuild
- two readings are reported: e8_disposition is the reading every p-value printed in the manuscript was computed on, and content_rule applies the V4/V6 pass-through rule that Table tab:e3-rd's risk differences and every DG6 interval use; they differ on violation pass-through alone
- <project>/results/e3_replay_qwen14b/verdicts.jsonl sha256 d4a7de38e598b24bbb7e10c5b8c745b29fa547a158005962f65f99a9209d290a
- <project>/results/e3_replay_qwen27b/verdicts.jsonl sha256 c932d3122723f50857c1ce4f78de3ac983a936df1e69e6b316fb0f458667aca6
- <project>/results/e3_replay_openai/verdicts.jsonl sha256 168a8b20626a3b70ea16308f7a56af95abe146da4e5607fdb3d3b6f36692dfee
- <project>/results/e3_replay_deepseek/verdicts.jsonl sha256 8e42a2c7a2730cee28e6de7aba54b4f96f88c87a712eb5a95c83fb8549106d4b
- <project>/results/e3_replay_sonnet/verdicts.jsonl sha256 8784318b09fb75599bb1d562cf156c3838b407833647fe82712e333b3d46ca36
- <project>/results/e3_replay_opus/verdicts.jsonl sha256 9af87fa798a1aede09a82db34cadee9455d6d20b65302c16f0a4ac89b2453a17
- <project>/analysis/E8_adjudication.csv sha256 141d978148e3c835dd5d4d7acbef8a83e26957b37cfe178c06c17e064b1d22a7
- end-task quality: suite sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a
- end-task quality: adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321
- end-task quality: e3_analyze reconciliation 7533/7533 passed
