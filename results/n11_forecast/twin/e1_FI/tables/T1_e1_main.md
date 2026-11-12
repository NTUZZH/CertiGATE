# T1

<!-- N11 Stage 3 forecast twin (l1-n11-forecast-1) -->
<!-- reading FI -->

Block rate is measured on the labelled violations of each class; the false-block rate is the same guard's block rate on the 800 matched benign twins, and the two are always read as a pair. Rows are pooled over repeats. `sep` is the V3/V4 evidence for claim C2: the proposal passed the feasibility guard and only the certificate refused it.

### Qwen3-14B (open, local, BF16) - M_constrained / xgrammar

5169 instructions pooled; benign false blocks 3.7% under G-FEAS and 5.6% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 66.0% | 67.3% | 163 | 6 | 1.2% |
| V2 | 555 | 0.0% | 66.3% | 67.4% | 187 | 6 | 1.1% |
| **V3** | 462 | 0.0% | 0.6% | 80.5% | 459 | 369 | **79.9%** |
| **V4** | 603 | 0.0% | 5.6% | 7.1% | 569 | 9 | **1.5%** |
| V5 | 600 | 0.0% | 31.2% | 34.2% | 413 | 18 | 3.0% |
| V6 | 600 | 0.0% | 32.3% | 34.3% | 406 | 12 | 2.0% |
| benign | 1869 | 0.0% | 3.7% | 5.6% | 1800 | 36 | 1.9% |

### Qwen3-14B (open, local, BF16) - M_free / none

5169 instructions pooled; benign false blocks 99.1% under G-FEAS and 99.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 91.0% | 91.7% | 43 | 3 | 0.6% |
| V2 | 555 | 0.0% | 95.1% | 95.1% | 27 | 0 | 0.0% |
| **V3** | 462 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 603 | 0.0% | 99.5% | 99.5% | 3 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 46.0% | 49.0% | 324 | 18 | 3.0% |
| V6 | 600 | 0.0% | 98.5% | 98.5% | 9 | 0 | 0.0% |
| benign | 1869 | 0.0% | 99.1% | 99.1% | 17 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_constrained / xgrammar

5169 instructions pooled; benign false blocks 3.7% under G-FEAS and 5.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 68.8% | 69.4% | 150 | 3 | 0.6% |
| V2 | 555 | 0.0% | 63.2% | 64.3% | 204 | 6 | 1.1% |
| **V3** | 462 | 0.0% | 0.6% | 86.4% | 459 | 396 | **85.7%** |
| **V4** | 603 | 0.0% | 0.5% | 2.0% | 600 | 9 | **1.5%** |
| V5 | 600 | 0.0% | 18.5% | 22.0% | 489 | 21 | 3.5% |
| V6 | 600 | 0.0% | 21.5% | 23.0% | 471 | 9 | 1.5% |
| benign | 1869 | 0.0% | 3.7% | 5.5% | 1800 | 33 | 1.8% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_free / none

5169 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 81.2% | 81.9% | 90 | 3 | 0.6% |
| V2 | 555 | 0.0% | 84.9% | 84.9% | 84 | 0 | 0.0% |
| **V3** | 462 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 603 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 35.0% | 37.5% | 390 | 15 | 2.5% |
| V6 | 600 | 0.0% | 96.0% | 96.0% | 24 | 0 | 0.0% |
| benign | 1869 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_constrained / xgrammar

1723 instructions pooled; benign false blocks 6.7% under G-FEAS and 8.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 71.2% | 71.9% | 46 | 1 | 0.6% |
| V2 | 185 | 0.0% | 74.1% | 75.1% | 48 | 2 | 1.1% |
| **V3** | 154 | 0.0% | 3.2% | 72.7% | 149 | 107 | **69.5%** |
| **V4** | 201 | 0.0% | 2.0% | 3.5% | 197 | 3 | **1.5%** |
| V5 | 200 | 0.0% | 54.0% | 56.0% | 92 | 4 | 2.0% |
| V6 | 200 | 0.0% | 33.5% | 35.0% | 133 | 3 | 1.5% |
| benign | 623 | 0.0% | 6.7% | 8.3% | 581 | 10 | 1.6% |

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

