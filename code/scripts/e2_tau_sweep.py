#!/usr/bin/env python
"""E2 tau sweep: the quality tolerance recomputed offline over the E1 verdicts.

Tau enters the guard at exactly one place: after stage 1 (schema) and stage 2
(feasibility) have passed, stage 3 computes the certified gap and accepts the
proposal iff ``gap <= tau`` (:func:`l1guard.guard._certify`).  Every G_CERT
verdict row already records its gap, so the sweep is **pure post-processing**
over ``verdicts_G_CERT.jsonl``: no model, no GPU, no replay, no dispatch
(decisions.md, "DESIGN FREEZE: E2 tau sweep", 2026-08-12).

How a terminal is recomputed at tolerance ``t``
-----------------------------------------------
``blocked_schema`` / ``blocked_feas``
    Tau-invariant.  The proposal never reached the quality gate, so no value of
    tau can change what happened to it.
a row carrying a certificate gap
    ``blocked_qual`` if ``gap > t``, else ``applied_with_certificate``.  This is
    the guard's own comparison (``accepted = gap <= config.tau``), re-evaluated.
anything else (no certificate gap and no early block)
    Kept **exactly as the recorded verdict has it**.  Two execution paths land
    here and neither depends on tau: ``lb_unavailable`` (no lower bound was
    produced, so stage 3 blocks with no certificate to compare) and
    ``execution_failed`` (an instrument fault at stage 2 or 3, which is an
    outcome, not a refusal).  The count of such rows is reported per arm; in the
    three E1 logs swept on 2026-08-12 it is zero everywhere.

G_FEAS verdicts are tau-invariant by construction (that arm has no quality
gate), so the V3/V4 separation counts reuse them unchanged.

Conventions inherited from the E1 evaluator (``scripts/e1_evaluate.py``), so
that every number is comparable to the accepted E1 tables:

* a row with an ``infra_error`` finding is an instrument fault, never a guard
  decision, and is excluded from every rate (per configuration);
* block rates are per ``primary_class`` over the rows eligible under G_CERT;
* separation is ``G_FEAS applied`` and ``G_CERT blocked``, over the rows
  eligible under both, with the class's full eligible count as denominator.

The warranted-outcome share is the guidance's warranted-outcome rate
(``L1_Complete_Guidance.md`` Section 5.4: "the fraction of instructions whose
disposition carries a machine-checkable justification (a certificate on applied
proposals; a matched violation label on blocks; an explicit referral record)").
No module in the codebase computes it, so this script is its first
implementation, at the freeze's operational reading: a row is warranted when it
ends ``applied_with_certificate`` (a certificate is attached) or when it is
blocked and its item carries an injected violation label (``primary_class`` is
not ``benign``).  There is no referral arm in E1, so the third disposition
contributes nothing here.  A stricter reading, requiring the blocking finding
code to match the injected violation subclass, is not implemented anywhere in
the codebase and is not used.

Hard anchor
-----------
At ``tau = 0.20`` every produced number must equal the accepted E1 numbers in
each arm's ``summary.json``: terminal-state counts, per-class block counts and
rates, and the separation quadruple.  The check runs on every arm and a
mismatch exits non-zero.

Outputs, under ``--out`` (default ``results/e2_tau_sweep``):

``summary.md``
    Per-arm curve tables, the operating-point table, one plain data statement
    per arm, the anchor check and the monotonicity check.
``summary.json``
    The same content, machine-readable.
``curves.csv``
    Long format: arm, mode, thinking, tau, class, items, blocks, block_rate,
    false_block_rate, v3_separated, v4_separated, warranted_share.

Run::

    python scripts/e2_tau_sweep.py --results-root results --out results/e2_tau_sweep
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# The terminal vocabulary comes from the guard itself, never from a copy: a
# renamed terminal must break this script rather than silently mis-bucket rows.
from l1guard.verdict import (  # noqa: E402
    APPLIED_STATES,
    APPLIED_WITH_CERTIFICATE,
    BLOCKED_FEAS,
    BLOCKED_QUAL,
    BLOCKED_SCHEMA,
    BLOCKED_STATES,
    TERMINAL_STATES,
)

SWEEP_VERSION = "l1-e2-tau-sweep-1"

#: The frozen grid (decisions.md, "DESIGN FREEZE: E2 tau sweep").
TAU_GRID = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00)

#: The tolerance the accepted E1 tables were produced at.  Every number this
#: script produces at this tau must reproduce them exactly.
ANCHOR_TAU = 0.20

#: Benign false-block budgets for the operating points.
FALSE_BLOCK_TARGETS = (0.01, 0.05)

#: Terminals that no value of tau can change: the proposal was refused before
#: the quality gate ran.
PRE_QUAL_BLOCKS = (BLOCKED_SCHEMA, BLOCKED_FEAS)

BENIGN = "benign"

REQUIRED_FILES = ("verdicts_G_CERT.jsonl", "verdicts_G_FEAS.jsonl", "summary.json")

LAUNCH_QUESTIONS = """\
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Produce the tau-sensitivity evidence promised in the guidance
   (Section 7.3 threats: "tau sensitivity (report a tau sweep)") and the E2
   operating-point choice: for every evaluated arm, the per-class block rates,
   the benign false-block rate, the V3/V4 separation and the warranted-outcome
   share as functions of tau.  Destination: the E2 tau-sweep exhibit and the
   sentence that justifies the published tau.
