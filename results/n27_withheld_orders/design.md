# N27 design (frozen): the gate on a known board that holds less of the window

Version l1-n27-withheld-1. Design pre-specified before the run.
Post hoc analysis, reported whichever way it falls. This file is written and its sha256
recorded before any pricing on a thinned board. Later choices go to addendum.md in this
folder; this file is never edited.

Before this design a timing probe priced, at f = 0 only (the benchmark's known board), the
proposals of three windows (c10_storm2_w80_u100_0005, c09_storm2_w80_u100_0005,
c10_replay_400_0005), with the no-proposal run, and counted the candidates for withholding.
No thinned board was priced. The probe gives about 0.8 s per pricing on a c10 storm board and
under 0.1 s elsewhere, so five draws per level fit well inside 90 minutes on two cores. The
probe also showed that the candidate set H is small (0 to about 50 orders on boards of 300 to
7,600 orders), because most unstarted orders on the known board are planned maintenance.

## 1. Population and labels

The 1,356 priced reference proposals of the direct benchmark (n20.build's records, as N15, N16,
N20, N24, N25 and N26 use them), at their stored decision instants t_d. Labels are the stored
ones (n13.costly_of on the stored realised-cost interval) at delta 0.20 and 0.10 and do not
change with the level: the world is the same, only what the gate sees shrinks.

## 2. Boards

- The known board K at t_d is built as in the direct benchmark (n8_causal.site_state with the
  planned calendar known, n8_causal.known_instance; frozen set n11_decision_time.kf_fix; pin
  schedule n8_causal.pin_schedule; running orders = the in-progress orders), the construction
  N23, N25 and N26 restate and tie to the stored census.
- Candidates for withholding H: orders on K that (i) are corrective (`is_pm` false; planned
  orders stay, since the benchmark treats the maintenance calendar as known), (ii) have not
  started at t_d (the queue; running and completed orders are not candidates), (iii) are named
  neither by the instruction (`referenced.order_ids` of the suite item) nor by any operation
  of the proposal (n8_causal.named_orders: the order ids of every operation and the members of
  every batch group it names), and (iv) are not in the standing frozen set the gate carries
  (a frozen unstarted order is pinned to its baseline slot; withholding it would also change
  the frozen set, which stays as in the benchmark). |H| and |K| are recorded per proposal.
- Levels f in {0, 0.25, 0.50, 0.75, 1.00}. At level f the gate's board is K minus n_w =
  floor(f x |H| + 0.5) orders of H (half rounded up), drawn without replacement with
  random.Random(seed) over the sorted ids of H, where seed = the first 16 hex digits of
  sha256("<item id>|<f with two decimals>|<draw index>") read as an integer. Five draws
  (0 to 4) at f = 0.25, 0.50 and 0.75; one draw at f = 1.00 (H itself); f = 0 is K (the
  self-check).
- Everything else is the benchmark's: the frozen set, the pin schedule, the running orders,
  every technician, the decision instant, ATC, seed 0, the guard's stages, the bound (LB2 on
  the board the gate is given) and the floor.
- A board with n_w = 0 is K itself, so its outcome is the f = 0 outcome; and two draws that
  withhold the same set give the same board. Each distinct board of a proposal is priced once
  and its outcome reused (deterministic replay; recorded per row).

## 3. The gate on a board

On each board B (K or thinned), with n11_decision_time.gen_price exactly as the direct
benchmark prices K (ref2 on, the running-work rule on):
- the proposal's outcome: schema and feasibility on B, objective on the edited and on the
  original values, the bound and the certificate, the D-REL2 reference;
- the no-proposal run on the same board B (gen_price with no operation): its objective, bound
  and certificate;
- prices: G-CERT = certified gap (floor 1.0); G-CERT-M = G-CERT minus the no-proposal gap;
  D-REL1 = relative difference to the no-proposal objective; D-REL2 = relative difference to
  the D-REL2 reference; D-ABS = objective minus the no-proposal objective; thresholds 0.20,
  0.20, 0.02, 0.02, 0.8119 weighted bh; refers when the price exceeds the threshold;
- the second price on field edits: g_orig = (objective on the original values minus the
  no-proposal bound on B) / max(that bound, 1); the certificate with the second price refers
  when G-CERT refers or (field edit and g_orig > 0.20) (n16.sp_flag's rule);
- a proposal that stages 1 or 2 refuse on B (or that ends in an instrument fault) is counted
  as refused, apart from applied and referred.

## 4. Share not seen

Per proposal and draw: (n_unknown + n_w) / n_window, with n_unknown the orders of the window
that arrive after t_d and n_window = n_completed + n_known + n_unknown (the census counts N18
uses; at f = 0 this is N18's later share).

## 5. Checks before any thinned-board number is read (run-fatal)

- Frozen files keep their sha256 prefixes (n16_robustness.py 39e5dc3e0bae, n13_fromlogs.py
  60e4deec5d8e, n11_decision_time.py 83d5217b291c, n10_field_change.py ac4dd5db85b4); the .py
  files under code/l1adapter/ have the same sha256 before and after.
- Probe on a micro-instance: withholding removes exactly the drawn orders from the board the
  gate prices and leaves every other order, every technician and the meta unchanged; named,
  running, planned and frozen orders are never candidates.
- f = 0, for all 1,356 proposals: the replayed known board and no-proposal run reproduce the
  stored census (terminals, codes, objectives, bound, certificate, D-REL2 reference,
  no-proposal objective, bound and gap), every design's stored known-board price and flag, the
  second price and its flag; and the frozen counts hold: 186 costly at 0.20, 168 referred, 18
  applied, 0 applied with the second price, 15 and 22 low-cost referred of 1,170; at 0.10, 208
  costly, 25 applied, 6 applied with the second price. Also N18's later-share median (8.6%)
  and maximum (38.5%) for the costly proposals at 0.20.

## 6. Reported (delta = tau = 0.20 first, then 0.10)

For each level, for the certificate and the certificate with the second price (the other four
designs in a second table): (1) costly proposals referred, applied and refused, mean over
draws and range over draws, and the number of costly proposals whose disposition differs from
f = 0 in at least one draw, split referred-to-applied and applied-to-referred; (2) low-cost
proposals referred, mean over draws and share, with the 95% interval of the n2 cluster
bootstrap over the 60 instances on draw 0 (seed 20261026, 20,000 replicates); (3) the same by
edit type (sequencing only, field edits, no operation) and by stratum; (4) costly proposals by
band of the share not seen (up to 10%, 10 to 25%, 25 to 50%, above 50%), proposal-draws and
referred; (5) the distribution of |H| / |K| and of the share not seen (median, quartiles,
maximum) per level, for the costly and for all priced proposals; (6) every costly proposal the
certificate refers at f = 0 and applies at some level: class, family, prices at each level and
draw, realised cost. Plus analysis/N27_fig_data.csv (one row per level, design and quantity:
share of costly referred, share of low-cost referred, median share not seen, each with its
range or interval) and a self-test on a second code path for at least ten numbers.

## 7. Outputs and machine

code/scripts/n27_withheld_orders.py (with --selftest); analysis/N27_rows.csv (one row per
proposal, level and draw); analysis/N27_numbers.json; analysis/N27_summary.md;
analysis/N27_fig_data.csv; analysis/N27_macros.tex (prefix \nTwentySeven, one comment line per
macro) copied byte for byte to manuscript/macros_n27.tex; this folder (design, addendum, raw
replay, adapter hashes). Cores 8 and 9, two worker processes, one thread each; deterministic
replays only; no solver, no model, no GPU.
