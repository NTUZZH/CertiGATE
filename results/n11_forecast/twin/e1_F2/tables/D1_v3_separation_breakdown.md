# D1

<!-- N11 Stage 3 forecast twin (l1-n11-forecast-1) -->
<!-- reading F2 -->

Diagnostic input for the pending translation-difference audit of the mini arm's V3 separation, which sits below both smaller open arms (decision record, 2026-08-12). Nothing here is a conclusion.

V3 separation requires two things at once: the proposal must pass the feasibility guard, and the certificate must then refuse it. A proposal that never reproduces the damaging instruction is not separated either, so the gold-match column is reported beside the separation column: it says whether the arm translated the V3 instruction as the ground truth does, which is the quantity the audit needs.

| arm | cut | value | think | V3 items | separation | gold match exact | unseparated: accepted | unseparated: feas-blocked |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | all | all | - | 462 | 79.9% | 35.7% | 90 | 0 |
| qwen3-14b | register | conversational | - | 132 | 70.5% | 36.4% | 39 | 0 |
| qwen3-14b | register | formal | - | 195 | 75.4% | 32.3% | 45 | 0 |
| qwen3-14b | register | terse | - | 135 | 95.6% | 40.0% | 6 | 0 |
| qwen3.6-27b-fp8 | all | all | - | 462 | 85.7% | 36.4% | 63 | 3 |
| qwen3.6-27b-fp8 | register | conversational | - | 132 | 72.7% | 38.6% | 36 | 0 |
| qwen3.6-27b-fp8 | register | formal | - | 195 | 87.7% | 30.8% | 21 | 3 |
| qwen3.6-27b-fp8 | register | terse | - | 135 | 95.6% | 42.2% | 6 | 0 |
| glm-4-9b | all | all | - | 154 | 70.1% | 37.0% | 41 | 4 |
| glm-4-9b | register | conversational | - | 44 | 59.1% | 40.9% | 18 | 0 |
| glm-4-9b | register | formal | - | 65 | 70.8% | 40.0% | 16 | 2 |
| glm-4-9b | register | terse | - | 45 | 80.0% | 28.9% | 7 | 2 |
| openai | all | all | - | 308 | 78.6% | 35.1% | 64 | 2 |
| openai | register | conversational | - | 88 | 72.7% | 42.0% | 24 | 0 |
| openai | register | formal | - | 130 | 75.4% | 30.0% | 30 | 2 |
| openai | register | terse | - | 90 | 88.9% | 35.6% | 10 | 0 |
| deepseek | all | all | non_think | 308 | 0.0% | 0.0% | 3 | 0 |
| deepseek | all | all | think_high | 308 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | non_think | 88 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | think_high | 88 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | non_think | 130 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | think_high | 130 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | terse | non_think | 90 | 0.0% | 0.0% | 3 | 0 |
| deepseek | register | terse | think_high | 90 | 0.0% | 0.0% | 0 | 0 |
| sonnet | all | all | disabled | 308 | 83.1% | 31.8% | 50 | 2 |
| sonnet | register | conversational | disabled | 88 | 73.9% | 40.9% | 23 | 0 |
| sonnet | register | formal | disabled | 130 | 87.7% | 33.1% | 14 | 2 |
| sonnet | register | terse | disabled | 90 | 85.6% | 21.1% | 13 | 0 |
| opus | all | all | default | 308 | 89.6% | 37.3% | 32 | 0 |
| opus | all | all | disabled | 308 | 89.0% | 36.7% | 34 | 0 |
| opus | register | conversational | default | 88 | 86.4% | 40.9% | 12 | 0 |
| opus | register | conversational | disabled | 88 | 86.4% | 40.9% | 12 | 0 |
| opus | register | formal | default | 130 | 87.7% | 40.8% | 16 | 0 |
| opus | register | formal | disabled | 130 | 86.2% | 39.2% | 18 | 0 |
| opus | register | terse | default | 90 | 95.6% | 28.9% | 4 | 0 |
| opus | register | terse | disabled | 90 | 95.6% | 28.9% | 4 | 0 |
| sol | all | all | none | 154 | 83.8% | 36.4% | 20 | 2 |
| sol | register | conversational | none | 44 | 70.5% | 40.9% | 12 | 0 |
| sol | register | formal | none | 65 | 84.6% | 30.8% | 7 | 2 |
| sol | register | terse | none | 45 | 95.6% | 40.0% | 1 | 0 |