2. EXPECTED RESULT.  Block rates fall monotonically as tau rises, V3 separation
   collapses towards the G_FEAS floor at large tau, and the benign false-block
   rate bottoms out at the schema-plus-feasibility floor that no tau can move.
   If instead a rate rose with tau, the recomputation would be wrong, not the
   guard.
3. CONTAMINATION.  Pure post-processing: no model, no GPU, no replay, no
   dispatch.  The output directory must be empty unless --force is explicit.
   Inputs are the frozen verdict logs; the accepted tau = 0.20 numbers in each
   arm's summary.json are asserted as a hard anchor, so a drifted input or a
   wrong recomputation fails the run instead of publishing a curve.
4. DATA ACCURACY.  Every e1_eval_* directory present at run time is swept, and
   the arms swept are printed.  G_CERT and G_FEAS rows are joined on
   (arm, mode, thinking, repeat, item_id), a key asserted unique and complete on
   both sides, so no separation count can be built from a mismatched pair.
================================================================================"""


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def tau_label(tau: float) -> str:
    return "{:.2f}".format(tau)


def thinking_label(value) -> str:
    return "-" if value is None else str(value)


def pct(numerator, denominator) -> str:
    return "n/a" if not denominator else "{:.1%}".format(numerator / denominator)


def fmt_rate(value) -> str:
    return "n/a" if value is None else "{:.1%}".format(value)


def md_table(headers, rows) -> list:
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    return out


def read_jsonl(path: Path) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit("{} line {} is not JSON: {}".format(path, n, exc))
    return rows


def row_key(row: dict) -> tuple:
    return (row["arm"], row["mode"], row.get("thinking"), row.get("repeat"),
            row["item_id"])


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #
def discover_eval_dirs(root: Path, explicit) -> list:
    if explicit:
        dirs = [Path(p).resolve() for p in explicit]
        for d in dirs:
            if not d.is_dir():
                raise SystemExit("no evaluation directory at {}".format(d))
        return sorted(dirs)
    dirs = sorted(p.resolve() for p in root.glob("e1_eval_*") if p.is_dir())
    if not dirs:
        raise SystemExit(
            "REFUSING TO RUN: no e1_eval_* directory under {}; the sweep is "
            "post-processing over evaluated arms and has nothing to read.".format(root)
        )
    return dirs


def load_arm(eval_dir: Path) -> dict:
    """One evaluated arm: the joined verdict rows plus its accepted summary."""
    cert_rows = read_jsonl(eval_dir / "verdicts_G_CERT.jsonl")
    feas_rows = read_jsonl(eval_dir / "verdicts_G_FEAS.jsonl")
    summary = json.loads((eval_dir / "summary.json").read_text())

    if not cert_rows:
        raise SystemExit("REFUSING TO RUN: {} has no G_CERT verdict rows".format(eval_dir))
    if len(cert_rows) != len(feas_rows):
        raise SystemExit(
            "REFUSING TO RUN: {} has {} G_CERT rows and {} G_FEAS rows; the "
            "separation count needs one G_FEAS verdict per G_CERT verdict.".format(
                eval_dir, len(cert_rows), len(feas_rows)
            )
        )

    feas_by_key = {}
    for row in feas_rows:
        key = row_key(row)
        if key in feas_by_key:
            raise SystemExit(
                "REFUSING TO RUN: {} has two G_FEAS rows for {}; the join key "
                "(arm, mode, thinking, repeat, item_id) must be unique.".format(eval_dir, key)
            )
        feas_by_key[key] = row

    joined = []
    seen = set()
    for row in cert_rows:
        key = row_key(row)
        if key in seen:
            raise SystemExit(
                "REFUSING TO RUN: {} has two G_CERT rows for {}; the join key "
                "(arm, mode, thinking, repeat, item_id) must be unique.".format(eval_dir, key)
            )
        seen.add(key)
        feas = feas_by_key.get(key)
        if feas is None:
            raise SystemExit(
                "REFUSING TO RUN: {} has a G_CERT row for {} with no G_FEAS "
                "counterpart.".format(eval_dir, key)
            )
        joined.append({
            "arm": row["arm"],
            "mode": row["mode"],
            "thinking": row.get("thinking"),
            "repeat": row.get("repeat"),
            "item_id": row["item_id"],
            "primary_class": row["primary_class"],
            "subclass": row.get("subclass"),
            "cert_terminal": row["terminal"],
            "cert_infra": bool(row["infra"]),
            "gap": row.get("certificate_gap"),
            "blocking_codes": tuple(row.get("blocking_codes") or ()),
            "feas_terminal": feas["terminal"],
            "feas_infra": bool(feas["infra"]),
        })

    # A gap plus a blocking quality finding that is not the tau comparison would
    # be a row whose block does not follow from gap-vs-tau; the guard has no such
    # path today (gap_above_tau and lb_unavailable are the only blocking stage-3
    # codes, and lb_unavailable leaves no certificate), so meeting one means the
    # guard changed and this recomputation is stale.
    unmodelled = [
        r for r in joined
        if r["gap"] is not None
        and r["cert_terminal"] not in PRE_QUAL_BLOCKS
        and set(r["blocking_codes"]) - {"gap_above_tau"}
    ]
    if unmodelled:
        raise SystemExit(
            "REFUSING TO RUN: {} has {} rows carrying a certificate gap and a "
            "blocking code other than gap_above_tau (first: {} / {}); the "
            "recomputation rule 'blocked_qual iff gap > tau' would misstate "
            "them.".format(eval_dir, len(unmodelled), unmodelled[0]["item_id"],
                           unmodelled[0]["blocking_codes"])
        )

    return {"dir": eval_dir, "rows": joined, "summary": summary,
            "arms": sorted({r["arm"] for r in joined})}


# --------------------------------------------------------------------------- #
# The recomputation                                                            #
# --------------------------------------------------------------------------- #
def terminal_at(row: dict, tau: float) -> str:
    """The G_CERT terminal this row would have had at tolerance ``tau``."""
    terminal = row["cert_terminal"]
    if terminal in PRE_QUAL_BLOCKS:
        return terminal
    if row["gap"] is not None:
        return BLOCKED_QUAL if row["gap"] > tau else APPLIED_WITH_CERTIFICATE
    # No certificate and no early block: whatever the guard recorded stands.
    return terminal


def tau_invariant_rows(rows: list) -> list:
    """Rows the sweep carries through unchanged because they never certified."""
    return [r for r in rows
            if r["gap"] is None and r["cert_terminal"] not in PRE_QUAL_BLOCKS]


def group_rows(rows: list) -> "OrderedDict":
    """(arm, mode, thinking) -> rows, pooled over repeats (the freeze's unit)."""
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for row in rows:
        groups.setdefault((row["arm"], row["mode"], row["thinking"]), []).append(row)
    return OrderedDict(sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1],
                                                              str(kv[0][2]))))


