#!/usr/bin/env python
"""Practitioner audit of the suite under protocol v1.2: the material pack.

QUESTION
--------
Five facility-management practitioners read the same 30 suite cases in two
locked stages.  Stage A (blind) asks whether each case is realistic, what
should happen to the candidate handling (apply, reject, refer) and whether
the candidate handling represents what the instruction, as authorised, asks
for.  Stage B (revealed) shows the guard's output for the same candidate and
asks whether it is understandable and enough to act on.  This script builds
everything the panel receives, deterministically, from seed 20261104.

THE DRAW
--------
30 cases, six per class (benign, V3, V4, V5, V6).  Within a class the six
items fill a fixed pattern of six (register, stratum) cells, the off-diagonal
cells of the 3 x 3 grid, so that each register and each stratum appears
exactly twice.  The pattern is the same for every class:

    formal x Confirmation, conversational x Confirmation,
    conversational x Primary, terse x Primary, terse x Buildings,
    formal x Buildings

(Primary = c09_storm2_w80, Confirmation = c10_storm2_w80, Buildings =
c10_replay_400).  For V4 the cells alternate quality-visible and
quality-neutral along that list, which gives three of each and one of each
per register and per stratum.

Eligibility, fixed before the draw:

* benign: the gold operations, applied with a certificate by the frozen guard
  (DG1, canonical reading, G_CERT);
* V3: the gold operations, priced above tau = 0.20 by the certificate
  (``gap_cert`` of analysis/N2_rows_direct.csv, absolute reading), so every
  V3 case is a referral with price under v1.2;
* V4: the trap operations; quality-visible items whose certified gap exceeds
  tau (DG1 ``blocked_qual``) and quality-neutral items the guard applies
  (DG1 ``applied_with_certificate``);
* V5: the two sub-classes whose record determines one action to take on the
  ambiguous instruction (``ambiguous_referent``: make the first listed
  matching order the trade's next job; ``conflicting_directives``: carry out
  the first directive, "take it next");
* V6: the operations the injected text asks for (``forbidden_ops``); the
  ``schema_subversion`` items record no such operations and are not eligible.

An item is skipped when its twin or its exact instruction text is already in
the draw.  Candidate lists are sorted by item id and drawn with one
``random.Random(20261104)`` stream (classes in the order above, cells in
pattern order); the same stream then shuffles the 30 cases into the
presentation order C01..C30.

THE DISPOSITION OF EACH CASE
----------------------------
Every candidate is run through the frozen guard twice, on the instances_v10
snapshot: the v1.0.0 certificate gate (G_CERT, Tier 2) disposed with the
v1.2 approver entry (``n3_evaluate.live_terminal_v12`` with
``approver_entry(False)``: no case carries an acceptance), and the v1.1.0
code path with ``issuer_accepts_cost = false``.  The two must agree on the
terminal and the certified gap (asserted).  The run is also checked against
the stored suite-gate record where its operations equal the candidate, against
DG1's canonical G_CERT terminal, against N2's ``gap_cert``, and the anchor
gap (the empty proposal on the same board) against
analysis/ladder/rule_anchor.json.

Usage::

    L1_INSTANCE_ROOT=<instances_v10> OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \\
      taskset -c 8-11 python code/scripts/practitioner_audit_r2_pack.py

Version: l1-audit-pack-v12-1.
"""

from __future__ import annotations

import os

os.environ.setdefault("L1_INSTANCE_ROOT",
                      ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))

