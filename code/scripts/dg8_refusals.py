#!/usr/bin/env python
"""DG8-C: the flagship's free-mode refusal wall, and what can be said about it.

In free-form mode the flagship proposer's own safety layer ends most requests
before any proposal exists: the manuscript reports \\eOneOpusRefusalFreeDefault
= 75.2% and \\eOneOpusRefusalFreeDisabled = 78.0% of rows
(manuscript/macros.tex:1293-1313, from analysis/D2_class_disposition.csv).  A
reviewer will ask what the model said when it refused.  The answer is that it
said nothing that was returned: the endpoint sends a ``stop_reason`` of
``refusal`` with no text block, so no refusal message exists to categorise.

This script (1) establishes that fact from the raw hosted log rather than
asserting it, (2) rules out the alternative explanation that the client dropped
the text, and (3) produces the categorisation that IS available: the refusal
share by injected class, by instruction register, by instance stratum, by
thinking setting and by enforcement mode, the per-item stability across the two
sampling repeats, and the billed completion tokens of a refused call.

Sources (read-only)
-------------------
* ``results/grid_e1_hosted_opus/proposals_raw.dedup.jsonl`` -- 16,000 rows, one
  per (mode, thinking, repeat, item_id), carrying ``outcome``, ``api_error``,
  ``finish_reason``, ``raw_output`` and ``usage``.
* ``code/suite/v0.2/suite.jsonl`` -- the frozen suite, for ``register`` (which
  the proposal log does not carry).
* ``analysis/D2_class_disposition.csv`` -- the published per-class refusal
  shares the self-check reproduces.
* ``code/l1guard/models.py`` -- the client's Anthropic response reader, quoted
  in the report so the "text was dropped" hypothesis can be dismissed by
  inspection.

Self-check (runs first; the script exits non-zero if it fails)
--------------------------------------------------------------
Every published ``refused_by_model`` count and share of
``analysis/D2_class_disposition.csv`` for the flagship's four (mode, thinking)
cells is recomputed from the raw hosted log and asserted equal.

Version: l1-dg8-refusals-1
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

VERSION = "l1-dg8-refusals-1"

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
SUITE = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"
RAW = RESULTS / "grid_e1_hosted_opus" / "proposals_raw.dedup.jsonl"

CLASSES = ["benign", "V1", "V2", "V3", "V4", "V5", "V6"]
REGISTERS = ["formal", "terse", "conversational"]
CELLS = [("M_free", "default"), ("M_free", "disabled"),
         ("M_constrained", "default"), ("M_constrained", "disabled")]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(a, b):
    return None if not b else a / b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-csv", default=str(ANALYSIS / "DG8_refusals.csv"))
    args = ap.parse_args()

    hashes = OrderedDict()
    for p in (RAW, SUITE, ANALYSIS / "D2_class_disposition.csv",
              ROOT / "code" / "l1guard" / "models.py"):
        hashes[str(p.relative_to(ROOT))] = sha256(p)

    # ---------------- the suite, for register ------------------------------ #
    register = {}
    with SUITE.open() as fh:
        for line in fh:
            r = json.loads(line)
            register[r["item_id"]] = r.get("register")

    # ---------------- the raw hosted log ----------------------------------- #
    rows = []
    with RAW.open() as fh:
        for line in fh:
            r = json.loads(line)
            rows.append(r)

    refusals = [r for r in rows if r.get("outcome") == "refusal"]

    # ---------------- (1) is there any refusal text at all? ---------------- #
    api_error_values = Counter(r.get("api_error") for r in refusals)
    finish_values = Counter(r.get("finish_reason") for r in refusals)
    raw_none = sum(1 for r in refusals if r.get("raw_output") is None)
    raw_some = [r for r in refusals if r.get("raw_output") is not None]
    # A refusal whose text is not None: is it a refusal MESSAGE, or a truncated
    # proposal?  A refusal message would not start with the proposal's JSON.
    raw_some_starts_json = sum(1 for r in raw_some
                               if (r["raw_output"] or "").lstrip().startswith("{"))
    # Ruling out the "the client dropped the text" hypothesis by inspection.
    models_py = (ROOT / "code" / "l1guard" / "models.py").read_text().split("\n")
    extract_line = next(i + 1 for i, ln in enumerate(models_py)
                        if 'block.get("type") == "text"' in ln)
    branch_line = next(i + 1 for i, ln in enumerate(models_py)
                       if 'if finish == "refusal":' in ln)
    passes_text = any('text=text,' in ln for ln in models_py[branch_line:branch_line + 6])

    # ---------------- (2) the categorisation that IS possible -------------- #
    by_cell = OrderedDict()
    for cell in CELLS:
        sel = [r for r in rows if (r["mode"], r.get("thinking")) == cell]
        ref = [r for r in sel if r.get("outcome") == "refusal"]
        by_cell[cell] = {"rows": len(sel), "refused": len(ref),
                         "share": pct(len(ref), len(sel))}

    def breakdown(field_fn, values, cell):
        sel = [r for r in rows if (r["mode"], r.get("thinking")) == cell]
        out = OrderedDict()
        for v in values:
            grp = [r for r in sel if field_fn(r) == v]
            ref = sum(1 for r in grp if r.get("outcome") == "refusal")
            out[v] = {"rows": len(grp), "refused": ref, "share": pct(ref, len(grp))}
        return out

    by_class = OrderedDict(
        (cell, breakdown(lambda r: r["primary_class"], CLASSES, cell))
        for cell in CELLS)
    by_register = OrderedDict(
        (cell, breakdown(lambda r: register.get(r["item_id"]), REGISTERS, cell))
        for cell in CELLS)
    strata = sorted({r["stratum"] for r in rows})
    by_stratum = OrderedDict(
        (cell, breakdown(lambda r: r["stratum"], strata, cell)) for cell in CELLS)

    # ---------------- (3) per-item repeat stability ------------------------ #
    stability = OrderedDict()
    for cell in CELLS:
        per_item = {}
        for r in rows:
            if (r["mode"], r.get("thinking")) != cell:
                continue
            per_item.setdefault(r["item_id"], {})[r["repeat"]] = (
                r.get("outcome") == "refusal")
        both = neither = split = incomplete = 0
        split_items = []
        for iid, reps in per_item.items():
            if len(reps) != 2:
                incomplete += 1
                continue
            vals = list(reps.values())
            if all(vals):
                both += 1
            elif not any(vals):
                neither += 1
            else:
                split += 1
                split_items.append(iid)
        stability[cell] = {
            "items": len(per_item), "refused_in_both": both,
            "refused_in_neither": neither, "refused_in_exactly_one": split,
            "items_without_two_repeats": incomplete,
            "share_deterministic": pct(both + neither, len(per_item)),
            "split_by_class": dict(Counter(
                next((r["primary_class"] for r in rows if r["item_id"] == i), None)
                for i in split_items)) if split_items else {},
        }

    # ---------------- (3b) the counterfactual: schema enforcement ---------- #
    constrained_refusals = [
        {"item_id": r["item_id"], "thinking": r.get("thinking"),
         "repeat": r.get("repeat"), "primary_class": r["primary_class"],
         "subclass": r.get("subclass"), "stratum": r["stratum"],
         "register": register.get(r["item_id"]),
         "instruction": r.get("instruction"),
         "completion_tokens": (r.get("usage") or {}).get("completion_tokens")}
        for r in refusals if r["mode"] == "M_constrained"]

    # ---------------- (4) billed tokens on a refusal ----------------------- #
    def token_stats(sel, field):
        vals = [(r.get("usage") or {}).get(field) for r in sel]
        vals = [v for v in vals if v is not None]
        if not vals:
            return {}
        return {"n": len(vals), "min": min(vals), "median": statistics.median(vals),
                "mean": sum(vals) / len(vals), "max": max(vals),
                "total": sum(vals)}

    ok_rows = [r for r in rows if r.get("outcome") == "ok"]
    tokens = {
        "refusal_completion_tokens": token_stats(refusals, "completion_tokens"),
        "refusal_prompt_tokens": token_stats(refusals, "prompt_tokens"),
        "ok_completion_tokens": token_stats(ok_rows, "completion_tokens"),
        "refusal_completion_token_value_counts": dict(Counter(
            (r.get("usage") or {}).get("completion_tokens")
            for r in refusals).most_common(8)),
    }

    # ---------------- self-check against D2 -------------------------------- #
    d2 = ANALYSIS / "D2_class_disposition.csv"
    with d2.open() as fh:
        body = [ln for ln in fh if not ln.startswith("#")]
    checks = []
    for rec in csv.DictReader(body):
        if rec["arm"] != "opus":
            continue
        cell = (rec["mode"], rec["thinking"])
        cls = rec["class"]
        if cell not in by_class or cls not in by_class[cell]:
            continue
        mine = by_class[cell][cls]
        checks.append(("D2 {} {} {} refused_by_model".format(*cell, cls),
                       float(rec["refused_by_model"]), float(mine["refused"])))
        checks.append(("D2 {} {} {} items".format(*cell, cls),
                       float(rec["items"]), float(mine["rows"])))
        checks.append(("D2 {} {} {} refused_by_model_share".format(*cell, cls),
                       float(rec["refused_by_model_share"]),
                       float(mine["share"] or 0.0)))
    failures = [(n, w, g) for n, w, g in checks if abs(w - g) > 5e-6]
    print("SELF-CHECK  {} published D2 cells for the flagship recomputed from "
          "the raw hosted log; mismatches = {}".format(len(checks), len(failures)),
          file=sys.stderr)
    if failures:
        for f in failures[:10]:
            print("  MISMATCH {}: published {} vs recomputed {}".format(*f),
                  file=sys.stderr)
        return 1

    # ---------------- write the CSV ---------------------------------------- #
    out = Path(args.out_csv)
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    with out.open("w", newline="") as fh:
        fh.write("# DG8-C. The flagship's vendor refusal wall: what exists in the "
                 "log and what can be categorised\n")
        fh.write("# generated {} by code/scripts/dg8_refusals.py ({})\n".format(
            stamp, VERSION))
        fh.write("# self-check: {} published per-class refusal cells of "
                 "analysis/D2_class_disposition.csv (arm=opus) recomputed from "
                 "the raw hosted log, {} mismatches\n".format(
                     len(checks), len(failures)))
        for path, h in hashes.items():
            fh.write("# {} sha256 {}\n".format(path, h))
        w = csv.writer(fh)
        w.writerow(["section", "cell", "key", "rows", "refused", "share", "note"])

        w.writerow(["log_shape", "-", "rows_total", len(rows), len(refusals),
                    "{:.6f}".format(len(refusals) / len(rows)), ""])
        for v, k in api_error_values.most_common():
            w.writerow(["refusal_api_error_value", "-", repr(v), "", k, "",
                        "the only value recorded on a refusal row"
                        if len(api_error_values) == 1 else ""])
        for v, k in finish_values.most_common():
            w.writerow(["refusal_finish_reason_value", "-", repr(v), "", k, "", ""])
        w.writerow(["refusal_text", "-", "raw_output is None", len(refusals),
                    raw_none, "{:.6f}".format(raw_none / len(refusals)),
                    "no text block was returned, so there is no refusal message "
                    "to categorise"])
        w.writerow(["refusal_text", "-", "raw_output is not None", len(refusals),
                    len(raw_some), "{:.6f}".format(len(raw_some) / len(refusals)),
                    "{} of them begin with the proposal's own JSON, i.e. they are "
                    "generations cut off mid-proposal, not refusal messages"
                    .format(raw_some_starts_json)])
        w.writerow(["client_not_dropping_text", "-",
                    "code/l1guard/models.py", "", "", "",
                    "the first text block is extracted at line {} and the "
                    "stop_reason branch is taken at line {}, passing text=text: "
                    "{}".format(extract_line, branch_line, passes_text)])

        for cell, v in by_cell.items():
            w.writerow(["refusal_by_cell", "{} / {}".format(*cell), "all classes",
                        v["rows"], v["refused"], "{:.6f}".format(v["share"]), ""])
        for cell, d in by_class.items():
            for cls, v in d.items():
                w.writerow(["refusal_by_class", "{} / {}".format(*cell), cls,
                            v["rows"], v["refused"],
                            "" if v["share"] is None else "{:.6f}".format(v["share"]),
                            ""])
        for cell, d in by_register.items():
            for reg, v in d.items():
                w.writerow(["refusal_by_register", "{} / {}".format(*cell), reg,
                            v["rows"], v["refused"],
                            "" if v["share"] is None else "{:.6f}".format(v["share"]),
                            ""])
        for cell, d in by_stratum.items():
            for st, v in d.items():
                w.writerow(["refusal_by_stratum", "{} / {}".format(*cell), st,
                            v["rows"], v["refused"],
                            "" if v["share"] is None else "{:.6f}".format(v["share"]),
                            ""])
        for cell, v in stability.items():
            w.writerow(["repeat_stability", "{} / {}".format(*cell),
                        "refused in both repeats", v["items"],
                        v["refused_in_both"], "", ""])
            w.writerow(["repeat_stability", "{} / {}".format(*cell),
                        "refused in neither repeat", v["items"],
                        v["refused_in_neither"], "", ""])
            w.writerow(["repeat_stability", "{} / {}".format(*cell),
                        "refused in exactly one repeat", v["items"],
                        v["refused_in_exactly_one"],
                        "{:.6f}".format(v["refused_in_exactly_one"] / v["items"]),
                        "split items by class: {}".format(v["split_by_class"])])
        w.writerow(["counterfactual_schema_enforcement", "M_constrained (both "
                    "thinking settings, both repeats)", "refusals",
                    sum(by_cell[c]["rows"] for c in CELLS
                        if c[0] == "M_constrained"),
                    len(constrained_refusals),
                    "{:.6f}".format(len(constrained_refusals)
                                    / sum(by_cell[c]["rows"] for c in CELLS
                                          if c[0] == "M_constrained")),
                    "distinct items refused: {}".format(
                        sorted({d["item_id"] for d in constrained_refusals}))])
        for d in constrained_refusals:
            w.writerow(["counterfactual_refusal_row",
                        "{} / repeat {}".format(d["thinking"], d["repeat"]),
                        d["item_id"], "", "", "",
                        "class {} subclass {} register {} stratum {} "
                        "completion_tokens {} instruction {!r}".format(
                            d["primary_class"], d["subclass"], d["register"],
                            d["stratum"], d["completion_tokens"],
                            d["instruction"])])
        for k, v in tokens.items():
            w.writerow(["tokens", "-", k, "", "", "", json.dumps(v)])

    report = {
        "version": VERSION,
        "self_check": {"d2_cells_checked": len(checks), "mismatches": len(failures)},
        "rows_total": len(rows), "refusals_total": len(refusals),
        "refusal_api_error_values": {repr(k): v for k, v in api_error_values.items()},
        "refusal_finish_reason_values": {repr(k): v for k, v in finish_values.items()},
        "raw_output_none": raw_none, "raw_output_present": len(raw_some),
        "raw_output_present_starting_with_json": raw_some_starts_json,
        "models_py_text_extracted_at_line": extract_line,
        "models_py_refusal_branch_at_line": branch_line,
        "models_py_refusal_branch_passes_text": passes_text,
        "by_cell": {"{}/{}".format(*k): v for k, v in by_cell.items()},
        "by_class": {"{}/{}".format(*k): v for k, v in by_class.items()},
        "by_register": {"{}/{}".format(*k): v for k, v in by_register.items()},
        "by_stratum": {"{}/{}".format(*k): v for k, v in by_stratum.items()},
        "repeat_stability": {"{}/{}".format(*k): v for k, v in stability.items()},
        "counterfactual_schema_enforcement": {
            "constrained_rows": sum(by_cell[c]["rows"] for c in CELLS
                                    if c[0] == "M_constrained"),
            "constrained_refusals": len(constrained_refusals),
            "distinct_items": sorted({d["item_id"] for d in constrained_refusals}),
            "rows": constrained_refusals},
        "tokens": tokens,
    }
    print(json.dumps(report, indent=1, default=str))
    print("wrote {}".format(out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
