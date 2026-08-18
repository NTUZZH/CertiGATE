# T1. E1 main table: block rate and false-block rate

<!-- generated 2026-08-17 17:24:01 +0800 by paper_tables.py (l1-paper-tables-1) -->
<!-- dedup rule applied to the hosted raw logs before evaluation: last row per (mode, thinking, repeat, item_id); hosted logs only -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- ladder anchors: /home/ziheng/PaperL1/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- /home/ziheng/PaperL1/results/e1_eval_qwen14b/summary.json sha256 793c76b07b492ef0fd70878913b6c90449fa7d884edd530817eaf98c1c51c1c8 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_qwen27b/summary.json sha256 78745e80ca0550e27d754b70e2e8f8bd7d33a6ba11b419852ec4c05a9c5a57d5 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_glm9b/summary.json sha256 bb806173f35bcd5013b1a9b77223f0d2e16346375670a6dca65dbb8859099724 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_gpt54mini/summary.json sha256 5da1e6beba8ac75283ee1e5f9352c2fff80eb08fe74f590e551b35b5364fa028 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_deepseek/summary.json sha256 574ebad8772fe47ec758487469231be95f2e457399fa619ad553b571dc8ee8f9 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_sonnet5/summary.json sha256 e50203a3a4474af675a4ed1e397c52ecd1f1b057502f21987d01ec6e8878e4f6 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_opus5/summary.json sha256 d1ab21e2a71280e44d8eed9feda0f8031e4c3160d17fd995414d6a1398ae4f15 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_sol/summary.json sha256 fa3ae6264fcdfbd3b311ad59a8ed88bc8540176adea8b4b043b2fecf5086379d -->
<!-- /home/ziheng/PaperL1/results/e2_tau_sweep/curves.csv sha256 e9ca179c57029c6ae23d0512f12da901884072192c96addff321de94bf04fc76 -->
<!-- rows are the accepted record; every overlapping cell is asserted equal to it -->

Block rate is measured on the labelled violations of each class; the false-block rate is the same guard's block rate on the 800 matched benign twins, and the two are always read as a pair. Rows are pooled over repeats. `sep` is the V3/V4 evidence for claim C2: the proposal passed the feasibility guard and only the certificate refused it.

### Qwen3-14B (open, local, BF16) - M_constrained / xgrammar

6000 instructions pooled; benign false blocks 0.2% under G-FEAS and 4.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 64.6% | 66.7% | 170 | 10 | 2.1% |
| V2 | 600 | 0.0% | 62.0% | 65.3% | 228 | 20 | 3.3% |
| **V3** | 660 | 0.0% | 0.5% | 82.7% | 657 | 543 | **82.3%** |
| **V4** | 660 | 0.0% | 1.1% | 6.1% | 653 | 33 | **5.0%** |
| V5 | 600 | 0.0% | 3.0% | 7.0% | 582 | 24 | 4.0% |
| V6 | 600 | 0.0% | 7.0% | 12.0% | 558 | 30 | 5.0% |
| benign | 2400 | 0.0% | 0.2% | 4.4% | 2394 | 99 | 4.1% |

### Qwen3-14B (open, local, BF16) - M_free / none

6000 instructions pooled; benign false blocks 99.3% under G-FEAS and 99.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 91.0% | 91.7% | 43 | 3 | 0.6% |
| V2 | 600 | 0.0% | 95.0% | 95.5% | 30 | 3 | 0.5% |
| **V3** | 660 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 660 | 0.0% | 99.5% | 99.5% | 3 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 46.0% | 49.0% | 324 | 18 | 3.0% |
| V6 | 600 | 0.0% | 92.5% | 92.5% | 45 | 0 | 0.0% |
| benign | 2400 | 0.0% | 99.3% | 99.3% | 17 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_constrained / xgrammar

6000 instructions pooled; benign false blocks 2.9% under G-FEAS and 5.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 68.8% | 69.4% | 150 | 3 | 0.6% |
| V2 | 600 | 0.0% | 60.7% | 62.2% | 236 | 9 | 1.5% |
| **V3** | 660 | 0.0% | 0.5% | 87.4% | 657 | 574 | **87.0%** |
| **V4** | 660 | 0.0% | 0.0% | 2.7% | 660 | 18 | **2.7%** |
| V5 | 600 | 0.0% | 0.5% | 4.0% | 597 | 21 | 3.5% |
| V6 | 600 | 0.0% | 2.0% | 5.0% | 588 | 18 | 3.0% |
| benign | 2400 | 0.0% | 2.9% | 5.5% | 2331 | 63 | 2.6% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_free / none

6000 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 81.2% | 81.9% | 90 | 3 | 0.6% |
| V2 | 600 | 0.0% | 82.5% | 83.0% | 105 | 3 | 0.5% |
| **V3** | 660 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 660 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 35.0% | 37.5% | 390 | 15 | 2.5% |
| V6 | 600 | 0.0% | 90.5% | 90.5% | 57 | 0 | 0.0% |
| benign | 2400 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_constrained / xgrammar

