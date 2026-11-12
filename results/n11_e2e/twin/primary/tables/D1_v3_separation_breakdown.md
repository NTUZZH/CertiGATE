# D1

<!-- N11 Stage 2 twin (l1-n11-stage2-1); decision instant t_d = t_known, planned-known, frozen set kf = running + seed on K -->
<!-- reading: primary -->

Diagnostic input for the pending translation-difference audit of the mini arm's V3 separation, which sits below both smaller open arms (decision record, 2026-08-12). Nothing here is a conclusion.

V3 separation requires two things at once: the proposal must pass the feasibility guard, and the certificate must then refuse it. A proposal that never reproduces the damaging instruction is not separated either, so the gold-match column is reported beside the separation column: it says whether the arm translated the V3 instruction as the ground truth does, which is the quantity the audit needs.

| arm | cut | value | think | V3 items | separation | gold match exact | unseparated: accepted | unseparated: feas-blocked |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | all | all | - | 462 | 80.5% | 35.7% | 87 | 0 |
| qwen3-14b | register | conversational | - | 132 | 68.2% | 36.4% | 42 | 0 |
| qwen3-14b | register | formal | - | 195 | 76.9% | 32.3% | 42 | 0 |
| qwen3-14b | register | terse | - | 135 | 97.8% | 40.0% | 3 | 0 |
| qwen3.6-27b-fp8 | all | all | - | 462 | 86.4% | 36.4% | 60 | 3 |
| qwen3.6-27b-fp8 | register | conversational | - | 132 | 70.5% | 38.6% | 39 | 0 |
| qwen3.6-27b-fp8 | register | formal | - | 195 | 89.2% | 30.8% | 18 | 3 |
| qwen3.6-27b-fp8 | register | terse | - | 135 | 97.8% | 42.2% | 3 | 0 |
| glm-4-9b | all | all | - | 154 | 70.1% | 37.0% | 41 | 4 |
| glm-4-9b | register | conversational | - | 44 | 56.8% | 40.9% | 19 | 0 |
| glm-4-9b | register | formal | - | 65 | 72.3% | 40.0% | 15 | 2 |
| glm-4-9b | register | terse | - | 45 | 80.0% | 28.9% | 7 | 2 |
| openai | all | all | - | 308 | 79.2% | 35.1% | 62 | 2 |
| openai | register | conversational | - | 88 | 70.5% | 42.0% | 26 | 0 |
| openai | register | formal | - | 130 | 76.9% | 30.0% | 28 | 2 |
| openai | register | terse | - | 90 | 91.1% | 35.6% | 8 | 0 |
| deepseek | all | all | non_think | 308 | 0.0% | 0.0% | 3 | 0 |
| deepseek | all | all | think_high | 308 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | non_think | 88 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | think_high | 88 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | non_think | 130 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | think_high | 130 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | terse | non_think | 90 | 0.0% | 0.0% | 3 | 0 |
| deepseek | register | terse | think_high | 90 | 0.0% | 0.0% | 0 | 0 |
| sonnet | all | all | disabled | 308 | 83.8% | 31.8% | 48 | 2 |
| sonnet | register | conversational | disabled | 88 | 71.6% | 40.9% | 25 | 0 |
| sonnet | register | formal | disabled | 130 | 89.2% | 33.1% | 12 | 2 |
| sonnet | register | terse | disabled | 90 | 87.8% | 21.1% | 11 | 0 |
| opus | all | all | default | 308 | 90.3% | 37.3% | 30 | 0 |
| opus | all | all | disabled | 308 | 89.6% | 36.7% | 32 | 0 |
| opus | register | conversational | default | 88 | 84.1% | 40.9% | 14 | 0 |
| opus | register | conversational | disabled | 88 | 84.1% | 40.9% | 14 | 0 |
| opus | register | formal | default | 130 | 89.2% | 40.8% | 14 | 0 |
| opus | register | formal | disabled | 130 | 87.7% | 39.2% | 16 | 0 |
| opus | register | terse | default | 90 | 97.8% | 28.9% | 2 | 0 |
| opus | register | terse | disabled | 90 | 97.8% | 28.9% | 2 | 0 |
| sol | all | all | none | 154 | 84.4% | 36.4% | 19 | 2 |
| sol | register | conversational | none | 44 | 68.2% | 40.9% | 13 | 0 |
| sol | register | formal | none | 65 | 86.2% | 30.8% | 6 | 2 |
| sol | register | terse | none | 45 | 97.8% | 40.0% | 0 | 0 |

