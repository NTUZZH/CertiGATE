# DG19. Certificate tightness: is a certified gap the bound's slack or the schedule's?

Generated 2026-08-23 11:39:18 +0800 by `code/scripts/cert_tightness.py` (l1-dg19-cert-tightness-1). Wall 91.8 s, single process, CPU only.

## The question, and the answer

The certified gap divides by an analytic lower bound, so a refusal could mean the executed schedule is far from the best the instance admits, or it could mean the bound is loose. Wherever CP-SAT closed an instance the two readings separate: the proved optimum replaces the bound and the same row is read twice.

On the 108 rows with a proof and a strictly positive objective at the 5 s budget (15 instances), the certified gap exceeds the gap to the proved optimum by a median of 3.92e-04 and never by more than 1.18e-03. At 1 s (85 rows, 13 instances) the median is 3.77e-04 and the maximum is the same 1.18e-03. Against the frozen tolerance tau = 0.2, slack of that size can only carry a row across the threshold if its gap to the proved optimum is already at least 0.1988.

Two facts sharpen that. On 69 of the 108 headline rows at 5 s (63.9%) the certified gap is exactly zero, so the analytic bound already equals the realized objective and there is no slack at all to measure. The largest excess quoted above is carried by those rows, and it is the CP-SAT model's centi-business-hour grid rather than slack; restricted to the rows whose certified gap is strictly positive, the largest excess is 6.44e-04 at 5 s.

So on the rows where the question can be settled, a certified gap is a statement about the schedule and not about the bound. What that does and does not license is set out under *Coverage boundary* below, and the boundary is the first thing to read. That second cut was made after the first run and is marked post hoc wherever it appears.

## Four launch questions, answered before the run

```
FOUR LAUNCH QUESTIONS (the project's standing experiment rules), answered before the run
---------------------------------------------------------------------------------
1. PURPOSE.  One number closes the question above: the distribution of
   ``excess`` on every row where the solver proved optimality, at both logged
   budgets.  It lands in the certificate-protocol discussion, next to the Tier-1
   vs Tier-2 exhibit, and in the paper.  A second, smaller
   number lands with it: the tolerance headroom ``tau - max(excess)``, the true
   gap a row must already carry before slack of the measured size could push it
   across tau.
2. EXPECTED RESULT.  The Tier-1 slice already reports that the solver bound
   exceeds the analytic one by a median 0.054% (1 s) and 0.095% (5 s) on the
   rows where it is tighter at all, so ``excess`` is expected to be of that
   order, three orders below tau = 0.20.  If it comes back that small, a
   certified gap is a statement about the schedule and not about the bound, and
   the false blocks the benchmark records are genuinely poor schedules on the
   rows we can check.  If instead ``excess`` reaches a few percent, the
   certificate's false-block cost is partly an artifact of the bound, the paper
   must say so, and the Tier-1 refinement stops being optional.  The two
   outcomes lead to different sentences, so the analysis is not redundant.
   Neither outcome is a finding about the storm strata, where the solver proves
   nothing; see COVERAGE BOUNDARY.
3. CONTAMINATION.  Replay only.  No API call, no model, no GPU, no solver: every
   quantity is arithmetic on ``results/tier1_slice/rows.jsonl``, which is on
   disk and whose sha256 is recorded in two files this script reads back rather
   than restates.  Nothing under ``results/`` or ``the manuscript folder`` is written.  The
   only randomness is the cluster bootstrap, at a fixed seed.  The single risk
   is a stale or partially written input, which the digest checks close.
4. DATA ACCURACY.  The population is the frozen 444-row Tier-1 slice, joined to
   nothing.  Before any new number is computed, two input digests are checked
   against the digests other files on disk recorded for the same inputs, and
   thirty-seven already-published values are recomputed from the raw rows and
   compared with ``manuscript/macros.tex``, including the two proved-optimal shares that fix
   this analysis's own denominator (27.3% at 1 s, 32.4% at 5 s) and the three
   per-stratum proved-optimal shares that fix its coverage (79.1% / 94.1% on
   c10_replay_400, 0.0% on both storm strata at both budgets).  A mismatch
   aborts before a single tightness number is produced.
```

## Declared design

