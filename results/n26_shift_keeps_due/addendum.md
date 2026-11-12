# N26 addendum (choices made after the design was frozen)

Entries are appended in order; each says whether it was written before or after any dispatch under convention D.

Entries 1 to 8 were written after the code was complete and after three development runs that
dispatched convention D on three windows only (c10_replay_400_0001, c09_storm2_w80_u100_0005,
c10_storm2_w80_u100_0005; output printed to the terminal, nothing written to the project).
Those runs tested the code path. No choice below was changed after seeing their numbers.

1. Boff (the patched function with the switch off) runs on the known board of 50 shift
   proposals drawn with random.Random(20261112).sample from the sorted list of priced shift
   proposals, not on every one. The micro-instance probes cover the switch on every code path.
2. The sample of 50 priced proposals without a shift is drawn with
   random.Random(20261111).sample from the sorted list of (set, item) keys of the suite and the
   new draws pooled.
3. Unpriced shift proposals: in the suite, every item whose reference proposal carries a
   reassign_window and that is not among the 1,356 priced; in the fresh suites, every such item
   that has no row in analysis/N17_rows.csv (rows exist only for priced proposals). Items that
   duplicate a published item are not removed from this unpriced list, since N17's duplicate
   rule applies to priced rows. Priced rows with held_out False stay outside the population.
   On the known board under B the terminal and the stage must equal the stored census; the
   stored codes must be a subset of the replayed codes, and a replayed code beyond them is
   allowed only when it is the running-work code on an item that is not issuable (the
   difference documented in n17_heldout.py at RUNNING_CODE).
4. The check on each shifted order compares its release with the shifted release, raised to t_d
   when earlier and the order is not frozen, because gen_price raises every unfrozen release to
   the dispatch origin (n8_causal.raise_releases) under both conventions.
5. The second price with full information on the new draws is computed from the stored
   full-information record and the stored full-information anchor (fi_anchors.jsonl), with the
   rule n13 section J uses for the suite. N17 does not publish it, so under B it is tied to the
   replay only.
6. Two worker processes (fork) share cores 8 and 9; each replays whole (set, window) tasks, so
   no number depends on the scheduling.
7. Development aids, refused for project outputs: N26_SMOKE (restrict the replay to named
   windows), N26_REPLAY_CACHE (a scratch copy of the replay) and N26_DEV_SUMMARY (a scratch
   copy of the summary and macros). Each is allowed only with --selftest.
8. Before any D tally, the costly proposals the certificate applies under B at 0.20 are
   asserted to split as the design states: suite 18 = 15 in v4_sign_flipped_shift and 3 in
   v4_objective_shifting; new draws 45 = 33 and 12.

Entry 9 was written after a full development run (with --selftest, nothing written to the
project) had produced every table.

9. Two descriptive additions, no definition changed: (a) for the costly proposals the
   certificate applies under B, the known-board objective on the edited values and the
   known-board bound under B and under D (per proposal in the summary; the summed rises and
   the largest certificate price under D as macros), which show why the certificate price
   stays low under D; (b) a list of every shift proposal whose label or disposition differs
   between B and D.

10. A note on timing, appended after the final run: entries 1 to 8 were appended while the
    first full test run was replaying, before it printed any number. The final outputs come from
    a fresh replay (695 s) whose macro file is byte-identical to the test run's.
