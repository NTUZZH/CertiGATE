# CertiGATE

**CertiGATE: a decision-time benchmarking framework for trustworthy LLM-assisted
work-order scheduling in facility management**

Ziheng Zhang, Wei Zhang, Tzu Pei Ku Chia, Xiaofei Yang, Xiangyu Chang,
Shuyi Wang, Jichuan Tang

Release v2.1.0. This repository holds the instruction suite, the frozen
prompts, the gate's reference implementation, the logged proposals and
verdicts of the experiments on the suite, and the analysis scripts that
compute the numbers the paper reports. The larger logs ship as release
assets. The practitioners' individual responses are not released, to protect
their privacy, and the section "What the release leaves out" names the
analyses whose inputs are therefore missing.

## What the benchmark tests

A large language model can turn a maintenance instruction into a proposed
change to a work-order schedule. A deterministic gate checks each proposal
and applies it, refers it to a person together with its price, or blocks it.
The gate makes this decision when the instruction is issued. At that instant
the site knows only part of the work in the dispatch window. The benchmark
tests the gate at this instant.

The decision instant of an instruction is the first instant at which every
order it names is known. The orders known at that instant form the known
board. The benchmark prices each proposal on the known board, and the gate decides
on the proposal from that price. The decision is then scored on the schedule
the site executes once every order of the window has arrived.

The instructions come from a suite generated from the FMUCD public
work-order corpus. The frozen suite holds 2,000 instructions, and 1,200 of
them carry an injected fault in one of six classes. Every instruction comes
with a reference proposal. The direct benchmark feeds these reference
proposals to the gate with no model in the loop. The end-to-end experiments
replay the logged proposals of eight language models.

## Repository layout

| Path | Contents |
|---|---|
| `code/suite/` | The frozen suite `v0.2` (2,000 instructions), its stated-acceptance extension `v1.1` (220 instructions and 220 negated controls), the held-out set `v0.3_heldout` (440) and three new draws of the suite, `v1.1_heldout_20261110`, `v1.1_heldout_20261111` and `v1.1_heldout_20261112` (2,000 each) |
| `code/l1suite/` | The suite generator |
| `code/l1guard/` | The gate's reference implementation: the schema, feasibility and quality stages, the certificate's analytic bound, the protocol 1.1 gate (`guard_v11.py`), the append-only log, the offline replay and the frozen prompts (`prompts.py`, versions 1.0.0 and 1.1.0). The module names keep the earlier word "guard" |
| `code/l1oracle/` | The CP-SAT oracle that brackets the optimum of a known board |
| `code/l1adapter/` | The read-only bridge to the scheduling environment |
| `code/schema/` | The adjustment schemas, versions 1.0.0 and 1.1.0 |
| `code/scripts/` | The experiment runners and the analysis scripts. A script named `nNN_*.py` writes the files `analysis/NNN_*` |
| `code/tests/` | The test suite |
| `analysis/` | The accepted analysis outputs. Each `*_macros.tex` file holds numbers the paper prints, and its header names the script that wrote it |
| `results/` | The logged proposals, verdicts and run records. The large logs ship as release assets, and `results/README.md` lists them |
| `manuscript/` | The macro files the paper reads: `macros.tex`, which `code/scripts/paper_macros.py` writes, and a copy of each `analysis/NNN_macros.tex` the paper reads. Three copies add a thousands separator to counts of 1,000 and above. `drafts/macro_names_used.tex` lists the macro names the manuscript used when N11 ran; `n11_stage2.py` and `n11_forecast.py` read it in place of the manuscript text to choose the decision-time twins they write |

## Installation

The code needs Python 3.11 and the scheduling environment of an earlier
paper, which the code imports read-only.

**1. Python packages.**

```bash
conda create -y -n certigate python=3.11
conda activate certigate
pip install -r requirements.txt
```

`requirements.txt` gives the versions the reported runs used. It also
describes the separate Python 3.12 environment with vLLM, which is needed
only to generate new proposals with a local open-weight model.

**2. The scheduling environment.** Clone the FM-Scheduling repository, check
out its release tag `v1.1`, and set `L1_Y1_ROOT` to the checkout. The tests
of this release were run on that tag.

```bash
git clone https://github.com/NTUZZH/FM-Scheduling.git
git -C FM-Scheduling checkout v1.1
export L1_Y1_ROOT="$PWD/FM-Scheduling"
mkdir -p "$L1_Y1_ROOT/data/processed"
tar -C "$L1_Y1_ROOT/data/processed" --zstd -xf "$L1_Y1_ROOT/data/instances.tar.zst"
```

