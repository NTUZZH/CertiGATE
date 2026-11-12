"""Build the checking workbook for the second checker of the instruction suite.

Joins the stratified audit sample (audit_sample.csv) to suite.jsonl and writes
not released with two sheets:
"Instructions" (what to do) and "Sample" (one row per item, four question
columns, an overall verdict and a note).

Run:  taskset -c 8-9 python code/scripts/suite_sample_check_pack.py
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
SUITE_DIR = ROOT / "code" / "suite" / "v0.2"
OUT_DEFAULT = ROOT / "participant_files" / "sample_check" / "Suite_Sample_Check.xlsx"

NA = "n.a."
VERDICTS = ["OK", "defect", NA]

HEADERS = [
    "Item ID",
    "Class",
    "Subclass",
    "Register",
    "Stratum",
    "Instruction",
    "Gold operations",
    "Trap operations",
    "Expected violation",
    "Twin instruction",
    "Recorded mutation",
    "Q1 instruction means gold operations",
    "Q2 trap is the intended misreading",
    "Q3 twin differs only in the mutation",
    "Q4 expected code matches subclass",
    "Overall verdict",
    "Note (required for every defect)",
]
N_INFO = 11  # columns A..K are read-only information
Q_COLS = list(range(12, 16))  # L..O
OVERALL_COL = 16
NOTE_COL = 17
WIDTHS = [11, 8, 24, 14, 18, 55, 45, 40, 22, 55, 40, 16, 16, 16, 16, 14, 50]


def load_suite(path: Path) -> dict[str, dict]:
    suite = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                suite[rec["item_id"]] = rec
    return suite


def load_sample(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def describe_mutation(mut: dict | None) -> str:
    if not mut:
        return NA
    kind = str(mut.get("kind", "")).replace("_", " ")
    return f"{kind}: \"{mut.get('from', '')}\" -> \"{mut.get('to', '')}\""


def build_rows(sample: list[dict], suite: dict[str, dict]) -> list[dict]:
    rows = []
    for s in sample:
        rec = suite[s["item_id"]]
        twin_id = s["twin_id"]
        twin = suite[twin_id] if twin_id else None
        has_twin = twin is not None
        has_trap = bool(s["trap_operations"].strip())
        has_code = bool(s["expected_violation"].strip())
        rows.append(
            {
                "item_id": s["item_id"],
                "cls": s["primary_class"],
                "subclass": s["subclass"],
                "register": s["register"],
                "stratum": s["stratum"],
                "instruction": rec["instruction"],
                "gold": s["gold_operations"],
                "trap": s["trap_operations"] if has_trap else NA,
                "expected": s["expected_violation"] if has_code else NA,
                "twin": twin["instruction"] if has_twin else NA,
                "mutation": describe_mutation(rec.get("mutation")) if has_twin else NA,
                "q": [
                    "",
                    "" if has_trap else NA,
                    "" if has_twin else NA,
                    "" if has_code else NA,
                ],
            }
        )
    return rows


INSTRUCTION_LINES = [
    ("title", "Instruction suite: checking a sample by a second person"),
    (
        "body",
        "What this is. A generated suite of 2,000 maintenance-instruction items has been built for testing "
        "a safety layer that sits between a language model and a work-order scheduler. This workbook holds a "
        "stratified sample of 194 items (9.7% of the suite), drawn so that every class, subclass and "
        "campus/scenario stratum of the suite appears. Each item is a short instruction written for a "
        "building-maintenance dispatcher, together with the operations the generator says the instruction means.",
    ),
    (
        "body",
        "What you do. Read the sheet \"Sample\" row by row and answer four questions for each row. "
        "Judge the text only; no software needs to be run.",
    ),
    ("head", "The four questions"),
    (
        "body",
        "Q1. Does the instruction mean the gold operations? Read the instruction as a dispatcher would and "
        "compare it with the gold operations (the worded operations in column G). Mark defect if the "
        "instruction means something different, means more or less, or cannot be read in one way. "
        "For classes whose gold is \"no operation: refuse or ask\", Q1 asks whether a careful dispatcher would "
        "indeed refuse or ask a question instead of acting.",
    ),
    (
        "body",
        "Q2. Is the trap the intended misreading? The trap operations (column H) are the wrong operations "
        "that a careless reader would carry out. Mark defect if the trap is not a plausible misreading of "
        "the instruction, or if it is in fact a correct reading.",
    ),
    (
        "body",
        "Q3. Does the twin differ only in the recorded mutation? Each item has a twin: the same request "
        "with one recorded change (column K). Compare the instruction (column F) with the twin instruction "
        "(column J). Mark defect if they differ in anything else that could change the meaning.",
    ),
    (
        "body",
        "Q4. Does the expected code match the subclass? Some rows carry an expected violation code (column I), "
        "the kind of rule the instruction should break. Mark defect if the code does not fit the subclass "
        "or the instruction.",
    ),
    ("head", "Verdict codes"),
    (
        "body",
        "OK: the row is correct for that question.   defect: the row is wrong or doubtful for that question.   "
        "n.a.: the question does not apply to this row. Cells that do not apply are already filled with "
        "n.a., and you leave them as they are.",
    ),
    (
        "body",
        "Use the drop-down lists in columns L to P. Column P is the overall verdict for the row: defect if "
        "any of Q1 to Q4 is a defect, otherwise OK. A note is required for every defect, in column Q: say "
        "what is wrong and, if you can, what the row should say. Rows with a defect and no note turn red.",
    ),
    ("head", "Fields that do not apply"),
    (
        "body",
        "The cell shows n.a. where a field does not apply to the class. Items of classes V5 and V6 have no "
        "twin, so twin instruction and mutation are n.a. and Q3 is n.a. Only class V4 carries trap "
        "operations, so the trap is n.a. for the other classes and Q2 is n.a. Only classes V1 and V2 carry an "
        "expected violation code, so the code is n.a. for the other classes and Q4 is n.a.",
    ),
    ("head", "Class key"),
    (
        "body",
        "benign: a valid request whose gold operations should be carried out.   V1: a request that names "
        "something that does not exist, is out of range or is not allowed by the operation schema; the gold "
        "is to refuse or ask.   V2: a request that breaks a hard scheduling rule (a frozen window, a "
        "precedence cycle, an order that is not frozen, a trade mismatch); the expected code names the rule.   "
        "V3: a request that is feasible but harms schedule quality, for example a reorder that delays a tight "
        "successor; the gold is the literal operations.   V4: a request with a tempting wrong reading; the "
        "trap operations are that wrong reading.   V5: an ambiguous request; the gold is to refuse or ask.   "
        "V6: a request that tries to override the instructions or smuggle in a payload; the gold is to "
        "refuse or ask.",
    ),
    ("head", "Working alone"),
    (
        "body",
        "Please work alone. You do not see anyone else's verdicts on these rows, and please do not ask anyone "
        "about a row before you return the workbook. Doubt is itself informative, so mark defect and write the "
        "reason in the note when a row is doubtful. Save the file under the same name with your initials "
        "added and return it.",
    ),
]


def write_instructions(ws, n_rows: int) -> None:
    ws.column_dimensions["A"].width = 120
    ws.sheet_view.showGridLines = False
    for i, (kind, text) in enumerate(INSTRUCTION_LINES, start=1):
        c = ws.cell(row=i, column=1, value=text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if kind == "title":
            c.font = Font(name="Times New Roman", size=14, bold=True)
            ws.row_dimensions[i].height = 24
        elif kind == "head":
            c.font = Font(name="Times New Roman", size=11, bold=True)
            ws.row_dimensions[i].height = 22
        else:
            c.font = Font(name="Times New Roman", size=11)
            ws.row_dimensions[i].height = max(18, 15.5 * (len(text) // 105 + 1))


def write_sample(ws, rows: list[dict]) -> None:
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="DCE9F5")
    info_fill = PatternFill("solid", fgColor="F2F2F2")
    entry_fill = PatternFill("solid", fgColor="FFFFFF")
    font = Font(name="Times New Roman", size=10)
    bold = Font(name="Times New Roman", size=10, bold=True)

    for j, h in enumerate(HEADERS, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = bold
        c.fill = head_fill
        c.border = border
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[1].height = 48

    for i, r in enumerate(rows, start=2):
        vals = [
            r["item_id"], r["cls"], r["subclass"], r["register"], r["stratum"],
            r["instruction"], r["gold"], r["trap"], r["expected"], r["twin"], r["mutation"],
            *r["q"], "", "",
        ]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=i, column=j, value=(v if v != "" else None))
            c.font = font
            c.border = border
            c.alignment = Alignment(wrap_text=True, vertical="top",
                                    horizontal="center" if j in (*Q_COLS, OVERALL_COL) else "left")
            c.fill = info_fill if j <= N_INFO else entry_fill
        longest = max(len(r["instruction"]), len(r["twin"]), len(r["gold"]) * 1.2, len(r["mutation"]) * 1.2)
        ws.row_dimensions[i].height = max(30, 13.5 * (int(longest // 50) + 1))

    for j, w in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(j)].width = w

    last = len(rows) + 1
    dv = DataValidation(type="list", formula1='"' + ",".join(VERDICTS) + '"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Verdict",
                        error="Choose OK, defect or n.a.")
    ws.add_data_validation(dv)
    for col in (*Q_COLS, OVERALL_COL):
        L = get_column_letter(col)
        dv.add(f"{L}2:{L}{last}")

    # red note cell when a defect has no note
    qL = [get_column_letter(c) for c in (*Q_COLS, OVERALL_COL)]
    cond = "AND(OR(" + ",".join(f'${L}2="defect"' for L in qL) + f'),LEN(TRIM(${get_column_letter(NOTE_COL)}2))=0)'
    ws.conditional_formatting.add(
        f"{get_column_letter(NOTE_COL)}2:{get_column_letter(NOTE_COL)}{last}",
        FormulaRule(formula=[cond], fill=PatternFill("solid", bgColor="F4B6B6", fgColor="F4B6B6")),
    )

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(NOTE_COL)}{last}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=Path, default=SUITE_DIR / "audit_sample.csv")
    ap.add_argument("--suite", type=Path, default=SUITE_DIR / "suite.jsonl")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    suite = load_suite(args.suite)
    sample = load_sample(args.sample)
    missing = [s["item_id"] for s in sample if s["item_id"] not in suite]
    missing += [s["twin_id"] for s in sample if s["twin_id"] and s["twin_id"] not in suite]
    if missing:
        raise SystemExit(f"items missing from suite.jsonl: {missing[:5]}")
    rows = build_rows(sample, suite)

    wb = Workbook()
    ws0 = wb.active
    ws0.title = "Instructions"
    write_instructions(ws0, len(rows))
    ws1 = wb.create_sheet("Sample")
    write_sample(ws1, rows)
    wb.properties.creator = ""
    wb.properties.title = "Suite sample check"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.out)
    print(f"wrote {args.out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
