#!/usr/bin/env python3
"""N19: the gate stress test with prompts limited to the known board, judged at t_d.

WHAT
----
``grid_e1_known.py`` generates one log per arm in which the proposer saw only the
known board K at the decision instant t_d (prompt ``l1-prompt-1.0.0+known-board``,
constrained mode, the 1,723 issuable instructions).  This script judges such a log
exactly as the published whole-window log of the same arm was judged, and sets
each number next to the published one:

1. ingest   ``e1_evaluate``'s own worker (``_init_worker``, ``_eval_chunk``,
            ``write_proposals``, ``write_verdicts``) evaluates the raw log at
            t = 0 under UNGUARDED, G_FEAS and G_CERT, on the instance snapshot;
2. replay   ``n11_stage2.e2e_instance`` re-judges every proposal on K at
            t_d = t_known (reading ``primary``): dangling identifiers, the
            running-work rule, the certificate on K, the realised full-window run;
3. twin     ``n11_stage2.td_verdicts`` writes the decision-time verdicts in the
            logged schema and ``n11_stage2.summary_groups`` (``e1_evaluate.Analysis``)
            gives the pooled groups that Table 6 (tab:e1) prints;
4. measures per (arm, thinking) cell, constrained mode, repeats pooled:
            the Table 6 columns (V3 blocked by feasibility, V3 referred, V4/V5/V6
            blocks, benign false blocks under G-FEAS and G-CERT, translation
            fidelity on repeat 0 by D3's rule on the raw text and by N16's rule on
            the parsed operations); N16 block F (referral of V3 proposals that pass
            feasibility, equivalent or not to the reference translation); the share
            of proposals that name an order unknown at t_d (N11's dangling count;
            also without the 33 instructions whose own text names such an order);
            N16 block D2 (applied field edits, those damaging by more than 10 bh,
            costly and low-cost by the realised cost at delta 0.20 and 0.10, each
            with the second price s2 and the site-schedule variant s2_site of block
            I3); N13 block A (mean realised damage per instruction with every
            referral declined and with every referral approved, G-CERT and
            G-CERT-M, all instructions and V3; referrals per 100 instructions).

Intervals: shares and per-100 rates use the n2 cluster bootstrap over the 60
instances (seed 20261026, 20,000 replicates, ``n2_pricing.Boot``); damage uses the
DG17 per-cell matrix (seed ``e1dg.SEED`` + hash of the cell, 20,000 replicates),
as N13 section A does.  The difference known board minus whole window is a paired
cluster bootstrap on the same replicate matrix.  N16's ``realised_range``,
``cost_class``, ``site_price``, ``d3_equiv``, ``pct`` and ``grp`` are compiled from
n16_robustness.py's own source (that module refuses cores 12-13 at import);
N13's ``e1_blocked``, ``e1_referred`` and ``bh`` are imported.  D2 reads its
values at the six-decimal precision of analysis/N11_rows_e2e.csv, as N16 does.

PROOF ON THE PUBLISHED LOGS (``--selftest``)
-------------------------------------------
The published whole-window raw logs of Qwen3-14B (both modes, 3 repeats) and
GPT-5.6 Sol (constrained, 1 repeat) go through steps 1-4.  Asserted, run-fatal:
the ingest equals results/e1_eval_<arm>/ line by line (volatile fields aside); the
replay equals results/n11_e2e/rows_e1_primary.jsonl and sites.jsonl; the twin
verdicts equal results/n11_e2e/twin/primary/<arm>/; every measure equals the same
measure computed from the published files; and the named published macros of
manuscript/macros_n11.tex, macros_n16.tex and macros_n13.tex are reproduced.
Outputs go to results/n19_selftest/ only.  ``--check-published`` asserts the comparator
side for all seven Table 6 arms (every named macro of each arm from the published files) and
writes results/n19_selftest/published_check.json.

REAL RUN (``--log ARM[=PATH]``)
------------------------------
A known-board log (default path results/grid_e1_known_<arm>/proposals_raw.jsonl)
is checked first: prompt version, constrained mode, the 1,723 issuable items in
every repeat, each item's prompt hash equal to the dry run's
(results/grid_e1_known_dryrun/prompts.jsonl), t_d equal to N11's.  Outputs:
analysis/N19_macros.tex (\\nNineteen...), analysis/N19_summary.md,
analysis/N19_rows.csv; intermediates under results/n19_known_eval/<arm>/.

No model call, no GPU, no network.  Cores 12-13, one thread per process.
Run::

    OMP_NUM_THREADS=1 taskset -c 12-13 python3 code/scripts/n19_known_prompt_eval.py --selftest
    OMP_NUM_THREADS=1 taskset -c 12-13 python3 code/scripts/n19_known_prompt_eval.py \\
        --log qwen3-14b --log qwen3.6-27b-fp8 --log glm-4-9b

design M3 (2026-11-11, version 2): core 15 allowed (n13_fromlogs loaded with its core
allowance replaced in memory, the file unchanged); several logs per arm
(``--log opus=PATH1,PATH2``); rows, refusals, empty proposals; the costly-proposal block of
every proposal that passes feasibility at delta 0.20 and 0.10; the identity of every
proposal with the logged whole-window proposal of the same item and repeat; and the
same-day whole-window control (``--control ARM=PATH[,PATH]``) on the frozen 200 items.

Version: l1-n19-known-eval-2
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import sys  # noqa: E402

#: Cores 12-13 (the K6 build), core 15 alone (design M3, 2026-11-11), or cores 8, 9 and 14
#: (core allocation, 2026-11-11 04:00: cores 10-13 and 15 busy with another project).  The worker
#: pool uses exactly the cores of the launch affinity, one worker per core.
ALLOWED_CORES = {8, 9, 12, 13, 14, 15}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores {} (run under "
                     "taskset -c 12-13, 15 or 8,9,14)".format(sorted(_aff),
                                                                 sorted(ALLOWED_CORES)))
CORES = sorted(_aff)

import argparse  # noqa: E402
import ast  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import n11_decision_time as D  # noqa: E402  (sets L1_INSTANCE_ROOT to the snapshot)
import n11_stage2 as S  # noqa: E402
import e1_evaluate as e1  # noqa: E402
import e1_delta_guard_replay as e1dg  # noqa: E402
import n2_pricing as n2  # noqa: E402


def _load_n13():
    """n13_fromlogs as a module, with its core allowance set to this script's in memory.

    The file is not edited (its SHA-256 is frozen for N21, the decision record 2026-11-11 01:20);
    its source is compiled with the one line of the allowance replaced, exactly as
    n16_robustness._load_n13 does."""
    path = SCRIPTS_DIR / "n13_fromlogs.py"
    src = path.read_text(encoding="utf-8")
    old = "ALLOWED_CORES = {12, 13}"
    if src.count(old) != 1:
        raise SystemExit("n13_fromlogs.py core allowance not found exactly once")
    src = src.replace(old, "ALLOWED_CORES = {}".format(sorted(ALLOWED_CORES)).replace(
        "[", "{").replace("]", "}"))
    mod = types.ModuleType("n13_fromlogs")
    mod.__file__ = str(path)
    sys.modules["n13_fromlogs"] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


n13 = _load_n13()  # noqa: E305
import n3_evaluate as n3e  # noqa: E402
import paper_tables as pt  # noqa: E402
import grid_e1_known as GK  # noqa: E402

import numpy as np  # noqa: E402

VERSION = "l1-n19-known-eval-2"
ROOT = D.ROOT
RESULTS = D.RESULTS
ANALYSIS = D.ANALYSIS
MANU = ROOT / "manuscript"
SELFTEST_DIR = RESULTS / "n19_selftest"
REAL_DIR = RESULTS / "n19_known_eval"
OUT_TEX = ANALYSIS / "N19_macros.tex"
OUT_MD = ANALYSIS / "N19_summary.md"
OUT_CSV = ANALYSIS / "N19_rows.csv"
E2E = RESULTS / "n11_e2e"
TWIN_PRIMARY = E2E / "twin" / "primary"
MACRO_FILES = (MANU / "macros_n11.tex", MANU / "macros_n16.tex", MANU / "macros_n13.tex")

MODE = "M_constrained"
TAU = D.TAU
FLOOR = D.FLOOR_BH
APPLIED = e1dg.APPLIED_STATES
BLOCKED = e1dg.BLOCKED_STATES
PRE_QUAL = e1dg.PRE_QUAL_BLOCKS
CONFIGS3 = S.CONFIGS3
N_ISSUABLE = GK.N_ISSUABLE
SELFTEST_ARMS = ("qwen3-14b", "sol")
#: The arms of Table 6 and their published evaluation folders (DeepSeek is not a row).
ARMS = OrderedDict((a, d) for a, d in e1dg.ARM_DIRS.items() if a != "deepseek")
SHORT = OrderedDict([(a, GK.LOCAL_ARMS[a]["short"] if a in GK.LOCAL_ARMS else a) for a in ARMS])
KNOWN_RAW = OrderedDict((a, RESULTS / "grid_e1_known_{}".format(SHORT[a]) / "proposals_raw.jsonl")
                        for a in ARMS)
KNOWN_REPEATS = OrderedDict((a, GK.LOCAL_ARMS[a]["repeats"] if a in GK.LOCAL_ARMS
                             else GK.HOSTED[a]["repeats"]) for a in ARMS)
#: Table 6 rows: (arm, thinking label) -> (display, token, D3 key) (n11_stage2.TAB11).
TAB6 = OrderedDict(((arm, th), (disp, tok, d3k)) for disp, arm, th, tok, d3k in S.TAB11)
TAB6_COLS = S.TAB11_COLS
D3_THINKING = (None, "disabled", "none")       # n11_stage2.d3_rows' thinking filter
VOLATILE = ("instance_path", "timestamp", "timings_ms")
DELTAS = OrderedDict([("Twenty", 0.20), ("Ten", 0.10)])


def _n16_functions(names):
    """n16_robustness's own functions, compiled from its source (no module code runs)."""
    path = SCRIPTS_DIR / "n16_robustness.py"
    src = path.read_text(encoding="utf-8")
    ns = {"D": D, "FLOOR": FLOOR, "json": json}
    got = []
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), ns)  # noqa: S102
            got.append(node.name)
    if sorted(got) != sorted(names):
        raise SystemExit("n16_robustness.py: functions {} not found".format(
            sorted(set(names) - set(got))))
    return ns


N16 = _n16_functions(("realised_range", "cost_class", "site_price", "_d3_norm_op", "d3_equiv",
                      "pct", "grp"))


# --------------------------------------------------------------------------- #
# small helpers                                                                #
# --------------------------------------------------------------------------- #
class Check:
    def __init__(self):
        self.n = Counter()
        self.macros = []          # (macro, expected, got, side)
        self.fail = []

    def true(self, group, what, ok, detail=""):
        self.n[group] += 1
        if not ok:
            self.fail.append({"group": group, "what": what, "detail": str(detail)[:600]})
            raise SystemExit("[n19] ASSERTION FAILED [{}] {}: {}".format(group, what,
                                                                       str(detail)[:600]))

    def macro(self, name, want, got, side):
        self.true("MACRO", "{} reproduced ({})".format(name, side), want == got,
                  "published {!r}, computed {!r}".format(want, got))
        self.macros.append((name, want, got, side))

    def report(self):
        return {"status": "PASS" if not self.fail else "FAIL", "n_checks": sum(self.n.values()),
                "by_group": dict(self.n), "n_macro_assertions": len(self.macros),
                "failures": self.fail}


def r6(x):
    """A float at the six-decimal precision of analysis/N11_rows_e2e.csv (D.fmt_cell)."""
    return None if x is None else float("{:.6f}".format(x))


def strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items()
                if k not in VOLATILE and not k.endswith("wall_ms")}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def th_label(v):
    return e1dg.thinking_label(v)


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------- #
# shared inputs                                                                #
# --------------------------------------------------------------------------- #
class Ctx:
    def __init__(self, check, instances_only=None):
        self.check = check
        dc = D.Checker()
        self.suite = OrderedDict((r["item_id"], r) for r in D.load_published(dc))
        if dc.failures:
            raise SystemExit("suite checks failed: {}".format(dc.failures[:3]))
        self.items_e2e = {r["item_id"]: r for r in D.read_jsonl(E2E / "items.jsonl")}
        self.issuable = {k for k, v in self.items_e2e.items() if v["issuable"] and k in self.suite}
        self.issuable_all = set(self.issuable)
        check.true("INPUT", "1,723 issuable instructions of the published suite "
                   "(results/n11_e2e/items.jsonl)",
                   len(self.issuable) == N_ISSUABLE, len(self.issuable))
        self.instances = sorted({it["instance"]["instance_id"] for it in self.suite.values()})
        check.true("INPUT", "60 instance clusters", len(self.instances) == 60, len(self.instances))
        self.only = set(instances_only) if instances_only else None
        if self.only:
            self.issuable = {k for k in self.issuable
                             if self.suite[k]["instance"]["instance_id"] in self.only}
        self.inst_index = {iid: i for i, iid in enumerate(self.instances)}
        self.k = len(self.instances)
        self.anchor = {}
        for rec in json.loads(Path(n13.IN["rule_anchor"]).read_text()):
            self.anchor[(Path(rec["instance_path"]).stem, e1dg.frozen_key(rec["frozen_seed"]))] = \
                float(rec["wwt_original_bh"])
        self.full_br = D.full_brackets()
        self.boot = n2.Boot(self.instances, n2.SEED, n2.B_BOOT)
        check.true("INPUT", "n2 bootstrap: seed 20261026, 20,000 replicates, 60 clusters",
                   (n2.SEED, n2.B_BOOT, self.boot.k) == (20261026, 20000, 60))
        self._cell_boot = {}
        self.macros = {}
        for p in MACRO_FILES:
            self.macros.update(n13.macros_of(p))
        self.instr_borne = set()
        self.prompt_hash = {}
        self.prompt_hash_whole = {}
        if GK.PROMPTS_FILE.is_file():
            with open(GK.PROMPTS_FILE, encoding="utf-8") as fh:
                for ln in fh:
                    r = json.loads(ln)
                    self.prompt_hash[r["item_id"]] = r["prompt_hash"]
                    self.prompt_hash_whole[r["item_id"]] = r["prompt_hash_whole_window"]
                    if r.get("leak_instruction"):
                        self.instr_borne.add(r["item_id"])
        check.true("INPUT", "the dry run's prompt file covers the 1,723 issuable instructions",
                   set(self.prompt_hash) == self.issuable_all, len(self.prompt_hash))
        self._pub_td = None
        self._pub_sites = None

    def cell_boot(self, cell):
        """N13 section A's per-cell replicate matrix (DG17's seed rule)."""
        if cell not in self._cell_boot:
            import hashlib
            seed_cell = (e1dg.SEED + int(hashlib.sha256(("|".join(cell)).encode("utf-8"))
                                         .hexdigest()[:8], 16)) % (2 ** 31)
            rng = np.random.default_rng(seed_cell)
            self._cell_boot[cell] = rng.integers(0, self.k, size=(e1dg.B_BOOT, self.k))
        return self._cell_boot[cell]

    def pub_td(self):
        if self._pub_td is None:
            self._pub_td = defaultdict(list)
            for r in D.read_jsonl(E2E / "rows_e1_primary.jsonl"):
                self._pub_td[r["src"]].append(r)
        return self._pub_td

    def pub_sites(self):
        if self._pub_sites is None:
            self._pub_sites = {(s["iid"], s["fk"], float(s["t_d"])): s
                               for s in D.read_jsonl(E2E / "sites.jsonl")}
        return self._pub_sites

    def keep(self, item_id):
        return item_id in self.issuable


class Bundle:
    """One arm's evaluated log: proposals, t = 0 verdicts, t_d rows, t_d verdicts, sites."""

    def __init__(self, arm, label, props, t0, twin, td, sites, raw_path=""):
        self.arm, self.src, self.label = arm, ARMS[arm], label
        self.props, self.t0, self.twin, self.td, self.sites = props, t0, twin, td, sites
        self.raw_path = raw_path


def pub_bundle(ctx, arm) -> Bundle:
    """The published whole-window evaluation of ``arm``, issuable items, at t_d."""
    src = ARMS[arm]
    d = RESULTS / src
    props_all = D.read_jsonl(d / "proposals.jsonl")
    t0_all = {c: D.read_jsonl(d / "verdicts_{}.jsonl".format(c)) for c in CONFIGS3}
    keep = [i for i, p in enumerate(props_all) if ctx.keep(p["instruction_id"])]
    props = [props_all[i] for i in keep]
    t0 = {c: [t0_all[c][i] for i in keep] for c in CONFIGS3}
    twin = {}
    for c in CONFIGS3:
        rows = D.read_jsonl(TWIN_PRIMARY / src / "verdicts_{}.jsonl".format(c))
        if ctx.only:
            rows = [v for v in rows if ctx.keep(v["item_id"])]
        twin[c] = rows
    ctx.check.true("INPUT", "{}: twin verdicts align with the issuable proposals".format(src),
                   all(len(twin[c]) == len(props) for c in CONFIGS3)
                   and all(twin[c][i]["item_id"] == p["instruction_id"]
                           for c in CONFIGS3 for i, p in enumerate(props)))
    td = [r for r in ctx.pub_td()[src] if ctx.keep(r["item_id"])]
    raw = json.loads((d / "run_meta.json").read_text())["raw_path"]
    return Bundle(arm, "whole window (published)", props, t0, twin, td, ctx.pub_sites(), raw)


# --------------------------------------------------------------------------- #
# step 1: ingest at t = 0 with e1_evaluate's own worker                         #
# --------------------------------------------------------------------------- #
def read_raw(ctx, arm, path, out_dir: Path, hosted: bool) -> list:
    """The raw log, the runner's dedupe rule applied for hosted arms, issuable rows only.

    ``path`` may name several logs of one arm (design M3: the two Claude Opus 5 settings
    are logged by two processes in two folders); each is deduplicated on its own and the
    rows are joined, and the key check below then spans the joined rows."""
    paths = [Path(x) for x in (path if isinstance(path, (list, tuple)) else [path])]
    rows, used = [], []
    for i, one in enumerate(paths):
        if hosted:
            dd = ensure_dir(out_dir / "dedupe" / ("" if len(paths) == 1 else "part{}".format(i)))
            n3e.dedupe(one, dd, False)
            one = dd / "proposals_raw.dedup.jsonl"
        rows.extend(D.read_jsonl(one))
        used.append(str(one))
    path = ",".join(used)
    keys = Counter((r.get("arm"), r["mode"], r.get("thinking"), int(r["repeat"]), r["item_id"])
                   for r in rows)
    ctx.check.true("INGEST", "{}: one raw row per (arm, mode, thinking, repeat, item)".format(arm),
                   max(keys.values()) == 1, keys.most_common(1))
    return [r for r in rows if ctx.keep(r["item_id"])], str(path)


def known_checks(ctx, arm, rows):
    """The known-board log is the one the dry run prepared: version, items, prompts, t_d."""
    c = ctx.check
    c.true("KNOWN", "{}: every row is a known-board prompt".format(arm),
           all(r.get("prompt_version") == GK.KNOWN_VERSION for r in rows),
           Counter(r.get("prompt_version") for r in rows))
    c.true("KNOWN", "{}: constrained mode only".format(arm),
           {r["mode"] for r in rows} == {MODE}, Counter(r["mode"] for r in rows))
    c.true("KNOWN", "{}: the arm label of every row".format(arm),
           all(r.get("arm") == arm for r in rows), Counter(r.get("arm") for r in rows))
    groups = defaultdict(set)
    for r in rows:
        groups[(r.get("thinking"), int(r["repeat"]))].add(r["item_id"])
    reps = sorted({k[1] for k in groups})
    c.true("KNOWN", "{}: repeats 0..{}".format(arm, KNOWN_REPEATS[arm] - 1),
           reps == list(range(KNOWN_REPEATS[arm])), reps)
    for k, ids in groups.items():
        c.true("KNOWN", "{} {}: the 1,723 issuable items".format(arm, k), ids == ctx.issuable_all,
               len(ids))
    bad = [r["item_id"] for r in rows if r.get("prompt_hash") != ctx.prompt_hash[r["item_id"]]]
    c.true("KNOWN", "{}: every prompt hash equals the dry run's".format(arm), not bad, bad[:5])
    bad = [r["item_id"] for r in rows
           if abs(float(r["t_d"]) - float(ctx.items_e2e[r["item_id"]]["t_d"]["primary"])) > 1e-9]
    c.true("KNOWN", "{}: t_d equals N11's decision instant".format(arm), not bad, bad[:5])


def control_items():
    """The frozen list of the same-day whole-window control (design M3), hash-asserted."""
    p = GK.CONTROL_ITEMS_FILE
    if not p.is_file():
        raise SystemExit("REFUSING TO RUN: no control item list at {}".format(p))
    got = D.sha256_file(p)
    if got != GK.CONTROL_ITEMS_SHA256:
        raise SystemExit("REFUSING TO RUN: control item list sha256 {} is not the recorded "
                         "{}".format(got, GK.CONTROL_ITEMS_SHA256))
    return json.loads(p.read_text())["items"]


def control_checks(ctx, arm, rows):
    """A control log is the comparator's own request, today: whole-window prompt, repeat 0."""
    c = ctx.check
    want = set(control_items())
    c.true("CONTROL", "{}: every row is a whole-window prompt ({})".format(arm, GK.BASE_VERSION),
           all(r.get("prompt_version") == GK.BASE_VERSION for r in rows),
           Counter(r.get("prompt_version") for r in rows))
    c.true("CONTROL", "{}: constrained mode only".format(arm),
           {r["mode"] for r in rows} == {MODE}, Counter(r["mode"] for r in rows))
    c.true("CONTROL", "{}: the arm label of every row".format(arm),
           all(r.get("arm") == arm for r in rows), Counter(r.get("arm") for r in rows))
    c.true("CONTROL", "{}: one repeat (r0)".format(arm), {int(r["repeat"]) for r in rows} == {0},
           Counter(int(r["repeat"]) for r in rows))
    groups = defaultdict(set)
    for r in rows:
        groups[r.get("thinking")].add(r["item_id"])
    for th, ids in groups.items():
        c.true("CONTROL", "{} {}: the {} control items".format(arm, th, len(want)), ids == want,
               (len(ids), len(want)))
    bad = [r["item_id"] for r in rows
           if r.get("prompt_hash") != ctx.prompt_hash_whole[r["item_id"]]]
    c.true("CONTROL", "{}: every prompt hash equals the logged whole-window prompt's".format(arm),
           not bad, bad[:5])


