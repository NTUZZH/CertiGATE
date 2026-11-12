# N26 design (frozen): a time-window shift that keeps the due date

Version l1-n26-shift-1. Design pre-specified before the run.
Post hoc sensitivity analysis, reported whichever way it falls. This file is written and its
sha256 recorded before any dispatch under convention D. Later choices go to addendum.md in this
folder; this file is never edited.

## 1. The two conventions

- B (benchmark): `reassign_window(order, shift)` sets `release' = max(0, release + shift)` and
  `due' = release' + SLA_BH[priority]` (code/l1adapter/apply.py, frozen v1.0.0 semantics).
- D (due date kept): the same operation sets `release' = max(0, release + shift)` and leaves the
  due date as it stands when the operation is applied. Nothing else changes: `set_priority`
  still sets weight and `due = release + SLA_BH[c]` from the release it sees, operations still
  apply in their listed order, precedence stays start-after-start, batch groups still sort by
  the final due dates, the frozen-window check still reads the shifted release, and the
  guard's stages, ATC, seed 0, the frozen set "fix", the bound (release-aware LB2 on the board
  the guard is given) and the floor are those of the benchmark.
- Implementation without editing any file under code/l1adapter/ or any frozen script:
  `apply.apply_operations` is compiled again from its own source with one textual change (the
  due-date line of the `reassign_window` branch runs only when a switch is off; asserted to
  occur exactly once). The module attributes `l1adapter.apply.apply_operations` and
  `l1adapter.apply_operations` point to the patched function only while a D board is priced.
- Probes on micro-instances before any replay (run-fatal): (a) the patched function with the
  switch off gives the unpatched module's adjusted instance and schedule byte for byte;
  (b) with the switch on, a shift moves the release and leaves the due date at its original
  value, and a `set_priority` before or after the shift behaves as stated above; (c) a
  proposal without a `reassign_window` gives the identical adjusted instance and schedule with
  the switch on and off.

## 2. Population

- Suite: the 1,356 priced reference proposals of the direct benchmark (n20.build's records, as
  N24 and N25 use them). Of these, the proposals whose reference proposal
  (n11_decision_time.canonical_ops) carries a `reassign_window` are replayed under B and D.
- New draws: the 3,733 priced held-out reference proposals of the three fresh suites (seeds
  20261110, 20261111, 20261112; rows of analysis/N17_rows.csv with `held_out` True), with
  records built by n17_heldout.build_records from the stored replays in
  results/n17_heldout/replay/<seed>/. The same selection of shift proposals is replayed.
- Proposals without a `reassign_window` keep their B values. A seeded sample of 50 of them
  (random.Random(20261111), drawn from the suite and the new draws pooled) is replayed under
  B and D and asserted identical on all three boards.
- Reference proposals that carry a `reassign_window` and are not priced (refused by a check or
  not issuable), in the suite and in the three fresh suites, are replayed on the known board
  and with full information under B and D. They are reported separately, with whether the
  refusal depends on the convention.

## 3. Boards and recomputed quantities (for every replayed proposal, under B and under D)

Boards as in the direct benchmark (n11_decision_time census and n11_forecast reading FI, the
construction that N23 and N25 restate): the known board K at the decision instant t_d, the
full-information board FI at t_d, and the realised whole-window run from t_d. Every board is
priced by n11_decision_time.gen_price. Recomputed with the functions the published numbers
came from:

- the schema and feasibility outcome on K and FI;
- the objective on the edited values and on the original values on K and FI;
- the certificate price `certified_gap(obj, lb, floor 1.0)` with the bound gen_price computes
  on the board it is given (LB2 depends on due dates, so under D it is the bound of the D
  board; under B it is asserted equal to the logged bound); the marginal certificate (minus
  the no-proposal gap of the site), D-REL1, D-REL2 and D-ABS at their own thresholds (0.20,
  0.20, 0.02, 0.02, 0.8119 weighted bh);
