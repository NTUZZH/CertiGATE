# T1

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: iss0 -->

Block rate is measured on the labelled violations of each class; the false-block rate is the same guard's block rate on the 800 matched benign twins, and the two are always read as a pair. Rows are pooled over repeats. `sep` is the V3/V4 evidence for claim C2: the proposal passed the feasibility guard and only the certificate refused it.

### Qwen3-14B (open, local, BF16) - M_constrained / xgrammar

216 instructions pooled; benign false blocks 0.0% under G-FEAS and 0.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 24 | 0.0% | 62.5% | 62.5% | 9 | 0 | 0.0% |
| V2 | 21 | 0.0% | 71.4% | 71.4% | 6 | 0 | 0.0% |
| **V3** | 18 | 0.0% | 0.0% | 83.3% | 18 | 15 | **83.3%** |
| **V4** | 24 | 0.0% | 0.0% | 0.0% | 24 | 0 | **0.0%** |
| V5 | 27 | 0.0% | 0.0% | 0.0% | 27 | 0 | 0.0% |
| V6 | 24 | 0.0% | 12.5% | 12.5% | 21 | 0 | 0.0% |
| benign | 78 | 0.0% | 0.0% | 0.0% | 78 | 0 | 0.0% |

### Qwen3-14B (open, local, BF16) - M_free / none

216 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 24 | 0.0% | 87.5% | 87.5% | 3 | 0 | 0.0% |
| V2 | 21 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| **V3** | 18 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 24 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 27 | 0.0% | 44.4% | 44.4% | 15 | 0 | 0.0% |
| V6 | 24 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 78 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_constrained / xgrammar

216 instructions pooled; benign false blocks 0.0% under G-FEAS and 0.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 24 | 0.0% | 62.5% | 62.5% | 9 | 0 | 0.0% |
| V2 | 21 | 0.0% | 57.1% | 57.1% | 9 | 0 | 0.0% |
| **V3** | 18 | 0.0% | 0.0% | 100.0% | 18 | 18 | **100.0%** |
| **V4** | 24 | 0.0% | 0.0% | 0.0% | 24 | 0 | **0.0%** |
| V5 | 27 | 0.0% | 0.0% | 0.0% | 27 | 0 | 0.0% |
| V6 | 24 | 0.0% | 0.0% | 0.0% | 24 | 0 | 0.0% |
| benign | 78 | 0.0% | 0.0% | 0.0% | 78 | 0 | 0.0% |

### Qwen3.6-27B-FP8 (open, local, quantized) - M_free / none

216 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 24 | 0.0% | 62.5% | 62.5% | 9 | 0 | 0.0% |
| V2 | 21 | 0.0% | 85.7% | 85.7% | 3 | 0 | 0.0% |
| **V3** | 18 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 24 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 27 | 0.0% | 33.3% | 33.3% | 18 | 0 | 0.0% |
| V6 | 24 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 78 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_constrained / xgrammar

72 instructions pooled; benign false blocks 7.7% under G-FEAS and 7.7% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 8 | 0.0% | 50.0% | 50.0% | 4 | 0 | 0.0% |
| V2 | 7 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| **V3** | 6 | 0.0% | 0.0% | 66.7% | 6 | 4 | **66.7%** |
| **V4** | 8 | 0.0% | 0.0% | 0.0% | 8 | 0 | **0.0%** |
| V5 | 9 | 0.0% | 11.1% | 11.1% | 8 | 0 | 0.0% |
| V6 | 8 | 0.0% | 0.0% | 0.0% | 8 | 0 | 0.0% |
| benign | 26 | 0.0% | 7.7% | 7.7% | 24 | 0 | 0.0% |

### GLM-4-9B (open, local, SPOT-CHECK) - M_free / none

72 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 8 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V2 | 7 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| **V3** | 6 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 8 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 9 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V6 | 8 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 26 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### GPT-5.4-mini (closed, budget tier) - M_constrained / json_schema

144 instructions pooled; benign false blocks 0.0% under G-FEAS and 0.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 62.5% | 62.5% | 6 | 0 | 0.0% |
| V2 | 14 | 0.0% | 71.4% | 71.4% | 4 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 0.0% | 83.3% | 12 | 10 | **83.3%** |
| **V4** | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 11.1% | 11.1% | 16 | 0 | 0.0% |
| V6 | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | 0.0% |
| benign | 52 | 0.0% | 0.0% | 0.0% | 52 | 0 | 0.0% |

### GPT-5.4-mini (closed, budget tier) - M_free / none

144 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| V2 | 14 | 0.0% | 92.9% | 92.9% | 1 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 93.8% | 93.8% | 1 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 50.0% | 50.0% | 9 | 0 | 0.0% |
| V6 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking non_think

144 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 75.0% | 75.0% | 4 | 0 | 0.0% |
| V2 | 14 | 0.0% | 78.6% | 78.6% | 3 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 87.5% | 87.5% | 2 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 11.1% | 11.1% | 16 | 0 | 0.0% |
| V6 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_constrained / json_object / thinking think_high

144 instructions pooled; benign false blocks 98.1% under G-FEAS and 98.1% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 75.0% | 75.0% | 4 | 0 | 0.0% |
| V2 | 14 | 0.0% | 57.1% | 57.1% | 6 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 22.2% | 22.2% | 14 | 0 | 0.0% |
| V6 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 98.1% | 98.1% | 1 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking non_think

