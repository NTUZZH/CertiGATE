#!/usr/bin/env python
"""N22: the practitioner audit and the second-annotator check.

WHAT THIS READS
---------------
The workbooks returned on 2026-11-11 (data only; nothing in them is executed):

    the returned workbooks (not released)
        Stage_A_Workbook_R1..R5.xlsx, Stage_B_Workbook_R1..R5.xlsx, Panel_Profiles.txt
    the returned workbooks (not released)
        Suite_Sample_Check_returned.xlsx, Annotator_Profile.txt

the packs as sent (not released,
not released), the audit key
(results/practitioner_audit_r2/label_map.csv, draw.csv, stage_b.jsonl), the
suite (code/suite/v0.2/suite.jsonl, audit_sample.csv), and the output of the
pre-specified audit scorer (results/practitioner_audit_r2_scored/scores.json and
cases.csv, written by code/scripts/practitioner_audit_r2_score.py).

WHAT THIS DOES
--------------
1. Checks every returned workbook against the workbook as sent: sheets, header,
   case order, every read-only cell, every rating cell inside its drop-down list,
   blanks, cells outside the sent range, and the file-level facts (document
   properties, zip timestamps, writer signature).  Nothing is repaired.
2. Recomputes, by its own code, every pooled, per-class, per-register and
   per-member count the scorer reports, asserts equality with scores.json, and
   adds the measures the scorer does not compute: per-member tables, Stage B by
   gate outcome, Fleiss' kappa and Krippendorff's alpha on the four rating
   scales, the per-case design effects and register unanimity, and the
   counterpart of every headline audit macro.
3. Scores the second-annotator workbook (agreement with the suite's own label,
   which is the all-OK reference of code/scripts/suite_sample_check_score.py),
   per question, per class, Cohen's kappa per field, and the disagreements.
4. Writes analysis/N22_macros.tex, analysis/N22_summary.md and
   analysis/N22_numbers.json, and runs a self-test that recomputes selected
   numbers by a second code path (raw-XML reader, statsmodels, sklearn, a
   pairwise Krippendorff loop, and the scorer's own bootstrap convention).

FORMULAS
--------
* Fleiss' kappa: kappa = (P_bar - P_e) / (1 - P_e), P_i = (sum_j n_ij^2 - n) /
  (n (n - 1)), P_bar = mean_i P_i, P_e = sum_j p_j^2, n = 5 raters per case.
* Krippendorff's alpha: alpha = 1 - D_o / D_e from the coincidence matrix
  o_ck = sum_u (n_uc n_uk - [c = k] n_uc) / (m_u - 1); D_o = sum_ck o_ck d_ck / n,
  D_e = sum_ck n_c n_k d_ck / (n (n - 1)); nominal d_ck = [c != k], ordinal
  d_ck = (sum_{g = c..k} n_g - (n_c + n_k) / 2)^2.
* Cohen's kappa: (p_o - p_e) / (1 - p_e).
* Wilson interval, z = 1.96 (as in suite_sample_check_score.py).
* Intervals of shares: the scorer's case-cluster percentile bootstrap,
  B = 20,000, numpy default_rng([20261104, key]), keys 0 (pooled), 101..105
  (class), 201..203 (register); this script uses keys 301..303 for the Stage B
  outcome sets and key 0 for the agreement statistics.
* Design effect (per-case definition):
  (pvariance of the 30 per-case proportions / 30) / (p (1 - p) / 150).

Run (the returned workbooks are data, so the interpreter runs isolated)::

    OMP_NUM_THREADS=1 taskset -c 14 python -I \\
        code/scripts/n22_audit_annotator.py

Version: l1-n22-audit-annotator-1.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, OrderedDict
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

VERSION = "l1-n22-audit-annotator-1"
ROOT = Path(__file__).resolve().parents[2]
RET = ROOT / "participant_files" / "returned_workbooks"
RET_AUDIT = RET / "2_Practitioner_Audit"
RET_ANNO = RET / "3_Second_Annotator"
RET_FIELD = RET / "1_Field_Instructions"
SENT_AUDIT = ROOT / "participant_files" / "audit_r2"
SENT_ANNO = ROOT / "participant_files" / "sample_check" / "Suite_Sample_Check.xlsx"
PACK = ROOT / "results" / "practitioner_audit_r2"
SCORED = ROOT / "results" / "practitioner_audit_r2_scored"
SUITE = ROOT / "code" / "suite" / "v0.2" / "suite.jsonl"
SAMPLE = ROOT / "code" / "suite" / "v0.2" / "audit_sample.csv"
OUT_TEX = ROOT / "analysis" / "N22_macros.tex"
OUT_MD = ROOT / "analysis" / "N22_summary.md"
OUT_JSON = ROOT / "analysis" / "N22_numbers.json"

SEED = 20261104
B_BOOT = 20000
N_PANEL = 5
RATERS = ["R1", "R2", "R3", "R4", "R5"]
RATER_WORD = {"R1": "ROne", "R2": "RTwo", "R3": "RThree", "R4": "RFour", "R5": "RFive"}
CLASSES = ["benign", "V3", "V4", "V5", "V6"]
CLASS_WORD = {"benign": "Benign", "V3": "VThree", "V4": "VFour", "V5": "VFive", "V6": "VSix",
              "V1": "VOne", "V2": "VTwo"}
REGISTERS = ["formal", "terse", "conversational"]
REG_WORD = {"formal": "Formal", "terse": "Terse", "conversational": "Conv"}
DISPOSITIONS = ["apply", "reject", "refer"]
SCALES = ["realism", "fidelity", "clarity", "action"]
SCALE_WORD = {"realism": "Realism", "fidelity": "Fid", "clarity": "Clar", "action": "Act"}
SCALE_NAME = {"realism": "realism", "fidelity": "fidelity", "clarity": "understandable",
              "action": "actionable"}
STAGE_COLS = {"A": OrderedDict([("realism", "Realism (1-4)"), ("disposition", "Disposition"),
                                ("fidelity", "Fidelity (1-4)"), ("comment", "Comment")]),
              "B": OrderedDict([("clarity", "Understandable (1-4)"),
                                ("action", "Actionable (1-4)"), ("comment", "Comment")])}
N_INFO = {"A": 5, "B": 5}
OUTCOME_OF = {"applied_with_certificate": "applied", "referred_with_price": "referred",
              "blocked_schema": "blocked", "blocked_feas": "blocked", "blocked_qual": "blocked"}
OUTCOMES = ["applied", "referred", "blocked"]
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
QUESTIONS = ["Q1", "Q2", "Q3", "Q4"]
ANNO_CLASSES = ["benign", "V1", "V2", "V3", "V4", "V5", "V6"]
DIRECTION_NOTE = ("Q3: The K arrow runs from this instruction to the twin, opposite the "
                  "stated twin-to-item direction. Reverse the mutation record or correct its "
                  "heading.")
#: Words that belong to Stage B or to the key and are not shown in Stage A.
STAGE_B_WORDS = ("certificate", "certified", "gap", "price", "tolerance", "anchor", "blocked",
                 "referred", "guard", "verdict")
KEY_WORDS = ("benign", "trap", "gold", "v3", "v4", "v5", "v6", "mistranslation", "stratum")


class Fail(Exception):
    pass


def check(name, ok, detail=""):
    if not ok:
        raise Fail("{}: {}".format(name, detail))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(x: float) -> str:
    return "{:.1f}\\%".format(100.0 * x)


def pct_plain(x) -> str:
    return "n/a" if x is None else "{:.1f}%".format(100.0 * x)


def word(n: int) -> str:
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


# --------------------------------------------------------------------------- #
# Reading                                                                      #
# --------------------------------------------------------------------------- #
def sheet_rows(path: Path, sheet: str) -> list:
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def wb_summary(path: Path) -> dict:
    wb = load_workbook(path, data_only=True)
    out = {"sheets": wb.sheetnames, "dims": {}, "dv": {}, "rows": {}}
    for ws in wb.worksheets:
        out["dims"][ws.title] = (ws.max_row, ws.max_column)
        out["dv"][ws.title] = sorted((str(dv.sqref), str(dv.formula1))
                                     for dv in ws.data_validations.dataValidation)
        out["rows"][ws.title] = [list(r) for r in ws.iter_rows(values_only=True)]
    return out


def zip_facts(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        dates = sorted({"{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(*i.date_time[:5])
                        for i in z.infolist()})
        wbx = z.read("xl/workbook.xml").decode("utf-8", "replace")
        sst = z.read("xl/sharedStrings.xml").decode("utf-8", "replace") \
            if "xl/sharedStrings.xml" in names else ""
    return {"parts": len(names), "docprops": any(n.startswith("docProps/") for n in names),
            "zip_dates": dates, "x_prefix": "<x:workbook" in wbx,
            "random_rids": bool(re.search(r'r:id="R[0-9a-f]{16}"', wbx)),
            "shared_strings_empty": sst.strip().endswith("/>") and "<x:si" not in sst
            and "<si" not in sst}


def read_profiles(path: Path) -> list:
    blocks, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.fullmatch(r"R(\d)", line)
        if m:
            cur = OrderedDict(rater="R" + m.group(1))
            blocks.append(cur)
            continue
        k, _, v = line.partition(":")
        cur[k.strip()] = v.strip()
    return blocks


def read_pack():
    with open(PACK / "label_map.csv", newline="") as fh:
        labels = OrderedDict((r["label"], r["case_id"]) for r in csv.DictReader(fh))
    with open(PACK / "draw.csv", newline="") as fh:
        draw = OrderedDict((r["case_id"], r) for r in csv.DictReader(fh))
    stage_b = [json.loads(l) for l in open(PACK / "stage_b.jsonl", encoding="utf-8") if l.strip()]
    return labels, draw, stage_b


# --------------------------------------------------------------------------- #
# 1. Checks of the returned audit workbooks                                    #
# --------------------------------------------------------------------------- #
def check_audit_returns(labels) -> tuple:
    """Return (ratings[rater][label] -> dict, problems list, file facts)."""
    problems, facts = [], OrderedDict()
    ratings = OrderedDict((r, OrderedDict((lab, {}) for lab in labels)) for r in RATERS)
    for stage in "AB":
        sent = wb_summary(SENT_AUDIT / "Stage_{}_Workbook.xlsx".format(stage))
        s_rows = sent["rows"]["Cases"]
        header = s_rows[0]
        cols = {k: header.index(v) for k, v in STAGE_COLS[stage].items()}
        sent_order = [r[0] for r in s_rows[1:]]
        for rater in RATERS:
            path = RET_AUDIT / "Stage_{}_Workbook_{}.xlsx".format(stage, rater)
            tag = "Stage {} {}".format(stage, rater)
            if not path.is_file():
                problems.append("{}: file missing".format(tag))
                continue
            ret = wb_summary(path)
            facts[path.name] = dict(sha256=sha256(path), **zip_facts(path))
            if ret["sheets"] != sent["sheets"]:
                problems.append("{}: sheets {} differ from {}".format(tag, ret["sheets"],
                                                                     sent["sheets"]))
            if ret["rows"]["Instructions"] != sent["rows"]["Instructions"]:
                problems.append("{}: Instructions sheet altered".format(tag))
            if ret["dv"]["Cases"] != sent["dv"]["Cases"]:
                problems.append("{}: drop-down lists altered {}".format(tag, ret["dv"]["Cases"]))
            r_rows = ret["rows"]["Cases"]
            if r_rows[0] != header:
                problems.append("{}: header altered {}".format(tag, r_rows[0]))
            if ret["dims"]["Cases"] != sent["dims"]["Cases"]:
                problems.append("{}: Cases range {} differs from sent {}".format(
                    tag, ret["dims"]["Cases"], sent["dims"]["Cases"]))
            order = [r[0] for r in r_rows[1:]]
            if order != sent_order:
                problems.append("{}: case order differs from the sent order".format(tag))
            seen = Counter(order)
            for lab in labels:
                if seen[lab] != 1:
                    problems.append("{}: case {} appears {} times".format(tag, lab, seen[lab]))
            for i, row in enumerate(r_rows[1:], start=2):
                srow = s_rows[i - 1] if i - 1 < len(s_rows) else [None] * len(header)
                for j in range(N_INFO[stage]):
                    if row[j] != srow[j]:
                        problems.append("{} row {}: read-only cell '{}' altered".format(
                            tag, i, header[j]))
                for j in range(len(header), len(row)):
                    if row[j] is not None:
                        problems.append("{} row {}: value outside the sent columns".format(tag, i))
                lab = row[0]
                if lab not in labels:
                    problems.append("{} row {}: unknown label {!r}".format(tag, i, lab))
                    continue
                rec = ratings[rater][lab]
                for key, j in cols.items():
                    v = row[j]
                    if key == "comment":
                        rec["comment_" + stage] = "" if v is None else str(v)
                        continue
                    if v is None or (isinstance(v, str) and not v.strip()):
                        problems.append("{} {}: {} blank".format(tag, lab, key))
                        rec[key] = None
                    elif key == "disposition":
                        if not isinstance(v, str) or v not in DISPOSITIONS:
                            problems.append("{} {}: disposition {!r} outside the list".format(
                                tag, lab, v))
                        rec[key] = v
                    else:
                        if isinstance(v, bool) or not isinstance(v, int) or v not in (1, 2, 3, 4):
                            problems.append("{} {}: {} = {!r} ({}) outside 1-4".format(
                                tag, lab, key, v, type(v).__name__))
                        rec[key] = v
    return ratings, problems, facts


# --------------------------------------------------------------------------- #
# 2. Measures                                                                  #
# --------------------------------------------------------------------------- #
def boot_idx(n: int, key: int) -> np.ndarray:
    return np.random.default_rng([SEED, key]).integers(0, n, size=(B_BOOT, n))


def boot_interval(values: np.ndarray) -> tuple:
    v = values[~np.isnan(values)]
    if v.size == 0:
        return (None, None)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return (float(lo), float(hi))


def share(num, den, idx=None) -> OrderedDict:
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    out = OrderedDict(num=int(num.sum()), den=int(den.sum()),
                      value=float(num.sum() / den.sum()) if den.sum() else None, lo=None, hi=None)
    if idx is not None and den.sum():
        bn, bd = num[idx].sum(axis=1), den[idx].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            out["lo"], out["hi"] = boot_interval(np.where(bd > 0, bn / bd, np.nan))
    return out


def case_rows(labels, draw, ratings) -> list:
    by_case = {cid: lab for lab, cid in labels.items()}
    rows = []
    for cid, d in draw.items():
        lab = by_case[cid]
        recs = [ratings[r][lab] for r in RATERS]
        disp = Counter(x["disposition"] for x in recs)
        rows.append(OrderedDict(
            case=cid, label=lab, cls=d["class"], register=d["register"],
            pool=("V4_visible" if d["quality_visible"] == "True" else "V4_neutral")
            if d["class"] == "V4" else d["class"],
            subclass=d["subclass"], suite=d["suite_disposition_v12"], guard=d["guard_disposition"],
            terminal=d["guard_terminal_v12"], outcome=OUTCOME_OF[d["guard_terminal_v12"]],
            counts=OrderedDict((k, disp.get(k, 0)) for k in DISPOSITIONS),
            pos=OrderedDict((k, sum(1 for x in recs if x[k] in (3, 4))) for k in SCALES),
            raw=OrderedDict((k, [x[k] for x in recs]) for k in SCALES + ["disposition"])))
    return rows


def block(rows, idx) -> OrderedDict:
    b = OrderedDict(n_cases=len(rows))
    for k in SCALES:
        b[k] = share([r["pos"][k] for r in rows], [N_PANEL] * len(rows), idx)
    den = [N_PANEL] * len(rows)
    for d in DISPOSITIONS:
        b["share_" + d] = share([r["counts"][d] for r in rows], den, idx)
    b["agree_suite"] = share([r["counts"][r["suite"]] for r in rows], den, idx)
    b["agree_guard"] = share([r["counts"][r["guard"]] for r in rows], den, idx)
    ref = [r["suite"] == "refer" for r in rows]
    if any(ref):
        b["withhold_when_refer"] = share(
            [(r["counts"]["reject"] + r["counts"]["refer"]) if f else 0 for r, f in zip(rows, ref)],
            [N_PANEL if f else 0 for f in ref], idx)
    else:
        b["withhold_when_refer"] = None
    b["four"] = OrderedDict((k, sum(1 for r in rows if r["pos"][k] >= 4)) for k in SCALES)
    b["four"]["panel_disposition"] = sum(1 for r in rows if max(r["counts"].values()) >= 4)
    b["four"]["suite_disposition"] = sum(1 for r in rows if r["counts"][r["suite"]] >= 4)
    b["four"]["guard_disposition"] = sum(1 for r in rows if r["counts"][r["guard"]] >= 4)
    return b


def fleiss(counts: np.ndarray) -> tuple:
    counts = np.asarray(counts, dtype=float)
    n = counts.sum(axis=1)[0]
    p_i = (np.square(counts).sum(axis=1) - n) / (n * (n - 1))
    p_bar = float(p_i.mean())
    p_j = counts.sum(axis=0) / counts.sum()
    p_e = float(np.square(p_j).sum())
    k = float("nan") if p_e >= 1 - 1e-12 else (p_bar - p_e) / (1 - p_e)
    return k, p_bar, p_e


def fleiss_boot(counts: np.ndarray, idx: np.ndarray) -> np.ndarray:
    c = counts[idx].astype(float)
    n = float(counts.sum(axis=1)[0])
    p_bar = ((np.square(c).sum(axis=2) - n) / (n * (n - 1))).mean(axis=1)
    p_j = c.sum(axis=1) / c.sum(axis=(1, 2))[:, None]
    p_e = np.square(p_j).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        k = (p_bar - p_e) / (1 - p_e)
    k[p_e >= 1 - 1e-12] = np.nan
    return k


def kripp_delta(n_c: np.ndarray, metric: str) -> np.ndarray:
    K = len(n_c)
    d = np.zeros((K, K))
    for c in range(K):
        for k in range(K):
            if metric == "nominal":
                d[c, k] = 0.0 if c == k else 1.0
            else:
                lo, hi = min(c, k), max(c, k)
                d[c, k] = (n_c[lo:hi + 1].sum() - (n_c[c] + n_c[k]) / 2.0) ** 2
    return d


def kripp_alpha(counts: np.ndarray, metric: str) -> float:
    """Krippendorff's alpha from a (units x categories) count matrix (complete data)."""
    C = np.asarray(counts, dtype=float)
    m = C.sum(axis=1)
    keep = m >= 2
    C, m = C[keep], m[keep]
    o = (C.T @ (C / (m - 1)[:, None])) - np.diag((C / (m - 1)[:, None]).sum(axis=0))
    n_c = o.sum(axis=0)
    n = n_c.sum()
    d = kripp_delta(n_c, metric)
    D_o = (o * d).sum() / n
    D_e = (np.outer(n_c, n_c) * d).sum() / (n * (n - 1))
    return float("nan") if D_e == 0 else float(1 - D_o / D_e)