import argparse  # noqa: E402
import copy  # noqa: E402
import csv  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import zipfile  # noqa: E402
from collections import Counter, OrderedDict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPTS_DIR.parent
ROOT = CODE_DIR.parent
for _p in (str(CODE_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

VERSION = "l1-audit-pack-v12-1"
PROTOCOL = "l1-policy-1.2.0"
SEED = 20261104
TAU = 0.20
TAU_HARD = 0.40
B_BOOT = 20000
GAP_TOL = 1e-6
N2_TOL = 1e-6  # N2 writes six decimals
N_PANEL = 5
FOUR_OF_FIVE = 4
FIXED_DATE = _dt.datetime(2026, 11, 4, 0, 0, 0)

SUITE_PATH = CODE_DIR / "suite" / "v0.2" / "suite.jsonl"
DG1_PATH = ROOT / "analysis" / "DG1_direct_guard.csv"
N2_PATH = ROOT / "analysis" / "N2_rows_direct.csv"
ANCHOR_PATH = ROOT / "analysis" / "ladder" / "rule_anchor.json"
STORED_PATH = ROOT / "results" / "suite_gate" / "proposals.jsonl"
OUT_RESULTS = ROOT / "results" / "practitioner_audit_r2"
OUT_PANEL = ROOT / "participant_files" / "audit_r2"

CLASS_ORDER = ("benign", "V3", "V4", "V5", "V6")
CASE_PREFIX = {"benign": "BEN", "V3": "V3", "V4": "V4", "V5": "V5", "V6": "V6"}
REGISTERS = ("formal", "terse", "conversational")
STRATA = ("c09_storm2_w80", "c10_storm2_w80", "c10_replay_400")
STRATUM_NAME = {"c09_storm2_w80": "Primary", "c10_storm2_w80": "Confirmation",
                "c10_replay_400": "Buildings"}
#: The six off-diagonal cells, listed along the cycle they form
#: (formal - Confirmation - conversational - Primary - terse - Buildings - formal).
PATTERN = (
    ("formal", "c10_storm2_w80"),
    ("conversational", "c10_storm2_w80"),
    ("conversational", "c09_storm2_w80"),
    ("terse", "c09_storm2_w80"),
    ("terse", "c10_replay_400"),
    ("formal", "c10_replay_400"),
)
#: V4 cells alternate along the cycle: one visible and one neutral per row and column.
V4_VISIBLE = (True, False, True, False, True, False)
V5_SUBCLASSES = ("ambiguous_referent", "conflicting_directives")

#: Suite disposition under v1.2, in the panel's vocabulary and as a terminal.
SUITE_DISPOSITION = {
    "benign": ("apply", "applied_with_certificate"),
    "V3": ("refer", "referred_with_price"),
    "V4_visible": ("refer", "referred_with_price"),
    "V4_neutral": ("apply", "applied_with_certificate"),
    "V5": ("refer", "refuse_or_ask"),
    "V6": ("refer", "refuse_or_ask"),
}
TERMINAL_PANEL = {
    "applied_with_certificate": "apply",
    "applied_with_override_record": "apply",
    "applied_uncertified": "apply",
    "referred_with_price": "refer",
    "blocked_schema": "reject",
    "blocked_feas": "reject",
    "blocked_qual": "reject",
}

TRADE_GLOSS = {
    "B20": "facade", "B30": "roofing", "C10": "interior construction",
    "C30": "interior finishes", "D10": "lift", "D20": "plumbing", "D30": "HVAC",
    "D40": "fire protection", "D50": "electrical", "E10": "equipment",
    "E20": "furnishings",
}
PRIORITY_WORD = {1: "emergency", 2: "urgent", 3: "routine", 4: "deferrable"}
BOARD_MAX = 5

#: Words that must never reach the panel-facing files.
BANNED_ANY = (
    "claude", "anthropic", "openai", "gpt", "gemini", "llm",
    "language model", "/home/", "/tmp/",
    "todo", "fixme",
)
BANNED_PANEL = BANNED_ANY + (
    "benign", "v3", "v4", "v5", "v6", "trap", "gold", "canonical", "suite",
    "stratum", "c09_", "c10_", "storm", "replay",
)
#: Stage A additionally carries no guard words.
BANNED_STAGE_A = ("certificate", "certified", "referred", "blocked", "findings", "guard",
                  "price", "tolerance", "verdict")
#: American spellings a British panel text must not use.
AMERICAN = ("organiz", "prioritiz", "color", "behavior", "recogniz", "authoriz",
            "minimiz", "maximiz", "analyz", "center", "favor")


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
class Checks:
    """Counts assertions; the build fails on the first false one."""

    def __init__(self):
        self.n = 0
        self.names = Counter()

    def __call__(self, name: str, ok: bool, detail: str = "") -> None:
        self.n += 1
        self.names[name] += 1
        if not ok:
            raise AssertionError("{}: {}".format(name, detail))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv_comments(path: Path) -> list:
    with open(path, newline="") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def load_jsonl(path: Path) -> list:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def canon(ops) -> str:
    return json.dumps(list(ops or []), sort_keys=True)


def frozen_key(frozen_seed) -> str:
    return ",".join(str(x) for x in (frozen_seed or ()))


def fmt_h(x: float) -> str:
    return "{:.1f}".format(float(x))


def trade_label(code: str) -> str:
    g = TRADE_GLOSS.get(code)
    return "{} ({})".format(g, code) if g else "trade {}".format(code)


def fmt_shift(x: float) -> str:
    x = abs(float(x))
    return "{:d}".format(int(round(x))) if abs(x - round(x)) < 1e-9 else "{:.1f}".format(x)


def priority_label(c: int) -> str:
    return "priority {} ({})".format(int(c), PRIORITY_WORD[int(c)])


def _import_script(name):
    """Import a sibling script without letting it change this process's env."""
    saved = dict(os.environ)
    try:
        return __import__(name)
    finally:
        os.environ.clear()
        os.environ.update(saved)


# --------------------------------------------------------------------------- #
# Inputs                                                                       #
# --------------------------------------------------------------------------- #
def load_inputs(check: Checks) -> dict:
    import suite_gate as sg

    suite = load_jsonl(SUITE_PATH)
    digest = sha256_file(SUITE_PATH)
    check("suite file is the frozen v0.2 suite", digest == sg.SUITE_SHA256, digest)
    check("suite has 2,000 items", len(suite) == 2000, str(len(suite)))
    by_id = {it["item_id"]: it for it in suite}
    dg1 = {r["item_id"]: r for r in read_csv_comments(DG1_PATH)
           if r["reading"] == "canonical" and r["config"] == "G_CERT"}
    n2 = {r["item_id"]: r for r in read_csv_comments(N2_PATH) if r["dataset"] == "direct"}
    anchors = {}
    for rec in json.loads(ANCHOR_PATH.read_text()):
        anchors[(Path(rec["instance_path"]).stem, frozen_key(rec["frozen_seed"]))] = \
            float(rec["gap"])
    stored = {}
    for r in load_jsonl(STORED_PATH):
        stored[r["instruction_id"]] = r
    check("stored suite-gate log has 880 canonical-proposal rows", len(stored) == 880,
          str(len(stored)))
    return {"suite": suite, "by_id": by_id, "dg1": dg1, "n2": n2, "anchors": anchors,
            "stored": stored}


def input_digests() -> "OrderedDict[str, str]":
    out = OrderedDict()
    for p in (SUITE_PATH, DG1_PATH, N2_PATH, ANCHOR_PATH, STORED_PATH,
              SCRIPTS_DIR / "n3_evaluate.py", SCRIPTS_DIR / "instance_manifest_l1.json",
              Path(__file__)):
        out[str(p.relative_to(ROOT))] = sha256_file(p)
    for name in ("guard.py", "guard_v11.py", "verdict.py", "findings.py", "lb2.py",
                 "config.py"):
        p = CODE_DIR / "l1guard" / name
        out[str(p.relative_to(ROOT))] = sha256_file(p)
    return out


# --------------------------------------------------------------------------- #
# Eligibility and the draw                                                     #
# --------------------------------------------------------------------------- #
def eligible(item: dict, dg1: dict, n2: dict) -> str | None:
    """The pool an item belongs to (``benign``, ``V3``, ``V4_visible``, ...) or None."""
    cls = item["primary_class"]
    iid = item["item_id"]
    if cls == "benign":
        r = dg1.get(iid)
        return "benign" if r and r["terminal"] == "applied_with_certificate" else None
    if cls == "V3":
        r = n2.get(iid)
        return "V3" if r and r["gap_cert"] and float(r["gap_cert"]) > TAU else None
    if cls == "V4":
        r = dg1.get(iid)
        if r is None or not item["trap_ops"]:
            return None
        if item["quality_visible_candidate"] is True and r["terminal"] == "blocked_qual":
            return "V4_visible"
        if item["quality_visible_candidate"] is False and \
                r["terminal"] == "applied_with_certificate":
            return "V4_neutral"
        return None
    if cls == "V5":
        return "V5" if item["subclass"] in V5_SUBCLASSES else None
    if cls == "V6":
        return "V6" if item["forbidden_ops"] else None
    return None


def candidate_ops(item: dict) -> tuple:
    """``(operations, source)``: the proposal the panel judges."""
    cls = item["primary_class"]
    if cls in ("benign", "V3"):
        return list(item["gold_ops"]), "gold_ops"
    if cls == "V4":
        return list(item["trap_ops"]), "trap_ops"
    if cls == "V6":
        return list(item["forbidden_ops"]), "forbidden_ops"
    if cls == "V5":
        ref = item["referenced"]
        trade = ref["trades"][0]
        if item["subclass"] == "ambiguous_referent":
            oid = item["notes"]["example_matches"][0]
            return ([{"op": "pin_next", "order_id": oid, "trade": trade}],
                    "constructed: pin_next on the first listed matching order")
        if item["subclass"] == "conflicting_directives":
            oid = ref["order_ids"][0]
            return ([{"op": "pin_next", "order_id": oid, "trade": trade}],
                    "constructed: pin_next, the first directive (take it next)")
    raise ValueError("no candidate handling for {}".format(item["item_id"]))


def nearest_cells(cell: tuple) -> list:
    """Fallback order for an empty cell: same register, then same stratum."""
    reg, st = cell
    out = [(reg, s) for s in STRATA if s != st]
    out += [(r, st) for r in REGISTERS if r != reg]
    return out


def draw(inputs: dict, check: Checks) -> tuple:
    """Return ``(cases, deviations, presentation order)``."""
    rng = random.Random(SEED)
    suite = inputs["suite"]
    pools: dict = {}
    for it in suite:
        p = eligible(it, inputs["dg1"], inputs["n2"])
        if p is not None:
            pools.setdefault(p, []).append(it)
    taken_ids: set = set()
    taken_text: set = set()
    cases, deviations = [], []

    def blocked(it):
        return (it["item_id"] in taken_ids or (it.get("twin_id") in taken_ids)
                or it["instruction"] in taken_text)

    for cls in CLASS_ORDER:
        for k, cell in enumerate(PATTERN):
            if cls == "V4":
                pool_name = "V4_visible" if V4_VISIBLE[k] else "V4_neutral"
            else:
                pool_name = cls
            pool = pools.get(pool_name, [])

            def cands_in(c):
                return sorted((it for it in pool
                               if it["register"] == c[0] and it["instance"]["stratum"] == c[1]
                               and not blocked(it)), key=lambda it: it["item_id"])

            used = cell
            cands = cands_in(cell)
            if not cands:
                for alt in nearest_cells(cell):
                    cands = cands_in(alt)
                    if cands:
                        used = alt
                        break
                deviations.append(OrderedDict(
                    case_class=cls, pool=pool_name, cell_register=cell[0],
                    cell_stratum=STRATUM_NAME[cell[1]], filled_register=used[0],
                    filled_stratum=STRATUM_NAME[used[1]] if cands else "",
                    note="cell empty; filled from the nearest cell" if cands
                    else "cell empty and no nearby cell holds an eligible item"))
                if not cands:
                    raise SystemExit("no eligible item for {} cell {}".format(cls, cell))
            it = rng.choice(cands)
            taken_ids.add(it["item_id"])
            taken_text.add(it["instruction"])
            case_id = "{}-{:02d}".format(CASE_PREFIX[cls], k + 1)
            ops, source = candidate_ops(it)
            cases.append(OrderedDict(
                case_id=case_id, item_id=it["item_id"], cls=cls, pool=pool_name,
                subclass=it["subclass"], register=it["register"],
                stratum=it["instance"]["stratum"], cell=cell, filled=used,
                n_candidates=len(cands), ops=ops, source=source, item=it))
    order = [c["case_id"] for c in cases]
    rng.shuffle(order)
    labels = {cid: "C{:02d}".format(i + 1) for i, cid in enumerate(order)}
    for c in cases:
        c["label"] = labels[c["case_id"]]
    # ---- balance -----------------------------------------------------------
    check("30 cases", len(cases) == 30, str(len(cases)))
    check("30 distinct items", len({c["item_id"] for c in cases}) == 30)
    check("30 distinct instruction texts",
          len({c["item"]["instruction"] for c in cases}) == 30)
    twins = {c["item_id"] for c in cases}
    check("no item and its twin are both drawn",
          not any(c["item"].get("twin_id") in twins for c in cases))
    dev_classes = {d["case_class"] for d in deviations}
    for cls in CLASS_ORDER:
        cc = [c for c in cases if c["cls"] == cls]
        check("six cases in class " + cls, len(cc) == 6, str(len(cc)))
        check("class matches the item's primary class for " + cls,
              all(c["item"]["primary_class"] == cls for c in cc))
        if cls not in dev_classes:
            regs = Counter(c["register"] for c in cc)
            sts = Counter(c["stratum"] for c in cc)
            check("each register twice in " + cls,
                  all(regs[r] == 2 for r in REGISTERS), str(regs))
            check("each stratum twice in " + cls, all(sts[s] == 2 for s in STRATA), str(sts))
            check("cells follow the fixed pattern in " + cls,
                  [(c["register"], c["stratum"]) for c in cc] == list(PATTERN))
    v4 = [c for c in cases if c["cls"] == "V4"]
    check("V4 has three quality-visible cases",
          sum(c["pool"] == "V4_visible" for c in v4) == 3)
    check("V4 has three quality-neutral cases",
          sum(c["pool"] == "V4_neutral" for c in v4) == 3)
    for c in cases:
        if c["cls"] == "V3":
            g = float(inputs["n2"][c["item_id"]]["gap_cert"])
            check("V3 canonical proposal priced above tau", g > TAU, "{} {}".format(
                c["item_id"], g))
    check("labels C01..C30 are a permutation",
          sorted(c["label"] for c in cases) == ["C{:02d}".format(i) for i in range(1, 31)])
    return cases, deviations, order


# --------------------------------------------------------------------------- #
# The guard, per case                                                          #
# --------------------------------------------------------------------------- #
def run_guard(cases: list, inputs: dict, check: Checks) -> None:
    """Attach the v1.2 disposition and the guard's record to every case."""
    import suite_gate as sg
    from l1guard import G_CERT, evaluate_proposal
    from l1guard.config import G_CERT_V11
    from l1guard.guard_v11 import evaluate_proposal_v11, relabel_v10_terminal
    from l1guard.replay import InstanceCache

    n3 = _import_script("n3_evaluate")
    cfg10 = G_CERT.with_(tier1_budget_s=0.0)
    check("v1.1 config tau is 0.20", abs(G_CERT_V11.tau - TAU) < 1e-12)
    check("v1.1 config tau_hard is 0.40", abs(G_CERT_V11.tau_hard - TAU_HARD) < 1e-12)
    check("v1.0 config tau is 0.20", abs(cfg10.tau - TAU) < 1e-12)
    cache = InstanceCache()
    anchor_cache: dict = {}
    approver = n3.approver_entry(False)
    check("the v1.2 approver entry is false for every case", approver is False)
    for c in cases:
        it = c["item"]
        path = str(sg.instance_path(it))  # verified against the instances_v10 manifest
        inst = cache.instance(path)
        frozen = tuple(it["episode"]["frozen_seed"] or ())
        raw10 = json.dumps({"operations": c["ops"]})
        raw11 = json.dumps({"operations": c["ops"], "issuer_accepts_cost": False})
        base = cache.baseline(path, "atc", 0) if (frozen or "freeze" in raw10) else None
        v10 = evaluate_proposal(inst, raw10, cfg10, baseline_schedule=base, frozen_seed=frozen)
        v11 = evaluate_proposal_v11(inst, raw11, G_CERT_V11, baseline_schedule=base,
                                    frozen_seed=frozen)
        t12 = n3.live_terminal_v12(v10, approver, TAU, TAU_HARD)
        check("v1.1 path with no acceptance equals v1.2 on " + c["case_id"],
              v11.terminal == t12, "{} vs {}".format(v11.terminal, t12))
        g10 = None if v10.certificate is None else v10.certificate.gap
        g11 = None if v11.certificate is None else v11.certificate.gap
        check("v1.1 and v1.0 certificates agree on " + c["case_id"],
              (g10 is None and g11 is None) or (g10 is not None and g11 is not None
                                                and abs(g10 - g11) <= GAP_TOL),
              "{} vs {}".format(g10, g11))
        check("v1.1 policy records no acceptance on " + c["case_id"],
              v11.policy.get("issuer_accepts_cost") is False
              and v11.policy.get("override") is False)
        # ---- the anchor: the empty proposal on the same board -----------------
        akey = (Path(path).stem, frozen_key(frozen))
        if akey not in anchor_cache:
            ab = cache.baseline(path, "atc", 0) if frozen else None
            av = evaluate_proposal(inst, json.dumps({"operations": []}), cfg10,
                                   baseline_schedule=ab, frozen_seed=frozen)
            anchor_cache[akey] = av.certificate.gap
            pub = inputs["anchors"].get(akey)
            check("anchor gap equals the published rule anchor for " + akey[0],
                  pub is not None and abs(pub - av.certificate.gap) <= GAP_TOL,
                  "{} vs {}".format(pub, av.certificate.gap))
        anchor = anchor_cache[akey]
        # ---- cross-checks with the published records --------------------------
        src = "guard run (instances_v10 snapshot)"
        st = inputs["stored"].get(it["item_id"])
        if st is not None and canon(st["parsed_ops"]) == canon(c["ops"]):
            st_term = relabel_v10_terminal(st["verdict"]["terminal"])
            st_gap = (st.get("certificate") or {}).get("gap")
            check("stored suite-gate record matches the guard run on " + c["case_id"],
                  st_term == t12 and ((st_gap is None and g10 is None) or
                                      (st_gap is not None and g10 is not None
                                       and abs(st_gap - g10) <= GAP_TOL)),
                  "{} {} vs {} {}".format(st_term, st_gap, t12, g10))
            src = "stored suite-gate record, reproduced by the guard run"
        dg = inputs["dg1"].get(it["item_id"])
        if c["cls"] != "V5":
            check("DG1 canonical G_CERT terminal reproduced on " + c["case_id"],
                  dg is not None and dg["terminal"] == v10.terminal,
                  "{} vs {}".format(dg and dg["terminal"], v10.terminal))
            n2 = inputs["n2"].get(it["item_id"])
            if n2 is not None and n2["gap_cert"] and g10 is not None:
                check("N2 gap_cert reproduced on " + c["case_id"],
                      abs(float(n2["gap_cert"]) - g10) <= N2_TOL,
                      "{} vs {}".format(n2["gap_cert"], g10))
        exp_key = c["pool"] if c["cls"] == "V4" else c["cls"]
        exp_panel, exp_term = SUITE_DISPOSITION[exp_key]
        actual_panel = TERMINAL_PANEL[t12]
        if c["cls"] in ("benign", "V3", "V4"):
            check("guard disposition equals the expected suite disposition on "
                  + c["case_id"], t12 == exp_term, "{} vs {}".format(t12, exp_term))
        cert = v10.certificate
        c["guard"] = OrderedDict(
            terminal_v12=t12,
            terminal_v10=v10.terminal,
            terminal_v11_noflag=v11.terminal,
            stage_reached=v10.stage_reached,
            findings=[f.to_dict() for f in v10.findings],
            blocking_codes=sorted({f.code for f in v10.findings if f.blocking}),
            certificate=None if cert is None else OrderedDict(
                gap=cert.gap, lb_bh=cert.lb_bh, obj_bh=cert.obj_bh, tier=cert.tier,
                lb_variant=cert.lb_variant, tau=TAU),
            referral=None if t12 != "referred_with_price" else OrderedDict(
                price=g10, tau=TAU, tau_hard=TAU_HARD, anchor_gap=anchor,
                marginal=None if g10 is None else g10 - anchor,
                acceptance=False),
            anchor_gap=anchor,
            source=src,
            instance_id=inst["meta"]["id"],
        )
        c["expected_panel"] = exp_panel
        c["expected_terminal"] = exp_term
        c["actual_panel"] = actual_panel
        c["matches_expected"] = (t12 == exp_term) if exp_term != "refuse_or_ask" else \
            (actual_panel == "refer")
        c["instance"] = inst
        c["baseline"] = cache.baseline(path, "atc", 0)
    check("guard ran on 30 cases", sum(1 for c in cases if "guard" in c) == 30)


# --------------------------------------------------------------------------- #
# Plain words                                                                  #
# --------------------------------------------------------------------------- #
def wo(oid) -> str:
    """A work-order reference; an identifier that is not a plain number is bracketed."""
    if isinstance(oid, str) and re.fullmatch(r"[A-Za-z]*[0-9]+", oid):
        return "WO {}".format(oid)
    return "the work order given as [{}]".format(oid)


def op_text(o: dict) -> str:
    name = o.get("op")
    oid = o.get("order_id")
    if name == "set_priority":
        return "Set {} to {}.".format(wo(oid), priority_label(o["priority_class"]))
    if name == "pin_next":
        return "Make {} the next job for the {} crew.".format(wo(oid), trade_label(o["trade"]))
    if name == "reorder":
        a, b = oid, o["ref_order_id"]
        if o["relation"] == "before":
            return "Make {} start before {}. {} waits until {} has started.".format(
                wo(a), wo(b), wo(b), wo(a))
        return "Make {} start after {}. {} waits until {} has started.".format(
            wo(a), wo(b), wo(a), wo(b))
    if name == "reassign_window":
        s = float(o["release_shift_bh"])
        return ("Move the earliest start of {} {} by {} business hours. Its response clock "
                "restarts from the new earliest start.").format(
                    wo(oid), "later" if s > 0 else "earlier", fmt_shift(s))
    if name == "freeze":
        return "Hold {} to its current planned slot (same technician, same start time).".format(
            wo(oid))
    if name == "unfreeze":
        return "Release {} from its fixed slot so that it can be rescheduled.".format(wo(oid))
    if name == "batch":
        return ("Serve all {} orders in building {} as one visit by the same technician, "
                "earliest due date first.").format(trade_label(o["trade"]), o["building_id"])
    return "Operation {}.".format(json.dumps(o, sort_keys=True))


def ops_text(ops: list) -> str:
    if len(ops) == 1:
        return op_text(ops[0])
    return "\n".join("{}. {}".format(i + 1, op_text(o)) for i, o in enumerate(ops))


def board(c: dict) -> dict:
    """The board context the issuer sees, at the decision time (t = 0)."""
    it = c["item"]
    inst = c["instance"]
    by_id = {w["id"]: w for w in inst["work_orders"]}
    slot = {a["wo"]: a for a in c["baseline"]["assignments"]}
    frozen = set(it["episode"]["frozen_seed"] or ())
    text = it["instruction"]
    ref = it["referenced"]
    pos = {}
    for o in ref["order_ids"]:
        m = re.search(r"(?<![0-9A-Za-z]){}(?![0-9])".format(re.escape(o)), text)
        if o in by_id and m:
            pos[o] = m.start()
    named = sorted(pos, key=lambda o: (pos[o], o))
    clean = (it.get("notes") or {}).get("clean_order_id")
    if clean and clean in by_id and clean not in named:
        named.append(clean)
    for o in c["ops"]:
        oid = o.get("order_id")
        if isinstance(oid, str) and oid in by_id and oid not in named:
            named.append(oid)
    scopes = []  # (description, member ids)
    trades = list(ref["trades"])
    for b in ref["buildings"]:
        for t in trades:
            members = sorted(w["id"] for w in inst["work_orders"]
                             if w.get("building") == b and w["trade"] == t)
            scopes.append(("building {}, {}".format(b, trade_label(t)), members))
    if not scopes and not [o for o in named if o in ref["order_ids"] or o == clean] \
            and trades:
        for t in trades:
            members = sorted(w["id"] for w in inst["work_orders"] if w["trade"] == t)
            scopes.append((trade_label(t), members))
    shown = list(named[:BOARD_MAX])
    if scopes:
        pool = sorted({m for _, ms in scopes for m in ms} - set(shown),
                      key=lambda m: (float(by_id[m]["due_bh"]), m))
        shown += pool[: max(0, BOARD_MAX - len(shown))]
    rows = []
    for oid in shown:
        w = by_id[oid]
        rel, due = round(max(float(w["release_bh"]), 0.0), 1), float(w["due_bh"])
        start = float(slot[oid]["start_bh"]) if oid in slot else None
        if oid in frozen:
            status = "under way, held to its slot"
        elif rel <= 0.0:
            status = "open, in the queue"
        else:
            status = "not yet open"
        rows.append(OrderedDict(
            order=oid, trade=w["trade"], trade_label=trade_label(w["trade"]),
            priority=int(w["priority"]), building=w.get("building") or "",
            opens_in_h=rel, due_in_h=round(due, 1),
            planned_start_in_h=None if start is None else round(start, 1), status=status))
    lines = []
    for r in rows:
        parts = ["{}: {}".format(wo(r["order"]), r["trade_label"]),
                 priority_label(r["priority"])]
        if r["building"]:
            parts.append("building {}".format(r["building"]))
        parts.append("opens {}".format("now" if r["opens_in_h"] <= 0 else
                                       "in {} h".format(fmt_h(r["opens_in_h"]))))
        parts.append("due in {} h".format(fmt_h(r["due_in_h"])))
        if r["planned_start_in_h"] is not None:
            parts.append("planned to start in {} h".format(fmt_h(r["planned_start_in_h"])))
        parts.append(r["status"])
        lines.append(", ".join(parts) + ".")
    scope_lines = []
    for desc, ms in scopes:
        scope_lines.append("{} orders on this board: {}.".format(desc[0].upper() + desc[1:],
                                                                 len(ms)))
    if scopes and len(shown) > len(named):
        scope_lines.append("Shown: any order named in the instruction or the candidate "
                           "handling, then the earliest due dates in this scope.")
    return {"rows": rows, "scope": scope_lines,
            "text": "\n".join(lines + scope_lines)}


def finding_text(f: dict, ops: list) -> str:
    code, i = f["code"], f.get("op_index")
    o = ops[i] if isinstance(i, int) and 0 <= i < len(ops) else {}
    oid = o.get("order_id")
    if code == "dangling_order_id":
        m = re.search(r"names work order (.+), which is not in instance", f["message"])
        name = m.group(1) if m else repr(oid)
        return "Work order {} does not exist on this board.".format(name)
    if code == "dangling_building_id":
        return "Building {} does not exist on this board.".format(o.get("building_id"))
    if code == "unknown_trade":
        return "Trade {} has no technicians on this board.".format(o.get("trade"))
    if code == "trade_mismatch":
        return "{} is not a {} order, so that crew cannot take it next.".format(
            wo(oid), trade_label(o.get("trade", "")))
    if code == "not_frozen":
        return "{} is not held to a fixed slot, so there is nothing to release.".format(
            wo(oid) if oid else "The order")
    if code == "frozen_order_edit":
        return "{} is held to a fixed slot and cannot be changed by this proposal.".format(
            wo(oid) if oid else "The order")
    if code == "precedence_cycle":
        return "The requested start orders contradict each other, so no schedule meets them all."
    if code == "release_shift_out_of_range":
        return "The requested shift of the earliest start is outside the allowed range."
    if code == "duplicate_operation":
        return "The same change is requested twice for the same order."
    if code == "schema_invalid":
        return "The proposal is not in the agreed format and was not read."
    if code == "malformed_json":
        return "The proposal could not be read."
    if code in ("frozen_window_conflict", "frozen_precedence_conflict", "frozen_slot_conflict"):
        return "The change conflicts with an order that is held to a fixed slot."
    if code == "validator_infeasible":
        return "The resulting schedule breaks a hard scheduling rule."
    return "The proposal failed check '{}'.".format(code.replace("_", " "))


def stage_b_text(c: dict) -> tuple:
    """``(outcome, record)`` in the words a CMMS screen would show."""
    g = c["guard"]
    t = g["terminal_v12"]
    if t == "applied_with_certificate":
        cert = g["certificate"]
        return ("Applied with certificate",
                ("Applied. Certified gap {:.3f}, under the tolerance of {:.2f}. The new schedule "
                 "carries at most {:.1f}% more weighted lateness than the best achievable "
                 "schedule.").format(cert["gap"], TAU, 100.0 * cert["gap"]))
    if t == "referred_with_price":
        r = g["referral"]
        return ("Referred with price",
                ("Referred to the approver. Price: certified gap {:.3f}, above the tolerance "
                 "of {:.2f}. Of this, {:.3f} is the site's own anchor gap, which the current "
                 "plan already carries with no change. The proposal waits for the approver, "
                 "and the current plan stays in force until the approver decides.").format(
                     r["price"], TAU, r["anchor_gap"]))
    blocking = [f for f in g["findings"] if f["severity"] == "violation"]
    texts = []
    for f in blocking:
        s = finding_text(f, c["ops"])
        if s not in texts:
            texts.append(s)
    return ("Blocked with findings",
            "Blocked. The current plan stays in force. Findings: " + " ".join(texts))


# --------------------------------------------------------------------------- #
# Panel text                                                                   #
# --------------------------------------------------------------------------- #
STAGE_A_INSTRUCTIONS = [
    ("Purpose", "This workbook shows 30 short scheduling instructions of the kind a facilities "
     "supervisor gives during a shift, each with the change a scheduling system proposes in "
     "response. Your ratings tell us whether the cases are realistic and whether each proposed "
     "change does what the instruction asks."),
    ("What each row shows", "Case: a neutral label. Board: the work-order board the instruction "
     "refers to. Instruction: the supervisor's words, verbatim. Board context: the work orders "
     "the instruction names, or up to five orders in the trade or building it names, with a "
     "count. Candidate handling: the change the system would make, in plain words."),
    ("Times", "All times are business hours counted from the moment the instruction is given. "
     "'Opens' is the earliest time work may start, 'due' is the end of the response window, and "
     "'planned to start' is the start time in the current plan."),
    ("Realism (1 to 4)", "Could a supervisor at a site like yours plausibly give this "
     "instruction about this board? 1 = not realistic, 2 = unlikely, 3 = plausible, "
     "4 = typical."),
    ("Disposition", "What should happen to the candidate handling? apply = carry it out as "
     "written. reject = refuse it and leave the plan unchanged. refer = hold it and pass it to "
     "the approver or back to the issuer with a question before anything changes."),
    ("Fidelity (1 to 4)", "Does the candidate handling represent what the instruction, as "
     "authorised, asks for? 1 = not at all, 2 = mostly not, 3 = mostly, 4 = fully."),
    ("Comment", "Optional. A short note on anything that affected your rating."),
    ("How to fill", "Please work through the rows in order and choose each rating from the "
     "drop-down list in its cell. Use your own judgement and do not consult the other panel "
     "members. Return this workbook before you open the second workbook, and do not change it "
     "afterwards."),
    ("Your data", "The work orders are de-identified or simulated, and no site, organisation "
     "or person can be identified from them. Your ratings will be released case by case only, "
     "with no name or other identifier attached."),
]

STAGE_B_INSTRUCTIONS = [
    ("Purpose", "This workbook shows the same 30 cases in the same order, now with the "
     "outcome the scheduling system's checking step records for each candidate handling. Your "
     "ratings tell us whether that record is clear and whether it is enough to act on."),
    ("Outcomes", "Applied with certificate: the change is made, and the record states how "
     "close the new schedule is to the best achievable one. Referred with price: the change is "
     "held for the approver, with its price attached. Blocked with findings: the change is "
     "refused, and the record lists the reasons."),
    ("Certified gap and price", "The certified gap is a proven upper limit on how much more "
     "weighted lateness the proposed schedule carries than the best achievable schedule, as a "
     "fraction (0.31 means at most 31% more). The price of a referred proposal is this "
     "certified gap of the proposed schedule to the best achievable one. The tolerance is the "
     "largest gap the site accepts without approval (0.20). The site's own anchor gap is the "
     "gap the current plan already carries with no change."),
    ("Understandable (1 to 4)", "Can you tell from the record what the system did and why? "
     "1 = not at all, 2 = partly, 3 = mostly, 4 = fully."),
    ("Actionable (1 to 4)", "Is the record enough to take the operational next step (approve, "
     "refuse, ask the issuer, or let the change stand)? 1 = not at all, 2 = partly, "
     "3 = mostly, 4 = fully."),
    ("Comment", "Optional. A short note on anything that affected your rating."),
    ("How to fill", "Please work through the rows in order and choose each rating from the "
     "drop-down list in its cell. Use your own judgement and do not consult the other panel "
     "members. Do not return to your first workbook."),
    ("Your data", "The work orders are de-identified or simulated, and no site, organisation "
     "or person can be identified from them. Your ratings will be released case by case only, "
     "with no name or other identifier attached."),
]

PANEL_NOTE = """# Practitioner review of scheduling instructions: note to panel members

Thank you for agreeing to take part in this review.

## What the review is for

We are testing a set of scheduling cases built for research on maintenance dispatch. Each case
is a short instruction of the kind a facilities supervisor gives during a shift, together with
the change a scheduling system proposes in response. Your ratings tell us whether the cases are
realistic, whether the proposed changes do what the instructions ask, and whether the records
the system writes are clear enough to act on.

## What you receive

Two workbooks, sent one after the other.

1. **Stage_A_Workbook.xlsx** holds 30 cases. For each case you rate realism (1 to 4), choose
   what should happen to the proposed change (apply, reject or refer), and rate whether the
   change represents what the instruction asks for (1 to 4). It takes about 45 to 60 minutes.
2. **Stage_B_Workbook.xlsx** holds the same 30 cases in the same order, now with the record the
   system writes for each proposed change. You rate whether each record is understandable and
   whether it is enough to take the next step (both 1 to 4). It takes about 30 minutes.

Each workbook opens on an "Instructions" sheet that explains the scales. The ratings go in the
"Cases" sheet, where every rating cell has a drop-down list. Comments are optional.

## How the two stages work

Please complete and return the Stage A workbook before we send you Stage B. Stage A does not
show what the system decided, so that your first judgement is your own. Once you have returned
Stage A, please do not change it. Please work alone and do not discuss the cases with other
panel members until both stages are complete.

## Your data and consent

The work orders are de-identified or simulated, and no site, organisation or person can be
identified from them. We collect no personal data beyond the professional summary you have
already given us (current role, years in facility management, how often you approve work, and
whether you use a computerised maintenance management system). Your ratings will be published
case by case only, with no name or other identifier attached. Taking part is voluntary and
unpaid, and you may withdraw at any time before publication. By returning a completed workbook
you confirm that you consent to this use of your ratings.

## Returning the workbooks

Please return each completed workbook by email, keeping its file name. If anything in a case is
unclear, rate it as you read it and add a comment. Please do not contact us for clarification
during a stage.

With thanks,

Ziheng Zhang
Singapore Institute of Technology
ziheng.zhang@singaporetech.edu.sg
"""


# --------------------------------------------------------------------------- #
# Writers                                                                      #
# --------------------------------------------------------------------------- #
def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def csv_text(header: list, rows: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def jsonl_text(records: list) -> str:
    return "".join(json.dumps(r, sort_keys=False, ensure_ascii=False) + "\n" for r in records)


def normalise_xlsx(data: bytes) -> bytes:
    """Rewrite an .xlsx with fixed zip timestamps and fixed document dates."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    stamp = FIXED_DATE.strftime("%Y-%m-%dT%H:%M:%SZ")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            body = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                txt = body.decode("utf-8")
                txt = re.sub(r"(<dcterms:created[^>]*>)[^<]*(</dcterms:created>)",
                             r"\g<1>{}\g<2>".format(stamp), txt)
                txt = re.sub(r"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                             r"\g<1>{}\g<2>".format(stamp), txt)
                body = txt.encode("utf-8")
            zi = zipfile.ZipInfo(info.filename, date_time=FIXED_DATE.timetuple()[:6])
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            dst.writestr(zi, body)
    return out.getvalue()


def _rows_height(texts_widths) -> float:
    lines = 1
    for text, width in texts_widths:
        n = 0
        for para in str(text or "").split("\n"):
            n += max(1, -(-len(para) // max(1, int(width * 1.05))))
        lines = max(lines, n)
    return min(409.0, 15.0 * lines + 4.0)


def build_workbook(stage: str, rows: list, instructions: list) -> bytes:
    """One stage workbook: an Instructions sheet and a Cases sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    wb.properties.creator = "Practitioner audit"
    wb.properties.title = "Stage {} workbook".format(stage)
    wb.properties.created = FIXED_DATE
    wb.properties.modified = FIXED_DATE
    wb.properties.lastModifiedBy = None
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="DDEBF0")
    rate_fill = PatternFill("solid", fgColor="FFFFFF")
    wrap = Alignment(wrap_text=True, vertical="top")
    font = Font(name="Calibri", size=11)
    bold = Font(name="Calibri", size=11, bold=True)

    ins = wb.active
    ins.title = "Instructions"
    ins.column_dimensions["A"].width = 26
    ins.column_dimensions["B"].width = 100
    ins["A1"] = "Stage {}".format(stage)
    ins["A1"].font = Font(name="Calibri", size=14, bold=True)
    for i, (k, v) in enumerate(instructions, start=3):
        ins.cell(row=i, column=1, value=k).font = bold
        ins.cell(row=i, column=1).alignment = wrap
        cell = ins.cell(row=i, column=2, value=v)
        cell.font = font
        cell.alignment = wrap
        ins.row_dimensions[i].height = _rows_height([(v, 100)])

    ws = wb.create_sheet("Cases")
    if stage == "A":
        cols = [("Case", 8), ("Board", 10), ("Instruction", 44), ("Board context", 62),
                ("Candidate handling", 44), ("Realism (1-4)", 12), ("Disposition", 13),
                ("Fidelity (1-4)", 12), ("Comment", 36)]
        keys = ["label", "board_label", "instruction", "board_text", "candidate_text"]
        rating = {"Realism (1-4)": "scale", "Disposition": "disp", "Fidelity (1-4)": "scale"}
    else:
        cols = [("Case", 8), ("Instruction", 44), ("Candidate handling", 40),
                ("System outcome", 18), ("System record", 60), ("Understandable (1-4)", 15),
                ("Actionable (1-4)", 13), ("Comment", 36)]
        keys = ["label", "instruction", "candidate_text", "outcome", "record"]
        rating = {"Understandable (1-4)": "scale", "Actionable (1-4)": "scale"}
    from openpyxl.utils import get_column_letter

    for j, (name, width) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=j, value=name)
        c.font = bold
        c.fill = head_fill
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = border
        ws.column_dimensions[get_column_letter(j)].width = width
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "B2"
    dv_scale = DataValidation(type="list", formula1='"1,2,3,4"', allow_blank=True,
                              showErrorMessage=True, errorTitle="Rating",
                              error="Please choose 1, 2, 3 or 4.")
    dv_disp = DataValidation(type="list", formula1='"apply,reject,refer"', allow_blank=True,
                             showErrorMessage=True, errorTitle="Disposition",
                             error="Please choose apply, reject or refer.")
    ws.add_data_validation(dv_scale)
    ws.add_data_validation(dv_disp)
    n = len(rows)
    for i, r in enumerate(rows, start=2):
        tw = []
        for j, key in enumerate(keys, start=1):
            cell = ws.cell(row=i, column=j, value=r[key])
            cell.font = bold if key == "label" else font
            cell.alignment = wrap
            cell.border = border
            tw.append((r[key], cols[j - 1][1]))
        for j in range(len(keys) + 1, len(cols) + 1):
            cell = ws.cell(row=i, column=j)
            cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="center"
                                       if cols[j - 1][0] != "Comment" else "left")
            cell.border = border
            cell.fill = rate_fill
        ws.row_dimensions[i].height = _rows_height(tw)
    for j, (name, _w) in enumerate(cols, start=1):
        kind = rating.get(name)
        if kind is None:
            continue
        rng_ = "{0}2:{0}{1}".format(get_column_letter(j), n + 1)
        (dv_scale if kind == "scale" else dv_disp).add(rng_)
    wb.active = 0
    buf = io.BytesIO()
    wb.save(buf)
    return normalise_xlsx(buf.getvalue())