**3. The instance corpora.** The instance archive of FM-Scheduling was
regenerated after this study's runs, and 46 of the 60 instances this study
replays differ from the files its logs were computed on. The decision-time
scripts read version 1.0 of the corpus from `data/processed/instances_v10`.
Its archive is in the history of the FM-Scheduling repository, at commit
`7198ee9`, which tag `v1.1` contains:

```bash
mkdir -p "$L1_Y1_ROOT/data/processed/instances_v10"
git -C "$L1_Y1_ROOT" show 7198ee9:data/instances.tar.zst \
  | tar -C "$L1_Y1_ROOT/data/processed/instances_v10" --strip-components=1 --zstd -xf -
```

The earlier scripts read `data/processed/instances`. The release asset
`instances_l1_snapshot.tar.zst` holds the 60 files they replay, as version
1.0 has them, and `instances_l1_snapshot.SHA256SUMS` lists their digests.
Unpack the snapshot over the regenerated corpus:

```bash
tar -C "$L1_Y1_ROOT/data/processed" --zstd -xf instances_l1_snapshot.tar.zst
```

The file `code/scripts/instance_manifest_l1.json` pins the 60 digests, and a
loader that reads an instance with another digest stops.

**4. The logs.** Download the release assets you need and unpack them at the
repository root, as `results/README.md` describes. The gate demo and the
regeneration of the paper's macro file need no asset.

## Quick start

Run every command from the repository root with `L1_Y1_ROOT` set. Nothing
below needs a GPU, an API key or a network connection.

**Run the tests.**

```bash
python -m pytest code/tests -q
```

Three test modules read logs that ship as release assets. Each of them is
skipped, with the asset named, until that asset is unpacked. With the assets
unpacked, run each of these modules on its own, because each one sets the
instance folder of its process when it is imported:

```bash
for m in test_n10 test_n11_forecast test_n14; do python -m pytest "code/tests/$m.py" -q; done
```

**See the gate decide.** The demo puts three hand-written proposals through
three gate configurations on one instance, logs them, and replays the log
offline:

```bash
python code/scripts/guard_demo.py
```

The feasible but costly proposal is applied without a certificate under the
feasibility-only gate and refused under the certificate, and the demo prints
the certified gap that justifies the refusal.

**Regenerate the paper's main macro file.** `code/scripts/paper_macros.py`
reads the accepted artifacts in `analysis/` and `results/` and writes every
macro of the paper's main macro file:

```bash
python code/scripts/paper_macros.py --out regenerated/macros.tex
```

It ends by listing the numbers that no accepted artifact carries, and that
list is empty.

## Replaying the direct benchmark at the decision instant

`code/scripts/n11_decision_time.py` implements the decision-time evaluation.
Its `census` stage replays the reference proposal of every suite item on the
known board at the item's decision instant. The stage prices each proposal
under every gate design and runs the realised schedule. The `oracle` stage
solves the relaxed boards with CP-SAT under a time budget. Its accepted
output ships in the asset `n11_oracle.tar.gz`, so a replay can skip this
stage. The `analyse` stage then writes the tables, the summary and the macro
file `analysis/N11_macros.tex`.

Each analysis script checks at start-up that it runs on the processor cores
assigned to it during the study. Set `CERTIGATE_ANY_CORES=1` to skip this
check on another machine, and pass the cores a stage may use with `--cores`:

```bash
export CERTIGATE_ANY_CORES=1
python code/scripts/n11_decision_time.py census --cores 0-1 --workers 2
python code/scripts/n11_decision_time.py analyse --cores 0-1 --workers 2
```

Both stages write into `results/n11_decision_time/` and `analysis/`, so run
them in a copy of the repository when you want to compare a fresh run with
the files on record. A failing assertion stops the stage, which then writes
the list of failures and exits with a non-zero status. To try one instance
first, add `--instances c10_replay_400_0000` to the `census` command. The
stage then writes into `results/n11_decision_time/smoke/`.

The census rows on record predate the rule that refuses an operation on
work already running at the decision instant. A fresh census therefore adds
the finding `names_running_work` to a few rows and the field
`names_running_any` to every row, while every terminal state stays the same.
`analysis/N11_summary.md` reports this rule as addition A.