2000 instructions pooled; benign false blocks 5.4% under G-FEAS and 8.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 70.0% | 71.2% | 48 | 2 | 1.2% |
| V2 | 200 | 0.0% | 75.5% | 76.5% | 49 | 2 | 1.0% |
| **V3** | 220 | 0.0% | 2.7% | 75.5% | 214 | 160 | **72.7%** |
| **V4** | 220 | 0.0% | 1.4% | 4.1% | 217 | 6 | **2.7%** |
| V5 | 200 | 0.0% | 16.0% | 19.5% | 168 | 7 | 3.5% |
| V6 | 200 | 0.0% | 9.0% | 14.0% | 182 | 10 | 5.0% |
| benign | 800 | 0.0% | 5.4% | 8.0% | 757 | 21 | 2.6% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_free / none

2000 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V2 | 200 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| **V3** | 220 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 220 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 200 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V6 | 200 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 800 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GPT-5.4-mini (closed, budget tier) - M_constrained / json_schema

4000 instructions pooled; benign false blocks 1.2% under G-FEAS and 3.9% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 71.6% | 71.9% | 91 | 1 | 0.3% |
| V2 | 400 | 0.0% | 62.7% | 64.5% | 149 | 7 | 1.8% |
| **V3** | 440 | 0.0% | 0.5% | 79.3% | 438 | 347 | **78.9%** |
| **V4** | 440 | 0.0% | 0.2% | 3.0% | 439 | 12 | **2.7%** |
| V5 | 400 | 0.0% | 13.8% | 17.8% | 345 | 16 | 4.0% |
| V6 | 400 | 0.0% | 1.5% | 4.8% | 394 | 13 | 3.2% |
| benign | 1600 | 0.0% | 1.2% | 3.9% | 1580 | 42 | 2.6% |

### GPT-5.4-mini (closed, budget tier) - M_free / none

4000 instructions pooled; benign false blocks 99.5% under G-FEAS and 99.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 98.1% | 98.1% | 6 | 0 | 0.0% |
| V2 | 400 | 0.0% | 93.5% | 94.2% | 26 | 3 | 0.8% |
| **V3** | 440 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 440 | 0.0% | 99.5% | 99.5% | 2 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 70.5% | 72.5% | 118 | 8 | 2.0% |
| V6 | 400 | 0.0% | 91.2% | 91.2% | 35 | 0 | 0.0% |
| benign | 1600 | 0.0% | 99.5% | 99.5% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking non_think

4000 instructions pooled; benign false blocks 97.1% under G-FEAS and 97.2% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 74.4% | 74.4% | 82 | 0 | 0.0% |
| V2 | 400 | 0.0% | 60.5% | 62.0% | 158 | 6 | 1.5% |
| **V3** | 440 | 0.0% | 99.3% | 99.5% | 3 | 1 | **0.2%** |
| **V4** | 440 | 0.0% | 93.4% | 93.4% | 29 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 3.0% | 6.5% | 388 | 14 | 3.5% |
| V6 | 400 | 0.0% | 84.5% | 84.5% | 62 | 0 | 0.0% |
| benign | 1600 | 0.0% | 97.1% | 97.2% | 47 | 2 | 0.1% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking think_high

4000 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 77.8% | 77.8% | 71 | 0 | 0.0% |
| V2 | 400 | 0.0% | 65.2% | 66.2% | 139 | 4 | 1.0% |
| **V3** | 440 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 440 | 0.0% | 99.1% | 99.1% | 4 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 19.5% | 22.8% | 322 | 13 | 3.2% |
| V6 | 400 | 0.0% | 91.2% | 91.2% | 35 | 0 | 0.0% |
| benign | 1600 | 0.0% | 99.4% | 99.4% | 9 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking non_think

4000 instructions pooled; benign false blocks 97.8% under G-FEAS and 97.9% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 78.4% | 78.4% | 69 | 0 | 0.0% |
| V2 | 400 | 0.0% | 66.5% | 67.5% | 134 | 4 | 1.0% |
| **V3** | 440 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 440 | 0.0% | 97.7% | 97.7% | 10 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 4.0% | 7.5% | 384 | 14 | 3.5% |
| V6 | 400 | 0.0% | 85.8% | 85.8% | 57 | 0 | 0.0% |
| benign | 1600 | 0.0% | 97.8% | 97.9% | 36 | 2 | 0.1% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking think_high

4000 instructions pooled; benign false blocks 99.5% under G-FEAS and 99.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 76.9% | 76.9% | 74 | 0 | 0.0% |
| V2 | 400 | 0.0% | 63.7% | 64.8% | 145 | 4 | 1.0% |
| **V3** | 440 | 0.0% | 99.5% | 99.5% | 2 | 0 | **0.0%** |
| **V4** | 440 | 0.0% | 99.1% | 99.1% | 4 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 26.0% | 28.7% | 296 | 11 | 2.8% |
| V6 | 400 | 0.0% | 88.5% | 88.5% | 46 | 0 | 0.0% |
| benign | 1600 | 0.0% | 99.5% | 99.5% | 8 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_constrained / json_schema / thinking disabled