def kripp_alpha_boot(counts: np.ndarray, idx: np.ndarray, metric: str) -> np.ndarray:
    C = counts[idx].astype(float)  # (B, N, K), every unit has m = 5
    m = float(counts.sum(axis=1)[0])
    o = np.einsum("bnc,bnk->bck", C, C) / (m - 1)
    diag = C.sum(axis=1) / (m - 1)
    o = o - np.einsum("bc,ck->bck", diag, np.eye(C.shape[2]))
    n_c = o.sum(axis=1)
    n = n_c.sum(axis=1)
    out = np.empty(C.shape[0])
    for b in range(C.shape[0]):
        d = kripp_delta(n_c[b], metric)
        D_o = (o[b] * d).sum() / n[b]
        D_e = (np.outer(n_c[b], n_c[b]) * d).sum() / (n[b] * (n[b] - 1))
        out[b] = np.nan if D_e == 0 else 1 - D_o / D_e
    return out


def design_effect(rows, key, getter) -> float:
    props = [getter(r) / N_PANEL for r in rows]
    total = sum(getter(r) for r in rows)
    p = total / (N_PANEL * len(rows))
    return (statistics.pvariance(props) / len(rows)) / (p * (1 - p) / (N_PANEL * len(rows)))


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return (max(0.0, c - h), min(1.0, c + h))


def cohen(ref, chk):
    n = len(ref)
    if n == 0:
        return None
    labs = sorted(set(ref) | set(chk))
    po = sum(a == b for a, b in zip(ref, chk)) / n
    pe = sum((ref.count(l) / n) * (chk.count(l) / n) for l in labs)
    return None if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)