## Recomputing the paper's numbers

Every number the paper prints is a macro. The macros of each analysis are in
`analysis/NNN_macros.tex`, next to a summary `analysis/NNN_summary.md` that
states each count and the rows it was counted from. The manuscript reads
copies of these files, which are in `manuscript/`. The header of each macro
file names the script that wrote it, and many headers also record the
SHA-256 of every input the script read.

The numbers in the abstract come from these files:

| Number | Value | Macro file | Script | Reproduction |
|---|---|---|---|---|
| `\nElevenIssuableAllItems` | 1,723 | `analysis/N11_macros.tex` | `code/scripts/n11_decision_time.py` | runs from a clone, with the assets |
| `\nSuiteInstances` | 60 | `manuscript/macros.tex` | `code/scripts/paper_macros.py` | runs from a clone |
| `\nEOneRowsTotal` | 78,000 | `manuscript/macros.tex` | `code/scripts/paper_macros.py` | runs from a clone |
| `\nEOneArmsWord` | eight | `manuscript/macros.tex` | `code/scripts/paper_macros.py` | runs from a clone |
| `\nTwentyEightAllPractitionersWord` | twenty-two | not in this release | `code/scripts/n28_field_r2.py` | needs the participants' files (not released) |
| `\nFifteenCostlyTwenty` | 186 | `analysis/N15_macros.tex` | `code/scripts/n15_composition.py` | runs from a clone, with the assets |
| `\nSixteenCertRefBothTwenty` | 168 | `analysis/N16_macros.tex` | `code/scripts/n16_robustness.py` | runs from a clone, with the assets |
| `\nFifteenCertMissBothTwenty` | 18 | `analysis/N15_macros.tex` | `code/scripts/n15_composition.py` | runs from a clone, with the assets |
| `\nTwentyEightInstructions` | 220 | not in this release | `code/scripts/n28_field_r2.py` | needs the participants' files (not released) |
| `\nTwentyEightYCostlyRefCertCount` | 58 | not in this release | `code/scripts/n28_field_r2.py` | needs the participants' files (not released) |
| `\nTwentyEightBPooledDeltaTwentyCostly` | 127 | not in this release | `code/scripts/n28_field_r2.py` | needs the participants' files (not released) |

Every macro file the paper reads has a script that writes it:

| Macro file | Macros | Command | Reproduction | Approximate minutes on one core |
|---|---|---|---|---|
| `manuscript/macros.tex` | 1,570 | `python code/scripts/paper_macros.py --out regenerated/macros.tex` | runs from a clone | under 1 |
| `manuscript/macros_n2.tex` | 879 | `python code/scripts/n2_pricing.py --macros --workers 1 --cores 14` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n3.tex` | 12,990 | `python code/scripts/n3_analyze.py --eval results/n3_eval_deepseek results/n3_eval_openai results/n3_eval_sol results/n3_eval_sonnet results/n3_eval_opus --neg-eval results/n3neg_eval_openai results/n3neg_eval_opus results/n3neg_eval_sol results/n3neg_eval_sonnet --macros` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n6.tex` | 367 | `python code/scripts/n6_rule_sensitivity.py --macros --workers 1 --cores 14` | runs from a clone, with the assets | 70 |
| `manuscript/macros_n8.tex` | 1,371 | `python code/scripts/n8_causal.py --workers 1 --cores 14` | runs from a clone, with the assets | 46 |
| `manuscript/macros_n9.tex` | 79 | `python code/scripts/n9_gates.py --cores 14 --workers 1` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n10.tex` | 279 | `python code/scripts/n10_field_change.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n11.tex` | 1,425 | `python code/scripts/n11_decision_time.py analyse --cores 8 --workers 1`<br>`python code/scripts/n11_stage2.py analyse2 --cores 8 --workers 1` | runs from a clone, with the assets | 3 |
| `manuscript/macros_n11f.tex` | 6,335 | `python code/scripts/n11_forecast.py analyse --cores 14 --workers 1` | runs from a clone, with the assets | 4 |
| `manuscript/macros_n12.tex` | 675 | `python code/scripts/n12_env_sensitivity.py analyse --env cal --workers 1`<br>`python code/scripts/n12_env_sensitivity.py analyse --env win050 --workers 1`<br>`python code/scripts/n12_env_sensitivity.py analyse --env win150 --workers 1`<br>`python code/scripts/n12_env_sensitivity.py analyse --env crew075 --workers 1`<br>`python code/scripts/n12_env_sensitivity.py analyse --env crew125 --workers 1`<br>`python code/scripts/n12_env_sensitivity.py report` | runs from a clone, with the assets | 2 |
| `manuscript/macros_n11f_paired.tex` | 530 | `python code/scripts/n11_paired.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n13.tex` | 4,132 | `python code/scripts/n13_fromlogs.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n14.tex` | 2,213 | `python code/scripts/n14_alt_dispatch.py analyse --cores 9` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n15.tex` | 665 | `python code/scripts/n15_composition.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n16.tex` | 1,631 | `python code/scripts/n16_robustness.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n17.tex` | 1,078 | `python code/scripts/n17_heldout.py analyse` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n18.tex` | 971 | `python code/scripts/n18_further_checks.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n20.tex` | 1,036 | `python code/scripts/n20_stratum_abs.py` | runs from a clone, with the assets | under 1 |
| `manuscript/macros_n19.tex` | 2,250 | `python code/scripts/n19_known_prompt_eval.py --force --workers 1 --log sonnet --log opus=results/grid_e1_known_opus_default/proposals_raw.jsonl,results/grid_e1_known_opus_disabled/proposals_raw.jsonl --control sonnet=results/grid_e1_control_sonnet/proposals_raw.jsonl --control opus=results/grid_e1_control_opus_default/proposals_raw.jsonl,results/grid_e1_control_opus_disabled/proposals_raw.jsonl` | runs from a clone, with the assets | 101 |
| `macros_n21.tex` (not in this release) | 2,079 | `python code/scripts/n21_field_instructions.py` | needs the participants' files (not released) |  |
| `macros_n22.tex` (not in this release) | 821 | `python code/scripts/n22_audit_annotator.py` | needs the participants' files (not released) |  |
| `macros_n22b.tex` (not in this release) | 2 | `python code/scripts/n22b_withheld_bound.py` | needs the participants' files (not released) |  |
| `manuscript/macros_n23.tex` | 1,471 | `python code/scripts/n23_urgent_orders.py` | runs from a clone, with the assets | 14 |
| `manuscript/macros_n24.tex` | 797 | `python code/scripts/n24_conventions.py` | needs the participants' files (not released) |  |
| `manuscript/macros_n25.tex` | 758 | `python code/scripts/n25_finish_to_start.py` | needs the participants' files (not released) |  |
| `manuscript/macros_n26.tex` | 515 | `python code/scripts/n26_shift_keeps_due.py` | runs from a clone, with the assets | 21 |
| `manuscript/macros_n27.tex` | 955 | `python code/scripts/n27_withheld_orders.py` | runs from a clone, with the assets | 29 |
| `manuscript/macros_n27b.tex` | 1,074 | `python code/scripts/n27b_withheld_all.py --from-stored` | runs from a clone, with the assets | under 1 |
| `macros_n28.tex` (not in this release) | 6,174 | `python code/scripts/n28_field_r2.py` | needs the participants' files (not released) |  |

A script marked "runs from a clone" was run for this release on a fresh copy of the repository, with every release asset unpacked, on one processor core with one thread, and each macro it wrote has the value of the shipped macro. Rows marked "with the assets" read logs that ship as release assets. Run each command from the repository root with `L1_Y1_ROOT` set and `CERTIGATE_ANY_CORES=1` exported, and run it in a copy of the repository, because the scripts overwrite their outputs in `analysis/` and `results/`. Where a command names `--cores`, pass the cores of your machine. The minutes come from that single run on a shared machine and are a guide only. A script marked "needs the participants' files" reads the practitioners' individual responses, which this release leaves out (see "What the release leaves out").

## What the release leaves out

The practitioners' individual responses are not released, to protect their
privacy. The release holds no file derived from a returned workbook, whether
a case-level record, a row-level record or a de-identified copy. Only the
aggregates that the paper prints remain, as macro values and as family-level
flags such as `in_disputed_families` in `analysis/N25_rows.csv`. The release
therefore holds the scripts of the analyses below without their inputs. The
macro files of the first three analyses stay out as well, and the paper
reports their results. The macro files of the last two analyses ship,
because they hold counts of suite items only. Every gate verdict on the
suite is recomputable from the released logs.

| Analysis | Script | Input that is not released |
|---|---|---|
| The practitioners' instructions (N21) | `code/scripts/n21_field_instructions.py` | the instructions as each practitioner wrote them, each respondent's answers about their role and experience, and the folder `results/field_v1/`, which holds the workbook provenance, the design choices, the spend log, the prompt metadata and the model calls on the instructions |
| The second set of practitioners' instructions (N28) | `code/scripts/n28_field_r2.py`, `code/scripts/field_cards_r2.py` | the instructions of the second set as each practitioner wrote them, each respondent's answers about their role and experience, the folder `results/field_r2/`, which holds the same kinds of record as `results/field_v1/` and the logs of the runs, and the withheld files of N21 and N22 that the two scripts also read |
| The practitioner audit (N22 and N22b) | `code/scripts/n22_audit_annotator.py`, `code/scripts/n22b_withheld_bound.py` | the panel members' ratings, roles and comments, and the folder `results/practitioner_audit_r2_scored/`, which holds the case-level vote counts and scores under protocol 1.2 |
| The planner's check of 194 suite rows | `code/scripts/suite_sample_check_score.py` | the planner's returned workbook and the folder `results/suite_sample_check_scored/`, which holds the scored report with the planner's defect notes and the 48 rows the planner disputed |
| The two disputed conventions (N24) | `code/scripts/n24_conventions.py` | the 48 disputed rows, the planner's defect notes and the audit numbers above, and the summary `analysis/N24_summary.md`, which lists the 48 rows |
| The finish-to-start reading of the precedence operation (N25) | `code/scripts/n25_finish_to_start.py` | the 48 disputed rows and the planner's defect notes, which it reads through `n24_conventions.py` to form the subsets without the disputed families |

The planner is a maintenance planning manager outside the author team. A
script that needs a withheld file stops and names the file. Paths under
`participant_files/` in these scripts name the returned workbooks and the
packs sent to the participants. Paths under `design_notes/` name the
pre-specified designs and the decision record, which a few analysis scripts
hash or quote. The release holds neither folder.

`results/practitioner_audit_r2/` holds the audit's cases as they were sent
to the panel, and `code/suite/*/audit_sample.csv` holds the
planner's sample as it was drawn. Neither holds a response.

## Where the logs are

`results/` holds one folder per experiment. The summaries, run records and
small logs are in this repository, and the large logs ship as release
assets that unpack into the same folders. `results/README.md` lists every
experiment, its folder and its asset.

## Provenance of the released files

The released files differ from the run copies in three ways. Machine paths
are masked. The release writes the scheduling checkout as `${L1_Y1_ROOT}`,
which the code resolves to the checkout in use, and the project folder as
`.` in data files and as `<project>` in text. Comments that pointed to
unreleased notes are reworded. Each changed file thus has a new SHA-256
digest, so every digest that a released file records for another released
file is re-pinned to the released bytes. A released script that checks a
digest therefore finds the file it expects.

Nine analysis scripts and four test modules were edited after the runs.
Eight of the scripts read a design note, a manuscript draft or a figure
script that this release leaves out, and they stopped when that file was
absent. In the release, each of them records the missing file as `not shipped` and
goes on. Where a script took constants from a figure script, the released script holds the
same values and compares them with the figure script whenever that script is
present. The ninth, `n24_conventions.py`, held the 48 rows the planner
disputed in its source. The released script reads them from the planner's withheld check,
and its macro file is unchanged. The four test modules skip a test until the
asset it reads is unpacked, use the rule names of FM-Scheduling `v1.1`, and
give a mock run the two repeats per item that its analysis requires. One of
them, `test_paper_macros.py`, compares the macro definitions of
`manuscript/macros.tex` with a fresh render and leaves out the comparison of
the whole file, because the release rewords comments of that file in place.
The script `n16_robustness.py` needs the same change as the eight scripts, but
six later scripts assert the digest it had when it ran. The release
therefore changes only its own copy of `n16_robustness.py` and re-pins those
six assertions to the released file. `RELEASE_CHANGES.csv` lists each
changed file with its digest in the project and in this release. For the
thirteen edited files, its column `run_sha256` adds the digest at the time
of the runs, so a digest quoted from a run can still be traced to the
released file.

## Licence

The code is released under the MIT licence (`LICENSE`). The instance files
derive from the FMUCD corpus (DOI 10.17632/cb8d2nsjss.1) and carry its
CC BY-NC 4.0 terms.

## Citation

Citation to be added upon publication.
