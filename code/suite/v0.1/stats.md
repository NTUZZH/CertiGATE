# L1 violation suite v0.1 - statistics

Total items: **2000**.  Config fingerprint `3ed4dd9457e82f7a`.

## Items per set and class
| set | class | c09_storm2_w80 | c10_storm2_w80 | c10_replay_150 | total |
|---|---|---|---|---|---|
| benign | benign | 391 | 155 | 254 | 800 |
| violation | V1 | 67 | 32 | 61 | 160 |
| violation | V2 | 111 | 40 | 49 | 200 |
| violation | V3 | 116 | 45 | 59 | 220 |
| violation | V4 | 97 | 38 | 85 | 220 |
| ambiguity | V5 | 111 | 40 | 49 | 200 |
| adversarial | V6 | 110 | 40 | 50 | 200 |

## Items per subclass
| class/subclass | n |
|---|---|
| V1/dangling_building_id | 20 |
| V1/dangling_order_id | 60 |
| V1/enum_invalid_trade | 10 |
| V1/out_of_range_shift | 30 |
| V1/unknown_op | 20 |
| V1/unstaffed_trade | 20 |
| V2/freeze_shift_contradiction | 50 |
| V2/frozen_order_edit | 40 |
| V2/not_frozen | 25 |
| V2/reorder_cycle | 60 |
| V2/trade_mismatch | 25 |
| V3/batch_low_priority_group | 15 |
| V3/delay_urgent | 70 |
| V3/demote_urgent | 45 |
| V3/pin_long_low_priority | 25 |
| V3/reorder_block_tight | 65 |
| V4/freeze_instead_of_pin | 30 |
| V4/priority_instead_of_window | 40 |
| V4/reorder_direction_flipped | 45 |
| V4/sign_flipped_shift | 55 |
| V4/wrong_building_same_trade | 15 |
| V4/wrong_order_same_building | 35 |
| V5/ambiguous_referent | 60 |
| V5/conflicting_directives | 40 |
| V5/open_ended_overreach | 20 |
| V5/unquantified_magnitude | 50 |
| V5/unscoped_scope | 30 |
| V6/embedded_injection | 45 |
| V6/instruction_override | 55 |
| V6/payload_smuggling | 35 |
| V6/role_confusion | 40 |
| V6/schema_subversion | 25 |
| benign/batch_low_priority_group | 15 |
| benign/dangling_building_id | 20 |
| benign/dangling_order_id | 60 |
| benign/delay_urgent | 70 |
| benign/demote_urgent | 45 |
| benign/enum_invalid_trade | 10 |
| benign/freeze_instead_of_pin | 30 |
| benign/freeze_shift_contradiction | 50 |
| benign/frozen_order_edit | 40 |
| benign/not_frozen | 25 |
| benign/out_of_range_shift | 30 |
| benign/pin_long_low_priority | 25 |
| benign/priority_instead_of_window | 40 |
| benign/reorder_block_tight | 65 |
| benign/reorder_cycle | 60 |
| benign/reorder_direction_flipped | 45 |
| benign/sign_flipped_shift | 55 |
| benign/trade_mismatch | 25 |
| benign/unknown_op | 20 |
| benign/unstaffed_trade | 20 |
| benign/wrong_building_same_trade | 15 |
| benign/wrong_order_same_building | 35 |

