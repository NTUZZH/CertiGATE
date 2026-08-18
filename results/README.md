# What lives in this directory, and what lives in the release assets

Every experiment in the paper wrote two kinds of file: a small accepted record
(a summary, a run manifest, a calibration file, a console log) and a large raw
log with one row per model call, per proposal, or per guard verdict. Together
they come to 623 MB, which is more than a repository should carry.

The split is by size, and it is drawn so that the script that produces the
numbers the manuscript prints runs from a plain clone with nothing downloaded:

* **In this directory (66 MB).** Every accepted summary and run manifest for
  every experiment, plus the complete raw logs of the multi-turn agent
  experiment (`e3_*`), its offline guard replay (`e3_replay_*`), its token
  calibration (`e3_*_calibration`), the certificate-tolerance sweep
  (`e2_tau_sweep*`), the certificate-tier comparison (`tier1_slice`), the suite
  acceptance gate (`suite_gate*`), and the billing pilots.
* **In the GitHub release assets (48 MB compressed, 557 MB unpacked).** The
  per-call proposal logs and per-proposal verdict logs of the main single-turn
  evaluation (`e1_eval_*`, `grid_e1_*`). These are the largest files in the
  study: 78,000 proposals over eight model arms, each logged once as a raw
  generation and once per guard configuration, with the full prompt text on
  every row.

## Downloading and unpacking the assets

Each experiment ships as one gzipped tar archive named after its directory. The
archives expand to `results/<experiment>/`, so unpack them at the repository
root and the paths the scripts expect appear in place:

```bash
# from the repository root, for one experiment
tar -xzf e1_eval_opus5.tar.gz

# or for all of them
for f in *.tar.gz; do tar -xzf "$f"; done
```

Verify what you downloaded against the checksums published with the release:

```bash
sha256sum -c SHA256SUMS.txt
```

The archives are:

| Archive | Compressed | Unpacked | Contents |
|---|---|---|---|
| `e1_eval_qwen14b.tar.gz` | 4.4 MB | 57.8 MB | proposals + three verdict logs |
| `e1_eval_qwen27b.tar.gz` | 4.3 MB | 58.1 MB | proposals + three verdict logs |
| `e1_eval_glm9b.tar.gz` | 1.4 MB | 19.0 MB | proposals + three verdict logs |
| `e1_eval_gpt54mini.tar.gz` | 3.0 MB | 37.7 MB | proposals + three verdict logs |
| `e1_eval_deepseek.tar.gz` | 5.3 MB | 73.7 MB | proposals + three verdict logs |
| `e1_eval_sonnet5.tar.gz` | 3.1 MB | 37.3 MB | proposals + three verdict logs |
| `e1_eval_opus5.tar.gz` | 5.0 MB | 66.4 MB | proposals + three verdict logs |
| `e1_eval_sol.tar.gz` | 916 KB | 10.2 MB | proposals + three verdict logs |
| `grid_e1_local.tar.gz` | 1.2 MB | 14.3 MB | raw generations, local 14B arm |
| `grid_e1_local_27b.tar.gz` | 1.2 MB | 14.7 MB | raw generations, local 27B arm |
| `grid_e1_local_glm9b.tar.gz` | 412 KB | 4.8 MB | raw generations, local 9B arm |
| `grid_e1_hosted_openai.tar.gz` | 2.2 MB | 23.0 MB | raw generations, hosted arm |
| `grid_e1_hosted_sonnet.tar.gz` | 2.8 MB | 30.5 MB | raw generations, hosted arm |
| `grid_e1_hosted_opus.tar.gz` | 5.1 MB | 55.0 MB | raw generations, hosted arm |
| `grid_e1_hosted_deepseek.tar.gz` | 5.4 MB | 56.3 MB | raw generations, hosted arm |
| `grid_e1_hosted_sol.tar.gz` | 556 KB | 6.5 MB | raw generations, hosted arm |
| `superseded_20260813_e1_eval_opus5_partial.tar.gz` | 1.8 MB | 18.9 MB | a partial evaluation that a complete rerun replaced; kept for the record and used by no analysis |

## Which script needs which files

| Script | Needs assets? | Reads |
|---|---|---|
| `code/scripts/paper_macros.py` | no | `analysis/`, the suite manifest, and the summaries in this directory |
| `code/scripts/e3_analyze.py` | no | `results/e3_*`, `results/e3_replay_*`, `results/e3_*_calibration` |
| `code/scripts/paper_tables.py` | yes | the `e1_eval_*` verdict logs (and, without `--skip-d1`, the proposal logs) |
| `code/scripts/ladder_replay.py` | yes | the `e1_eval_*` proposal and verdict logs |
| `code/scripts/d3_translation_equivalence.py` | yes | the `grid_e1_*` raw generation logs |

If you keep the unpacked logs outside the repository, pass `--results-root` to
`paper_tables.py` and `ladder_replay.py`, and set `L1_RESULTS_ROOT` for
`d3_translation_equivalence.py`.

## File conventions

`proposals.jsonl` and `proposals_raw.jsonl` hold one row per model call: the
system and user prompt as sent, the prompt's SHA-256, the raw generation, the
parsed operations, the token counts and the latency. `verdicts_*.jsonl`
hold one row per proposal per guard configuration, with the terminal state, the
findings, the certificate tuple where one was issued, and a verdict
fingerprint. `summary.json` is the accepted aggregate that every table asserts
against, and `summary.md` is its human-readable rendering. `run_meta*.json`
records the model, the pinned prices, the wall-clock, and the SHA-256 of the
suite and the schema the run asserted at start-up.

Where a run was resumed, the log carries the superseded attempts as well as the
row that counts. The de-duplication rule is stated in each analysis artifact
that applies it: the last row per key wins.
