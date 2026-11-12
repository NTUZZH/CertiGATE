# N25 frozen design: the direct benchmark under a finish-to-start reading of reorder

Version l1-n25-fts-1. Design pre-specified before the run.
Written 2026-11-11 before any dispatch under reading F (no probe, no replay). Later choices go
to results/n25_finish_to_start/addendum.md; this file is never edited. Its sha256 is recorded
in results/n25_finish_to_start/design.sha256 and asserted by code/scripts/n25_finish_to_start.py
before any replay.

## Purpose

Post hoc sensitivity analysis. Question: if every reorder edge is read as finish-to-start
(the successor is eligible only once the predecessor has completed), does the headline of the
direct benchmark change? Destination: one sentence of the main text and one paragraph with a
small table in the Supplementary Material. The result is reported whichever way it falls.
Expected: reorder proposals cost at least as much under F, the costly set does not shrink, and
the certificate refers them on both boards. If K and FI then disagree on some proposals, that
count is the finding.

## Readings

- S (published, start-after-start): the unpatched code/l1adapter/dispatch.py. A successor is
  eligible once every predecessor is in the set `started`.
- F (finish-to-start): the same dispatcher with the eligibility test replaced in memory. No
  file under code/l1adapter/ is edited. The function `dispatch._run` is compiled again from
  its own source with three textual changes, each asserted to occur exactly once:
  1. `_precedence_ok(oid)` under F returns True when the order has no predecessor, or when
     every predecessor a has been assigned and its end time end_a satisfies end_a <= now (the
     current dispatch instant). A predecessor completed before the decision instant is on the
     realised board as a frozen order with its logged slot, so it counts as complete. On the
     known board and the full-information board a completed order is absent, and a reorder
     that names it is refused as a dangling id before dispatch in both readings.
  2. `_assign` and the frozen-start branch record the end time of every order they place.
  3. At each instant, after the events are drained and the frozen orders are placed, the
     trades of the successors of every order that completes at that instant join the sweep.
     This is the mechanism the dispatcher already uses for a frozen start (a cross-trade
     successor would otherwise wait for an unrelated event in its own trade). Under S this
     step does nothing.
  The patched function carries a switch. With the switch off it executes the S code path,
  plus the bookkeeping of change 2, which no decision reads.
- Everything else is unchanged in both readings: ATC, seed 0, the frozen set "fix", the
  batch rules (the head of a batch chain is chosen with the same eligibility test, so under F
  a member waits for its predecessor's completion), the documented conflict order (a freeze
  wins over a precedence edge and over a batch chain), apply.py (field edits, the frozen-path
  check on starts, the notes), the guard's schema and feasibility stages, the bound, the
  floor and the D-REL2 reference dispatch (which carries no constraining operation).
- Deadlock: n11_decision_time.gen_price turns a DispatchDeadlock into execution_failed at the
  feasibility stage (an infrastructure finding), and a validator rejection into
  blocked_feas. Either way the proposal is not priced on that board. Under F such a
  proposal leaves the priced population and is listed. Every schedule under F is asserted
  complete.

## Probes (in memory, before any replay of the suite)