```
DECLARED DESIGN (fixed before the results were computed)
--------------------------------------------------------
POPULATIONS, per budget b in {1 s, 5 s}:

  ``slice``             all 444 rows of the Tier-1 slice.  Every one of them is
                        a row the deployed certificate ACCEPTED
                        (``applied_with_certificate``); the slice carries no
                        blocked row.  Asserted, not assumed.
  ``optimal_all``       rows with ``tier1_status == 'OPTIMAL'`` and a non-null
                        incumbent.  This is the census of rows on which the
                        question can be answered at all.
  ``optimal_positive``  ``optimal_all`` restricted to ``obj_bh > 0``.  THE
                        HEADLINE POPULATION.
  ``optimal_zero``      the complement, ``obj_bh == 0``.  Weighted tardiness is
                        non-negative, so a schedule with objective 0 attains the
                        minimum, which forces ``LB2 == OPT == obj == 0`` and
                        ``gap_certified == gap_true == excess == 0`` identically.
                        The split is structural, not data-dependent: it is a
                        property of the objective's range, not of the numbers
                        this script computes.  Both populations are reported so
                        that neither the informative subset nor the full census
                        can be read alone.

CLUSTER: ``instance_id``.  Rows of the slice sit several to an instance (seven
arms, two classes, repeats), and rows on one instance share its optimum, so the
instance is the independent unit.

CONVENTIONS:
  ``LB_FLOOR_BH = 1.0``      the certificate's own floor, applied to both gaps.
  ``gap_certified``          ``(obj_bh - lb_tier2_bh) / max(lb_tier2_bh, 1.0)``
  ``gap_true``               ``(obj_bh - tier1_incumbent_bh) / max(tier1_incumbent_bh, 1.0)``
  ``excess``                 ``gap_certified - gap_true``
  ``slack_abs_bh``           ``tier1_incumbent_bh - lb_tier2_bh``, the bound's
                             slack in business hours
  ``slack_rel``              ``slack_abs_bh / max(lb_tier2_bh, 1.0)``, the
                             relative tightening the analytic bound would need
                             to reach the proved optimum.  Reported because it
                             is the quantity the false-block rescue analysis
                             (``analysis/DG2_tier1_rescue.csv``) states its
                             REQUIRED tightening in, so achievable and required
                             can be compared on one scale.
  ``TAU_PUBLISHED = 0.20``   the frozen operating point.

REPORTED STATISTICS: min, q25, median, q75, IQR, p90, max, mean of ``excess``
and of ``slack_rel``, overall and per stratum, arm and primary class, at both
budgets.  Quantiles use numpy's linear interpolation, and the point estimate
and the interval use the same convention.

INTERVALS: cluster bootstrap over ``instance_id``, B = 20,000 replicates,
2.5 / 97.5 percentile, seed 20260823.  A replicate draws K instances with
replacement and pools their rows.  Intervals are reported only for groups with
at least 5 instances; below that a percentile interval is not informative and
the cell is left blank rather than filled with a number nobody should read.
The max is reported as observed, never with an interval: the bootstrap
distribution of a sample maximum is degenerate and its percentile interval
would be misleading.

SELECTION POLICIES: none beyond the declared populations.  Every population is
a census of the rows meeting a condition fixed in advance; nothing is chosen
after seeing a result, no threshold is searched, no group is dropped.

SEEDS: ``SEED = 20260823``, used by the bootstrap only.  Nothing else samples.
```

## Coverage boundary

CP-SAT proves optimality on one stratum only. The table is the whole slice, not the proved subset, so the denominators are visible.

| stratum | rows in slice | instances | closed at 1 s | closed at 5 s |
|---|---|---|---|---|
| c09_storm2_w80 | 151 | 22 | 0 (0.0%) | 0 (0.0%) |
| c10_storm2_w80 | 140 | 12 | 0 (0.0%) | 0 (0.0%) |
| c10_replay_400 | 153 | 24 | 121 (79.1%) | 144 (94.1%) |

Three limits follow, and none of them is removable with the data on disk.