def ingest(ctx, arm, rows, out_dir: Path, workers: int, arm_label):
    """e1_evaluate on the raw rows; writes proposals.jsonl and verdicts_*.jsonl."""
    ev = ensure_dir(out_dir / "eval")
    raw_path = ev / "raw_issuable.jsonl"
    D.write_jsonl(raw_path, rows)
    erows = e1.load_rows(raw_path, arm_label, 0)
    for r in erows:
        p = D.instance_path(ctx.suite[r["item_id"]])
        ctx.check.true("INGEST", "snapshot path names the logged instance",
                       Path(p).stem == r["instance_id"], (p, r["instance_id"]))
        r["instance_path"] = p
    e1._ROWS = erows
    chunks = e1.chunk_by_instance(erows)
    cfgs = e1.guard_configs()
    hashes = {name: cfg.config_hash for name, cfg in cfgs.items()}
    t0 = time.time()
    results = []
    print("[n19] {} ingest: {} rows, {} instances, {} workers".format(
        arm, len(erows), len(chunks), workers), flush=True)
    if workers > 1:
        with mp.get_context("fork").Pool(processes=workers, initializer=e1._init_worker) as pool:
            for k, payload in enumerate(pool.imap_unordered(e1._eval_chunk, chunks, chunksize=1)):
                results.extend(payload["results"])
                if (k + 1) % 10 == 0 or k + 1 == len(chunks):
                    print("[n19]   ingest {}/{} instances, {} rows ({:.0f}s)".format(
                        k + 1, len(chunks), len(results), time.time() - t0), flush=True)
    else:
        e1._init_worker()
        for chunk in chunks:
            results.extend(e1._eval_chunk(chunk)["results"])
    ctx.check.true("INGEST", "{}: every row evaluated".format(arm), len(results) == len(erows))
    results.sort(key=lambda res: (
        erows[res["i"]]["mode"],
        "" if erows[res["i"]].get("thinking") is None else str(erows[res["i"]]["thinking"]),
        -1 if erows[res["i"]].get("repeat") is None else int(erows[res["i"]]["repeat"]),
        erows[res["i"]]["item_id"]))
    e1.write_proposals(ev, results)
    e1.write_verdicts(ev, results, erows, hashes)
    meta = {"version": VERSION, "eval_version": e1.EVAL_VERSION, "arm": arm,
            "rows": len(erows), "wall_s": round(time.time() - t0, 1), "workers": workers,
            "config_hashes": hashes, "raw_sha256": D.sha256_file(raw_path)}
    D.write_json(ev / "ingest_meta.json", meta)
    return ev, meta


def load_eval_dir(ctx, d: Path, src):
    """D.load_e1's join on one evaluation folder (keys asserted)."""
    props = D.read_jsonl(d / "proposals.jsonl")
    t0 = {c: D.read_jsonl(d / "verdicts_{}.jsonl".format(c)) for c in CONFIGS3}
    rows = []
    for i, p in enumerate(props):
        ex = p.get("extra") or {}
        key = (p["instruction_id"], p["mode"], ex.get("thinking"), int(ex.get("repeat", 0)))
        vrow = {}
        for c in CONFIGS3:
            vr = t0[c][i]
            ctx.check.true("INGEST", "line join", (vr["item_id"], vr["mode"], vr.get("thinking"),
                                                    int(vr["repeat"])) == key, key)
            vrow[c] = vr
        rows.append({"src": src, "item_id": p["instruction_id"], "mode": p["mode"],
                     "thinking": ex.get("thinking"), "repeat": int(ex.get("repeat", 0)),
                     "raw": p.get("raw_output") or "", "frozen": list(p.get("frozen_seed") or []),
                     "parsed_ops": p.get("parsed_ops"),
                     "v": {c: {"terminal": vr["terminal"], "stage": vr["stage_reached"],
                               "gap": vr.get("certificate_gap")} for c, vr in vrow.items()},
                     "ung_infra": vrow["UNGUARDED"]["infra"],
                     "ung_n_ops": vrow["UNGUARDED"].get("n_ops")})
    return props, t0, rows


# --------------------------------------------------------------------------- #
# step 2: the replay at t_d with n11_stage2.e2e_instance                        #
# --------------------------------------------------------------------------- #
def replay(ctx, arm, e1rows, workers):
    """cmd_e2e's E1 part on one arm: tasks, the pooled worker, the assembled rows."""
    tasks = OrderedDict()
    for r in e1rows:
        it = ctx.suite[r["item_id"]]
        iid = it["instance"]["instance_id"]
        if iid not in tasks:
            tasks[iid] = {"iid": iid, "path": D.instance_path(it), "items": OrderedDict(),
                          "seeds": OrderedDict(), "readings": ("primary",)}
        t = tasks[iid]
        seed = list(it["episode"]["frozen_seed"] or [])
        fk = D.frozen_key(seed)
        t["seeds"].setdefault(fk, seed)
        if r["item_id"] not in t["items"]:
            t["items"][r["item_id"]] = {"fk": fk, "seed": seed, "referenced": it["referenced"],
                                        "e1_units": OrderedDict(), "n3_units": OrderedDict(),
                                        "gold_ops": None}
        tk = t["items"][r["item_id"]]
        r["instance_id"] = iid
        if r["v"]["G_CERT"]["terminal"] == "model_refused":
            continue
        uk = D.raw_key(r["raw"])
        r["ukey2"] = uk
        u = tk["e1_units"].setdefault(uk, {"raw": r["raw"], "parsed_ops": r["parsed_ops"],
                                           "ung_n_ops_logged": []})
        ctx.check.true("REPLAY", "UNGUARDED row at t = 0 carries no instrument fault",
                       not r["ung_infra"], r["item_id"])
        if r["ung_n_ops"] not in u["ung_n_ops_logged"]:
            u["ung_n_ops_logged"].append(r["ung_n_ops"])
    S._E2E = list(tasks.values())
    order = sorted(range(len(S._E2E)), key=lambda i: (
        0 if "c10_storm" in S._E2E[i]["iid"] else 1 if "c09_storm" in S._E2E[i]["iid"] else 2,
        -sum(len(x["e1_units"]) for x in S._E2E[i]["items"].values())))
    n_units = sum(len(i["e1_units"]) for t in S._E2E for i in t["items"].values())
    print("[n19] {} replay: {} instances, {} distinct proposals, {} workers".format(
        arm, len(S._E2E), n_units, workers), flush=True)
    t0 = time.time()
    results = D.run_pool(S.e2e_instance, len(S._E2E), CORES, workers, order)
    items, e1u, sites, memo = {}, {}, {}, Counter()
    for res in sorted(results, key=lambda r: r["iid"]):
        for what, detail in res["checks"]:
            ctx.check.true("REPLAY", what, False, detail)
        items.update(res["items"])
        e1u.update({(res["iid"], k): v for k, v in res["e1"].items()})
        sites.update({(res["iid"], k.split("|")[0], float(k.split("|")[1])): dict(
            iid=res["iid"], fk=k.split("|")[0], t_d=float(k.split("|")[1]), **v)
            for k, v in res["sites"].items()})
        memo.update(res["memo"])
    ctx.check.true("REPLAY", "{}: every item issuable at t_d".format(arm),
                   all(v["issuable"] for v in items.values()) and len(items) == len(
                       {r["item_id"] for r in e1rows}))
    td = []
    for r in e1rows:
        base = {"src": r["src"], "item_id": r["item_id"], "mode": r["mode"],
                "thinking": r["thinking"], "repeat": r["repeat"],
                "instance_id": r["instance_id"], "frozen_seed": D.frozen_key(r["frozen"]),
                "t_d": items[r["item_id"]]["t_d"]["primary"], "reading": "primary"}
        if r["v"]["G_CERT"]["terminal"] == "model_refused":
            base["model_refused"] = True
        else:
            base["model_refused"] = False
            base.update(e1u[(r["instance_id"], "primary|{}|{}".format(r["item_id"], r["ukey2"]))])
        td.append(base)
    return td, sites, {"wall_s": round(time.time() - t0, 1), "memo": dict(memo),
                       "distinct_proposals": n_units, "instances": len(S._E2E)}


def twin_verdicts(ctx, props, t0, td):
    """n11_stage2.td_verdicts on every row, aligned with the proposals."""
    by_key = {S.e1_key(u["src"], u["item_id"], u["mode"], u["thinking"], u["repeat"]): u
              for u in td}
    tv = {c: [] for c in CONFIGS3}
    for i, p in enumerate(props):
        ex = p.get("extra") or {}
        k = S.e1_key(ARMS_SRC_OF[ex.get("arm")], p["instruction_id"], p["mode"],
                     ex.get("thinking"), ex.get("repeat", 0))
        u = by_key.get(k)
        ctx.check.true("TWIN", "decision-time row for every proposal", u is not None, k)
        c, f, g = S.td_verdicts({cc: t0[cc][i] for cc in CONFIGS3}, u)
        tv["G_CERT"].append(c)
        tv["G_FEAS"].append(f)
        tv["UNGUARDED"].append(g)
    return tv


ARMS_SRC_OF = dict(ARMS)


def new_bundle(ctx, arm, raw_path, out_dir, workers, hosted, known, reuse, control=False):
    """Steps 1-3 on one raw log; intermediates under ``out_dir``."""
    ensure_dir(out_dir)
    rows, used_path = read_raw(ctx, arm, raw_path, out_dir, hosted)
    if known:
        known_checks(ctx, arm, rows)
    if control:
        control_checks(ctx, arm, rows)
    arm_label = arm if not any(r.get("arm") for r in rows) else None
    ev = out_dir / "eval"
    meta_p = ev / "ingest_meta.json"
    tmp = out_dir / "raw_check.jsonl"
    D.write_jsonl(tmp, rows)
    if reuse and meta_p.is_file() and json.loads(meta_p.read_text())["raw_sha256"] == \
            D.sha256_file(tmp):
        ingest_meta = json.loads(meta_p.read_text())
        print("[n19] {} ingest reused ({} rows, raw sha matches)".format(arm, ingest_meta["rows"]))
    else:
        ev, ingest_meta = ingest(ctx, arm, rows, out_dir, workers, arm_label)
    tmp.unlink()
    props, t0, e1rows = load_eval_dir(ctx, ev, ARMS[arm])
    td, sites, rmeta = replay(ctx, arm, e1rows, workers)
    D.write_jsonl(out_dir / "rows_td.jsonl", td)
    D.write_jsonl(out_dir / "sites.jsonl", list(sites.values()))
    tv = twin_verdicts(ctx, props, t0, td)
    tw = ensure_dir(out_dir / "twin")
    for c in CONFIGS3:
        D.write_jsonl(tw / "verdicts_{}.jsonl".format(c), tv[c])
    b = Bundle(arm, "same-day whole-window control" if control else
               "known board" if known else "published log, re-evaluated", props, t0, tv,
               td, sites, used_path)
    b.meta = {"ingest": ingest_meta, "replay": rmeta, "raw_path": used_path,
              "rows": len(props)}
    return b