def group_curve(rows: list, classes: list) -> dict:
    """Every tabulated quantity, for one (arm, mode, thinking) at every tau."""
    cert_eligible = [r for r in rows if not r["cert_infra"]]
    both_eligible = [r for r in rows if not r["cert_infra"] and not r["feas_infra"]]

    by_class = {cls: [r for r in cert_eligible if r["primary_class"] == cls]
                for cls in classes}
    sep_by_class = {cls: [r for r in both_eligible if r["primary_class"] == cls]
                    for cls in classes}

    points = OrderedDict()
    for tau in TAU_GRID:
        terminals = Counter(terminal_at(r, tau) for r in rows)

        blocks = {}
        for cls in classes:
            sel = by_class[cls]
            blocked = sum(1 for r in sel if terminal_at(r, tau) in BLOCKED_STATES)
            blocks[cls] = {
                "n": len(sel),
                "blocked": blocked,
                "rate": None if not sel else blocked / len(sel),
            }

        separation = {}
        for cls in classes:
            sel = sep_by_class[cls]
            feas_pass = [r for r in sel if r["feas_terminal"] in APPLIED_STATES]
            separated = sum(1 for r in feas_pass if terminal_at(r, tau) in BLOCKED_STATES)
            separation[cls] = {
                "n": len(sel),
                "feas_pass": len(feas_pass),
                "cert_block": sum(1 for r in sel if terminal_at(r, tau) in BLOCKED_STATES),
                "separated": separated,
                "share": None if not sel else separated / len(sel),
            }

        warranted = 0
        for r in cert_eligible:
            terminal = terminal_at(r, tau)
            if terminal == APPLIED_WITH_CERTIFICATE:
                warranted += 1
            elif terminal in BLOCKED_STATES and r["primary_class"] != BENIGN:
                warranted += 1

        benign = blocks.get(BENIGN)
        points[tau_label(tau)] = {
            "tau": tau,
            "terminals": {t: terminals.get(t, 0) for t in TERMINAL_STATES if terminals.get(t)},
            "blocks": blocks,
            "separation": separation,
            "false_block_rate": None if not benign else benign["rate"],
            "false_blocks": None if not benign else benign["blocked"],
            "benign_items": None if not benign else benign["n"],
            "warranted": warranted,
            "warranted_n": len(cert_eligible),
            "warranted_share": None if not cert_eligible else warranted / len(cert_eligible),
        }

    return {
        "n_rows": len(rows),
        "anchor_row_mismatches": sum(
            1 for r in rows if terminal_at(r, ANCHOR_TAU) != r["cert_terminal"]),
        "n_eligible_cert": len(cert_eligible),
        "n_eligible_both": len(both_eligible),
        "infra_cert": sum(1 for r in rows if r["cert_infra"]),
        "infra_feas": sum(1 for r in rows if r["feas_infra"]),
        "n_tau_invariant_uncertified": len(tau_invariant_rows(rows)),
        "tau_invariant_uncertified_terminals": dict(
            Counter(r["cert_terminal"] for r in tau_invariant_rows(rows))),
        "classes": classes,
        "points": points,
    }


def operating_points(curve: dict) -> dict:
    """Largest tau meeting each benign false-block budget (the frozen rule).

    The frozen definition is *largest*.  Because the false-block rate is
    non-increasing in tau, the largest qualifying grid point is the loosest gate
    that meets the budget; the *smallest* qualifying grid point is the tightest
    gate that meets it, and is the one that catches the most violations at the
    same false-block cost.  Both are reported, the frozen one first.
    """
    out = {}
    for target in FALSE_BLOCK_TARGETS:
        qualifying = [
            point["tau"] for point in curve["points"].values()
            if point["false_block_rate"] is not None
            and point["false_block_rate"] <= target
        ]
        key = "fb_le_{:g}pct".format(target * 100)
        if not qualifying:
            out[key] = {"target": target, "tau_largest": None, "tau_smallest": None,
                        "false_block_rate_at_largest": None,
                        "false_block_rate_at_smallest": None,
                        "note": "no grid tau meets this budget"}
            continue
        largest, smallest = max(qualifying), min(qualifying)
        out[key] = {
            "target": target,
            "tau_largest": largest,
            "tau_smallest": smallest,
            "false_block_rate_at_largest":
                curve["points"][tau_label(largest)]["false_block_rate"],
            "false_block_rate_at_smallest":
                curve["points"][tau_label(smallest)]["false_block_rate"],
            "note": None,
        }
    return out


