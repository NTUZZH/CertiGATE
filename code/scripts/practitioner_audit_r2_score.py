#!/usr/bin/env python
"""Practitioner audit under protocol v1.2: scoring the returned workbooks.

INPUT
-----
One folder holding the five returned workbooks of each stage, renamed by the
author to

    Stage_A_Workbook_R<n>.xlsx    Stage_B_Workbook_R<n>.xlsx    (n = 1 .. 5)

where ``R<n>`` is the panel member's number.  The panel's own file names are
not read.  The case material comes from the pack
(``results/practitioner_audit_r2``): ``label_map.csv`` maps the neutral labels
C01..C30 to case ids and ``draw.csv`` carries each case's class, register,
stratum, suite disposition under v1.2 and the guard's actual disposition.

OUTPUT (``--out``, default ``results/practitioner_audit_r2``)
--------------------------------------------------------------
``cases.csv``     one row per case, case-level and de-identified, in the format
                  ``Case,class,register,stratum,disposition,apply,reject,refer,
                  realism,fidelity,clarity,action``: the suite disposition, the
                  number of panel members choosing each disposition, and the
                  number rating each scale positive (3 or 4).  ``clarity`` is
                  Stage B's "understandable", ``action`` its "actionable".
``scores.json``   every measure below, with its interval.
``scores.md``     the same measures as tables.

MEASURES (decision rules fixed before the draw)
-----------------------------------------------
* pooled positive shares of realism, fidelity, clarity and action, with 95%
  percentile intervals from a case-cluster bootstrap (B = 20,000, seed
  20261104; the same resample indices for every measure of one case set);
* the same shares per class and per register;
* disposition counts, the share of ratings that equal the suite disposition
  (and, for cases whose suite disposition is refer, the share that withhold
  application), the share that equal the guard's actual disposition;
* Fleiss' kappa on the three dispositions, with its bootstrap interval;
* four-of-five counts: cases with at least four positive ratings per scale,
  cases with a panel disposition (four or more members agree), and cases where
  four or more members choose the suite disposition.

Synthetic workbooks (``--make-synthetic DIR``) carry the keyword
``SYNTHETIC TEST DATA`` in their document properties and a banner on the
Instructions sheet.  The scorer refuses to write synthetic scores into the
default output folder, so a synthetic ``cases.csv`` can never sit where the
real one goes.

Version: l1-audit-score-v12-1.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent

VERSION = "l1-audit-score-v12-1"
SEED = 20261104
B_BOOT = 20000
N_PANEL = 5
FOUR_OF_FIVE = 4
PACK_DIR = ROOT / "results" / "practitioner_audit_r2"
PANEL_DIR = ROOT / "participant_files" / "audit_r2"
DEFAULT_OUT = PACK_DIR
SYNTHETIC_KEYWORD = "SYNTHETIC TEST DATA"
FILE_RE = re.compile(r"^Stage_([AB])_Workbook_(R[1-9])\.xlsx$")
DISPOSITIONS = ("apply", "reject", "refer")
CLASSES = ("benign", "V3", "V4", "V5", "V6")
REGISTERS = ("formal", "terse", "conversational")
STRATUM_NAME = {"c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
                "c10_replay_400": "Buildings"}
STAGE_COLUMNS = {
    "A": OrderedDict([("realism", "Realism (1-4)"), ("disposition", "Disposition"),
                      ("fidelity", "Fidelity (1-4)"), ("comment_a", "Comment")]),
    "B": OrderedDict([("clarity", "Understandable (1-4)"), ("action", "Actionable (1-4)"),
                      ("comment_b", "Comment")]),
}
SCALES = ("realism", "fidelity", "clarity", "action")
CASES_HEADER = ["Case", "class", "register", "stratum", "disposition", "apply", "reject",
                "refer", "realism", "fidelity", "clarity", "action"]


# --------------------------------------------------------------------------- #
# Reading                                                                      #
# --------------------------------------------------------------------------- #
def read_pack(pack_dir: Path) -> tuple:
    with open(pack_dir / "label_map.csv", newline="") as fh:
        labels = OrderedDict((r["label"], r["case_id"]) for r in csv.DictReader(fh))
    with open(pack_dir / "draw.csv", newline="") as fh:
        draw = OrderedDict((r["case_id"], r) for r in csv.DictReader(fh))
    if len(labels) != len(draw) or set(labels.values()) != set(draw):
        raise SystemExit("label_map.csv and draw.csv describe different cases")
    return labels, draw


def is_synthetic(wb) -> bool:
    return SYNTHETIC_KEYWORD in str(wb.properties.keywords or "")


def read_workbook(path: Path, stage: str, labels) -> tuple:
    """``({label: {field: value}}, synthetic)`` for one returned workbook."""
    from openpyxl import load_workbook

    wb = load_workbook(path, data_only=True)
    if "Cases" not in wb.sheetnames:
        raise SystemExit("{}: no sheet named 'Cases'".format(path.name))
    ws = wb["Cases"]
    header = [c.value for c in ws[1]]
    col = {}
    for key, name in list(STAGE_COLUMNS[stage].items()) + [("label", "Case")]:
        if name not in header:
            raise SystemExit("{}: column '{}' is missing".format(path.name, name))
        col[key] = header.index(name)
    out = OrderedDict()
    for row in ws.iter_rows(min_row=2, values_only=True):
        lab = row[col["label"]]
        if lab is None or str(lab).strip() == "":
            continue
        lab = str(lab).strip()
        if lab not in labels:
            raise SystemExit("{}: unknown case label {!r}".format(path.name, lab))
        if lab in out:
            raise SystemExit("{}: case {} appears twice".format(path.name, lab))
        rec = {}
        for key in STAGE_COLUMNS[stage]:
            v = row[col[key]]
            if key.startswith("comment"):
                rec[key] = "" if v is None else str(v)
            elif key == "disposition":
                rec[key] = None if v is None else str(v).strip().lower()
            else:
                rec[key] = None if v is None else _as_int(v)
        out[lab] = rec
    return out, is_synthetic(wb)


def _as_int(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "invalid:{}".format(v)
    return int(f) if f == int(f) else "invalid:{}".format(v)


def collect(in_dir: Path, labels, allow_missing: bool = False) -> tuple:
    """Return ``(ratings[rater][label] -> merged record, raters, synthetic)``."""
    files = {}
    for p in sorted(in_dir.iterdir()):
        m = FILE_RE.match(p.name)
        if m:
            files[(m.group(1), m.group(2))] = p
    raters = sorted({r for _, r in files})
    for stage in "AB":
        have = sorted(r for s, r in files if s == stage)
        if have != raters:
            raise SystemExit("stage {} workbooks for {} do not match the raters {}".format(
                stage, have, raters))
    if len(raters) != N_PANEL:
        raise SystemExit("expected {} panel members, found {}: {}".format(
            N_PANEL, len(raters), raters))
    ratings, synthetic, problems = OrderedDict(), False, []
    for r in raters:
        merged = OrderedDict((lab, {}) for lab in labels)
        for stage in "AB":
            recs, syn = read_workbook(files[(stage, r)], stage, labels)
            synthetic = synthetic or syn
            for lab in labels:
                rec = recs.get(lab)
                if rec is None:
                    problems.append("{} stage {} has no row for {}".format(r, stage, lab))
                    rec = {k: None for k in STAGE_COLUMNS[stage]}
                merged[lab].update(rec)
        for lab, rec in merged.items():
            for k in SCALES:
                v = rec.get(k)
                if v is None:
                    problems.append("{} {}: {} is blank".format(r, lab, k))
                elif v not in (1, 2, 3, 4):
                    problems.append("{} {}: {} = {!r} is not 1-4".format(r, lab, k, v))
                    rec[k] = None
            d = rec.get("disposition")
            if d is None:
                problems.append("{} {}: disposition is blank".format(r, lab))
            elif d not in DISPOSITIONS:
                problems.append("{} {}: disposition {!r} is not apply/reject/refer".format(
                    r, lab, d))
                rec["disposition"] = None
        ratings[r] = merged
    if problems and not allow_missing:
        raise SystemExit("incomplete or invalid ratings:\n  " + "\n  ".join(problems[:40]))
    return ratings, raters, synthetic, problems


# --------------------------------------------------------------------------- #
# Measures                                                                     #
# --------------------------------------------------------------------------- #
def fleiss_kappa(counts: np.ndarray) -> float:
    """Fleiss' kappa for an (N subjects x k categories) matrix of rater counts.

    Every subject must have the same number of ratings n >= 2.  Returns NaN
    when the expected agreement is 1 (every rating in one category).
    """
    counts = np.asarray(counts, dtype=float)
    n = counts.sum(axis=1)
    if counts.shape[0] == 0 or not np.allclose(n, n[0]) or n[0] < 2:
        raise ValueError("Fleiss' kappa needs the same number (>= 2) of ratings per subject")
    n = n[0]
    p_i = (np.square(counts).sum(axis=1) - n) / (n * (n - 1))
    p_bar = p_i.mean()
    p_j = counts.sum(axis=0) / counts.sum()
    p_e = float(np.square(p_j).sum())
    if p_e >= 1.0 - 1e-12:
        return float("nan")
    return float((p_bar - p_e) / (1.0 - p_e))


def _fleiss_boot(counts: np.ndarray, idx: np.ndarray) -> np.ndarray:
    c = counts[idx]  # (B, N, k)
    n = float(counts.sum(axis=1)[0])
    p_i = (np.square(c).sum(axis=2) - n) / (n * (n - 1))
    p_bar = p_i.mean(axis=1)
    p_j = c.sum(axis=1) / c.sum(axis=(1, 2))[:, None]
    p_e = np.square(p_j).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        k = (p_bar - p_e) / (1.0 - p_e)
    k[p_e >= 1.0 - 1e-12] = np.nan
    return k


def boot_indices(n_cases: int, key: int) -> np.ndarray:
    rng = np.random.default_rng([SEED, key])
    return rng.integers(0, n_cases, size=(B_BOOT, n_cases))


def interval(values: np.ndarray) -> tuple:
    v = values[~np.isnan(values)]
    if v.size == 0:
        return (None, None)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return (float(lo), float(hi))


def share_stat(num: np.ndarray, den: np.ndarray, idx: np.ndarray) -> OrderedDict:
    """A ratio of sums over cases, with its case-cluster bootstrap interval."""
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    total = den.sum()
    value = float(num.sum() / total) if total > 0 else None
    if total > 0:
        bn, bd = num[idx].sum(axis=1), den[idx].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            boot = np.where(bd > 0, bn / bd, np.nan)
        lo, hi = interval(boot)
    else:
        lo = hi = None
    return OrderedDict(value=value, lo=lo, hi=hi, num=int(num.sum()), den=int(total))


def case_table(labels, draw, ratings, raters) -> list:
    """One record per case in draw order, with counts over the panel."""
    by_case = {cid: lab for lab, cid in labels.items()}
    rows = []
    for cid, d in draw.items():
        lab = by_case[cid]
        recs = [ratings[r][lab] for r in raters]
        disp = Counter(x.get("disposition") for x in recs if x.get("disposition"))
        pos = {k: sum(1 for x in recs if x.get(k) in (3, 4)) for k in SCALES}
        rated = {k: sum(1 for x in recs if x.get(k) in (1, 2, 3, 4)) for k in SCALES}
        rows.append(OrderedDict(
            case=cid, label=lab, cls=d["class"], register=d["register"],
            stratum=STRATUM_NAME.get(d["stratum"], d["stratum"]),
            suite=d["suite_disposition_v12"], guard=d["guard_disposition"],
            counts={k: disp.get(k, 0) for k in DISPOSITIONS},
            n_disp=sum(disp.values()), pos=pos, rated=rated))
    return rows


def measures(rows: list) -> OrderedDict:
    out = OrderedDict()
    n = len(rows)
    idx_all = boot_indices(n, 0)

    def block(sub_rows, idx):
        b = OrderedDict(n_cases=len(sub_rows))
        for k in SCALES:
            b[k] = share_stat([r["pos"][k] for r in sub_rows],
                              [r["rated"][k] for r in sub_rows], idx)
        den = [r["n_disp"] for r in sub_rows]
        for dname in DISPOSITIONS:
            b["share_" + dname] = share_stat([r["counts"][dname] for r in sub_rows], den, idx)
        b["agree_suite"] = share_stat([r["counts"][r["suite"]] for r in sub_rows], den, idx)
        b["agree_guard"] = share_stat([r["counts"][r["guard"]] for r in sub_rows], den, idx)
        if any(r["suite"] == "refer" for r in sub_rows):
            # Cases whose suite disposition is apply enter with zero weight.
            num = [(r["counts"]["reject"] + r["counts"]["refer"]) if r["suite"] == "refer"
                   else 0 for r in sub_rows]
            dd = [r["n_disp"] if r["suite"] == "refer" else 0 for r in sub_rows]
            b["withhold_when_refer"] = share_stat(num, dd, idx)
        else:
            b["withhold_when_refer"] = None
        b["four_of_five"] = OrderedDict(
            (k, sum(1 for r in sub_rows if r["pos"][k] >= FOUR_OF_FIVE)) for k in SCALES)
        b["four_of_five"]["panel_disposition"] = sum(
            1 for r in sub_rows if max(r["counts"].values()) >= FOUR_OF_FIVE)
        b["four_of_five"]["suite_disposition"] = sum(
            1 for r in sub_rows if r["counts"][r["suite"]] >= FOUR_OF_FIVE)
        b["four_of_five"]["guard_disposition"] = sum(
            1 for r in sub_rows if r["counts"][r["guard"]] >= FOUR_OF_FIVE)
        return b

    out["pooled"] = block(rows, idx_all)
    counts = np.array([[r["counts"][d] for d in DISPOSITIONS] for r in rows], dtype=float)
    complete = all(r["n_disp"] == N_PANEL for r in rows)
    if complete:
        k = fleiss_kappa(counts)
        lo, hi = interval(_fleiss_boot(counts, idx_all))
        out["fleiss_kappa"] = OrderedDict(value=None if np.isnan(k) else k, lo=lo, hi=hi,
                                          categories=list(DISPOSITIONS), n_cases=len(rows),
                                          n_raters=N_PANEL)
    else:
        out["fleiss_kappa"] = OrderedDict(value=None, note="incomplete dispositions")
    out["by_class"] = OrderedDict()
    for i, cls in enumerate(CLASSES, start=1):
        sub = [r for r in rows if r["cls"] == cls]
        if sub:
            out["by_class"][cls] = block(sub, boot_indices(len(sub), 100 + i))
    out["by_register"] = OrderedDict()
    for i, reg in enumerate(REGISTERS, start=1):
        sub = [r for r in rows if r["register"] == reg]
        if sub:
            out["by_register"][reg] = block(sub, boot_indices(len(sub), 200 + i))
    return out


# --------------------------------------------------------------------------- #
# Writing                                                                      #
# --------------------------------------------------------------------------- #
def cases_csv(rows: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CASES_HEADER)
    for r in rows:
        w.writerow([r["case"], r["cls"], r["register"], r["stratum"], r["suite"],
                    r["counts"]["apply"], r["counts"]["reject"], r["counts"]["refer"],
                    r["pos"]["realism"], r["pos"]["fidelity"], r["pos"]["clarity"],
                    r["pos"]["action"]])
    return buf.getvalue()


def _pct(s) -> str:
    if s is None or s.get("value") is None:
        return "n/a"
    if s.get("lo") is None:
        return "{:.1f}%".format(100 * s["value"])
    return "{:.1f}% [{:.1f}, {:.1f}]".format(100 * s["value"], 100 * s["lo"], 100 * s["hi"])


def scores_md(m: OrderedDict, synthetic: bool, n_cases: int) -> str:
    L = []
    A = L.append
    if synthetic:
        A("> SYNTHETIC TEST DATA. These numbers come from generated workbooks and are not "
          "panel ratings.")
        A("")
    A("# Practitioner audit under protocol v1.2: scores")
    A("")
    A("{} cases, {} panel members. A rating of 3 or 4 is positive. Intervals are 95% "
      "case-cluster bootstrap percentiles (B = {:,}, seed {}).".format(
          n_cases, N_PANEL, B_BOOT, SEED))
    A("")
    k = m["fleiss_kappa"]
    if k.get("value") is not None:
        A("Fleiss' kappa on dispositions (apply, reject, refer): {:.3f} [{:.3f}, {:.3f}].".format(
            k["value"], k["lo"], k["hi"]))
    else:
        A("Fleiss' kappa on dispositions: not defined ({}).".format(k.get("note", "no variation")))
    A("")
    head = ("| Set | n | Realism | Fidelity | Understandable | Actionable | Agree with suite | "
            "Withhold when refer | Agree with guard |")
    sep = "|---|---|---|---|---|---|---|---|---|"
    A("## Positive shares and disposition agreement")
    A("")
    A(head)
    A(sep)

    def line(name, b):
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            name, b["n_cases"], _pct(b["realism"]), _pct(b["fidelity"]), _pct(b["clarity"]),
            _pct(b["action"]), _pct(b["agree_suite"]), _pct(b["withhold_when_refer"]),
            _pct(b["agree_guard"])))

    line("All", m["pooled"])
    for cls, b in m["by_class"].items():
        line(cls, b)
    for reg, b in m["by_register"].items():
        line(reg, b)
    A("")
    A("## Dispositions chosen")
    A("")
    A("| Set | apply | reject | refer |")
    A("|---|---|---|---|")
    for name, b in [("All", m["pooled"])] + list(m["by_class"].items()):
        A("| {} | {} | {} | {} |".format(name, _pct(b["share_apply"]), _pct(b["share_reject"]),
                                         _pct(b["share_refer"])))
    A("")
    A("## Four-of-five counts (cases)")
    A("")
    A("| Set | n | Realism | Fidelity | Understandable | Actionable | Panel disposition | "
      "Suite disposition | Guard disposition |")
    A("|---|---|---|---|---|---|---|---|---|")
    for name, b in [("All", m["pooled"])] + list(m["by_class"].items()) + \
            list(m["by_register"].items()):
        f = b["four_of_five"]
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            name, b["n_cases"], f["realism"], f["fidelity"], f["clarity"], f["action"],
            f["panel_disposition"], f["suite_disposition"], f["guard_disposition"]))
    A("")
    return "\n".join(L) + "\n"


def score(in_dir: Path, out_dir: Path, pack_dir: Path = PACK_DIR,
          allow_missing: bool = False, quiet: bool = False) -> dict:
    labels, draw = read_pack(pack_dir)
    ratings, raters, synthetic, problems = collect(in_dir, labels, allow_missing)
    if synthetic and out_dir.resolve() == DEFAULT_OUT.resolve():
        raise SystemExit("synthetic workbooks: refusing to write into {}; pass --out "
                         "elsewhere".format(DEFAULT_OUT))
    rows = case_table(labels, draw, ratings, raters)
    m = measures(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cases.csv").write_text(cases_csv(rows))
    payload = OrderedDict(version=VERSION, synthetic=synthetic, seed=SEED, B=B_BOOT,
                          n_cases=len(rows), raters=raters, problems=problems, measures=m)
    (out_dir / "scores.json").write_text(json.dumps(payload, indent=1) + "\n")
    (out_dir / "scores.md").write_text(scores_md(m, synthetic, len(rows)))
    if synthetic:
        (out_dir / "SYNTHETIC_TEST_DATA.txt").write_text(
            "Every file in this folder was computed from generated workbooks, not from panel "
            "ratings.\n")
    if not quiet:
        p = m["pooled"]
        print("scored {} cases x {} raters{}: realism {}, fidelity {}, agree-with-suite {}, "
              "kappa {}".format(len(rows), len(raters), " (SYNTHETIC)" if synthetic else "",
                                _pct(p["realism"]), _pct(p["fidelity"]),
                                _pct(p["agree_suite"]), m["fleiss_kappa"].get("value")))
    return {"rows": rows, "measures": m, "synthetic": synthetic}


# --------------------------------------------------------------------------- #
# Synthetic workbooks (for testing the pipeline only)                          #
# --------------------------------------------------------------------------- #
def make_synthetic(out_dir: Path, pack_dir: Path = PACK_DIR, panel_dir: Path = PANEL_DIR,
                   seed: int = 7) -> list:
    """Five filled copies of each blank workbook, clearly marked as synthetic.

    Ratings are drawn per case from class-dependent probabilities, so per-class
    measures differ, and with a fixed seed so the set is reproducible.
    """
    import random

    from openpyxl import load_workbook

    labels, draw = read_pack(pack_dir)
    rng = random.Random(seed)
    p_pos = {"benign": 0.9, "V3": 0.85, "V4": 0.35, "V5": 0.3, "V6": 0.2}
    disp_w = {"apply": {"apply": 0.85, "reject": 0.05, "refer": 0.10},
              "refer": {"apply": 0.10, "reject": 0.30, "refer": 0.60}}
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for n in range(1, N_PANEL + 1):
        for stage in "AB":
            src = panel_dir / "Stage_{}_Workbook.xlsx".format(stage)
            wb = load_workbook(src)
            wb.properties.keywords = SYNTHETIC_KEYWORD
            ins = wb["Instructions"]
            ins.insert_rows(1)
            ins["A1"] = SYNTHETIC_KEYWORD + ": generated ratings for testing the scorer."
            ws = wb["Cases"]
            header = [c.value for c in ws[1]]
            for row in range(2, ws.max_row + 1):
                lab = ws.cell(row=row, column=1).value
                if not lab:
                    continue
                d = draw[labels[lab]]
                pp = p_pos[d["class"]]
                for key, name in STAGE_COLUMNS[stage].items():
                    j = header.index(name) + 1
                    if key.startswith("comment"):
                        continue
                    if key == "disposition":
                        w = disp_w[d["suite_disposition_v12"]]
                        val = rng.choices(DISPOSITIONS, weights=[w[x] for x in DISPOSITIONS])[0]
                    else:
                        p = 0.9 if key == "realism" else pp if key == "fidelity" else 0.75
                        val = rng.choice((3, 4)) if rng.random() < p else rng.choice((1, 2))
                    ws.cell(row=row, column=j, value=val)
            path = out_dir / "Stage_{}_Workbook_R{}.xlsx".format(stage, n)
            wb.save(path)
            written.append(path)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="in_dir", help="folder with the ten returned workbooks")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--pack", default=str(PACK_DIR))
    ap.add_argument("--panel", default=str(PANEL_DIR),
                    help="folder with the blank workbooks (for --make-synthetic)")
    ap.add_argument("--allow-missing", action="store_true",
                    help="score with blank or invalid ratings left out (reported)")
    ap.add_argument("--make-synthetic", metavar="DIR",
                    help="write five synthetic filled workbooks per stage into DIR and exit")
    args = ap.parse_args(argv)
    if args.make_synthetic:
        paths = make_synthetic(Path(args.make_synthetic), Path(args.pack), Path(args.panel))
        print("wrote {} synthetic workbooks to {}".format(len(paths), args.make_synthetic))
        return 0
    if not args.in_dir:
        ap.error("--in is required")
    score(Path(args.in_dir), Path(args.out), Path(args.pack), args.allow_missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
