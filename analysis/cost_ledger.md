# The experiment-cost ledger behind USD 221.63

The manuscript's cost disclosure (Section 6.8) prints one number,
USD 221.63, defined as the sum of three audited components. This file is
the per-arm ledger behind the first two; the third has its own generated
artifact.

## 1. E1/E2 hosted-API spend through the 2026-08-12 reconciliation, USD 100.81

Each figure is the provider-billed spend for the arm, reconciled against
the token counts of the released call logs at the pinned per-arm price
bases (the price tables and their retrieval dates are in
`code/scripts/anthropic_pilot.py` and the run configurations).

| arm | USD |
|---|---|
| DeepSeek V4-Pro | 9.01 |
| GPT-5.4-mini | 10.39 |
| GPT-5.6 Sol | 25.83 |
| Terra pilot | 0.19 |
| Claude Sonnet 5 | 20.74 |
| Claude Opus 5 (core E1) | 34.66 |
| **Total through the checkpoint** | **100.81** |

Of which pilots: USD 1.06. By vendor: OpenAI 36.40, Anthropic 55.40,
DeepSeek 9.01.

## 2. The Claude Opus 5 E1 relaunch (2026-08-13), USD 79.16

The full Opus arm re-evaluation after the checkpoint. Opus E1 total:
34.66 + 79.16 = USD 113.82.

## 3. E3, USD 41.66

`analysis/E13_e3_costs.csv`, row [ALL / grid + calibration],
`usd_recomputed`: every logged E3 call priced at its arm's pinned price
base and reconciled against every run meta's session tally (residuals in
the same table).

## Total, and the cross-checks

100.81 + 79.16 + 41.66 = **USD 221.63**. An independent list-price
recomputation over the released call logs gives USD 220.57, a 0.5%
difference against the billed total. With the provider-recorded prompt-cache
saving of USD 117.00 on the Anthropic arms added back, the same calls
without caching price at USD 338.63. The two local arms carry an explicit
zero API price (electricity only), at 3.5 GPU hours.