1. **The storm strata contribute no proof at all.** Every number below is measured on `c10_replay_400`, the small replay instances. The certificate's benign false blocks concentrate on the storm strata, where the solver returns a vacuous bound at both budgets, so the tightness reported here transfers to them only by assumption.
2. **Every row of the slice is a row the certificate ACCEPTED.** The slice was drawn from certified verdicts, so its largest certified gap is 0.1965, below tau. The slack is therefore measured off the refusal boundary rather than on it.
3. **The proofs come from few instances.** 15 distinct instances carry the 108 headline rows at 5 s, so the cluster bootstrap has 15 clusters and its intervals are coarse.

## Inputs

| file | sha256 |
|---|---|
| `results/tier1_slice/rows.jsonl` | `b43875f5c938c9d2e814a76d088bde22ba6655e88fbead88a3e2c5d38b255093` |
| `results/tier1_slice/summary.json` | `d874d70fada2cac9f9d3d27c4829ccd654308bc5218fd1ceb8e94aa7961ce06c` |
| `analysis/DG2_tier1_rescue_rows.jsonl` | `3e562221331f7e785305fce8b8676f1cc97db7d9e2cef7acb3396ef54af5584f` |
| `analysis/DG2_tier1_rescue.csv` | `dd4677b906898894c7e3dfc417b4871b901597da2ae3c41000716d1afd5bf526` |
| `manuscript/macros.tex` | `4365f466cdc21c5c95584553898bc195dbb61eb784ebc436ee130b8fc85b7bc2` |

The digest of `results/tier1_slice/rows.jsonl` is compared with the one `analysis/DG2_tier1_rescue.csv` recorded when it read the same file, and the digest of `results/tier1_slice/summary.json` with the one `manuscript/macros.tex` records, so neither is a literal typed into this script.

## Self-check

1583 assertions passed. 39 of them run before any tightness number is produced. Two compare an input's sha256 with the digest another file on disk recorded for the same input. The other 37 recompute an already-published value from the raw rows and compare it with `manuscript/macros.tex`: the three sample sizes, the two reproduction counts, and per budget the tighter, vacuous and proved-optimal shares, the median and maximum relative tightness delta, the median and maximum gap movement, the median solve and Tier-2 bound walls, the Tier-1-only refusal share, and the proved-optimal and vacuous shares of each of the three strata. The remainder are row-level identities: the recomputed certified gap against the row's own `gap_tier2`, `t2_gap` and `accepted_gap` to 1e-12; the solver's bound against its incumbent on every proved row; the schedule digest; the containment of the 1 s proof set in the 5 s one; and the sign of the excess.

## The distribution of the excess

`excess` is the certified gap minus the gap to the proved optimum, on one row, at one budget. The headline population is the proved rows with a strictly positive objective; the 36 rows whose objective is exactly zero are shown separately, where both gaps are zero by construction because weighted tardiness cannot fall below zero.

Before the distribution, one fact about it. On 69 of the 108 headline rows at 5 s (63.9%) the certified gap is exactly zero: the analytic bound already equals the realized objective, so the certificate proves the schedule optimal with no solver involved. On those rows the excess is not slack, because there is none; it is the CP-SAT model's centi-business-hour grid putting the discretized optimum a fraction above the continuous one, which shows up as a slightly negative proved gap. They carry the largest excess values in the table, which is why the post-hoc cut below reports the 39 rows with a strictly positive certified gap on their own.

**Budget 1 s.**

| population | rows | instances | median certified gap | median proved gap | median excess | quartiles | p90 | max | mean | median 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|
| optimal_all | 121 | 21 | 0.0000 | 0.0000 | 1.58e-04 | [0.00e+00, 3.96e-04] | 6.45e-04 | 1.18e-03 | 2.65e-04 | [0.00e+00, 3.87e-04] |
| optimal_positive | 85 | 13 | 0.0000 | 0.0000 | 3.77e-04 | [1.58e-04, 5.48e-04] | 6.45e-04 | 1.18e-03 | 3.77e-04 | [1.58e-04, 5.48e-04] |
| optimal_zero | 36 | 8 | 0.0000 | 0.0000 | 0.00e+00 | [0.00e+00, 0.00e+00] | 0.00e+00 | 0.00e+00 | 0.00e+00 | [0.00e+00, 0.00e+00] |
| posthoc_gap_positive | 35 | 6 | 0.0163 | 0.0160 | 3.51e-04 | [1.58e-04, 3.96e-04] | 5.12e-04 | 6.28e-04 | 2.94e-04 | [1.58e-04, 4.67e-04] |

