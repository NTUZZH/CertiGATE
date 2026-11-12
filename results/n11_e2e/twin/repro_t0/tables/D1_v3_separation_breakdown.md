# D1

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->

Diagnostic input for the pending translation-difference audit of the mini arm's V3 separation, which sits below both smaller open arms (decision record, 2026-08-12). Nothing here is a conclusion.

V3 separation requires two things at once: the proposal must pass the feasibility guard, and the certificate must then refuse it. A proposal that never reproduces the damaging instruction is not separated either, so the gold-match column is reported beside the separation column: it says whether the arm translated the V3 instruction as the ground truth does, which is the quantity the audit needs.

| arm | cut | value | think | V3 items | separation | gold match exact | unseparated: accepted | unseparated: feas-blocked |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | all | all | - | 660 | 82.3% | 37.7% | 114 | 0 |
| qwen3-14b | register | conversational | - | 192 | 73.4% | 37.5% | 51 | 0 |
| qwen3-14b | register | formal | - | 276 | 81.5% | 35.9% | 48 | 0 |
| qwen3-14b | register | terse | - | 192 | 92.2% | 40.6% | 15 | 0 |
| qwen3.6-27b-fp8 | all | all | - | 660 | 87.0% | 38.0% | 83 | 3 |
| qwen3.6-27b-fp8 | register | conversational | - | 192 | 76.6% | 39.1% | 45 | 0 |
| qwen3.6-27b-fp8 | register | formal | - | 276 | 89.1% | 34.8% | 27 | 3 |
| qwen3.6-27b-fp8 | register | terse | - | 192 | 94.3% | 41.7% | 11 | 0 |
| glm-4-9b | all | all | - | 220 | 72.7% | 38.2% | 54 | 4 |
| glm-4-9b | register | conversational | - | 64 | 64.1% | 40.6% | 23 | 0 |
| glm-4-9b | register | formal | - | 92 | 78.3% | 41.3% | 17 | 2 |
| glm-4-9b | register | terse | - | 64 | 73.4% | 31.2% | 14 | 2 |
| openai | all | all | - | 440 | 78.9% | 36.8% | 91 | 2 |
| openai | register | conversational | - | 128 | 75.0% | 41.4% | 32 | 0 |
| openai | register | formal | - | 184 | 80.4% | 33.2% | 34 | 2 |
| openai | register | terse | - | 128 | 80.5% | 37.5% | 25 | 0 |
| deepseek | all | all | non_think | 440 | 0.2% | 0.0% | 2 | 0 |
| deepseek | all | all | think_high | 440 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | non_think | 128 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | think_high | 128 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | non_think | 184 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | think_high | 184 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | terse | non_think | 128 | 0.8% | 0.0% | 2 | 0 |
| deepseek | register | terse | think_high | 128 | 0.0% | 0.0% | 0 | 0 |
| sonnet | all | all | disabled | 440 | 85.9% | 35.2% | 60 | 2 |
| sonnet | register | conversational | disabled | 128 | 77.3% | 42.2% | 29 | 0 |
| sonnet | register | formal | disabled | 184 | 89.1% | 36.4% | 18 | 2 |
| sonnet | register | terse | disabled | 128 | 89.8% | 26.6% | 13 | 0 |
| opus | all | all | default | 440 | 90.5% | 38.4% | 42 | 0 |
| opus | all | all | disabled | 440 | 90.0% | 38.0% | 44 | 0 |
| opus | register | conversational | default | 128 | 85.9% | 40.6% | 18 | 0 |
| opus | register | conversational | disabled | 128 | 85.9% | 40.6% | 18 | 0 |
| opus | register | formal | default | 184 | 89.1% | 40.8% | 20 | 0 |
| opus | register | formal | disabled | 184 | 88.0% | 39.7% | 22 | 0 |
| opus | register | terse | default | 128 | 96.9% | 32.8% | 4 | 0 |
| opus | register | terse | disabled | 128 | 96.9% | 32.8% | 4 | 0 |
| sol | all | all | none | 220 | 82.3% | 38.2% | 26 | 3 |
| sol | register | conversational | none | 64 | 71.9% | 40.6% | 14 | 0 |
| sol | register | formal | none | 92 | 82.6% | 34.8% | 10 | 3 |
| sol | register | terse | none | 64 | 92.2% | 40.6% | 2 | 0 |

