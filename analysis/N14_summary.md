# N14. The gate comparison at the decision instant under other dispatching rules

Generated 2026-11-10T14:53:59+08:00 by `code/scripts/n14_alt_dispatch.py` (l1-n14-alt-dispatch-1). Status COMPLETE. 139981 analyse assertions passed; census assertions: see `results/n14_altdispatch/census_assertions.json`.

## What was computed

- Population: the 1723 issuable published items of N11 with N11's decision instant t_d = t_known and canonical proposals; thresholds tau = 0.20, D-REL1 0.02, D-REL2 0.02, D-ABS 0.8119 bh.
- Dispatchers (the site's rule for the baseline, the trajectory, every dispatch of K, FI and the full window, the D-REL2 reference and the realised run): `atc` (ATC, k = 2 (the site's dispatcher, control)); `wspt` (Weighted shortest processing time); `pfifo` (Priority class, then first in first out); `edd` (Earliest due date). PFIFO keeps the release recorded before the dispatch-origin raise (N6's `pfifo` on every dispatch where nothing is raised, asserted).
- Readings: K (known board at t_d), FI (full window minus completed orders, at t_d), P0 (full window at t = 0). Truths: realised marginal cost on the original fields against the rule's own no-proposal run (`orig`, the tab:decision truth), the realised absolute cost on the original fields (`origabs`), and the decision-time oracle of the known board (absolute g and marginal m; dispatcher-free).

## Headline: dispositions at delta = 0.10 (realised marginal cost, original fields)

Miss = share of costly proposals applied; FR = share of cheap proposals referred; 95% cluster-bootstrap interval over instances (N2's bootstrap). Union = G-CERT-M or D-REL2.

### atc (ATC, k = 2 (the site's dispatcher, control)): 1356 priced on K, 208 costly and 1148 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 12.0 (25/208) [8.5, 15.7] | 0.0 (0/1148) [0.0, 0.0] | 13.5 (28/208) [8.9, 18.6] | 2.0 (23/1148) [0.0, 5.1] | 14.4 (30/208) [9.4, 20.1] | 2.8 (32/1148) [0.0, 7.3] |
| G-CERT-M | 12.5 (26/208) [8.9, 16.3] | 0.0 (0/1148) [0.0, 0.0] | 14.9 (31/208) [9.9, 20.5] | 0.0 (0/1148) [0.0, 0.0] | 19.2 (40/208) [13.0, 26.2] | 0.0 (0/1148) [0.0, 0.0] |
| D-REL1 | 10.1 (21/208) [6.8, 13.4] | 5.3 (61/1148) [4.0, 6.8] | 10.1 (21/208) [6.8, 13.4] | 5.2 (60/1148) [3.9, 6.7] | 10.1 (21/208) [6.8, 13.4] | 3.2 (37/1148) [2.1, 4.5] |
| D-REL2 | 10.1 (21/208) [6.8, 13.4] | 1.2 (14/1148) [0.4, 2.2] | 10.1 (21/208) [6.8, 13.4] | 1.1 (13/1148) [0.3, 2.2] | 10.1 (21/208) [6.8, 13.4] | 0.9 (10/1148) [0.2, 1.8] |
| D-ABS | 9.6 (20/208) [6.3, 13.0] | 5.4 (62/1148) [4.0, 6.9] | 9.1 (19/208) [5.8, 12.6] | 6.1 (70/1148) [4.6, 7.8] | 9.1 (19/208) [5.8, 12.6] | 4.5 (52/1148) [3.1, 6.1] |
| Union | 10.1 (21/208) [6.8, 13.4] | 1.2 (14/1148) [0.4, 2.2] | 10.1 (21/208) [6.8, 13.4] | 1.1 (13/1148) [0.3, 2.2] | 10.1 (21/208) [6.8, 13.4] | 0.9 (10/1148) [0.2, 1.8] |

### wspt (Weighted shortest processing time): 1346 priced on K, 200 costly and 1146 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 14.5 (29/200) [8.7, 21.3] | 4.0 (46/1146) [1.7, 6.8] | 14.0 (28/200) [7.8, 21.2] | 26.2 (300/1146) [15.5, 37.5] | 10.5 (21/200) [6.0, 15.5] | 29.9 (343/1146) [17.3, 43.0] |
| G-CERT-M | 18.5 (37/200) [11.9, 25.8] | 0.0 (0/1146) [0.0, 0.0] | 21.0 (42/200) [12.7, 30.7] | 0.0 (0/1146) [0.0, 0.0] | 26.0 (52/200) [16.4, 36.6] | 0.0 (0/1146) [0.0, 0.0] |
| D-REL1 | 11.5 (23/200) [7.4, 15.5] | 5.1 (59/1146) [3.8, 6.6] | 11.5 (23/200) [7.4, 15.5] | 5.1 (59/1146) [3.8, 6.6] | 11.5 (23/200) [7.4, 15.5] | 3.5 (40/1146) [2.2, 4.9] |
| D-REL2 | 11.5 (23/200) [7.4, 15.5] | 1.0 (12/1146) [0.2, 2.1] | 11.5 (23/200) [7.4, 15.5] | 1.0 (11/1146) [0.1, 2.0] | 11.5 (23/200) [7.4, 15.5] | 1.0 (11/1146) [0.1, 2.0] |
| D-ABS | 11.5 (23/200) [7.4, 15.5] | 5.7 (65/1146) [4.2, 7.2] | 10.0 (20/200) [6.2, 13.7] | 6.8 (78/1146) [5.1, 8.6] | 10.0 (20/200) [6.2, 13.7] | 5.5 (63/1146) [3.8, 7.4] |
| Union | 11.5 (23/200) [7.4, 15.5] | 1.0 (12/1146) [0.2, 2.1] | 11.5 (23/200) [7.4, 15.5] | 1.0 (11/1146) [0.1, 2.0] | 11.5 (23/200) [7.4, 15.5] | 1.0 (11/1146) [0.1, 2.0] |

### pfifo (Priority class, then first in first out): 1358 priced on K, 209 costly and 1149 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 11.5 (24/209) [8.0, 15.3] | 0.1 (1/1149) [0.0, 0.3] | 12.0 (25/209) [7.9, 16.7] | 2.3 (26/1149) [0.0, 5.8] | 12.4 (26/209) [8.1, 17.3] | 2.8 (32/1149) [0.0, 7.2] |
| G-CERT-M | 11.5 (24/209) [8.0, 15.3] | 0.0 (0/1149) [0.0, 0.0] | 14.4 (30/209) [9.5, 19.6] | 0.0 (0/1149) [0.0, 0.0] | 15.8 (33/209) [10.5, 21.8] | 0.0 (0/1149) [0.0, 0.0] |
| D-REL1 | 10.5 (22/209) [7.1, 14.1] | 5.6 (64/1149) [4.1, 7.2] | 10.5 (22/209) [7.1, 14.1] | 5.6 (64/1149) [4.1, 7.2] | 10.5 (22/209) [7.1, 14.1] | 3.7 (42/1149) [2.3, 5.2] |
| D-REL2 | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.3 (15/1149) [0.4, 2.4] |
| D-ABS | 10.5 (22/209) [7.1, 14.1] | 6.0 (69/1149) [4.4, 7.7] | 10.5 (22/209) [7.1, 14.1] | 6.2 (71/1149) [4.6, 7.9] | 10.5 (22/209) [7.1, 14.1] | 4.5 (52/1149) [3.0, 6.2] |
| Union | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.3 (15/1149) [0.4, 2.4] |

### edd (Earliest due date): 1358 priced on K, 209 costly and 1149 cheap

| design | K miss | K FR | FI miss | FI FR | P0 miss | P0 FR |
|---|---|---|---|---|---|---|
| G-CERT | 11.5 (24/209) [8.0, 15.3] | 0.1 (1/1149) [0.0, 0.3] | 12.0 (25/209) [7.9, 16.7] | 2.3 (26/1149) [0.0, 5.8] | 12.4 (26/209) [8.1, 17.3] | 2.8 (32/1149) [0.0, 7.2] |
| G-CERT-M | 11.5 (24/209) [8.0, 15.3] | 0.0 (0/1149) [0.0, 0.0] | 14.4 (30/209) [9.5, 19.6] | 0.0 (0/1149) [0.0, 0.0] | 15.8 (33/209) [10.5, 21.8] | 0.0 (0/1149) [0.0, 0.0] |
| D-REL1 | 10.5 (22/209) [7.1, 14.1] | 5.6 (64/1149) [4.1, 7.2] | 10.5 (22/209) [7.1, 14.1] | 5.6 (64/1149) [4.1, 7.2] | 10.5 (22/209) [7.1, 14.1] | 3.7 (42/1149) [2.3, 5.2] |
| D-REL2 | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.3 (15/1149) [0.4, 2.4] |
| D-ABS | 10.5 (22/209) [7.1, 14.1] | 6.0 (69/1149) [4.4, 7.7] | 10.5 (22/209) [7.1, 14.1] | 6.2 (71/1149) [4.6, 7.9] | 10.5 (22/209) [7.1, 14.1] | 4.5 (52/1149) [3.0, 6.2] |
| Union | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.5 (17/1149) [0.5, 2.7] | 10.5 (22/209) [7.1, 14.1] | 1.3 (15/1149) [0.4, 2.4] |

## The anchor gap of the known board per dispatcher

Anchor gap on K = (anchor dispatch of K by the rule - OPT_K)/max(OPT_K, 1 bh), one value per issuable item (its (instance, t_d) board); OPT_K is the decision-time oracle. The certified anchor gap is the certificate's own gap of the anchor on K.

| rule | stratum | items | median % | p90 % | max % | gap 0 | > 0.05 | > 0.10 | > 0.20 | certified median % | certified > tau |
|---|---|---|---|---|---|---|---|---|---|---|---|
| atc | All | 1723 | 0.0 | 0.0 | 20.6 | 1670 | 10 | 3 | 1 | 0.0 | 1 |
| atc | Primary | 890 | 0.0 | 0.0 | 20.6 | 838 | 10 | 3 | 1 | 0.0 | 1 |
| atc | Confirmation | 335 | 0.0 | 0.0 | 0.0 | 334 | 0 | 0 | 0 | 0.0 | 0 |
| atc | Buildings | 498 | 0.0 | 0.0 | 0.0 | 498 | 0 | 0 | 0 | 0.0 | 0 |
| wspt | All | 1723 | 0.0 | 6.7 | 1275.3 | 1365 | 202 | 144 | 74 | 0.0 | 74 |
| wspt | Primary | 890 | 0.0 | 6.4 | 315.1 | 654 | 101 | 77 | 46 | 0.0 | 46 |
| wspt | Confirmation | 335 | 0.0 | 13.8 | 1275.3 | 243 | 74 | 45 | 12 | 0.0 | 12 |
| wspt | Buildings | 498 | 0.0 | 0.0 | 20.6 | 468 | 27 | 22 | 16 | 0.0 | 16 |
| pfifo | All | 1723 | 0.0 | 0.0 | 20.6 | 1692 | 12 | 3 | 1 | 0.0 | 1 |
| pfifo | Primary | 890 | 0.0 | 0.0 | 20.6 | 860 | 12 | 3 | 1 | 0.0 | 1 |
| pfifo | Confirmation | 335 | 0.0 | 0.0 | 2.0 | 334 | 0 | 0 | 0 | 0.0 | 0 |
| pfifo | Buildings | 498 | 0.0 | 0.0 | 0.0 | 498 | 0 | 0 | 0 | 0.0 | 0 |
| edd | All | 1723 | 0.0 | 0.0 | 20.6 | 1692 | 12 | 3 | 1 | 0.0 | 1 |
| edd | Primary | 890 | 0.0 | 0.0 | 20.6 | 860 | 12 | 3 | 1 | 0.0 | 1 |
| edd | Confirmation | 335 | 0.0 | 0.0 | 2.0 | 334 | 0 | 0 | 0 | 0.0 | 0 |
| edd | Buildings | 498 | 0.0 | 0.0 | 0.0 | 498 | 0 | 0 | 0 | 0.0 | 0 |

Per distinct (instance, t_d) board:

| rule | boards | median % | p90 % | gap 0 | > 0.10 |
|---|---|---|---|---|---|
| atc | 411 | 0.0 | 0.0 | 391 | 2 |
| wspt | 411 | 0.0 | 14.6 | 262 | 60 |
| pfifo | 411 | 0.0 | 0.0 | 400 | 2 |
| edd | 411 | 0.0 | 0.0 | 400 | 2 |

Full-window anchor gap of each rule (t = 0, 60 instances; N6's Table 1 quantity, reproduced):

| rule | stratum | instances | median % | max % | above 0.20 |
|---|---|---|---|---|---|
| atc | All | 60 | 0.3 | 28.7 | 2 |
| atc | Primary | 24 | [4.0, 4.1] | 28.7 | 2 |
| atc | Confirmation | 12 | [0.1, 0.2] | 9.0 | 0 |
| atc | Buildings | 24 | 0.0 | 1.6 | 0 |
| wspt | All | 60 | 9.5 | 82.1 | 15 |
| wspt | Primary | 24 | 17.7 | 65.6 | 9 |
| wspt | Confirmation | 12 | 22.9 | 82.1 | 6 |
| wspt | Buildings | 24 | 0.0 | 8.8 | 0 |
| pfifo | All | 60 | 0.2 | 23.6 | 2 |
| pfifo | Primary | 24 | [3.2, 3.3] | 23.6 | 2 |
| pfifo | Confirmation | 12 | 0.1 | 10.7 | 0 |
| pfifo | Buildings | 24 | 0.0 | 1.9 | 0 |
| edd | All | 60 | 0.2 | 23.6 | 2 |
| edd | Primary | 24 | [3.2, 3.3] | 23.6 | 2 |
| edd | Confirmation | 12 | 0.1 | 10.7 | 0 |
| edd | Buildings | 24 | 0.0 | 1.9 | 0 |

## Pricing error against the known-board optimum (Table 14 twin)

Error = price - the decision-time oracle's cost on K; under = error below -0.05.

Absolute truth (cells: under % / median error):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS |
|---|---|---|---|---|---|
| atc | 0.0 / 0.000 | 0.7 / 0.000 | 2.4 / 0.000 | 0.7 / 0.000 | 2.4 / 0.000 |
| wspt | 0.0 / 0.000 | 13.8 / 0.000 | 14.3 / 0.000 | 12.9 / 0.000 | 14.1 / 0.000 |
| pfifo | 0.0 / 0.000 | 0.9 / 0.000 | 2.4 / 0.000 | 0.6 / 0.000 | 2.5 / 0.000 |
| edd | 0.0 / 0.000 | 0.9 / 0.000 | 2.4 / 0.000 | 0.6 / 0.000 | 2.5 / 0.000 |

Marginal truth (cells: under % / median error):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS |
|---|---|---|---|---|---|
| atc | 0.0 / 0.000 | 0.0 / 0.000 | 1.8 / 0.000 | 0.0 / 0.000 | 1.8 / 0.000 |
| wspt | 0.0 / 0.000 | 0.0 / 0.000 | 2.6 / 0.000 | 1.2 / 0.000 | 1.7 / 0.000 |
| pfifo | 0.0 / 0.000 | 0.0 / 0.000 | 1.8 / 0.000 | 0.0 / 0.000 | 1.8 / 0.000 |
| edd | 0.0 / 0.000 | 0.0 / 0.000 | 1.8 / 0.000 | 0.0 / 0.000 | 1.8 / 0.000 |

D-REL2 by stratum:

| rule | stratum | priced | absolute under % | marginal under % |
|---|---|---|---|---|
| atc | Primary | 706 | 1.3 | 0.0 |
| atc | Confirmation | 261 | 0.0 | 0.0 |
| atc | Buildings | 389 | 0.0 | 0.0 |
| wspt | Primary | 696 | 11.8 | 1.1 |
| wspt | Confirmation | 261 | 26.1 | 3.1 |
| wspt | Buildings | 389 | 6.2 | 0.0 |
| pfifo | Primary | 708 | 1.1 | 0.0 |
| pfifo | Confirmation | 261 | 0.0 | 0.0 |
| pfifo | Buildings | 389 | 0.0 | 0.0 |
| edd | Primary | 708 | 1.1 | 0.0 |
| edd | Confirmation | 261 | 0.0 | 0.0 |
| edd | Buildings | 389 | 0.0 | 0.0 |

## Dispositions against the known-board oracle (pricing panel of Table 16), delta = 0.10

Absolute cost on K (cells: miss % / FR %):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union | costly / cheap |
|---|---|---|---|---|---|---|---|
| atc | 6.6 / 0.0 | 7.1 / 0.0 | 0.0 / 4.5 | 0.0 / 0.4 | 0.0 / 4.7 | 0.0 / 0.4 | 196 / 1160 |
| wspt | 22.8 / 0.0 | 42.0 / 0.0 | 34.2 / 4.8 | 35.6 / 0.8 | 32.4 / 4.9 | 35.6 / 0.8 | 281 / 1065 |
| pfifo | 6.1 / 0.0 | 6.6 / 0.0 | 0.0 / 4.6 | 0.0 / 0.5 | 0.0 / 5.0 | 0.0 / 0.5 | 198 / 1160 |
| edd | 6.1 / 0.0 | 6.6 / 0.0 | 0.0 / 4.6 | 0.0 / 0.5 | 0.0 / 5.0 | 0.0 / 0.5 | 198 / 1160 |

Marginal cost on K (cells: miss % / FR %):

| rule | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union | costly / cheap |
|---|---|---|---|---|---|---|---|
| atc | 5.7 / 0.0 | 6.2 / 0.0 | 0.0 / 4.6 | 0.0 / 0.6 | 0.0 / 4.8 | 0.0 / 0.6 | 194 / 1162 |
| wspt | 3.4 / 3.8 | 8.9 / 0.0 | 1.1 / 5.1 | 1.1 / 1.0 | 1.1 / 5.6 | 1.1 / 1.0 | 179 / 1167 |
| pfifo | 5.1 / 0.0 | 5.6 / 0.0 | 0.0 / 4.7 | 0.0 / 0.7 | 0.0 / 5.2 | 0.0 / 0.7 | 196 / 1162 |
| edd | 5.1 / 0.0 | 5.6 / 0.0 | 0.0 / 4.7 | 0.0 / 0.7 | 0.0 / 5.2 | 0.0 / 0.7 | 196 / 1162 |

## Dispositions against the realised absolute cost (origabs), delta = 0.10

| rule | reading | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union | costly / cheap |
|---|---|---|---|---|---|---|---|---|
| atc | K | 39.8 / 0.0 | 40.1 / 0.0 | 35.2 / 4.8 | 37.2 / 1.0 | 34.9 / 4.9 | 37.2 / 1.0 | 304 / 1052 |
| atc | FI | 33.2 / 0.0 | 41.8 / 0.0 | 35.5 / 4.8 | 37.5 / 1.0 | 33.6 / 5.4 | 37.5 / 1.0 | 304 / 1052 |
| wspt | K | 75.9 / 2.1 | 81.0 / 0.0 | 74.6 / 3.7 | 78.0 / 0.0 | 74.2 / 4.1 | 78.0 / 0.0 | 859 / 486 |
| wspt | FI | 45.1 / 0.0 | 81.6 / 0.0 | 74.7 / 3.7 | 78.1 / 0.0 | 72.8 / 4.7 | 78.1 / 0.0 | 859 / 486 |
| pfifo | K | 43.6 / 0.0 | 43.9 / 0.0 | 39.7 / 5.1 | 41.5 / 1.1 | 39.7 / 5.5 | 41.5 / 1.1 | 330 / 1028 |
| pfifo | FI | 36.4 / 0.0 | 45.8 / 0.0 | 39.7 / 5.1 | 41.5 / 1.1 | 39.7 / 5.7 | 41.5 / 1.1 | 330 / 1028 |
| edd | K | 43.6 / 0.0 | 43.9 / 0.0 | 39.7 / 5.1 | 41.5 / 1.1 | 39.7 / 5.5 | 41.5 / 1.1 | 330 / 1028 |
| edd | FI | 36.4 / 0.0 | 45.8 / 0.0 | 39.7 / 5.1 | 41.5 / 1.1 | 39.7 / 5.7 | 41.5 / 1.1 | 330 / 1028 |

## Costly proposals D-REL2 applies and the certificate refers (delta = 0.10)

| rule | truth | reading | costly | G-CERT refers, D-REL2 applies | G-CERT-M refers, D-REL2 applies | D-REL2 refers, G-CERT-M applies | cheap | G-CERT refers cheap, D-REL2 not | G-CERT-M refers cheap, D-REL2 not |
|---|---|---|---|---|---|---|---|---|---|
| atc | kabs | K | 196 | 0 | 0 | 14 | 1160 | 0 | 0 |
| atc | kabs | FI | 196 | 0 | 0 | 19 | 1160 | 24 | 0 |
| atc | origabs | K | 304 | 0 | 0 | 9 | 1052 | 0 | 0 |
| atc | origabs | FI | 304 | 24 | 0 | 13 | 1052 | 0 | 0 |
| atc | orig | K | 208 | 0 | 0 | 5 | 1148 | 0 | 0 |
| atc | orig | FI | 208 | 1 | 0 | 10 | 1148 | 23 | 0 |
| wspt | kabs | K | 281 | 46 | 0 | 18 | 1065 | 0 | 0 |
| wspt | kabs | FI | 281 | 59 | 0 | 23 | 1065 | 243 | 0 |
| wspt | origabs | K | 859 | 36 | 0 | 26 | 486 | 10 | 0 |
| wspt | origabs | FI | 859 | 302 | 0 | 30 | 486 | 0 | 0 |
| wspt | orig | K | 200 | 0 | 0 | 14 | 1146 | 46 | 0 |
| wspt | orig | FI | 200 | 4 | 0 | 19 | 1146 | 298 | 0 |
| pfifo | kabs | K | 198 | 0 | 0 | 13 | 1160 | 0 | 0 |
| pfifo | kabs | FI | 198 | 0 | 0 | 19 | 1160 | 27 | 0 |
| pfifo | origabs | K | 330 | 0 | 0 | 8 | 1028 | 0 | 0 |
| pfifo | origabs | FI | 330 | 27 | 0 | 14 | 1028 | 0 | 0 |
| pfifo | orig | K | 209 | 0 | 0 | 2 | 1149 | 0 | 0 |
| pfifo | orig | FI | 209 | 2 | 0 | 8 | 1149 | 25 | 0 |
| edd | kabs | K | 198 | 0 | 0 | 13 | 1160 | 0 | 0 |
| edd | kabs | FI | 198 | 0 | 0 | 19 | 1160 | 27 | 0 |
| edd | origabs | K | 330 | 0 | 0 | 8 | 1028 | 0 | 0 |
| edd | origabs | FI | 330 | 27 | 0 | 14 | 1028 | 0 | 0 |
| edd | orig | K | 209 | 0 | 0 | 2 | 1149 | 0 | 0 |
| edd | orig | FI | 209 | 2 | 0 | 8 | 1149 | 25 | 0 |

## Populations and the decision instant under each rule

| rule | issuable (N11) | priced on K | named order started by t_d | names running work | not issuable under the rule | stopped before the quality stage | priced and issuable under the rule |
|---|---|---|---|---|---|---|---|
| atc | 1723 | 1356 | 0 | 0 | 0 | 367 | 1356 |
| wspt | 1723 | 1346 | 11 | 0 | 11 | 377 | 1346 |
| pfifo | 1723 | 1358 | 6 | 6 | 6 | 365 | 1358 |
| edd | 1723 | 1358 | 6 | 6 | 6 | 365 | 1358 |

Sensitivity on the items also issuable under the rule (K and FI, orig, delta 0.10, miss / FR %):

| rule | reading | G-CERT | G-CERT-M | D-REL1 | D-REL2 | D-ABS | Union |
|---|---|---|---|---|---|---|---|
| atc | K | 12.0 / 0.0 | 12.5 / 0.0 | 10.1 / 5.3 | 10.1 / 1.2 | 9.6 / 5.4 | 10.1 / 1.2 |
| atc | FI | 13.5 / 2.0 | 14.9 / 0.0 | 10.1 / 5.2 | 10.1 / 1.1 | 9.1 / 6.1 | 10.1 / 1.1 |
| wspt | K | 14.5 / 4.0 | 18.5 / 0.0 | 11.5 / 5.1 | 11.5 / 1.0 | 11.5 / 5.7 | 11.5 / 1.0 |
| wspt | FI | 14.0 / 26.2 | 21.0 / 0.0 | 11.5 / 5.1 | 11.5 / 1.0 | 10.0 / 6.8 | 11.5 / 1.0 |
| pfifo | K | 11.5 / 0.1 | 11.5 / 0.0 | 10.5 / 5.6 | 10.5 / 1.5 | 10.5 / 6.0 | 10.5 / 1.5 |
| pfifo | FI | 12.0 / 2.3 | 14.4 / 0.0 | 10.5 / 5.6 | 10.5 / 1.5 | 10.5 / 6.2 | 10.5 / 1.5 |
| edd | K | 11.5 / 0.1 | 11.5 / 0.0 | 10.5 / 5.6 | 10.5 / 1.5 | 10.5 / 6.0 | 10.5 / 1.5 |
| edd | FI | 12.0 / 2.3 | 14.4 / 0.0 | 10.5 / 5.6 | 10.5 / 1.5 | 10.5 / 6.2 | 10.5 / 1.5 |

## Oracle on the known boards

| rule | boards | complete | proved | trades closed by LB2 | trades reusing N11 | trades solved by N14 | max width_rel |
|---|---|---|---|---|---|---|---|
| atc | 879 | 879 | 879 | 9684 | 26 | 0 | 0.0003 |
| wspt | 879 | 879 | 879 | 9599 | 9 | 102 | 0.0007 |
| pfifo | 886 | 886 | 886 | 9788 | 5 | 11 | 0.0003 |
| edd | 886 | 886 | 886 | 9788 | 5 | 11 | 0.0003 |

Solve stage: 85 distinct trades solved ({'atc': 26, 'edd': 5, 'pfifo': 5, 'wspt': 9} reused from N11 by content), 0 re-solves, wall 321 s, cores [8, 9, 10, 11], 4 CP-SAT workers, budget 60.0 s. Budget-limited rows: 0. Max foreign_share on a budget-limited row: none. cpu_share (whole call) median 0.513; recorded on every row, not the validity test (foreign_share > 0.10 is).

## Assertions

- `atc`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 1356 covered rows).
- `wspt`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 1346 covered rows).
- `pfifo`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 1358 covered rows).
- `edd`: the certificate never under-prices g on K (minimum margin over the optimistic end 0.000000; 1358 covered rows).
- Control reproduction (R10): {"consequence_cells": 2268, "pricing_cells": 330, "wins_cells": 1692, "brackets": 879}.
- Analyse checks by group: {"A1": 2, "R10": 120025, "R9": 19954}.