# --------------------------------------------------------------------------- #
# 3. Second annotator                                                          #
# --------------------------------------------------------------------------- #
def check_annotator() -> tuple:
    problems = []
    path = RET_ANNO / "Suite_Sample_Check_returned.xlsx"
    sent, ret = wb_summary(SENT_ANNO), wb_summary(path)
    facts = dict(sha256=sha256(path), **zip_facts(path))
    if ret["sheets"] != sent["sheets"]:
        problems.append("sheets differ: {}".format(ret["sheets"]))
    if ret["rows"]["Instructions"] != sent["rows"]["Instructions"]:
        problems.append("Instructions sheet altered")
    if ret["dv"]["Sample"] != sent["dv"]["Sample"]:
        problems.append("drop-down lists altered")
    s, r = sent["rows"]["Sample"], ret["rows"]["Sample"]
    header = s[0]
    if r[0] != header:
        problems.append("header altered")
    if ret["dims"]["Sample"] != sent["dims"]["Sample"]:
        problems.append("range {} differs from sent {}".format(ret["dims"]["Sample"],
                                                             sent["dims"]["Sample"]))
    if [x[0] for x in r[1:]] != [x[0] for x in s[1:]]:
        problems.append("row order or item ids differ from the sent workbook")
    rows = []
    valid = {"OK", "defect", "n.a."}
    for i, (srow, row) in enumerate(zip(s[1:], r[1:]), start=2):
        for j in range(11):
            if row[j] != srow[j]:
                problems.append("row {} ({}): read-only cell '{}' altered".format(i, row[0],
                                                                               header[j]))
        rec = OrderedDict(item=row[0], cls=row[1], subclass=row[2])
        for q, j in zip(QUESTIONS, range(11, 15)):
            v = row[j]
            rec[q] = v
            if srow[j] == "n.a." and v != "n.a.":
                problems.append("{}: pre-filled n.a. in {} changed to {!r}".format(row[0], q, v))
            if srow[j] is None and v == "n.a.":
                problems.append("{}: {} applies but is marked n.a.".format(row[0], q))
            if v is None:
                problems.append("{}: {} blank".format(row[0], q))
            elif v not in valid:
                problems.append("{}: {} = {!r} outside the list".format(row[0], q, v))
        rec["overall"] = row[15]
        rec["note"] = row[16] or ""
        if row[15] not in ("OK", "defect"):
            problems.append("{}: overall verdict {!r} is not OK or defect".format(row[0], row[15]))
        anydef = any(rec[q] == "defect" for q in QUESTIONS)
        if anydef != (rec["overall"] == "defect"):
            problems.append("{}: overall verdict does not follow Q1-Q4".format(row[0]))
        if rec["overall"] == "defect" and not rec["note"].strip():
            problems.append("{}: defect without a note".format(row[0]))
        rows.append(rec)
    sent_text = " ".join(str(v) for t in ("Instructions", "Sample") for row in sent["rows"][t]
                         for v in row if v is not None).lower()
    outside = []
    for rec in rows:
        for w in re.findall(r"\b(card \d+|crew cards?|campus-\d+ crew cards?)\b", rec["note"].lower()):
            if w not in sent_text:
                outside.append((rec["item"], w))
    return rows, problems, facts, outside


def direction_check(sample_rows) -> Counter:
    """For each benign row with a twin: which instruction holds mutation 'from' and 'to'."""
    suite = {}
    for line in open(SUITE, encoding="utf-8"):
        if line.strip():
            rec = json.loads(line)
            suite[rec["item_id"]] = rec
    def txt(v) -> str:
        if isinstance(v, float) and v == int(v):
            return str(abs(int(v))) if v != 0 else ""
        return "" if isinstance(v, (list, dict)) else str(v)

    res = Counter()
    for s in sample_rows:
        if not s["twin_id"]:
            continue
        side = "benign" if s["primary_class"] == "benign" else "violation"
        rec, tw = suite[s["item_id"]], suite[s["twin_id"]]
        m = rec.get("mutation") or {}
        f, t = txt(m.get("from", "")), txt(m.get("to", ""))
        a, b = rec["instruction"], tw["instruction"]
        if (f and f in a and f not in b) or (t and t in b and t not in a):
            res[side + ":this_to_twin"] += 1
        elif (f and f in b and f not in a) or (t and t in a and t not in b):
            res[side + ":twin_to_this"] += 1
        else:
            res[side + ":not_decidable_by_text"] += 1
    return res


# --------------------------------------------------------------------------- #
# Second code path for the self-test                                           #
# --------------------------------------------------------------------------- #
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def xml_cells(path: Path, sheet: str) -> dict:
    """{(row, col_letter): value} read from the raw sheet XML, no openpyxl."""
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rid = [s for s in wb.find("m:sheets", NS) if s.get("name") == sheet][0].get(
            "{%s}id" % NS["r"])
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = [x for x in rels if x.get("Id") == rid][0].get("Target")
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])) for si in sst]
        ws = ET.fromstring(z.read(target))
    out = {}
    for c in ws.iter("{%s}c" % NS["m"]):
        ref = c.get("r")
        col = re.match(r"[A-Z]+", ref).group(0)
        row = int(ref[len(col):])
        t = c.get("t")
        if t == "inlineStr":
            v = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
        else:
            ve = c.find("m:v", NS)
            if ve is None:
                continue
            v = ve.text
            if t == "s":
                v = shared[int(v)]
            elif t in (None, "n"):
                v = float(v)
        out[(row, col)] = v
    return out


def self_test(rows, measures, scores, labels, draw, anno_rows, anno) -> list:
    log = []

    def same(name, a, b, tol=1e-12):
        ok = (a == b) if not isinstance(a, float) else abs(a - b) <= tol
        check("self-test " + name, ok, "{} vs {}".format(a, b))
        log.append((name, a, b))

    # (1) Fleiss' kappa on dispositions: own code, statsmodels, and the scorer
    from statsmodels.stats.inter_rater import fleiss_kappa as sm_fleiss
    counts = np.array([[r["counts"][d] for d in DISPOSITIONS] for r in rows])
    same("Fleiss kappa (dispositions), own vs statsmodels", round(fleiss(counts)[0], 12),
         round(float(sm_fleiss(counts, method="fleiss")), 12))
    same("Fleiss kappa (dispositions), own vs scorer", round(fleiss(counts)[0], 12),
         round(scores["measures"]["fleiss_kappa"]["value"], 12))
    # (2) pooled realism and (3) pooled actionable positives, from the raw sheet XML
    real = act = agree = 0
    by_case = {lab: draw[cid] for lab, cid in labels.items()}
    for rater in RATERS:
        a = xml_cells(RET_AUDIT / "Stage_A_Workbook_{}.xlsx".format(rater), "Cases")
        b = xml_cells(RET_AUDIT / "Stage_B_Workbook_{}.xlsx".format(rater), "Cases")
        for row in range(2, 32):
            lab = a[(row, "A")]
            real += a[(row, "F")] in (3.0, 4.0)
            agree += a[(row, "G")] == by_case[lab]["suite_disposition_v12"]
            act += b[(row, "G")] in (3.0, 4.0)
    same("pooled realism positives, openpyxl vs raw XML", measures["pooled"]["realism"]["num"],
         real)
    same("pooled actionable positives, openpyxl vs raw XML", measures["pooled"]["action"]["num"],
         act)
    # (4) agreement with the suite disposition: raw XML vs the scorer's cases.csv
    with open(SCORED / "cases.csv", newline="") as fh:
        sc_agree = sum(int(r[r["disposition"]]) for r in csv.DictReader(fh))
    same("agreement with suite disposition, raw XML vs scorer cases.csv", agree, sc_agree)
    # (5) Krippendorff's alpha (ordinal, realism): coincidence matrix vs pairwise loop
    vals = [r["raw"]["realism"] for r in rows]
    cats = [1, 2, 3, 4]
    cm = np.array([[v.count(c) for c in cats] for v in vals])
    a1 = kripp_alpha(cm, "ordinal")
    allv = [x for v in vals for x in v]
    nc = {c: allv.count(c) for c in cats}

    def dord(c, k):
        lo, hi = min(c, k), max(c, k)
        return (sum(nc[g] for g in cats if lo <= g <= hi) - (nc[c] + nc[k]) / 2.0) ** 2

    num = sum(dord(v[i], v[j]) / (len(v) - 1) for v in vals for i in range(len(v))
              for j in range(len(v)) if i != j)
    n = len(allv)
    den = sum(dord(x, y) for i, x in enumerate(allv) for j, y in enumerate(allv) if i != j)
    a2 = 1 - (num / n) / (den / (n * (n - 1)))
    same("Krippendorff alpha (ordinal, realism), matrix vs pairwise loop", round(a1, 12),
         round(a2, 12))
    # (6) the scorer's bootstrap interval of pooled realism, reproduced
    same("pooled realism interval low, own bootstrap vs scorer",
         round(measures["pooled"]["realism"]["lo"], 12),
         round(scores["measures"]["pooled"]["realism"]["lo"], 12))
    # (7) annotator agreement: own Wilson vs statsmodels; own kappa vs sklearn
    from sklearn.metrics import cohen_kappa_score
    from statsmodels.stats.proportion import proportion_confint
    k, nn = anno["overall"]["ok"], anno["overall"]["n"]
    lo, hi = proportion_confint(k, nn, alpha=0.05, method="wilson")
    same("annotator overall Wilson low, own vs statsmodels", round(anno["overall"]["lo"], 3),
         round(float(lo), 3))
    chk = [r["overall"] for r in anno_rows]
    same("annotator overall Cohen kappa, own vs sklearn", round(cohen(["OK"] * len(chk), chk), 12),
         round(float(cohen_kappa_score(["OK"] * len(chk), chk)), 12))
    return log