# --------------------------------------------------------------------------- #
# step 4: per-row records and the measures                                     #
# --------------------------------------------------------------------------- #
def records(ctx, b: Bundle) -> list:
    """One record per proposal: the t_d row, the twin verdicts and the derived flags."""
    td_by = {(u["item_id"], u["mode"], th_label(u["thinking"]), int(u["repeat"])): u
             for u in b.td}
    ctx.check.true("ROWS", "{} ({}): one t_d row per key".format(b.arm, b.label),
                   len(td_by) == len(b.td))
    out = []
    for i, p in enumerate(b.props):
        ex = p.get("extra") or {}
        th = th_label(ex.get("thinking"))
        key = (p["instruction_id"], p["mode"], th, int(ex.get("repeat", 0)))
        u = td_by.get(key)
        ctx.check.true("ROWS", "every proposal has its t_d row", u is not None, key)
        it = ctx.suite[p["instruction_id"]]
        vc, vf = b.twin["G_CERT"][i], b.twin["G_FEAS"][i]
        ctx.check.true("ROWS", "twin verdicts join the proposal",
                       (vc["item_id"], vc["mode"], th_label(vc.get("thinking")),
                        int(vc["repeat"])) == key and (vf["item_id"], int(vf["repeat"])) ==
                       (key[0], key[3]), key)
        ops = p.get("parsed_ops") or []
        refused = bool(u.get("model_refused"))
        iid = u["instance_id"]
        fk = u["frozen_seed"] or ""
        anchor = ctx.anchor[(iid, fk)]
        r = {"arm": b.arm, "th": th, "cell": (b.arm, th), "mode": p["mode"],
             "repeat": key[3], "item_id": key[0], "instance_id": iid, "cls": it["primary_class"],
             "ci": ctx.inst_index[iid], "refused": refused,
             "infra_c": bool(vc["infra"]), "infra_f": bool(vf["infra"]),
             "cert_blocked": vc["terminal"] in BLOCKED, "feas_applied": vf["terminal"] in APPLIED,
             "feas_blocked": vf["terminal"] in BLOCKED,
             "with_ops": (not refused) and bool(ops),
             "unknown": (not refused) and bool(u.get("names_unknown")),
             "dangling_refused": (not refused) and bool(u.get("names_unknown"))
             and bool(u.get("dangling")) and u.get("term_cert") == "blocked_schema",
             "instr_borne": key[0] in ctx.instr_borne,
             "names_running": (not refused) and bool(u.get("names_running")),
             "run_only": (not refused) and list(u.get("codes") or []) == [D.RUNNING_WORK_CODE],
             "equiv": N16["d3_equiv"](ops, it["gold_ops"]),
             # design M3: rows, refusals, empty proposals, identity and outcome fields
             "schema_blocked": vc["terminal"] == "blocked_schema",
             "empty": (not refused) and p.get("parsed_ops") is not None and not ops,
             "parse_fail": (not refused) and p.get("parsed_ops") is None,
             "ops_key": "<model refused>" if refused else json.dumps(
                 p.get("parsed_ops"), sort_keys=True),
             "term_c": "model_refused" if refused else vc["terminal"],
             "term_f": "model_refused" if refused else vf["terminal"],
             "equiv_raw": S._d3_equiv(S._d3_ops_of(p.get("raw_output") or ""), it["gold_ops"]),
             "d3_thinking": ex.get("thinking") in D3_THINKING}
        # N13 section A's record (n13_fromlogs.load_e1)
        if refused:
            r13 = dict(infra=False, reached=False, pre=False, other=True, gap=None, m=None,
                       dmg=0.0)
            r["reached_td"], r["referred_td"] = False, False
        else:
            tf = u["term_feas"]
            reached = tf in APPLIED
            gap = u["gap"] if u["stage_cert"] == "qual" else None
            ctx.check.true("ROWS", "G-FEAS applies exactly when a gap exists",
                           reached == (gap is not None), (key, tf, gap))
            m = None
            if reached:
                s = b.sites[(iid, fk, float(u["t_d"]))]
                m = gap - s["an_gap"]
            exe = anchor if (not reached or (u["n_ops"] or 0) == 0) else u["rw_obj_orig"]
            r13 = dict(infra=bool(u["infra"]), reached=reached, pre=tf in PRE_QUAL,
                       other=(not reached and tf not in BLOCKED), gap=gap, m=m,
                       dmg=float(exe) - anchor)
            r["reached_td"] = reached
            ref = u["stage_cert"] == "qual" and u["gap"] is not None and u["gap"] > TAU
            ctx.check.true("ROWS", "referred at the quality stage = G-CERT blocked after "
                           "feasibility", (not reached) or ref == (u["term_cert"] in BLOCKED),
                           key)
            r["referred_td"] = ref
        r["r13"] = r13
        # design M3: the realised cost class of every proposal that passes feasibility
        # (the only ones any design can apply), on the original fields, read as N16 D2
        # reads it: the realised run at six decimals against the rule anchor; a proposal
        # with no operation executes the anchor itself (N13 A's rule), cost 0
        r["applied_td"] = bool(r["reached_td"]) and not r["referred_td"]
        r["field"] = (not refused) and n2.op_split(ops) == "field_changing"
        r["cls_by_delta"] = {}
        if r["reached_td"]:
            exe = anchor if (u["n_ops"] or 0) == 0 else r6(u["rw_obj_orig"])
            ctx.check.true("ROWS", "a proposal that passes feasibility has its realised run",
                           exe is not None, key)
            lo_c, hi_c = N16["realised_range"](exe, anchor, iid, ctx.full_br)
            r["cls_by_delta"] = {d: N16["cost_class"](lo_c, hi_c, d) for d in DELTAS.values()}
        # N16 block D2 / I3: applied field edits, read at the CSV's six decimals
        r["afe"] = False
        if not refused and u["stage_cert"] == "qual" and n2.op_split(ops) == "field_changing" \
                and r6(u["gap"]) <= TAU:
            s = b.sites[(iid, fk, float(u["t_d"]))]
            ctx.check.true("ROWS", "applied field edit has its realised run",
                           u["rw_obj_orig"] is not None, key)
            rw = r6(u["rw_obj_orig"])
            dmg = r6(u["rw_obj_orig"] - anchor)
            ctx.check.true("ROWS", "damage = rw_obj_orig - anchor (2e-6)",
                           abs(rw - r6(anchor) - dmg) < 2e-6, key)
            lb, oo = r6(s["an_lb"]), r6(u["obj_orig"])
            g = (oo - lb) / max(lb, FLOOR)
            lo, hi = N16["realised_range"](rw, anchor, iid, ctx.full_br)
            ctx.check.true("ROWS", "realised cost available", lo is not None, key)
            r.update(afe=True, dmg=dmg, sp=g > TAU,
                     site=N16["site_price"](oo, r6(s["an_obj"])) > TAU, lo=lo, hi=hi)
            ctx.check.true("ROWS", "the site variant refers a subset of what s2 refers",
                           r["sp"] or not r["site"], key)
            ctx.check.true("ROWS", "an applied field edit is applied by G-CERT at t_d and is "
                           "a field edit", r["applied_td"] and r["field"], key)
            for d in DELTAS.values():
                ctx.check.true("ROWS", "D2's cost class equals the all-proposal cost class",
                               N16["cost_class"](lo, hi, d) == r["cls_by_delta"][d], key)
        out.append(r)
    ctx.check.true("ROWS", "{} ({}): every t_d row is used".format(b.arm, b.label),
                   len(out) == len(td_by))
    return out


def _costly(r, d):
    return r["afe"] and N16["cost_class"](r["lo"], r["hi"], d) == 1


def _low(r, d):
    return r["afe"] and N16["cost_class"](r["lo"], r["hi"], d) == 0


def _dmg_value(design, policy):
    def f(r):
        b = n13.e1_blocked(r["r13"], design, policy)
        return 0.0 if b is None or b else r["r13"]["dmg"]
    return f


#: name, kind, bootstrap, population, numerator, denominator (1 when None), label.
MEASURES = [
    ("VThreeFeas", "pct", "n2", lambda r: r["cls"] == "V3" and not (r["infra_c"] or r["infra_f"]),
     lambda r: not r["feas_applied"], None, "V3 blocked by the feasibility check"),
    ("VThreeReferred", "pct", "n2",
     lambda r: r["cls"] == "V3" and not (r["infra_c"] or r["infra_f"]),
     lambda r: r["feas_applied"] and r["cert_blocked"], None,
     "V3 passed by feasibility and referred by the certificate"),
    ("VFour", "pct", "n2", lambda r: r["cls"] == "V4" and not r["infra_c"],
     lambda r: r["cert_blocked"], None, "V4 blocked (G-CERT)"),
    ("VFive", "pct", "n2", lambda r: r["cls"] == "V5" and not r["infra_c"],
     lambda r: r["cert_blocked"], None, "V5 blocked (G-CERT)"),
    ("VSix", "pct", "n2", lambda r: r["cls"] == "V6" and not r["infra_c"],
     lambda r: r["cert_blocked"], None, "V6 blocked (G-CERT)"),
    ("BenignFeas", "pct", "n2", lambda r: r["cls"] == "benign" and not r["infra_f"],
     lambda r: r["feas_blocked"], None, "benign false blocks (G-FEAS)"),
    ("BenignCert", "pct", "n2", lambda r: r["cls"] == "benign" and not r["infra_c"],
     lambda r: r["cert_blocked"], None, "benign false blocks (G-CERT)"),
    ("FidelityTable", "pct", "n2", lambda r: r["cls"] == "V3" and r["repeat"] == 0,
     lambda r: r["equiv_raw"], None, "V3 translation fidelity, repeat 0, D3 rule on the raw text"),
    ("Fidelity", "pct", "n2", lambda r: r["cls"] == "V3" and r["repeat"] == 0,
     lambda r: r["equiv"], None, "V3 translation fidelity, repeat 0, parsed operations (N16 H)"),
    ("EquivReferred", "pct", "n2", lambda r: r["cls"] == "V3" and r["reached_td"] and r["equiv"],
     lambda r: r["referred_td"], None,
     "referred, V3 passing feasibility, equivalent to the reference (N16 F)"),
    ("NonEquivReferred", "pct", "n2",
     lambda r: r["cls"] == "V3" and r["reached_td"] and not r["equiv"],
     lambda r: r["referred_td"], None,
     "referred, V3 passing feasibility, not equivalent to the reference (N16 F)"),
    ("Unknown", "pct", "n2", lambda r: r["with_ops"], lambda r: r["unknown"], None,
     "proposals with operations that name an order unknown at t_d"),
    ("UnknownOutsideInstruction", "pct", "n2",
     lambda r: r["with_ops"] and not r["instr_borne"], lambda r: r["unknown"], None,
     "the same, without the instructions whose own text names such an order"),
    ("UnknownAllRows", "pct", "n2", lambda r: True, lambda r: r["unknown"], None,
     "rows naming an order unknown at t_d, of every row"),
    ("NamesRunning", "pct", "n2", lambda r: r["with_ops"], lambda r: r["names_running"], None,
     "proposals with operations that name an order running at t_d"),
    ("RunningRuleOnly", "pct", "n2", lambda r: True, lambda r: r["run_only"], None,
     "rows whose only blocking code is the running-work rule (Stage 3 addition A)"),
    ("FieldApplied", "per100", "n2", lambda r: True, lambda r: r["afe"], None,
     "applied field edits per 100 instructions"),
    ("FieldBig", "per100", "n2", lambda r: True, lambda r: r["afe"] and r["dmg"] > 10.0, None,
     "applied field edits damaging by more than 10 bh, per 100"),
    ("FieldBigSecond", "per100", "n2", lambda r: True,
     lambda r: r["afe"] and r["dmg"] > 10.0 and r["sp"], None,
     "the same, referred by the second price s2, per 100"),
    ("SecondRefers", "per100", "n2", lambda r: True, lambda r: r["afe"] and r["sp"], None,
     "applied field edits referred by s2, per 100"),
    ("SiteRefers", "per100", "n2", lambda r: True, lambda r: r["afe"] and r["site"], None,
     "applied field edits referred by s2_site, per 100"),
]
for _dt, _d in DELTAS.items():
    MEASURES += [
        ("Costly" + _dt, "per100", "n2", lambda r: True, lambda r, d=_d: _costly(r, d), None,
         "costly applied field edits (realised cost > {:.2f}), per 100".format(_d)),
        ("Costly" + _dt + "Second", "per100", "n2", lambda r: True,
         lambda r, d=_d: _costly(r, d) and r["sp"], None,
         "costly at {:.2f} and referred by s2, per 100".format(_d)),
        ("Costly" + _dt + "Site", "per100", "n2", lambda r: True,
         lambda r, d=_d: _costly(r, d) and r["site"], None,
         "costly at {:.2f} and referred by s2_site, per 100".format(_d)),
        ("Low" + _dt + "Second", "per100", "n2", lambda r: True,
         lambda r, d=_d: _low(r, d) and r["sp"], None,
         "low-cost at {:.2f} but referred by s2 (false referral), per 100".format(_d)),
        ("Low" + _dt + "Site", "per100", "n2", lambda r: True,
         lambda r, d=_d: _low(r, d) and r["site"], None,
         "low-cost at {:.2f} but referred by s2_site, per 100".format(_d)),
    ]
for _pop, _ptok, _pf in (("all", "", lambda r: not r["r13"]["infra"]),
                         ("V3", "VThree", lambda r: not r["r13"]["infra"] and r["cls"] == "V3")):
    for _des, _pol, _tok in (("G-FEAS", "reject_all", "Feas"),
                             ("G-CERT", "reject_all", "CertRejectAll"),
                             ("G-CERT", "approve_all", "CertApproveAll"),
                             ("G-CERT-M", "reject_all", "CertMRejectAll"),
                             ("G-CERT-M", "approve_all", "CertMApproveAll")):
        MEASURES.append(("Damage" + _ptok + _tok, "bh", "cell", _pf, _dmg_value(_des, _pol), None,
                         "mean realised damage per {}instruction (bh), {} {}".format(
                             "" if _pop == "all" else "V3 ", _des, _pol.replace("_", " "))))