`posthoc_gap_positive` was added after the first run and is not part of the declared design; it is the last row for that reason.

**Budget 5 s.**

| population | rows | instances | median certified gap | median proved gap | median excess | quartiles | p90 | max | mean | median 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|
| optimal_all | 144 | 23 | 0.0000 | 0.0000 | 3.03e-04 | [0.00e+00, 5.48e-04] | 7.54e-04 | 1.18e-03 | 3.30e-04 | [0.00e+00, 5.40e-04] |
| optimal_positive | 108 | 15 | 0.0000 | -0.0002 | 3.92e-04 | [1.89e-04, 6.45e-04] | 7.54e-04 | 1.18e-03 | 4.40e-04 | [1.89e-04, 6.45e-04] |
| optimal_zero | 36 | 8 | 0.0000 | 0.0000 | 0.00e+00 | [0.00e+00, 0.00e+00] | 0.00e+00 | 0.00e+00 | 0.00e+00 | [0.00e+00, 0.00e+00] |
| posthoc_gap_positive | 39 | 7 | 0.0242 | 0.0237 | 3.52e-04 | [1.58e-04, 4.68e-04] | 5.68e-04 | 6.44e-04 | 3.25e-04 | [1.58e-04, 5.41e-04] |

`posthoc_gap_positive` was added after the first run and is not part of the declared design; it is the last row for that reason.

Intervals are a cluster bootstrap over `instance_id`, B = 20,000 replicates, 2.5 / 97.5 percentile, seed 20260823 offset per cell. The maximum is reported as observed and never with an interval.

### The same rows, by arm and by class

The headline population only. Every proved row sits in `c10_replay_400`, so the per-stratum split is the overall row and is not repeated.

**Budget 1 s.**

| group | rows | instances | median excess | p90 | max | median 95% CI |
|---|---|---|---|---|---|---|
| arm glm-4-9b | 13 | 10 | 3.03e-04 | 5.46e-04 | 1.18e-03 | [0.00e+00, 4.72e-04] |
| arm openai | 6 | 3 | 9.10e-04 | 1.18e-03 | 1.18e-03 | n/a |
| arm opus | 26 | 9 | 3.64e-04 | 6.28e-04 | 6.45e-04 | [0.00e+00, 4.69e-04] |
| arm qwen3-14b | 8 | 6 | 3.27e-04 | 6.24e-04 | 1.18e-03 | [1.58e-04, 3.87e-04] |
| arm qwen3.6-27b-fp8 | 11 | 9 | 3.96e-04 | 6.45e-04 | 1.18e-03 | [1.89e-04, 6.45e-04] |
| arm sol | 11 | 6 | 3.03e-04 | 6.45e-04 | 1.18e-03 | [1.58e-04, 6.45e-04] |
| arm sonnet | 10 | 9 | 3.27e-04 | 5.57e-04 | 6.45e-04 | [1.51e-04, 5.41e-04] |
| class V3 | 16 | 5 | 3.78e-04 | 5.48e-04 | 6.28e-04 | [0.00e+00, 4.69e-04] |
| class V4 | 35 | 12 | 3.87e-04 | 1.18e-03 | 1.18e-03 | [1.58e-04, 6.45e-04] |
| class benign | 34 | 13 | 3.03e-04 | 6.45e-04 | 1.18e-03 | [1.58e-04, 5.48e-04] |

**Budget 5 s.**