# --------------------------------------------------------------------------- #
# Macros                                                                       #
# --------------------------------------------------------------------------- #
class Macros:
    def __init__(self):
        self.items = OrderedDict()

    def add(self, name, value, comment):
        name = "nTwentyTwo" + name
        check("macro name is letters only: " + name, re.fullmatch(r"[A-Za-z]+", name) is not None)
        check("macro defined once: " + name, name not in self.items)
        self.items[name] = (str(value), comment)

    def share_set(self, stem, s, what, src, interval=True):
        self.add(stem + "Count", s["num"], "{}: {} of {} ({})".format(what, s["num"], s["den"], src))
        self.add(stem + "Den", s["den"], "{}: the denominator ({})".format(what, src))
        if s["value"] is not None:
            self.add(stem + "Share", pct(s["value"]), "{}: share, {} over {} ({})".format(
                what, s["num"], s["den"], src))
        if interval and s.get("lo") is not None:
            self.add(stem + "ShareLo", pct(s["lo"]), "{}: lower end of the 95% case-cluster "
                     "bootstrap interval (B = 20,000, seed 20261104) ({})".format(what, src))
            self.add(stem + "ShareHi", pct(s["hi"]), "{}: upper end of the same interval "
                     "({})".format(what, src))

    def text(self) -> str:
        L = ["% N22 macros ({}); generated by code/scripts/n22_audit_annotator.py from the "
             "workbooks returned on 2026-11-11 (practitioner audit, five panel members, "
             "30 cases; second-annotator check, 194 rows); each macro follows a comment line "
             "giving its definition and source".format(VERSION)]
        for name, (val, com) in self.items.items():
            L.append("% " + com)
            L.append("\\newcommand{\\" + name + "}{" + val + "}")
        return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    labels, draw, stage_b = read_pack()
    ratings, audit_problems, audit_facts = check_audit_returns(labels)
    check("audit returns complete and inside the lists", not audit_problems,
          "\n  ".join(audit_problems[:50]))
    rows = case_rows(labels, draw, ratings)
    scores = json.loads((SCORED / "scores.json").read_text())
    check("scorer output is not synthetic", scores["synthetic"] is False)
    check("scorer reported no problems", scores["problems"] == [], str(scores["problems"][:5]))

    # ---- measures ---------------------------------------------------------------
    M = OrderedDict()
    M["pooled"] = block(rows, boot_idx(len(rows), 0))
    M["by_class"] = OrderedDict((c, block([r for r in rows if r["cls"] == c],
                                          boot_idx(6, 100 + i)))
                                for i, c in enumerate(CLASSES, start=1))
    M["by_register"] = OrderedDict((g, block([r for r in rows if r["register"] == g],
                                             boot_idx(10, 200 + i)))
                                   for i, g in enumerate(REGISTERS, start=1))
    # assert equality with the scorer on every shared measure
    sm = scores["measures"]
    for scope, mine, theirs in ([("pooled", M["pooled"], sm["pooled"])]
                                + [("class " + c, M["by_class"][c], sm["by_class"][c]) for c in CLASSES]
                                + [("register " + g, M["by_register"][g], sm["by_register"][g])
                                   for g in REGISTERS]):
        for key in SCALES + ["share_apply", "share_reject", "share_refer", "agree_suite",
                             "agree_guard", "withhold_when_refer"]:
            a, b = mine[key], theirs[key]
            if a is None or b is None:
                check("{} {} both undefined".format(scope, key), a is None and b is None)
                continue
            for f in ("num", "den"):
                check("{} {} {} equals scorer".format(scope, key, f), a[f] == b[f],
                      "{} vs {}".format(a[f], b[f]))
            for f in ("value", "lo", "hi"):
                check("{} {} {} equals scorer".format(scope, key, f),
                      (a[f] is None and b[f] is None) or abs(a[f] - b[f]) < 1e-12,
                      "{} vs {}".format(a[f], b[f]))
        f4 = theirs["four_of_five"]
        for key, val in mine["four"].items():
            check("{} four-of-five {} equals scorer".format(scope, key), f4[key] == val)

    # V4 pools, Stage B by gate outcome
    M["by_pool"] = OrderedDict((p, block([r for r in rows if r["pool"] == p], None))
                               for p in ("V4_visible", "V4_neutral"))
    M["by_outcome"] = OrderedDict()
    for i, o in enumerate(OUTCOMES, start=1):
        sub = [r for r in rows if r["outcome"] == o]
        M["by_outcome"][o] = block(sub, boot_idx(len(sub), 300 + i))

    # per panel member
    per_rater = OrderedDict()
    by_case = {lab: draw[cid] for lab, cid in labels.items()}
    for rater in RATERS:
        recs = ratings[rater]
        d = OrderedDict()
        for k in SCALES:
            v = [recs[l][k] for l in labels]
            d[k + "_pos"] = sum(1 for x in v if x in (3, 4))
            d[k + "_mean"] = statistics.mean(v)
            d[k + "_dist"] = OrderedDict((c, v.count(c)) for c in (1, 2, 3, 4))
        disp = [recs[l]["disposition"] for l in labels]
        for x in DISPOSITIONS:
            d[x] = disp.count(x)
        d["agree_suite"] = sum(recs[l]["disposition"] == by_case[l]["suite_disposition_v12"]
                               for l in labels)
        d["agree_guard"] = sum(recs[l]["disposition"] == by_case[l]["guard_disposition"]
                               for l in labels)
        d["by_class"] = OrderedDict()
        for c in CLASSES:
            ls = [l for l in labels if by_case[l]["class"] == c]
            d["by_class"][c] = OrderedDict(
                [(k, sum(1 for l in ls if recs[l][k] in (3, 4))) for k in SCALES]
                + [("agree_suite", sum(recs[l]["disposition"] == by_case[l]["suite_disposition_v12"]
                                       for l in ls))]
                + [(x, sum(recs[l]["disposition"] == x for l in ls)) for x in DISPOSITIONS])
        per_rater[rater] = d
    for k in SCALES:
        check("per-member {} sums to pooled".format(k),
              sum(per_rater[r][k + "_pos"] for r in RATERS) == M["pooled"][k]["num"])

    # agreement statistics
    idx0 = boot_idx(len(rows), 0)
    agree = OrderedDict()
    dc = np.array([[r["counts"][d] for d in DISPOSITIONS] for r in rows])
    k, po, pe = fleiss(dc)
    lo, hi = boot_interval(fleiss_boot(dc, idx0))
    check("Fleiss kappa interval equals scorer",
          abs(lo - sm["fleiss_kappa"]["lo"]) < 1e-12 and abs(hi - sm["fleiss_kappa"]["hi"]) < 1e-12)
    agree["disposition"] = OrderedDict(fleiss=k, po=po, pe=pe, fleiss_lo=lo, fleiss_hi=hi)
    a = kripp_alpha(dc, "nominal")
    lo, hi = boot_interval(kripp_alpha_boot(dc, idx0, "nominal"))
    agree["disposition"].update(alpha_nominal=a, alpha_lo=lo, alpha_hi=hi)
    for s in SCALES:
        c4 = np.array([[r["raw"][s].count(c) for c in (1, 2, 3, 4)] for r in rows])
        c2 = np.array([[r["raw"][s].count(1) + r["raw"][s].count(2),
                        r["raw"][s].count(3) + r["raw"][s].count(4)] for r in rows])
        f4, po4, pe4 = fleiss(c4)
        f2, po2, pe2 = fleiss(c2)
        al = kripp_alpha(c4, "ordinal")
        alo, ahi = boot_interval(kripp_alpha_boot(c4, idx0, "ordinal"))
        f2lo, f2hi = boot_interval(fleiss_boot(c2, idx0))
        agree[s] = OrderedDict(fleiss4=f4, po4=po4, pe4=pe4, fleiss2=f2, po2=po2, pe2=pe2,
                               fleiss2_lo=f2lo, fleiss2_hi=f2hi, alpha_ordinal=al,
                               alpha_lo=alo, alpha_hi=ahi)

    # per-case design effects and unanimity
    first = OrderedDict()
    first["deff"] = OrderedDict()
    for s in SCALES:
        first["deff"][s] = design_effect(rows, s, lambda r, s=s: r["pos"][s])
    first["deff"]["disposition"] = design_effect(rows, "d", lambda r: r["counts"][r["suite"]])
    first["unanimous_suite"] = OrderedDict()
    first["mean_agree"] = OrderedDict()
    first["unanimous_panel"] = OrderedDict()
    for g in REGISTERS:
        sub = [r for r in rows if r["register"] == g]
        first["unanimous_suite"][g] = sum(1 for r in sub if r["counts"][r["suite"]] == N_PANEL)
        first["mean_agree"][g] = statistics.mean(r["counts"][r["suite"]] for r in sub)
        first["unanimous_panel"][g] = sum(1 for r in sub if max(r["counts"].values()) == N_PANEL)
    first["nonunanimous_suite"] = OrderedDict(
        (g, 10 - first["unanimous_suite"][g]) for g in REGISTERS)
    first["nonunanimous_suite_total"] = sum(first["nonunanimous_suite"].values())
    first["nonunanimous_panel_total"] = sum(10 - first["unanimous_panel"][g] for g in REGISTERS)
    below = OrderedDict()
    for key, get in (("realism", lambda r: r["pos"]["realism"]),
                     ("disposition", lambda r: r["counts"][r["suite"]]),
                     ("fidelity", lambda r: r["pos"]["fidelity"]),
                     ("clarity", lambda r: r["pos"]["clarity"]),
                     ("action", lambda r: r["pos"]["action"])):
        below[key] = [r["case"] for r in rows if get(r) < 4]
    first["below"] = below
    first["below_stage_a_distinct"] = sorted(set(below["realism"]) | set(below["disposition"])
                                             | set(below["fidelity"]))
    # fidelity read against the suite's own reading (derived, not pre-specified): a faithful
    # candidate (benign, V3: the gold operations) should be rated positive and an unfaithful one
    # (V4 trap, V5 arbitrary resolution, V6 injected operations) negative
    fid_match = sum((r["pos"]["fidelity"] if r["cls"] in ("benign", "V3")
                     else N_PANEL - r["pos"]["fidelity"]) for r in rows)
    first["fidelity_matches_suite_reading"] = fid_match
    # panel modal disposition against the gate
    modal = OrderedDict()
    for r in rows:
        top = max(r["counts"].values())
        modes = [d for d in DISPOSITIONS if r["counts"][d] == top]
        modal[r["case"]] = modes[0] if len(modes) == 1 else "tie"
    first["modal_equals_guard"] = sum(1 for r in rows if modal[r["case"]] == r["guard"])
    first["modal_equals_suite"] = sum(1 for r in rows if modal[r["case"]] == r["suite"])
    first["guard_equals_suite_cases"] = sum(1 for r in rows if r["guard"] == r["suite"])
    first["guard_equals_suite_by_class"] = OrderedDict(
        (c, sum(1 for r in rows if r["cls"] == c and r["guard"] == r["suite"])) for c in CLASSES)
    first["guard_terminals_by_class"] = OrderedDict(
        (c, dict(Counter(r["terminal"] for r in rows if r["cls"] == c))) for c in CLASSES)
    first["modal"] = modal
    raw_means = OrderedDict((s, statistics.mean(x for r in rows for x in r["raw"][s]))
                            for s in SCALES)

    # comments: duplicates and Stage-A words that Stage A does not show
    comment_hits = []
    dup = Counter()
    for rater in RATERS:
        for lab in labels:
            for st in "AB":
                txt = ratings[rater][lab].get("comment_" + st, "")
                if txt:
                    dup[txt] += 1
                if st == "A" and txt:
                    low = txt.lower()
                    hits = [w for w in STAGE_B_WORDS + KEY_WORDS
                            if re.search(r"(?<![a-z0-9]){}(?![a-z0-9])".format(w), low)]
                    if hits:
                        comment_hits.append((rater, lab, hits, txt))
    n_comments = sum(dup.values())
    dup_texts = {t: n for t, n in dup.items() if n > 1}
    pair_identical = OrderedDict()
    for s in SCALES + ["disposition"]:
        for i, r1 in enumerate(RATERS):
            for r2 in RATERS[i + 1:]:
                v1 = [ratings[r1][l][s] for l in labels]
                v2 = [ratings[r2][l][s] for l in labels]
                pair_identical[(s, r1, r2)] = sum(a == b for a, b in zip(v1, v2))
    full_identical = [(r1, r2) for i, r1 in enumerate(RATERS) for r2 in RATERS[i + 1:]
                      if all(ratings[r1][l][s] == ratings[r2][l][s] for l in labels
                             for s in SCALES + ["disposition"])]
    # the gate output the panel rated
    sent_b = sheet_rows(SENT_AUDIT / "Stage_B_Workbook.xlsx", "Cases")
    out_counts = Counter(r[3] for r in sent_b[1:])
    v3_labels = [lab for lab, cid in labels.items() if draw[cid]["class"] == "V3"]
    v3_rows = [r for r in sent_b[1:] if r[0] in v3_labels]
    check("every V3 case shows 'Referred with price' in Stage B",
          all(r[3] == "Referred with price" for r in v3_rows))
    check("Stage B outcome equals the pack's v1.2 terminal on every case",
          all({"applied_with_certificate": "Applied with certificate",
               "referred_with_price": "Referred with price"}.get(
                   draw[labels[r[0]]]["guard_terminal_v12"], "Blocked with findings") == r[3]
              for r in sent_b[1:]))
    quote_row = [r for r in sent_b[1:] if r[0] == "C23"][0]

    # panel profiles
    prof = read_profiles(RET_AUDIT / "Panel_Profiles.txt")
    check("five profiles R1..R5", [p["rater"] for p in prof] == RATERS)
    years = [float(p["Years in facility management"]) for p in prof]
    freq = [p["Work-order change approval frequency"].lower() for p in prof]
    cmms = [p["CMMS use"].lower().startswith("yes") for p in prof]
    panel = OrderedDict(
        roles=[p["Role"] for p in prof], years=years, years_min=min(years),
        years_median=statistics.median(years), years_max=max(years),
        years_mean=statistics.mean(years),
        approve_weekly_or_more=sum(f in ("daily", "weekly") for f in freq),
        approve_daily=freq.count("daily"), approve_weekly=freq.count("weekly"),
        approve_never=freq.count("never"), cmms=sum(cmms),
        years_at_least_five=sum(y >= 5 for y in years), freq=freq,
        cmms_text=[p["CMMS use"] for p in prof])

    # ---- second annotator ------------------------------------------------------
    anno_rows, anno_problems, anno_facts, anno_outside = check_annotator()
    with open(SAMPLE, newline="") as fh:
        sample = list(csv.DictReader(fh))
    check("annotator rows follow audit_sample.csv",
          [r["item"] for r in anno_rows] == [s["item_id"] for s in sample])
    anno = OrderedDict(rows=len(anno_rows))
    k = sum(r["overall"] == "OK" for r in anno_rows)
    nn = sum(r["overall"] in ("OK", "defect") for r in anno_rows)
    lo, hi = wilson(k, nn)
    anno["overall"] = OrderedDict(ok=k, defect=nn - k, n=nn, p=k / nn, lo=lo, hi=hi,
                                  kappa=cohen(["OK"] * nn, [r["overall"] for r in anno_rows]))
    anno["by_question"] = OrderedDict()
    for q in QUESTIONS:
        c = Counter(r[q] for r in anno_rows)
        n_app = c["OK"] + c["defect"]
        lo, hi = wilson(c["OK"], n_app)
        anno["by_question"][q] = OrderedDict(
            ok=c["OK"], defect=c["defect"], na=c["n.a."], n=n_app,
            p=c["OK"] / n_app if n_app else None, lo=lo, hi=hi,
            kappa=cohen(["OK"] * n_app, [r[q] for r in anno_rows if r[q] in ("OK", "defect")]))
    anno["by_class"] = OrderedDict()
    for c in ANNO_CLASSES:
        sub = [r for r in anno_rows if r["cls"] == c]
        kk = sum(r["overall"] == "OK" for r in sub)
        lo, hi = wilson(kk, len(sub))
        anno["by_class"][c] = OrderedDict(
            rows=len(sub), ok=kk, defect=len(sub) - kk, p=kk / len(sub), lo=lo, hi=hi,
            kappa=cohen(["OK"] * len(sub), [r["overall"] for r in sub]),
            q_defects=OrderedDict((q, sum(r[q] == "defect" for r in sub)) for q in QUESTIONS))
    direction_only = [r["item"] for r in anno_rows if r["note"] == DIRECTION_NOTE]
    direction_any = [r["item"] for r in anno_rows if DIRECTION_NOTE in r["note"]]
    anno["direction_only"] = len(direction_only)
    anno["direction_any"] = len(direction_any)
    anno["direction_check"] = direction_check(sample)
    anno["agree_excl_direction"] = OrderedDict(ok=k + len(direction_only), n=nn)
    lo, hi = wilson(k + len(direction_only), nn)
    anno["agree_excl_direction"].update(p=(k + len(direction_only)) / nn, lo=lo, hi=hi)
    anno["distinct_notes"] = len({r["note"] for r in anno_rows if r["note"]})
    anno_prof = OrderedDict()
    for line in (RET_ANNO / "Annotator_Profile.txt").read_text(encoding="utf-8").splitlines():
        kk2, _, vv = line.partition(":")
        if vv:
            anno_prof[kk2.strip()] = vv.strip()

    # field-instruction returns: file-level facts only (not scored here)
    field_facts = OrderedDict((p.name, zip_facts(p)) for p in sorted(RET_FIELD.glob("*.xlsx")))
    sent_facts = OrderedDict((p.name, zip_facts(p)) for p in
                             [SENT_AUDIT / "Stage_A_Workbook.xlsx",
                              SENT_AUDIT / "Stage_B_Workbook.xlsx", SENT_ANNO])

    # ---- self-test ------------------------------------------------------------
    st_log = self_test(rows, M, scores, labels, draw, anno_rows, anno)

    # ---- macros -----------------------------------------------------------------
    mac = Macros()
    S = "analysis/N22_summary.md; results/practitioner_audit_r2_scored/scores.json"
    mac.add("AuditCases", len(rows), "cases in the audit (results/practitioner_audit_r2/draw.csv)")
    mac.add("AuditReviewers", N_PANEL, "panel members who returned both stages (returned workbooks)")
    mac.add("AuditReviewersWord", word(N_PANEL), "the same, as a word")
    mac.add("AuditJudgements", N_PANEL * len(rows), "member-case judgements per measure, 5 x 30")
    mac.add("AuditBootReplicates", "20{,}000", "bootstrap replicates behind every interval (scorer)")
    mac.add("AuditKappa", "{:.3f}".format(agree["disposition"]["fleiss"]),
            "Fleiss' kappa over apply, reject and refer, 5 raters, 30 cases ({})".format(S))
    mac.add("AuditKappaLo", "{:.3f}".format(agree["disposition"]["fleiss_lo"]),
            "lower end of the 95% case-bootstrap interval of that kappa ({})".format(S))
    mac.add("AuditKappaHi", "{:.3f}".format(agree["disposition"]["fleiss_hi"]),
            "upper end of the same interval ({})".format(S))
    mac.add("AuditKappaPo", "{:.3f}".format(agree["disposition"]["po"]),
            "observed agreement P-bar of that kappa: mean share of agreeing rater pairs")
    mac.add("AuditKappaPe", "{:.3f}".format(agree["disposition"]["pe"]),
            "chance agreement P-e of that kappa: sum of squared category marginals")
    mac.add("AuditAlphaDisp", "{:.3f}".format(agree["disposition"]["alpha_nominal"]),
            "Krippendorff's alpha (nominal) on the dispositions (analysis/N22_summary.md)")
    for s in SCALES:
        w = SCALE_WORD[s]
        g = agree[s]
        mac.add("AuditFleissBin" + w, "{:.3f}".format(g["fleiss2"]),
                "Fleiss' kappa on {} read as positive (3, 4) or not (1, 2), 5 raters, 30 cases "
                "(analysis/N22_summary.md)".format(SCALE_NAME[s]))
        mac.add("AuditFleissFour" + w, "{:.3f}".format(g["fleiss4"]),
                "Fleiss' kappa on {} with its four points as nominal categories "
                "(analysis/N22_summary.md)".format(SCALE_NAME[s]))
        mac.add("AuditAlpha" + w, "{:.3f}".format(g["alpha_ordinal"]),
                "Krippendorff's alpha (ordinal) on the four-point {} ratings "
                "(analysis/N22_summary.md)".format(SCALE_NAME[s]))
        mac.add("AuditAlpha" + w + "Lo", "{:.3f}".format(g["alpha_lo"]),
                "lower end of the 95% case-bootstrap interval of that alpha (key 0)")
        mac.add("AuditAlpha" + w + "Hi", "{:.3f}".format(g["alpha_hi"]),
                "upper end of the same interval")
    stems = [("Realism", "realism", "positive realism ratings (3 or 4)"),
             ("Fid", "fidelity", "positive fidelity ratings (3 or 4): the candidate handling "
              "represents the instruction"),
             ("Clar", "clarity", "positive understandable ratings (3 or 4) of the gate's record"),
             ("Act", "action", "positive actionable ratings (3 or 4) of the gate's record"),
             ("Disp", "agree_suite", "Stage A dispositions equal to the suite disposition under "
              "v1.2"),
             ("Guard", "agree_guard", "Stage A dispositions equal to the gate's actual v1.2 "
              "disposition"),
             ("Apply", "share_apply", "Stage A dispositions apply"),
             ("Reject", "share_reject", "Stage A dispositions reject"),
             ("Refer", "share_refer", "Stage A dispositions refer"),
             ("Withhold", "withhold_when_refer", "reject or refer on cases whose suite "
              "disposition is refer")]
    for stem, key, what in stems:
        mac.share_set("Audit" + stem, M["pooled"][key], what + ", pooled", S)
        for c in CLASSES:
            if M["by_class"][c][key] is not None:
                mac.share_set("Audit" + stem + CLASS_WORD[c], M["by_class"][c][key],
                              what + ", class " + c, S)
        for g in REGISTERS:
            if M["by_register"][g][key] is not None:
                mac.share_set("Audit" + stem + REG_WORD[g], M["by_register"][g][key],
                              what + ", register " + g, S)
    for p, pw in (("V4_visible", "VFourVisible"), ("V4_neutral", "VFourNeutral")):
        for stem, key, what in stems[:9]:
            mac.share_set("Audit" + stem + pw, M["by_pool"][p][key],
                          what + ", " + p.replace("_", " "), "analysis/N22_summary.md",
                          interval=False)
    for o in OUTCOMES:
        b = M["by_outcome"][o]
        ow = o.capitalize()
        mac.add("AuditOutcome" + ow + "Cases", b["n_cases"],
                "cases whose Stage B record shows the gate outcome '{}' (stage_b.jsonl)".format(o))
        for stem, key, what in stems[:4]:
            mac.share_set("Audit" + stem + "Outcome" + ow, b[key],
                          what + ", cases the gate " + o, "analysis/N22_summary.md")
    four_names = [("Realism", "realism"), ("Fid", "fidelity"), ("Clar", "clarity"),
                  ("Act", "action"), ("PanelDisp", "panel_disposition"),
                  ("Disp", "suite_disposition"), ("GuardDisp", "guard_disposition")]
    for stem, key in four_names:
        mac.add("AuditRuleCases" + stem, M["pooled"]["four"][key],
                "cases (of 30) meeting the four-of-five rule on {} ({})".format(key, S))
        for c in CLASSES:
            mac.add("AuditRuleCases" + stem + CLASS_WORD[c], M["by_class"][c]["four"][key],
                    "cases (of 6) of class {} meeting the four-of-five rule on {} ({})".format(
                        c, key, S))
    nb = len(first["below_stage_a_distinct"])
    mac.add("AuditBelowRule", nb, "distinct cases below the four-of-five rule on at least one of "
            "realism, suite disposition and fidelity: {} (analysis/N22_summary.md)".format(
                ";".join(first["below_stage_a_distinct"])))
    mac.add("AuditBelowRuleWord", word(nb) if nb < 10 else str(nb), "the same, as a word")
    for x in DISPOSITIONS:
        mac.add("AuditVotes" + x.capitalize(), M["pooled"]["share_" + x]["num"],
                "Stage A votes for {} over every case, of 150 ({})".format(x, S))
    for s in SCALES:
        mac.add("AuditDeff" + SCALE_WORD[s], "{:.2f}".format(first["deff"][s]),
                "design effect of the pooled {} share, per-case definition "
                "(analysis/N22_summary.md)".format(SCALE_NAME[s]))
    mac.add("AuditDeffDisp", "{:.2f}".format(first["deff"]["disposition"]),
            "design effect of the pooled agreement with the suite disposition, per-case "
            "definition")
    dv = list(first["deff"].values())
    mac.add("AuditDeffMin", "{:.2f}".format(min(dv)), "minimum design effect over the five "
            "pooled measures (realism, disposition, fidelity, understandable, actionable)")
    mac.add("AuditDeffMax", "{:.2f}".format(max(dv)), "maximum design effect over the same five")
    for g in REGISTERS:
        u = first["unanimous_suite"][g]
        mac.add("AuditUnan" + REG_WORD[g], u, "{} cases (of 10) on which all five members chose "
                "the suite disposition (analysis/N22_summary.md)".format(g))
        mac.add("AuditUnan" + REG_WORD[g] + "Word", word(u), "the same, as a word")
        mac.add("AuditMean" + REG_WORD[g], "{:.2f}".format(first["mean_agree"][g]),
                "mean number of members per {} case choosing the suite disposition, of 5".format(g))
        nu = first["nonunanimous_suite"][g]
        mac.add("AuditNonUnan" + REG_WORD[g], nu, "{} cases (of 10) on which at least one member "
                "chose other than the suite disposition".format(g))
        mac.add("AuditNonUnan" + REG_WORD[g] + "Word", word(nu), "the same, as a word")
        mac.add("AuditPanelUnan" + REG_WORD[g], first["unanimous_panel"][g],
                "{} cases (of 10) on which all five members chose the same disposition, "
                "whatever the suite disposition".format(g))
    mac.add("AuditNonUnan", first["nonunanimous_suite_total"], "cases (of 30) on which at least "
            "one member chose other than the suite disposition")
    mac.add("AuditPanelNonUnan", first["nonunanimous_panel_total"], "cases (of 30) on which the "
            "five members did not all choose the same disposition")
    mac.add("AuditModalGuard", first["modal_equals_guard"], "cases (of 30) whose single most "
            "chosen Stage A disposition equals the gate's actual disposition")
    mac.add("AuditModalSuite", first["modal_equals_suite"], "cases (of 30) whose single most "
            "chosen Stage A disposition equals the suite disposition")
    mac.add("AuditGuardSuiteCases", first["guard_equals_suite_cases"], "cases (of 30) on which "
            "the gate's actual disposition equals the suite disposition (draw.csv)")
    for c in CLASSES:
        mac.add("AuditGuardSuiteCases" + CLASS_WORD[c], first["guard_equals_suite_by_class"][c],
                "cases (of 6) of class {} on which the gate's actual disposition equals the "
                "suite disposition (draw.csv)".format(c))
    fm = first["fidelity_matches_suite_reading"]
    mac.add("AuditFidSuiteReadingCount", fm, "derived, not pre-specified: fidelity judgements "
            "that match the suite's reading of the candidate (positive on benign and V3, "
            "negative on V4, V5 and V6), of 150")
    mac.add("AuditFidSuiteReadingShare", pct(fm / 150.0), "the same, as a share of 150")
    for s in SCALES:
        mac.add("AuditMean" + SCALE_WORD[s], "{:.2f}".format(raw_means[s]),
                "mean of the 150 raw {} ratings (1 to 4)".format(SCALE_NAME[s]))
    mac.add("AuditStageBReferred", out_counts["Referred with price"],
            "Stage B cases whose record shows 'Referred with price' (not released"
            "Stage_B_Workbook.xlsx)")
    mac.add("AuditStageBApplied", out_counts["Applied with certificate"],
            "Stage B cases whose record shows 'Applied with certificate'")
    mac.add("AuditStageBBlocked", out_counts["Blocked with findings"],
            "Stage B cases whose record shows 'Blocked with findings'")
    for rater in RATERS:
        d = per_rater[rater]
        rw = RATER_WORD[rater]
        for s in SCALES:
            mac.add("Audit" + rw + SCALE_WORD[s] + "Count", d[s + "_pos"],
                    "panel member {}: positive {} ratings, of 30".format(rater, SCALE_NAME[s]))
            mac.add("Audit" + rw + SCALE_WORD[s] + "Share", pct(d[s + "_pos"] / 30.0),
                    "panel member {}: the same, as a share of 30".format(rater))
        mac.add("Audit" + rw + "DispCount", d["agree_suite"], "panel member {}: dispositions equal "
                "to the suite disposition, of 30".format(rater))
        mac.add("Audit" + rw + "DispShare", pct(d["agree_suite"] / 30.0),
                "panel member {}: the same, as a share of 30".format(rater))
        for x in DISPOSITIONS:
            mac.add("Audit" + rw + x.capitalize(), d[x], "panel member {}: dispositions {}, of 30"
                    .format(rater, x))
    mac.add("PanelSize", N_PANEL, "panel members with a profile (Panel_Profiles.txt)")
    mac.add("PanelYearsMin", "{:g}".format(panel["years_min"]),
            "fewest years in facility management on the panel (Panel_Profiles.txt)")
    mac.add("PanelYearsMedian", "{:g}".format(panel["years_median"]),
            "median years in facility management on the panel")
    mac.add("PanelYearsMax", "{:g}".format(panel["years_max"]),
            "most years in facility management on the panel")
    mac.add("PanelYearsAtLeastFive", panel["years_at_least_five"],
            "panel members with at least five years in facility management")
    mac.add("PanelYearsAtLeastFiveWord", word(panel["years_at_least_five"]), "the same, as a word")
    mac.add("PanelApproveWeekly", panel["approve_weekly_or_more"],
            "panel members who approve work-order changes at least weekly (daily or weekly)")
    mac.add("PanelApproveWeeklyWord", word(panel["approve_weekly_or_more"]), "the same, as a word")
    mac.add("PanelApproveDaily", panel["approve_daily"], "panel members who approve daily")
    mac.add("PanelApproveNever", panel["approve_never"], "panel members who never approve "
            "work-order changes")
    mac.add("PanelCMMS", panel["cmms"], "panel members who use a CMMS")
    mac.add("PanelCMMSWord", word(panel["cmms"]), "the same, as a word")
    SA = "results/suite_sample_check_scored/report_planner.txt; analysis/N22_summary.md"
    o = anno["overall"]
    mac.add("AnnoRows", anno["rows"], "rows checked by the second annotator (Suite_Sample_Check_returned.xlsx)")
    mac.add("AnnoOK", o["ok"], "rows the annotator marks OK overall, i.e. agreeing with the "
            "suite's label ({})".format(SA))
    mac.add("AnnoDefect", o["defect"], "rows the annotator marks defect overall ({})".format(SA))
    mac.add("AnnoAgreeShare", pct(o["p"]), "overall agreement with the suite's label, {} of {} "
            "({})".format(o["ok"], o["n"], SA))
    mac.add("AnnoAgreeLo", pct(o["lo"]), "lower end of the Wilson 95% interval of that share")
    mac.add("AnnoAgreeHi", pct(o["hi"]), "upper end of the Wilson 95% interval of that share")
    mac.add("AnnoKappa", "{:.3f}".format(o["kappa"]), "Cohen's kappa of the overall verdict "
            "against the suite's label; zero by construction, because the suite's label is OK "
            "on every row")
    qw = {"Q1": "QOne", "Q2": "QTwo", "Q3": "QThree", "Q4": "QFour"}
    for q in QUESTIONS:
        d = anno["by_question"][q]
        mac.add("Anno" + qw[q] + "OK", d["ok"], "{}: rows marked OK ({})".format(q, SA))
        mac.add("Anno" + qw[q] + "Defect", d["defect"], "{}: rows marked defect".format(q))
        mac.add("Anno" + qw[q] + "Applies", d["n"], "{}: rows where the question applies "
                "(OK or defect)".format(q))
        mac.add("Anno" + qw[q] + "AgreeShare", pct(d["p"]), "{}: agreement with the suite's "
                "label, {} of {}".format(q, d["ok"], d["n"]))
        mac.add("Anno" + qw[q] + "AgreeLo", pct(d["lo"]), "{}: Wilson 95% lower end".format(q))
        mac.add("Anno" + qw[q] + "AgreeHi", pct(d["hi"]), "{}: Wilson 95% upper end".format(q))
        mac.add("Anno" + qw[q] + "Kappa", "{:.3f}".format(d["kappa"]),
                "{}: Cohen's kappa against the suite's label, zero by construction".format(q))
    for c in ANNO_CLASSES:
        d = anno["by_class"][c]
        mac.add("Anno" + CLASS_WORD[c] + "Rows", d["rows"], "class {}: rows checked".format(c))
        mac.add("Anno" + CLASS_WORD[c] + "OK", d["ok"], "class {}: rows marked OK overall".format(c))
        mac.add("Anno" + CLASS_WORD[c] + "AgreeShare", pct(d["p"]),
                "class {}: agreement with the suite's label, {} of {}".format(c, d["ok"], d["rows"]))
    mac.add("AnnoDirectionOnly", anno["direction_only"], "post hoc: defect rows whose only note "
            "is that column K runs from this item to the twin, opposite its heading")
    mac.add("AnnoDirectionAny", anno["direction_any"], "post hoc: rows whose note includes that "
            "column-K direction remark (all benign rows)")
    ex = anno["agree_excl_direction"]
    mac.add("AnnoAgreeExclDirectionShare", pct(ex["p"]), "post hoc: overall agreement if the "
            "direction-only rows counted as OK, {} of {}".format(ex["ok"], ex["n"]))
    mac.add("AnnoYears", anno_prof.get("Years in facility management", ""),
            "second annotator's years in facility management (Annotator_Profile.txt)")

    tex = mac.text()
    OUT_TEX.write_text(tex, encoding="utf-8")

    # ---- summary ----------------------------------------------------------------
    numbers = OrderedDict(version=VERSION, inputs=OrderedDict(
        (str(p.relative_to(ROOT)), sha256(p)) for p in
        sorted(RET_AUDIT.glob("*")) + sorted(RET_ANNO.glob("*")) +
        [SCORED / "scores.json", SCORED / "cases.csv", PACK / "draw.csv", PACK / "label_map.csv"]),
        measures=M, per_rater=per_rater, agreement=agree, first_round_style=first,
        raw_means=raw_means, panel=panel, annotator=anno, annotator_profile=anno_prof,
        self_test=st_log)
    OUT_JSON.write_text(json.dumps(numbers, indent=1, default=lambda x: list(x)
                                   if isinstance(x, (set, tuple)) else str(x)) + "\n")
    md = summary_md(rows, M, per_rater, agree, first, raw_means, panel, anno, anno_rows,
                    anno_prof, audit_facts, anno_facts, field_facts, sent_facts, comment_hits,
                    n_comments, dup_texts, pair_identical, full_identical, quote_row,
                    out_counts, anno_outside, st_log, len(mac.items))
    OUT_MD.write_text(md, encoding="utf-8")
    print("N22: {} macros, {} self-test comparisons passed; audit pooled realism {}, fidelity {}, "
          "understandable {}, actionable {}, agree-with-suite {}, kappa {:.3f}; annotator "
          "agreement {}".format(len(mac.items), len(st_log), pct_plain(M["pooled"]["realism"]["value"]),
                                pct_plain(M["pooled"]["fidelity"]["value"]),
                                pct_plain(M["pooled"]["clarity"]["value"]),
                                pct_plain(M["pooled"]["action"]["value"]),
                                pct_plain(M["pooled"]["agree_suite"]["value"]),
                                agree["disposition"]["fleiss"], pct_plain(anno["overall"]["p"])))
    return 0