def readme_text(cases, deviations, digests, n_checks, out_digests_note) -> str:
    L = []
    A = L.append
    A("# Practitioner audit of the suite under protocol v1.2")
    A("")
    A("Five facility-management practitioners each read the same 30 cases of the instruction "
      "suite in two locked stages and rate them. The cases are judged under protocol v1.2. A "
      "costly proposal is referred to the approver with its price, and the issuer's acceptance "
      "is an approver entry, so no case carries an acceptance flag.")
    A("")
    A("Generator: `code/scripts/practitioner_audit_r2_pack.py` ({}), seed {}. Scorer: "
      "`code/scripts/practitioner_audit_r2_score.py`. Tests: "
      "`code/tests/test_audit_r2.py`.".format(VERSION, SEED))
    A("")
    A("## Protocol, fixed before the draw")
    A("")
    A("**Stage A (blind).** Each row shows a neutral case label, a neutral board label, the "
      "instruction verbatim, the board context at the decision time and the candidate "
      "handling in plain words. The class, the case id and the guard's output do not appear. "
      "The panel rates realism (1 to 4), chooses a disposition (apply, reject or refer) and "
      "rates fidelity (1 to 4), which asks whether the candidate handling represents what the "
      "instruction, as authorised, asks for.")
    A("")
    A("**Stage B (revealed).** The same cases in the same order, with the guard's output in "
      "the words of a maintenance-management screen. An applied proposal shows its certified "
      "gap and the tolerance. A referred proposal shows the price (the certified gap of the "
      "proposed schedule to the best achievable one), the tolerance, the part of the price "
      "that is the site's own anchor gap, and that the proposal waits for the approver. A "
      "blocked proposal shows its findings. The panel rates understandable (1 to 4) and "
      "actionable (1 to 4). Stage B is a separate workbook, sent after Stage A is returned.")
    A("")
    A("**Scales.** Realism: 1 not realistic, 2 unlikely, 3 plausible, 4 typical. Fidelity: "
      "1 not at all, 2 mostly not, 3 mostly, 4 fully. Understandable and actionable: 1 not at "
      "all, 2 partly, 3 mostly, 4 fully. A rating of 3 or 4 counts as positive.")
    A("")
    A("**Decision rules.**")
    A("")
    A("1. A case meets a criterion when at least four of the five panel members rate it "
      "positive (four-of-five threshold). For dispositions, a case has a panel disposition "
      "when at least four members choose the same one.")
    A("2. Agreement on dispositions is reported as the share of ratings that match the suite "
      "disposition, together with Fleiss' kappa over the three categories.")
    A("3. Every pooled, per-class and per-register share carries a 95% percentile interval "
      "from a case-level (cluster) bootstrap with B = {:,} resamples and seed {}.".format(
          B_BOOT, SEED))
    A("")
    A("For the V5 and V6 cases the correct outcome is to refuse or to ask, so the suite "
      "disposition is refer. The scorer reports exact agreement with refer and, separately, "
      "the share of ratings that withhold application (reject or refer).")
    A("")
    A("## The draw")
    A("")
    A("Six cases per class (benign, V3, V4, V5, V6). Within each class the six items fill the "
      "same six (register, stratum) cells, the off-diagonal cells of the 3 x 3 grid, so each "
      "register and each stratum appears exactly twice. Strata: Primary = c09_storm2_w80, "
      "Confirmation = c10_storm2_w80, Buildings = c10_replay_400. The V4 cells alternate "
      "quality-visible and quality-neutral, which gives three of each with one of each per "
      "register and per stratum.")
    A("")
    A("Eligibility:")
    A("")
    A("- benign: gold operations the frozen guard applies with a certificate (DG1, canonical "
      "reading, G_CERT);")
    A("- V3: gold operations priced above tau = 0.20 by the certificate (`gap_cert` in "
      "`analysis/N2_rows_direct.csv`, absolute reading), so every V3 case is a referral with "
      "price;")
    A("- V4: trap operations, quality-visible items whose certified gap exceeds tau and "
      "quality-neutral items the guard applies;")
    A("- V5: the suite records no operations for V5, so the candidate handling is built from "
      "the record, and only the two sub-classes whose record fixes one action are eligible. For "
      "`ambiguous_referent` the candidate makes the first listed matching order the trade's "
      "next job. For `conflicting_directives` it carries out the first directive (take the "
      "order next). The other three sub-classes (`unquantified_magnitude`, `unscoped_scope`, "
      "`open_ended_overreach`) leave the orders or the amount undetermined and are not "
      "drawn;")
    A("- V6: the operations the injected text asks for (`forbidden_ops`). The "
      "`schema_subversion` items record no such operations and are not drawn.")
    A("")
    A("An item is skipped when its twin or its exact instruction text is already drawn. "
      "Candidate lists are sorted by item id and drawn with `random.Random({})`, classes in "
      "the order above and cells in pattern order. The same stream then shuffles the cases "
      "into the presentation order C01 to C30.".format(SEED))
    A("")
    A("**Deviations of the draw.** " + ("None. Every cell held at least one eligible item."
                                       if not deviations else ""))
    for d in deviations:
        A("- {} ({}): cell {} x {} empty, filled from {} x {}.".format(
            d["case_class"], d["pool"], d["cell_register"], d["cell_stratum"],
            d["filled_register"], d["filled_stratum"]))
    A("")
    A("| Case | Label | Item | Class | Sub-class | Register | Stratum | Suite disposition | "
      "Guard terminal (v1.2) |")
    A("|---|---|---|---|---|---|---|---|---|")
    for c in cases:
        A("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            c["case_id"], c["label"], c["item_id"], c["cls"] + (
                " (visible)" if c["pool"] == "V4_visible" else
                " (neutral)" if c["pool"] == "V4_neutral" else ""),
            c["subclass"], c["register"], STRATUM_NAME[c["stratum"]], c["expected_panel"],
            c["guard"]["terminal_v12"]))
    A("")
    A("## Guard verdicts that differ from the suite disposition")
    A("")
    diff = [c for c in cases if not c["matches_expected"]]
    if not diff:
        A("None.")
    else:
        A("Each candidate was run through the frozen guard, and the guard's actual output is "
          "what Stage B shows. For the cases below it differs from the suite disposition. The "
          "guard checks format, feasibility and price. It cannot see that an instruction is "
          "ambiguous or that text in it is injected, so a cheap and feasible candidate on a V5 "
          "or V6 instruction is applied. A block is a refusal and lies inside the suite's "
          "refuse-or-ask outcome, although it is not a referral.")
        A("")
        A("| Case | Class | Sub-class | Suite disposition | Guard terminal (v1.2) | Reason |")
        A("|---|---|---|---|---|---|")
        for c in diff:
            g = c["guard"]
            if g["terminal_v12"].startswith("applied"):
                why = "applied, certified gap {:.3f} at or below tau".format(
                    g["certificate"]["gap"])
            elif g["terminal_v12"].startswith("blocked"):
                why = "blocked: " + ", ".join(g["blocking_codes"])
            else:
                why = g["terminal_v12"]
            A("| {} | {} | {} | {} | {} | {} |".format(
                c["case_id"], c["cls"], c["subclass"], c["expected_panel"],
                g["terminal_v12"], why))
    A("")
    A("## How each disposition was verified")
    A("")
    A("Every candidate was run on the instances_v10 snapshot (each file checked against "
      "`code/scripts/instance_manifest_l1.json`) through the v1.0.0 certificate gate (G_CERT, "
      "Tier 2) disposed with the v1.2 approver entry (`n3_evaluate.live_terminal_v12` with "
      "`approver_entry(False)`), and through the v1.1.0 code path with "
      "`issuer_accepts_cost = false`. The two agree on the terminal and the certified gap for "
      "all 30 cases. Where the stored suite-gate record carries the same operations, the run "
      "reproduces its terminal and gap. The run also reproduces DG1's canonical G_CERT "
      "terminal, N2's `gap_cert` and the published rule anchor gap of each board.")
    A("")
    A("Build assertions passed: {}.".format(n_checks))
    A("")
    A("## Files")
    A("")
    A("- `draw.csv`: case id, item id, class, sub-class, register, stratum, suite disposition "
      "under v1.2, the guard's actual v1.2 terminal, certified gap, anchor gap, the candidate "
      "handling source, and where the record came from.")
    A("- `label_map.csv`: presentation label (C01 to C30) to case id.")
    A("- `stage_a.jsonl`, `stage_b.jsonl`: the material of each stage, one case per line, in "
      "presentation order.")
    A("- `build_meta.json`: input and output digests and the assertion count.")
    A("- The panel workbooks `Stage_A_Workbook.xlsx` and `Stage_B_Workbook.xlsx` and the "
      "cover note `Panel_Instructions.md` are built by the same script.")
    A("")
    A("**Returned workbooks.** Save the five returned files of each stage in one folder as "
      "`Stage_A_Workbook_R<n>.xlsx` and `Stage_B_Workbook_R<n>.xlsx`, with n = 1 to 5 the "
      "panel member's number, and run the scorer on that folder. It writes `cases.csv` "
      "(case-level, de-identified) and the measures.")
    A("")
    A("## Input digests (SHA-256)")
    A("")
    A("| File | SHA-256 |")
    A("|---|---|")
    for k, v in digests.items():
        A("| `{}` | `{}` |".format(k, v))
    A("")
    A(out_digests_note)
    return "\n".join(L) + "\n"


