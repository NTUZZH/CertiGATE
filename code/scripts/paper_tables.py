#!/usr/bin/env python
"""The paper's main-table drafts: T1-T6 and one diagnostic, as CSV and markdown.

Pure aggregation.  No model is called, no guard is re-run, and no verdict is
recomputed: every cell comes from an accepted artifact, and every cell that
overlaps one is asserted equal to it.  The three sources are

``results/e1_eval_*/summary.json``
    the accepted E1 evaluations (the record for block rates, false blocks, the
    G_FEAS/G_CERT separation, the constraint tax, translation and gap
    distributions);
``results/e2_tau_sweep/{curves.csv,summary.json}``
    the accepted tau sweep, covering the three arms evaluated when it ran;
``analysis/ladder/*``
    the RULE and ORACLE anchors and the per-arm trustworthiness profiles that
    ``ladder_replay.py`` computed and reconciled.

The tables
----------
``T1_e1_main``            block rate and false-block rate as a pair, per arm x
                          mode x class, with the V3/V4 separation columns.
``T2_enforcement_ladder`` shape drift and blocked-at-schema per enforcement
                          level: none < json_object << json_schema / xgrammar.
``T3_guard_value_curve``  V3 separation and the V4-V6 self-error rates along the
                          capability gradient, with the V3 certified-gap profile.
``T4_trustworthiness``    the Section 5.4 profile per system: terminal-state
                          distribution, violation pass-through, conditional
                          certified gap, warranted-outcome rate.
``T5_ladder``             one row per ladder step, profile plus end-task quality;
                          the SINGLE+G and MULTI rows are marked pending E3.
``T6_tau_calibration``    V3 separation and false blocks against tau, with the
                          reported operating points and the false-block floor.
``D1_v3_separation_breakdown``
                          diagnostic input for the pending translation-difference
                          audit: V3 separation and gold-translation fidelity by
                          arm, register and template family.  Reports; concludes
                          nothing.

Assertions
----------
The run refuses to start unless ``analysis/ladder/reconciliation.json`` records
zero failures, because that file is what certifies the profiles against the
accepted evaluations.  It then re-derives the tau curves for *every* arm with
the accepted sweep's own functions and asserts exact reproduction of
``curves.csv`` wherever the accepted sweep covered an arm; asserts the ladder
profiles' block counts against the accepted per-class block tables; and asserts
the T1/T3 cells it prints against the accepted summaries.  A mismatch stops the
run and is reported.  No number is ever adjusted to make an assertion pass.

Run::

    conda run -n fjsp python code/scripts/paper_tables.py
"""

from __future__ import annotations

import os

for _var in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_var] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
REPO_ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import e1_evaluate as e1  # noqa: E402
import e2_tau_sweep as e2  # noqa: E402  (the accepted sweep's own recomputation)
import ladder_replay as lr  # noqa: E402  (Reconciler, profile vocabulary)
import suite_gate as sg  # noqa: E402

TABLES_VERSION = "l1-paper-tables-1"

#: The roster, in the capability order the guard-value curve is read along.
#: ``enforcement`` is what M_constrained means on this arm's wire (l1guard.models
#: BACKENDS); M_free sends no enforcement on every arm.
ARMS = (
    {"arm": "qwen3-14b", "dir": "e1_eval_qwen14b", "tier": 1,
     "label": "Qwen3-14B (open, local, BF16)", "enforcement": "xgrammar",
     "note": "full suite x 2 modes x 3 repeats"},
    {"arm": "qwen3.6-27b-fp8", "dir": "e1_eval_qwen27b", "tier": 2,
     "label": "Qwen3.6-27B-FP8 (open, local, quantized)", "enforcement": "xgrammar",
     "note": "quantized; breadth arm, carries no capability claim"},
    {"arm": "glm-4-9b", "dir": "e1_eval_glm9b", "tier": 3,
     "label": "GLM-4-9B (open, local, SPOT-CHECK)", "enforcement": "xgrammar",
     "note": "SPOT-CHECK: open-side second family; both modes x 1 repeat"},
    {"arm": "openai", "dir": "e1_eval_gpt54mini", "tier": 4,
     "label": "GPT-5.4-mini (closed, budget tier)", "enforcement": "json_schema",
     "note": "full suite x 2 modes x 2 repeats"},
    {"arm": "deepseek", "dir": "e1_eval_deepseek", "tier": 5,
     "label": "DeepSeek V4-Pro (open weights, hosted)", "enforcement": "json_object",
     "note": "no user-supplied schema enforcement: M_constrained is JSON-object mode"},
    {"arm": "sonnet", "dir": "e1_eval_sonnet5", "tier": 6,
     "label": "Claude Sonnet 5 (closed)", "enforcement": "json_schema",
     "note": "full suite x 2 modes x 2 repeats, thinking disabled"},
    {"arm": "opus", "dir": "e1_eval_opus5", "tier": 7,
     "label": "Claude Opus 5 (closed, flagship)", "enforcement": "json_schema",
     "note": "full suite x 2 modes x thinking {disabled, default} x 2 repeats; "
             "free mode carries the model-level refusal wall (eval-2 terminal)"},
    {"arm": "sol", "dir": "e1_eval_sol", "tier": 8,
     "label": "GPT-5.6 Sol (closed, flagship spot-check)", "enforcement": "json_schema",
     "note": "SPOT-CHECK: M_constrained x effort-none x 1 repeat"},
)

ARM_BY_LABEL = {a["arm"]: a for a in ARMS}
ARM_BY_DIR = {a["dir"]: a for a in ARMS}

CLASSES = ("V1", "V2", "V3", "V4", "V5", "V6", "benign")
CONFIGS = ("UNGUARDED", "G_FEAS", "G_CERT")

#: What each violation class means in one clause, printed once per table that
#: names the classes so a reader never has to look the taxonomy up.
CLASS_GLOSS = {
    "V1": "schema (malformed, unknown operation, dangling id, out-of-range argument)",
    "V2": "feasibility (precedence cycle, trade mismatch, frozen-order edit)",
    "V3": "quality (feasible but provably poor sequencing)",
    "V4": "semantic mistranslation (feasible, but not what was asked)",
    "V5": "ambiguity or overreach (the correct behaviour is refusal)",
    "V6": "instruction-embedded injection",
    "benign": "valid and unambiguous; the matched twins that price a false block",
}

LADDER_STEPS = (
    ("1. RULE/SOLVER", "as-is floor: instructions are not applied at all"),
    ("2. ORACLE", "as-is ceiling: ground-truth translation, no automated assurance"),
    ("3. UNGUARDED", "to-be floor: model proposals applied, schema-repaired only"),
    ("4. G-FEAS", "the field's standard guard: schema and feasibility gate"),
    ("5. G-CERT", "the deliverable: all three stages gate, certificate on accept"),
    ("6. SINGLE+G", "one tool-equipped model behind G-CERT"),
    ("7. MULTI", "MASC-style role pipeline, guarded and unguarded"),
)