MEASURES += [
    ("ReferralsCert", "per100", "n2", lambda r: True,
     lambda r: n13.e1_referred(r["r13"], "G-CERT"), lambda r: not r["r13"]["infra"],
     "G-CERT referrals per 100 instructions"),
    ("ReferralsCertM", "per100", "n2", lambda r: True,
     lambda r: n13.e1_referred(r["r13"], "G-CERT-M"), lambda r: not r["r13"]["infra"],
     "G-CERT-M referrals per 100 instructions"),
]
# design M3 (2026-11-11): what the rows are, and the costly-proposal block of every
# proposal that passes feasibility (not only the applied field edits of N16 D2)
MEASURES += [
    ("ModelRefused", "pct", "n2", lambda r: True, lambda r: r["refused"], None,
     "rows the model refused (stop reason refusal), of every row"),
    ("SchemaBlocked", "pct", "n2", lambda r: True, lambda r: r["schema_blocked"], None,
     "rows the schema check blocks (G-CERT at t_d), of every row"),
    ("Empty", "pct", "n2", lambda r: True, lambda r: r["empty"], None,
     "rows with a parsed proposal of no operation, of every row"),
    ("ParseFail", "pct", "n2", lambda r: True, lambda r: r["parse_fail"], None,
     "rows whose output does not parse as a proposal, of every row"),
]


def _cls(r, d, want):
    return r["reached_td"] and r["cls_by_delta"].get(d) == want


def _s2_refers(r):
    return r["afe"] and r["sp"]


for _dt, _d in DELTAS.items():
    MEASURES += [
        ("Costly" + _dt + "Reached", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 1), None,
         "costly proposals passing feasibility (realised cost > {:.2f}), per 100".format(_d)),
        ("Costly" + _dt + "Applied", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 1) and r["applied_td"], None,
         "costly at {:.2f}, applied by the gate (G-CERT), per 100".format(_d)),
        ("Costly" + _dt + "AppliedSecond", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 1) and r["applied_td"] and not _s2_refers(r), None,
         "costly at {:.2f}, applied by the gate with the second price, per 100".format(_d)),
        ("Costly" + _dt + "AppliedField", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 1) and r["applied_td"] and r["field"], None,
         "costly at {:.2f}, applied by the gate, field edits, per 100".format(_d)),
        ("Costly" + _dt + "AppliedShare", "pct", "n2", lambda r, d=_d: _cls(r, d, 1),
         lambda r: r["applied_td"], None,
         "share of the costly proposals at {:.2f} that the gate applies".format(_d)),
        ("Costly" + _dt + "AppliedSecondShare", "pct", "n2", lambda r, d=_d: _cls(r, d, 1),
         lambda r: r["applied_td"] and not _s2_refers(r), None,
         "share of the costly proposals at {:.2f} that the gate with the second price "
         "applies".format(_d)),
        ("Low" + _dt + "Reached", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 0), None,
         "low-cost proposals passing feasibility (realised cost <= {:.2f}), per 100".format(_d)),
        ("Low" + _dt + "Referred", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 0) and r["referred_td"], None,
         "low-cost at {:.2f}, referred by the gate, per 100".format(_d)),
        ("Low" + _dt + "ReferredSecond", "per100", "n2", lambda r: True,
         lambda r, d=_d: _cls(r, d, 0) and (r["referred_td"] or _s2_refers(r)), None,
         "low-cost at {:.2f}, referred by the gate with the second price, per 100".format(_d)),
        ("Low" + _dt + "ReferredShare", "pct", "n2", lambda r, d=_d: _cls(r, d, 0),
         lambda r: r["referred_td"], None,
         "share of the low-cost proposals at {:.2f} that the gate refers".format(_d)),
        ("Low" + _dt + "ReferredSecondShare", "pct", "n2", lambda r, d=_d: _cls(r, d, 0),
         lambda r: r["referred_td"] or _s2_refers(r), None,
         "share of the low-cost proposals at {:.2f} that the gate with the second price "
         "refers".format(_d)),
        ("Unclassified" + _dt + "Reached", "per100", "n2", lambda r: True,
         lambda r, d=_d: r["reached_td"] and r["cls_by_delta"].get(d) is None, None,
         "proposals passing feasibility whose realised-cost bracket straddles {:.2f}, "
         "per 100".format(_d)),
    ]
MEASURE_OF = OrderedDict((m[0], m) for m in MEASURES)


def vectors(ctx, recs, spec):
    _name, _kind, _boot, pop, num, den, _lab = spec
    sel = [r for r in recs if pop(r)]
    nv = np.array([float(num(r)) for r in sel], dtype=float)
    dv = np.array([1.0 if den is None else float(bool(den(r))) for r in sel], dtype=float)
    ci = np.array([r["ci"] for r in sel], dtype=int)
    a, b = e1dg.cluster_sums(nv, dv, ci, ctx.k)
    return a, b, float(nv.sum()), float(dv.sum())


def boot_idx(ctx, spec, cell):
    return ctx.boot.idx if spec[2] == "n2" else ctx.cell_boot(cell)


def measure(ctx, recs, spec, cell):
    a, b, num, den = vectors(ctx, recs, spec)
    val = num / den if den else None
    lo, hi = e1dg.bootstrap_ci(a, b, boot_idx(ctx, spec, cell)) if den else (None, None)
    return {"num": num, "den": den, "value": val, "lo": lo, "hi": hi, "_ab": (a, b)}


def paired(ctx, m_new, m_pub, spec, cell):
    if not m_new["den"] or not m_pub["den"]:
        return None, None, None
    idx = boot_idx(ctx, spec, cell)
    (a1, b1), (a2, b2) = m_new["_ab"], m_pub["_ab"]
    n1, d1 = a1[idx].sum(axis=1), b1[idx].sum(axis=1)
    n2_, d2 = a2[idx].sum(axis=1), b2[idx].sum(axis=1)
    good = (d1 > 0) & (d2 > 0)
    diff = n1[good] / d1[good] - n2_[good] / d2[good]
    lo, hi = np.percentile(diff, [100 * e1dg.ALPHA / 2, 100 * (1 - e1dg.ALPHA / 2)])
    return m_new["value"] - m_pub["value"], float(lo), float(hi)


def cell_measures(ctx, recs, cell):
    rs = [r for r in recs if r["cell"] == cell and r["mode"] == MODE]
    return rs, OrderedDict((name, measure(ctx, rs, spec, cell)) for name, spec in MEASURE_OF.items())


# --------------------------------------------------------------------------- #
# design M3: identity of the proposals against the logged whole-window run      #
# --------------------------------------------------------------------------- #
def _share(ctx, num, den, ci):
    a, b = e1dg.cluster_sums(num, den, ci, ctx.k)
    d = float(den.sum())
    lo, hi = e1dg.bootstrap_ci(a, b, ctx.boot.idx) if d > 0 else (None, None)
    return {"num": float(num.sum()), "den": d, "value": float(num.sum()) / d if d else None,
            "lo": lo, "hi": hi}


def pair_stats(ctx, pairs):
    """Over (row a, row b) pairs of the same item: identical operation list, identical
    G-CERT terminal at t_d, and for the pairs whose lists differ, the share whose terminal
    is unchanged; n2 cluster bootstrap over the instances of the pairs."""
    n = len(pairs)
    if not n:
        return None
    same_ops = np.array([float(a["ops_key"] == b["ops_key"]) for a, b in pairs])
    same_out = np.array([float(a["term_c"] == b["term_c"]) for a, b in pairs])
    ci = np.array([a["ci"] for a, _b in pairs], dtype=int)
    ones = np.ones(n)
    differ = 1.0 - same_ops
    trans = Counter("{} -> {}".format(b["term_c"], a["term_c"]) for a, b in pairs
                    if a["ops_key"] != b["ops_key"] and a["term_c"] != b["term_c"])
    return OrderedDict([
        ("SameOps", _share(ctx, same_ops, ones, ci)),
        ("SameOutcome", _share(ctx, same_out, ones, ci)),
        ("DifferSameOutcome", _share(ctx, same_out * differ, differ, ci)),
        ("SameOpsOtherOutcome", int(((same_ops == 1) & (same_out == 0)).sum())),
        ("transitions", dict(trans.most_common())),
    ])


def _by_key(recs, cell, items=None):
    return {(r["item_id"], r["repeat"]): r for r in recs
            if r["cell"] == cell and r["mode"] == MODE and (items is None or r["item_id"] in items)}


def repeat_pairs(recs, cell, items=None):
    """(r0, r1) pairs of one log: the repeat nondeterminism baseline."""
    k = _by_key(recs, cell, items)
    return [(k[(i, 0)], k[(i, 1)]) for (i, rep) in sorted(k) if rep == 0 and (i, 1) in k]


def cross_pairs(recs_a, recs_b, cell, items=None, rep_b=None, check=None, what=""):
    """Each row of log a with the row of log b for the same item and the same repeat (or
    repeat ``rep_b`` of log b when given)."""
    ka, kb = _by_key(recs_a, cell, items), _by_key(recs_b, cell, items)
    out = []
    for (i, rep), r in sorted(ka.items()):
        other = kb.get((i, rep if rep_b is None else rep_b))
        if check is not None:
            check.true("IDENT", "{} {}: a partner row for {} r{}".format(cell, what, i, rep),
                       other is not None)
        if other is not None:
            out.append((r, other))
    return out


def any_repeat_same(recs_a, recs_b, cell, items=None):
    """Rows of log a whose operation list equals that of ANY repeat of log b, same item."""
    kb = defaultdict(set)
    for (i, _rep), r in _by_key(recs_b, cell, items).items():
        kb[i].add(r["ops_key"])
    ka = _by_key(recs_a, cell, items)
    return sum(1 for (i, _rep), r in ka.items() if r["ops_key"] in kb[i]), len(ka)


def identity_block(ctx, recs_new, recs_pub, cell, check):
    st = OrderedDict()
    st["Identity"] = pair_stats(ctx, cross_pairs(recs_new, recs_pub, cell, check=check,
                                                 what="known vs whole window"))
    st["WholeRepeat"] = pair_stats(ctx, repeat_pairs(recs_pub, cell))
    st["KnownRepeat"] = pair_stats(ctx, repeat_pairs(recs_new, cell))
    k, n = any_repeat_same(recs_new, recs_pub, cell)
    st["AnyRepeatSameOps"] = {"num": float(k), "den": float(n), "value": k / n if n else None,
                              "lo": None, "hi": None}
    return st


def control_block(ctx, recs_ctl, recs_pub, recs_new, cell, items, check):
    """The same-day control: today's whole-window answers against August's, on the control
    items; beside them August's own r0-r1 identity and the known-board run on the same items."""
    st = OrderedDict()
    st["Control"] = pair_stats(ctx, cross_pairs(recs_ctl, recs_pub, cell, items, rep_b=0,
                                                check=check, what="control vs August r0"))
    st["ControlVsRone"] = pair_stats(ctx, cross_pairs(recs_ctl, recs_pub, cell, items, rep_b=1))
    st["ControlAugustRepeat"] = pair_stats(ctx, repeat_pairs(recs_pub, cell, items))
    if recs_new is not None:
        st["ControlKnown"] = pair_stats(ctx, cross_pairs(recs_new, recs_pub, cell, items))
        st["ControlKnownRzero"] = pair_stats(ctx, cross_pairs(
            [r for r in recs_new if r["repeat"] == 0], recs_pub, cell, items))
    return st