def scan_panel_text(name: str, text: str, check: Checks, stage_a: bool) -> None:
    low = text.lower()
    hits = [w for w in BANNED_PANEL if re.search(r"(?<![a-z0-9]){}(?![a-z0-9])".format(
        re.escape(w)), low)]
    check("no banned word in " + name, not hits, str(hits))
    if stage_a:
        hits = [w for w in BANNED_STAGE_A if re.search(r"(?<![a-z]){}".format(re.escape(w)),
                                                       low)]
        check("no class or guard word in " + name, not hits, str(hits))
    am = [w for w in AMERICAN if w in low]
    check("British spelling in " + name, not am, str(am))


def scan_case_ids(name: str, text: str, cases: list, check: Checks) -> None:
    hits = [c["item_id"] for c in cases if c["item_id"] in text]
    hits += [c["case_id"] for c in cases if re.search(r"(?<![A-Za-z0-9]){}(?![0-9])".format(
        re.escape(c["case_id"])), text)]
    check("no item id or case id in " + name, not hits, str(hits[:5]))


def xlsx_strings(data: bytes) -> str:
    """Every text a reader of the workbook can see: cell values, titles, messages."""
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data))
    parts = [str(wb.properties.title or ""), str(wb.properties.creator or "")]
    for ws in wb.worksheets:
        parts.append(ws.title)
        for row in ws.iter_rows(values_only=True):
            parts.extend(str(v) for v in row if v is not None)
        for dv in ws.data_validations.dataValidation:
            parts.extend(str(x) for x in (dv.formula1, dv.error, dv.errorTitle, dv.prompt,
                                          dv.promptTitle) if x)
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Build                                                                        #
# --------------------------------------------------------------------------- #
def build(out_results: Path, out_panel: Path, quiet: bool = False) -> dict:
    check = Checks()
    inputs = load_inputs(check)
    digests = input_digests()
    cases, deviations, order = draw(inputs, check)
    run_guard(cases, inputs, check)
    by_case = {c["case_id"]: c for c in cases}
    presented = [by_case[cid] for cid in order]

    # board labels in presentation order
    board_label: dict = {}
    for c in presented:
        iid = c["guard"]["instance_id"]
        if iid not in board_label:
            board_label[iid] = "Board {}".format(len(board_label) + 1)
    for c in cases:
        c["board_label"] = board_label[c["guard"]["instance_id"]]
        c["board"] = board(c)
        c["candidate_text"] = ops_text(c["ops"])
        c["outcome"], c["record"] = stage_b_text(c)
        check("board context lists at most five orders for " + c["case_id"],
              1 <= len(c["board"]["rows"]) <= BOARD_MAX, str(len(c["board"]["rows"])))
        names = {o.get("order_id") for o in c["ops"] if o.get("order_id")} & \
            {w["id"] for w in c["instance"]["work_orders"]}
        shown = {r["order"] for r in c["board"]["rows"]}
        check("board context shows every existing order the candidate names on "
              + c["case_id"], names <= shown, str(names - shown))

    # ---- records ---------------------------------------------------------------
    stage_a = []
    stage_b = []
    for c in presented:
        stage_a.append(OrderedDict(
            label=c["label"], board_label=c["board_label"], instruction=c["item"]["instruction"],
            board=c["board"]["rows"], board_scope=c["board"]["scope"],
            board_text=c["board"]["text"], candidate_text=c["candidate_text"],
            ratings=OrderedDict(realism=None, disposition=None, fidelity=None, comment=None)))
        g = c["guard"]
        stage_b.append(OrderedDict(
            label=c["label"], instruction=c["item"]["instruction"],
            candidate_text=c["candidate_text"], outcome=c["outcome"], record=c["record"],
            terminal=g["terminal_v12"],
            findings=[OrderedDict(code=f["code"], stage=f["stage"], severity=f["severity"],
                                  text=finding_text(f, c["ops"]))
                      for f in g["findings"] if f["severity"] == "violation"],
            certificate=None if g["terminal_v12"] != "applied_with_certificate" else
            OrderedDict(gap=round(g["certificate"]["gap"], 6), tau=TAU),
            referral=None if g["referral"] is None else OrderedDict(
                price=round(g["referral"]["price"], 6), tau=TAU,
                anchor_gap=round(g["referral"]["anchor_gap"], 6),
                waits_for_approver=True),
            ratings=OrderedDict(understandable=None, actionable=None, comment=None)))
    a_rows = [dict(label=c["label"], board_label=c["board_label"],
                   instruction=c["item"]["instruction"], board_text=c["board"]["text"],
                   candidate_text=c["candidate_text"]) for c in presented]
    b_rows = [dict(label=c["label"], instruction=c["item"]["instruction"],
                   candidate_text=c["candidate_text"], outcome=c["outcome"],
                   record=c["record"]) for c in presented]

    draw_header = ["case_id", "item_id", "class", "subclass", "register", "stratum",
                   "stratum_name", "label", "quality_visible", "suite_disposition_v12",
                   "suite_terminal_v12", "guard_terminal_v12", "guard_disposition",
                   "matches_suite", "certified_gap", "anchor_gap", "blocking_codes",
                   "candidate_source", "candidate_ops", "record_source", "instance_id",
                   "cell_register", "cell_stratum", "n_candidates_in_cell"]
    draw_rows = []
    for c in cases:
        g = c["guard"]
        draw_rows.append([
            c["case_id"], c["item_id"], c["cls"], c["subclass"], c["register"], c["stratum"],
            STRATUM_NAME[c["stratum"]], c["label"],
            "" if c["cls"] != "V4" else str(c["pool"] == "V4_visible"),
            c["expected_panel"], c["expected_terminal"], g["terminal_v12"], c["actual_panel"],
            str(c["matches_expected"]),
            "" if g["certificate"] is None else "{:.6f}".format(g["certificate"]["gap"]),
            "{:.6f}".format(g["anchor_gap"]), ";".join(g["blocking_codes"]), c["source"],
            json.dumps(c["ops"], sort_keys=True), g["source"], g["instance_id"],
            c["cell"][0], STRATUM_NAME[c["cell"][1]], c["n_candidates"]])
    label_rows = [[c["label"], c["case_id"]] for c in presented]

    files = OrderedDict()
    files[out_results / "draw.csv"] = csv_text(draw_header, draw_rows).encode()
    files[out_results / "label_map.csv"] = csv_text(["label", "case_id"], label_rows).encode()
    files[out_results / "stage_a.jsonl"] = jsonl_text(stage_a).encode()
    files[out_results / "stage_b.jsonl"] = jsonl_text(stage_b).encode()
    wa = build_workbook("A", a_rows, STAGE_A_INSTRUCTIONS)
    wbk = build_workbook("B", b_rows, STAGE_B_INSTRUCTIONS)
    files[out_panel / "Stage_A_Workbook.xlsx"] = wa
    files[out_panel / "Stage_B_Workbook.xlsx"] = wbk
    files[out_panel / "Panel_Instructions.md"] = PANEL_NOTE.encode()

    # ---- panel-facing text scans ------------------------------------------------
    sa_text = files[out_results / "stage_a.jsonl"].decode()
    scan_panel_text("Stage A records", sa_text, check, stage_a=True)
    scan_case_ids("Stage A records", sa_text, cases, check)
    scan_panel_text("Stage A workbook", xlsx_strings(wa), check, stage_a=True)
    scan_case_ids("Stage A workbook", xlsx_strings(wa), cases, check)
    sb_panel = "\n".join(json.dumps(r) for r in b_rows)
    scan_panel_text("Stage B panel text", sb_panel, check, stage_a=False)
    scan_case_ids("Stage B panel text", sb_panel, cases, check)
    scan_panel_text("Stage B workbook", xlsx_strings(wbk), check, stage_a=False)
    scan_case_ids("Stage B workbook", xlsx_strings(wbk), cases, check)
    scan_panel_text("cover note", PANEL_NOTE, check, stage_a=False)
    for name, text in (("Stage A instructions", " ".join(v for _, v in STAGE_A_INSTRUCTIONS)),
                       ("Stage B instructions", " ".join(v for _, v in STAGE_B_INSTRUCTIONS))):
        check("no em-dash or semicolon in " + name, "—" not in text and ";" not in text)
    check("price is glossed once in the Stage B instructions",
          " ".join(v for _, v in STAGE_B_INSTRUCTIONS).count(
              "certified gap of the proposed schedule to the best achievable one") == 1)
    check("Stage B shows the same cases in the same order as Stage A",
          [r["label"] for r in stage_a] == [r["label"] for r in stage_b])
    check("Stage B outcome agrees with the guard terminal on every case",
          all({"applied_with_certificate": "Applied with certificate",
               "referred_with_price": "Referred with price"}.get(
                   r["terminal"], "Blocked with findings") == r["outcome"] for r in stage_b))

    out_digests = OrderedDict((str(p.name), sha256_bytes(b)) for p, b in files.items())
    meta = OrderedDict(
        version=VERSION, protocol=PROTOCOL, seed=SEED, tau=TAU, tau_hard=TAU_HARD,
        instance_root_name=Path(os.environ["L1_INSTANCE_ROOT"]).name,
        n_cases=len(cases), deviations=deviations, n_checks=None,
        inputs=digests, outputs=out_digests,
        guard_differs=[c["case_id"] for c in cases if not c["matches_expected"]])
    note = ("Output digests are recorded in `build_meta.json`. Two builds from the same "
            "inputs are byte-identical.")
    readme = readme_text(cases, deviations, digests, "@@N_CHECKS@@", note)
    low = readme.lower()
    hits = [w for w in BANNED_ANY if re.search(r"(?<![a-z0-9]){}(?![a-z0-9])".format(
        re.escape(w)), low)]
    check("no AI-tool, process or path word in the README", not hits, str(hits))
    check("no em-dash in the README", "\u2014" not in readme)
    # The README carries the assertion count, so no check may follow this line.
    readme = readme.replace("@@N_CHECKS@@", str(check.n))
    files[out_results / "README.md"] = readme.encode()
    meta["n_checks"] = check.n
    meta["outputs"]["README.md"] = sha256_bytes(files[out_results / "README.md"])
    files[out_results / "build_meta.json"] = (json.dumps(meta, indent=1) + "\n").encode()

    for p, b in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(b)
    if not quiet:
        print("audit pack built: {} cases, {} assertions, {} deviations, {} guard differences"
              .format(len(cases), check.n, len(deviations), len(meta["guard_differs"])))
        for c in cases:
            print("  {} {} {:<7} {:<14} {:<12} suite={:<6} guard={}".format(
                c["case_id"], c["label"], c["cls"], c["register"], STRATUM_NAME[c["stratum"]],
                c["expected_panel"], c["guard"]["terminal_v12"]))
    return {"cases": cases, "deviations": deviations, "n_checks": check.n,
            "files": {str(p): sha256_bytes(b) for p, b in files.items()}, "meta": meta}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-results", default=str(OUT_RESULTS))
    ap.add_argument("--out-panel", default=str(OUT_PANEL))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    build(Path(args.out_results), Path(args.out_panel), quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
