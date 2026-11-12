# T1

<!-- N11 Stage 3, late reading t_d' = t_start -->

Block rate is measured on the labelled violations of each class; the false-block rate is the same guard's block rate on the 800 matched benign twins, and the two are always read as a pair. Rows are pooled over repeats. `sep` is the V3/V4 evidence for claim C2: the proposal passed the feasibility guard and only the certificate refused it.

### Qwen3-14B (open, local, BF16) - M_constrained / xgrammar

5169 instructions pooled; benign false blocks 3.9% under G-FEAS and 3.9% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 66.0% | 66.0% | 163 | 0 | 0.0% |
| V2 | 555 | 0.0% | 66.3% | 66.3% | 187 | 0 | 0.0% |
| **V3** | 462 | 0.0% | 0.6% | 81.2% | 459 | 372 | **80.5%** |
| **V4** | 603 | 0.0% | 6.1% | 6.1% | 566 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 31.2% | 31.2% | 413 | 0 | 0.0% |
| V6 | 600 | 0.0% | 40.8% | 40.8% | 355 | 0 | 0.0% |
| benign | 1869 | 0.0% | 3.9% | 3.9% | 1797 | 0 | 0.0% |

### Qwen3-14B (open, local, BF16) - M_free / none

5169 instructions pooled; benign false blocks 99.1% under G-FEAS and 99.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 91.0% | 91.0% | 43 | 0 | 0.0% |
| V2 | 555 | 0.0% | 95.1% | 95.1% | 27 | 0 | 0.0% |
| **V3** | 462 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 603 | 0.0% | 99.5% | 99.5% | 3 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 46.0% | 46.0% | 324 | 0 | 0.0% |
| V6 | 600 | 0.0% | 98.5% | 98.5% | 9 | 0 | 0.0% |
| benign | 1869 | 0.0% | 99.1% | 99.1% | 17 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_constrained / xgrammar

5169 instructions pooled; benign false blocks 3.7% under G-FEAS and 3.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 68.8% | 68.8% | 150 | 0 | 0.0% |
| V2 | 555 | 0.0% | 63.2% | 63.2% | 204 | 0 | 0.0% |
| **V3** | 462 | 0.0% | 0.6% | 87.0% | 459 | 399 | **86.4%** |
| **V4** | 603 | 0.0% | 1.2% | 1.2% | 596 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 18.5% | 18.5% | 489 | 0 | 0.0% |
| V6 | 600 | 0.0% | 33.2% | 33.2% | 401 | 0 | 0.0% |
| benign | 1869 | 0.0% | 3.7% | 3.7% | 1799 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_free / none

5169 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 480 | 0.0% | 81.2% | 81.2% | 90 | 0 | 0.0% |
| V2 | 555 | 0.0% | 84.9% | 84.9% | 84 | 0 | 0.0% |
| **V3** | 462 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 603 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 600 | 0.0% | 35.0% | 35.0% | 390 | 0 | 0.0% |
| V6 | 600 | 0.0% | 96.0% | 96.0% | 24 | 0 | 0.0% |
| benign | 1869 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_constrained / xgrammar

1723 instructions pooled; benign false blocks 6.7% under G-FEAS and 6.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 71.9% | 71.9% | 45 | 0 | 0.0% |
| V2 | 185 | 0.0% | 74.1% | 74.1% | 48 | 0 | 0.0% |
| **V3** | 154 | 0.0% | 3.2% | 73.4% | 149 | 108 | **70.1%** |
| **V4** | 201 | 0.0% | 2.5% | 2.5% | 196 | 0 | **0.0%** |
| V5 | 200 | 0.0% | 54.0% | 54.0% | 92 | 0 | 0.0% |
| V6 | 200 | 0.0% | 45.5% | 45.5% | 109 | 0 | 0.0% |
| benign | 623 | 0.0% | 6.7% | 6.7% | 581 | 0 | 0.0% |

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