## Coverage matrix (operation type x class x stratum)
Cells are item counts; `.` means the combination is not generated (see the report for which combinations are impossible).
| operation | class | c09_storm2_w80 | c10_storm2_w80 | c10_replay_150 |
|---|---|---|---|---|
| set_priority | benign | 58 | 21 | 26 |
| set_priority | V1 | 33 | 12 | 15 |
| set_priority | V3 | 25 | 9 | 11 |
| pin_next | benign | 89 | 46 | 23 |
| pin_next | V1 | 39 | 22 | 17 |
| pin_next | V2 | 14 | 5 | 6 |
| pin_next | V3 | 16 | 9 | . |
| pin_next | V4 | 20 | 10 | . |
| reorder | benign | 94 | 34 | 42 |
| reorder | V2 | 33 | 12 | 15 |
| reorder | V3 | 36 | 13 | 16 |
| reorder | V4 | 25 | 9 | 11 |
| reassign_window | benign | 158 | 57 | 105 |
| reassign_window | V1 | 17 | 6 | 7 |
| reassign_window | V2 | 50 | 18 | 22 |
| reassign_window | V3 | 39 | 14 | 17 |
| reassign_window | V4 | 52 | 19 | 59 |
| freeze | benign | 39 | 14 | 17 |
| freeze | V1 | 11 | 4 | 5 |
| freeze | V2 | 28 | 10 | 12 |
| unfreeze | benign | 14 | 5 | 6 |
| unfreeze | V2 | 14 | 5 | 6 |
| batch | benign | . | . | 62 |
| batch | V1 | . | . | 32 |
| batch | V3 | . | . | 15 |
| batch | V4 | . | . | 15 |

## Benign set: operation coverage and operation count
| operation | items |
|---|---|
| set_priority | 105 |
| pin_next | 158 |
| reorder | 170 |
| reassign_window | 320 |
| freeze | 70 |
| unfreeze | 25 |
| batch | 62 |

| operations per item | items |
|---|---|
| 1 | 577 |
| 2 | 209 |
| 3 | 14 |

## Expected violation codes (V1, V2)
| code | items |
|---|---|
| ArgumentOutOfRange | 30 |
| CyclicPrecedence | 60 |
| DanglingBuildingID | 20 |
| DanglingOrderID | 60 |
| FrozenWindowConflict | 90 |
| NotFrozen | 25 |
| SchemaViolation | 30 |
| TradeMismatch | 25 |
| UnknownTrade | 20 |

V1 decoder split: decoder_absorbable 30, guard_requiring 130

## V3 candidates: heuristic badness by subclass
`badness` is the relative rise in weighted tardiness against the instance's own deadlines, versus doing nothing in the same episode. Certified severity is assigned in the guard pass.
| subclass | n | badness > 0 | median | max |
|---|---|---|---|---|
| batch_low_priority_group | 15 | 0 | 0.0 | 0.0 |
| delay_urgent | 70 | 67 | 1.0491 | 1436.0 |
| demote_urgent | 45 | 17 | 0.0 | 0.5028 |
| pin_long_low_priority | 25 | 1 | 0.0 | 0.0285 |
| reorder_block_tight | 65 | 41 | 0.0915 | 13.302 |

Benign twins for comparison: 20 of 800 have badness > 0, median 0.0.

## V4 traps: provisional quality separation by subclass
| subclass | n | quality-visible candidates | schedule differs | median delta |
|---|---|---|---|---|
| freeze_instead_of_pin | 30 | 6 | 18 | 0.0 |
| priority_instead_of_window | 40 | 4 | 40 | 0.0 |
| reorder_direction_flipped | 45 | 38 | 45 | 248.5208 |
| sign_flipped_shift | 55 | 34 | 55 | 118.0 |
| wrong_building_same_trade | 15 | 0 | 15 | 0.0 |
| wrong_order_same_building | 35 | 0 | 35 | 0.0 |

## Surface form
| register | items | median words | min | max |
|---|---|---|---|---|
| conversational | 583 | 17 | 7 | 34 |
| formal | 819 | 19 | 6 | 49 |
| terse | 598 | 10.0 | 4 | 24 |

Instruction length over the whole suite: 15 to 285 characters (median 85.0), 4 to 49 words (median 16.0).

## Queue state of the targeted trade
| stratum | deep | moderate | not_applicable | shallow |
|---|---|---|---|---|
| c09_storm2_w80 | 582 | 399 | 17 | 5 |
| c10_storm2_w80 | 256 | 128 | 6 | 0 |
| c10_replay_150 | 0 | 48 | 7 | 552 |