# --------------------------------------------------------------------------- #
# Checks                                                                       #
# --------------------------------------------------------------------------- #
def close(a, b, tol=1e-12) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def anchor_checks(key: tuple, curve: dict, summary: dict) -> list:
    """Every tau = 0.20 number against the accepted E1 summary.json."""
    arm, mode, thinking = key
    pooled = [
        g for g in summary.get("groups", [])
        if g.get("pooled") and g.get("arm") == arm and g.get("mode") == mode
        and g.get("thinking") == thinking
    ]
    if len(pooled) != 1:
        return [{
            "group": "{} / {} / {}".format(arm, mode, thinking_label(thinking)),
            "check": "accepted pooled group present in summary.json",
            "expected": "exactly 1", "got": str(len(pooled)), "pass": False,
        }]
    accepted = pooled[0]
    point = curve["points"][tau_label(ANCHOR_TAU)]
    label = "{} / {} / {}".format(arm, mode, thinking_label(thinking))
    out = []

    def check(name, expected, got):
        ok = (expected == got) if not isinstance(expected, float) else close(expected, got)
        out.append({"group": label, "check": name, "expected": expected,
                    "got": got, "pass": bool(ok)})

    check("rows", accepted["n_rows"], curve["n_rows"])

    # The tightest form of the anchor: tau = 0.20 is the tolerance the E1 logs
    # were evaluated at, so the recomputation must return every row to its own
    # recorded terminal.  An aggregate match can hide two errors that cancel;
    # this cannot.
    check("rows whose recomputed terminal differs from the recorded verdict",
          0, curve["anchor_row_mismatches"])

    expected_terminals = {k: v for k, v in accepted["terminals"]["G_CERT"].items() if v}
    check("G_CERT terminal counts", expected_terminals, point["terminals"])

    for cls in curve["classes"]:
        exp = accepted["blocks"][cls]["G_CERT"]
        got = point["blocks"][cls]
        check("blocks[{}] items".format(cls), exp["n"], got["n"])
        check("blocks[{}] blocked".format(cls), exp["blocked"], got["blocked"])
        check("blocks[{}] rate".format(cls), exp["rate"], got["rate"])

        exp_sep = accepted["separation"].get(cls)
        got_sep = point["separation"][cls]
        if exp_sep is None:
            check("separation[{}] present".format(cls), "present", "absent")
            continue
        for field in ("n", "feas_pass", "cert_block", "separated"):
            check("separation[{}] {}".format(cls, field), exp_sep[field], got_sep[field])
        check("separation[{}] share".format(cls), exp_sep["share"], got_sep["share"])

    # The warranted-outcome share has no counterpart in the E1 summary (E1 never
    # reported it), but it is a function of numbers that do: the certified
    # applications plus the blocks on the violation classes.  When the arm has no
    # infra row the two populations coincide exactly and the anchor is exact.
    blocked_violations = sum(
        accepted["blocks"][cls]["G_CERT"]["blocked"]
        for cls in curve["classes"] if cls != BENIGN
    )
    if curve["infra_cert"] == 0:
        expected_warranted = (
            accepted["terminals"]["G_CERT"].get(APPLIED_WITH_CERTIFICATE, 0)
            + blocked_violations
        )
        check("warranted outcomes (certified applications + blocked violations)",
              expected_warranted, point["warranted"])
    else:
        check("warranted outcomes, blocked-violation part "
              "(applied part not derivable: this arm has infra rows)",
              blocked_violations,
              point["warranted"] - point["terminals"].get(APPLIED_WITH_CERTIFICATE, 0))
    return out


def monotonicity_checks(key: tuple, curve: dict) -> list:
    """Block counts (and the derived rates and separations) must not rise with tau."""
    arm, mode, thinking = key
    label = "{} / {} / {}".format(arm, mode, thinking_label(thinking))
    taus = list(TAU_GRID)
    out = []

    def series_check(name, values):
        violations = [
            "tau {} -> {}: {} -> {}".format(tau_label(taus[i]), tau_label(taus[i + 1]),
                                            values[i], values[i + 1])
            for i in range(len(values) - 1)
            if values[i + 1] is not None and values[i] is not None
            and values[i + 1] > values[i]
        ]
        out.append({"group": label, "series": name,
                    "first": values[0], "last": values[-1],
                    "violations": violations, "pass": not violations})

    for cls in curve["classes"]:
        series_check("blocks[{}] blocked".format(cls),
                     [curve["points"][tau_label(t)]["blocks"][cls]["blocked"] for t in taus])
    series_check("benign false-block rate",
                 [curve["points"][tau_label(t)]["false_block_rate"] for t in taus])
    for cls in ("V3", "V4"):
        if cls in curve["classes"]:
            series_check("separation[{}] separated".format(cls),
                         [curve["points"][tau_label(t)]["separation"][cls]["separated"]
                          for t in taus])
    return out


