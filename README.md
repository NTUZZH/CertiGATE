# CertiGATE

**CertiGATE: A Guard Benchmark and Quality-Certificate Protocol for Large
Language Model-Based Work-Order Scheduling in Facility Management**

Ziheng Zhang, Tzu Pei Ku Chia, Xiaofei Yang, Xiangyu Chang, Shuyi Wang,
Wei Zhang

---

When a language model is used to change a facility-management work-order
schedule, a deterministic validator sits between the model and the plan and
decides whether the proposed change may be applied. CertiGATE makes that
validator, not the model, the system under test. It provides an
injected-violation suite of 2,000 labelled dispatcher instructions over a
replayable work-order dispatch environment, a reference guard that checks a
proposal in three stages and certifies the optimality gap of everything it
accepts, and the complete logged proposals and verdicts of eight language
models evaluated single-turn and six evaluated as guarded single-agent and
multi-agent systems at matched token budgets. This repository is the artifact
behind the paper: the suite, the frozen prompts, the guard, the raw logs, and
the scripts that turn those logs into every number the paper prints.

## Repository layout

| Path | What it holds |
|---|---|
| `code/l1suite/` | The suite generator: templates, phrasing registers, violation codes, integrity checks |
| `code/suite/v0.2/` | The **frozen violation suite**: `suite.jsonl` (2,000 labelled items), its manifest, statistics and audit sample |
| `code/suite/v0.1/` | The earlier suite revision, kept so the freeze is auditable |
| `code/l1guard/` | The **guard reference implementation**: the three stages, the certificate's analytic bound with its solver-based diagnostic, the closed finding vocabulary, the append-only proposal log, the offline replay, and the **frozen prompts** (`prompts.py`) |
| `code/l1adapter/` | The read-only bridge to the scheduling environment: schema-checked operations, application, re-dispatch, scoring |
| `code/schema/` | The frozen adjustment schema the proposer must satisfy |
| `code/scripts/` | Experiment runners and the analysis scripts, including `paper_macros.py` |
| `code/tests/` | 635 tests over the adapter, the guard, the suite and the analysis |
| `analysis/` | The accepted analysis artifacts: tables T1-T6, diagnostics D1-D3, agent-experiment tables E7-E13, and the trustworthiness ladder. These are what the paper's numbers are read from |
| `results/` | The logged proposals and verdicts. Large raw logs ship as release assets; see `results/README.md` |

Class counts in the frozen suite: 800 benign instructions and 1,200 with an
injected violation, split as V1 schema violation (160), V2 infeasibility (200),
V3 quality failure (220), V4 semantic mistranslation (220), V5 overreach on an
ambiguous instruction (200) and V6 instruction-embedded injection (200). The
800 items in V1 to V4 are each paired with a matched benign twin, which is what
makes a false block measurable; V5 and V6 are unpaired.

Docstrings occasionally cite the project's internal decision log by filename.
That log is not part of this release; every decision it records that affects a
published number is stated in the paper.

## Environment

Two things are needed beyond a Python interpreter.