def fmt_s(s) -> str:
    if s is None or s["value"] is None:
        return "n/a"
    t = "{}/{} ({:.1f}%".format(s["num"], s["den"], 100 * s["value"])
    if s.get("lo") is not None:
        t += " [{:.1f}, {:.1f}]".format(100 * s["lo"], 100 * s["hi"])
    return t + ")"


def summary_md(rows, M, per_rater, agree, first, raw_means, panel, anno, anno_rows, anno_prof,
               audit_facts, anno_facts, field_facts, sent_facts, comment_hits, n_comments,
               dup_texts, pair_identical, full_identical, quote_row, out_counts, anno_outside,
               st_log, n_macros) -> str:
    L = []
    A = L.append
    A("# N22: practitioner audit and second-annotator check")
    A("")
    A("Generated by `code/scripts/n22_audit_annotator.py` ({}) from the workbooks returned on "
      "2026-11-11. Counts are judgements (5 panel members x cases) unless a row says cases. A rating "
      "of 3 or 4 is positive. Intervals of shares are the scorer's 95% case-cluster bootstrap "
      "(B = 20,000, seed 20261104); annotator intervals are Wilson 95%. {} macros in "
      "`analysis/N22_macros.tex`.".format(VERSION, n_macros))
    A("")
    A("## 1. File-level facts of the returned workbooks")
    A("")
    A("| File | parts | docProps | zip entry dates | x: prefix | random r:ids | empty sharedStrings |")
    A("|---|---|---|---|---|---|---|")
    for name, f in list(audit_facts.items()) + [("Suite_Sample_Check_returned.xlsx", anno_facts)] + \
            list(field_facts.items()):
        A("| {} | {} | {} | {} | {} | {} | {} |".format(name, f["parts"], f["docprops"],
                                                       ", ".join(f["zip_dates"]), f["x_prefix"],
                                                       f["random_rids"], f["shared_strings_empty"]))
    A("")
    A("Workbooks as sent, for comparison:")
    A("")
    A("| File | parts | docProps | zip entry dates | x: prefix |")
    A("|---|---|---|---|---|")
    for name, f in sent_facts.items():
        A("| {} | {} | {} | {} | {} |".format(name, f["parts"], f["docprops"],
                                             ", ".join(f["zip_dates"]), f["x_prefix"]))
    A("")
    A("## 2. Content checks of the returns")
    A("")
    A("Practitioner audit: every returned workbook has the sent sheets, header, drop-down lists, "
      "case order (C01 to C30) and read-only cells; every rating cell is filled and inside its "
      "list (scales are integers 1 to 4, dispositions are apply, reject or refer); no cell lies "
      "outside the sent range. The scorer reported no problem. {} comments were written (of 300 "
      "possible), {} comment texts occur more than once.".format(n_comments, len(dup_texts)))
    A("")
    A("Panel-member pairs with identical ratings on every field of every case: {}.".format(
        ", ".join("{}-{}".format(a, b) for a, b in full_identical) or "none"))
    A("")
    A("| Field | identical ratings per panel-member pair (of 30): R1-R2, R1-R3, R1-R4, R1-R5, R2-R3, "
      "R2-R4, R2-R5, R3-R4, R3-R5, R4-R5 |")
    A("|---|---|")
    for s in SCALES + ["disposition"]:
        vals = [pair_identical[(s, a, b)] for i, a in enumerate(RATERS) for b in RATERS[i + 1:]]
        A("| {} | {} |".format(SCALE_NAME.get(s, s), ", ".join(str(v) for v in vals)))
    A("")
    A("Stage A comments that use a word Stage A does not show (Stage B or key vocabulary): "
      "{}.".format(len(comment_hits)))
    for rater, lab, hits, txt in comment_hits:
        A("- {} {} [{}]: {}".format(rater, lab, ", ".join(hits), txt))
    A("")
    A("Second annotator: sheets, header, drop-down list, row order and all read-only cells (A to "
      "K) equal the sent workbook; every pre-filled n.a. is kept; no applicable cell is marked "
      "n.a.; every verdict is inside its list; the overall verdict follows Q1 to Q4 on every row; "
      "every defect carries a note. {} distinct note texts over {} defect rows.".format(
          anno["distinct_notes"], anno["overall"]["defect"]))
    if anno_outside:
        A("")
        A("Annotator notes that cite material not in the annotator's workbook: " + "; ".join(
            "{} ('{}')".format(i, w) for i, w in anno_outside) + ".")
    A("")
    A("## 3. Which gate output the panel rated")
    A("")
    A("Stage B outcomes as sent: {} 'Applied with certificate', {} 'Referred with price', {} "
      "'Blocked with findings'. Every V3 case shows 'Referred with price'. Example, C23 (V3-01):"
      .format(out_counts["Applied with certificate"], out_counts["Referred with price"],
              out_counts["Blocked with findings"]))
    A("")
    A("> {} / {}".format(quote_row[3], quote_row[4]))
    A("")
    A("The gate's actual v1.2 terminal by class, and the cases on which it equals the suite "
      "disposition: " + "; ".join("{}: {} ({} of 6 equal)".format(
          c, ", ".join("{} {}".format(k, v) for k, v in sorted(
              first["guard_terminals_by_class"][c].items())),
          first["guard_equals_suite_by_class"][c]) for c in CLASSES) + ".")
    A("")
    A("## 4. Stage A and Stage B, pooled, per class, per register")
    A("")
    A("| Set | cases | Realism | Fidelity | Understandable | Actionable | Agree with suite | "
      "Withhold when refer | Agree with gate |")
    A("|---|---|---|---|---|---|---|---|---|")
    sets = [("All", M["pooled"])] + [(c, M["by_class"][c]) for c in CLASSES] + \
        [("V4 visible (referred)", M["by_pool"]["V4_visible"]),
         ("V4 neutral (applied)", M["by_pool"]["V4_neutral"])] + \
        [(g, M["by_register"][g]) for g in REGISTERS]
    for name, b in sets:
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            name, b["n_cases"], fmt_s(b["realism"]), fmt_s(b["fidelity"]), fmt_s(b["clarity"]),
            fmt_s(b["action"]), fmt_s(b["agree_suite"]), fmt_s(b["withhold_when_refer"]),
            fmt_s(b["agree_guard"])))
    A("")
    A("| Set | apply | reject | refer |")
    A("|---|---|---|---|")
    for name, b in sets[:8]:
        A("| {} | {} | {} | {} |".format(name, fmt_s(b["share_apply"]), fmt_s(b["share_reject"]),
                                         fmt_s(b["share_refer"])))
    A("")
    A("Stage B by the gate outcome shown:")
    A("")
    A("| Gate outcome | cases | Understandable | Actionable | Realism | Fidelity | Agree with suite |")
    A("|---|---|---|---|---|---|---|")
    for o in OUTCOMES:
        b = M["by_outcome"][o]
        A("| {} | {} | {} | {} | {} | {} | {} |".format(o, b["n_cases"], fmt_s(b["clarity"]),
                                                       fmt_s(b["action"]), fmt_s(b["realism"]),
                                                       fmt_s(b["fidelity"]), fmt_s(b["agree_suite"])))
    A("")
    A("Mean raw rating (1 to 4) over 150: " + ", ".join(
        "{} {:.2f}".format(SCALE_NAME[s], raw_means[s]) for s in SCALES) + ".")
    A("")
    A("Derived, not pre-specified: fidelity judgements that match the suite's reading of the "
      "candidate (positive on benign and V3, whose candidate is the gold operations; negative on "
      "V4, V5 and V6, whose candidate is the trap, an arbitrary resolution or the injected "
      "operations): {} of 150 ({:.1f}%).".format(first["fidelity_matches_suite_reading"],
                                                  100 * first["fidelity_matches_suite_reading"] / 150))
    A("")
    A("## 5. Four-of-five counts (cases)")
    A("")
    A("| Set | n | Realism | Fidelity | Understandable | Actionable | Panel disposition | "
      "Suite disposition | Gate disposition |")
    A("|---|---|---|---|---|---|---|---|---|")
    for name, b in [sets[0]] + sets[1:6] + sets[8:]:
        f = b["four"]
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            name, b["n_cases"], f["realism"], f["fidelity"], f["clarity"], f["action"],
            f["panel_disposition"], f["suite_disposition"], f["guard_disposition"]))
    A("")
    for k, v in first["below"].items():
        A("- below the rule on {}: {} cases ({})".format(k, len(v), ", ".join(v)))
    A("- distinct cases below on realism, suite disposition or fidelity: {}".format(
        len(first["below_stage_a_distinct"])))
    A("")
    A("## 6. Per panel member")
    A("")
    A("| Panel member | Realism + | Fidelity + | Understandable + | Actionable + | apply | reject | "
      "refer | = suite | = gate | means (R, F, U, A) |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in RATERS:
        d = per_rater[r]
        A("| {} | {}/30 | {}/30 | {}/30 | {}/30 | {} | {} | {} | {}/30 | {}/30 | {:.2f}, {:.2f}, "
          "{:.2f}, {:.2f} |".format(r, d["realism_pos"], d["fidelity_pos"], d["clarity_pos"],
                                    d["action_pos"], d["apply"], d["reject"], d["refer"],
                                    d["agree_suite"], d["agree_guard"], d["realism_mean"],
                                    d["fidelity_mean"], d["clarity_mean"], d["action_mean"]))
    A("")
    A("Rating distributions (counts of 1, 2, 3, 4):")
    A("")
    A("| Panel member | Realism | Fidelity | Understandable | Actionable |")
    A("|---|---|---|---|---|")
    for r in RATERS:
        d = per_rater[r]
        A("| {} | {} |".format(r, " | ".join("/".join(str(d[s + "_dist"][c]) for c in (1, 2, 3, 4))
                                            for s in SCALES)))
    A("")
    A("Per panel member and class (positive counts of 6; dispositions of 6):")
    A("")
    A("| Panel member | Class | Realism | Fidelity | Understandable | Actionable | = suite | apply | "
      "reject | refer |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in RATERS:
        for c in CLASSES:
            d = per_rater[r]["by_class"][c]
            A("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                r, c, d["realism"], d["fidelity"], d["clarity"], d["action"], d["agree_suite"],
                d["apply"], d["reject"], d["refer"]))
    A("")
    A("## 7. Inter-rater agreement (5 raters, 30 cases)")
    A("")
    g = agree["disposition"]
    A("Dispositions: Fleiss' kappa {:.3f} [{:.3f}, {:.3f}] (P-bar {:.4f}, P-e {:.4f}); "
      "Krippendorff's alpha (nominal) {:.3f} [{:.3f}, {:.3f}].".format(
          g["fleiss"], g["fleiss_lo"], g["fleiss_hi"], g["po"], g["pe"], g["alpha_nominal"],
          g["alpha_lo"], g["alpha_hi"]))
    A("")
    A("| Scale | Fleiss, positive vs not | Fleiss, four nominal points | Krippendorff alpha, ordinal |")
    A("|---|---|---|---|")
    for s in SCALES:
        g = agree[s]
        A("| {} | {:.3f} [{:.3f}, {:.3f}] (P-bar {:.3f}, P-e {:.3f}) | {:.3f} (P-bar {:.3f}, P-e "
          "{:.3f}) | {:.3f} [{:.3f}, {:.3f}] |".format(
              SCALE_NAME[s], g["fleiss2"], g["fleiss2_lo"], g["fleiss2_hi"], g["po2"], g["pe2"],
              g["fleiss4"], g["po4"], g["pe4"], g["alpha_ordinal"], g["alpha_lo"], g["alpha_hi"]))
    A("")
    A("Formulas: Fleiss' kappa = (P-bar - P-e)/(1 - P-e) with P_i = (sum_j n_ij^2 - n)/(n(n-1)) and "
      "P-e = sum_j p_j^2; Krippendorff's alpha = 1 - D_o/D_e from the coincidence matrix, nominal "
      "or ordinal distance. Kappa and alpha intervals use the pooled bootstrap indices (key 0).")
    A("")
    A("## 8. Per-case design effects and unanimity")
    A("")
    A("Design effects (per-case definition): " + ", ".join(
        "{} {:.2f}".format(k, v) for k, v in first["deff"].items()) + ".")
    A("")
    A("| Register | cases | all five chose the suite disposition | mean choosing it | "
      "not unanimous with suite | all five chose the same disposition |")
    A("|---|---|---|---|---|---|")
    for gg in REGISTERS:
        A("| {} | 10 | {} | {:.2f} | {} | {} |".format(
            gg, first["unanimous_suite"][gg], first["mean_agree"][gg],
            first["nonunanimous_suite"][gg], first["unanimous_panel"][gg]))
    A("")
    A("Cases whose single most chosen disposition equals the gate's actual disposition: {} of "
      "30; equals the suite disposition: {} of 30. The gate's disposition equals the suite "
      "disposition on {} of 30 cases.".format(first["modal_equals_guard"],
                                             first["modal_equals_suite"],
                                             first["guard_equals_suite_cases"]))
    A("")
    A("## 9. Case table")
    A("")
    A("| Case | Label | Class | Register | Gate outcome | Suite | Gate | apply/reject/refer | "
      "Realism+ | Fidelity+ | Understandable+ | Actionable+ |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        c = r["counts"]
        A("| {} | {} | {} | {} | {} | {} | {} | {}/{}/{} | {} | {} | {} | {} |".format(
            r["case"], r["label"], r["pool"], r["register"], r["outcome"], r["suite"], r["guard"],
            c["apply"], c["reject"], c["refer"], r["pos"]["realism"], r["pos"]["fidelity"],
            r["pos"]["clarity"], r["pos"]["action"]))
    A("")
    A("## 10. Panel profiles")
    A("")
    A("| Panel member | Role | Years | Approves changes | CMMS |")
    A("|---|---|---|---|---|")
    for i, r in enumerate(RATERS):
        A("| {} | {} | {:g} | {} | {} |".format(r, panel["roles"][i], panel["years"][i],
                                              panel["freq"][i], panel["cmms_text"][i]))
    A("")
    A("Years: minimum {:g}, median {:g}, maximum {:g} (mean {:.1f}). At least five years: {} of 5. "
      "Approve work-order changes at least weekly: {} of 5 (daily {}, weekly {}, never {}). Use "
      "a CMMS: {} of 5.".format(panel["years_min"], panel["years_median"], panel["years_max"],
                                panel["years_mean"], panel["years_at_least_five"],
                                panel["approve_weekly_or_more"], panel["approve_daily"],
                                panel["approve_weekly"], panel["approve_never"], panel["cmms"]))
    A("")
    A("## 11. Second annotator")
    A("")
    A("Profile: " + "; ".join("{}: {}".format(k, v) for k, v in anno_prof.items()) + ".")
    A("")
    o = anno["overall"]
    A("Rows checked: {}. Overall verdict OK {} and defect {}; agreement with the suite's label "
      "{}/{} = {:.1f}% (Wilson 95% {:.1f} to {:.1f}). Cohen's kappa against the suite's label: "
      "{:.3f}, zero by construction because the suite's label is OK on every row.".format(
          anno["rows"], o["ok"], o["defect"], o["ok"], o["n"], 100 * o["p"], 100 * o["lo"],
          100 * o["hi"], o["kappa"]))
    A("")
    A("| Field | OK | defect | n.a. | agreement (applicable rows) | Cohen's kappa |")
    A("|---|---|---|---|---|---|")
    for q in QUESTIONS:
        d = anno["by_question"][q]
        A("| {} | {} | {} | {} | {}/{} = {:.1f}% [{:.1f}, {:.1f}] | {:.3f} (by construction) |"
          .format(q, d["ok"], d["defect"], d["na"], d["ok"], d["n"], 100 * d["p"], 100 * d["lo"],
                  100 * d["hi"], d["kappa"]))
    A("| Overall | {} | {} | 0 | {}/{} = {:.1f}% [{:.1f}, {:.1f}] | {:.3f} (by construction) |".format(
        o["ok"], o["defect"], o["ok"], o["n"], 100 * o["p"], 100 * o["lo"], 100 * o["hi"],
        o["kappa"]))
    A("")
    A("| Class | rows | OK | defect | agreement | Q1 defects | Q2 defects | Q3 defects | Q4 defects |")
    A("|---|---|---|---|---|---|---|---|---|")
    for c in ANNO_CLASSES:
        d = anno["by_class"][c]
        A("| {} | {} | {} | {} | {:.1f}% [{:.1f}, {:.1f}] | {} | {} | {} | {} |".format(
            c, d["rows"], d["ok"], d["defect"], 100 * d["p"], 100 * d["lo"], 100 * d["hi"],
            *[d["q_defects"][q] for q in QUESTIONS]))
    A("")
    dc = anno["direction_check"]
    ex = anno["agree_excl_direction"]
    A("Post hoc. {} rows (every benign row) carry the note that column K, headed 'Mutation (twin "
      "to this item)', runs from this item to the twin; on {} of them it is the only note. "
      "Checked against suite.jsonl on the benign rows: the recorded mutation runs from this item "
      "to the twin on {}, from the twin to this item on {}, and a text match does not decide {}; "
      "on the violation rows with a twin it runs from the twin to this item on {}, the other way "
      "on {}, undecided {}. If the direction-only rows counted as OK, agreement would be {}/{} = "
      "{:.1f}% [{:.1f}, {:.1f}]."
      .format(anno["direction_any"], anno["direction_only"], dc.get("benign:this_to_twin", 0),
              dc.get("benign:twin_to_this", 0), dc.get("benign:not_decidable_by_text", 0),
              dc.get("violation:twin_to_this", 0), dc.get("violation:this_to_twin", 0),
              dc.get("violation:not_decidable_by_text", 0), ex["ok"], ex["n"],
              100 * ex["p"], 100 * ex["lo"], 100 * ex["hi"]))
    A("")
    A("### Disagreements (suite's label OK on every field; the annotator's label below)")
    A("")
    A("| Item | Class | Subclass | Q1 | Q2 | Q3 | Q4 | Overall | Note |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in anno_rows:
        if r["overall"] == "defect":
            A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                r["item"], r["cls"], r["subclass"], r["Q1"], r["Q2"], r["Q3"], r["Q4"],
                r["overall"], r["note"].replace("\n", " ").replace("|", "/")))
    A("")
    A("## 12. Self-test (second code path)")
    A("")
    A("| Quantity | first path | second path |")
    A("|---|---|---|")
    for name, a, b in st_log:
        A("| {} | {} | {} |".format(name, a, b))
    A("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as e:
        print("N22 FAILED: {}".format(e), file=sys.stderr)
        raise SystemExit(1)