# --------------------------------------------------------------------------- #
# Reporting                                                                    #
# --------------------------------------------------------------------------- #
def curve_statement(key: tuple, curve: dict, ops: dict) -> str:
    """One plain data statement about the shape of this arm's curve."""
    arm, mode, thinking = key
    points = curve["points"]
    lo, hi = points[tau_label(TAU_GRID[0])], points[tau_label(TAU_GRID[-1])]
    anchor = points[tau_label(ANCHOR_TAU)]
    parts = []
    parts.append(
        "Benign false blocks run {} at tau {} to {} at tau {}, and {} at tau {}.".format(
            fmt_rate(lo["false_block_rate"]), tau_label(TAU_GRID[0]),
            fmt_rate(hi["false_block_rate"]), tau_label(TAU_GRID[-1]),
            fmt_rate(anchor["false_block_rate"]), tau_label(ANCHOR_TAU))
    )
    if "V3" in curve["classes"]:
        parts.append(
            "V3 separation runs {} of {} items at tau {} to {} at tau {}, and {} at "
            "tau {}.".format(
                lo["separation"]["V3"]["separated"], lo["separation"]["V3"]["n"],
                tau_label(TAU_GRID[0]), hi["separation"]["V3"]["separated"],
                tau_label(TAU_GRID[-1]), anchor["separation"]["V3"]["separated"],
                tau_label(ANCHOR_TAU))
        )
    if "V4" in curve["classes"]:
        parts.append(
            "V4 separation runs {} to {}, and is {} at tau {}.".format(
                lo["separation"]["V4"]["separated"], hi["separation"]["V4"]["separated"],
                anchor["separation"]["V4"]["separated"], tau_label(ANCHOR_TAU))
        )
    shares = [p["warranted_share"] for p in points.values()]
    if all(s is not None for s in shares):
        top = max(shares)
        attaining = [p["tau"] for p in points.values() if p["warranted_share"] == top]
        if len(attaining) == len(shares):
            parts.append(
                "The warranted-outcome share is flat at {:.1%} across the grid.".format(top))
        else:
            parts.append(
                "The warranted-outcome share peaks at {:.1%}, first reached at tau {}, "
                "and is {:.1%} at tau {}.".format(
                    top, tau_label(min(attaining)), anchor["warranted_share"],
                    tau_label(ANCHOR_TAU))
            )
    op = ops["fb_le_1pct"]
    if op["tau_largest"] is None:
        parts.append("No grid tau holds benign false blocks at or below 1%.")
    else:
        parts.append(
            "The 1% false-block budget is met from tau {} upward.".format(
                tau_label(op["tau_smallest"]))
        )
    return " ".join(parts)


