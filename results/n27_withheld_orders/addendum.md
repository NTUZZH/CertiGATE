# N27 addendum (choices made after the design was frozen)

Entries are appended in order; each says whether it was written before or after any pricing on a thinned board.

1. (Before any price on a thinned board was read.) Test runs. A smoke self-test on two
   windows (c09_storm2_w80_u100_0005 and c10_replay_400_0005) ran the checks, the probe and the
   f = 0 tie on its 61 proposals and printed only |K|, |H| and the number of distinct boards
   per proposal. A full self-test then replays all 1,356 proposals and keeps the replay in a
   copy outside the project, used only to test the analysis code. The reported outputs come
   from a separate fresh replay with no copy loaded (the script refuses a loaded replay
   without --selftest).
2. (Before any price on a thinned board was read.) The pricing call is
   n11_decision_time.gen_price with ref2 on and the running-work rule on, for the proposal,
   and with no operation for the no-proposal run, as section 3 states. The benchmark's own
   call also sets keep_live, which only keeps the dispatched objects for later inspection and
   changes no returned number. The script leaves it off; the f = 0 tie to the stored census
   on every proposal confirms that the numbers are the same.
3. (Before any price on a thinned board was read.) Two run-fatal checks added on every board:
   the no-proposal run is priced (stage 3 reached, objective, bound and certificate present),
   and the window size of the instance equals the census's n_completed + n_known + n_unknown.
   A proposal that reaches stage 3 but ends in an instrument fault or without a bound counts
   as refused, as section 3 states.
4. (After reading the summary of the full test run, which showed no change of any costly
   proposal's disposition under the certificate.) Two descriptive tables added to explain the
   result, with their macros: 5b, the composition of K at t_d (running orders, queued planned
   orders, planned orders on the calendar, queued corrective orders that are named or frozen,
   and the candidates H), as shares of K and counts; and 6b, the movement of the certificate
   price (per proposal the largest absolute change from f = 0 over all draws and levels, and
   per level the smallest price among the costly proposals referred at f = 0 and the largest
   among those applied at f = 0). No level, candidate rule, draw, threshold, label or design
   changed; every number of items 1 to 6 is as the design specifies.
5. (After reading the summary of the full test run.) A third descriptive table, 5c, with its
   macros, a figure-data row and two row columns: the share of the window's corrective orders
   not seen, (n_unknown + n_w) / (corrective orders of the window), per level, and the costly
   proposal-draws by the same four bands. Every order that arrives after t_d is corrective
   (n8_causal.site_state with the planned calendar known puts planned orders released after
   t_d on the calendar), so this is the share of the corrective workload the gate does not
   see; the design's share of section 4 stays the reported share of items 4 and 5. The
   corrective count of each window is read from its instance file in the main process. No
   level, candidate rule, draw, threshold, label or design changed.
6. (After the results.) The first official run replayed every proposal, passed every check and
   wrote the row file, the figure data, the raw replay and the adapter hashes, then stopped
   while writing the numbers file, because the descriptive dictionary of entries 4 and 5 has
   tuple keys. The keys are now written as strings, and the self-test serialises the numbers
   file and reads it back, so this step is exercised before any output is written. No number
   changed (the self-test macros before and after the fix are byte-identical). Every output
   comes from a second fresh official run, which overwrites the partial files of the first.
