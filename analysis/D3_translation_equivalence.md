# D3. Equivalence-aware translation fidelity (M_constrained, r0)

Two-rule normalisation (numeric type; reorder inversion). Raw exact-match floors at 0% on the two-op V3 families for every arm — a measurement artifact this measure removes.

| arm | benign | V3 (obedience to harmful instructions) | V4 |
|---|---|---|---|
| qwen3-14b | 604/800 (76%) | 189/220 (86%) | 141/220 (64%) |
| qwen3.6-27b-fp8 | 710/800 (89%) | 208/220 (95%) | 190/220 (86%) |
| glm-4-9b | 565/800 (71%) | 164/220 (75%) | 113/220 (51%) |
| mini | 623/800 (78%) | 178/220 (81%) | 180/220 (82%) |
| sonnet | 714/800 (89%) | 203/220 (92%) | 207/220 (94%) |
| opus | 713/800 (89%) | 211/220 (96%) | 200/220 (91%) |
| sol | 662/800 (83%) | 197/220 (90%) | 205/220 (93%) |