def build_summary_md(state: dict) -> str:
    lines = []
    add = lines.append

    add("# E2 tau sweep: the quality tolerance recomputed over the E1 verdicts")
    add("")
    add(LAUNCH_QUESTIONS)
    add("")
    add("## Run")
    add("")
    lines.extend(md_table(["field", "value"], [
        ["date", state["meta"]["date"]],
        ["sweep version", state["meta"]["sweep_version"]],
        ["evaluated arms swept", ", ".join(state["meta"]["arms"])],
        ["source directories", "<br>".join("`{}`".format(d)
                                           for d in state["meta"]["eval_dirs"])],
        ["verdict rows read", state["meta"]["n_rows"]],
        ["groups (arm x mode x thinking)", len(state["groups"])],
        ["tau grid", ", ".join(tau_label(t) for t in TAU_GRID)],
        ["anchor tau", tau_label(ANCHOR_TAU)],
        ["anchor checks", "{} of {} pass".format(state["meta"]["anchor_passed"],
                                                 state["meta"]["anchor_total"])],
        ["monotonicity checks", "{} of {} pass".format(state["meta"]["mono_passed"],
                                                       state["meta"]["mono_total"])],
        ["wall", "{:.2f} s".format(state["meta"]["wall_s"])],
    ]))
    add("")
    add("Pure post-processing: no model was called, no GPU was held, and nothing was "
        "replayed or dispatched. Tau enters the guard only as the final `gap <= tau` "
        "comparison at stage 3, and every G_CERT verdict row already records its "
        "certified gap, so the whole sweep is arithmetic over the frozen verdict logs.")
    add("")

    add("## How each terminal was recomputed")
    add("")
    lines.extend(md_table(
        ["recorded G_CERT row", "terminal at tolerance tau", "rows"],
        [
            ["`blocked_schema` or `blocked_feas`",
             "unchanged (the proposal never reached the quality gate)",
             state["meta"]["n_pre_qual_blocked"]],
            ["carries a certificate gap",
             "`blocked_qual` if gap > tau, else `applied_with_certificate`",
             state["meta"]["n_certified"]],
            ["no certificate gap and no early block",
             "kept exactly as recorded (`lb_unavailable` blocks and "
             "`execution_failed` rows are tau-invariant)",
             state["meta"]["n_tau_invariant_uncertified"]],
        ]))
    add("")
    if state["meta"]["n_tau_invariant_uncertified"]:
        add("The third row is carried through verbatim: recorded terminals {}.".format(
            state["meta"]["tau_invariant_uncertified_terminals"]))
    else:
        add("The third row is empty in every arm swept here: no evaluated proposal "
            "reached stage 3 without producing a certificate, and no arm carries an "
            "instrument fault, so no verdict had to be carried through by fiat.")
    add("")
    add("Rows with an `infra_error` finding are instrument faults, never guard "
        "decisions, and are excluded from every rate, per the E1 evaluator's "
        "convention ({} such rows under G_CERT across all arms). G_FEAS verdicts are "
        "tau-invariant, so the separation counts reuse them unchanged.".format(
            state["meta"]["n_infra_cert"]))
    add("")
    add("The **warranted-outcome share** is the guidance's warranted-outcome rate "
        "(`L1_Complete_Guidance.md`, Section 5.4: the fraction of instructions whose "
        "disposition carries a machine-checkable justification, a certificate on "
        "applied proposals or a matched violation label on blocks). No module in the "
        "codebase computes it, so the operational reading here is the freeze's: a row "
        "counts as warranted when it ends `applied_with_certificate`, or when it is "
        "blocked and its item carries an injected violation label (`primary_class` "
        "other than `benign`). E1 has no referral arm, so the third disposition "
        "contributes nothing. Denominator: all rows of the group eligible under "
        "G_CERT.")
    add("")
    add("What that reading counts, stated so no reader has to infer it: a violation "
        "item blocked at the schema stage is warranted here, even though the block "
        "was triggered by the shape of the proposal rather than by the injected "
        "violation. That is why the M_free groups sit near 60%, which is the share of "
        "violation items in the suite: almost every row is schema-blocked, and the "
        "violation ones therefore count as warranted while the benign ones do not. A "
        "stricter reading, requiring the blocking finding code to match the injected "
        "violation subclass, is not implemented anywhere in the codebase and is not "
        "used here.")
    add("")

    # -- per-arm curves ------------------------------------------------------- #
    add("## Curves per arm, mode and thinking (pooled over repeats)")
    add("")
    for entry in state["groups"]:
        key = (entry["arm"], entry["mode"], entry["thinking"])
        curve = entry["curve"]
        add("### {} - {} - thinking {}".format(entry["arm"], entry["mode"],
                                               thinking_label(entry["thinking"])))
        add("")
        add("{} rows pooled over repeats {}; source `{}`.".format(
            curve["n_rows"], ", ".join(str(r) for r in entry["repeats"]),
            entry["source_dir"]))
        add("")
        classes = curve["classes"]
        headers = (["tau"] + ["{} blocked".format(c) for c in classes]
                   + ["benign false-block rate", "V3 separated", "V4 separated",
                      "warranted share"])
        rows = []
        for tau in TAU_GRID:
            point = curve["points"][tau_label(tau)]
            cells = [tau_label(tau)]
            for cls in classes:
                block = point["blocks"][cls]
                cells.append("{}/{} ({})".format(block["blocked"], block["n"],
                                                 pct(block["blocked"], block["n"])))
            cells.append(fmt_rate(point["false_block_rate"]))
            for cls in ("V3", "V4"):
                cells.append(point["separation"][cls]["separated"]
                             if cls in classes else "-")
            cells.append(fmt_rate(point["warranted_share"]))
            rows.append(cells)
        lines.extend(md_table(headers, rows))
        add("")
        add("What the curve shows: {}".format(entry["statement"]))
        add("")

    # -- operating points ------------------------------------------------------ #
    add("## Operating points")
    add("")
    add("The frozen rule is the **largest** grid tau whose benign false-block rate "
        "meets the budget. Because that rate is non-increasing in tau, the largest "
        "qualifying tau is the loosest gate meeting the budget and, whenever any grid "
        "point qualifies, it is the top of the grid; the smallest qualifying tau is "
        "the tightest gate meeting the same budget and blocks the most violations. "
        "Both are printed, the frozen one first.")
    add("")
    rows = []
    for entry in state["groups"]:
        ops = entry["operating_points"]
        cells = [entry["arm"], entry["mode"], thinking_label(entry["thinking"])]
        for target_key in ("fb_le_1pct", "fb_le_5pct"):
            op = ops[target_key]
            if op["tau_largest"] is None:
                cells.extend(["none", "none"])
            else:
                cells.append("{} ({})".format(tau_label(op["tau_largest"]),
                                              fmt_rate(op["false_block_rate_at_largest"])))
                cells.append("{} ({})".format(tau_label(op["tau_smallest"]),
                                              fmt_rate(op["false_block_rate_at_smallest"])))
        rows.append(cells)
    lines.extend(md_table(
        ["arm", "mode", "thinking",
         "largest tau, false blocks <= 1%", "smallest tau, false blocks <= 1%",
         "largest tau, false blocks <= 5%", "smallest tau, false blocks <= 5%"], rows))
    add("")
    add("`none` means no grid tau meets that budget for the group: the benign "
        "false-block rate has a floor set by the schema and feasibility gates, which "
        "no value of tau can move.")
    add("")

    # -- V3 separation, three numbers ------------------------------------------ #
    add("### V3 separation at three tolerances")
    add("")
    rows = []
    for entry in state["groups"]:
        curve = entry["curve"]
        if "V3" not in curve["classes"]:
            continue
        cells = [entry["arm"], entry["mode"], thinking_label(entry["thinking"]),
                 curve["points"][tau_label(0.05)]["separation"]["V3"]["n"]]
        for tau in (0.05, 0.20, 0.50):
            sep = curve["points"][tau_label(tau)]["separation"]["V3"]
            cells.append("{} ({})".format(sep["separated"], pct(sep["separated"], sep["n"])))
        rows.append(cells)
    lines.extend(md_table(
        ["arm", "mode", "thinking", "V3 items", "tau 0.05", "tau 0.20", "tau 0.50"], rows))
    add("")

    # -- anchor ----------------------------------------------------------------- #
    add("## Hard anchor: tau = 0.20 reproduces the accepted E1 numbers")
    add("")
    add("Every number this script produces at tau = {} is compared to the accepted "
        "value in the arm's own `summary.json`: the G_CERT terminal counts, the "
        "per-class block counts and rates, and the separation quadruple with its "
        "share. A mismatch exits non-zero.".format(tau_label(ANCHOR_TAU)))
    add("")
    rows = []
    for entry in state["groups"]:
        checks = entry["anchor"]
        failed = [c for c in checks if not c["pass"]]
        rows.append([entry["arm"], entry["mode"], thinking_label(entry["thinking"]),
                     len(checks), len(failed),
                     "PASS" if not failed else "**FAIL**"])
    lines.extend(md_table(
        ["arm", "mode", "thinking", "checks", "failed", "verdict"], rows))
    add("")
    failures = [c for entry in state["groups"] for c in entry["anchor"] if not c["pass"]]
    if failures:
        add("### Anchor failures")
        add("")
        lines.extend(md_table(
            ["group", "check", "accepted (summary.json)", "produced here"],
            [[c["group"], c["check"], c["expected"], c["got"]] for c in failures]))
        add("")

    # -- monotonicity ----------------------------------------------------------- #
    add("## Monotonicity: no rate rises with tau")
    add("")
    add("Raising tau can only turn a `blocked_qual` into an "
        "`applied_with_certificate`, never the reverse, so every block count, the "
        "benign false-block rate and the V3/V4 separation counts must be "
        "non-increasing across the grid. Checked series by series.")
    add("")
    mono_failures = [c for entry in state["groups"] for c in entry["monotonicity"]
                     if not c["pass"]]
    rows = []
    for entry in state["groups"]:
        checks = entry["monotonicity"]
        bad = [c for c in checks if not c["pass"]]
        rows.append([entry["arm"], entry["mode"], thinking_label(entry["thinking"]),
                     len(checks), len(bad), "PASS" if not bad else "**FAIL**"])
    lines.extend(md_table(
        ["arm", "mode", "thinking", "series checked", "violations", "verdict"], rows))
    add("")
    if mono_failures:
        add("### Monotonicity violations")
        add("")
        lines.extend(md_table(
            ["group", "series", "violations"],
            [[c["group"], c["series"], "; ".join(c["violations"])] for c in mono_failures]))
        add("")

    add("Files: `summary.md`, `summary.json`, `curves.csv` (long format: arm, mode, "
        "thinking, tau, class, items, blocks, block_rate, false_block_rate, "
        "v3_separated, v4_separated, warranted_share; the last four are group-level "
        "and repeat on every class row of that group and tau).")
    return "\n".join(lines)


