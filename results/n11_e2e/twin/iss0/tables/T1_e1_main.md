# T1

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

Block rate is measured on the labelled violations of each class; the false-block rate is the same guard's block rate on the 800 matched benign twins, and the two are always read as a pair. Rows are pooled over repeats. `sep` is the V3/V4 evidence for claim C2: the proposal passed the feasibility guard and only the certificate refused it.

### Qwen3-14B (open, local, BF16) - M_constrained / xgrammar

5169 instructions pooled; benign false blocks 0.3% under G-FEAS and 5.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 64.6% | 66.7% | 170 | 10 | 2.1% |
| V2 | 555 | 0.0% | 59.5% | 63.1% | 225 | 20 | 3.6% |
| **V3** | 462 | 0.0% | 0.6% | 81.2% | 459 | 372 | **80.5%** |
| **V4** | 603 | 0.0% | 0.5% | 6.0% | 600 | 33 | **5.5%** |
| V5 | 600 | 0.0% | 3.0% | 7.0% | 582 | 24 | 4.0% |
| V6 | 600 | 0.0% | 7.0% | 12.0% | 558 | 30 | 5.0% |
| benign | 1869 | 0.0% | 0.3% | 5.0% | 1863 | 87 | 4.7% |

### Qwen3-14B (open, local, BF16) - M_free / none

5169 instructions pooled; benign false blocks 99.1% under G-FEAS and 99.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 91.0% | 91.7% | 43 | 3 | 0.6% |
| V2 | 555 | 0.0% | 95.1% | 95.7% | 27 | 3 | 0.5% |
| **V3** | 462 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 603 | 0.0% | 99.5% | 99.5% | 3 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 46.0% | 49.0% | 324 | 18 | 3.0% |
| V6 | 600 | 0.0% | 92.5% | 92.5% | 45 | 0 | 0.0% |
| benign | 1869 | 0.0% | 99.1% | 99.1% | 17 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_constrained / xgrammar

5169 instructions pooled; benign false blocks 3.7% under G-FEAS and 6.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 68.8% | 69.4% | 150 | 3 | 0.6% |
| V2 | 555 | 0.0% | 63.2% | 64.9% | 204 | 9 | 1.6% |
| **V3** | 462 | 0.0% | 0.6% | 86.4% | 459 | 396 | **85.7%** |
| **V4** | 603 | 0.0% | 0.0% | 3.0% | 603 | 18 | **3.0%** |
| V5 | 600 | 0.0% | 0.5% | 4.0% | 597 | 21 | 3.5% |
| V6 | 600 | 0.0% | 2.0% | 5.0% | 588 | 18 | 3.0% |
| benign | 1869 | 0.0% | 3.7% | 6.4% | 1800 | 51 | 2.7% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_free / none

5169 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 81.2% | 81.9% | 90 | 3 | 0.6% |
| V2 | 555 | 0.0% | 84.9% | 85.4% | 84 | 3 | 0.5% |
| **V3** | 462 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 603 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 35.0% | 37.5% | 390 | 15 | 2.5% |
| V6 | 600 | 0.0% | 90.5% | 90.5% | 57 | 0 | 0.0% |
| benign | 1869 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_constrained / xgrammar

1723 instructions pooled; benign false blocks 6.1% under G-FEAS and 8.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 70.0% | 71.2% | 48 | 2 | 1.2% |
| V2 | 185 | 0.0% | 73.5% | 74.6% | 49 | 2 | 1.1% |
| **V3** | 154 | 0.0% | 3.2% | 74.0% | 149 | 109 | **70.8%** |
| **V4** | 201 | 0.0% | 1.5% | 4.5% | 198 | 6 | **3.0%** |
| V5 | 200 | 0.0% | 16.0% | 19.5% | 168 | 7 | 3.5% |
| V6 | 200 | 0.0% | 9.0% | 14.0% | 182 | 10 | 5.0% |
| benign | 623 | 0.0% | 6.1% | 8.8% | 585 | 17 | 2.7% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_free / none

1723 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V2 | 185 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| **V3** | 154 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 201 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 200 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V6 | 200 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 623 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GPT-5.4-mini (closed, budget tier) - M_constrained / json_schema