| group | rows | instances | median excess | p90 | max | median 95% CI |
|---|---|---|---|---|---|---|
| arm glm-4-9b | 16 | 12 | 3.87e-04 | 7.54e-04 | 1.18e-03 | [0.00e+00, 5.48e-04] |
| arm openai | 8 | 5 | 6.99e-04 | 1.18e-03 | 1.18e-03 | [2.70e-04, 1.18e-03] |
| arm opus | 34 | 11 | 4.22e-04 | 6.45e-04 | 7.54e-04 | [1.58e-04, 6.28e-04] |
| arm qwen3-14b | 13 | 8 | 3.87e-04 | 7.54e-04 | 1.18e-03 | [1.58e-04, 7.54e-04] |
| arm qwen3.6-27b-fp8 | 12 | 10 | 4.68e-04 | 6.45e-04 | 1.18e-03 | [1.89e-04, 6.45e-04] |
| arm sol | 14 | 7 | 3.87e-04 | 7.54e-04 | 1.18e-03 | [1.58e-04, 7.54e-04] |
| arm sonnet | 11 | 10 | 3.51e-04 | 6.45e-04 | 7.54e-04 | [1.89e-04, 5.48e-04] |
| class V3 | 20 | 6 | 4.22e-04 | 6.29e-04 | 6.44e-04 | [0.00e+00, 5.91e-04] |
| class V4 | 45 | 14 | 3.96e-04 | 1.01e-03 | 1.18e-03 | [1.58e-04, 7.54e-04] |
| class benign | 43 | 15 | 3.87e-04 | 7.54e-04 | 1.18e-03 | [1.58e-04, 5.48e-04] |

## What the measured slack can do at tau = 0.2

| budget | rows | largest excess | largest relative bound slack | gap to the proved optimum a blocked row must already carry |
|---|---|---|---|---|
| 1 s | 85 | 1.18e-03 | 1.18e-03 | 0.1988 |
| 5 s | 108 | 1.18e-03 | 1.18e-03 | 0.1988 |

The last column is `tau - max(excess)`. A row refused at tau = 0.2 whose bound carried slack of the largest size measured here would still have been within 0.0012 of the tolerance on its proved gap, so slack of this magnitude cannot manufacture a refusal on its own; it can only move a row that was already at the boundary.

On the post-hoc cut, the rows carrying a strictly positive certified gap, the largest excess is 6.28e-04 at 1 s and 6.44e-04 at 5 s and the last column becomes 0.1994. The looser figure in the table is the exactly tight rows' discretization residue, not slack.

## The one blocked item CP-SAT closed

The tightness above is measured on accepted rows. One blocked benign item in the false-block population sits on a replay instance the solver could close, and it is the only direct reading of a refusal.

| item | instance | budget | objective (bh) | Tier-2 bound | proved optimum | certified gap | proved gap | excess |
|---|---|---|---|---|---|---|---|---|
| BEN-0699 | c10_replay_400_0020 | 5 s | 144.6112 | 106.0000 | 106.0800 | 0.3643 | 0.3632 | 1.03e-03 |

The schedule that proposal produced really does sit 36.3% above the proved optimum, against a tolerance of 20%. The bound's slack accounts for 1.03e-03 of the 0.3643 certified gap. The block is the schedule's, not the bound's. One proposal is one row of the blocked population, and this one was produced by qwen3-14b on 3 logged rows.

The same comparison across the whole blocked population is indirect but one-sided. The population is 112 distinct blocked benign proposals, one per proposal digest, covering 372 logged blocked rows over 35 suite items. Each would have needed the Tier-2 bound to tighten by a stated amount to be accepted at tau: the smallest such requirement is 0.0200 and the median is 0.0606. The largest relative bound slack measured anywhere a proof exists is 1.18e-03, so the smallest requirement is 17 times that slack and the median requirement 52 times it. That comparison crosses strata, so it bounds nothing formally; it is reported as the scale it is.

## Caveats

1. **The proved optimum is the optimum of a relaxation, on a discretized grid.** The CP-SAT model carries the adjusted instance's fields but not the proposal's dispatch constraints, and it scales business hours by 100, rounding processing times and releases up. Both tiers bound the same relaxation, so the comparison is like for like, and the rounding pushes the discretized optimum slightly above the continuous one. The excess reported here is therefore an over-estimate of the true slack rather than an under-estimate.
2. **The proved gap is negative on some rows.** On 57 of the 108 headline rows at 5 s the executed schedule's objective sits fractionally below the discretized optimum, by at most 1.18e-03 in relative terms. That is the discretization in caveat 1 made visible, not a violation of optimality.
3. **Accepted rows only, one stratum, few clusters.** Restated from *Coverage boundary*, because it governs every number above.
4. **No new computation.** Every quantity is arithmetic on the frozen Tier-1 slice; no solver ran, no model was called, and the only draw is the seeded bootstrap.

Long form, every row and every summary: `analysis/DG19_tightness.csv`.
