# N14. The gate comparison at the decision instant under other dispatching rules

Generated 2026-11-10T14:31:26+08:00 by `code/scripts/n14_alt_dispatch.py` (l1-n14-alt-dispatch-1). Status COMPLETE. 1300 analyse assertions passed; census assertions: see `results/n14_altdispatch/census_assertions.json`.

## What was computed

- Population: the 1723 issuable published items of N11 with N11's decision instant t_d = t_known and canonical proposals; thresholds tau = 0.20, D-REL1 0.02, D-REL2 0.02, D-ABS 0.8119 bh.
- Dispatchers (the site's rule for the baseline, the trajectory, every dispatch of K, FI and the full window, the D-REL2 reference and the realised run): `atc` (ATC, k = 2 (the site's dispatcher, control)); `wspt` (Weighted shortest processing time); `pfifo` (Priority class, then first in first out); `edd` (Earliest due date). PFIFO keeps the release recorded before the dispatch-origin raise (N6's `pfifo` on every dispatch where nothing is raised, asserted).
- Readings: K (known board at t_d), FI (full window minus completed orders, at t_d), P0 (full window at t = 0). Truths: realised marginal cost on the original fields against the rule's own no-proposal run (`orig`, the tab:decision truth), the realised absolute cost on the original fields (`origabs`), and the decision-time oracle of the known board (absolute g and marginal m; dispatcher-free).

## Headline: dispositions at delta = 0.10 (realised marginal cost, original fields)

Miss = share of costly proposals applied; FR = share of cheap proposals referred; 95% cluster-bootstrap interval over instances (N2's bootstrap). Union = G-CERT-M or D-REL2.

### atc (ATC, k = 2 (the site's dispatcher, control)): 89 priced on K, 17 costly and 72 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] |
| G-CERT-M | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] | 23.5 (4/17) [16.7, 50.0] | 0.0 (0/72) [0.0, 0.0] |
| D-REL1 | 17.6 (3/17) [11.1, 50.0] | 5.6 (4/72) [4.5, 10.0] | 17.6 (3/17) [11.1, 50.0] | 4.2 (3/72) [2.5, 10.0] | 17.6 (3/17) [11.1, 50.0] | 1.4 (1/72) [0.0, 2.5] |
| D-REL2 | 17.6 (3/17) [11.1, 50.0] | 1.4 (1/72) [0.0, 2.5] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] |
| D-ABS | 17.6 (3/17) [11.1, 50.0] | 5.6 (4/72) [4.5, 10.0] | 17.6 (3/17) [11.1, 50.0] | 5.6 (4/72) [4.5, 10.0] | 17.6 (3/17) [11.1, 50.0] | 2.8 (2/72) [0.0, 5.0] |
| Union | 17.6 (3/17) [11.1, 50.0] | 1.4 (1/72) [0.0, 2.5] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] | 17.6 (3/17) [11.1, 50.0] | 0.0 (0/72) [0.0, 0.0] |

### wspt (Weighted shortest processing time): 87 priced on K, 16 costly and 71 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 12.5 (2/16) [0.0, 50.0] | 8.5 (6/71) [0.0, 15.4] | 6.2 (1/16) [0.0, 50.0] | 64.8 (46/71) [0.0, 100.0] | 6.2 (1/16) [0.0, 50.0] | 84.5 (60/71) [0.0, 100.0] |
| G-CERT-M | 25.0 (4/16) [16.7, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 50.0 (8/16) [16.7, 75.0] | 0.0 (0/71) [0.0, 0.0] |
| D-REL1 | 12.5 (2/16) [0.0, 50.0] | 4.2 (3/71) [2.6, 10.0] | 12.5 (2/16) [0.0, 50.0] | 4.2 (3/71) [2.6, 10.0] | 12.5 (2/16) [0.0, 50.0] | 1.4 (1/71) [0.0, 2.6] |
| D-REL2 | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] |
| D-ABS | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [2.6, 13.6] | 12.5 (2/16) [0.0, 50.0] | 4.2 (3/71) [2.6, 10.0] | 12.5 (2/16) [0.0, 50.0] | 1.4 (1/71) [0.0, 2.6] |
| Union | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] |

### pfifo (Priority class, then first in first out): 87 priced on K, 16 costly and 71 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] |
| G-CERT-M | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] |
| D-REL1 | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] |
| D-REL2 | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 1.4 (1/71) [0.0, 2.6] |
| D-ABS | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 4.2 (3/71) [0.0, 7.7] |
| Union | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 1.4 (1/71) [0.0, 2.6] |