**1. The scheduling environment.** CertiGATE evaluates proposals against the
work-order dispatch environment published with an earlier paper, at
[github.com/NTUZZH/FM-Scheduling](https://github.com/NTUZZH/FM-Scheduling). That
repository is imported read-only and never modified. Clone it, unpack its
instance archive, and point `L1_Y1_ROOT` at it:

```bash
git clone https://github.com/NTUZZH/FM-Scheduling.git
cd FM-Scheduling
mkdir -p data/processed && tar -C data/processed --zstd -xf data/instances.tar.zst
export L1_Y1_ROOT="$PWD"
```

**2. A Python environment.** Python 3.11 with the analysis dependencies is
enough for everything in this README:

```bash
conda create -y -n certigate python=3.11
conda activate certigate
pip install jsonschema==4.26.0 pytest==9.1.1 pandas==3.0.3 numpy==1.26.4 ortools==9.14.6206
```

`requirements.txt` lists these with the versions the reported runs used, and
documents the separate Python 3.12 + vLLM environment needed only to generate
new proposals with a local open-weight model. Generating new proposals from a
hosted model needs no extra package, only a `.env` file at the repository root
holding `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `DEEPSEEK_API_KEY`; the
runners load it into their own process and nothing else.

## Quickstart

Run from the repository root, with `L1_Y1_ROOT` set.

**See the guard decide.** Three hand-written proposals, one clean, one
infeasible, one feasible but poor, are put through all three guard
configurations on a real instance, logged, and then replayed offline to show
that the replayed verdict is the verdict:

```bash
python code/scripts/guard_demo.py
```

The last block of output is the point of the paper in miniature: the feasible
but poor proposal is `applied_uncertified` under a feasibility-only guard and
`blocked_qual` under the certificate, with the gap that justifies the refusal
printed next to it.

**Run the tests.** 634 pass and 1 skips in about 45 seconds:

```bash
python -m pytest code/tests -q
```

The one skip is the check that the manuscript's macro file is current, which
needs a manuscript checkout. Nothing here needs a GPU or an API key.

**Regenerate the paper's numbers.** `paper_macros.py` is the only writer of the
manuscript's macro file, and every macro body comes from an accepted artifact
in `analysis/` or `results/`. It runs from a plain clone with nothing
downloaded:

```bash
python code/scripts/paper_macros.py --out /tmp/macros.tex
```

It prints the 959 macros it wrote, grouped by the claim they support, and ends
with the list of numbers no accepted artifact carries. That list is empty.

## Regenerating every number

The paper's numbers come from three layers, and each layer asserts itself
against the one below rather than restating it. A mismatch stops the run.

| Step | Command | Produces | Needs release assets |
|---|---|---|---|
| Multi-turn agent tables | `python code/scripts/e3_analyze.py` | `analysis/E7`-`E13` | no |
| Trustworthiness ladder | `python code/scripts/ladder_replay.py` | `analysis/ladder/` | yes |
| Main tables | `python code/scripts/paper_tables.py` | `analysis/T1`-`T6`, `D1`, `D2` | yes |
| Translation fidelity | `python code/scripts/d3_translation_equivalence.py` | `analysis/D3` | yes |
| Every cited number | `python code/scripts/paper_macros.py` | the manuscript's macro file | no |

`e3_analyze.py` takes about seven minutes and re-derives the multi-turn
experiment from its raw call logs: 7,580 assertions and 120,960 verdict-field
comparisons against the accepted offline replay, all of which must pass.
`paper_tables.py` and `ladder_replay.py` read the single-turn proposal and
verdict logs, which ship as release assets; unpack them at the repository root
first, or pass `--results-root`. `paper_tables.py --skip-d1` still needs the
verdict logs, because the certificate-tolerance table re-derives its curves
from them.

Each script writes to `analysis/` by default and takes `--out` to write
somewhere else, which is the safe way to compare a fresh run against the
accepted artifacts already in the tree.

## Results and release assets

`results/` in this repository holds every accepted summary and run manifest,
and the complete raw logs of the multi-turn agent experiment, the
certificate-tolerance sweep, the two-bound comparison and the suite
acceptance gate: 66 MB in all. The single-turn proposal and verdict logs are
much larger, so they ship as per-experiment archives attached to the GitHub
release: 48 MB compressed, 557 MB unpacked, with a `SHA256SUMS.txt` to check
what you downloaded. `results/README.md` lists every archive, its size, and
which script needs it.

## Reproducibility

The suite and the schema are content-addressed, and every runner asserts their
SHA-256 at start-up rather than trusting the file on disk. The frozen suite is
`0a0b471f4d04ba03...` and the frozen adjustment schema is `1115fa83d8910ed1...`;
a runner whose input does not hash to these refuses to start. Every logged
proposal carries the SHA-256 of the prompt that produced it and the hash of the
guard configuration that judged it, so any row can be re-decided offline with
`l1guard.replay` and compared against the verdict on record.

## License

MIT. See `LICENSE`.

## Citation

Citation to be added upon publication.

## Reviewer-response analyses

The following artifacts answer specific questions about the guard's own
behaviour, the uncertainty on the reported rates, and the boundaries of the
tolerance. Each script regenerates its own tables and self-checks against an
already-published quantity before writing.

| Artifact | Question it answers | Script |
|---|---|---|
| `analysis/DG1_direct_guard*` | What does the guard do when the canonical proposal is fed to it directly, with no model in the loop? | `code/scripts/direct_guard_benchmark.py` |
| `analysis/DG2_falseblock*`, `DG2_tier1_rescue*` | How much of the false-block rate is slack in the analytic bound rather than proposal quality? | `code/scripts/falseblock_decompose.py` |
| `analysis/DG3_prevalence*` | How do the ladder means read at violation prevalences other than the suite's own? | `code/scripts/prevalence_reweight.py` |
| `analysis/DG4_tau_cost_rule*` | Which tolerance does a declared cost rule select, and does it agree with the reported operating point? | `code/scripts/tau_cost_rule.py` |
| `analysis/DG5_e1_intervals*` | What are the cluster-bootstrap intervals on the headline rates, and where do the false blocks land? | `code/scripts/e1_intervals.py` |
| `analysis/DG6_e3_intervals*` | Are the two agent architectures equivalent within a declared margin, and what could the design detect? | `code/scripts/e3_intervals.py` |
| `analysis/DG7_passthrough*` | What is violation pass-through under each denominator, and per class? | `code/scripts/passthrough_decompose.py` |
| `analysis/DG8_*` | How often does the gap floor bind, do the certified gaps match the ground truth item by item, and what shape does the provider refusal wall have? | `code/scripts/dg8_floor.py`, `dg8_gap_agreement.py`, `dg8_refusals.py` |
| `analysis/DG11_e3_exposure*` | How far did the retired guard-v0.1 rule reach into the recorded E3 trajectories, and what do the loop statistics look like without the touched items? | `code/scripts/e3_exposure.py` |
| `analysis/DG12_guard_relaxation*` | Does guard v0.2 accept a strict superset of what v0.1 accepted on every recorded E3 proposal? | `code/scripts/guard_relaxation_audit.py` |
| `analysis/DG13_practitioner_audit*` | Do independent facility-management practitioners agree with the suite's labels, and can they read the guard's output? | `code/scripts/practitioner_audit.py` (input: `results/practitioner_audit/cases.csv`) |