3446 instructions pooled; benign false blocks 1.6% under G-FEAS and 4.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 71.6% | 71.9% | 91 | 1 | 0.3% |
| V2 | 370 | 0.0% | 61.1% | 63.0% | 144 | 7 | 1.9% |
| **V3** | 308 | 0.0% | 0.6% | 79.9% | 306 | 244 | **79.2%** |
| **V4** | 402 | 0.0% | 0.2% | 3.2% | 401 | 12 | **3.0%** |
| V5 | 400 | 0.0% | 13.8% | 17.8% | 345 | 16 | 4.0% |
| V6 | 400 | 0.0% | 1.5% | 4.8% | 394 | 13 | 3.2% |
| benign | 1246 | 0.0% | 1.6% | 4.3% | 1226 | 34 | 2.7% |

### GPT-5.4-mini (closed, budget tier) - M_free / none

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 98.1% | 98.1% | 6 | 0 | 0.0% |
| V2 | 370 | 0.0% | 93.8% | 94.6% | 23 | 3 | 0.8% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.5% | 99.5% | 2 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 70.5% | 72.5% | 118 | 8 | 2.0% |
| V6 | 400 | 0.0% | 91.2% | 91.2% | 35 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking non_think

3446 instructions pooled; benign false blocks 96.3% under G-FEAS and 96.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 74.4% | 74.4% | 82 | 0 | 0.0% |
| V2 | 370 | 0.0% | 65.4% | 67.0% | 128 | 6 | 1.6% |
| **V3** | 308 | 0.0% | 99.0% | 99.4% | 3 | 1 | **0.3%** |
| **V4** | 402 | 0.0% | 95.3% | 95.3% | 19 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 3.0% | 6.5% | 388 | 14 | 3.5% |
| V6 | 400 | 0.0% | 84.5% | 84.5% | 62 | 0 | 0.0% |
| benign | 1246 | 0.0% | 96.3% | 96.5% | 46 | 2 | 0.2% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking think_high

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 77.8% | 77.8% | 71 | 0 | 0.0% |
| V2 | 370 | 0.0% | 68.9% | 70.0% | 115 | 4 | 1.1% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.8% | 99.8% | 1 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 19.5% | 22.8% | 322 | 13 | 3.2% |
| V6 | 400 | 0.0% | 91.2% | 91.2% | 35 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking non_think

3446 instructions pooled; benign false blocks 97.1% under G-FEAS and 97.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 78.4% | 78.4% | 69 | 0 | 0.0% |
| V2 | 370 | 0.0% | 71.4% | 72.4% | 106 | 4 | 1.1% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 98.0% | 98.0% | 8 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 4.0% | 7.5% | 384 | 14 | 3.5% |
| V6 | 400 | 0.0% | 85.8% | 85.8% | 57 | 0 | 0.0% |
| benign | 1246 | 0.0% | 97.1% | 97.3% | 36 | 2 | 0.2% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking think_high

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 76.9% | 76.9% | 74 | 0 | 0.0% |
| V2 | 370 | 0.0% | 67.6% | 68.6% | 120 | 4 | 1.1% |
| **V3** | 308 | 0.0% | 99.7% | 99.7% | 1 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.0% | 99.0% | 4 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 26.0% | 28.7% | 296 | 11 | 2.8% |
| V6 | 400 | 0.0% | 88.5% | 88.5% | 46 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 7 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_constrained / json_schema / thinking disabled

3446 instructions pooled; benign false blocks 1.5% under G-FEAS and 4.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 55.9% | 56.2% | 141 | 1 | 0.3% |
| V2 | 370 | 0.0% | 42.4% | 44.6% | 213 | 8 | 2.2% |
| **V3** | 308 | 0.0% | 0.6% | 83.8% | 306 | 256 | **83.1%** |
| **V4** | 402 | 0.0% | 0.0% | 3.0% | 402 | 12 | **3.0%** |
| V5 | 400 | 0.0% | 0.0% | 3.5% | 400 | 14 | 3.5% |
| V6 | 400 | 0.0% | 0.2% | 3.2% | 399 | 12 | 3.0% |
| benign | 1246 | 0.0% | 1.5% | 4.3% | 1227 | 34 | 2.7% |

### Claude Sonnet 5 (closed) - M_free / none / thinking disabled