CSV_HEADER = ["arm", "mode", "thinking", "tau", "class", "items", "blocks",
              "block_rate", "false_block_rate", "v3_separated", "v4_separated",
              "warranted_share"]


def write_curves_csv(path: Path, state: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        for entry in state["groups"]:
            curve = entry["curve"]
            for tau in TAU_GRID:
                point = curve["points"][tau_label(tau)]
                v3 = point["separation"]["V3"]["separated"] if "V3" in curve["classes"] else ""
                v4 = point["separation"]["V4"]["separated"] if "V4" in curve["classes"] else ""
                for cls in curve["classes"]:
                    block = point["blocks"][cls]
                    writer.writerow([
                        entry["arm"], entry["mode"], thinking_label(entry["thinking"]),
                        tau_label(tau), cls, block["n"], block["blocked"],
                        "" if block["rate"] is None else "{:.6f}".format(block["rate"]),
                        "" if point["false_block_rate"] is None
                        else "{:.6f}".format(point["false_block_rate"]),
                        v3, v4,
                        "" if point["warranted_share"] is None
                        else "{:.6f}".format(point["warranted_share"]),
                    ])


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-root", default=str(CODE_DIR.parent / "results"),
                    help="directory holding the e1_eval_* evaluation directories")
    ap.add_argument("--eval-dir", action="append", default=None,
                    help="sweep only this evaluation directory (repeatable); "
                         "default is every e1_eval_* under --results-root")
    ap.add_argument("--out", default=None,
                    help="output directory (default: <results-root>/e2_tau_sweep)")
    ap.add_argument("--force", action="store_true",
                    help="allow writing into a directory that already has results")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="skip an e1_eval_* directory that is missing a verdict or "
                         "summary file instead of refusing to run")
    args = ap.parse_args()

    print(LAUNCH_QUESTIONS)
    started = time.perf_counter()

    root = Path(args.results_root).resolve()
    out_dir = Path(args.out).resolve() if args.out else root / "e2_tau_sweep"
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit(
            "REFUSING TO RUN: {} already has results. Move it aside or pass "
            "--force.".format(out_dir)
        )

    eval_dirs = discover_eval_dirs(root, args.eval_dir)
    usable, skipped = [], []
    for d in eval_dirs:
        missing = [f for f in REQUIRED_FILES if not (d / f).exists()]
        if not missing:
            usable.append(d)
            continue
        if args.allow_incomplete:
            skipped.append((d, missing))
            continue
        raise SystemExit(
            "REFUSING TO RUN: {} is missing {}; an evaluation directory that is "
            "still being written would be swept as if it were complete. Move it "
            "aside, or pass --allow-incomplete to skip it.".format(
                d, ", ".join(missing))
        )
    if not usable:
        raise SystemExit("REFUSING TO RUN: no complete evaluation directory to sweep")
    for d, missing in skipped:
        print("[e2-tau] SKIPPED {} (missing {})".format(d, ", ".join(missing)))

    print("\n[e2-tau] sweeping {} evaluation director{}".format(
        len(usable), "y" if len(usable) == 1 else "ies"))
    arms_loaded = []
    all_rows = []
    summaries = {}
    source_of = {}
    for d in usable:
        arm = load_arm(d)
        arms_loaded.extend(arm["arms"])
        all_rows.extend(arm["rows"])
        for label in arm["arms"]:
            summaries[label] = arm["summary"]
            source_of[label] = str(d)
        print("[e2-tau] {:<28s} arms {:<24s} rows {}".format(
            d.name, ",".join(arm["arms"]), len(arm["rows"])))

    duplicate = [a for a, n in Counter(arms_loaded).items() if n > 1]
    if duplicate:
        raise SystemExit(
            "REFUSING TO RUN: arm label(s) {} appear in more than one evaluation "
            "directory; pooling two evaluations of one arm would double-count "
            "it.".format(", ".join(sorted(duplicate)))
        )

    groups = group_rows(all_rows)
    state = {"groups": [], "meta": {}}
    anchor_total = anchor_passed = mono_total = mono_passed = 0

    for key, rows in groups.items():
        arm, mode, thinking = key
        classes = sorted({r["primary_class"] for r in rows})
        curve = group_curve(rows, classes)
        ops = operating_points(curve)
        anchor = anchor_checks(key, curve, summaries[arm])
        mono = monotonicity_checks(key, curve)
        anchor_total += len(anchor)
        anchor_passed += sum(1 for c in anchor if c["pass"])
        mono_total += len(mono)
        mono_passed += sum(1 for c in mono if c["pass"])
        entry = {
            "arm": arm, "mode": mode, "thinking": thinking,
            "source_dir": source_of[arm],
            "repeats": sorted({r["repeat"] for r in rows},
                              key=lambda v: (v is None, v)),
            "curve": curve,
            "operating_points": ops,
            "anchor": anchor,
            "monotonicity": mono,
        }
        entry["statement"] = curve_statement(key, curve, ops)
        state["groups"].append(entry)
        print("[e2-tau] {:<20s} {:<14s} thinking {:<8s} rows {:>6d}  anchor {}/{}  "
              "monotone {}/{}".format(
                  arm, mode, thinking_label(thinking), len(rows),
                  sum(1 for c in anchor if c["pass"]), len(anchor),
                  sum(1 for c in mono if c["pass"]), len(mono)))

    wall = time.perf_counter() - started
    state["meta"] = {
        "sweep_version": SWEEP_VERSION,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "results_root": str(root),
        "out_dir": str(out_dir),
        "eval_dirs": [str(d) for d in usable],
        "skipped_dirs": [{"dir": str(d), "missing": m} for d, m in skipped],
        "arms": sorted(set(arms_loaded)),
        "n_rows": len(all_rows),
        "tau_grid": list(TAU_GRID),
        "anchor_tau": ANCHOR_TAU,
        "false_block_targets": list(FALSE_BLOCK_TARGETS),
        "n_pre_qual_blocked": sum(1 for r in all_rows
                                  if r["cert_terminal"] in PRE_QUAL_BLOCKS),
        "n_certified": sum(1 for r in all_rows if r["gap"] is not None
                           and r["cert_terminal"] not in PRE_QUAL_BLOCKS),
        "n_tau_invariant_uncertified": len(tau_invariant_rows(all_rows)),
        "tau_invariant_uncertified_terminals": dict(
            Counter(r["cert_terminal"] for r in tau_invariant_rows(all_rows))),
        "n_infra_cert": sum(1 for r in all_rows if r["cert_infra"]),
        "anchor_total": anchor_total,
        "anchor_passed": anchor_passed,
        "mono_total": mono_total,
        "mono_passed": mono_passed,
        "wall_s": wall,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    text = build_summary_md(state)
    (out_dir / "summary.md").write_text(text)
    (out_dir / "summary.json").write_text(
        json.dumps(state, indent=1, sort_keys=True, default=str))
    write_curves_csv(out_dir / "curves.csv", state)

    print("\n" + text)
    print("\n[e2-tau] arms swept: {}".format(", ".join(state["meta"]["arms"])))
    print("[e2-tau] written to {}".format(out_dir))
    print("[e2-tau] wall {:.2f} s".format(wall))

    failed_anchor = [c for entry in state["groups"] for c in entry["anchor"]
                     if not c["pass"]]
    failed_mono = [c for entry in state["groups"] for c in entry["monotonicity"]
                   if not c["pass"]]
    if failed_anchor:
        print("\n[e2-tau] HARD ANCHOR FAILED at tau = {}: {} of {} checks".format(
            tau_label(ANCHOR_TAU), len(failed_anchor), anchor_total))
        for c in failed_anchor[:20]:
            print("  {} | {} | accepted {!r} | produced {!r}".format(
                c["group"], c["check"], c["expected"], c["got"]))
        return 3
    print("[e2-tau] hard anchor at tau = {}: {} checks PASS".format(
        tau_label(ANCHOR_TAU), anchor_total))
    if failed_mono:
        print("\n[e2-tau] MONOTONICITY FAILED: {} of {} series".format(
            len(failed_mono), mono_total))
        for c in failed_mono[:20]:
            print("  {} | {} | {}".format(c["group"], c["series"],
                                          "; ".join(c["violations"])))
        return 4
    print("[e2-tau] monotonicity: {} series PASS".format(mono_total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