- the full-information price, the same way on FI;
- the second price on field edits, `g_orig = (obj_orig - lb_anchor) / max(lb_anchor, 1)` on K
  (tau 0.20; n16.sp_flag), and the same rule with full information (FI anchor bound);
- the realised run on the whole window, its objective on the original values and its damage
  against the unchanged no-proposal run (the no-AI anchor).

The no-proposal runs of each site carry no operation, so they are the same under B and D.

## 4. Labels

Unchanged rule: a proposal is costly at delta when the lower end of its realised-cost interval
(damage on the original values over the larger of the floor and the full-window optimum of the
untouched instance, with the stored bracket of the window) exceeds delta, low-cost when the
upper end is at most delta, undecided otherwise (n11_decision_time.attach_truth,
n13.costly_of). delta = 0.20 (headline) and 0.10. The bracket does not depend on the
convention, so no solver runs. If any quantity needed a new bracket the run would stop.

## 5. Checks before any D number is read (run-fatal)

- The four frozen files keep their sha256 prefixes (n16_robustness.py 39e5dc3e0bae,
  n13_fromlogs.py 60e4deec5d8e, n11_decision_time.py 83d5217b291c, n10_field_change.py
  ac4dd5db85b4); nothing under code/l1adapter/ changes (sha256 before and after).
- B from the stored records reproduces the frozen counts. Suite: 1,356 priced; at 0.20, 186
  costly, 168 referred on K and the same 168 with FI, 18 applied, 0 applied with the second
  price, 15 and 22 low-cost referred of 1,170; at 0.10, 208 costly, 25 applied on K, 28 with
  FI, 6 with the second price. New draws: 3,733 priced; at 0.20, 529 costly, 45 applied, 4
  applied with the second price, 65 and 98 low-cost referred of 3,204.
- The B replay of every shift proposal reproduces its stored values: on K the terminals,
  codes, both objectives, the bound, the certificate and the D-REL2 reference; on FI the stored
  full-information record; on the realised run the terminals and both objectives; the damage,
  the realised-cost interval, the label at 0.20 and 0.10, every design's price and flag on K
  and FI, and the second price on K (and on FI for the suite). Tolerance 1e-9 on full-precision
  fields, 1e-6 on fields read from a six-decimal file.
- Under D every schedule is complete. On every D board each shifted order's due date equals
  its due date before the operation, and its release equals the B release.

## 6. Reported (suite and new draws pooled, delta 0.20 and 0.10, B beside D)

1. priced, costly, low-cost;
2. costly referred by the certificate on K, with FI, under both; costly applied on K and with
   FI;
3. the same with the second price on field edits (K and FI);
4. low-cost referred on K, alone and with the second price (count, share and the n2 cluster
   bootstrap interval: seed 20261026, 20,000 replicates, 60 instance clusters; for the new
   draws the three seeds' rows of an instance form one cluster);
5. the fate under D of the costly proposals the certificate applies under B at 0.20 (suite 18,
   new draws 45): costly or not, referred or applied by the certificate on K and with FI, by
   the second price, split by template family (v4_sign_flipped_shift, v4_objective_shifting);
6. correct translations that carry a shift (classes benign and V3, whose reference proposal is
   the recorded reading): how many the certificate refers on K (and with FI) under B and D,
   and how many of those are low-cost, per class;
7. label changes between B and D in each direction, and how many K, FI and realised schedules
   differ;
plus the change in realised damage (D minus B: median, p10, p90, min, max, share lower and
higher), the unpriced shift proposals, and a self-test on a second code path for at least ten
headline numbers.

## 7. Outputs

code/scripts/n26_shift_keeps_due.py (with --selftest); analysis/N26_rows.csv;
analysis/N26_numbers.json; analysis/N26_summary.md; analysis/N26_macros.tex (prefix
\nTwentySix, suffix B or D for the convention, one comment line per macro) copied byte for
byte to manuscript/macros_n26.tex; this folder (design, addendum, raw replay, adapter hashes).
Runs: one thread per process, cores 8 and 9 only, deterministic replays, no solver, no model,
no GPU.