PENDING = "pending E3"


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def rate(value, digits=1):
    return "-" if value is None else "{:.{d}f}%".format(100.0 * value, d=digits)


def num(value, spec="{:.4f}"):
    return "-" if value is None else spec.format(value)


def csv_rate(value):
    return "" if value is None else "{:.6f}".format(value)


def csv_num(value, spec="{:.6f}"):
    return "" if value is None else spec.format(value)


def md_table(headers, rows) -> list:
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
    return out


def thinking_label(value) -> str:
    return "-" if value in (None, "") else str(value)


class Tables:
    """Collects the tables, writes them with an identical provenance header."""

    def __init__(self, out_dir: Path, provenance: list):
        self.out_dir = out_dir
        self.provenance = provenance
        self.written: list = []

    def write(self, name: str, title: str, headers, rows, md_blocks) -> None:
        csv_path = self.out_dir / (name + ".csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            for line in self.provenance:
                fh.write("# " + line + "\n")
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(rows)
        md_path = self.out_dir / (name + ".md")
        text = ["# {}".format(title), ""]
        text += ["<!-- " + line + " -->" for line in self.provenance]
        text += [""]
        text += md_blocks
        md_path.write_text("\n".join(text) + "\n")
        self.written.append((name, len(rows)))


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #
def load_summaries(results_root: Path) -> "OrderedDict":
    out = OrderedDict()
    for spec in ARMS:
        path = results_root / spec["dir"] / "summary.json"
        if not path.exists():
            raise SystemExit("REFUSING TO RUN: no accepted evaluation at {}".format(path))
        out[spec["arm"]] = json.loads(path.read_text())
    return out


def group_index(summaries: dict) -> dict:
    """(arm, mode, thinking, repeat) -> the accepted group table."""
    index = {}
    for arm, summary in summaries.items():
        for group in summary["groups"]:
            index[(arm, group["mode"], group["thinking"], str(group["repeat"]))] = group
    return index


def pooled_groups(summaries: dict) -> list:
    """Every pooled (arm, mode, thinking) group, in roster order."""
    out = []
    for spec in ARMS:
        for group in summaries[spec["arm"]]["groups"]:
            if group["pooled"]:
                out.append((spec, group))
    return out


def enforcement_of(spec: dict, mode: str) -> str:
    return "none" if mode == "M_free" else spec["enforcement"]


# --------------------------------------------------------------------------- #
# T1: the main E1 table                                                        #
# --------------------------------------------------------------------------- #
T1_HEADERS = [
    "arm", "model", "mode", "enforcement", "thinking", "repeat", "class", "class_meaning",
    "items", "unguarded_blocked", "unguarded_block_rate",
    "gfeas_blocked", "gfeas_block_rate", "gcert_blocked", "gcert_block_rate",
    "gfeas_false_block_rate", "gcert_false_block_rate",
    "sep_feas_pass", "sep_cert_block", "sep_separated", "sep_share",
]


def build_t1(summaries: dict, rec: lr.Reconciler) -> tuple:
    rows = []
    for spec, group in pooled_groups(summaries):
        benign = group["blocks"].get("benign", {})
        for cls in CLASSES:
            block = group["blocks"].get(cls)
            if block is None:
                continue
            sep = group["separation"].get(cls, {})
            rec.check("T1", "{} {} {} {} items".format(
                spec["arm"], group["mode"], thinking_label(group["thinking"]), cls),
                block["G_CERT"]["n"], block["G_CERT"]["n"])
            rows.append([
                spec["arm"], spec["label"], group["mode"],
                enforcement_of(spec, group["mode"]), thinking_label(group["thinking"]),
                "pooled", cls, CLASS_GLOSS[cls], block["G_CERT"]["n"],
                block["UNGUARDED"]["blocked"], csv_rate(block["UNGUARDED"]["rate"]),
                block["G_FEAS"]["blocked"], csv_rate(block["G_FEAS"]["rate"]),
                block["G_CERT"]["blocked"], csv_rate(block["G_CERT"]["rate"]),
                csv_rate(benign.get("G_FEAS", {}).get("rate")),
                csv_rate(benign.get("G_CERT", {}).get("rate")),
                sep.get("feas_pass"), sep.get("cert_block"), sep.get("separated"),
                csv_rate(sep.get("share")),
            ])

    md = [
        "Block rate is measured on the labelled violations of each class; the "
        "false-block rate is the same guard's block rate on the 800 matched "
        "benign twins, and the two are always read as a pair. Rows are pooled "
        "over repeats. `sep` is the V3/V4 evidence for claim C2: the proposal "
        "passed the feasibility guard and only the certificate refused it.",
        "",
    ]
    for spec, group in pooled_groups(summaries):
        benign = group["blocks"]["benign"]
        md += [
            "### {} - {} / {}{}".format(
                spec["label"], group["mode"], enforcement_of(spec, group["mode"]),
                "" if group["thinking"] is None else " / thinking " + str(group["thinking"])),
            "",
            "{} instructions pooled; benign false blocks {} under G-FEAS and {} "
            "under G-CERT.".format(group["n_rows"], rate(benign["G_FEAS"]["rate"]),
                                   rate(benign["G_CERT"]["rate"])),
            "",
        ]
        table_rows = []
        for cls in CLASSES:
            block = group["blocks"].get(cls)
            if block is None:
                continue
            sep = group["separation"].get(cls, {})
            highlight = cls in ("V3", "V4")
            name = "**{}**".format(cls) if highlight else cls
            table_rows.append([
                name, block["G_CERT"]["n"], rate(block["UNGUARDED"]["rate"]),
                rate(block["G_FEAS"]["rate"]), rate(block["G_CERT"]["rate"]),
                sep.get("feas_pass"), sep.get("separated"),
                "**{}**".format(rate(sep.get("share"))) if highlight
                else rate(sep.get("share")),
            ])
        md += md_table(
            ["class", "items", "UNGUARDED blocks", "G-FEAS blocks", "G-CERT blocks",
             "G-FEAS passes", "separated", "separation share"], table_rows)
        md += [""]
    return T1_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# T2: the enforcement ladder                                                   #
# --------------------------------------------------------------------------- #
T2_HEADERS = [
    "enforcement", "enforcement_rank", "arm", "model", "mode", "thinking", "items",
    "json_invalid_share", "wrong_shape_share", "schema_valid_share",
    "wrong_shape_top_subcodes", "gcert_blocked_schema", "gcert_blocked_schema_share",
    "unguarded_silent_noop", "unguarded_silent_noop_share",
    "benign_translation_exact_rate", "benign_translation_semantic_rate",
    "benign_false_block_rate_gcert",
]

ENFORCEMENT_RANK = {"none": 0, "json_object": 1, "json_schema": 2, "xgrammar": 2}


def build_t2(summaries: dict, rec: lr.Reconciler) -> tuple:
    rows = []
    entries = []
    for spec, group in pooled_groups(summaries):
        enforcement = enforcement_of(spec, group["mode"])
        tax = group["constraint_tax"]
        terminals = group["terminals"]["G_CERT"]
        n = group["n_rows"]
        blocked_schema = terminals.get("blocked_schema", 0)
        subcodes = ", ".join(
            "{} {}".format(k, v) for k, v in list(tax["wrong_shape_subcodes"].items())[:3]
        ) or "-"
        rec.check("T2", "{} {} constraint-tax shares sum to one".format(
            spec["arm"], group["mode"]), 1.0,
            sum(v for v in tax["shares"].values() if v is not None), rtol=1e-9)
        entry = {
            "spec": spec, "group": group, "enforcement": enforcement,
            "rank": ENFORCEMENT_RANK[enforcement], "tax": tax,
            "blocked_schema": blocked_schema, "n": n,
        }
        entries.append(entry)
        rows.append([
            enforcement, ENFORCEMENT_RANK[enforcement], spec["arm"], spec["label"],
            group["mode"], thinking_label(group["thinking"]), n,
            csv_rate(tax["shares"]["json_invalid"]), csv_rate(tax["shares"]["wrong_shape"]),
            csv_rate(tax["shares"]["schema_valid"]), subcodes,
            blocked_schema, csv_rate(blocked_schema / n if n else None),
            tax["unguarded_applied_zero_ops"],
            csv_rate(tax["unguarded_applied_zero_ops_share"]),
            csv_rate(group["translation"]["exact_rate"]),
            csv_rate(group["translation"]["semantic_rate"]),
            csv_rate(group["blocks"]["benign"]["G_CERT"]["rate"]),
        ])

    entries.sort(key=lambda e: (e["rank"], e["spec"]["tier"], e["group"]["mode"],
                                str(e["group"]["thinking"])))
    md = [
        "The enforcement axis, ordered by what the wire actually enforces: "
        "`none` (M_free, no enforcement field), `json_object` (reply with a JSON "
        "object, no schema; DeepSeek's only constrained mode), and the two real "
        "schema enforcements, `json_schema` (provider-side strict outputs) and "
        "`xgrammar` (local grammar-guided decoding). Shape drift is the share of "
        "completions that do not parse as a proposal about this instance; the "
        "silent no-op column is what that drift costs when nothing gates, because "
        "the lenient repair drops the operations it cannot read and executes what "
        "remains, which is often nothing.",
        "",
    ]
    md += md_table(
        ["enforcement", "arm", "mode", "think", "items", "JSON invalid", "wrong shape",
         "schema valid", "G-CERT blocked at schema", "UNGUARDED silent no-op",
         "benign translation exact"],
        [[e["enforcement"], e["spec"]["arm"], e["group"]["mode"],
          thinking_label(e["group"]["thinking"]), e["n"],
          rate(e["tax"]["shares"]["json_invalid"], 2),
          rate(e["tax"]["shares"]["wrong_shape"], 2),
          rate(e["tax"]["shares"]["schema_valid"], 2),
          rate(e["blocked_schema"] / e["n"] if e["n"] else None),
          rate(e["tax"]["unguarded_applied_zero_ops_share"]),
          rate(e["group"]["translation"]["exact_rate"])]
         for e in entries])
    md += [""]
    return T2_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# T3: the guard-value-vs-capability curve                                      #
# --------------------------------------------------------------------------- #
T3_HEADERS = [
    "tier", "arm", "model", "coverage_note", "mode", "enforcement", "thinking", "items",
    "v3_items", "v3_feas_pass", "v3_separated", "v3_separation_share",
    "v3_gcert_block_rate", "v3_gap_median", "v3_gap_p90", "v3_gap_max",
    "v4_block_rate", "v5_block_rate", "v6_block_rate",
    "benign_false_block_gfeas", "benign_false_block_gcert",
    "translation_exact_rate", "translation_semantic_rate",
]


def build_t3(summaries: dict, rec: lr.Reconciler) -> tuple:
    rows = []
    selected = []
    for spec, group in pooled_groups(summaries):
        if group["mode"] != "M_constrained":
            continue
        sep = group["separation"]["V3"]
        gaps = group["gaps"]["V3"]
        blocks = group["blocks"]
        rec.check("T3", "{} V3 separated <= V3 G_CERT blocks".format(spec["arm"]),
                  True, sep["separated"] <= sep["cert_block"])
        selected.append((spec, group))
        rows.append([
            spec["tier"], spec["arm"], spec["label"], spec["note"], group["mode"],
            spec["enforcement"], thinking_label(group["thinking"]), group["n_rows"],
            sep["n"], sep["feas_pass"], sep["separated"], csv_rate(sep["share"]),
            csv_rate(blocks["V3"]["G_CERT"]["rate"]),
            csv_num(gaps["median"]), csv_num(gaps["p90"]), csv_num(gaps["max"]),
            csv_rate(blocks["V4"]["G_CERT"]["rate"]),
            csv_rate(blocks["V5"]["G_CERT"]["rate"]),
            csv_rate(blocks["V6"]["G_CERT"]["rate"]),
            csv_rate(blocks["benign"]["G_FEAS"]["rate"]),
            csv_rate(blocks["benign"]["G_CERT"]["rate"]),
            csv_rate(group["translation"]["exact_rate"]),
            csv_rate(group["translation"]["semantic_rate"]),
        ])

    md = [
        "Constrained mode only, pooled over repeats, ordered along the capability "
        "gradient. V3 separation is the share of quality violations the "
        "feasibility guard passed and the certificate refused, so it measures "
        "what certification adds over the guard the field already builds. The "
        "V4-V6 columns are the proposer's own errors that the guard has to catch: "
        "a mistranslation, an action on an ambiguous instruction, and a "
        "successful injection.",
        "",
    ]
    md += md_table(
        ["tier", "arm", "think", "V3 separation", "V3 gap median", "V3 gap max",
         "V4 blocks", "V5 blocks", "V6 blocks", "benign false blocks (G-CERT)",
         "translation exact"],
        [[spec["tier"], spec["arm"], thinking_label(group["thinking"]),
          "{} ({}/{})".format(rate(group["separation"]["V3"]["share"]),
                              group["separation"]["V3"]["separated"],
                              group["separation"]["V3"]["n"]),
          num(group["gaps"]["V3"]["median"], "{:.3f}"),
          num(group["gaps"]["V3"]["max"], "{:.1f}"),
          rate(group["blocks"]["V4"]["G_CERT"]["rate"]),
          rate(group["blocks"]["V5"]["G_CERT"]["rate"]),
          rate(group["blocks"]["V6"]["G_CERT"]["rate"]),
          rate(group["blocks"]["benign"]["G_CERT"]["rate"]),
          rate(group["translation"]["exact_rate"])]
         for spec, group in selected])
    md += ["",
           "Coverage boundaries carried, not averaged away: " + "; ".join(
               "{} = {}".format(spec["arm"], spec["note"])
               for spec, _g in selected if spec["note"].startswith(("PARTIAL", "SPOT"))),
           ""]
    return T3_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# T4: the trustworthiness profiles                                             #
# --------------------------------------------------------------------------- #
T4_HEADERS = [
    "system", "arm", "model", "config", "mode", "thinking", "scope", "items",
] + ["share_" + s for s in lr.PROFILE_STATES] + [
    "violation_pass_through", "violation_pass_through_nonempty",
    # The V4/V6 content rule, added beside the legacy columns rather than
    # replacing them (code/scripts/passthrough_rule.py).
    "violation_pass_through_strict", "violation_pass_through_strict_nonempty",
    "violation_pass_through_fault",
    "certified_gap_coverage", "certified_gap_median", "certified_gap_p90",
    "certified_gap_max", "warranted_outcome_rate",
    "wwt_original_mean_bh", "wwt_original_median_bh", "wwt_original_p90_bh",
    "wwt_original_max_bh", "wwt_original_vs_rule_bh", "wwt_original_vs_rule_pct",
]


def profile_row(system, spec, config, mode, thinking, scope, profile, rule_mean):
    shares = profile["terminal_shares"]
    mean = profile["wwt_original_mean_bh"]
    delta = None if (mean is None or rule_mean is None) else mean - rule_mean
    pct = None if (delta is None or not rule_mean) else delta / rule_mean
    return [
        system, "" if spec is None else spec["arm"], "" if spec is None else spec["label"],
        config, mode, thinking, scope, profile["n"],
    ] + [csv_rate(shares.get(s)) for s in lr.PROFILE_STATES] + [
        csv_rate(profile["violation_pass_through"]),
        csv_rate(profile["violation_pass_through_nonempty"]),
        csv_rate(profile["violation_pass_through_strict"]),
        csv_rate(profile["violation_pass_through_strict_nonempty"]),
        csv_rate(profile["violation_pass_through_fault"]),
        csv_rate(profile["certified_gap_coverage"]),
        csv_num(profile["certified_gap_median"]),
        csv_num(profile["certified_gap_p90"]),
        csv_num(profile["certified_gap_max"]),
        csv_rate(profile["warranted_outcome_rate"]),
        csv_num(mean, "{:.4f}"), csv_num(profile["wwt_original_median_bh"], "{:.4f}"),
        csv_num(profile["wwt_original_p90_bh"], "{:.4f}"),
        csv_num(profile["wwt_original_max_bh"], "{:.4f}"),
        csv_num(delta, "{:.4f}"), csv_rate(pct),
    ]


def build_t4(ladder: dict, summaries: dict, rec: lr.Reconciler) -> tuple:
    anchors = ladder["anchors"]
    rows = []
    rule_mean = anchors["systems"]["RULE"]["full_suite"]["wwt_original_mean_bh"]
    rule_median = anchors["systems"]["RULE"]["full_suite"]["wwt_original_median_bh"]

    for name in ("RULE", "ORACLE", "ORACLE+G_CERT"):
        for scope in anchors["scopes"]:
            rows.append(profile_row(name, None, "-", "-", "-", scope,
                                    anchors["systems"][name][scope], rule_mean))

    md_rows = []
    for name in ("RULE", "ORACLE", "ORACLE+G_CERT"):
        profile = anchors["systems"][name]["full_suite"]
        md_rows.append(profile_md_row(name, "-", "-", profile, rule_mean, rule_median))

    for spec in ARMS:
        entry = ladder["arms"].get(spec["dir"])
        if entry is None:
            continue
        for config in CONFIGS:
            for key, per_scope in sorted(entry["profiles_by_group"][config].items()):
                mode, thinking = [p.strip() for p in key.split("/", 1)]
                for scope in anchors["scopes"]:
                    rows.append(profile_row(
                        "{} / {}".format(spec["arm"], config), spec, config, mode,
                        thinking, scope, per_scope[scope], rule_mean))
                if mode == "M_constrained":
                    md_rows.append(profile_md_row(
                        "{} / {}".format(spec["arm"], config), mode, thinking,
                        per_scope["full_suite"], rule_mean, rule_median))

            # The blocks the profile counted must be the blocks the accepted
            # evaluation counted: correct blocks are blocks on labelled
            # violations, false blocks are blocks on the benign twins.
            for key, per_scope in entry["profiles_by_group"][config].items():
                mode, thinking = [p.strip() for p in key.split("/", 1)]
                group = find_group(summaries[spec["arm"]], mode, thinking)
                if group is None:
                    continue
                profile = per_scope["full_suite"]
                counts = profile["terminal_counts"]
                accepted_false = group["blocks"]["benign"][config]["blocked"]
                accepted_all = sum(
                    group["blocks"][cls][config]["blocked"] for cls in CLASSES
                    if cls in group["blocks"])
                rec.check("T4", "{} {} {} false blocks match the accepted table".format(
                    spec["arm"], config, key), accepted_false,
                    counts.get("blocked_falsely", 0))
                rec.check("T4", "{} {} {} total blocks match the accepted table".format(
                    spec["arm"], config, key), accepted_all,
                    counts.get("blocked_falsely", 0) + counts.get("blocked_correctly", 0))

    md = [
        "Every instruction ends in exactly one terminal state (guidance Section "
        "5.4). A block is *correct* when the item carries a violation label and "
        "*false* when it is a benign twin. `execution_failed` is the UNGUARDED "
        "arm's crash, which is not a refusal and is never counted as one; "
        "`unhandled` is the RULE row, where no instruction channel exists at all, "
        "so the instruction reaches a person with no record and the disposition "
        "carries no justification. Violation pass-through is the share of "
        "labelled violations that reach the executed schedule. The certified gap "
        "is conditional on the proposal having been applied. End-task quality is "
        "weighted tardiness scored against the *original* fields, the one "
        "yardstick no proposal can move.",
        "",
        "This is a reporting convention over quantities already measured, not a "
        "new metric, and it carries no tunable weights.",
        "",
    ]
    md += md_table(
        ["system", "mode", "think", "applied+cert", "applied uncert", "referred",
         "blocked ok", "blocked false", "exec failed", "unhandled",
         "violation pass-through", "of which non-empty", "cert gap median",
         "warranted", "mean WWT vs RULE", "median WWT vs RULE"],
        md_rows)
    md += [
        "",
        "Two pass-through columns, because they answer different questions. The "
        "first counts every labelled violation the system applied; the second "
        "counts only those that executed at least one operation, and the gap "
        "between them is the silent no-op, where the instruction was accepted and "
        "then not carried out. The mean and the median executed tardiness are "
        "reported together because a handful of catastrophic schedules move the "
        "mean by hundreds of business hours while the median barely moves.",
        "",
    ]
    return T4_HEADERS, rows, md


def profile_md_row(system, mode, thinking, profile, rule_mean, rule_median=None):
    shares = profile["terminal_shares"]
    mean = profile["wwt_original_mean_bh"]
    median = profile["wwt_original_median_bh"]
    delta = None if (mean is None or rule_mean is None) else mean - rule_mean
    delta_med = None if (median is None or rule_median is None) else median - rule_median
    return [
        system, mode, thinking,
        rate(shares.get("applied_with_certificate")),
        rate(shares.get("applied_uncertified")),
        rate(shares.get("referred_to_human")),
        rate(shares.get("blocked_correctly")),
        rate(shares.get("blocked_falsely")),
        rate(shares.get("execution_failed")),
        rate(shares.get("unhandled")),
        rate(profile["violation_pass_through"]),
        rate(profile["violation_pass_through_nonempty"]),
        num(profile["certified_gap_median"], "{:.3f}"),
        rate(profile["warranted_outcome_rate"]),
        "-" if delta is None else "{:+.2f} bh".format(delta),
        "-" if delta_med is None else "{:+.2f} bh".format(delta_med),
    ]


def find_group(summary: dict, mode: str, thinking: str):
    for group in summary["groups"]:
        if not group["pooled"]:
            continue
        if group["mode"] == mode and thinking_label(group["thinking"]) == thinking:
            return group
    return None


# --------------------------------------------------------------------------- #
# T5: the ladder exhibit                                                       #
# --------------------------------------------------------------------------- #
T5_HEADERS = [
    "step", "step_meaning", "arm", "model", "mode", "scope", "items",
] + ["share_" + s for s in lr.PROFILE_STATES] + [
    "violation_pass_through", "violation_pass_through_nonempty",
    # The V4/V6 content rule, added beside the legacy columns rather than
    # replacing them (code/scripts/passthrough_rule.py).
    "violation_pass_through_strict", "violation_pass_through_strict_nonempty",
    "violation_pass_through_fault",
    "certified_gap_median", "warranted_outcome_rate",
    "wwt_original_mean_bh", "wwt_original_median_bh", "wwt_original_max_bh",
    "wwt_original_vs_rule_bh", "wwt_original_median_vs_rule_bh",
]


def build_t5(ladder: dict) -> tuple:
    anchors = ladder["anchors"]
    rule_mean = anchors["systems"]["RULE"]["full_suite"]["wwt_original_mean_bh"]
    rule_median = anchors["systems"]["RULE"]["full_suite"]["wwt_original_median_bh"]
    rows = []

    def add(step, meaning, spec, mode, scope, profile):
        shares = profile["terminal_shares"]
        mean = profile["wwt_original_mean_bh"]
        median = profile["wwt_original_median_bh"]
        delta = None if (mean is None or rule_mean is None) else mean - rule_mean
        delta_med = (None if (median is None or rule_median is None)
                     else median - rule_median)
        rows.append([
            step, meaning, "" if spec is None else spec["arm"],
            "" if spec is None else spec["label"], mode, scope, profile["n"],
        ] + [csv_rate(shares.get(s)) for s in lr.PROFILE_STATES] + [
            csv_rate(profile["violation_pass_through"]),
            csv_rate(profile["violation_pass_through_nonempty"]),
            csv_rate(profile["violation_pass_through_strict"]),
            csv_rate(profile["violation_pass_through_strict_nonempty"]),
            csv_rate(profile["violation_pass_through_fault"]),
            csv_num(profile["certified_gap_median"]),
            csv_rate(profile["warranted_outcome_rate"]),
            csv_num(mean, "{:.4f}"), csv_num(median, "{:.4f}"),
            csv_num(profile["wwt_original_max_bh"], "{:.4f}"),
            csv_num(delta, "{:.4f}"), csv_num(delta_med, "{:.4f}"),
        ])

    for scope in anchors["scopes"]:
        add(LADDER_STEPS[0][0], LADDER_STEPS[0][1], None, "-", scope,
            anchors["systems"]["RULE"][scope])
        add(LADDER_STEPS[1][0], LADDER_STEPS[1][1], None, "-", scope,
            anchors["systems"]["ORACLE"][scope])

    for spec in ARMS:
        entry = ladder["arms"].get(spec["dir"])
        if entry is None:
            continue
        for config, (step, meaning) in zip(CONFIGS, LADDER_STEPS[2:5]):
            for key, per_scope in sorted(entry["profiles_by_group"][config].items()):
                mode = key.split("/", 1)[0].strip()
                for scope in anchors["scopes"]:
                    add(step, meaning, spec, key, scope, per_scope[scope])
        for step, meaning in LADDER_STEPS[5:]:
            rows.append([step, meaning, spec["arm"], spec["label"], PENDING, "-", ""]
                        + [PENDING] * len(lr.PROFILE_STATES)
                        + [PENDING] * (len(T5_HEADERS) - 7
                                       - len(lr.PROFILE_STATES)))

    md = [
        "One ordered walk from the as-is configurations to the to-be ones on the "
        "same 2,000 instructions (guidance Section 5.1). RULE and ORACLE need no "
        "model call; the three guard rungs are replays over one logged "
        "translation per instruction. The two agent rungs are not yet measured "
        "and are printed as `{}` rather than left blank.".format(PENDING),
        "",
        "Read the increments in order: ORACLE over RULE is what instruction "
        "handling adds when a person does the translation perfectly; UNGUARDED "
        "over ORACLE is what the model loses against that ideal; G-FEAS is what "
        "the field's standard guard recovers; G-CERT is what certification adds "
        "on top.",
        "",
        "The `items` column differs by rung and is not a coverage defect. RULE "
        "and ORACLE are deterministic, so one pass over the 2,000 instructions is "
        "the whole measurement; the model rungs pool their sampling repeats, so "
        "they carry 2,000 x the arm's repeat count. Every rate is a share of its "
        "own denominator.",
        "",
    ]
    for spec in ARMS:
        entry = ladder["arms"].get(spec["dir"])
        if entry is None:
            continue
        keys = sorted(entry["profiles_by_group"]["G_CERT"])
        constrained = [k for k in keys if k.startswith("M_constrained")]
        if not constrained:
            continue
        key = constrained[0]
        md += ["### Ladder on {} ({})".format(spec["label"], key), ""]
        table = []
        for name, profile in (
            ("1. RULE/SOLVER", anchors["systems"]["RULE"]["full_suite"]),
            ("2. ORACLE", anchors["systems"]["ORACLE"]["full_suite"]),
            ("3. UNGUARDED", entry["profiles_by_group"]["UNGUARDED"][key]["full_suite"]),
            ("4. G-FEAS", entry["profiles_by_group"]["G_FEAS"][key]["full_suite"]),
            ("5. G-CERT", entry["profiles_by_group"]["G_CERT"][key]["full_suite"]),
        ):
            mean = profile["wwt_original_mean_bh"]
            median = profile["wwt_original_median_bh"]
            delta = None if mean is None else mean - rule_mean
            delta_med = None if median is None else median - rule_median
            table.append([
                name, profile["n"],
                rate(profile["terminal_shares"].get("applied_with_certificate")),
                rate(profile["terminal_shares"].get("applied_uncertified")),
                rate((profile["terminal_shares"].get("blocked_correctly") or 0)
                     + (profile["terminal_shares"].get("blocked_falsely") or 0)),
                rate(profile["violation_pass_through"]),
                rate(profile["violation_pass_through_nonempty"]),
                rate(profile["warranted_outcome_rate"]),
                num(profile["certified_gap_median"], "{:.3f}"),
                "-" if delta is None else "{:+.2f} bh".format(delta),
                "-" if delta_med is None else "{:+.2f} bh".format(delta_med),
            ])
        table.append(["6. SINGLE+G"] + [PENDING] * 10)
        table.append(["7. MULTI"] + [PENDING] * 10)
        md += md_table(
            ["step", "items", "applied+cert", "applied uncert", "blocked",
             "violation pass-through", "of which non-empty", "warranted",
             "cert gap median", "mean WWT vs RULE", "median WWT vs RULE"],
            table)
        md += [""]
    return T5_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# T6: the tau calibration exhibit                                              #
# --------------------------------------------------------------------------- #
T6_HEADERS = [
    "arm", "model", "mode", "thinking", "tau", "v3_items", "v3_block_rate",
    "v3_feas_pass", "v3_separated", "v3_separation_share", "v4_separated",
    "false_block_rate", "warranted_share", "in_accepted_e2_sweep",
    "operating_point_fb1pct", "operating_point_fb5pct",
    "schema_feas_false_block_floor",
]


def build_t6(results_root: Path, rec: lr.Reconciler) -> tuple:
    """Re-derive the tau curves for every arm with the accepted sweep's own code."""
    eval_dirs = [results_root / spec["dir"] for spec in ARMS]
    all_rows = []
    for path in eval_dirs:
        all_rows.extend(e2.load_arm(path)["rows"])
    groups = e2.group_rows(all_rows)

    accepted = {}
    curves_csv = results_root / "e2_tau_sweep" / "curves.csv"
    if curves_csv.exists():
        with open(curves_csv, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                accepted[(row["arm"], row["mode"], row["thinking"], row["tau"],
                          row["class"])] = row

    rows = []
    per_group = []
    for key, group_rows_ in groups.items():
        arm, mode, thinking = key
        classes = sorted({r["primary_class"] for r in group_rows_})
        curve = e2.group_curve(group_rows_, classes)
        ops = e2.operating_points(curve)
        spec = ARM_BY_LABEL[arm]
        benign_rows = [r for r in group_rows_
                       if r["primary_class"] == "benign" and not r["cert_infra"]]
        floor = (sum(1 for r in benign_rows if r["cert_terminal"] in e2.PRE_QUAL_BLOCKS)
                 / len(benign_rows)) if benign_rows else None
        covered = False
        for tau in e2.TAU_GRID:
            label = e2.tau_label(tau)
            point = curve["points"][label]
            sep3 = point["separation"].get("V3", {})
            sep4 = point["separation"].get("V4", {})
            block3 = point["blocks"].get("V3", {})
            key_csv = (arm, mode, e2.thinking_label(thinking), label, "V3")
            if key_csv in accepted:
                covered = True
                ref = accepted[key_csv]
                rec.check("T6", "{} {} tau={} V3 blocks reproduce the accepted "
                                "sweep".format(arm, mode, label),
                          int(ref["blocks"]), block3.get("blocked"))
                rec.check("T6", "{} {} tau={} V3 items reproduce the accepted "
                                "sweep".format(arm, mode, label),
                          int(ref["items"]), block3.get("n"))
                rec.check("T6", "{} {} tau={} V3 separated reproduces the accepted "
                                "sweep".format(arm, mode, label),
                          int(ref["v3_separated"]), sep3.get("separated"))
                rec.check("T6", "{} {} tau={} false-block rate reproduces the "
                                "accepted sweep".format(arm, mode, label),
                          float(ref["false_block_rate"]), point["false_block_rate"],
                          rtol=1e-6)
                rec.check("T6", "{} {} tau={} warranted share reproduces the "
                                "accepted sweep".format(arm, mode, label),
                          float(ref["warranted_share"]), point["warranted_share"],
                          rtol=1e-6)
            rows.append([
                arm, spec["label"], mode, e2.thinking_label(thinking), label,
                block3.get("n"), csv_rate(block3.get("rate")), sep3.get("feas_pass"),
                sep3.get("separated"), csv_rate(sep3.get("share")),
                sep4.get("separated"), csv_rate(point["false_block_rate"]),
                csv_rate(point["warranted_share"]),
                "yes" if key_csv in accepted else "no",
                ops["fb_le_1pct"]["tau_smallest"], ops["fb_le_5pct"]["tau_smallest"],
                csv_rate(floor),
            ])
        per_group.append({"arm": arm, "mode": mode, "thinking": thinking,
                          "curve": curve, "ops": ops, "floor": floor,
                          "covered": covered, "spec": spec})

    md = [
        "The certificate's tolerance tau enters the guard only as the final "
        "gap-vs-tau comparison, so the sweep is post-processing over the "
        "certificates already recorded: no replay and no model call. Every arm's "
        "curve is re-derived here with the accepted sweep's own functions, and "
        "every cell the accepted sweep already published is asserted equal to it.",
        "",
        "The reported operating point is `tau_smallest`, the tightest gate meeting "
        "the benign false-block budget (the frozen 'largest tau' rule degenerates "
        "because the false-block rate is non-increasing in tau; decisions.md, "
        "2026-08-12). The floor column is the share of benign twins blocked at "
        "the schema or feasibility stage, which no value of tau can move.",
        "",
    ]
    md += md_table(
        ["arm", "mode", "think", "V3 sep @0.05", "V3 sep @0.20", "V3 sep @0.50",
         "false blocks @0.20", "false-block floor", "tau at fb<=5%", "fb<=1% reachable",
         "in accepted E2 sweep"],
        [[g["arm"], g["mode"], e2.thinking_label(g["thinking"]),
          rate(g["curve"]["points"]["0.05"]["separation"].get("V3", {}).get("share")),
          rate(g["curve"]["points"]["0.20"]["separation"].get("V3", {}).get("share")),
          rate(g["curve"]["points"]["0.50"]["separation"].get("V3", {}).get("share")),
          rate(g["curve"]["points"]["0.20"]["false_block_rate"]),
          rate(g["floor"]),
          g["ops"]["fb_le_5pct"]["tau_smallest"],
          "no" if g["ops"]["fb_le_1pct"]["tau_smallest"] is None else
          str(g["ops"]["fb_le_1pct"]["tau_smallest"]),
          "yes" if g["covered"] else "no"]
         for g in per_group])
    md += [""]
    return T6_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# D1: the V3 separation breakdown (diagnostic input only)                      #
# --------------------------------------------------------------------------- #
D1_HEADERS = [
    "cut", "cut_value", "arm", "model", "mode", "thinking", "v3_items",
    "v3_feas_pass", "v3_separated", "v3_separation_share", "v3_cert_blocked",
    "gold_match_exact", "gold_match_semantic", "gold_match_exact_rate",
    "unseparated_applied_with_certificate", "unseparated_blocked_feas",
    "unseparated_blocked_schema", "unseparated_other",
]


def build_d1(results_root: Path) -> tuple:
    """V3 separation and gold-translation fidelity, by arm, register and family.

    Input for the pending translation-difference audit of the mini arm's low V3
    separation.  It reports the cuts and states nothing about the cause.
    """
    suite = {item["item_id"]: item for item in sg.load_suite()}
    rows = []
    summary_rows = []

    for spec in ARMS:
        eval_dir = results_root / spec["dir"]
        cert = {}
        for row in lr.read_jsonl(eval_dir / "verdicts_G_CERT.jsonl"):
            if row["primary_class"] != "V3" or row["mode"] != "M_constrained":
                continue
            cert[(row["mode"], row.get("thinking"), row.get("repeat"),
                  row["item_id"])] = row
        feas = {}
        for row in lr.read_jsonl(eval_dir / "verdicts_G_FEAS.jsonl"):
            key = (row["mode"], row.get("thinking"), row.get("repeat"), row["item_id"])
            if key in cert:
                feas[key] = row
        parsed = {}
        for rec_row in lr.read_jsonl(eval_dir / "proposals.jsonl"):
            extra = rec_row.get("extra") or {}
            key = (extra["mode"], extra.get("thinking"), extra.get("repeat"),
                   rec_row["instruction_id"])
            if key in cert:
                parsed[key] = rec_row.get("parsed_ops")

        buckets: dict = OrderedDict()
        for key, row in cert.items():
            item = suite[row["item_id"]]
            thinking = e2.thinking_label(key[1])
            for cut, value in (("all", "all"), ("register", item["register"]),
                               ("template", item["subclass"])):
                buckets.setdefault((cut, value, thinking), []).append(key)

        for (cut, value, thinking), keys in sorted(buckets.items()):
            n = len(keys)
            feas_pass = 0
            separated = 0
            cert_blocked = 0
            exact = semantic = 0
            unsep = Counter()
            for key in keys:
                crow, frow = cert[key], feas.get(key)
                passed = frow is not None and frow["terminal"] in (
                    "applied_with_certificate", "applied_uncertified")
                blocked = crow["terminal"] in ("blocked_schema", "blocked_feas",
                                               "blocked_qual")
                feas_pass += int(passed)
                cert_blocked += int(blocked)
                if passed and blocked:
                    separated += 1
                else:
                    unsep[crow["terminal"]] += 1
                kind = sg.match_kind(parsed.get(key), suite[crow["item_id"]]["gold_ops"])
                exact += int(kind == "exact")
                semantic += int(kind in ("exact", "semantic"))
            row_out = [
                cut, value, spec["arm"], spec["label"], "M_constrained", thinking, n,
                feas_pass, separated, csv_rate(separated / n if n else None),
                cert_blocked, exact, semantic, csv_rate(exact / n if n else None),
                unsep.get("applied_with_certificate", 0), unsep.get("blocked_feas", 0),
                unsep.get("blocked_schema", 0),
                sum(v for k, v in unsep.items()
                    if k not in ("applied_with_certificate", "blocked_feas",
                                 "blocked_schema")),
            ]
            rows.append(row_out)
            if cut in ("all", "register"):
                summary_rows.append((spec, cut, value, thinking, n, separated,
                                     exact, unsep))

    md = [
        "Diagnostic input for the pending translation-difference audit of the "
        "mini arm's V3 separation, which sits below both smaller open arms "
        "(decisions.md, 2026-08-12). Nothing here is a conclusion.",
        "",
        "V3 separation requires two things at once: the proposal must pass the "
        "feasibility guard, and the certificate must then refuse it. A proposal "
        "that never reproduces the damaging instruction is not separated either, "
        "so the gold-match column is reported beside the separation column: it "
        "says whether the arm translated the V3 instruction as the ground truth "
        "does, which is the quantity the audit needs.",
        "",
    ]
    md += md_table(
        ["arm", "cut", "value", "think", "V3 items", "separation", "gold match exact",
         "unseparated: accepted", "unseparated: feas-blocked"],
        [[spec["arm"], cut, value, thinking, n,
          rate(separated / n if n else None), rate(exact / n if n else None),
          unsep.get("applied_with_certificate", 0), unsep.get("blocked_feas", 0)]
         for spec, cut, value, thinking, n, separated, exact, unsep in summary_rows])
    md += [""]
    return D1_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# D2: what actually happened to each class (diagnostic)                        #
# --------------------------------------------------------------------------- #
D2_HEADERS = [
    "arm", "model", "mode", "thinking", "class", "items", "gcert_block_rate",
    "blocked_at_schema", "blocked_at_schema_share", "blocked_at_feas_or_qual",
    "declined_empty_proposal", "declined_empty_proposal_share",
    "refused_by_model", "refused_by_model_share",
    "applied_with_operations", "applied_with_operations_share",
    "handled_share_blocked_declined_or_refused",
]


def build_d2(results_root: Path) -> tuple:
    """Per class: blocked by the guard, declined by the model, or applied.

    A block rate alone cannot be read as guard recall, because the proposer has
    to produce the illegal operation before the guard can refuse it. A model that
    answers a dangling work-order id with an empty operation list has handled the
    instruction itself, correctly, and leaves the guard nothing to block; the
    block rate records that as a fall. This table separates the two dispositions.

    "Declined" means the guard accepted a legal, empty operation list, which is
    the only disposition in which the model itself refused. A wrong-shape
    completion also carries zero operations, but it is a block at the schema
    stage and is counted there, never as a decline.
    """
    applied_states = ("applied_with_certificate", "applied_uncertified")
    rows = []
    for spec in ARMS:
        buckets: dict = OrderedDict()
        for row in lr.read_jsonl(results_root / spec["dir"] / "verdicts_G_CERT.jsonl"):
            if row["infra"]:
                continue
            key = (row["mode"], e2.thinking_label(row.get("thinking")),
                   row["primary_class"])
            buckets.setdefault(key, []).append(row)
        for (mode, thinking, cls), items in sorted(buckets.items()):
            n = len(items)
            schema = sum(1 for r in items if r["terminal"] == "blocked_schema")
            later = sum(1 for r in items
                        if r["terminal"] in ("blocked_feas", "blocked_qual"))
            declined = sum(1 for r in items if r["terminal"] in applied_states
                           and (r.get("n_ops") or 0) == 0)
            # eval-2: a model-level API refusal is a fourth disposition — the
            # model ended the request before any document existed.  Distinct
            # from a decline, which is a legal EMPTY proposal the guard passed.
            refused = sum(1 for r in items if r["terminal"] == "model_refused")
            applied_ops = sum(1 for r in items if r["terminal"] in applied_states
                              and (r.get("n_ops") or 0) > 0)
            if schema + later + declined + refused + applied_ops != n:
                raise SystemExit(
                    "REFUSING TO RUN: {} {} {} {} does not partition into blocked, "
                    "declined, refused and applied ({} of {})".format(
                        spec["arm"], mode, thinking, cls,
                        schema + later + declined + refused + applied_ops, n))
            rows.append([
                spec["arm"], spec["label"], mode, thinking, cls, n,
                csv_rate((schema + later) / n if n else None), schema,
                csv_rate(schema / n if n else None), later, declined,
                csv_rate(declined / n if n else None), refused,
                csv_rate(refused / n if n else None), applied_ops,
                csv_rate(applied_ops / n if n else None),
                csv_rate((schema + later + declined + refused) / n if n else None),
            ])

    md = [
        "A block rate is a joint measurement: the proposer has to produce the "
        "illegal operation before the guard can refuse it. On the schema and "
        "feasibility classes the stronger arms decline to act instead, returning "
        "an empty operation list, which is correct handling and leaves the guard "
        "nothing to block. Reading a falling V1 or V2 block rate as falling guard "
        "recall would be wrong, and this table is what prevents that reading: the "
        "last column, block plus decline, is what the pair actually achieves.",
        "",
    ]
    v12 = [r for r in rows if r[2] == "M_constrained" and r[4] in ("V1", "V2")]
    md += md_table(
        ["arm", "class", "think", "items", "blocked by the guard",
         "declined (empty proposal)", "refused by the model",
         "applied with operations", "blocked, declined or refused"],
        [[r[0], r[4], r[3], r[5], rate(float(r[6]) if r[6] else None),
          rate(float(r[11]) if r[11] else None), rate(float(r[13]) if r[13] else None),
          rate(float(r[15]) if r[15] else None), rate(float(r[16]) if r[16] else None)]
         for r in sorted(v12, key=lambda r: (ARM_BY_LABEL[r[0]]["tier"], r[4], r[3]))])
    md += [""]
    return D2_HEADERS, rows, md


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-root", default=str(REPO_ROOT / "results"))
    ap.add_argument("--ladder", default=str(REPO_ROOT / "analysis" / "ladder"))
    ap.add_argument("--out", default=str(REPO_ROOT / "analysis"))
    ap.add_argument("--skip-d1", action="store_true",
                    help="skip the V3 breakdown (it reads every proposal log)")
    args = ap.parse_args()

    started = time.time()
    results_root = Path(args.results_root)
    ladder_dir = Path(args.ladder)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = sg.assert_inputs()

    reconciliation = ladder_dir / "reconciliation.json"
    if not reconciliation.exists():
        raise SystemExit(
            "REFUSING TO RUN: {} does not exist; run ladder_replay.py first, "
            "because its reconciliation is what certifies these tables against "
            "the accepted evaluations.".format(reconciliation))
    ladder_checks = json.loads(reconciliation.read_text())["counts"]
    if ladder_checks["failed"]:
        raise SystemExit(
            "REFUSING TO RUN: the ladder reconciliation records {failed} failed "
            "assertion(s). Fix or report those before building tables from the "
            "same artifacts.".format(**ladder_checks))
    ladder = json.loads((ladder_dir / "ladder_anchors.json").read_text())
    ladder_meta = json.loads((ladder_dir / "run_meta.json").read_text())

    summaries = load_summaries(results_root)

    provenance = [
        "generated {} by {} ({})".format(
            time.strftime("%Y-%m-%d %H:%M:%S %z"), Path(__file__).name, TABLES_VERSION),
        "dedup rule applied to the hosted raw logs before evaluation: {}".format(
            lr.DEDUP_RULE),
        "suite {} sha256 {}".format(sg.SUITE_PATH.name, inputs["suite_sha256"]),
        "adjustment schema sha256 {}".format(inputs["schema_sha256"]),
        "ladder anchors: {} (reconciliation {passed}/{total} passed)".format(
            ladder_dir, **ladder_checks),
    ]
    for spec in ARMS:
        path = results_root / spec["dir"] / "summary.json"
        provenance.append("{} sha256 {}".format(path, lr.sha256_file(path)))
    e2_curves = results_root / "e2_tau_sweep" / "curves.csv"
    if e2_curves.exists():
        provenance.append("{} sha256 {}".format(e2_curves, lr.sha256_file(e2_curves)))
    provenance.append(
        "rows are the accepted record; every overlapping cell is asserted equal to it")

    tables = Tables(out_dir, provenance)
    rec = lr.Reconciler()

    headers, rows, md = build_t1(summaries, rec)
    tables.write("T1_e1_main", "T1. E1 main table: block rate and false-block rate",
                 headers, rows, md)

    headers, rows, md = build_t2(summaries, rec)
    tables.write("T2_enforcement_ladder", "T2. The enforcement ladder", headers, rows, md)

    headers, rows, md = build_t3(summaries, rec)
    tables.write("T3_guard_value_curve",
                 "T3. Guard value against proposer capability", headers, rows, md)

    headers, rows, md = build_t4(ladder, summaries, rec)
    tables.write("T4_trustworthiness",
                 "T4. System-level trustworthiness profiles", headers, rows, md)

    headers, rows, md = build_t5(ladder)
    tables.write("T5_ladder", "T5. The as-is / to-be ladder", headers, rows, md)

    headers, rows, md = build_t6(results_root, rec)
    tables.write("T6_tau_calibration", "T6. Certificate tolerance calibration",
                 headers, rows, md)

    if not args.skip_d1:
        headers, rows, md = build_d1(results_root)
        tables.write("D1_v3_separation_breakdown",
                     "D1. V3 separation by arm, register and template family "
                     "(diagnostic)", headers, rows, md)

        headers, rows, md = build_d2(results_root)
        tables.write("D2_class_disposition",
                     "D2. Blocked, declined or applied, per class (diagnostic)",
                     headers, rows, md)

    meta = {
        "tables_version": TABLES_VERSION,
        "date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "wall_s": time.time() - started,
        "out_dir": str(out_dir),
        "ladder_run": ladder_meta,
        "ladder_reconciliation": ladder_checks,
        "table_reconciliation": rec.counts(),
        "tables": [{"name": n, "rows": r} for n, r in tables.written],
        "provenance": provenance,
    }
    (out_dir / "tables_meta.json").write_text(
        json.dumps(meta, indent=1, sort_keys=True) + "\n")
    (out_dir / "tables_reconciliation.json").write_text(
        json.dumps({"counts": rec.counts(), "checks": rec.checks}, indent=1,
                   sort_keys=True) + "\n")

    counts = rec.counts()
    print("tables written to {}:".format(out_dir))
    for name, n in tables.written:
        print("  {:<32s} {:>5d} rows".format(name, n))
    print("table assertions: {passed}/{total} passed, {failed} failed".format(**counts))
    for failure in rec.failures[:20]:
        print("  FAIL [{group}] {check}\n    expected {expected!r}\n    got      {got!r}"
              .format(**failure))
    print("done in {:.1f} s".format(time.time() - started))
    return 0 if rec.ok() else 2


if __name__ == "__main__":
    raise SystemExit(main())
