# L1 violation suite v0.2 - statistics

Total items: **2000**.  Config fingerprint `17dbb217f1b10be5`.

## Items per set and class
| set | class | c09_storm2_w80 | c10_storm2_w80 | c10_replay_400 | total |
|---|---|---|---|---|---|
| benign | benign | 394 | 153 | 253 | 800 |
| violation | V1 | 67 | 32 | 61 | 160 |
| violation | V2 | 111 | 40 | 49 | 200 |
| violation | V3 | 114 | 41 | 65 | 220 |
| violation | V4 | 102 | 40 | 78 | 220 |
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
| V3/reorder_behind_batch_member | 15 |
| V3/reorder_block_tight | 70 |
| V3/reorder_cross_trade | 45 |
| V3/reorder_two_successors | 45 |
| V3/window_blocked_predecessor | 45 |
| V4/freeze_instead_of_pin | 25 |
| V4/objective_shifting | 40 |
| V4/priority_instead_of_window | 25 |
| V4/reorder_direction_flipped | 50 |
| V4/sign_flipped_shift | 40 |
| V4/wrong_building_same_trade | 15 |
| V4/wrong_order_same_building | 25 |
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
| benign/dangling_building_id | 20 |
| benign/dangling_order_id | 60 |
| benign/enum_invalid_trade | 10 |
| benign/freeze_instead_of_pin | 25 |
| benign/freeze_shift_contradiction | 50 |
| benign/frozen_order_edit | 40 |
| benign/not_frozen | 25 |
| benign/objective_shifting | 40 |
| benign/out_of_range_shift | 30 |
| benign/priority_instead_of_window | 25 |
| benign/reorder_behind_batch_member | 15 |
| benign/reorder_block_tight | 70 |
| benign/reorder_cross_trade | 45 |
| benign/reorder_cycle | 60 |
| benign/reorder_direction_flipped | 50 |
| benign/reorder_two_successors | 45 |
| benign/sign_flipped_shift | 40 |
| benign/trade_mismatch | 25 |
| benign/unknown_op | 20 |
| benign/unstaffed_trade | 20 |
| benign/window_blocked_predecessor | 45 |
| benign/wrong_building_same_trade | 15 |
| benign/wrong_order_same_building | 25 |

## Coverage matrix (operation type x class x stratum)
Cells are item counts; `.` means the combination is not generated (see the report for which combinations are impossible).
| operation | class | c09_storm2_w80 | c10_storm2_w80 | c10_replay_400 |
|---|---|---|---|---|
| set_priority | benign | 33 | 12 | 15 |
| set_priority | V1 | 33 | 12 | 15 |
| pin_next | benign | 91 | 44 | 33 |
| pin_next | V1 | 39 | 22 | 17 |
| pin_next | V2 | 14 | 5 | 6 |
| pin_next | V4 | 38 | 17 | 10 |
| reorder | benign | 175 | 63 | 92 |
| reorder | V2 | 33 | 12 | 15 |
| reorder | V3 | 114 | 41 | 65 |
| reorder | V4 | 28 | 10 | 12 |
| reassign_window | benign | 128 | 46 | 81 |
| reassign_window | V1 | 17 | 6 | 7 |
| reassign_window | V2 | 50 | 18 | 22 |
| reassign_window | V3 | 25 | 9 | 11 |
| reassign_window | V4 | 36 | 13 | 41 |
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
| set_priority | 60 |
| pin_next | 168 |
| reorder | 330 |
| reassign_window | 255 |
| freeze | 70 |
| unfreeze | 25 |
| batch | 62 |

| operations per item | items |
|---|---|
| 1 | 525 |
| 2 | 275 |

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

## V3 candidates: schedule degradation by subclass
`badness` is weighted tardiness on the adjusted instance under the item's operations, minus the same instance dispatched with nothing imposed, in weighted business hours. It measures schedule degradation rather than movement of the objective's own fields, which is what an adjusted-instance certificate can see. Certified severity is assigned in the guard pass.
| subclass | n | badness > 0 | median | max |
|---|---|---|---|---|
| reorder_behind_batch_member | 15 | 15 | 48.0 | 374.2152 |
| reorder_block_tight | 70 | 70 | 248.256 | 814.12 |
| reorder_cross_trade | 45 | 45 | 226.884 | 774.876 |
| reorder_two_successors | 45 | 45 | 516.8496 | 1651.9752 |
| window_blocked_predecessor | 45 | 45 | 343.0068 | 941.8944 |

**V3 positive-badness share: 220/220 = 100.0%.**

Benign twins for comparison: 8 of 800 degrade the schedule at all, median 0.0.

## V4 traps: provisional quality separation by trap type
`median delta` is badness(trap) minus badness(gold). A trap that only moves the objective's own fields scores zero by construction and is caught by the matched twin alone, which is a reported finding rather than a defect.
| trap type | n | quality-visible candidates | schedule differs | median delta |
|---|---|---|---|---|
| freeze_instead_of_pin | 25 | 0 | 19 | 0.0 |
| objective_shifting | 40 | 5 | 21 | 0.0 |
| priority_instead_of_window | 25 | 0 | 25 | 0.0 |
| reorder_direction_flipped | 50 | 50 | 50 | 213.9396 |
| sign_flipped_shift | 40 | 0 | 40 | 0.0 |
| wrong_building_same_trade | 15 | 0 | 14 | 0.0 |
| wrong_order_same_building | 25 | 0 | 25 | 0.0 |

## Surface form
| register | items | median words | min | max |
|---|---|---|---|---|
| conversational | 581 | 17 | 7 | 34 |
| formal | 825 | 19 | 6 | 49 |
| terse | 594 | 11.0 | 4 | 24 |

Instruction length over the whole suite: 18 to 288 characters (median 86.0), 4 to 49 words (median 16.0).

## Queue state of the targeted trade
| stratum | deep | moderate | not_applicable | shallow |
|---|---|---|---|---|
| c09_storm2_w80 | 555 | 424 | 17 | 13 |
| c10_storm2_w80 | 201 | 179 | 6 | 0 |
| c10_replay_400 | 0 | 214 | 7 | 384 |