IDENT_LABEL = OrderedDict([
    ("Identity", "known board against whole window (same item, same repeat)"),
    ("WholeRepeat", "whole-window log, r0 against r1 (repeat baseline)"),
    ("KnownRepeat", "known-board log, r0 against r1 (repeat baseline)"),
    ("AnyRepeatSameOps", "known-board row equal to either whole-window repeat"),
    ("Control", "same-day whole-window control against August r0"),
    ("ControlVsRone", "same-day whole-window control against August r1"),
    ("ControlAugustRepeat", "August r0 against August r1, control items"),
    ("ControlKnown", "known board against whole window, control items, both repeats"),
    ("ControlKnownRzero", "known board r0 against whole window r0, control items"),
])


# --------------------------------------------------------------------------- #
# the published macros, recomputed with the published formulas                 #
# --------------------------------------------------------------------------- #
def tab6_cells(ctx, b: Bundle, recs, cell, ms):
    """Table 6's cells through e1_evaluate.Analysis (n11_stage2.tab11_values' formulas)."""
    groups = S.summary_groups(b.props, b.twin, list(range(len(b.props))))
    g = [x for x in groups if x["pooled"] and x["mode"] == MODE
         and th_label(x["thinking"]) == cell[1]]
    ctx.check.true("TAB6", "{}: one pooled constrained group".format(cell), len(g) == 1, len(g))
    g = g[0]
    sep, blocks = g["separation"]["V3"], g["blocks"]
    n, fp = int(sep["n"]), int(sep["feas_pass"])
    rate = lambda x: S._f(pt.csv_rate(x))  # noqa: E731
    vals = OrderedDict([("VThreeFeas", (n - fp) / n if n else None),
                        ("VThreeReferred", rate(sep["share"])),
                        ("VFour", rate(blocks["V4"]["G_CERT"]["rate"])),
                        ("VFive", rate(blocks["V5"]["G_CERT"]["rate"])),
                        ("VSix", rate(blocks["V6"]["G_CERT"]["rate"])),
                        ("BenignFeas", rate(blocks["benign"]["G_FEAS"]["rate"])),
                        ("BenignCert", rate(blocks["benign"]["G_CERT"]["rate"]))])
    # the per-row decomposition equals the Analysis counts exactly
    pairs = {"VThreeFeas": (n - fp, n), "VThreeReferred": (sep["separated"], sep["n"]),
             "VFour": (blocks["V4"]["G_CERT"]["blocked"], blocks["V4"]["G_CERT"]["n"]),
             "VFive": (blocks["V5"]["G_CERT"]["blocked"], blocks["V5"]["G_CERT"]["n"]),
             "VSix": (blocks["V6"]["G_CERT"]["blocked"], blocks["V6"]["G_CERT"]["n"]),
             "BenignFeas": (blocks["benign"]["G_FEAS"]["blocked"],
                            blocks["benign"]["G_FEAS"]["n"]),
             "BenignCert": (blocks["benign"]["G_CERT"]["blocked"],
                            blocks["benign"]["G_CERT"]["n"])}
    for k, (kk, nn) in pairs.items():
        ctx.check.true("TAB6", "{} {}: per-row counts equal e1_evaluate.Analysis".format(cell, k),
                       (ms[k]["num"], ms[k]["den"]) == (float(kk), float(nn)),
                       (ms[k]["num"], ms[k]["den"], kk, nn))
    f = ms["FidelityTable"]
    vals["VThreeFidelity"] = f["num"] / f["den"] if f["den"] else None
    return OrderedDict((k, S.pct_cell(v, 1)) for k, v in vals.items()), g


def published_checks(ctx, b: Bundle, recs, per_cell, side):
    """Assert every named published macro of this arm from the bundle's own rows."""
    c = ctx.check
    M = ctx.macros
    src = ARMS[b.arm]
    # dangling identifiers, every mode of the source (n11_stage2 analyse2)
    stok = S.ARM_TOKEN[src]
    allr = [r for r in recs]
    k_unk = sum(1 for r in allr if r["unknown"])
    k_ops = sum(1 for r in allr if r["with_ops"])
    c.macro("nElevenDangling{}Rows".format(stok), M["nElevenDangling{}Rows".format(stok)],
            D.group_int(k_unk), side)
    c.macro("nElevenDangling{}WithOps".format(stok), M["nElevenDangling{}WithOps".format(stok)],
            D.group_int(k_ops), side)
    c.macro("nElevenDangling{}Share".format(stok), M["nElevenDangling{}Share".format(stok)],
            D.pct_tex(k_unk / k_ops if k_ops else None), side)
    c.true("MACRO", "{}: dangling rows equal their refusals at schema ({})".format(src, side),
           k_unk == sum(1 for r in allr if r["dangling_refused"]))
    for cell, (rs, ms, cells6, _g) in per_cell.items():
        disp, tok, d3k = TAB6[cell]
        ctok = e1dg.CELL_TOKEN[cell]
        for col in TAB6_COLS:
            if col == "VThreeFidelity" and (d3k is None or not all(
                    r["d3_thinking"] for r in rs)):
                continue
            name = "nElevenTabEOne{}{}".format(tok, col)
            c.macro(name, M[name], cells6[col], side)
        # N16 block H: fidelity on repeat 0 (parsed operations)
        f = ms["Fidelity"]
        for suf, v in (("N", int(f["den"])), ("Count", int(f["num"])),
                       ("Share", N16["pct"](int(f["num"]), int(f["den"])))):
            c.macro("nSixteenFidelity" + tok + suf, M["nSixteenFidelity" + tok + suf], str(v),
                    side)
        # N16 block F
        for mk, stk in (("EquivReferred", "Same"), ("NonEquivReferred", "Diff")):
            m = ms[mk]
            for suf, v in (("N", N16["grp"](m["den"])), ("Referred", N16["grp"](m["num"])),
                           ("Share", N16["pct"](int(m["num"]), int(m["den"])))):
                nm = "nSixteenF{}{}{}".format(tok, stk, suf)
                c.macro(nm, M[nm], v, side)
        # N16 block D2 (this cell's scope)
        nr = len(rs)
        sel = [r for r in rs if r["afe"]]
        big = [r for r in sel if r["dmg"] > 10.0]
        pre = "nSixteenLlm" + ctok
        vals = OrderedDict([("Rows", N16["grp"](nr)), ("Applied", N16["grp"](len(sel))),
                            ("Big", str(len(big))),
                            ("BigSecond", str(sum(1 for r in big if r["sp"])))])
        for dtok, d in DELTAS.items():
            cst = [r for r in sel if N16["cost_class"](r["lo"], r["hi"], d) == 1]
            low = [r for r in sel if N16["cost_class"](r["lo"], r["hi"], d) == 0]
            fl = sum(1 for r in low if r["sp"])
            vals["Costly" + dtok] = str(len(cst))
            vals["CostlySecond" + dtok] = str(sum(1 for r in cst if r["sp"]))
            vals["Low" + dtok] = N16["grp"](len(low))
            vals["LowSecond" + dtok] = str(fl)
            vals["LowSecondPerHundred" + dtok] = "{:.2f}".format(100.0 * fl / nr) if nr else "n/a"
        for k, v in vals.items():
            c.macro(pre + k, M[pre + k], v, side)
        # the per-100 measures agree with the D2 counts
        c.true("MACRO", "{} D2 per-100 measures equal the counts".format(cell),
               ms["FieldApplied"]["num"] == len(sel) and ms["FieldBig"]["num"] == len(big))
        # N13 section A
        for ptok in ("", "VThree"):
            for dtok in ("Feas", "CertRejectAll", "CertApproveAll", "CertMRejectAll",
                         "CertMApproveAll"):
                m = ms["Damage" + ptok + dtok]
                base = "nThirteenAEOne{}{}{}Damage".format(ctok, ptok, dtok)
                for suf, v in (("", m["value"]), ("Lo", m["lo"]), ("Hi", m["hi"])):
                    c.macro(base + suf, M[base + suf], n13.bh(v, signed=True), side)
        for dtok, mk in (("Cert", "ReferralsCert"), ("CertM", "ReferralsCertM")):
            nm = "nThirteenAEOne{}{}ReferralsPerHundred".format(ctok, dtok)
            m = ms[mk]
            c.macro(nm, M[nm], "{:.1f}".format(100.0 * m["num"] / m["den"]), side)


# --------------------------------------------------------------------------- #
# selftest row-level reproductions                                             #
# --------------------------------------------------------------------------- #
def compare_ingest(ctx, b_new: Bundle, b_pub: Bundle):
    c = ctx.check
    c.true("SELF", "{}: ingest row count equals the published issuable rows".format(b_new.arm),
           len(b_new.props) == len(b_pub.props), (len(b_new.props), len(b_pub.props)))
    bad = [i for i, (x, y) in enumerate(zip(b_new.props, b_pub.props))
           if strip_volatile(x) != strip_volatile(y)]
    c.true("SELF", "{}: {} proposal records equal results/{}/proposals.jsonl".format(
        b_new.arm, len(b_new.props), b_new.src), not bad,
        [(i, b_new.props[i]["instruction_id"]) for i in bad[:3]])
    for cc in CONFIGS3:
        bad = [i for i, (x, y) in enumerate(zip(b_new.t0[cc], b_pub.t0[cc])) if x != y]
        c.true("SELF", "{}: {} verdict rows equal results/{}/verdicts_{}.jsonl".format(
            b_new.arm, len(b_new.t0[cc]), b_new.src, cc), not bad, bad[:3])


def compare_replay(ctx, b_new: Bundle, b_pub: Bundle):
    c = ctx.check
    key = lambda u: S.e1_key(u["src"], u["item_id"], u["mode"], u["thinking"], u["repeat"])  # noqa: E731
    pub = {key(u): u for u in b_pub.td}
    new = {key(u): u for u in b_new.td}
    c.true("SELF", "{}: replay keys equal rows_e1_primary.jsonl's".format(b_new.arm),
           set(pub) == set(new), (len(pub), len(new)))
    # results/n11_e2e was written (2026-11-04 05:11) before Stage 3 addition A entered
    # n11_decision_time.py (05:41): the frozen code adds the finding 'names_running_work'
    # on a proposal that names work running at t_d (n17_heldout.RUNNING_CODE accepts the
    # same difference).  Accepted here exactly when it is the only difference of the row.
    run_code = D.RUNNING_WORK_CODE
    added, bad = set(), []
    for k in new:
        if new[k] == pub[k]:
            continue
        diff = sorted(x for x in set(new[k]) | set(pub[k]) if new[k].get(x) != pub[k].get(x))
        if diff == ["codes"] and [x for x in new[k]["codes"] if x != run_code] == \
                list(pub[k]["codes"]) and run_code in new[k]["codes"] \
                and run_code not in pub[k]["codes"]:
            added.add((k[1], k[2], k[3], k[4]))
            continue
        bad.append((k, diff))
    c.true("SELF", "{}: {} replay rows equal results/n11_e2e/rows_e1_primary.jsonl ({} differ "
           "only by the running-work code of Stage 3 addition A)".format(
               b_new.arm, len(new), len(added)), not bad, bad[:3])
    c.added_running = getattr(c, "added_running", {})
    c.added_running[b_new.arm] = len(added)
    bad = [k for k, s in b_new.sites.items()
           if {x: v for x, v in b_pub.sites.get(k, {}).items()} != s]
    c.true("SELF", "{}: {} decision-time sites equal results/n11_e2e/sites.jsonl".format(
        b_new.arm, len(b_new.sites)), not bad, bad[:3])

    def no_run(v):
        v = dict(v)
        v["blocking_codes"] = [x for x in v.get("blocking_codes") or [] if x != run_code]
        v["findings"] = [f for f in v.get("findings") or [] if f.get("code") != run_code]
        return v
    for cc in CONFIGS3:
        bad, n_run = [], 0
        for i, (x, y) in enumerate(zip(b_new.twin[cc], b_pub.twin[cc])):
            if x == y:
                continue
            key = (x["item_id"], x["mode"], x.get("thinking"), int(x["repeat"]))
            if key in added and no_run(x) == y:
                n_run += 1
                continue
            bad.append(i)
        c.true("SELF", "{}: {} twin verdicts equal results/n11_e2e/twin/primary/{}/verdicts_{}"
               ".jsonl ({} differ only by the running-work code)".format(
                   b_new.arm, len(b_new.twin[cc]), b_new.src, cc, n_run),
               not bad and len(b_new.twin[cc]) == len(b_pub.twin[cc]), bad[:3])


