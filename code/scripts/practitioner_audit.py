#!/usr/bin/env python
"""DG13: what five practitioners said about the suite's own dispositions.

The suite decides, for every item, whether a proposal should be applied,
rejected or referred, and the manuscript reports rates against those decisions.
A reviewer can reasonably ask whether the decisions themselves are the ones a
scheduler would make.  Thirty cases were therefore read by five practitioners,
each of whom recorded a disposition and rated the case on four four-point
scales.  This script turns that record into the numbers Section 6 cites.

WHAT THE RECORD CONTAINS
------------------------
``results/practitioner_audit/cases.csv``, one row per case, de-identified and
case-level: no reviewer-level file exists.  ``apply``, ``reject`` and ``refer``
are the disposition votes, which sum to five on every row.  ``realism``,
``fidelity``, ``clarity`` and ``action`` are counts of POSITIVE ratings out of
the five reviewers, a rating of 3 or 4 on the four-point scale counting as
positive.  Disposition agreement is the number of votes matching the suite's
own disposition for that case, so it is derived from the vote columns rather
than recorded separately.

WHAT IS MEASURED
----------------
* the five measures pooled over the 150 judgements, with a nonparametric
  cluster bootstrap over the 30 cases (a case is the cluster: its five ratings
  are not independent of each other) and the design effect that interval
  implies;
* the same five measures per suite class;
* Fleiss' kappa over the three disposition categories, five raters, thirty
  cases;
* the four-of-five rule the audit was read against: a case meets it when at
  least four of the five ratings are positive;
* unanimity of the disposition vote by register, which is where the
  disagreement sits.

WHAT IS ASSERTED (the script exits non-zero if any of these fails)
-----------------------------------------------------------------
Every headline the manuscript prints: the five totals, the vote marginals, the
twenty-five per-class counts, kappa, the four-of-five counts and the cases
below the rule, the register split, the five bootstrap intervals, and the
design-effect range.  A drift in the recorded file therefore fails here rather
than moving a published number quietly.

The bootstrap is seeded (``random.seed(20260817)``, 20,000 replicates, one
draw of thirty cases with replacement per replicate) and the percentile
endpoints are the 500th and the 19,499th sorted replicate, so the intervals
reproduce byte for byte on any machine running the standard library's
Mersenne Twister.

OUTPUTS
-------
``analysis/DG13_practitioner_audit.csv``   the measurements
``analysis/DG13_practitioner_audit.md``    the same, as the tables the note reads

Run::

    conda run -n fjsp python code/scripts/practitioner_audit.py

Version: l1-dg13-practitioner-audit-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import random
import statistics
import sys
from collections import OrderedDict
from pathlib import Path

VERSION = "l1-dg13-practitioner-audit-1"

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent.parent
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"

#: Five reviewers, thirty cases; every count in this file is out of one of these.
N_REVIEWERS = 5
N_CASES = 30
N_JUDGEMENTS = N_REVIEWERS * N_CASES

#: The bootstrap, fixed here rather than passed in: the published intervals are
#: these settings, and a flag that could change them would let a rerun print a
#: different interval under the same macro name.
BOOT_REPLICATES = 20000
BOOT_SEED = 20260817
BOOT_LO_INDEX = 500          # 2.5th percentile of 20,000 sorted replicates
BOOT_HI_INDEX = 19499        # 97.5th percentile

#: House style writes a count below ten as a word when it is a count noun in
#: prose, so the note spells the small counts it states in sentences.
WORDS = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
         6: "six", 7: "seven", 8: "eight", 9: "nine"}

#: A case meets the reading rule when at least four of the five ratings are
#: positive.  Section 6 reads the three Stage-A measures against it.
RULE_THRESHOLD = 4

#: (measure name, column of cases.csv).  Disposition agreement has no column of
#: its own: it is the vote count matching the suite's disposition.
MEASURES = [
    ("realism", "realism"),
    ("disposition", "_agree"),
    ("fidelity", "fidelity"),
    ("clarity", "clarity"),
    ("actionability", "action"),
]
STAGE_A = ["realism", "disposition", "fidelity"]

CLASSES = ["benign", "V3", "V4", "V5", "V6"]
REGISTERS = ["formal", "terse", "conversational"]
VOTE_COLUMNS = ["apply", "reject", "refer"]
DISPOSITION_VOTE = {"Apply": "apply", "Reject": "reject", "Refer": "refer"}

# --------------------------------------------------------------------------
# The recorded headlines.  Every one of them is asserted below.
# --------------------------------------------------------------------------

EXPECT_TOTALS = {"realism": 133, "disposition": 136, "fidelity": 132,
                 "clarity": 132, "actionability": 120}
EXPECT_VOTES = {"apply": 37, "reject": 59, "refer": 54}
#: class -> counts in MEASURES order.
EXPECT_PER_CLASS = {
    "benign": [29, 29, 29, 29, 28],
    "V3": [28, 28, 28, 28, 27],
    "V4": [27, 26, 26, 26, 23],
    "V5": [25, 28, 25, 25, 22],
    "V6": [24, 25, 24, 24, 20],
}
EXPECT_KAPPA = "0.7251"
EXPECT_RULE_MET = {"realism": 28, "disposition": 28, "fidelity": 28}
EXPECT_RULE_BELOW = {
    "realism": ["V5-M05", "V6-M05"],
    "disposition": ["V4-M06", "V6-M06"],
    "fidelity": ["V5-M05", "V6-M05"],
    "actionability": ["V4-M05", "V5-M04", "V5-M05", "V6-M02", "V6-M04",
                      "V6-M05", "V6-M06"],
}
EXPECT_UNANIMOUS = {"formal": 10, "terse": 7, "conversational": 1}
EXPECT_MEAN_AGREE = {"formal": "5.00", "terse": "4.70", "conversational": "3.90"}
EXPECT_NON_UNANIMOUS = {"formal": 0, "terse": 3, "conversational": 9}
EXPECT_CI = {
    "realism": ("84.0", "92.7"),
    "disposition": ("86.0", "94.7"),
    "fidelity": ("83.3", "92.0"),
    "clarity": ("84.0", "92.0"),
    "actionability": ("75.3", "84.7"),
}
EXPECT_DEFF = {"realism": "0.75", "disposition": "0.90", "fidelity": "0.71",
               "clarity": "0.58", "actionability": "0.58"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cases(path: Path) -> list:
    """The recorded cases, with the derived agreement column attached."""
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for col in VOTE_COLUMNS + [c for _m, c in MEASURES if not
                                   c.startswith("_")]:
            r[col] = int(r[col])
        if sum(r[c] for c in VOTE_COLUMNS) != N_REVIEWERS:
            raise SystemExit(
                "REFUSING TO RUN: case {} records {} disposition votes, not "
                "{}".format(r["case"], sum(r[c] for c in VOTE_COLUMNS),
                            N_REVIEWERS))
        for _m, col in MEASURES:
            if col.startswith("_"):
                continue
            if not 0 <= r[col] <= N_REVIEWERS:
                raise SystemExit(
                    "REFUSING TO RUN: case {} records {} positive {} ratings, "
                    "outside 0..{}".format(r["case"], r[col], col,
                                           N_REVIEWERS))
        if r["disposition"] not in DISPOSITION_VOTE:
            raise SystemExit("REFUSING TO RUN: case {} carries an unknown "
                             "disposition {!r}".format(r["case"],
                                                       r["disposition"]))
        r["_agree"] = r[DISPOSITION_VOTE[r["disposition"]]]
    if len(rows) != N_CASES:
        raise SystemExit("REFUSING TO RUN: {} cases recorded, {} expected"
                         .format(len(rows), N_CASES))
    return rows


def fleiss_kappa(rows: list) -> tuple:
    """(Po, Pe, kappa) over the three disposition categories, five raters.

    Po is the mean over cases of the share of rater PAIRS that agree, which is
    ``sum_c n_c(n_c-1) / (m(m-1))`` with m = 5 raters; Pe is the sum of squared
    category marginals over all 150 judgements.
    """
    pairs = N_REVIEWERS * (N_REVIEWERS - 1)
    po = sum(sum(r[c] * (r[c] - 1) for c in VOTE_COLUMNS) / pairs
             for r in rows) / len(rows)
    marg = [sum(r[c] for r in rows) / (len(rows) * N_REVIEWERS)
            for c in VOTE_COLUMNS]
    pe = sum(p * p for p in marg)
    return po, pe, (po - pe) / (1 - pe)


def bootstrap(rows: list) -> dict:
    """Percentile intervals from a cluster bootstrap over the thirty cases.

    A case is the cluster: a drawn case contributes all five of its ratings on
    every measure, so the five measures are resampled together and the interval
    carries the between-case variation the pooled share hides.  The draw order
    is one ``randrange`` per case per replicate, which is what fixes the
    published endpoints to this seed.
    """
    rng = random.Random()
    rng.seed(BOOT_SEED)
    reps = {m: [] for m, _c in MEASURES}
    n = len(rows)
    for _ in range(BOOT_REPLICATES):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        for m, col in MEASURES:
            reps[m].append(100.0 * sum(r[col] for r in sample) / N_JUDGEMENTS)
    out = {}
    for m, _col in MEASURES:
        s = sorted(reps[m])
        out[m] = (s[BOOT_LO_INDEX], s[BOOT_HI_INDEX])
    return out


def design_effect(rows: list, col: str, total: int) -> float:
    """Between-case variance of the per-case proportions over the naive one.

    The cluster variance of the pooled share is the variance of the thirty
    per-case proportions divided by thirty; the naive binomial variance treats
    the 150 ratings as independent.  Above one means the cases disagree with
    each other more than independent ratings would, so the naive interval is
    too narrow.
    """
    props = [r[col] / N_REVIEWERS for r in rows]
    p = total / N_JUDGEMENTS
    return (statistics.pvariance(props) / len(rows)) / (
        p * (1 - p) / N_JUDGEMENTS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases",
                    default=str(RESULTS / "practitioner_audit" / "cases.csv"))
    ap.add_argument("--out-csv",
                    default=str(ANALYSIS / "DG13_practitioner_audit.csv"))
    ap.add_argument("--out-md",
                    default=str(ANALYSIS / "DG13_practitioner_audit.md"))
    args = ap.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.is_file():
        raise SystemExit(
            "REFUSING TO RUN: {} does not exist. The recorded audit is the "
            "only input; nothing here is simulated.".format(cases_path))
    rows = load_cases(cases_path)

    # ------------------------------------------------------------------ #
    # (a) the five measures, pooled and per class                         #
    # ------------------------------------------------------------------ #
    totals = OrderedDict((m, sum(r[col] for r in rows)) for m, col in MEASURES)
    votes = OrderedDict((c, sum(r[c] for r in rows)) for c in VOTE_COLUMNS)
    per_class = OrderedDict()
    for cls in CLASSES:
        sub = [r for r in rows if r["class"] == cls]
        per_class[cls] = (len(sub),
                          [sum(r[col] for r in sub) for _m, col in MEASURES])

    # ------------------------------------------------------------------ #
    # (b) the four-of-five reading rule                                   #
    # ------------------------------------------------------------------ #
    rule_met, rule_below = OrderedDict(), OrderedDict()
    for m, col in MEASURES:
        below = [r for r in rows if r[col] < RULE_THRESHOLD]
        rule_met[m] = len(rows) - len(below)
        rule_below[m] = below
    stage_a_below = sorted({r["case"] for m in STAGE_A for r in rule_below[m]})
    stage_a_registers = sorted({r["register"] for m in STAGE_A
                                for r in rule_below[m]})

    # ------------------------------------------------------------------ #
    # (c) agreement                                                       #
    # ------------------------------------------------------------------ #
    po, pe, kappa = fleiss_kappa(rows)

    unanimous, mean_agree, non_unanimous = OrderedDict(), OrderedDict(), \
        OrderedDict()
    for reg in REGISTERS:
        sub = [r for r in rows if r["register"] == reg]
        unanimous[reg] = sum(1 for r in sub if r["_agree"] == N_REVIEWERS)
        non_unanimous[reg] = len(sub) - unanimous[reg]
        mean_agree[reg] = statistics.mean(r["_agree"] for r in sub)
    non_unanimous_total = sum(non_unanimous.values())

    # ------------------------------------------------------------------ #
    # (d) intervals and design effects                                    #
    # ------------------------------------------------------------------ #
    ci = bootstrap(rows)
    deff = OrderedDict((m, design_effect(rows, col, totals[m]))
                       for m, col in MEASURES)

    # ------------------------------------------------------------------ #
    # Assertions                                                          #
    # ------------------------------------------------------------------ #
    checks, failures = [], []

    def check(what, expected, got):
        checks.append(what)
        if expected != got:
            failures.append("{}: expected {!r}, got {!r}".format(
                what, expected, got))

    check("judgements per measure", N_JUDGEMENTS, len(rows) * N_REVIEWERS)
    for m, _col in MEASURES:
        check("total positive " + m, EXPECT_TOTALS[m], totals[m])
    for c in VOTE_COLUMNS:
        check("disposition votes " + c, EXPECT_VOTES[c], votes[c])
    check("vote marginals sum to the judgements", N_JUDGEMENTS,
          sum(votes.values()))
    for cls in CLASSES:
        check("per-class counts " + cls, EXPECT_PER_CLASS[cls],
              per_class[cls][1])
    check("Fleiss kappa", EXPECT_KAPPA, "{:.4f}".format(kappa))
    for m in STAGE_A:
        check("cases meeting the four-of-five rule on " + m,
              EXPECT_RULE_MET[m], rule_met[m])
    for m, expected in EXPECT_RULE_BELOW.items():
        check("cases below the four-of-five rule on " + m, expected,
              [r["case"] for r in rule_below[m]])
    check("registers of the Stage-A cases below the rule",
          ["conversational"], stage_a_registers)
    for reg in REGISTERS:
        check("unanimous disposition cases, " + reg, EXPECT_UNANIMOUS[reg],
              unanimous[reg])
        check("mean agreeing reviewers, " + reg, EXPECT_MEAN_AGREE[reg],
              "{:.2f}".format(mean_agree[reg]))
        check("non-unanimous cases, " + reg, EXPECT_NON_UNANIMOUS[reg],
              non_unanimous[reg])
    check("non-unanimous cases", 12, non_unanimous_total)
    for m, _col in MEASURES:
        check("bootstrap interval " + m, EXPECT_CI[m],
              ("{:.1f}".format(ci[m][0]), "{:.1f}".format(ci[m][1])))
        check("design effect " + m, EXPECT_DEFF[m],
              "{:.2f}".format(deff[m]))
    check("design-effect minimum", "0.58",
          "{:.2f}".format(min(deff.values())))
    check("design-effect maximum", "0.90",
          "{:.2f}".format(max(deff.values())))
    if failures:
        for f in failures:
            print("ASSERTION FAILED  " + f, file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    # Output: the table                                                   #
    # ------------------------------------------------------------------ #
    digest = sha256(cases_path)
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    def share(a, b):
        return "{:.1f}".format(100.0 * a / b)

    out = Path(args.out_csv)
    with out.open("w", newline="") as fh:
        fh.write("# DG13. A practitioner audit of the suite's own "
                 "dispositions: {} cases, {} reviewers, {} judgements per "
                 "measure\n".format(N_CASES, N_REVIEWERS, N_JUDGEMENTS))
        fh.write("# generated {} by code/scripts/practitioner_audit.py "
                 "({})\n".format(stamp, VERSION))
        fh.write("# input results/practitioner_audit/cases.csv sha256 "
                 "{}\n".format(digest))
        fh.write("# counts are POSITIVE ratings out of {}: each reviewer "
                 "answered on a four-point scale and a 3 or a 4 counts as "
                 "positive\n".format(N_REVIEWERS))
        fh.write("# the disposition measure is the number of reviewer votes "
                 "matching the suite's own disposition for that case\n")
        fh.write("# ci_lo_pct / ci_hi_pct: percentile endpoints of a cluster "
                 "bootstrap over the {} cases, {} replicates, "
                 "random.seed({}), sorted replicates {} and {}\n".format(
                     N_CASES, BOOT_REPLICATES, BOOT_SEED, BOOT_LO_INDEX,
                     BOOT_HI_INDEX))
        fh.write("# deff: (between-case variance of the per-case proportions "
                 "/ {}) over (p(1-p) / {}); above 1 means the cases disagree "
                 "more than independent ratings would\n".format(
                     N_CASES, N_JUDGEMENTS))
        fh.write("# rule_met / rule_below: cases with at least {} of the {} "
                 "ratings positive, and the cases below that rule\n".format(
                     RULE_THRESHOLD, N_REVIEWERS))
        fh.write("# self-check: {} assertions passed\n".format(len(checks)))
        w = csv.writer(fh)
        w.writerow(["block", "measure", "scope", "count", "denom", "share_pct",
                    "ci_lo_pct", "ci_hi_pct", "deff", "stat", "rule_met",
                    "rule_below", "note"])

        for m, col in MEASURES:
            w.writerow([
                "overall", m, "ALL", totals[m], N_JUDGEMENTS,
                share(totals[m], N_JUDGEMENTS),
                "{:.1f}".format(ci[m][0]), "{:.1f}".format(ci[m][1]),
                "{:.2f}".format(deff[m]), "", rule_met[m],
                ";".join(r["case"] for r in rule_below[m]),
                "positive ratings pooled over the {} judgements".format(
                    N_JUDGEMENTS)])

        for cls in CLASSES:
            n_cases, counts = per_class[cls]
            denom = n_cases * N_REVIEWERS
            for (m, _col), value in zip(MEASURES, counts):
                w.writerow(["per_class", m, cls, value, denom,
                            share(value, denom), "", "", "", "", "", "",
                            "{} cases of class {}".format(n_cases, cls)])

        for reg in REGISTERS:
            n_reg = sum(1 for r in rows if r["register"] == reg)
            w.writerow(["register", "disposition_unanimous", reg,
                        unanimous[reg], n_reg, share(unanimous[reg], n_reg),
                        "", "", "", "{:.2f}".format(mean_agree[reg]), "", "",
                        "cases where all {} reviewers chose the suite's "
                        "disposition; stat is the mean number of agreeing "
                        "reviewers".format(N_REVIEWERS)])
            w.writerow(["register", "disposition_nonunanimous", reg,
                        non_unanimous[reg], n_reg,
                        share(non_unanimous[reg], n_reg), "", "", "", "", "",
                        "", ""])
        w.writerow(["register", "disposition_nonunanimous", "ALL",
                    non_unanimous_total, N_CASES,
                    share(non_unanimous_total, N_CASES), "", "", "", "", "",
                    "", "cases where at least one reviewer chose otherwise"])

        w.writerow(["agreement", "fleiss_kappa", "ALL", "", "", "", "", "", "",
                    "{:.4f}".format(kappa), "", "",
                    "three disposition categories, {} raters, {} cases; "
                    "Po {:.4f}, Pe {:.4f}".format(N_REVIEWERS, N_CASES,
                                                  po, pe)])
        w.writerow(["agreement", "observed_agreement", "ALL", "", "", "", "",
                    "", "", "{:.4f}".format(po), "", "",
                    "mean share of agreeing rater pairs"])
        w.writerow(["agreement", "chance_agreement", "ALL", "", "", "", "", "",
                    "", "{:.4f}".format(pe), "", "",
                    "sum of squared category marginals"])
        for c in VOTE_COLUMNS:
            w.writerow(["agreement", "votes_" + c, "ALL", votes[c],
                        N_JUDGEMENTS, share(votes[c], N_JUDGEMENTS), "", "",
                        "", "", "", "",
                        "reviewer votes for {} over every case".format(c)])

    # ------------------------------------------------------------------ #
    # Output: the note                                                    #
    # ------------------------------------------------------------------ #
    md = ["# DG13. A practitioner audit of the suite's own dispositions",
          "",
          "Generated by `code/scripts/practitioner_audit.py` (`{}`). Companion "
          "table: `analysis/DG13_practitioner_audit.csv`.".format(VERSION),
          "",
          "## What was audited",
          "",
          "Five practitioners each read the same {} cases, recorded the "
          "disposition they would choose (apply, reject, refer) and rated the "
          "case on four four-point scales. A rating of 3 or 4 counts as "
          "positive, so every count below is out of {} judgements: {} cases "
          "times {} reviewers. The record is case-level and de-identified "
          "(`results/practitioner_audit/cases.csv`); no reviewer-level file "
          "exists. The disposition measure is not a recorded column: it is the "
          "number of votes matching the suite's own disposition for that "
          "case.".format(N_CASES, N_JUDGEMENTS, N_CASES, N_REVIEWERS),
          "",
          "## 1. The five measures, pooled",
          "",
          "| measure | positive | of | share | 95% CI (case-clustered) | design "
          "effect | cases meeting four of five |",
          "|---|---|---|---|---|---|---|"]
    for m, _col in MEASURES:
        md.append("| {} | {} | {} | {}% | {}% to {}% | {:.2f} | {}/{} |".format(
            m, totals[m], N_JUDGEMENTS, share(totals[m], N_JUDGEMENTS),
            "{:.1f}".format(ci[m][0]), "{:.1f}".format(ci[m][1]), deff[m],
            rule_met[m], N_CASES))
    md += ["",
           "The interval is a nonparametric cluster bootstrap over the {} "
           "cases: a replicate draws {} cases with replacement, each drawn "
           "case contributing all five of its ratings, and the endpoints are "
           "the 2.5 and 97.5 percentiles of {:,} replicates at "
           "`random.seed({})`. Every design effect is below one, so the cases "
           "agree with each other slightly more than independent ratings "
           "would and the naive binomial interval is, if anything, a little "
           "wide.".format(N_CASES, N_CASES, BOOT_REPLICATES, BOOT_SEED),
           "",
           "## 2. The same measures by suite class",
           "",
           "| class | cases | " + " | ".join(m for m, _c in MEASURES) + " |",
           "|---|---|" + "---|" * len(MEASURES)]
    for cls in CLASSES:
        n_cases, counts = per_class[cls]
        md.append("| {} | {} | ".format(cls, n_cases)
                  + " | ".join("{}/{}".format(v, n_cases * N_REVIEWERS)
                               for v in counts) + " |")
    md += ["",
           "Realism, fidelity and clarity fall monotonically as the class gets "
           "harder, and actionability falls furthest: {}% of the benign "
           "judgements call the suite's verdict actionable against {}% of the "
           "V6 ones. Disposition agreement is the exception, recovering on V5 "
           "because a refer verdict on an ambiguous instruction is the one "
           "practitioners agree on most readily.".format(
               share(per_class["benign"][1][4], 30),
               share(per_class["V6"][1][4], 30)),
           "",
           "## 3. Agreement on the disposition",
           "",
           "Fleiss' kappa over the three disposition categories, {} raters and "
           "{} cases, is **{:.4f}** (observed pairwise agreement {:.4f}, "
           "chance {:.4f}). The vote marginals are apply {}, reject {}, refer "
           "{}, of {}.".format(N_REVIEWERS, N_CASES, kappa, po, pe,
                               votes["apply"], votes["reject"], votes["refer"],
                               N_JUDGEMENTS),
           "",
           "| register | cases | unanimous | mean agreeing reviewers | "
           "non-unanimous |",
           "|---|---|---|---|---|"]
    for reg in REGISTERS:
        n_reg = sum(1 for r in rows if r["register"] == reg)
        md.append("| {} | {} | {} | {:.2f} | {} |".format(
            reg, n_reg, unanimous[reg], mean_agree[reg], non_unanimous[reg]))
    md += ["",
           "The disagreement is concentrated in one register: of the {} "
           "non-unanimous cases, {} are conversational and {} are terse, and "
           "no formal case drew a split vote.".format(
               non_unanimous_total, non_unanimous["conversational"],
               non_unanimous["terse"]),
           "",
           "## 4. The four-of-five reading rule",
           "",
           "A case meets the rule when at least {} of its {} ratings are "
           "positive.".format(RULE_THRESHOLD, N_REVIEWERS),
           "",
           "| measure | cases meeting the rule | cases below it |",
           "|---|---|---|"]
    for m, _col in MEASURES:
        below = rule_below[m]
        md.append("| {} | {}/{} | {} |".format(
            m, rule_met[m], N_CASES,
            ", ".join("{} ({})".format(r["case"], r["register"])
                      for r in below) or "none"))
    md += ["",
           "The {} cases below the rule on realism, disposition agreement or "
           "fidelity are all conversational: {}. Actionability is the "
           "exception the audit records rather than explains away: {} cases "
           "sit below the rule, and one of them ({}) is formal.".format(
               WORDS[len(stage_a_below)], ", ".join(stage_a_below),
               WORDS[len(rule_below["actionability"])], "V6-M02"),
           "",
           "## Scope",
           "",
           "Thirty cases and five reviewers. The audit is a check on whether "
           "practitioners recognise the suite's dispositions as the ones they "
           "would make, not a measurement of the guard, and the intervals are "
           "wide enough that only the ordering of the classes, not the "
           "distance between neighbouring ones, is supported.",
           "",
           "## Sources",
           "",
           "* `results/practitioner_audit/cases.csv` sha256 `{}`".format(digest),
           ""]
    Path(args.out_md).write_text("\n".join(md))

    print(json.dumps({
        "version": VERSION,
        "cases": N_CASES,
        "reviewers": N_REVIEWERS,
        "judgements": N_JUDGEMENTS,
        "totals": totals,
        "votes": votes,
        "per_class": {c: v[1] for c, v in per_class.items()},
        "fleiss_kappa": round(kappa, 4),
        "observed_agreement": round(po, 4),
        "chance_agreement": round(pe, 4),
        "rule_met": rule_met,
        "rule_below": {m: [r["case"] for r in v]
                       for m, v in rule_below.items()},
        "unanimous": unanimous,
        "mean_agreeing_reviewers": {k: round(v, 2)
                                    for k, v in mean_agree.items()},
        "non_unanimous": non_unanimous,
        "ci_pct": {m: [round(lo, 1), round(hi, 1)]
                   for m, (lo, hi) in ci.items()},
        "design_effect": {m: round(v, 2) for m, v in deff.items()},
        "cases_sha256": digest,
    }, indent=1))
    print("wrote {}".format(out), file=sys.stderr)
    print("wrote {}".format(args.out_md), file=sys.stderr)
    print("all {} assertions passed".format(len(checks)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