3446 instructions pooled; benign false blocks 2.1% under G-FEAS and 2.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 71.6% | 71.6% | 91 | 0 | 0.0% |
| V2 | 370 | 0.0% | 61.1% | 61.1% | 144 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 0.6% | 79.9% | 306 | 244 | **79.2%** |
| **V4** | 402 | 0.0% | 0.2% | 0.2% | 401 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 59.8% | 59.8% | 161 | 0 | 0.0% |
| V6 | 400 | 0.0% | 32.0% | 32.0% | 272 | 0 | 0.0% |
| benign | 1246 | 0.0% | 2.1% | 2.1% | 1220 | 0 | 0.0% |

### GPT-5.4-mini (closed, budget tier) - M_free / none

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 98.1% | 98.1% | 6 | 0 | 0.0% |
| V2 | 370 | 0.0% | 93.8% | 93.8% | 23 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.5% | 99.5% | 2 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 70.5% | 70.5% | 118 | 0 | 0.0% |
| V6 | 400 | 0.0% | 92.5% | 92.5% | 30 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking non_think

3446 instructions pooled; benign false blocks 96.3% under G-FEAS and 96.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 74.4% | 74.4% | 82 | 0 | 0.0% |
| V2 | 370 | 0.0% | 65.4% | 65.4% | 128 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 99.0% | 99.0% | 3 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 95.3% | 95.3% | 19 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 3.0% | 3.0% | 388 | 0 | 0.0% |
| V6 | 400 | 0.0% | 84.5% | 84.5% | 62 | 0 | 0.0% |
| benign | 1246 | 0.0% | 96.3% | 96.3% | 46 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking think_high

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 77.8% | 77.8% | 71 | 0 | 0.0% |
| V2 | 370 | 0.0% | 68.9% | 68.9% | 115 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.8% | 99.8% | 1 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 19.5% | 19.5% | 322 | 0 | 0.0% |
| V6 | 400 | 0.0% | 94.2% | 94.2% | 23 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 8 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking non_think

3446 instructions pooled; benign false blocks 97.1% under G-FEAS and 97.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 78.4% | 78.4% | 69 | 0 | 0.0% |
| V2 | 370 | 0.0% | 71.4% | 71.4% | 106 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 98.0% | 98.0% | 8 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 4.0% | 4.0% | 384 | 0 | 0.0% |
| V6 | 400 | 0.0% | 87.8% | 87.8% | 49 | 0 | 0.0% |
| benign | 1246 | 0.0% | 97.1% | 97.1% | 36 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking think_high

3446 instructions pooled; benign false blocks 99.4% under G-FEAS and 99.4% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 76.9% | 76.9% | 74 | 0 | 0.0% |
| V2 | 370 | 0.0% | 67.6% | 67.6% | 120 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 99.7% | 99.7% | 1 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 99.0% | 99.0% | 4 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 26.0% | 26.0% | 296 | 0 | 0.0% |
| V6 | 400 | 0.0% | 90.8% | 90.8% | 37 | 0 | 0.0% |
| benign | 1246 | 0.0% | 99.4% | 99.4% | 7 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_constrained / json_schema / thinking disabled

3446 instructions pooled; benign false blocks 1.6% under G-FEAS and 1.6% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 55.9% | 55.9% | 141 | 0 | 0.0% |
| V2 | 370 | 0.0% | 42.4% | 42.4% | 213 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 0.6% | 84.4% | 306 | 258 | **83.8%** |
| **V4** | 402 | 0.0% | 1.2% | 1.2% | 397 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 8.0% | 8.0% | 368 | 0 | 0.0% |
| V6 | 400 | 0.0% | 11.0% | 11.0% | 356 | 0 | 0.0% |
| benign | 1246 | 0.0% | 1.6% | 1.6% | 1226 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_free / none / thinking disabled