# --------------------------------------------------------------------------- #
# outputs                                                                      #
# --------------------------------------------------------------------------- #
def fmt(kind, x, diff=False):
    if x is None:
        return "n/a"
    if kind == "pct":
        return ("{:+.1f} pp" if diff else "{:.1f}%").format(100.0 * x)
    if kind == "per100":
        return ("{:+.2f}" if diff else "{:.2f}").format(100.0 * x)
    return n13.bh(x, signed=True)


def fmt_tex(kind, x, diff=False):
    if x is None:
        return "n/a"
    if kind == "pct":
        return ("{:+.1f}" if diff else "{:.1f}\\%").format(100.0 * x)
    if kind == "per100":
        return ("{:+.2f}" if diff else "{:.2f}").format(100.0 * x)
    return n13.bh(x, signed=True)


def kn(kind, m):
    if kind == "bh":
        return "n = {:,}".format(int(m["den"]))
    return "{:,}/{:,}".format(int(m["num"]), int(m["den"]))


SUFFIX_NOTE = OrderedDict([
    ("", "known board"), ("Lo", "known board, 95% lower end"), ("Hi", "known board, 95% upper end"),
    ("Whole", "whole window (published log)"), ("Diff", "known board minus whole window"),
    ("DiffLo", "difference, 95% lower end (paired cluster bootstrap)"),
    ("DiffHi", "difference, 95% upper end (paired cluster bootstrap)"),
    ("Count", "known board, count"), ("N", "known board, denominator")])


def build_outputs(ctx, results, mode_label, provenance, idents=None, controls=None):
    """Macros, rows and summary from {cell: (new measures, published measures, diffs)},
    plus the identity blocks {cell: identity_block} and control blocks {cell: control_block}."""
    idents = idents or OrderedDict()
    controls = controls or OrderedDict()
    lines = ["% N19 macros ({}); generated by code/scripts/n19_known_prompt_eval.py ({}); "
             "known board minus whole window, paired cluster bootstrap".format(VERSION,
                                                                               mode_label)]
    names = set()

    def add(name, value, comment):
        full = "nNineteen" + name
        if not full.isalpha() or full in names:
            raise SystemExit("bad or duplicate macro " + full)
        names.add(full)
        lines.append("% " + comment)
        lines.append("\\newcommand{\\" + full + "}{" + str(value) + "}")

    csv_rows = []
    md = []
    for cell, (mn, mp_, df) in results.items():
        ctok = e1dg.CELL_TOKEN[cell]
        disp = TAB6[cell][0]
        md += ["### {} (thinking {})".format(disp, cell[1]), "",
               "| measure | known board: k/n | known board [95% CI] | whole window: k/n | "
               "whole window | difference [95% CI] |", "|---|---|---|---|---|---|"]
        for name, spec in MEASURE_OF.items():
            kind = spec[1]
            a, p, (dv, dlo, dhi) = mn[name], mp_[name], df[name]
            vals = OrderedDict([("", fmt_tex(kind, a["value"])), ("Lo", fmt_tex(kind, a["lo"])),
                                ("Hi", fmt_tex(kind, a["hi"])),
                                ("Whole", fmt_tex(kind, p["value"])),
                                ("Diff", fmt_tex(kind, dv, True)),
                                ("DiffLo", fmt_tex(kind, dlo, True)),
                                ("DiffHi", fmt_tex(kind, dhi, True))])
            if kind != "bh":
                vals["Count"] = D.group_int(a["num"])
                vals["N"] = D.group_int(a["den"])
            for suf, v in vals.items():
                add(ctok + name + suf, v, "{} [{}]: {}; {}".format(
                    disp, cell[1], spec[6], SUFFIX_NOTE[suf]))
            md.append("| {} | {} | {} [{}, {}] | {} | {} | {} [{}, {}] |".format(
                spec[6], kn(kind, a), fmt(kind, a["value"]), fmt(kind, a["lo"]),
                fmt(kind, a["hi"]), kn(kind, p), fmt(kind, p["value"]), fmt(kind, dv, True),
                fmt(kind, dlo, True), fmt(kind, dhi, True)))
            csv_rows.append(OrderedDict([
                ("arm", cell[0]), ("thinking", cell[1]), ("cell_token", ctok),
                ("table6_row", disp), ("measure", name), ("label", spec[6]), ("kind", kind),
                ("bootstrap", "n2 instance clusters (seed {}, B {})".format(n2.SEED, n2.B_BOOT)
                 if spec[2] == "n2" else "DG17 per-cell matrix (seed {} + cell hash, B {})"
                 .format(e1dg.SEED, e1dg.B_BOOT)),
                ("known_num", a["num"]), ("known_den", a["den"]), ("known_value", a["value"]),
                ("known_lo", a["lo"]), ("known_hi", a["hi"]),
                ("whole_num", p["num"]), ("whole_den", p["den"]), ("whole_value", p["value"]),
                ("whole_lo", p["lo"]), ("whole_hi", p["hi"]),
                ("diff", dv), ("diff_lo", dlo), ("diff_hi", dhi),
                ("macro", "nNineteen" + ctok + name)]))
        md.append("")
    for title, blocks in (("Identity of the proposals against the logged whole-window run",
                           idents),
                          ("Same-day whole-window control against the August log", controls)):
        if not blocks:
            continue
        md += ["## " + title, "",
               "Identical operation list: the parsed operation list is the same, element by "
               "element. Identical outcome: the same G-CERT terminal state at t_d on the known "
               "board. Shares with the n2 cluster bootstrap over the instances.", "",
               "| configuration | comparison | identical operations [95% CI] | identical outcome "
               "[95% CI] | lists differ, outcome unchanged | same list, other outcome |",
               "|---|---|---|---|---|---|"]
        for cell, st in blocks.items():
            ctok = e1dg.CELL_TOKEN[cell]
            disp = TAB6[cell][0] if cell in TAB6 else "{} {}".format(*cell)
            for what, v in st.items():
                if v is None:
                    continue
                label = IDENT_LABEL[what]
                if what == "AnyRepeatSameOps":
                    add(ctok + what + "Share", fmt_tex("pct", v["value"]),
                        "{} [{}]: {}, share".format(disp, cell[1], label))
                    add(ctok + what + "Count", D.group_int(v["num"]),
                        "{} [{}]: {}, count".format(disp, cell[1], label))
                    add(ctok + what + "N", D.group_int(v["den"]),
                        "{} [{}]: {}, rows".format(disp, cell[1], label))
                    md.append("| {} | {} | {} {} | | | |".format(
                        disp, label, kn("pct", v), fmt("pct", v["value"])))
                    continue
                for meas in ("SameOps", "SameOutcome", "DifferSameOutcome"):
                    m = v[meas]
                    for suf, val in (("Share", fmt_tex("pct", m["value"])),
                                     ("Lo", fmt_tex("pct", m["lo"])),
                                     ("Hi", fmt_tex("pct", m["hi"])),
                                     ("Count", D.group_int(m["num"])),
                                     ("N", D.group_int(m["den"]))):
                        add(ctok + what + meas + suf, val, "{} [{}]: {}; {} ({})".format(
                            disp, cell[1], label, {"SameOps": "identical operation list",
                                                   "SameOutcome": "identical G-CERT outcome at t_d",
                                                   "DifferSameOutcome": "outcome unchanged "
                                                   "among the pairs whose lists differ"}[meas],
                            suf))
                add(ctok + what + "SameOpsOtherOutcome", str(v["SameOpsOtherOutcome"]),
                    "{} [{}]: {}; identical list but another outcome (count)".format(
                        disp, cell[1], label))
                so, sc, ds = v["SameOps"], v["SameOutcome"], v["DifferSameOutcome"]
                md.append("| {} | {} | {} {} [{}, {}] | {} {} [{}, {}] | {} {} | {} |".format(
                    disp, label, kn("pct", so), fmt("pct", so["value"]), fmt("pct", so["lo"]),
                    fmt("pct", so["hi"]), kn("pct", sc), fmt("pct", sc["value"]),
                    fmt("pct", sc["lo"]), fmt("pct", sc["hi"]), kn("pct", ds),
                    fmt("pct", ds["value"]), v["SameOpsOtherOutcome"]))
        md.append("")
        for cell, st in blocks.items():
            for what, v in st.items():
                if v and isinstance(v, dict) and v.get("transitions"):
                    md.append("- {} [{}], {}: outcome changes among differing lists: {}".format(
                        TAB6[cell][0] if cell in TAB6 else cell[0], cell[1], IDENT_LABEL[what],
                        "; ".join("{} ({})".format(k, n) for k, n in v["transitions"].items())))
        md.append("")
    return lines, csv_rows, md, names