The three micro-instances use n24's probe builders. (a) Patch off: the canonical schedule
JSON equals the unpatched module's byte for byte on probes 1 to 3 and on a no-reorder probe.
(b) Patch on: in probe 1 (cross-trade) and probe 2 (same trade, two technicians) the
successor B starts at the predecessor A's end, 7.0 bh. (c) A proposal without a reorder edge
(probe 3's shift, a pin and a batch on micro-instances) gives the identical schedule with the
patch on and off.

## Population

- The 1,356 priced reference proposals of the direct benchmark (n20.build's records).
- Every proposal whose canonical operations carry at least one reorder (364 expected) is
  replayed under S and under F on three boards, exactly as n23 builds them: the known board at
  t_d (K, N11's dt run), the full-information board at t_d (FI, n11_forecast's FI board), and
  the realised whole-window run from t_d. The no-proposal runs (K anchor, FI anchor, realised
  without the proposal) carry no reorder edge; they are recomputed under F for every site of a
  reorder proposal and asserted equal to the stored totals.
- 50 priced proposals without a reorder edge, drawn with random.Random(20261111).sample over
  the sorted item ids, are replayed under S and F on the three boards and asserted identical
  (canonical schedules and totals). All proposals without a reorder edge then keep their
  published values.
- The reference proposals with a reorder that are not priced: those issuable but refused, and
  those not issuable. Each is run through gen_price on K (and on FI when issuable) under S and
  F at its stored decision instant; the terminal and the codes are compared with
  results/n11_decision_time/items.jsonl and between the readings. They are reported
  separately, with whether the refusal depends on the reading.

## Quantities recomputed under F for each reorder proposal

With the functions the published numbers came from (n11_decision_time.gen_price, n2.prices,
n11_forecast.prices_of, n11_decision_time.attach_truth):
- the schema and feasibility outcome on K and on FI (terminal, stage, codes);
- the known-board objective on the adjusted and on the original values;
- the certificate price: certified_gap(obj, lb, floor 1.0) with the logged bound lb of the
  board (asserted equal to the bound gen_price computes under F, since the bound does not read
  precedence);
- the full-information price, the same on the FI board with its logged bound;
- G-CERT-M (certificate minus the no-proposal board's logged certificate), D-REL1, D-REL2
  (against the dispatched reference, asserted equal to the logged one), D-ABS, each at its own
  threshold (0.20, 0.02, 0.02, 0.8119 weighted bh), on K and on FI;
- the second price on field edits, g_orig = (WT_orig - LB_anchor) / max(LB_anchor, 1 bh) at
  tau = 0.20, on K (n16.sp_flag rule) and on FI (n20's two_f rule);
- the realised run on the whole window and its damage on the original values against the
  unchanged no-proposal run (the no-AI anchor's weighted tardiness);
- the common-denominator pair: gap_bh = max(0, obj - lb) on each board over the realised-cost
  denominator max(midpoint of the oracle_v1 base bracket, 1).

## Labels

Unchanged rule: costly at delta when the lower end of the realised marginal-cost interval
(attach_truth with the window's stored base bracket and the no-AI anchor) exceeds delta,
low-cost when its upper end is at most delta, undecided otherwise. delta = 0.20 (headline)
and 0.10. The bracket is the window's stored bracket and does not depend on the reading.

## Run-fatal checks before any number under F

- With the patch off (the unpatched module), the replay reproduces for every reorder
  proposal the stored known-board objective (adjusted and original), the bound, the price, the
  full-information price record, and the realised totals and damage (tolerances as in n23:
  1e-9 against full-precision totals, 1e-6 against the anchor and the six-decimal CSV), and
  the published flags of every design on K and FI and the label at both levels.
- n16.section0, n18.section0 and n20.section0 pass on n20.build's records.
- The sha256 prefixes of n16_robustness.py 39e5dc3e0bae, n13_fromlogs.py 60e4deec5d8e,
  n11_decision_time.py 83d5217b291c, n10_field_change.py ac4dd5db85b4; the sha256 of every .py
  file under code/l1adapter/ is recorded before and after the run and asserted unchanged.
- Under F every schedule is complete; for every reorder edge (a, b) of a priced proposal,
  start_b >= end_a holds on every board unless b is frozen (the freeze wins, counted).

## Reported

In the layout of Block C of N24, S beside F, at delta 0.20 and 0.10: priced; costly
and low-cost; costly referred on K, with FI, and by both; costly applied on K and with FI;
applied with the second price (K and FI); low-cost referred without and with the second price
(K, and FI); the common-denominator pair; pooled and per stratum (Primary, Confirmation,
Buildings); the low-cost referral shares on K, without and with the second price, with the n2
cluster-bootstrap 95% interval (seed 20261026, 20,000 replicates, 60 instance clusters), the
interval the published tables carry. Also: the four other designs at their own thresholds
(costly applied and low-cost referred on K and FI); proposals referred by the certificate on
one board only (count and list); how many reorder proposals get a different schedule under F
on K, on FI and on the realised run; the change in realised damage F minus S over the reorder
proposals (median, p10, p90 by numpy linear percentiles, min, max, share lower under F, share
higher, share equal within 1e-9); label changes in each direction at both levels; disposition
changes on K and on FI (certificate, and certificate with the second price). The same
headline restricted to (i) the families outside every disputed group (n24's subset ExAll) and
(ii) the four precedence families of group P (n24's S["fams"]["P"]).

Self-test: at least ten headline numbers recomputed by a second code path (csv/json readers,
a label function and a bootstrap written in the script) and asserted equal.

## Rules

Deterministic replays only; no solver, no time budget, no model call, no network, no GPU, no
git, no deletion. Every run: OMP_NUM_THREADS=1 taskset -c 14
python. Nothing is tuned after a result is seen.
