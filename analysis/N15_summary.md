# N15: composition of the scored sets (l1-n15-composition-1)

Direct benchmark at the decision instant, 1356 priced proposals, 255 without operations, 655 with a known-board bound of at least one weighted bh.

## delta = 0.20: 186 costly, 1170 low-cost (915 with operations)

Costly by class: {'V3': 132, 'V4': 54}; by edit type: {'sequencing_only': 126, 'field_changing': 60}.
Low-cost by class: {'benign': 623, 'V1': 30, 'V3': 22, 'V4': 146, 'V5': 200, 'V6': 149}; by edit type: {'field_changing': 471, 'sequencing_only': 444, 'empty': 255}.

| design | check | applied K | field edits among them | applied FI | applied under both | referred K | of them benign | share | share over proposals with operations | referred FI |
|---|---|---|---|---|---|---|---|---|---|---|
| G-CERT | first price | 18/186 | 18 | 18 | 18 | 15/1170 | 0 | 1.3% | 1.6% | 35 |
| G-CERT | with the second price on field edits | 0/186 | 0 |  |  | 22/1170 | 0 | 1.9% | 2.4% |  |
| G-CERT-M | first price | 18/186 | 18 | 18 | 18 | 14/1170 | 0 | 1.2% | 1.5% | 9 |
| G-CERT-M | with the second price on field edits | 0/186 | 0 |  |  | 21/1170 | 0 | 1.8% | 2.3% |  |
| D-REL1 | first price | 18/186 | 18 | 18 | 18 | 80/1170 | 33 | 6.8% | 8.7% | 79 |
| D-REL1 | with the second price on field edits | 0/186 | 0 |  |  | 86/1170 | 33 | 7.4% | 9.4% |  |
| D-REL2 | first price | 18/186 | 18 | 18 | 18 | 33/1170 | 1 | 2.8% | 3.6% | 32 |
| D-REL2 | with the second price on field edits | 0/186 | 0 |  |  | 40/1170 | 1 | 3.4% | 4.4% |  |
| D-ABS | first price | 17/186 | 17 | 16 | 16 | 81/1170 | 34 | 6.9% | 8.9% | 89 |
| D-ABS | with the second price on field edits | 0/186 | 0 |  |  | 87/1170 | 34 | 7.4% | 9.5% |  |

Proposals with a known-board bound of at least one weighted bh: 181 costly, 474 low-cost.

| design | applied K | applied FI | referred K | referred FI |
|---|---|---|---|---|
| G-CERT | 18/181 | 18/181 | 15/474 | 15/474 |
| G-CERT-M | 18/181 | 18/181 | 14/474 | 9/474 |
| D-REL1 | 18/181 | 18/181 | 80/474 | 79/474 |
| D-REL2 | 18/181 | 18/181 | 33/474 | 32/474 |
| D-ABS | 17/181 | 16/181 | 81/474 | 85/474 |

## delta = 0.10: 208 costly, 1148 low-cost (893 with operations)

Costly by class: {'V3': 144, 'V4': 64}; by edit type: {'sequencing_only': 144, 'field_changing': 64}.
Low-cost by class: {'benign': 623, 'V1': 30, 'V4': 136, 'V5': 200, 'V6': 149, 'V3': 10}; by edit type: {'field_changing': 467, 'sequencing_only': 426, 'empty': 255}.

| design | check | applied K | field edits among them | applied FI | applied under both | referred K | of them benign | share | share over proposals with operations | referred FI |
|---|---|---|---|---|---|---|---|---|---|---|
| G-CERT | first price | 25/208 | 21 | 28 | 23 | 0/1148 | 0 | 0.0% | 0.0% | 23 |
| G-CERT | with the second price on field edits | 6/208 | 2 |  |  | 6/1148 | 0 | 0.5% | 0.7% |  |
| G-CERT-M | first price | 26/208 | 21 | 31 | 25 | 0/1148 | 0 | 0.0% | 0.0% | 0 |
| G-CERT-M | with the second price on field edits | 7/208 | 2 |  |  | 6/1148 | 0 | 0.5% | 0.7% |  |
| D-REL1 | first price | 21/208 | 21 | 21 | 21 | 61/1148 | 33 | 5.3% | 6.8% | 60 |
| D-REL1 | with the second price on field edits | 2/208 | 2 |  |  | 66/1148 | 33 | 5.7% | 7.4% |  |
| D-REL2 | first price | 21/208 | 21 | 21 | 21 | 14/1148 | 1 | 1.2% | 1.6% | 13 |
| D-REL2 | with the second price on field edits | 2/208 | 2 |  |  | 20/1148 | 1 | 1.7% | 2.2% |  |
| D-ABS | first price | 20/208 | 20 | 19 | 19 | 62/1148 | 34 | 5.4% | 6.9% | 70 |
| D-ABS | with the second price on field edits | 2/208 | 2 |  |  | 67/1148 | 34 | 5.8% | 7.5% |  |