### edd (Earliest due date): 87 priced on K, 16 costly and 71 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] |
| G-CERT-M | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] | 12.5 (2/16) [0.0, 50.0] | 0.0 (0/71) [0.0, 0.0] |
| D-REL1 | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] |
| D-REL2 | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 1.4 (1/71) [0.0, 2.6] |
| D-ABS | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 7.0 (5/71) [4.5, 10.0] | 12.5 (2/16) [0.0, 50.0] | 4.2 (3/71) [0.0, 7.7] |
| Union | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 2.8 (2/71) [0.0, 5.1] | 12.5 (2/16) [0.0, 50.0] | 1.4 (1/71) [0.0, 2.6] |

## The anchor gap of the known board per dispatcher

Anchor gap on K = (anchor dispatch of K by the rule - OPT_K)/max(OPT_K, 1 bh), one value per issuable item (its (instance, t_d) board); OPT_K is the decision-time oracle. The certified anchor gap is the certificate's own gap of the anchor on K.

| rule | stratum | items | median % | p90 % | max % | gap 0 | > 0.05 | > 0.10 | > 0.20 | certified median % | certified > tau |
|---|---|---|---|---|---|---|---|---|---|---|---|
| atc | All | 110 | 0.0 | 0.0 | 20.6 | 106 | 3 | 3 | 1 | 0.0 | 1 |
| atc | Primary | 58 | 0.0 | 0.0 | 20.6 | 54 | 3 | 3 | 1 | 0.0 | 1 |
| atc | Confirmation | 36 | 0.0 | 0.0 | 0.0 | 36 | 0 | 0 | 0 | 0.0 | 0 |
| atc | Buildings | 16 | 0.0 | 0.0 | 0.0 | 16 | 0 | 0 | 0 | 0.0 | 0 |
| wspt | All | 110 | 0.0 | 15.3 | 73.7 | 68 | 29 | 20 | 8 | 0.0 | 8 |
| wspt | Primary | 58 | 0.0 | 33.6 | 73.7 | 35 | 10 | 9 | 8 | 0.0 | 8 |
| wspt | Confirmation | 36 | 6.0 | 15.3 | 15.3 | 17 | 19 | 11 | 0 | 6.0 | 0 |
| wspt | Buildings | 16 | 0.0 | 0.0 | 0.0 | 16 | 0 | 0 | 0 | 0.0 | 0 |
| pfifo | All | 110 | 0.0 | 0.0 | 20.6 | 107 | 3 | 3 | 1 | 0.0 | 1 |
| pfifo | Primary | 58 | 0.0 | 0.0 | 20.6 | 55 | 3 | 3 | 1 | 0.0 | 1 |
| pfifo | Confirmation | 36 | 0.0 | 0.0 | 0.0 | 36 | 0 | 0 | 0 | 0.0 | 0 |
| pfifo | Buildings | 16 | 0.0 | 0.0 | 0.0 | 16 | 0 | 0 | 0 | 0.0 | 0 |
| edd | All | 110 | 0.0 | 0.0 | 20.6 | 107 | 3 | 3 | 1 | 0.0 | 1 |
| edd | Primary | 58 | 0.0 | 0.0 | 20.6 | 55 | 3 | 3 | 1 | 0.0 | 1 |
| edd | Confirmation | 36 | 0.0 | 0.0 | 0.0 | 36 | 0 | 0 | 0 | 0.0 | 0 |
| edd | Buildings | 16 | 0.0 | 0.0 | 0.0 | 16 | 0 | 0 | 0 | 0.0 | 0 |

Per distinct (instance, t_d) board:

| rule | boards | median % | p90 % | gap 0 | > 0.10 |
|---|---|---|---|---|---|
| atc | 29 | 0.0 | 0.5 | 26 | 2 |
| wspt | 29 | 4.1 | 36.8 | 13 | 11 |
| pfifo | 29 | 0.0 | 0.0 | 27 | 2 |
| edd | 29 | 0.0 | 0.0 | 27 | 2 |

