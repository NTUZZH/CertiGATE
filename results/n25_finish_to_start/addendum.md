# N25 addendum to the frozen design (design.md, sha256 f90cd858797b0e1c...)

Choices made while writing code/scripts/n25_finish_to_start.py, before any dispatch under
reading F (no probe and no replay had run when entries 1 to 7 were written).

1. Parity of the patched function on real boards. Besides the probes, the patched function
   with the switch off (reading "S-off") dispatches the known board of every reorder
   proposal, and its canonical schedule JSON and objective are asserted equal to the
   unpatched module's. The S replay itself uses the unpatched module.
2. The patched `_run` is compiled from `inspect.getsource(dispatch._run)` (asserted to be a
   slice of dispatch.py on disk) with the `annotations` future flag of dispatch.py, into a
   copy of the dispatch module's globals that also holds the switch. The module attribute
   `dispatch._run` is swapped for the duration of each F (or S-off) call and restored after
   it; `dispatch_adjusted` looks `_run` up at call time, so gen_price, n8.trajectory and the
   D-REL2 reference all see the reading in force.
3. Python is run with bytecode writing disabled, so no .pyc file is written under code/.
4. Board construction is n23's (code/scripts/n23_urgent_orders.py, replay_instance): the same
   gen_price arguments for the known board, the FI board and the realised run, and the same
   no-proposal runs. The functions are restated in n25 (n23 cannot be imported under core 14
   without rewriting its guard), and every S board is tied to its stored total.
5. If under F the FI board of a proposal priced on K stops being priced (deadlock or validator
   rejection), the FI board is counted as refusing it (referred on FI, with and without the
   second price, and on the common denominator), and the case is listed. If the realised run
   under F has no schedule, the label is undecided and the case is listed. (Fallbacks; they
   apply only if such a case occurs.)
6. Per-stratum intervals use the same 60-cluster bootstrap object as the pooled ones (n13.score
   through n24.headline); replicates that draw no proposal of the stratum are dropped by
   e1_delta_guard_replay.bootstrap_ci, as in N23's per-stratum Table 4.
7. Disposition on a board means the certificate's referral flag at tau = 0.20 on that board
   (and, separately, the flag with the second price). "Discordant" means referred by the
   certificate on one of K and FI and not on the other; it is reported for all priced
   proposals and for the costly and the low-cost ones at each delta.

Entries 8 and 9 were appended after the final run of 2026-11-11. The input hash of this file in
analysis/N25_summary.md (a9a6905a...) covers entries 1 to 7.

8. Check on the unpriced proposals, changed after the first full run stopped on it (before any
   F number had been read). The first run asserted that the replay's known-board terminal, stage
   and codes equal results/n11_decision_time/items.jsonl for every unpriced reorder proposal. It
   stopped on BEN-0170: the replay adds the code names_running_work, which the stored row lacks
   (the terminal blocked_feas and the stage agree). The check now asserts the terminal and the
   stage, and that every stored code is among the replay's codes. The extra codes are counted
   and reported (137 not-issuable items). No priced proposal is affected; their codes are still
   asserted equal.
9. Development aids, used only with --selftest and only with files in the session working folder:
   N25_REPLAY_CACHE (a pickle of the replay) and N25_DEV_SUMMARY (a scratch copy of the summary
   and macros). The script refuses to write project outputs from a cached replay; every output
   file comes from the final fresh replay.