Proposals with a known-board bound of at least one weighted bh: 203 costly, 452 low-cost.

| design | applied K | applied FI | referred K | referred FI |
|---|---|---|---|---|
| G-CERT | 25/203 | 28/203 | 0/452 | 3/452 |
| G-CERT-M | 26/203 | 31/203 | 0/452 | 0/452 |
| D-REL1 | 21/203 | 21/203 | 61/452 | 60/452 |
| D-REL2 | 21/203 | 21/203 | 14/452 | 13/452 |
| D-ABS | 20/203 | 19/203 | 62/452 | 66/452 |

## Four dispatching rules (analysis/N14_rows.csv)

delta = 0.20

| rule | design | applied K | applied FI | applied under both | referred K |
|---|---|---|---|---|---|
| atc | G-CERT | 18/186 | 18 | 18 | 15/1170 |
| atc | G-CERT-M | 18/186 | 18 | 18 | 14/1170 |
| atc | D-REL1 | 18/186 | 18 | 18 | 80/1170 |
| atc | D-REL2 | 18/186 | 18 | 18 | 33/1170 |
| atc | D-ABS | 17/186 | 16 | 16 | 81/1170 |
| wspt | G-CERT | 16/164 | 14 | 14 | 69/1182 |
| wspt | G-CERT-M | 16/164 | 16 | 16 | 15/1182 |
| wspt | D-REL1 | 16/164 | 16 | 16 | 88/1182 |
| wspt | D-REL2 | 16/164 | 16 | 16 | 41/1182 |
| wspt | D-ABS | 16/164 | 14 | 14 | 94/1182 |
| pfifo | G-CERT | 15/191 | 15 | 15 | 10/1167 |
| pfifo | G-CERT-M | 15/191 | 15 | 15 | 9/1167 |
| pfifo | D-REL1 | 15/191 | 15 | 15 | 75/1167 |
| pfifo | D-REL2 | 15/191 | 15 | 15 | 28/1167 |
| pfifo | D-ABS | 15/191 | 15 | 15 | 80/1167 |
| edd | G-CERT | 15/191 | 15 | 15 | 10/1167 |
| edd | G-CERT-M | 15/191 | 15 | 15 | 9/1167 |
| edd | D-REL1 | 15/191 | 15 | 15 | 75/1167 |
| edd | D-REL2 | 15/191 | 15 | 15 | 28/1167 |
| edd | D-ABS | 15/191 | 15 | 15 | 80/1167 |

delta = 0.10

| rule | design | applied K | applied FI | applied under both | referred K |
|---|---|---|---|---|---|
| atc | G-CERT | 25/208 | 28 | 23 | 0/1148 |
| atc | G-CERT-M | 26/208 | 31 | 25 | 0/1148 |
| atc | D-REL1 | 21/208 | 21 | 21 | 61/1148 |
| atc | D-REL2 | 21/208 | 21 | 21 | 14/1148 |
| atc | D-ABS | 20/208 | 19 | 19 | 62/1148 |
| wspt | G-CERT | 29/200 | 28 | 24 | 46/1146 |
| wspt | G-CERT-M | 37/200 | 42 | 35 | 0/1146 |
| wspt | D-REL1 | 23/200 | 23 | 23 | 59/1146 |
| wspt | D-REL2 | 23/200 | 23 | 23 | 12/1146 |
| wspt | D-ABS | 23/200 | 20 | 20 | 65/1146 |
| pfifo | G-CERT | 24/209 | 25 | 22 | 1/1149 |
| pfifo | G-CERT-M | 24/209 | 30 | 24 | 0/1149 |
| pfifo | D-REL1 | 22/209 | 22 | 22 | 64/1149 |
| pfifo | D-REL2 | 22/209 | 22 | 22 | 17/1149 |
| pfifo | D-ABS | 22/209 | 22 | 22 | 69/1149 |
| edd | G-CERT | 24/209 | 25 | 22 | 1/1149 |
| edd | G-CERT-M | 24/209 | 30 | 24 | 0/1149 |
| edd | D-REL1 | 22/209 | 22 | 22 | 64/1149 |
| edd | D-REL2 | 22/209 | 22 | 22 | 17/1149 |
| edd | D-ABS | 22/209 | 22 | 22 | 69/1149 |


60 assertions passed; 665 macros.