3446 instructions pooled; benign false blocks 1.6% under G-FEAS and 3.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 71.6% | 71.9% | 91 | 1 | 0.3% |
| V2 | 370 | 0.0% | 61.1% | 62.7% | 144 | 6 | 1.6% |
| **V3** | 308 | 0.0% | 0.6% | 79.2% | 306 | 242 | **78.6%** |
| **V4** | 402 | 0.0% | 0.2% | 1.7% | 401 | 6 | **1.5%** |
| V5 | 400 | 0.0% | 59.8% | 61.5% | 161 | 7 | 1.8% |
| V6 | 400 | 0.0% | 20.2% | 21.8% | 319 | 6 | 1.5% |
| benign | 1246 | 0.0% | 1.6% | 3.4% | 1226 | 22 | 1.8% |

### GPT-5.4-mini (closed, budget tier) - M_free / none

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 98.1% | 98.1% | 6 | 0 | 0.0% |
| V2 | 370 | 0.0% | 93.8% | 94.1% | 23 | 1 | 0.3% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.5% | 99.5% | 2 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 70.5% | 72.5% | 118 | 8 | 2.0% |
| V6 | 400 | 0.0% | 92.5% | 92.5% | 30 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking non_think

3446 instructions pooled; benign false blocks 96.3% under G-FEAS and 96.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 74.4% | 74.4% | 82 | 0 | 0.0% |
| V2 | 370 | 0.0% | 65.4% | 66.5% | 128 | 4 | 1.1% |
| **V3** | 308 | 0.0% | 99.0% | 99.0% | 3 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 95.3% | 95.3% | 19 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 3.0% | 6.5% | 388 | 14 | 3.5% |
| V6 | 400 | 0.0% | 84.5% | 84.5% | 62 | 0 | 0.0% |
| benign | 1246 | 0.0% | 96.3% | 96.5% | 46 | 2 | 0.2% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking think_high

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 77.8% | 77.8% | 71 | 0 | 0.0% |
| V2 | 370 | 0.0% | 68.9% | 69.5% | 115 | 2 | 0.5% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.8% | 99.8% | 1 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 19.5% | 22.8% | 322 | 13 | 3.2% |
| V6 | 400 | 0.0% | 94.2% | 94.2% | 23 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking non_think

3446 instructions pooled; benign false blocks 97.1% under G-FEAS and 97.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 78.4% | 78.4% | 69 | 0 | 0.0% |
| V2 | 370 | 0.0% | 71.4% | 71.9% | 106 | 2 | 0.5% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 98.0% | 98.0% | 8 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 4.0% | 7.5% | 384 | 14 | 3.5% |
| V6 | 400 | 0.0% | 87.8% | 87.8% | 49 | 0 | 0.0% |
| benign | 1246 | 0.0% | 97.1% | 97.3% | 36 | 2 | 0.2% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking think_high

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 76.9% | 76.9% | 74 | 0 | 0.0% |
| V2 | 370 | 0.0% | 67.6% | 68.1% | 120 | 2 | 0.5% |
| **V3** | 308 | 0.0% | 99.7% | 99.7% | 1 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.0% | 99.0% | 4 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 26.0% | 28.7% | 296 | 11 | 2.8% |
| V6 | 400 | 0.0% | 90.8% | 90.8% | 37 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 7 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_constrained / json_schema / thinking disabled

3446 instructions pooled; benign false blocks 1.5% under G-FEAS and 3.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 55.9% | 56.2% | 141 | 1 | 0.3% |
| V2 | 370 | 0.0% | 42.4% | 44.1% | 213 | 6 | 1.6% |
| **V3** | 308 | 0.0% | 0.6% | 83.8% | 306 | 256 | **83.1%** |
| **V4** | 402 | 0.0% | 0.0% | 1.5% | 402 | 6 | **1.5%** |
| V5 | 400 | 0.0% | 8.0% | 11.5% | 368 | 14 | 3.5% |
| V6 | 400 | 0.0% | 9.2% | 11.5% | 363 | 9 | 2.2% |
| benign | 1246 | 0.0% | 1.5% | 3.3% | 1227 | 22 | 1.8% |

