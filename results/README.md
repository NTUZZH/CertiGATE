# The logged results

Each experiment wrote two kinds of file. The first kind is a small record,
such as a summary, a run manifest, an assertion file or a console log. The
second kind is a large log with one row per model call, per proposal, per
verdict or per solver bracket. This directory holds every small record. The
large logs ship as release assets because together they come to
4.3 GB unpacked.

A file stays in this directory when it is at most 256 KB and is a summary,
record, table or console log. A few experiments stay here whole, so that `code/scripts/e3_analyze.py` runs from a plain
clone. Every other file of an experiment ships in that experiment's asset.

## Downloading and unpacking the assets

Each asset is a gzipped tar archive named after its folder. An archive
unpacks to `results/<experiment>/` (or to `analysis/` for
`analysis_large.tar.gz`), so unpacking it at the repository root puts the
files where the scripts look for them. Unpacking never overwrites a file of
the repository, because each archive holds only the files this directory
lacks.

```bash
# from the repository root, for one experiment
tar -xzf n11_decision_time.tar.gz

# or for every downloaded archive
for f in *.tar.gz; do tar -xzf "$f"; done
```

Check the download against the checksums of the release:

```bash
sha256sum -c SHA256SUMS.txt
```

The assets of this release come to 296.2 MB compressed.

## Experiments

