"""Score a returned Suite_Sample_Check workbook.

Counts verdicts per question and per class, lists every defect with its note,
and reports agreement with the reference pass in which every row is OK
(agreement = share of rows the second checker also marks OK), overall and per
class, with Wilson 95% intervals. Cohen's kappa against that reference is
reported where defined. Against a reference that is constant, kappa is 0 when
the checker marks at least one defect and undefined when the checker marks
every row OK; the script says so instead of printing a number.

Run:  taskset -c 8-9 python code/scripts/suite_sample_check_score.py RETURNED.xlsx
"""

from __future__ import annotations

import argparse
import collections
import math
from pathlib import Path

from openpyxl import load_workbook

QUESTIONS = ["Q1", "Q2", "Q3", "Q4"]
CLASS_ORDER = ["benign", "V1", "V2", "V3", "V4", "V5", "V6"]


def norm(v) -> str:
    if v is None:
        return ""
    t = str(v).strip().lower()
    return {"ok": "OK", "defect": "defect", "n.a.": "n.a.", "na": "n.a.", "n/a": "n.a."}.get(t, t)


def read_workbook(path: Path) -> list[dict]:
    wb = load_workbook(path, data_only=True)
    if "Sample" not in wb.sheetnames:
        raise SystemExit("sheet 'Sample' not found")
    ws = wb["Sample"]
    header = [str(c.value or "").strip() for c in ws[1]]

    def col(prefix: str) -> int:
        for i, h in enumerate(header):
            if h.startswith(prefix):
                return i
        raise SystemExit(f"column starting with {prefix!r} not found")

    idx = {"item_id": col("Item ID"), "cls": col("Class"), "subclass": col("Subclass"),
           "overall": col("Overall verdict"), "note": col("Note")}
    for q in QUESTIONS:
        idx[q] = col(q)
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[idx["item_id"]]:
            continue
        rec = {k: r[i] for k, i in idx.items()}
        for k in QUESTIONS + ["overall"]:
            rec[k] = norm(rec[k])
        rec["note"] = (str(rec["note"]).strip() if rec["note"] else "")
        rows.append(rec)
    return rows


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cohen_kappa(ref: list[str], chk: list[str]) -> float | None:
    n = len(ref)
    if n == 0:
        return None
    labels = sorted(set(ref) | set(chk))
    po = sum(a == b for a, b in zip(ref, chk)) / n
    pe = sum((ref.count(l) / n) * (chk.count(l) / n) for l in labels)
    if abs(1 - pe) < 1e-12:
        return None
    return (po - pe) / (1 - pe)


def score(rows: list[dict]) -> dict:
    out: dict = {"n_rows": len(rows)}
    valid = {"OK", "defect", "n.a."}
    problems = []
    for r in rows:
        for k in QUESTIONS + ["overall"]:
            if r[k] == "":
                problems.append(f"{r['item_id']}: {k} is empty")
            elif r[k] not in valid:
                problems.append(f"{r['item_id']}: {k} has invalid value {r[k]!r}")
        if r["overall"] == "n.a.":
            problems.append(f"{r['item_id']}: overall verdict must be OK or defect")
        has_def = "defect" in [r[q] for q in QUESTIONS] or r["overall"] == "defect"
        if has_def and not r["note"]:
            problems.append(f"{r['item_id']}: defect without a note")
        if any(r[q] == "defect" for q in QUESTIONS) and r["overall"] == "OK":
            problems.append(f"{r['item_id']}: a question is a defect but overall is OK")
    out["problems"] = problems

    # per question
    per_q = {}
    for q in QUESTIONS:
        c = collections.Counter(r[q] for r in rows)
        per_q[q] = {"OK": c["OK"], "defect": c["defect"], "n.a.": c["n.a."], "blank": c[""]}
    out["per_question"] = per_q

    # per class (overall verdict and per question)
    classes = [c for c in CLASS_ORDER if any(r["cls"] == c for r in rows)]
    classes += sorted({r["cls"] for r in rows} - set(classes))
    per_class = {}
    for cl in classes:
        sub = [r for r in rows if r["cls"] == cl]
        d = {"rows": len(sub),
             "overall_OK": sum(r["overall"] == "OK" for r in sub),
             "overall_defect": sum(r["overall"] == "defect" for r in sub),
             "overall_blank": sum(r["overall"] == "" for r in sub)}
        for q in QUESTIONS:
            d[q + "_OK"] = sum(r[q] == "OK" for r in sub)
            d[q + "_defect"] = sum(r[q] == "defect" for r in sub)
        per_class[cl] = d
    out["per_class"] = per_class

    # agreement with the all-OK reference
    scored = [r for r in rows if r["overall"] in ("OK", "defect")]
    k = sum(r["overall"] == "OK" for r in scored)
    out["agreement"] = {"k": k, "n": len(scored), "p": (k / len(scored) if scored else float("nan")),
                        "ci": wilson(k, len(scored))}
    out["agreement_by_class"] = {}
    for cl in classes:
        sub = [r for r in scored if r["cls"] == cl]
        kk = sum(r["overall"] == "OK" for r in sub)
        out["agreement_by_class"][cl] = {"k": kk, "n": len(sub),
                                         "p": (kk / len(sub) if sub else float("nan")),
                                         "ci": wilson(kk, len(sub))}
    out["agreement_by_question"] = {}
    for q in QUESTIONS:
        sub = [r for r in rows if r[q] in ("OK", "defect")]
        kk = sum(r[q] == "OK" for r in sub)
        out["agreement_by_question"][q] = {"k": kk, "n": len(sub),
                                           "p": (kk / len(sub) if sub else float("nan")),
                                           "ci": wilson(kk, len(sub))}
    ref = ["OK"] * len(scored)
    chk = [r["overall"] for r in scored]
    out["kappa"] = cohen_kappa(ref, chk)
    out["kappa_by_class"] = {}
    for cl in classes:
        sub = [r["overall"] for r in scored if r["cls"] == cl]
        out["kappa_by_class"][cl] = cohen_kappa(["OK"] * len(sub), sub) if sub else None

    out["defects"] = [
        {"item_id": r["item_id"], "cls": r["cls"], "subclass": r["subclass"],
         "questions": [q for q in QUESTIONS if r[q] == "defect"], "overall": r["overall"], "note": r["note"]}
        for r in rows if r["overall"] == "defect" or any(r[q] == "defect" for q in QUESTIONS)
    ]
    return out