### Claude Sonnet 5 (closed) - M_free / none / thinking disabled

3446 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 83.8% | 83.8% | 52 | 0 | 0.0% |
| V2 | 370 | 0.0% | 81.6% | 81.6% | 68 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 18.5% | 22.0% | 326 | 14 | 3.5% |
| V6 | 400 | 0.0% | 94.8% | 94.8% | 21 | 0 | 0.0% |
| benign | 1246 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking default

3446 instructions pooled; benign false blocks 1.7% under G-FEAS and 3.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 22.5% | 23.4% | 248 | 3 | 0.9% |
| V2 | 370 | 0.0% | 5.7% | 8.4% | 349 | 10 | 2.7% |
| **V3** | 308 | 0.0% | 0.0% | 89.6% | 308 | 276 | **89.6%** |
| **V4** | 402 | 0.0% | 0.0% | 1.5% | 402 | 6 | **1.5%** |
| V5 | 400 | 0.0% | 0.5% | 4.0% | 398 | 14 | 3.5% |
| V6 | 400 | 0.0% | 6.0% | 9.0% | 374 | 12 | 3.0% |
| benign | 1246 | 0.0% | 1.7% | 3.5% | 1225 | 22 | 1.8% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking disabled

3446 instructions pooled; benign false blocks 3.0% under G-FEAS and 4.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 44.1% | 45.0% | 179 | 3 | 0.9% |
| V2 | 370 | 0.0% | 21.9% | 24.3% | 289 | 9 | 2.4% |
| **V3** | 308 | 0.0% | 0.0% | 89.0% | 308 | 274 | **89.0%** |
| **V4** | 402 | 0.0% | 0.0% | 1.5% | 402 | 6 | **1.5%** |
| V5 | 400 | 0.0% | 1.2% | 4.8% | 395 | 14 | 3.5% |
| V6 | 400 | 0.0% | 7.0% | 9.0% | 370 | 8 | 2.0% |
| benign | 1246 | 0.0% | 3.0% | 4.8% | 1208 | 22 | 1.8% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking default

3446 instructions pooled; benign false blocks 26.7% under G-FEAS and 26.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 10.0% | 10.0% | 38 | 0 | 0.0% |
| V2 | 370 | 0.0% | 6.8% | 6.8% | 16 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 25.3% | 25.6% | 1 | 1 | **0.3%** |
| **V4** | 402 | 0.0% | 23.1% | 23.1% | 5 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 1.8% | 154 | 7 | 1.8% |
| V6 | 400 | 0.0% | 3.8% | 4.0% | 23 | 1 | 0.2% |
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
| V6 | 400 | 0.0% | 2.0% | 2.0% | 23 | 0 | 0.0% |
| benign | 1246 | 0.0% | 21.3% | 21.4% | 76 | 2 | 0.2% |

### GPT-5.6 Sol (closed, flagship spot-check) - M_constrained / json_schema / thinking none

1723 instructions pooled; benign false blocks 7.5% under G-FEAS and 9.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 37.5% | 38.1% | 100 | 1 | 0.6% |
| V2 | 185 | 0.0% | 25.4% | 27.6% | 138 | 4 | 2.2% |
| **V3** | 154 | 0.0% | 3.2% | 87.0% | 149 | 129 | **83.8%** |
| **V4** | 201 | 0.0% | 4.5% | 6.5% | 192 | 4 | **2.0%** |
| V5 | 200 | 0.0% | 0.5% | 4.0% | 199 | 7 | 3.5% |
| V6 | 200 | 0.0% | 9.0% | 11.0% | 182 | 4 | 2.0% |
| benign | 623 | 0.0% | 7.5% | 9.3% | 576 | 11 | 1.8% |