| Folder | What it holds | In this repository | Asset |
|---|---|---|---|
| `e1_eval_deepseek/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 192.1 KB | `e1_eval_deepseek.tar.gz` (5.2 MB, 4 files, 70.0 MB unpacked) |
| `e1_eval_glm9b/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 70.3 KB | `e1_eval_glm9b.tar.gz` (1.3 MB, 4 files, 18.0 MB unpacked) |
| `e1_eval_gpt54mini/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 101.4 KB | `e1_eval_gpt54mini.tar.gz` (3.0 MB, 4 files, 35.8 MB unpacked) |
| `e1_eval_opus5/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 193.7 KB | `e1_eval_opus5.tar.gz` (4.9 MB, 4 files, 63.0 MB unpacked) |
| `e1_eval_qwen14b/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 132.6 KB | `e1_eval_qwen14b.tar.gz` (4.3 MB, 4 files, 54.6 MB unpacked) |
| `e1_eval_qwen27b/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 131.9 KB | `e1_eval_qwen27b.tar.gz` (4.2 MB, 4 files, 54.9 MB unpacked) |
| `e1_eval_sol/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 42.3 KB | `e1_eval_sol.tar.gz` (909.6 KB, 4 files, 9.7 MB unpacked) |
| `e1_eval_sonnet5/` | single-turn stress test: the proposals of one model arm and the verdicts of three gate configurations | 3 files, 102.4 KB | `e1_eval_sonnet5.tar.gz` (3.0 MB, 4 files, 35.5 MB unpacked) |
| `e2_tau_sweep/` | the certificate-tolerance sweep | 3 files, 673.8 KB |  |
| `e2_tau_sweep_3arm_accepted_20260812/` | the certificate-tolerance sweep | 3 files, 218.2 KB |  |
| `e3_deepseek/` | the multi-turn agent experiment: call logs and trajectories | 3 files, 7.9 MB |  |
| `e3_deepseek_calibration/` | the token calibration of the multi-turn agent experiment | 4 files, 425.8 KB |  |
| `e3_openai/` | the multi-turn agent experiment: call logs and trajectories | 4 files, 5.1 MB |  |
| `e3_openai_calibration/` | the token calibration of the multi-turn agent experiment | 4 files, 302.2 KB |  |
| `e3_opus/` | the multi-turn agent experiment: call logs and trajectories | 4 files, 6.7 MB |  |
| `e3_opus_calibration/` | the token calibration of the multi-turn agent experiment | 4 files, 384.7 KB |  |
| `e3_qwen14b/` | the multi-turn agent experiment: call logs and trajectories | 3 files, 12.5 MB |  |
| `e3_qwen14b_calibration/` | the token calibration of the multi-turn agent experiment | 4 files, 352.2 KB |  |
| `e3_qwen27b/` | the multi-turn agent experiment: call logs and trajectories | 3 files, 5.4 MB |  |
| `e3_qwen27b_calibration/` | the token calibration of the multi-turn agent experiment | 4 files, 293.5 KB |  |
| `e3_replay_deepseek/` | the offline gate replay of the multi-turn agent experiment | 4 files, 1.6 MB |  |
| `e3_replay_openai/` | the offline gate replay of the multi-turn agent experiment | 4 files, 1.6 MB |  |
| `e3_replay_opus/` | the offline gate replay of the multi-turn agent experiment | 4 files, 1.6 MB |  |
| `e3_replay_qwen14b/` | the offline gate replay of the multi-turn agent experiment | 4 files, 3.4 MB |  |
| `e3_replay_qwen27b/` | the offline gate replay of the multi-turn agent experiment | 4 files, 1.7 MB |  |
| `e3_replay_sonnet/` | the offline gate replay of the multi-turn agent experiment | 4 files, 1.6 MB |  |
| `e3_sample/` | the item sample of the multi-turn agent experiment | 1 files, 18.1 KB |  |
| `e3_sonnet/` | the multi-turn agent experiment: call logs and trajectories | 3 files, 5.7 MB |  |
| `e3_sonnet_calibration/` | the token calibration of the multi-turn agent experiment | 4 files, 331.9 KB |  |
| `grid_e1_control_opus_default/` | same-day whole-window control of a known-board rerun | 2 files, 6.0 KB | `grid_e1_control_opus_default.tar.gz` (31.7 KB, 1 files, 284.0 KB unpacked) |
| `grid_e1_control_opus_disabled/` | same-day whole-window control of a known-board rerun | 2 files, 6.0 KB | `grid_e1_control_opus_disabled.tar.gz` (31.7 KB, 1 files, 284.3 KB unpacked) |
| `grid_e1_control_sonnet/` | same-day whole-window control of a known-board rerun | 2 files, 5.7 KB | `grid_e1_control_sonnet.tar.gz` (31.8 KB, 1 files, 288.1 KB unpacked) |
| `grid_e1_hosted_deepseek/` | single-turn stress test: raw generations of a hosted model | 3 files, 6.3 KB | `grid_e1_hosted_deepseek.tar.gz` (5.3 MB, 2 files, 52.9 MB unpacked) |
| `grid_e1_hosted_openai/` | single-turn stress test: raw generations of a hosted model | 3 files, 4.6 KB | `grid_e1_hosted_openai.tar.gz` (2.1 MB, 2 files, 21.6 MB unpacked) |
| `grid_e1_hosted_opus/` | single-turn stress test: raw generations of a hosted model | 2 files, 80.4 KB | `grid_e1_hosted_opus.tar.gz` (5.0 MB, 3 files, 51.7 MB unpacked) |
| `grid_e1_hosted_sol/` | single-turn stress test: raw generations of a hosted model | 1 files, 1.3 KB | `grid_e1_hosted_sol.tar.gz` (552.2 KB, 2 files, 6.1 MB unpacked) |
| `grid_e1_hosted_sonnet/` | single-turn stress test: raw generations of a hosted model | 3 files, 5.0 KB | `grid_e1_hosted_sonnet.tar.gz` (2.7 MB, 2 files, 28.7 MB unpacked) |
| `grid_e1_known_dryrun/` | the known-board prompts written before the known-board reruns | 3 files, 59.2 KB | `grid_e1_known_dryrun.tar.gz` (1.4 MB, 2 files, 15.1 MB unpacked) |
| `grid_e1_known_opus_default/` | known-board prompt rerun: raw generations of one Claude configuration | 2 files, 5.8 KB | `grid_e1_known_opus_default.tar.gz` (815.3 KB, 1 files, 6.0 MB unpacked) |
| `grid_e1_known_opus_disabled/` | known-board prompt rerun: raw generations of one Claude configuration | 2 files, 5.8 KB | `grid_e1_known_opus_disabled.tar.gz` (813.0 KB, 1 files, 6.0 MB unpacked) |
| `grid_e1_known_prelaunch_m3/` | the frozen control item list and the resolved configurations of the known-board reruns | 7 files, 54.3 KB |  |
| `grid_e1_known_sonnet/` | known-board prompt rerun: raw generations of one Claude configuration | 2 files, 5.6 KB | `grid_e1_known_sonnet.tar.gz` (814.1 KB, 1 files, 6.1 MB unpacked) |
| `grid_e1_local/` | single-turn stress test: raw generations of a local open-weight model | 1 files, 1.3 KB | `grid_e1_local.tar.gz` (1.2 MB, 1 files, 13.2 MB unpacked) |
| `grid_e1_local_27b/` | single-turn stress test: raw generations of a local open-weight model | 1 files, 1.3 KB | `grid_e1_local_27b.tar.gz` (1.2 MB, 1 files, 13.5 MB unpacked) |
| `grid_e1_local_glm9b/` | single-turn stress test: raw generations of a local open-weight model | 1 files, 785 B | `grid_e1_local_glm9b.tar.gz` (408.1 KB, 1 files, 4.5 MB unpacked) |
| `n11_decision_time/` | the decision-time census of the direct benchmark | 54 files, 650.8 KB | `n11_decision_time.tar.gz` (21.0 MB, 29 files, 195.0 MB unpacked) |
| `n11_e2e/` | the decision-time replay of the logged end-to-end proposals | 187 files, 5.2 MB | `n11_e2e.tar.gz` (50.9 MB, 225 files, 909.3 MB unpacked) |
| `n11_forecast/` | the forecast reading of the decision-time benchmark | 138 files, 4.1 MB | `n11_forecast.tar.gz` (100.3 MB, 301 files, 1.7 GB unpacked) |
| `n11_oracle/` | the decision-time oracle brackets of the known boards | 3 files, 79.4 KB | `n11_oracle.tar.gz` (148.3 KB, 6 files, 1.2 MB unpacked) |
| `n12_env/` | the environment sensitivity: scaled service windows and crew sizes | 102 files, 3.6 MB | `n12_env.tar.gz` (24.4 MB, 418 files, 225.0 MB unpacked) |
| `n14_altdispatch/` | alternative dispatching rules on the known board | 36 files, 1.3 MB | `n14_altdispatch.tar.gz` (4.2 MB, 56 files, 48.8 MB unpacked) |
| `n17_heldout/` | the replays on three new draws of the suite | 38 files, 232.9 KB | `n17_heldout.tar.gz` (4.4 MB, 379 files, 55.6 MB unpacked) |
| `n19_known_eval/` | the evaluation of the known-board reruns | 6 files, 32.8 KB | `n19_known_eval.tar.gz` (10.7 MB, 46 files, 118.6 MB unpacked) |
| `n19_selftest/` | the self-test of the known-board evaluator on earlier logs | 16 files, 671.5 KB | `n19_selftest.tar.gz` (7.5 MB, 54 files, 116.2 MB unpacked) |
| `n25_finish_to_start/` | replays under a finish-to-start reading of every reorder edge | 4 files, 15.6 KB | `n25_finish_to_start.tar.gz` (139.3 KB, 1 files, 1.9 MB unpacked) |
| `n26_shift_keeps_due/` | replays under the second time-window shift convention | 4 files, 14.5 KB | `n26_shift_keeps_due.tar.gz` (333.1 KB, 1 files, 5.7 MB unpacked) |
| `n27_withheld_orders/` | the withheld-orders analysis | 8 files, 23.6 KB | `n27_withheld_orders.tar.gz` (990.7 KB, 2 files, 22.0 MB unpacked) |
| `n3_deepseek/` | stated acceptance (protocol 1.1): raw generations of one model | 6 files, 50.3 KB | `n3_deepseek.tar.gz` (359.0 KB, 1 files, 4.0 MB unpacked) |
| `n3_eval_deepseek/` | stated acceptance (protocol 1.1): the evaluated proposals of one model under protocols 1.0, 1.1 and 1.2 | 1 files, 3.0 KB | `n3_eval_deepseek.tar.gz` (1.2 MB, 7 files, 28.1 MB unpacked) |
| `n3_eval_openai/` | stated acceptance (protocol 1.1): the evaluated proposals of one model under protocols 1.0, 1.1 and 1.2 | 1 files, 3.3 KB | `n3_eval_openai.tar.gz` (1.4 MB, 7 files, 28.6 MB unpacked) |
| `n3_eval_opus/` | stated acceptance (protocol 1.1): the evaluated proposals of one model under protocols 1.0, 1.1 and 1.2 | 1 files, 3.4 KB | `n3_eval_opus.tar.gz` (1.2 MB, 7 files, 27.5 MB unpacked) |
| `n3_eval_sol/` | stated acceptance (protocol 1.1): the evaluated proposals of one model under protocols 1.0, 1.1 and 1.2 | 1 files, 3.3 KB | `n3_eval_sol.tar.gz` (1.4 MB, 7 files, 28.6 MB unpacked) |
| `n3_eval_sonnet/` | stated acceptance (protocol 1.1): the evaluated proposals of one model under protocols 1.0, 1.1 and 1.2 | 1 files, 3.3 KB | `n3_eval_sonnet.tar.gz` (1.4 MB, 7 files, 28.6 MB unpacked) |
| `n3_mock_r2_openai/` | a mock-model rehearsal of the stated-acceptance runner, read by the tests | 9 files, 26.6 KB | `n3_mock_r2_openai.tar.gz` (30.4 KB, 8 files, 475.1 KB unpacked) |
| `n3_openai/` | stated acceptance (protocol 1.1): raw generations of one model | 6 files, 50.2 KB | `n3_openai.tar.gz` (348.3 KB, 1 files, 3.9 MB unpacked) |
| `n3_opus/` | stated acceptance (protocol 1.1): raw generations of one model | 4 files, 43.7 KB | `n3_opus.tar.gz` (333.3 KB, 1 files, 3.8 MB unpacked) |
| `n3_sol/` | stated acceptance (protocol 1.1): raw generations of one model | 6 files, 50.4 KB | `n3_sol.tar.gz` (345.1 KB, 1 files, 3.8 MB unpacked) |
| `n3_sonnet/` | stated acceptance (protocol 1.1): raw generations of one model | 4 files, 44.4 KB | `n3_sonnet.tar.gz` (349.5 KB, 1 files, 4.0 MB unpacked) |
| `n3neg_eval_openai/` | stated acceptance, negated-clause control: the evaluated proposals of one model | 1 files, 3.2 KB | `n3neg_eval_openai.tar.gz` (279.4 KB, 7 files, 5.1 MB unpacked) |
| `n3neg_eval_opus/` | stated acceptance, negated-clause control: the evaluated proposals of one model | 1 files, 3.0 KB | `n3neg_eval_opus.tar.gz` (278.0 KB, 7 files, 5.1 MB unpacked) |
| `n3neg_eval_sol/` | stated acceptance, negated-clause control: the evaluated proposals of one model | 1 files, 3.0 KB | `n3neg_eval_sol.tar.gz` (273.7 KB, 7 files, 5.0 MB unpacked) |
| `n3neg_eval_sonnet/` | stated acceptance, negated-clause control: the evaluated proposals of one model | 1 files, 3.0 KB | `n3neg_eval_sonnet.tar.gz` (278.2 KB, 7 files, 5.1 MB unpacked) |
| `n3neg_openai/` | stated acceptance, negated-clause control: raw generations of one model | 2 files, 18.8 KB | `n3neg_openai.tar.gz` (61.4 KB, 1 files, 711.9 KB unpacked) |
| `n3neg_opus/` | stated acceptance, negated-clause control: raw generations of one model | 4 files, 27.9 KB | `n3neg_opus.tar.gz` (73.0 KB, 1 files, 860.8 KB unpacked) |
| `n3neg_sol/` | stated acceptance, negated-clause control: raw generations of one model | 2 files, 18.8 KB | `n3neg_sol.tar.gz` (60.3 KB, 1 files, 686.9 KB unpacked) |
| `n3neg_sonnet/` | stated acceptance, negated-clause control: raw generations of one model | 2 files, 19.4 KB | `n3neg_sonnet.tar.gz` (61.8 KB, 1 files, 723.1 KB unpacked) |
| `n8_causal/` | the realised-cost runs of the causal analysis | 2 files, 1.9 KB | `n8_causal.tar.gz` (331.0 KB, 1 files, 3.9 MB unpacked) |
| `n9_instruction_cost/` | the decision-cost brackets of the held-out set | 9 files, 197.4 KB | `n9_instruction_cost.tar.gz` (462.3 KB, 8 files, 2.8 MB unpacked) |
| `opus5_pilot/` | the pilot of one hosted model before the main runs | 2 files, 137.2 KB |  |
| `oracle_v1/` | the CP-SAT oracle brackets of the full-window boards | 6 files, 201.9 KB | `oracle_v1.tar.gz` (1.5 MB, 5 files, 39.4 MB unpacked) |
| `practitioner_audit_r2/` | the practitioner audit: the cases as drawn, the label map and the stage A and B records | 6 files, 87.0 KB |  |
| `sol_pilot/` | the pilot of one hosted model before the main runs | 2 files, 103.4 KB |  |
| `suite_gate/` | the suite acceptance gate | 3 files, 3.4 MB |  |
| `suite_gate_mock/` | the dry run of the suite acceptance gate | 3 files, 41.0 KB |  |
| `superseded_20260813_e1_eval_opus5_partial/` | a partial evaluation that a complete rerun replaced; no analysis reads it | 3 files, 57.4 KB | `superseded_20260813_e1_eval_opus5_partial.tar.gz` (1.7 MB, 4 files, 18.0 MB unpacked) |
| `terra_pilot/` | the pilot of one hosted model before the main runs | 2 files, 103.5 KB |  |
| `tier1_slice/` | the comparison of the two certificate tiers | 3 files, 1.2 MB |  |
| `analysis/` (large row files) | the largest row files of the analyses | | `analysis_large.tar.gz` (8.3 MB, 16 files, 151.1 MB unpacked) |

Console logs of single runs (`*.log`) and the pilot files of the first hosted endpoints sit at the top of `results/`.

## File conventions

`proposals.jsonl` and `proposals_raw.jsonl` hold one row per model call. A
row carries the system and user prompts as sent, the prompt's SHA-256, the
raw generation, the parsed operations, the token counts and the latency.
`verdicts_*.jsonl` hold one row per proposal and gate configuration. A
verdict row carries the terminal state, the findings, the certificate where
one was issued, and a fingerprint of the verdict. `summary.json` is the
accepted aggregate that the analysis scripts assert against, and
`summary.md` renders it for reading. `run_meta*.json` records the model,
the pinned prices, the wall-clock time and the SHA-256 of the suite and the
schema that the run checked at start-up.

A resumed run keeps the superseded attempts in its log next to the row that
counts. Each analysis that reads such a log states its de-duplication rule,
which keeps the last row per key.

Logged instance paths begin with `${L1_Y1_ROOT}`, which stands for the
checkout of the scheduling environment. The analysis scripts locate each
instance under `L1_Y1_ROOT`, from its suite item or its file name, so the logs
need no editing.

## Participant data

The two sets of practitioners' instructions, the practitioner audit under
protocol 1.2 and the planner's check of 194 suite rows involved people.
Their individual responses are not released, to protect their privacy, and
this directory holds no file derived from a returned workbook. The folders
`field_v1/`, `field_r2/`, `practitioner_audit_r2_scored/` and
`suite_sample_check_scored/` are therefore absent. `practitioner_audit_r2/`
holds the audit's cases as they were sent to the panel, with no response.
The section "What the release
leaves out" of the top-level README names the analyses whose inputs are
therefore missing.