3446 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 83.8% | 83.8% | 52 | 0 | 0.0% |
| V2 | 370 | 0.0% | 81.6% | 82.2% | 68 | 2 | 0.5% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 18.5% | 22.0% | 326 | 14 | 3.5% |
| V6 | 400 | 0.0% | 92.0% | 92.0% | 32 | 0 | 0.0% |
| benign | 1246 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking default

3446 instructions pooled; benign false blocks 1.7% under G-FEAS and 4.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 22.5% | 23.4% | 248 | 3 | 0.9% |
| V2 | 370 | 0.0% | 5.7% | 8.9% | 349 | 12 | 3.2% |
| **V3** | 308 | 0.0% | 0.0% | 89.6% | 308 | 276 | **89.6%** |
| **V4** | 402 | 0.0% | 0.0% | 3.0% | 402 | 12 | **3.0%** |
| V5 | 400 | 0.0% | 0.0% | 3.5% | 400 | 14 | 3.5% |
| V6 | 400 | 0.0% | 0.0% | 3.0% | 398 | 12 | 3.0% |
| benign | 1246 | 0.0% | 1.7% | 4.4% | 1225 | 34 | 2.7% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking disabled

3446 instructions pooled; benign false blocks 3.0% under G-FEAS and 5.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 44.1% | 45.0% | 179 | 3 | 0.9% |
| V2 | 370 | 0.0% | 21.9% | 24.9% | 289 | 11 | 3.0% |
| **V3** | 308 | 0.0% | 0.0% | 89.0% | 308 | 274 | **89.0%** |
| **V4** | 402 | 0.0% | 0.0% | 3.0% | 402 | 12 | **3.0%** |
| V5 | 400 | 0.0% | 0.0% | 3.5% | 400 | 14 | 3.5% |
| V6 | 400 | 0.0% | 0.0% | 3.0% | 398 | 12 | 3.0% |
| benign | 1246 | 0.0% | 3.0% | 5.8% | 1208 | 34 | 2.7% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking default

3446 instructions pooled; benign false blocks 26.7% under G-FEAS and 26.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 10.0% | 10.0% | 38 | 0 | 0.0% |
| V2 | 370 | 0.0% | 6.8% | 6.8% | 16 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 25.3% | 25.6% | 1 | 1 | **0.3%** |
| **V4** | 402 | 0.0% | 23.1% | 23.1% | 5 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 1.8% | 154 | 7 | 1.8% |
| V6 | 400 | 0.0% | 3.2% | 3.5% | 25 | 1 | 0.2% |
| benign | 1246 | 0.0% | 26.7% | 26.7% | 19 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking disabled

3446 instructions pooled; benign false blocks 21.3% under G-FEAS and 21.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 11.9% | 11.9% | 19 | 0 | 0.0% |
| V2 | 370 | 0.0% | 8.4% | 8.9% | 28 | 2 | 0.5% |
| **V3** | 308 | 0.0% | 23.1% | 24.7% | 5 | 5 | **1.6%** |
| **V4** | 402 | 0.0% | 16.7% | 16.7% | 23 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 0.0% | 76 | 0 | 0.0% |
| V6 | 400 | 0.0% | 1.0% | 1.2% | 27 | 1 | 0.2% |
| benign | 1246 | 0.0% | 21.3% | 21.4% | 76 | 2 | 0.2% |

### GPT-5.6 Sol (closed, flagship spot-check) - M_constrained / json_schema / thinking none

1723 instructions pooled; benign false blocks 7.1% under G-FEAS and 9.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 30.0% | 31.2% | 112 | 2 | 1.2% |
| V2 | 185 | 0.0% | 25.4% | 28.1% | 138 | 5 | 2.7% |
| **V3** | 154 | 0.0% | 3.2% | 87.0% | 149 | 129 | **83.8%** |
| **V4** | 201 | 0.0% | 2.5% | 6.5% | 196 | 8 | **4.0%** |
| V5 | 200 | 0.0% | 0.0% | 3.5% | 200 | 7 | 3.5% |
| V6 | 200 | 0.0% | 0.0% | 3.0% | 200 | 6 | 3.0% |
| benign | 623 | 0.0% | 7.1% | 9.8% | 579 | 17 | 2.7% |