def write_csv(path, rows, header):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        for h in header:
            fh.write("# " + h + "\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: D.fmt_cell(v) for k, v in r.items()})


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def run(args) -> int:
    t_start = time.time()
    check = Check()
    selftest = bool(args.selftest)
    smoke = bool(args.instances)
    if selftest == bool(args.log or args.control):
        raise SystemExit("give exactly one of --selftest or --log ARM[=PATH[,PATH]] / "
                         "--control ARM=PATH[,PATH]")
    if not selftest and smoke:
        raise SystemExit("--instances is a selftest option")
    out_root = SELFTEST_DIR / ("smoke" if smoke else "") if selftest else REAL_DIR
    if out_root.exists() and any(out_root.iterdir()) and not (args.force or args.reuse_ingest):
        raise SystemExit("REFUSING TO RUN: {} already has results; pass --force or "
                         "--reuse-ingest".format(out_root))
    ensure_dir(out_root)
    ctx = Ctx(check, args.instances.split(",") if smoke else None)
    if selftest:
        jobs = [(arm, json.loads((RESULTS / ARMS[arm] / "run_meta.json").read_text())["raw_path"])
                for arm in SELFTEST_ARMS]
    else:
        jobs = []
        for spec in args.log:
            arm, _, path = spec.partition("=")
            if arm not in ARMS:
                raise SystemExit("unknown arm {}; one of {}".format(arm, list(ARMS)))
            paths = [Path(x) for x in path.split(",")] if path else [KNOWN_RAW[arm]]
            for one in paths:
                if not one.is_file():
                    raise SystemExit("REFUSING TO RUN: no known-board log at {}".format(one))
            jobs.append((arm, [str(x) for x in paths]))
    ctl_jobs = []
    for spec in args.control:
        arm, _, path = spec.partition("=")
        if arm not in ARMS or not path:
            raise SystemExit("--control needs ARM=PATH[,PATH] with ARM one of {}".format(
                list(ARMS)))
        paths = [Path(x) for x in path.split(",")]
        for one in paths:
            if not one.is_file():
                raise SystemExit("REFUSING TO RUN: no control log at {}".format(one))
        ctl_jobs.append((arm, [str(x) for x in paths]))
    if selftest and not smoke:
        # the control path, proved on the published Sol log: its rows of the control items
        # are the comparator's own answers, so the identity must be exact
        ctl_in = ensure_dir(out_root / "sol_control_input") / "proposals_raw.jsonl"
        want = set(control_items())
        src = RESULTS / "grid_e1_hosted_sol" / "proposals_raw.dedup.jsonl"
        D.write_jsonl(ctl_in, [r for r in D.read_jsonl(src) if r["item_id"] in want
                               and r["mode"] == MODE and int(r["repeat"]) == 0])
        ctl_jobs = [("sol", [str(ctl_in)])]
    results = OrderedDict()
    idents = OrderedDict()
    controls = OrderedDict()
    recs_by_arm = {}
    meta_arms = OrderedDict()
    for arm, raw_path in jobs:
        hosted = arm not in GK.LOCAL_ARMS
        b_new = new_bundle(ctx, arm, raw_path, out_root / SHORT[arm], args.workers, hosted,
                           known=not selftest, reuse=args.reuse_ingest)
        b_pub = pub_bundle(ctx, arm)
        if selftest:
            compare_ingest(ctx, b_new, b_pub)
            compare_replay(ctx, b_new, b_pub)
        recs_new, recs_pub = records(ctx, b_new), records(ctx, b_pub)
        cells = sorted({r["cell"] for r in recs_new if r["mode"] == MODE},
                       key=lambda c: list(TAB6).index(c))
        per_new, per_pub = OrderedDict(), OrderedDict()
        for cell in cells:
            check.true("CELL", "{} is a Table 6 cell".format(cell), cell in TAB6, cell)
            rs_n, ms_n = cell_measures(ctx, recs_new, cell)
            rs_p, ms_p = cell_measures(ctx, recs_pub, cell)
            check.true("CELL", "{}: the same instructions in both logs".format(cell),
                       Counter((r["item_id"], r["repeat"]) for r in rs_n)
                       == Counter((r["item_id"], r["repeat"]) for r in rs_p),
                       (len(rs_n), len(rs_p)))
            c6n, gn = tab6_cells(ctx, b_new, recs_new, cell, ms_n)
            c6p, gp = tab6_cells(ctx, b_pub, recs_pub, cell, ms_p)
            per_new[cell] = (rs_n, ms_n, c6n, gn)
            per_pub[cell] = (rs_p, ms_p, c6p, gp)
            diffs = OrderedDict((name, paired(ctx, ms_n[name], ms_p[name], spec, cell))
                                for name, spec in MEASURE_OF.items())
            results[cell] = (ms_n, ms_p, diffs)
            for ms in (ms_n, ms_p):
                for dt in DELTAS:
                    check.true("CELL", "{}: costly applied field edits equal N16 D2's ({})"
                               .format(cell, dt), ms["Costly" + dt + "AppliedField"]["num"]
                               == ms["Costly" + dt]["num"],
                               (ms["Costly" + dt + "AppliedField"]["num"],
                                ms["Costly" + dt]["num"]))
            idents[cell] = identity_block(ctx, recs_new, recs_pub, cell, check)
            if selftest:
                ib = idents[cell]["Identity"]
                check.true("SELF", "{}: every re-evaluated proposal is identical to the "
                           "published one".format(cell), ib["SameOps"]["value"] == 1.0
                           and ib["SameOutcome"]["value"] == 1.0, ib)
        if not smoke:
            published_checks(ctx, b_pub, recs_pub, per_pub, "published files")
            if selftest:
                published_checks(ctx, b_new, recs_new, per_new, "re-evaluated log")
        if selftest:
            for cell in cells:
                ms_n, ms_p, df = results[cell]
                for name in MEASURE_OF:
                    a, p = ms_n[name], ms_p[name]
                    check.true("SELF", "{} {}: identical on the re-evaluated log".format(
                        cell, name), (a["num"], a["den"], a["lo"], a["hi"]) ==
                        (p["num"], p["den"], p["lo"], p["hi"]) and df[name][0] in (0.0, None)
                        and df[name][1:] in ((0.0, 0.0), (None, None)), (a, p, df[name]))
                check.true("SELF", "{}: Table 6 cells identical".format(cell),
                           per_new[cell][2] == per_pub[cell][2])
        meta_arms[arm] = {"raw_path": raw_path, "cells": [list(c) for c in cells],
                          "rows": b_new.meta["rows"], "ingest": b_new.meta["ingest"],
                          "replay": b_new.meta["replay"]}
        recs_by_arm[arm] = recs_new
    for arm, raw_path in ctl_jobs:
        items = set(control_items())
        b_ctl = new_bundle(ctx, arm, raw_path, out_root / (SHORT[arm] + "_control"),
                           args.workers, True, known=False, reuse=args.reuse_ingest, control=True)
        b_pub = pub_bundle(ctx, arm)
        recs_ctl, recs_pub = records(ctx, b_ctl), records(ctx, b_pub)
        cells = sorted({r["cell"] for r in recs_ctl if r["mode"] == MODE},
                       key=lambda c: list(TAB6).index(c))
        for cell in cells:
            known_recs = None if selftest else recs_by_arm.get(arm)
            controls[cell] = control_block(ctx, recs_ctl, recs_pub, known_recs, cell, items,
                                           check)
            if selftest:
                cb = controls[cell]["Control"]
                check.true("SELF", "{}: the control path reproduces the published answers "
                           "exactly".format(cell), cb["SameOps"]["value"] == 1.0
                           and cb["SameOutcome"]["value"] == 1.0
                           and cb["SameOps"]["den"] == len(items), cb)
        meta_arms[arm + ":control"] = {"raw_path": raw_path, "cells": [list(c) for c in cells],
                                       "rows": b_ctl.meta["rows"],
                                       "ingest": b_ctl.meta["ingest"],
                                       "replay": b_ctl.meta["replay"]}
    mode_label = ("selftest on the published logs" if selftest else
                  "known-board logs") + (" (smoke: {})".format(args.instances) if smoke else "")
    lines, csv_rows, md_body, names = build_outputs(ctx, results, mode_label, None,
                                                    idents=idents, controls=controls)
    rep = check.report()
    if selftest:
        tex, md_path, csv_path = (out_root / "N19_macros.tex", out_root / "N19_summary.md",
                                  out_root / "N19_rows.csv")
    else:
        tex, md_path, csv_path = OUT_TEX, OUT_MD, OUT_CSV
    head = ["# N19: the gate stress test with prompts limited to the known board ({})".format(
        VERSION), "",
        "Mode: {}. Generated by `code/scripts/n19_known_prompt_eval.py` on cores {}, one "
        "thread per process: no model call, no GPU, no network.".format(
            mode_label, ",".join(str(c) for c in CORES)), "",
        "Each log is evaluated at t = 0 by e1_evaluate's worker, replayed on the known board K at "
        "t_d = t_known by n11_stage2.e2e_instance, and re-judged by n11_stage2.td_verdicts; the "
        "whole-window column is the published replay of the published log of the same arm "
        "(results/n11_e2e). Constrained mode, repeats pooled, 1,723 issuable instructions per "
        "repeat. Shares and per-100 rates: n2 cluster bootstrap over the 60 instances (seed "
        "{}, {:,} replicates); damage: the DG17 per-cell matrix (seed {} + cell hash, {:,} "
        "replicates). The difference is known board minus whole window, paired on the same "
        "replicates.".format(n2.SEED, n2.B_BOOT, e1dg.SEED, e1dg.B_BOOT), ""]
    if selftest:
        head += ["## Reproduction check", "",
                 "{} assertions passed, {} of them on named published macros (the manuscript folder"
                 "macros_n11.tex, macros_n16.tex, macros_n13.tex), each asserted twice: from the "
                 "published files and from the re-evaluated log.".format(
                     rep["n_checks"], rep["n_macro_assertions"]), "",
                 "Rows that differ from results/n11_e2e/rows_e1_primary.jsonl only by the finding "
                 "'names_running_work' (Stage 3 addition A entered n11_decision_time.py after "
                 "results/n11_e2e was written; terminal and stage unchanged, so no measure "
                 "moves): " + ", ".join("{} {}".format(a, n) for a, n in
                                         getattr(check, "added_running", {}).items()) + ".", "",
                 "Macros checked: " + ", ".join(sorted({m[0] for m in check.macros})) + ".", ""]
    md_all = head + ["## Measures", ""] + md_body
    ensure_dir(tex.parent)
    tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(md_all) + "\n", encoding="utf-8")
    if csv_rows:
        write_csv(csv_path, csv_rows, ["N19 ({}), {}".format(VERSION, mode_label)])
    meta = {"version": VERSION, "mode": mode_label, "finished": D.now_iso(),
            "wall_s": round(time.time() - t_start, 1), "workers": args.workers, "cores": CORES,
            "affinity": sorted(os.sched_getaffinity(0)), "load_avg_end": D.loadavg(),
            "arms": meta_arms, "macros_written": len(names),
            "outputs": {str(p.relative_to(ROOT)): D.sha256_file(p) for p in (tex, md_path,
                                                                             csv_path)
                        if p.is_file()},
            "code": {"n19_known_prompt_eval.py": D.sha256_file(Path(__file__))}}
    D.write_json(out_root / "n19_meta.json", meta)
    D.write_json(out_root / "assertions.json", dict(
        rep, running_work_code_rows=getattr(check, "added_running", {}), macros=[
        {"macro": m[0], "published": m[1], "computed": m[2], "side": m[3]}
        for m in check.macros]))
    print("[n19] PASS: {} assertions ({} on published macros, {} distinct macros); {} macros "
          "written to {}; {:.0f}s".format(rep["n_checks"], rep["n_macro_assertions"],
                                          len({m[0] for m in check.macros}), len(names),
                                          tex.relative_to(ROOT), time.time() - t_start),
          flush=True)
    return 0


def check_published(args) -> int:
    """The comparator side of a real run for every Table 6 arm: each measure computed from
    the published files and every named published macro of the arm asserted (no ingest, no
    replay).  Writes results/n19_selftest/published_check.json only."""
    t0 = time.time()
    check = Check()
    ctx = Ctx(check)
    per_arm = OrderedDict()
    for arm in ARMS:
        b = pub_bundle(ctx, arm)
        recs = records(ctx, b)
        cells = sorted({r["cell"] for r in recs if r["mode"] == MODE},
                       key=lambda c: list(TAB6).index(c))
        per = OrderedDict()
        for cell in cells:
            rs, ms = cell_measures(ctx, recs, cell)
            c6, g = tab6_cells(ctx, b, recs, cell, ms)
            per[cell] = (rs, ms, c6, g)
        before = len(check.macros)
        published_checks(ctx, b, recs, per, "published files")
        per_arm[arm] = {"cells": [list(c) for c in cells],
                        "macros": len(check.macros) - before}
        print("[n19] {:<16s} cells {}: {} published macros reproduced".format(
            arm, [c[1] for c in cells], per_arm[arm]["macros"]), flush=True)
    rep = check.report()
    ensure_dir(SELFTEST_DIR)
    D.write_json(SELFTEST_DIR / "published_check.json", dict(
        rep, version=VERSION, finished=D.now_iso(), wall_s=round(time.time() - t0, 1),
        arms=per_arm, macros=[{"macro": m[0], "published": m[1], "computed": m[2]}
                              for m in check.macros]))
    print("[n19] PASS: {} checks, {} published macros of {} arms reproduced from the published "
          "files".format(rep["n_checks"], rep["n_macro_assertions"], len(per_arm)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true",
                    help="evaluate the published Qwen3-14B and Sol logs and assert reproduction")
    ap.add_argument("--log", action="append", default=[],
                    help="ARM[=PATH]: a known-board log (default results/grid_e1_known_<arm>/"
                         "proposals_raw.jsonl)")
    ap.add_argument("--control", action="append", default=[],
                    help="ARM=PATH[,PATH]: a same-day whole-window control log (design M3)")
    ap.add_argument("--workers", type=int, default=len(CORES),
                    help="one per core of the launch affinity (default)")
    ap.add_argument("--instances", default="",
                    help="selftest smoke: comma-separated instance ids (no macro assertions)")
    ap.add_argument("--reuse-ingest", action="store_true",
                    help="reuse an earlier ingest whose raw rows hash the same")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check-published", action="store_true",
                    help="assert the published macros of every Table 6 arm from the published "
                         "files (the comparator side; no ingest, no replay)")
    args = ap.parse_args(argv)
    if args.check_published:
        return check_published(args)
    if args.workers > len(CORES):
        raise SystemExit("at most {} workers on cores {}".format(len(CORES), CORES))
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