3446 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 83.8% | 83.8% | 52 | 0 | 0.0% |
| V2 | 370 | 0.0% | 81.6% | 81.6% | 68 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 402 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 18.5% | 18.5% | 326 | 0 | 0.0% |
| V6 | 400 | 0.0% | 94.8% | 94.8% | 21 | 0 | 0.0% |
| benign | 1246 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking default

3446 instructions pooled; benign false blocks 1.7% under G-FEAS and 1.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 22.5% | 22.5% | 248 | 0 | 0.0% |
| V2 | 370 | 0.0% | 5.7% | 5.7% | 349 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 0.0% | 90.3% | 308 | 278 | **90.3%** |
| **V4** | 402 | 0.0% | 0.0% | 0.0% | 402 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.5% | 0.5% | 398 | 0 | 0.0% |
| V6 | 400 | 0.0% | 6.0% | 6.0% | 374 | 0 | 0.0% |
| benign | 1246 | 0.0% | 1.7% | 1.7% | 1225 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking disabled

3446 instructions pooled; benign false blocks 3.0% under G-FEAS and 3.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 44.1% | 44.1% | 179 | 0 | 0.0% |
| V2 | 370 | 0.0% | 21.9% | 21.9% | 289 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 0.0% | 89.6% | 308 | 276 | **89.6%** |
| **V4** | 402 | 0.0% | 0.2% | 0.2% | 401 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 1.2% | 1.2% | 395 | 0 | 0.0% |
| V6 | 400 | 0.0% | 7.2% | 7.2% | 369 | 0 | 0.0% |
| benign | 1246 | 0.0% | 3.0% | 3.0% | 1208 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking default

3446 instructions pooled; benign false blocks 26.7% under G-FEAS and 26.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 10.0% | 10.0% | 38 | 0 | 0.0% |
| V2 | 370 | 0.0% | 6.8% | 6.8% | 16 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 25.3% | 25.6% | 1 | 1 | **0.3%** |
| **V4** | 402 | 0.0% | 23.1% | 23.1% | 5 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 0.0% | 154 | 0 | 0.0% |
| V6 | 400 | 0.0% | 3.8% | 3.8% | 23 | 0 | 0.0% |
| benign | 1246 | 0.0% | 26.7% | 26.7% | 19 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking disabled

3446 instructions pooled; benign false blocks 21.3% under G-FEAS and 21.3% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 320 | 0.0% | 11.9% | 11.9% | 19 | 0 | 0.0% |
| V2 | 370 | 0.0% | 8.4% | 8.4% | 28 | 0 | 0.0% |
| **V3** | 308 | 0.0% | 23.1% | 24.7% | 5 | 5 | **1.6%** |
| **V4** | 402 | 0.0% | 16.7% | 16.7% | 23 | 0 | **0.0%** |
| V5 | 400 | 0.0% | 0.0% | 0.0% | 76 | 0 | 0.0% |
| V6 | 400 | 0.0% | 2.0% | 2.0% | 23 | 0 | 0.0% |
| benign | 1246 | 0.0% | 21.3% | 21.3% | 76 | 0 | 0.0% |

### GPT-5.6 Sol (closed, flagship spot-check) - M_constrained / json_schema / thinking none

1723 instructions pooled; benign false blocks 7.5% under G-FEAS and 7.5% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 160 | 0.0% | 37.5% | 37.5% | 100 | 0 | 0.0% |
| V2 | 185 | 0.0% | 25.4% | 25.4% | 138 | 0 | 0.0% |
| **V3** | 154 | 0.0% | 3.2% | 87.7% | 149 | 130 | **84.4%** |
| **V4** | 201 | 0.0% | 4.5% | 5.0% | 192 | 1 | **0.5%** |
| V5 | 200 | 0.0% | 0.5% | 0.5% | 199 | 0 | 0.0% |
| V6 | 200 | 0.0% | 12.0% | 12.0% | 176 | 0 | 0.0% |
| benign | 623 | 0.0% | 7.5% | 7.5% | 576 | 0 | 0.0% |