Full-window anchor gap of each rule (t = 0, 60 instances; N6's Table 1 quantity, reproduced):

| rule | stratum | instances | median % | max % | above 0.20 |
|---|---|---|---|---|---|
| atc | All | 3 | [0.0, 0.2] | 12.4 | 0 |
| atc | Primary | 1 | 12.4 | 12.4 | 0 |
| atc | Confirmation | 1 | [0.0, 0.2] | 0.2 | 0 |
| atc | Buildings | 1 | 0.0 | 0.0 | 0 |
| wspt | All | 3 | 28.4 | 73.6 | 2 |
| wspt | Primary | 1 | 28.4 | 28.4 | 1 |
| wspt | Confirmation | 1 | [73.2, 73.6] | 73.6 | 1 |
| wspt | Buildings | 1 | 0.0 | 0.0 | 0 |
| pfifo | All | 3 | 0.0 | 10.1 | 0 |
| pfifo | Primary | 1 | 10.1 | 10.1 | 0 |
| pfifo | Confirmation | 1 | 0.0 | 0.0 | 0 |
| pfifo | Buildings | 1 | 0.0 | 0.0 | 0 |
| edd | All | 3 | 0.0 | 10.1 | 0 |
| edd | Primary | 1 | 10.1 | 10.1 | 0 |
| edd | Confirmation | 1 | 0.0 | 0.0 | 0 |
| edd | Buildings | 1 | 0.0 | 0.0 | 0 |

## Pricing error against the known-board optimum (Table 14 twin)

Error = price - the decision-time oracle's cost on K; under = error below -0.05.

Absolute truth (cells: under % / median error):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS |
|---|---|---|---|---|---|
| atc | 0.0 / 0.000 | 3.4 / 0.000 | 4.5 / 0.000 | 2.2 / 0.000 | 4.5 / 0.000 |
| wspt | 0.0 / 0.000 | 32.2 / 0.000 | 33.3 / 0.000 | 32.2 / 0.000 | 31.0 / 0.000 |
| pfifo | 0.0 / 0.000 | 3.4 / 0.000 | 4.6 / 0.000 | 2.3 / 0.000 | 4.6 / 0.000 |
| edd | 0.0 / 0.000 | 3.4 / 0.000 | 4.6 / 0.000 | 2.3 / 0.000 | 4.6 / 0.000 |

Marginal truth (cells: under % / median error):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS |
|---|---|---|---|---|---|
| atc | 0.0 / 0.000 | 0.0 / 0.000 | 2.2 / 0.000 | 0.0 / 0.000 | 2.2 / 0.000 |
| wspt | 0.0 / 0.000 | 0.0 / 0.000 | 2.3 / 0.000 | 1.1 / 0.000 | 2.3 / 0.000 |
| pfifo | 0.0 / 0.000 | 0.0 / 0.000 | 2.3 / 0.000 | 0.0 / 0.000 | 2.3 / 0.000 |
| edd | 0.0 / 0.000 | 0.0 / 0.000 | 2.3 / 0.000 | 0.0 / 0.000 | 2.3 / 0.000 |

D-REL2 by stratum:

| rule | stratum | priced | absolute under % | marginal under % |
|---|---|---|---|---|
| atc | Primary | 49 | 4.1 | 0.0 |
| atc | Confirmation | 28 | 0.0 | 0.0 |
| atc | Buildings | 12 | 0.0 | 0.0 |
| wspt | Primary | 47 | 23.4 | 2.1 |
| wspt | Confirmation | 28 | 60.7 | 0.0 |
| wspt | Buildings | 12 | 0.0 | 0.0 |
| pfifo | Primary | 47 | 4.3 | 0.0 |
| pfifo | Confirmation | 28 | 0.0 | 0.0 |
| pfifo | Buildings | 12 | 0.0 | 0.0 |
| edd | Primary | 47 | 4.3 | 0.0 |
| edd | Confirmation | 28 | 0.0 | 0.0 |
| edd | Buildings | 12 | 0.0 | 0.0 |

## Dispositions against the known-board oracle (pricing panel of Table 16), delta = 0.10

Absolute cost on K (cells: miss % / FR %):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union | costly / cheap |
|---|---|---|---|---|---|---|---|
| atc | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 5.3 | 0.0 / 1.3 | 0.0 / 5.3 | 0.0 / 1.3 | 14 / 75 |
| wspt | 33.3 / 0.0 | 60.0 / 0.0 | 50.0 / 3.5 | 53.3 / 0.0 | 43.3 / 3.5 | 53.3 / 0.0 | 30 / 57 |
| pfifo | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 6.8 | 0.0 / 2.7 | 0.0 / 6.8 | 0.0 / 2.7 | 14 / 73 |
| edd | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 6.8 | 0.0 / 2.7 | 0.0 / 6.8 | 0.0 / 2.7 | 14 / 73 |

Marginal cost on K (cells: miss % / FR %):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union | costly / cheap |
|---|---|---|---|---|---|---|---|
| atc | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 5.3 | 0.0 / 1.3 | 0.0 / 5.3 | 0.0 / 1.3 | 14 / 75 |
| wspt | 0.0 / 6.9 | 20.0 / 0.0 | 6.7 / 4.2 | 6.7 / 0.0 | 6.7 / 6.9 | 6.7 / 0.0 | 15 / 72 |
| pfifo | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 6.8 | 0.0 / 2.7 | 0.0 / 6.8 | 0.0 / 2.7 | 14 / 73 |
| edd | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 6.8 | 0.0 / 2.7 | 0.0 / 6.8 | 0.0 / 2.7 | 14 / 73 |

## Dispositions against the realised absolute cost (origabs), delta = 0.10

| rule | reading | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union | costly / cheap |
|---|---|---|---|---|---|---|---|---|
| atc | K | 75.4 / 0.0 | 75.4 / 0.0 | 71.9 / 6.2 | 73.7 / 0.0 | 71.9 / 6.2 | 73.7 / 0.0 | 57 / 32 |
| atc | FI | 75.4 / 0.0 | 75.4 / 0.0 | 73.7 / 6.2 | 75.4 / 0.0 | 71.9 / 6.2 | 75.4 / 0.0 | 57 / 32 |
| wspt | K | 74.0 / 0.0 | 84.4 / 0.0 | 79.2 / 10.0 | 81.8 / 0.0 | 76.6 / 10.0 | 81.8 / 0.0 | 77 / 10 |
| wspt | FI | 20.8 / 0.0 | 81.8 / 0.0 | 79.2 / 10.0 | 81.8 / 0.0 | 79.2 / 10.0 | 81.8 / 0.0 | 77 / 10 |
| pfifo | K | 73.6 / 0.0 | 73.6 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 53 / 34 |
| pfifo | FI | 73.6 / 0.0 | 73.6 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 53 / 34 |
| edd | K | 73.6 / 0.0 | 73.6 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 53 / 34 |
| edd | FI | 73.6 / 0.0 | 73.6 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 69.8 / 8.8 | 69.8 / 0.0 | 53 / 34 |

## Costly proposals D-REL2 applies and the certificate refers (delta = 0.10)

| rule | truth | reading | costly | G-CERT refers, D-REL2 applies | G-CERT-M refers, D-REL2 applies | D-REL2 refers, G-CERT-M applies | cheap | G-CERT refers cheap, D-REL2 not | G-CERT-M refers cheap, D-REL2 not |
|---|---|---|---|---|---|---|---|---|---|
| atc | kabs | K | 14 | 0 | 0 | 0 | 75 | 0 | 0 |
| atc | kabs | FI | 14 | 0 | 0 | 0 | 75 | 0 | 0 |
| atc | origabs | K | 57 | 0 | 0 | 1 | 32 | 0 | 0 |
| atc | origabs | FI | 57 | 0 | 0 | 0 | 32 | 0 | 0 |
| atc | orig | K | 17 | 0 | 0 | 0 | 72 | 0 | 0 |
| atc | orig | FI | 17 | 0 | 0 | 0 | 72 | 0 | 0 |
| wspt | kabs | K | 30 | 6 | 0 | 2 | 57 | 0 | 0 |
| wspt | kabs | FI | 30 | 9 | 0 | 0 | 57 | 38 | 0 |
| wspt | origabs | K | 77 | 6 | 0 | 2 | 10 | 0 | 0 |
| wspt | origabs | FI | 77 | 47 | 0 | 0 | 10 | 0 | 0 |
| wspt | orig | K | 16 | 0 | 0 | 2 | 71 | 6 | 0 |
| wspt | orig | FI | 16 | 1 | 0 | 0 | 71 | 46 | 0 |
| pfifo | kabs | K | 14 | 0 | 0 | 0 | 73 | 0 | 0 |
| pfifo | kabs | FI | 14 | 0 | 0 | 0 | 73 | 0 | 0 |
| pfifo | origabs | K | 53 | 0 | 0 | 2 | 34 | 0 | 0 |
| pfifo | origabs | FI | 53 | 0 | 0 | 2 | 34 | 0 | 0 |
| pfifo | orig | K | 16 | 0 | 0 | 0 | 71 | 0 | 0 |
| pfifo | orig | FI | 16 | 0 | 0 | 0 | 71 | 0 | 0 |
| edd | kabs | K | 14 | 0 | 0 | 0 | 73 | 0 | 0 |
| edd | kabs | FI | 14 | 0 | 0 | 0 | 73 | 0 | 0 |
| edd | origabs | K | 53 | 0 | 0 | 2 | 34 | 0 | 0 |
| edd | origabs | FI | 53 | 0 | 0 | 2 | 34 | 0 | 0 |
| edd | orig | K | 16 | 0 | 0 | 0 | 71 | 0 | 0 |
| edd | orig | FI | 16 | 0 | 0 | 0 | 71 | 0 | 0 |

## Populations and the decision instant under each rule

| rule | issuable (N11) | priced on K | named order started by t_d | names running work | not issuable under the rule | stopped before the quality stage | priced and issuable under the rule |
|---|---|---|---|---|---|---|---|
| atc | 110 | 89 | 0 | 0 | 0 | 21 | 89 |
| wspt | 110 | 87 | 2 | 0 | 2 | 23 | 87 |
| pfifo | 110 | 87 | 2 | 2 | 2 | 23 | 87 |
| edd | 110 | 87 | 2 | 2 | 2 | 23 | 87 |

Sensitivity on the items also issuable under the rule (K and FI, orig, delta 0.10, miss / FR %):

| rule | reading | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union |
|---|---|---|---|---|---|---|---|
| atc | K | 17.6 / 0.0 | 17.6 / 0.0 | 17.6 / 5.6 | 17.6 / 1.4 | 17.6 / 5.6 | 17.6 / 1.4 |
| atc | FI | 17.6 / 0.0 | 17.6 / 0.0 | 17.6 / 4.2 | 17.6 / 0.0 | 17.6 / 5.6 | 17.6 / 0.0 |
| wspt | K | 12.5 / 8.5 | 25.0 / 0.0 | 12.5 / 4.2 | 12.5 / 0.0 | 12.5 / 7.0 | 12.5 / 0.0 |
| wspt | FI | 6.2 / 64.8 | 12.5 / 0.0 | 12.5 / 4.2 | 12.5 / 0.0 | 12.5 / 4.2 | 12.5 / 0.0 |
| pfifo | K | 12.5 / 0.0 | 12.5 / 0.0 | 12.5 / 7.0 | 12.5 / 2.8 | 12.5 / 7.0 | 12.5 / 2.8 |
| pfifo | FI | 12.5 / 0.0 | 12.5 / 0.0 | 12.5 / 7.0 | 12.5 / 2.8 | 12.5 / 7.0 | 12.5 / 2.8 |
| edd | K | 12.5 / 0.0 | 12.5 / 0.0 | 12.5 / 7.0 | 12.5 / 2.8 | 12.5 / 7.0 | 12.5 / 2.8 |
| edd | FI | 12.5 / 0.0 | 12.5 / 0.0 | 12.5 / 7.0 | 12.5 / 2.8 | 12.5 / 7.0 | 12.5 / 2.8 |

## Oracle on the known boards

| rule | boards | complete | proved | trades closed by LB2 | trades reusing N11 | trades solved by N14 | max width_rel |
|---|---|---|---|---|---|---|---|
| atc | 58 | 58 | 58 | 644 | 4 | 0 | 0.0000 |
| wspt | 58 | 58 | 58 | 633 | 2 | 13 | 0.0002 |
| pfifo | 58 | 58 | 58 | 645 | 3 | 0 | 0.0000 |
| edd | 58 | 58 | 58 | 645 | 3 | 0 | 0.0000 |

Solve stage: 8 distinct trades solved ({'atc': 4, 'edd': 3, 'pfifo': 3, 'wspt': 2} reused from N11 by content), 0 re-solves, wall 1 s, cores [8, 9, 10, 11], 4 CP-SAT workers, budget 60.0 s. Budget-limited rows: 0. Max foreign_share on a budget-limited row: none. cpu_share (whole call) median 0.442; recorded on every row, not the validity test (foreign_share > 0.10 is).

## Assertions

- `atc`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 89 covered rows).
- `wspt`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 87 covered rows).
- `pfifo`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 87 covered rows).
- `edd`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 87 covered rows).
- Control reproduction (R10): {"skipped": "smoke"}.
- Analyse checks by group: {"A1": 2, "R9": 1298}.