144 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 75.0% | 75.0% | 4 | 0 | 0.0% |
| V2 | 14 | 0.0% | 71.4% | 71.4% | 4 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 93.8% | 93.8% | 1 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 11.1% | 11.1% | 16 | 0 | 0.0% |
| V6 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### DeepSeek V4-Pro (open weights, hosted) - M_free / none / thinking think_high

144 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 75.0% | 75.0% | 4 | 0 | 0.0% |
| V2 | 14 | 0.0% | 50.0% | 50.0% | 7 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 11.1% | 11.1% | 16 | 0 | 0.0% |
| V6 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_constrained / json_schema / thinking disabled

144 instructions pooled; benign false blocks 0.0% under G-FEAS and 0.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 56.2% | 56.2% | 7 | 0 | 0.0% |
| V2 | 14 | 0.0% | 28.6% | 28.6% | 10 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 0.0% | 100.0% | 12 | 12 | **100.0%** |
| **V4** | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 0.0% | 0.0% | 18 | 0 | 0.0% |
| V6 | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | 0.0% |
| benign | 52 | 0.0% | 0.0% | 0.0% | 52 | 0 | 0.0% |

### Claude Sonnet 5 (closed) - M_free / none / thinking disabled

144 instructions pooled; benign false blocks 100.0% under G-FEAS and 100.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 87.5% | 87.5% | 2 | 0 | 0.0% |
| V2 | 14 | 0.0% | 85.7% | 85.7% | 2 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 22.2% | 22.2% | 14 | 0 | 0.0% |
| V6 | 16 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 100.0% | 100.0% | 0 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking default

144 instructions pooled; benign false blocks 0.0% under G-FEAS and 0.0% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 25.0% | 25.0% | 12 | 0 | 0.0% |
| V2 | 14 | 0.0% | 14.3% | 14.3% | 12 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 0.0% | 100.0% | 12 | 12 | **100.0%** |
| **V4** | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 0.0% | 0.0% | 18 | 0 | 0.0% |
| V6 | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | 0.0% |
| benign | 52 | 0.0% | 0.0% | 0.0% | 52 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_constrained / json_schema / thinking disabled

144 instructions pooled; benign false blocks 3.8% under G-FEAS and 3.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 50.0% | 50.0% | 8 | 0 | 0.0% |
| V2 | 14 | 0.0% | 28.6% | 28.6% | 10 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 0.0% | 100.0% | 12 | 12 | **100.0%** |
| **V4** | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 0.0% | 0.0% | 18 | 0 | 0.0% |
| V6 | 16 | 0.0% | 0.0% | 0.0% | 16 | 0 | 0.0% |
| benign | 52 | 0.0% | 3.8% | 3.8% | 50 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking default

144 instructions pooled; benign false blocks 21.2% under G-FEAS and 21.2% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 12.5% | 12.5% | 2 | 0 | 0.0% |
| V2 | 14 | 0.0% | 0.0% | 0.0% | 0 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 41.7% | 41.7% | 0 | 0 | **0.0%** |
| **V4** | 16 | 0.0% | 37.5% | 37.5% | 0 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 0.0% | 0.0% | 7 | 0 | 0.0% |
| V6 | 16 | 0.0% | 6.2% | 6.2% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 21.2% | 21.2% | 0 | 0 | 0.0% |

### Claude Opus 5 (closed, flagship) - M_free / none / thinking disabled

144 instructions pooled; benign false blocks 21.2% under G-FEAS and 21.2% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 16 | 0.0% | 12.5% | 12.5% | 0 | 0 | 0.0% |
| V2 | 14 | 0.0% | 0.0% | 0.0% | 0 | 0 | 0.0% |
| **V3** | 12 | 0.0% | 50.0% | 58.3% | 1 | 1 | **8.3%** |
| **V4** | 16 | 0.0% | 25.0% | 25.0% | 2 | 0 | **0.0%** |
| V5 | 18 | 0.0% | 0.0% | 0.0% | 2 | 0 | 0.0% |
| V6 | 16 | 0.0% | 0.0% | 0.0% | 0 | 0 | 0.0% |
| benign | 52 | 0.0% | 21.2% | 21.2% | 0 | 0 | 0.0% |

### GPT-5.6 Sol (closed, flagship spot-check) - M_constrained / json_schema / thinking none

72 instructions pooled; benign false blocks 3.8% under G-FEAS and 3.8% under G-CERT.

| class | items | UNGUARDED blocks | G-FEAS blocks | G-CERT blocks | G-FEAS passes | separated | separation share |
|---|---|---|---|---|---|---|---|
| V1 | 8 | 0.0% | 37.5% | 37.5% | 5 | 0 | 0.0% |
| V2 | 7 | 0.0% | 0.0% | 0.0% | 7 | 0 | 0.0% |
| **V3** | 6 | 0.0% | 16.7% | 100.0% | 5 | 5 | **83.3%** |
| **V4** | 8 | 0.0% | 0.0% | 0.0% | 8 | 0 | **0.0%** |
| V5 | 9 | 0.0% | 0.0% | 0.0% | 9 | 0 | 0.0% |
| V6 | 8 | 0.0% | 0.0% | 0.0% | 8 | 0 | 0.0% |
| benign | 26 | 0.0% | 3.8% | 3.8% | 25 | 0 | 0.0% |