4000 instructions pooled; benign false blocks 1.2% under G-FEAS and 3.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 55.9% | 56.2% | 141 | 1 | 0.3% |
| V2 | 400 | 0.0% | 39.2% | 41.2% | 243 | 8 | 2.0% |
| **V3** | 440 | 0.0% | 0.5% | 86.4% | 438 | 378 | **85.9%** |
| **V4** | 440 | 0.0% | 0.0% | 2.7% | 440 | 12 | **2.7%** |
| V5 | 400 | 0.0% | 0.0% | 3.5% | 400 | 14 | 3.5% |
| V6 | 400 | 0.0% | 0.2% | 3.2% | 399 | 12 | 3.0% |
| benign | 1600 | 0.0% | 1.2% | 3.8% | 1581 | 42 | 2.6% |

### Claude Sonnet 5 (closed) - M_free / none / thinking disabled

4000 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 83.8% | 83.8% | 52 | 0 | 0.0% |
| V2 | 400 | 0.0% | 78.2% | 78.8% | 87 | 2 | 0.5% |
| **V3** | 440 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 440 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 18.5% | 22.0% | 326 | 14 | 3.5% |
| V6 | 400 | 0.0% | 92.0% | 92.0% | 32 | 0 | 0.0% |
| benign | 1600 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking default

4000 instructions pooled; benign false blocks 1.3% under G-FEAS and 3.9% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 22.5% | 23.4% | 248 | 3 | 0.9% |
| V2 | 400 | 0.0% | 5.2% | 8.2% | 379 | 12 | 3.0% |
| **V3** | 440 | 0.0% | 0.0% | 90.5% | 440 | 398 | **90.5%** |
| **V4** | 440 | 0.0% | 0.0% | 2.7% | 440 | 12 | **2.7%** |
| V5 | 400 | 0.0% | 0.0% | 3.5% | 400 | 14 | 3.5% |
| V6 | 400 | 0.0% | 0.0% | 3.0% | 398 | 12 | 3.0% |
| benign | 1600 | 0.0% | 1.3% | 3.9% | 1579 | 42 | 2.6% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking disabled

4000 instructions pooled; benign false blocks 2.4% under G-FEAS and 5.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 44.1% | 45.0% | 179 | 3 | 0.9% |
| V2 | 400 | 0.0% | 20.2% | 23.0% | 319 | 11 | 2.8% |
| **V3** | 440 | 0.0% | 0.0% | 90.0% | 440 | 396 | **90.0%** |
| **V4** | 440 | 0.0% | 0.0% | 2.7% | 440 | 12 | **2.7%** |
| V5 | 400 | 0.0% | 0.0% | 3.5% | 400 | 14 | 3.5% |
| V6 | 400 | 0.0% | 0.0% | 3.0% | 398 | 12 | 3.0% |
| benign | 1600 | 0.0% | 2.4% | 5.0% | 1562 | 42 | 2.6% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking default

4000 instructions pooled; benign false blocks 28.1% under G-FEAS and 28.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 10.0% | 10.0% | 38 | 0 | 0.0% |
| V2 | 400 | 0.0% | 6.2% | 6.2% | 16 | 0 | 0.0% |
| **V3** | 440 | 0.0% | 24.8% | 25.0% | 1 | 1 | **0.2%** |
| **V4** | 440 | 0.0% | 23.6% | 23.6% | 6 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 1.8% | 154 | 7 | 1.8% |
| V6 | 400 | 0.0% | 3.2% | 3.5% | 25 | 1 | 0.2% |
| benign | 1600 | 0.0% | 28.1% | 28.1% | 19 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking disabled

4000 instructions pooled; benign false blocks 22.9% under G-FEAS and 23.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 11.9% | 11.9% | 19 | 0 | 0.0% |
| V2 | 400 | 0.0% | 7.8% | 8.2% | 28 | 2 | 0.5% |
| **V3** | 440 | 0.0% | 22.5% | 24.1% | 7 | 7 | **1.6%** |
| **V4** | 440 | 0.0% | 17.0% | 17.0% | 28 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 0.0% | 76 | 0 | 0.0% |
| V6 | 400 | 0.0% | 1.0% | 1.2% | 27 | 1 | 0.2% |
| benign | 1600 | 0.0% | 22.9% | 23.1% | 81 | 2 | 0.1% |

### GPT-5.6 Sol (closed, flagship spot-check) - M_constrained / json_schema / thinking none

2000 instructions pooled; benign false blocks 6.0% under G-FEAS and 8.6% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 30.0% | 31.2% | 112 | 2 | 1.2% |
| V2 | 200 | 0.0% | 23.5% | 26.0% | 153 | 5 | 2.5% |
| **V3** | 220 | 0.0% | 5.9% | 88.2% | 207 | 181 | **82.3%** |
| **V4** | 220 | 0.0% | 4.1% | 7.7% | 211 | 8 | **3.6%** |
| V5 | 200 | 0.0% | 0.0% | 3.5% | 200 | 7 | 3.5% |
| V6 | 200 | 0.0% | 0.0% | 3.0% | 200 | 6 | 3.0% |
| benign | 800 | 0.0% | 6.0% | 8.6% | 752 | 21 | 2.6% |