def fmt_p(a: dict) -> str:
    if a["n"] == 0:
        return "n/a"
    lo, hi = a["ci"]
    return f"{a['k']}/{a['n']} = {100 * a['p']:.1f}% (95% CI {100 * lo:.1f} to {100 * hi:.1f})"


def fmt_kappa(k, n_def: int) -> str:
    if k is None:
        return "undefined (the checker marked every row OK, so both raters are constant)"
    return f"{k:.3f}" + (" (zero by construction: the reference is constant)" if n_def else "")


def report(res: dict) -> str:
    L = []
    L.append(f"Rows read: {res['n_rows']}")
    if res["problems"]:
        L.append(f"\nPROBLEMS ({len(res['problems'])}):")
        L += [f"  {p}" for p in res["problems"]]
    L.append("\nVerdicts per question")
    L.append(f"  {'':4s}{'OK':>6s}{'defect':>8s}{'n.a.':>6s}{'blank':>7s}")
    for q, d in res["per_question"].items():
        L.append(f"  {q:4s}{d['OK']:6d}{d['defect']:8d}{d['n.a.']:6d}{d['blank']:7d}")
    L.append("\nVerdicts per class (overall; then defects per question)")
    L.append(f"  {'class':8s}{'rows':>5s}{'OK':>5s}{'defect':>8s}{'blank':>7s}   Q1 Q2 Q3 Q4 defects")
    for cl, d in res["per_class"].items():
        qs = " ".join(f"{d[q + '_defect']:2d}" for q in QUESTIONS)
        L.append(f"  {cl:8s}{d['rows']:5d}{d['overall_OK']:5d}{d['overall_defect']:8d}{d['overall_blank']:7d}   {qs}")
    L.append("\nAgreement with the reference pass (all rows OK)")
    L.append(f"  overall: {fmt_p(res['agreement'])}")
    for cl, a in res["agreement_by_class"].items():
        L.append(f"  {cl:8s}: {fmt_p(a)}")
    L.append("  by question (rows where the question applies):")
    for q, a in res["agreement_by_question"].items():
        L.append(f"  {q:8s}: {fmt_p(a)}")
    n_def = res["agreement"]["n"] - res["agreement"]["k"]
    L.append(f"\nCohen's kappa against the reference, overall: {fmt_kappa(res['kappa'], n_def)}")
    for cl, k in res["kappa_by_class"].items():
        a = res["agreement_by_class"][cl]
        L.append(f"  {cl:8s}: {fmt_kappa(k, a['n'] - a['k']) if a['n'] else 'n/a'}")
    L.append(f"\nDefects ({len(res['defects'])} rows)")
    for d in res["defects"]:
        qs = ",".join(d["questions"]) or "-"
        L.append(f"  {d['item_id']} [{d['cls']}/{d['subclass']}] questions: {qs}; overall: {d['overall'] or 'blank'}")
        L.append(f"      note: {d['note'] or '(none)'}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook", type=Path)
    args = ap.parse_args()
    print(report(score(read_workbook(args.workbook))))


if __name__ == "__main__":
    main()
