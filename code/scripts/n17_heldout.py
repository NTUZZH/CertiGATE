#!/usr/bin/env python3
"""N17: the frozen gate with the second price on three fresh draws of the suite.

QUESTION
--------
The gate prices a proposed schedule change on the edited values of priorities
and time windows.  On the published direct benchmark it applies 18 costly
reference proposals, all of them field edits.  A second price on the original
values (g_orig) was defined after those misses were seen and refers all 18 in
replay.  That gate was frozen in the decision record on 2026-11-10 at 20:05 (entry
"stage K, freeze before the held-out test").  N17 replays the frozen gate on
instructions that did not exist when it was frozen: three fresh draws of the
full suite from the published generator with global seeds 20261110, 20261111
and 20261112, on the same 60 dispatch windows, each reference proposal priced
at its decision instant exactly as in the published direct benchmark.  Part 2
(``issue``) moves the issue time of every published instruction inside its
issuable interval and repeats the headline table.

THE FOUR LAUNCH ANSWERS
-----------------------
1. Purpose.  The numbers land in Section 5.3, one supplement table, the
   abstract and the Introduction: costly field edits applied by the gate with
   the second price, pooled over the three draws, with the low-cost referral
   share and its cluster-bootstrap interval as the cost.
2. Ideal result.  The second price refers all or nearly all costly field edits
   at a low-cost referral share near 2%.  A miss is reported with its cause;
   the result is reported whatever it is.
3. Contamination.  No solver, no model call, no GPU: deterministic dispatch
   replay and analytic bounds, so core contention changes wall time only.  The
   fresh replay refuses to start until the reproduction check on the published
   suite has passed (``repro``), and the gate definitions are hashed into that
   check and asserted unchanged by every later stage.
4. Data accuracy.  Instances are read from the instances_v10 snapshot through
   suite_gate (manifest-verified); the generator is pointed at the same
   snapshot (as code/scripts/build_suite_heldout.py does) and must rebuild the
   published suite v0.2 byte for byte from seed 20260811 (``build
   --check-published``); the replay must reproduce every published per-item
   quantity and disposition before any fresh seed is replayed.

WHAT IS IMPORTED, NOT RE-IMPLEMENTED
------------------------------------
n11_decision_time (D): build_tasks, census_instance (issuability, the decision
instant, the known board K, the gate's price on K, the realised run from t_d),
build_rows (the prices of every design), load_anchor_records, full_brackets.
n11_forecast (F): forecast_instance with the single reading FI (the gate at
t_d with every order of the window known), reading_prices, refers_rec,
attach_orig_truth, assert_k_direct, assert_runs.  n16_robustness: build_recs
(the second price g_orig), sp_flag (the gate with the second price),
site_price (s2_site), realised_range.  n13_fromlogs: score, costly_of,
refers.  n2_pricing: Boot (seed 20261026, 20,000 replicates, 60 clusters).
n16 and n13 refuse to run outside their own cores; their sources are loaded
with that one constant set to cores 8-11 (asserted to occur exactly as
expected) and are not modified on disk.  The site-schedule variant's flag is
n16 block I's closure ``site_flag``, restated in one line (``flag_cert_site``)
and checked against n16's published count.

Part 2 needs an issue time that is not t_d.  census_instance takes it from
``D.decision_instant_of(iss, reading)``; this script installs, in memory only,
a wrapper of ``D.issuability`` that carries the drawn time on the item's
issuability record and a wrapper of ``D.decision_instant_of`` that returns it
for the readings ``issue_uniform`` and ``issue_mid`` (every other reading is
delegated unchanged).  No file on disk is touched.

SUBCOMMANDS
-----------
build    --seed S | --check-published : the generator (build_suite.py's main)
         on the snapshot; writes code/suite/v1.1_heldout_S/
replay   --suite published|S [--reading primary|issue_uniform|issue_mid]
repro    the reproduction check on the published suite (run-fatal)
analyse  Part 1 tables, rows, macros and summary, and Part 2 when its two replays
         (``replay --suite published --reading issue_uniform|issue_mid``) are on disk

Run: OMP_NUM_THREADS=1 taskset -c 8-11 python3 code/scripts/n17_heldout.py <cmd>
Version: l1-n17-heldout-1
"""
import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
import pickle  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402
from collections import Counter, OrderedDict, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

ALLOWED_CORES = {8, 9, 10, 11}
_aff = set(os.sched_getaffinity(0))
if not _aff <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
    raise SystemExit("REFUSING TO RUN: affinity {} is not inside cores 8-11 "
                     "(run under taskset -c 8-11)".format(sorted(_aff)))

SCRIPTS_DIR = Path(__file__).resolve().parent
CODE = SCRIPTS_DIR.parent
ROOT = CODE.parent
for _p in (str(CODE), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

VERSION = "l1-n17-heldout-1"
SEEDS = (20261110, 20261111, 20261112)
SEED_TOK = OrderedDict([(20261110, "SeedA"), (20261111, "SeedB"), (20261112, "SeedC")])
PUBLISHED_SEED = 20260811
ISSUE_SEED = 20261110
ISSUE_READINGS = OrderedDict([("issue_uniform", "Uniform"), ("issue_mid", "Mid")])
RESULTS = ROOT / "results" / "n17_heldout"
ANALYSIS = ROOT / "analysis"
MANU = ROOT / "manuscript"
OUT_TEX = ANALYSIS / "N17_macros.tex"
OUT_CSV = ANALYSIS / "N17_rows.csv"
OUT_ISSUE_CSV = ANALYSIS / "N17_issue_rows.csv"
OUT_MD = ANALYSIS / "N17_summary.md"
OUT_MANU = MANU / "macros_n17.tex"
REPRO_PATH = RESULTS / "repro" / "repro_assertions.json"
SNAPSHOT = Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))
PROTECTED_SUITES = ("v0.1", "v0.2", "v0.3_heldout", "v1.1")

#: The frozen scripts (decision record, the K freeze, 2026-11-10 20:05), full digests.
FROZEN = OrderedDict([
    ("n16_robustness.py", "dde428a8cedf206a8f43bcd359a72317f72d6197d7a5203a5ca15da74c174481"),
    ("n13_fromlogs.py", "523c1e41df5e9c275e2bdc98e50d85444a227c43a0302d8dcd15802f8dbe3095"),
    ("n11_decision_time.py", "05978a918888782627f1cba89e67e590c306e0e6d52997e0181cbfc1fff2bc90"),
    ("n10_field_change.py", "5a790905576d49c182c19168e1fdb97ee1e479a595c1c2a8089aa127c31ebde5"),
])
#: Other code the replay runs (recorded, not frozen by the decision).
RECORDED = ("n11_forecast.py", "n8_causal.py", "n2_pricing.py", "suite_gate.py",
            "build_suite.py", "e1_delta_guard_replay.py")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_frozen() -> OrderedDict:
    out = OrderedDict()
    for name, want in FROZEN.items():
        got = sha256_file(SCRIPTS_DIR / name)
        if got != want:
            raise SystemExit("REFUSING TO RUN: frozen {} has sha256 {}, expected {}".format(
                name, got, want))
        out[name] = got
    return out


def code_hashes() -> OrderedDict:
    out = OrderedDict((k, sha256_file(SCRIPTS_DIR / k)) for k in FROZEN)
    for k in RECORDED:
        out[k] = sha256_file(SCRIPTS_DIR / k)
    for sub in ("l1adapter", "l1guard", "l1suite"):
        h = hashlib.sha256()
        for p in sorted((CODE / sub).glob("*.py")):
            h.update(p.name.encode())
            h.update(sha256_file(p).encode())
        out[sub + "/*.py"] = h.hexdigest()
    return out


FROZEN_AT_START = assert_frozen()

import n11_decision_time as D  # noqa: E402  (sets L1_INSTANCE_ROOT to the snapshot)
import n11_forecast as F  # noqa: E402


def _load_patched(name, replacements):
    """A frozen script as a module, with its core allowance replaced in memory only."""
    path = SCRIPTS_DIR / (name + ".py")
    src = path.read_text(encoding="utf-8")
    for old, new, count in replacements:
        if src.count(old) != count:
            raise SystemExit("{}: '{}' found {} times, expected {}".format(
                name, old, src.count(old), count))
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


# n16 holds 'ALLOWED_CORES = {14, 15}' twice: its own allowance and the one it installs
# into n13's source; both become cores 8-11.
n16 = _load_patched("n16_robustness", [("ALLOWED_CORES = {14, 15}",
                                        "ALLOWED_CORES = {8, 9, 10, 11}", 2)])
n13 = n16.n13
n2 = n13.n2
np = n13.np
if n13.ALLOWED_CORES != ALLOWED_CORES or n16.ALLOWED_CORES != ALLOWED_CORES:
    raise SystemExit("core allowance patch did not take")

TAU = n16.TAU                     # 0.20
FLOOR = D.FLOOR_BH                # 1 weighted bh
DELTAS = OrderedDict([("Twenty", 0.20), ("Ten", 0.10)])
REL2_SETTINGS = OrderedDict([("Pub", 0.02), ("Twenty", 0.20)])


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return D.now_iso()


def read_jsonl(path) -> list:
    return D.read_jsonl(path)


def write_jsonl(path, rows) -> None:
    D.write_jsonl(path, rows)


def write_json(path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    D.write_json(path, obj)


def parse_cores(text) -> list:
    cores = D.parse_cores(text)
    if not set(cores) <= ALLOWED_CORES and not os.environ.get("CERTIGATE_ANY_CORES"):
        raise SystemExit("REFUSING TO RUN: worker cores {} are not inside 8-11".format(cores))
    return cores


def sha_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


def suite_dir(seed) -> Path:
    return CODE / "suite" / "v1.1_heldout_{}".format(int(seed))


def replay_dir(tag, reading="primary") -> Path:
    return RESULTS / "replay" / (tag if reading == "primary" else "{}_{}".format(tag, reading))


# --------------------------------------------------------------------------- #
# build: the published generator on the snapshot                              #
# --------------------------------------------------------------------------- #
def point_generator_at_snapshot():
    """The suite's pool is read through l1adapter.instances (build_suite_heldout.py's way)."""
    import l1adapter.instances as instances_mod

    instances_mod.INSTANCE_ROOT = SNAPSHOT
    return instances_mod


def verify_pool() -> dict:
    """Every pool file the generator reads is in the manifest and carries its digest."""
    from l1suite import facts as facts_mod
    from l1suite.config import STRATA

    man = json.loads((SCRIPTS_DIR / "instance_manifest_l1.json").read_text())["files"]
    out = OrderedDict()
    for s in STRATA:
        for p in facts_mod.pool(s.key):
            rel = str(Path(p).resolve().relative_to(SNAPSHOT.resolve()))
            got = sha256_file(p)
            if man.get(rel) != got:
                raise SystemExit("pool file {} does not match the instance manifest".format(rel))
            out[rel] = got
    if len(out) != 60:
        raise SystemExit("pool holds {} files, expected 60".format(len(out)))
    return out


def cmd_build(args) -> int:
    import suite_gate as sg

    if args.check_published:
        seed, out = PUBLISHED_SEED, RESULTS / "published_rebuild"
    else:
        seed = int(args.seed)
        if seed not in SEEDS:
            raise SystemExit("seed {} is not one of the frozen held-out seeds {}".format(
                seed, SEEDS))
        out = suite_dir(seed)
    out = out.resolve()
    for name in PROTECTED_SUITES:
        if out == (CODE / "suite" / name).resolve():
            raise SystemExit("REFUSING TO WRITE into the published suite directory " + name)
    if (out / "suite.jsonl").exists():
        raise SystemExit("REFUSING TO OVERWRITE {}".format(out / "suite.jsonl"))
    pub_before = sha256_file(sg.SUITE_PATH)
    point_generator_at_snapshot()
    import build_suite as bs

    t0 = time.time()
    argv = sys.argv
    sys.argv = ["build_suite.py", "--seed", str(seed), "--out", str(out), "--quiet"]
    try:
        rc = bs.main()
    finally:
        sys.argv = argv
    wall = time.time() - t0
    if rc != 0:
        raise SystemExit("build_suite.main returned {}".format(rc))
    pool = verify_pool()
    got = sha256_file(out / "suite.jsonl")
    man = json.loads((out / "manifest.json").read_text())
    rows = read_jsonl(out / "suite.jsonl")
    pub_after = sha256_file(sg.SUITE_PATH)
    if pub_before != sg.SUITE_SHA256 or pub_after != sg.SUITE_SHA256:
        raise SystemExit("the published suite file changed during the build")
    rec = OrderedDict(
        version=VERSION, seed=seed, out=str(out.relative_to(ROOT)), suite_sha256=got,
        manifest_sha256=man["artifacts"]["suite.jsonl"]["sha256"],
        config_fingerprint=man["config_fingerprint"], suite_version=man["suite_version"],
        global_seed=man["config"]["global_seed"], items=len(rows),
        by_class=dict(sorted(Counter(r["primary_class"] for r in rows).items())),
        instances=len({r["instance"]["instance_id"] for r in rows}),
        instance_pool_files=man["instance_pool"], pool_verified=len(pool),
        wall_s=round(wall, 1), cores=sorted(os.sched_getaffinity(0)), finished=now_iso(),
        code=code_hashes())
    if got != rec["manifest_sha256"]:
        raise SystemExit("suite.jsonl digest differs from its manifest")
    if args.check_published:
        rec["published_sha256"] = sg.SUITE_SHA256
        rec["identical_to_published"] = got == sg.SUITE_SHA256
        write_json(RESULTS / "build_published_check.json", rec)
        print(json.dumps({k: rec[k] for k in ("suite_sha256", "identical_to_published",
                                               "items", "wall_s")}))
        return 0 if rec["identical_to_published"] else 3
    write_json(RESULTS / "build_{}.json".format(seed), rec)
    print(json.dumps({k: rec[k] for k in ("suite_sha256", "items", "by_class", "wall_s")}))
    return 0


# --------------------------------------------------------------------------- #
# Part 2: the issue time as a parameter (in-memory wrappers, nothing on disk)   #
# --------------------------------------------------------------------------- #
_ISSUE_T = {}           # item_id -> drawn issue time (set in the parent before the fork)
_ORIG_ISSUABILITY = D.issuability
_ORIG_DECISION_INSTANT = D.decision_instant_of


def _issuability_with_time(item, by_id, starts):
    iss = _ORIG_ISSUABILITY(item, by_id, starts)
    t = _ISSUE_T.get(item["item_id"])
    if t is not None:
        iss["_issue_t"] = float(t)
    return iss


def _decision_instant_with_time(iss, reading):
    if reading in ISSUE_READINGS:
        t = iss.get("_issue_t")
        return float(iss["t_known"]) if t is None else float(t)
    return _ORIG_DECISION_INSTANT(iss, reading)


def install_issue_times(times) -> None:
    _ISSUE_T.clear()
    _ISSUE_T.update(times)
    D.issuability = _issuability_with_time
    D.decision_instant_of = _decision_instant_with_time


def draw_issue_times(items) -> OrderedDict:
    """One issue time per issuable published instruction (t_d .. first start of a named order).

    Uniform: t_d + u (t_start - t_d), u from one generator with seed 20261110 over the
    issuable items in item-id order.  Midpoint: (t_d + t_start) / 2.  An instruction whose
    interval is empty (t_start equal to t_d, or no named order in the window) keeps t_d.
    """
    rng = np.random.default_rng(ISSUE_SEED)
    out = OrderedDict((k, OrderedDict()) for k in ISSUE_READINGS)
    for r in sorted(items, key=lambda x: x["item_id"]):
        if not r["issuable"]:
            continue
        u = float(rng.random())
        t_d, t_s = float(r["t_d"]), r["t_start"]
        if t_s is None or float(t_s) <= t_d:
            out["issue_uniform"][r["item_id"]] = t_d
            out["issue_mid"][r["item_id"]] = t_d
            continue
        t_s = float(t_s)
        out["issue_uniform"][r["item_id"]] = t_d + u * (t_s - t_d)
        out["issue_mid"][r["item_id"]] = 0.5 * (t_d + t_s)
    return out


# --------------------------------------------------------------------------- #
# replay: census_instance + forecast_instance (FI only), per instance          #
# --------------------------------------------------------------------------- #
def load_suite(tag, check):
    if tag == "published":
        return D.load_published(check), D.sha256_file(D.SUITE_PATH)
    seed = int(tag)
    rec = json.loads((RESULTS / "build_{}.json".format(seed)).read_text())
    path = suite_dir(seed) / "suite.jsonl"
    got = sha256_file(path)
    check.true("N17", "fresh suite {} carries the digest its build recorded".format(seed),
               got == rec["suite_sha256"], got)
    rows = read_jsonl(path)
    check.true("N17", "fresh suite {} holds 2,000 items".format(seed), len(rows) == 2000,
               len(rows))
    return rows, got


def make_tasks(rows, reading) -> list:
    pub = OrderedDict((r["item_id"], r) for r in rows)
    tasks = D.build_tasks(pub, OrderedDict(), {})
    for t in tasks:
        t["kf"], t["reading"] = "fix", reading
    return tasks


def fi_task(task, items) -> dict:
    """n11_forecast.direct_units for one instance, the reading FI only."""
    units = []
    for r in items:
        if not r["issuable"]:
            continue
        units.append({"uid": r["item_id"], "fk": r["fk"], "t_d": float(r["t_d"]),
                      "raw": json.dumps({"operations": r["_ops"]}),
                      "forecast": r["dt_stage_cert"] == "qual", "empty": not r["_ops"],
                      "rw_obj": r["rw_obj"], "rw_obj_orig": r["rw_obj_orig"],
                      "rw0_obj": r["rw0_obj"], "rw0_obj_orig": r["rw0_obj_orig"]})
    return {"iid": task["iid"], "path": task["path"], "units": units, "seeds": task["seeds"],
            "readings": [("FI", 1)], "topup": False, "open_trades": False, "pool": None}


def _work(ti) -> dict:
    t0 = time.perf_counter()
    task = D._TASKS[ti]
    res = D.census_instance(ti)
    ops_of = {it["item_id"]: it["ops"] for it in task["items"]}
    for r in res["items"]:
        r["_ops"] = ops_of[r["item_id"]]
    F._TASKS = {ti: fi_task(task, res["items"])}
    fres = F.forecast_instance(ti)
    for r in res["items"]:
        r.pop("_ops", None)
    cen = {"iid": res["iid"], "items": res["items"], "seeds": res["seeds"],
           "anchor_omni": res["anchor_omni"], "n_boards": len(res["boards"]),
           "wall_census_s": res["wall_s"]}
    fc = {k: fres[k] for k in ("iid", "stratum", "k", "k_anchor", "anchors", "prices", "af",
                               "af1", "af3", "counts", "mhat", "topup", "names_running",
                               "wall_s")}
    return {"iid": res["iid"], "census": cen, "fc": fc, "wall_s": time.perf_counter() - t0,
            "pid": os.getpid(), "cpu_s": time.process_time()}


def run_instances(tasks, part_dir, cores, workers, cfg) -> dict:
    import multiprocessing as mp

    part_dir.mkdir(parents=True, exist_ok=True)
    results, todo = {}, []
    for i, t in enumerate(tasks):
        pth = part_dir / "{}.pkl".format(t["iid"])
        tsha = sha_obj(t)
        if pth.is_file():
            with open(pth, "rb") as fh:
                got = pickle.load(fh)
            if got.get("_cfg") == cfg and got.get("_task_sha") == tsha:
                results[t["iid"]] = got
                continue
        todo.append(i)
    D._TASKS = tasks
    order = sorted(todo, key=lambda i: (
        0 if "c10_storm" in tasks[i]["iid"] else 1 if "c09_storm" in tasks[i]["iid"] else 2,
        -len(tasks[i]["items"])))
    print("[n17] {} instances ({} from parts), {} to run, {} workers on cores {}".format(
        len(tasks), len(results), len(order), workers, cores), flush=True)

    def keep(res):
        t = [x for x in tasks if x["iid"] == res["iid"]][0]
        res["_cfg"], res["_task_sha"] = cfg, sha_obj(t)
        tmp = part_dir / "{}.pkl.tmp".format(res["iid"])
        with open(tmp, "wb") as fh:
            pickle.dump(res, fh)
        os.replace(tmp, part_dir / "{}.pkl".format(res["iid"]))
        results[res["iid"]] = res
        print("[n17]   done {} ({:.0f}s), {} of {}".format(res["iid"], res["wall_s"],
                                                         len(results), len(tasks)), flush=True)

    if order:
        if workers <= 1:
            D._winit(cores)
            for i in order:
                keep(_work(i))
        else:
            ctx = mp.get_context("fork")
            with ctx.Pool(workers, initializer=D._winit, initargs=(cores,),
                          maxtasksperchild=4) as pool:
                for res in pool.imap_unordered(_work, order):
                    keep(res)
    return results


def attach_meta(items, rows):
    """cmd_census's per-row attributes (class, stratum, edit type, frozen-set key)."""
    meta = {r["item_id"]: r for r in rows}
    anchors = D.load_anchor_records()
    for r in items:
        it = meta[r["item_id"]]
        r["primary_class"] = it["primary_class"]
        r["subclass"] = it["subclass"]
        r["stratum"] = it["instance"]["stratum"]
        r["instance_id"] = it["instance"]["instance_id"]
        r["twin_id"] = it.get("twin_id")
        r["quality_visible"] = bool(it.get("quality_visible_candidate"))
        r["register"] = it.get("register")
        ops = D.canonical_ops(it)
        r["n_ops"] = len(ops)
        r["op_types"] = "|".join(sorted({o.get("op", "?") for o in ops if isinstance(o, dict)}))
        r["split"] = D.op_split(ops)
        r["c_role"] = None
        r["frozen_seed"] = r.pop("fk")
        a = anchors[(r["instance_id"], r["frozen_seed"])]
        r["pub_anchor_wwt"] = float(a["wwt_original_bh"])
        r["pub_anchor_gap"] = float(a["gap"])
    return items


def cmd_replay(args) -> int:
    cores = parse_cores(args.cores)
    D.cap_threads(1)
    tag, reading = args.suite, args.reading
    if tag != "published":
        if int(tag) not in SEEDS:
            raise SystemExit("unknown seed {}".format(tag))
        rep = require_repro()
        print("[n17] reproduction check PASS ({}), fresh replay allowed".format(
            rep["finished"]), flush=True)
    if reading in ISSUE_READINGS and tag != "published":
        raise SystemExit("the issue-time sensitivity runs on the published suite only")
    if reading not in ("primary",) + tuple(ISSUE_READINGS):
        raise SystemExit("unknown reading " + reading)
    out = replay_dir(tag, reading)
    out.mkdir(parents=True, exist_ok=True)
    check = D.Checker()
    t0 = time.time()
    load0 = D.loadavg()
    rows, suite_sha = load_suite(tag, check)
    if check.failures:
        check.fatal(out / "replay_assertions.json")
    times = None
    if reading in ISSUE_READINGS:
        rep = require_repro()
        prim = read_jsonl(replay_dir("published") / "items.jsonl")
        times = draw_issue_times(prim)[reading]
        install_issue_times(times)
        write_json(out / "issue_times.json", times)
    tasks = make_tasks(rows, reading)
    if args.instances:
        keep = set(args.instances.split(","))
        tasks = [t for t in tasks if t["iid"] in keep]
    cfg = sha_obj({"version": VERSION, "reading": reading, "suite": suite_sha,
                   "code": code_hashes(), "issue_times": times})
    res = run_instances(tasks, out / "parts", cores, args.workers, cfg)
    items, fres = [], OrderedDict()
    for iid in sorted(res):
        items.extend(res[iid]["census"]["items"])
        fres[iid] = res[iid]["fc"]
    attach_meta(items, rows)
    krows = D.build_rows(items, {}, D.full_brackets(), D.load_anchor_records())
    F.assert_k_direct(check, fres, items, krows)
    summ = F.assert_runs(check, fres)
    n_fi = sum(1 for v in fres.values() for p in v["prices"] if p["reading"] == "FI")
    n_q = sum(1 for r in items if r["issuable"] and r["dt_stage_cert"] == "qual")
    check.true("N17", "one FI price per issuable item priced on K", n_fi == n_q, (n_fi, n_q))
    if times is not None:
        for r in items:
            if r["item_id"] in times:
                check.close("N17", "issue time used on " + r["item_id"], r["t_d"],
                            times[r["item_id"]], 1e-12)
    fi_rows, fi_anchor = [], []
    for iid, v in fres.items():
        for p in v["prices"]:
            if p["reading"] == "FI":
                fi_rows.append(dict(p, iid=iid))
        for a in v["anchors"]:
            if a["reading"] == "FI":
                fi_anchor.append(dict(a, iid=iid))
    write_jsonl(out / "items.jsonl", sorted(items, key=lambda r: r["item_id"]))
    write_jsonl(out / "fullinfo.jsonl", fi_rows)
    write_jsonl(out / "fi_anchors.jsonl", fi_anchor)
    wall = time.time() - t0
    meta = OrderedDict(
        version=VERSION, suite=tag, reading=reading, suite_sha256=suite_sha,
        instances=len(tasks), items=len(items), smoke=bool(args.instances),
        workers=args.workers, worker_cores=cores, parent_affinity=sorted(os.sched_getaffinity(0)),
        omp_num_threads=os.environ.get("OMP_NUM_THREADS"), host=socket.gethostname(),
        python=sys.version.split()[0], numpy=np.__version__, started_load_avg=load0,
        finished=now_iso(), wall_s=round(wall, 1), load_avg_end=D.loadavg(),
        instance_wall_s={k: round(v["wall_s"], 1) for k, v in res.items()},
        instance_cpu_s={k: round(v.get("cpu_s", 0.0), 1) for k, v in res.items()},
        fc_counts=dict(summ["stage_diff"]), af1_rows=summ["af1_rows"], code=code_hashes(),
        outputs={p.name: sha256_file(p) for p in sorted(out.glob("*.jsonl"))})
    write_json(out / "replay_meta.json", meta)
    check.fatal(out / "replay_assertions.json", {"finished": now_iso(), "outputs": meta["outputs"]})
    print("[n17 replay {} {}] PASS: {} checks, {} items, {:.0f}s".format(
        tag, reading, check.report()["n_checks"], len(items), wall), flush=True)
    return 0


# --------------------------------------------------------------------------- #
# Records and the gate definitions (frozen with the reproduction check)        #
# --------------------------------------------------------------------------- #
def fc_rec(r, rp_rec, lo, hi, dmg):
    """One record in n13.load_inputs' layout, built in memory (full precision)."""
    rec = OrderedDict(item_id=r["item_id"], primary_class=r["primary_class"],
                      stratum=r["stratum"], instance_id=r["instance_id"], split=r["split"],
                      t_d=float(r["t_d"]), stopped=bool(rp_rec["stopped"]),
                      und=set(rp_rec["undecided"]), lo=lo, hi=hi, dmg=dmg)
    for g in n13.DESIGNS + ("D-ABS-orig",):
        rec["p_" + g] = rp_rec.get("p_" + g)
    for g in n13.DESIGNS:
        rec["ref_" + g] = F.refers_rec(rp_rec, g)
    rec["ref_" + n13.UNION] = F.refers_rec(rp_rec, "G-CERT-M|D-REL2")
    return rec


def build_records(items, fi_rows):
    """n11_forecast.cmd_analyse's K and FI readings and n16.build_recs, on one replay."""
    items = [dict(r) for r in items]
    krows = D.build_rows(items, {}, D.full_brackets(), D.load_anchor_records())
    by = {r["item_id"]: r for r in items}
    priced = [r for r in krows if r["set"] == "published" and r["issuable"] and r["priced"]]
    anchors = D.load_anchor_records()
    full_br = D.full_brackets()
    for r in priced:
        it = by[r["item_id"]]
        r["frozen_seed_key"] = it["frozen_seed"]
        for k in ("om_term_cert", "om_stage_cert", "om_obj_orig", "an_obj_orig"):
            r[k] = it.get(k)
        for g in F.DESIGNS:
            r["om_p_" + g] = it.get("om_p_" + g)
    F.attach_orig_truth(priced, full_br, anchors)
    fullinfo = defaultdict(list)
    for p in fi_rows:
        fullinfo[(p["uid"], p["reading"])].append((p["s"], p))
    rp = F.reading_prices(priced, {}, fullinfo, ("K", "FI"))
    fc = {"K": OrderedDict(), "FI": OrderedDict()}
    for r in priced:
        lo, hi = r.get("orig_m_lo"), r.get("orig_m_hi")
        if not r.get("orig_covered_m"):
            lo = hi = None
        dmg = None if r["rw_obj_orig"] is None else r["rw_obj_orig"] - r["anchor_pub"]
        for rd in ("K", "FI"):
            fc[rd][r["item_id"]] = fc_rec(r, rp[rd][r["item_id"]], lo, hi, dmg)
    recs, by_dt = n16.build_recs(items, fc)
    for rec in recs:
        it = by_dt[rec["item_id"]]
        rec["s2_site"] = n16.site_price(it["dt_obj_orig"], it["an_obj"])
        rec["t_start"] = it["t_start"]
        rec["subclass"] = it["subclass"]
        rec["obj_orig_K"] = it["dt_obj_orig"]
        rec["lb_anchor_K"] = it["an_lb"]
        rec["wt_anchor_K"] = it["an_obj"]
        rec["rw_obj_orig"] = it["rw_obj_orig"]
        rec["anchor_pub"] = it["pub_anchor_wwt"]
        rec["op_types"] = it["op_types"]
        rec["frozen_seed"] = it["frozen_seed"]
    return recs, by_dt, priced, krows


def flag_cert(r):
    return n13.refers(r, "G-CERT")


def flag_cert_fi(r):
    return n13.refers(r["fi"], "G-CERT")


def flag_cert_sp(r):
    return n16.sp_flag(r, "G-CERT")


def flag_cert_site(r):
    # n16 block I's site_flag: n13.refers(r, g) or (field edit and s2_site > tau)
    return n13.refers(r, "G-CERT") or (r["split"] == "field_changing" and r["s2_site"] > TAU)


def flag_rel2(r):
    return n13.refers(r, "D-REL2")


def flag_rel2_sp(r):
    return n16.sp_flag(r, "D-REL2")


def _rel2_at(r, s):
    p = r["p_D-REL2"]
    return p is not None and p > s


def flag_rel2_20(r):
    return _rel2_at(r, REL2_SETTINGS["Twenty"])


def flag_rel2_20_sp(r):
    return _rel2_at(r, REL2_SETTINGS["Twenty"]) or (r["split"] == "field_changing" and r["sp"])


GATES = OrderedDict([
    ("cert", ("certificate on K (G-CERT, tau 0.20)", flag_cert)),
    ("certfi", ("certificate with full information (FI)", flag_cert_fi)),
    ("certsp", ("certificate on K with the second price", flag_cert_sp)),
    ("certsite", ("certificate on K with the site-schedule variant", flag_cert_site)),
    ("rel", ("D-REL2 at 0.02", flag_rel2)),
    ("relsp", ("D-REL2 at 0.02 with the second price", flag_rel2_sp)),
    ("reltw", ("D-REL2 at 0.20", flag_rel2_20)),
    ("reltwsp", ("D-REL2 at 0.20 with the second price", flag_rel2_20_sp)),
])
GATE_TOK = OrderedDict([("cert", "Cert"), ("certfi", "CertFI"), ("certsp", "CertSP"),
                        ("certsite", "CertSite"), ("rel", "RelTwo"), ("relsp", "RelTwoSP"),
                        ("reltw", "RelTwoAtTwenty"), ("reltwsp", "RelTwoAtTwentySP")])


def definitions_sha() -> str:
    """Digest of every definition the dispositions depend on (asserted after repro)."""
    parts = [inspect.getsource(f) for f in (fc_rec, build_records, flag_cert, flag_cert_fi,
                                            flag_cert_sp, flag_cert_site, flag_rel2,
                                            flag_rel2_sp, _rel2_at, flag_rel2_20,
                                            flag_rel2_20_sp, draw_issue_times)]
    parts.append(repr([(k, v[0]) for k, v in GATES.items()]))
    parts.append(repr((TAU, FLOOR, dict(DELTAS), dict(REL2_SETTINGS), ISSUE_SEED)))
    parts.extend(FROZEN.values())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def require_repro() -> dict:
    if not REPRO_PATH.is_file():
        raise SystemExit("REFUSING TO RUN: the reproduction check has not been run")
    rep = json.loads(REPRO_PATH.read_text())
    if rep.get("status") != "PASS":
        raise SystemExit("REFUSING TO RUN: the reproduction check says {}".format(
            rep.get("status")))
    if rep.get("definitions_sha") != definitions_sha():
        raise SystemExit("REFUSING TO RUN: the gate definitions changed after the "
                         "reproduction check")
    for k, v in FROZEN.items():
        if rep["code"].get(k) != v:
            raise SystemExit("REFUSING TO RUN: frozen {} differs from the reproduction run".format(k))
    return rep


# --------------------------------------------------------------------------- #
# repro: the published suite, item by item                                     #
# --------------------------------------------------------------------------- #
ITEM_EXACT = ("issuable", "issuable_strict", "dt_stage_cert", "dt_term_cert", "dt_term_feas",
              "dt_stage_feas", "dt_fp", "n_known", "n_completed", "n_unknown", "n_ref",
              "rw_term", "rw_term_feas", "frozen_seed", "instance_id", "primary_class",
              "split", "an_term")
#: The published census (results/n11_decision_time/items.jsonl, 2026-11-04 04:26) was
#: written by n11_decision_time.py c15bed5d..., before Stage 3 addition A (the running-work
#: finding, code 'names_running_work') entered the frozen version 83d5217b...  The frozen
#: code therefore adds that one code on items that name work running at t_d.  The check
#: below accepts exactly that difference, and only on items outside the direct benchmark
#: (not issuable) whose terminal and stage are unchanged.
RUNNING_CODE = "names_running_work"
ITEM_FLOAT = ("t_d", "t_known", "t_start", "dt_obj", "dt_obj_orig", "dt_lb", "dt_gap",
              "dt_ref2", "an_obj", "an_obj_orig", "an_lb", "an_gap", "rw_obj", "rw_obj_orig",
              "rw0_obj_orig", "pub_anchor_wwt")
TOL = 1e-9


def published_records(check):
    """The rows N16 reads, through N16's own loaders (n13.load_inputs, n16.build_recs)."""
    hashes, items_dt, pub, boot, fc = n13.load_inputs()
    recs, by = n16.build_recs(items_dt, fc)
    for rec in recs:
        it = by[rec["item_id"]]
        rec["s2_site"] = n16.site_price(it["dt_obj_orig"], it["an_obj"])
    return hashes, items_dt, recs, by, boot, fc


def close(check, what, a, b, tol=TOL):
    check.close("R", what, a, b, tol)


def count_cells(recs, boot, with_ci=True) -> OrderedDict:
    """Every headline count of one set of records (the design's list and the extensions)."""
    out = OrderedDict()
    for dtok, delta in DELTAS.items():
        costly = [r for r in recs if n13.costly_of(r, delta) == 1]
        low = [r for r in recs if n13.costly_of(r, delta) == 0]
        und = [r for r in recs if n13.costly_of(r, delta) is None]
        out["costly" + dtok] = len(costly)
        out["low" + dtok] = len(low)
        out["und" + dtok] = len(und)
        out["costlyfield" + dtok] = sum(1 for r in costly if r["split"] == "field_changing")
        out["costlyseq" + dtok] = sum(1 for r in costly if r["split"] == "sequencing_only")
        for g, (_lab, fl) in GATES.items():
            s = n13.score(boot, recs, fl, delta, with_ci=with_ci)
            out[g + "_miss" + dtok] = s["miss"]
            out[g + "_missfield" + dtok] = sum(1 for r, m in zip(s["_costly"], s["_miss"])
                                               if m and r["split"] == "field_changing")
            out[g + "_fr" + dtok] = s["fr"]
            out[g + "_frshare" + dtok] = s["fr_share"]
            out[g + "_frlo" + dtok] = s["fr_lo"]
            out[g + "_frhi" + dtok] = s["fr_hi"]
            out[g + "_frben" + dtok] = sum(1 for r, f in zip(s["_cheap"], s["_fr"])
                                           if f and r["primary_class"] == "benign")
            out[g + "_ref" + dtok] = s["costly"] - s["miss"]
    return out


def cmd_repro(args) -> int:
    t0 = time.time()
    check = D.Checker()
    out = RESULTS / "repro"
    out.mkdir(parents=True, exist_ok=True)
    rd = replay_dir("published")
    rep_replay = json.loads((rd / "replay_assertions.json").read_text())
    check.true("R", "the published replay passed its own assertions",
               rep_replay.get("status") == "PASS", rep_replay.get("status"))
    meta = json.loads((rd / "replay_meta.json").read_text())
    check.true("R", "the published replay covered all 60 instances", meta["instances"] == 60
               and not meta["smoke"], (meta["instances"], meta["smoke"]))
    for name, digest in meta["outputs"].items():
        check.true("R", "replay output {} carries its digest".format(name),
                   sha256_file(rd / name) == digest)
    mine = OrderedDict((r["item_id"], r) for r in read_jsonl(rd / "items.jsonl"))
    fi_mine = read_jsonl(rd / "fullinfo.jsonl")

    # ---- the published side, through N16's loaders
    hashes, items_dt, precs, pby, boot, pfc = published_records(check)
    pub_items = OrderedDict((r["item_id"], r) for r in items_dt if r["set"] == "published")
    check.true("R", "2,000 published items in both", len(mine) == len(pub_items) == 2000,
               (len(mine), len(pub_items)))
    # ---- per item: the census quantities
    n_float = 0
    CODE_DIFF = []
    for iid, p in pub_items.items():
        m = mine.get(iid)
        if m is None:
            check.true("R", "item replayed: " + iid, False)
            continue
        for k in ITEM_EXACT:
            check.true("R", "{} equal on {}".format(k, iid), m.get(k) == p.get(k),
                       "{!r} vs {!r}".format(m.get(k), p.get(k)))
        cm_, cp_ = list(m.get("dt_codes") or []), list(p.get("dt_codes") or [])
        if cm_ == cp_:
            check.true("R", "dt_codes equal on " + iid, True)
        else:
            ok = (set(cm_) - set(cp_) == {RUNNING_CODE} and set(cp_) <= set(cm_)
                  and not m["issuable"] and bool(m.get("names_running_any"))
                  and m["dt_term_cert"] == p["dt_term_cert"]
                  and m["dt_stage_cert"] == p["dt_stage_cert"])
            check.true("R", "dt_codes differ only by the running-work code, on a "
                       "non-issuable item: " + iid, ok, "{} vs {}".format(cm_, cp_))
            CODE_DIFF.append(iid)
        for k in ITEM_FLOAT:
            a, b = m.get(k), p.get(k)
            close(check, "{} on {}".format(k, iid), a, b)
            n_float += 1
    iss = [r for r in mine.values() if r["issuable"]]
    check.true("R", "1,723 issuable", len(iss) == 1723, len(iss))
    # ---- FI prices, item by item, against results/n11_forecast/fullinfo_direct.jsonl
    fi_pub = {}
    for r in read_jsonl(n13.IN["fullinfo"]):
        fi_pub[r["uid"]] = r
    fi_m = {r["uid"]: r for r in fi_mine}
    check.true("R", "FI rows: the same items", set(fi_m) == set(fi_pub), (len(fi_m), len(fi_pub)))
    for uid, p in fi_pub.items():
        m = fi_m.get(uid)
        if m is None:
            continue
        check.true("R", "FI stage on " + uid, m["p"]["stage_cert"] == p["p"]["stage_cert"])
        for g in F.DESIGNS + ("D-ABS-orig",):
            close(check, "FI price {} on {}".format(g, uid), m["prices"][g], p["prices"][g])
        for k in ("obj", "obj_orig", "lb", "gap", "ref2"):
            close(check, "FI {} on {}".format(k, uid), m["p"][k], p["p"][k])
    # ---- records: prices, the second prices, the realised cost, every disposition
    recs, by, priced, krows = build_records(list(mine.values()), fi_mine)
    check.true("R", "1,356 priced reference proposals", len(recs) == 1356, len(recs))
    pmap = {r["item_id"]: r for r in precs}
    check.true("R", "the same priced items", set(pmap) == {r["item_id"] for r in recs})
    pk = {r["item_id"]: r for r in n13.read_csv(n13.IN["rows_direct"]) if r["dataset"] == "direct_td"}
    for r in recs:
        iid = r["item_id"]
        p = pmap.get(iid)
        if p is None:
            continue
        close(check, "t_d on " + iid, r["t_d"], p["t_d"])
        close(check, "g_orig on " + iid, r["g_orig"], p["g_orig"])
        close(check, "s2_site on " + iid, r["s2_site"], p["s2_site"])
        # the published K and FI records are read from N11_rows_forecast.csv (6 decimals)
        for g in n13.DESIGNS:
            close(check, "price on K {} on {} (printed)".format(g, iid), r["p_" + g],
                  p["p_" + g], 5.0000001e-7)
            close(check, "price with FI {} on {} (printed)".format(g, iid), r["fi"]["p_" + g],
                  p["fi"]["p_" + g], 5.0000001e-7)
            check.true("R", "refers on K, {} on {}".format(g, iid),
                       r["ref_" + g] == p["ref_" + g])
            check.true("R", "refers with FI, {} on {}".format(g, iid),
                       r["fi"]["ref_" + g] == p["fi"]["ref_" + g])
            x = pk[iid]
            close(check, "price on K {} on {} (N11_rows_direct)".format(g, iid), r["p_" + g],
                  n13.fnum(x["p_" + g]), 5.0000001e-7)
        check.true("R", "union flag on " + iid, r["ref_" + n13.UNION] == p["ref_" + n13.UNION])
        close(check, "realised cost lower end on " + iid, r["lo"], p["lo"], 6e-7)
        close(check, "realised cost upper end on " + iid, r["hi"], p["hi"], 6e-7)
        lo2, hi2 = n16.realised_range(by[iid]["rw_obj_orig"], by[iid]["pub_anchor_wwt"],
                                      r["instance_id"], D.full_brackets())
        close(check, "realised cost = n16.realised_range (lower) on " + iid, r["lo"], lo2)
        close(check, "realised cost = n16.realised_range (upper) on " + iid, r["hi"], hi2)
        pe = pby[iid]
        lo3, hi3 = n16.realised_range(pe["rw_obj_orig"], pe["pub_anchor_wwt"], r["instance_id"],
                                      D.full_brackets())
        close(check, "realised cost lower end, full precision, on " + iid, r["lo"], lo3)
        close(check, "realised cost upper end, full precision, on " + iid, r["hi"], hi3)
        check.true("R", "edit type on " + iid, r["split"] == p["split"])
        for delta in DELTAS.values():
            check.true("R", "cost class at {} on {}".format(delta, iid),
                       n13.costly_of(r, delta) == n13.costly_of(p, delta))
        for g, (_lab, fl) in GATES.items():
            check.true("R", "disposition {} on {}".format(g, iid), bool(fl(r)) == bool(fl(p)))
    # ---- the published counts (the design's list and N16's cells)
    cm = count_cells(recs, boot, with_ci=True)
    cp = count_cells(precs, boot, with_ci=True)
    for k in cm:
        v1, v2 = cm[k], cp[k]
        if isinstance(v1, float) or isinstance(v2, float):
            close(check, "cell {} equals the published records".format(k), v1, v2)
        else:
            check.true("R", "cell {} equals the published records".format(k), v1 == v2, (v1, v2))
    want = OrderedDict([("costlyTwenty", 186), ("lowTwenty", 1170), ("costlyTen", 208),
                        ("lowTen", 1148), ("undTwenty", 0), ("cert_refTwenty", 168),
                        ("certfi_refTwenty", 168), ("cert_missTwenty", 18),
                        ("cert_missfieldTwenty", 18), ("certsp_missTwenty", 0),
                        ("cert_frTwenty", 15), ("certsp_frTwenty", 22), ("certsite_frTwenty", 21),
                        ("certsite_missTwenty", 0), ("rel_frTwenty", 33), ("relsp_frTwenty", 40),
                        ("rel_missTwenty", 18), ("relsp_missTwenty", 0),
                        ("certsp_frbenTwenty", 0), ("relsp_frbenTwenty", 1),
                        ("cert_missTen", 25), ("certsp_missTen", 6), ("certsp_frTen", 6),
                        ("rel_missTen", 21), ("relsp_frTen", 20), ("costlyfieldTwenty", 60)])
    for k, v in want.items():
        check.true("R", "design cell {} = {}".format(k, v), cm[k] == v, cm[k])
    costly20 = [r for r in recs if n13.costly_of(r, 0.20) == 1]
    rk = {r["item_id"] for r in costly20 if flag_cert(r)}
    rf = {r["item_id"] for r in costly20 if flag_cert_fi(r)}
    check.true("R", "the certificate refers the same 168 on K and with FI", rk == rf and
               len(rk) == 168, (len(rk), len(rf), len(rk & rf)))
    applied = [r for r in costly20 if not flag_cert(r)]
    check.true("R", "the 18 applied are all field edits",
               all(r["split"] == "field_changing" for r in applied) and len(applied) == 18)
    check.true("R", "the second price refers 18 of 18",
               all(flag_cert_sp(r) for r in applied))
    # the published share and interval of the gate with the second price (N16 I1)
    n16m = n13.macros_of(ANALYSIS / "N16_macros.tex")
    check.true("R", "low-cost referral share with the second price = N16 I1 (1.9% [0.8%, 3.0%])",
               (n16.pctv(cm["certsp_frshareTwenty"]), n16.pctv(cm["certsp_frloTwenty"]),
                n16.pctv(cm["certsp_frhiTwenty"])) == ("1.9\\%", "0.8\\%", "3.0\\%"),
               (cm["certsp_frshareTwenty"], cm["certsp_frloTwenty"], cm["certsp_frhiTwenty"]))
    rep = check.report()
    rep.update(version=VERSION, finished=now_iso(), wall_s=round(time.time() - t0, 1),
               definitions_sha=definitions_sha(), code=code_hashes(),
               replay_outputs=meta["outputs"], published_inputs=hashes,
               n16_macros_sha256=sha256_file(ANALYSIS / "N16_macros.tex"),
               cells=OrderedDict((k, v) for k, v in cm.items()), n_float_items=n_float,
               running_code_only_differences=sorted(CODE_DIFF),
               n16_macro_count=len(n16m))
    write_json(REPRO_PATH, rep)
    if check.failures:
        print("REPRODUCTION CHECK FAILED ({} of {}):".format(rep["n_failures"], rep["n_checks"]),
              file=sys.stderr)
        for f in check.failures[:60]:
            print("  -", f, file=sys.stderr)
        return 2
    print("[n17 repro] PASS: {} checks in {:.0f}s".format(rep["n_checks"], rep["wall_s"]))
    return 0


# --------------------------------------------------------------------------- #
# analyse: Part 1 and Part 2 tables, rows, macros, summary                     #
# --------------------------------------------------------------------------- #
def canon(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def grp(n) -> str:
    return n16.grp(n)


def pctv(x) -> str:
    return n16.pctv(x)


def pctp(x) -> str:
    return n16.pctpv(x)


def fmtn(n) -> str:
    return "{:,}".format(int(n))


def f6(x) -> str:
    return "" if x is None else "{:.6f}".format(x)


def edited_fields(op_types) -> str:
    ops = set((op_types or "").split("|"))
    out = []
    if "set_priority" in ops:
        out.append("priority")
    if "reassign_window" in ops:
        out.append("time window")
    return " and ".join(out) or "none"


class Macros:
    def __init__(self, prefix="nSeventeen"):
        self.prefix = prefix
        self.lines = ["% N17 macros ({}); generated by code/scripts/n17_heldout.py analyse "
                      "(no solve, no model call)".format(VERSION)]
        self.names = set()

    def add(self, name, value):
        full = self.prefix + name
        if not full.isalpha():
            raise SystemExit("macro name not alphabetic: " + full)
        if full in self.names:
            raise SystemExit("duplicate macro " + full)
        self.names.add(full)
        self.lines.append("\\newcommand{\\" + full + "}{" + str(value) + "}")


def check_replay(tag, reading="primary") -> tuple:
    rd = replay_dir(tag, reading)
    rep = json.loads((rd / "replay_assertions.json").read_text())
    if rep.get("status") != "PASS":
        raise SystemExit("replay {} {} did not pass".format(tag, reading))
    meta = json.loads((rd / "replay_meta.json").read_text())
    if meta["instances"] != 60 or meta["smoke"]:
        raise SystemExit("replay {} {} is not a full run".format(tag, reading))
    for name, digest in meta["outputs"].items():
        if sha256_file(rd / name) != digest:
            raise SystemExit("replay output {} {} {} changed".format(tag, reading, name))
    return read_jsonl(rd / "items.jsonl"), read_jsonl(rd / "fullinfo.jsonl"), meta, rep


def unit_keys(items, rows) -> dict:
    """item_id -> (instance, frozen set, t_d, canonical proposal) of each priced proposal."""
    by = {r["item_id"]: r for r in rows}
    out = {}
    for r in items:
        if r["issuable"] and r["dt_stage_cert"] == "qual":
            ops = D.canonical_ops(by[r["item_id"]])
            if ops:
                out[r["item_id"]] = (r["instance_id"], r["frozen_seed"], "{:.9f}".format(
                    float(r["t_d"])), canon(ops))
    return out


def opt_of(iid, full_br):
    b = full_br.get((iid, D.BASE_FP))
    if b is None:
        return None, None
    lo_e, up_e, _p = D.ends(b)
    return lo_e, up_e


def miss_reason(r, full_br) -> str:
    """One factual line on why a costly field edit passes a gate with a second price."""
    dk = r["obj_orig_K"] - r["wt_anchor_K"]
    dr = r["rw_obj_orig"] - r["anchor_pub"]
    olo, oup = opt_of(r["instance_id"], full_br)
    if r["hi"] is not None and r["hi"] <= TAU:
        kind = "realised cost at most 0.20, below the gate's tolerance"
    elif dk < 0.5 * dr:
        kind = "most of the realised damage is not on the known board at t_d"
    elif oup is not None and r["lb_anchor_K"] > oup:
        kind = "the bound of the untouched known board exceeds the full-window optimum"
    else:
        kind = "damage on K close to the realised damage; see the prices"
    return ("g_orig {:.4f} ({} 0.20), s2_site {:.4f}; damage on the original values {:.2f} bh "
            "on K against {:.2f} bh realised; LB_anchor_K {:.2f} bh, full-window optimum "
            "[{:.2f}, {:.2f}] bh; known share {:.1%}: {}".format(
                r["g_orig"], "<=" if r["g_orig"] <= TAU else ">", r["s2_site"], dk, dr,
                r["lb_anchor_K"], olo or 0.0, oup or 0.0, r["known_share"], kind))


def f1_cells(recs, delta) -> OrderedDict:
    costly = [r for r in recs if n13.costly_of(r, delta) == 1]
    rk = {(r["seed"], r["item_id"]) for r in costly if flag_cert(r)}
    rf = {(r["seed"], r["item_id"]) for r in costly if flag_cert_fi(r)}
    out = OrderedDict(costly=len(costly), K=len(rk), FI=len(rf), Both=len(rk & rf),
                      KOnly=len(rk - rf), FIOnly=len(rf - rk))
    for sp, st in (("sequencing_only", "Seq"), ("field_changing", "Field")):
        ids = {(r["seed"], r["item_id"]) for r in costly if r["split"] == sp}
        out["n" + st] = len(ids)
        out["K" + st] = len(rk & ids)
        out["FI" + st] = len(rf & ids)
    return out


def headline_rows(scope, cells, n_iss, n_priced, delta, dtok):
    body = []
    for g, (lab, _fl) in GATES.items():
        body.append([scope, "{:.2f}".format(delta), lab, n_iss, n_priced,
                     cells["costly" + dtok], cells["costlyfield" + dtok],
                     cells[g + "_miss" + dtok], cells[g + "_missfield" + dtok],
                     "{} of {}".format(cells[g + "_fr" + dtok], grp(cells["low" + dtok])
                                       .replace("{,}", ",")),
                     "{} [{}, {}]".format(pctp(cells[g + "_frshare" + dtok]),
                                          pctp(cells[g + "_frlo" + dtok]),
                                          pctp(cells[g + "_frhi" + dtok])),
                     cells[g + "_frben" + dtok]])
    return body


HEAD = ["scope", "delta", "gate", "issuable", "priced", "costly", "costly field edits",
        "costly applied", "costly field edits applied", "low-cost referred",
        "low-cost referral share [95% CI]", "benign among the referred"]


def cell_macros(M, scope, cells, n_iss, n_priced):
    M.add(scope + "Issuable", grp(n_iss))
    M.add(scope + "Priced", grp(n_priced))
    for dtok in DELTAS:
        for k in ("costly", "low", "und", "costlyfield", "costlyseq"):
            M.add(scope + {"costly": "Costly", "low": "Low", "und": "Undecided",
                           "costlyfield": "CostlyField", "costlyseq": "CostlySeq"}[k] + dtok,
                  grp(cells[k + dtok]))
        for g, gt in GATE_TOK.items():
            M.add(scope + gt + "Applied" + dtok, grp(cells[g + "_miss" + dtok]))
            M.add(scope + gt + "AppliedField" + dtok, grp(cells[g + "_missfield" + dtok]))
            M.add(scope + gt + "Referred" + dtok, grp(cells[g + "_ref" + dtok]))
            M.add(scope + gt + "LowRef" + dtok, grp(cells[g + "_fr" + dtok]))
            M.add(scope + gt + "LowRefShare" + dtok, pctv(cells[g + "_frshare" + dtok]))
            M.add(scope + gt + "LowRefLo" + dtok, pctv(cells[g + "_frlo" + dtok]))
            M.add(scope + gt + "LowRefHi" + dtok, pctv(cells[g + "_frhi" + dtok]))
            M.add(scope + gt + "LowRefBenign" + dtok, grp(cells[g + "_frben" + dtok]))


def f1_macros(M, scope, f1, dtok):
    for k, v in f1.items():
        tok = {"costly": "Costly", "K": "K", "FI": "FI", "Both": "Both", "KOnly": "KOnly",
               "FIOnly": "FIOnly", "nSeq": "CostlySeq", "KSeq": "KSeq", "FISeq": "FISeq",
               "nField": "CostlyField", "KField": "KField", "FIField": "FIField"}[k]
        M.add(scope + "FOne" + tok + dtok, grp(v))


def qrow(xs):
    if not xs:
        return ["", "", "", "", "", ""]
    a = np.asarray(xs, dtype=float)
    q = np.percentile(a, [0, 25, 50, 75, 100])
    return ["{:.2f}".format(v) for v in q] + ["{:.2f}".format(a.mean())]


def cmd_analyse(args) -> int:
    t0 = time.time()
    rep = require_repro()
    import suite_gate as sg

    full_br = D.full_brackets()
    pchk = D.Checker()
    pub_rows = D.load_published(pchk)
    if pchk.failures:
        raise SystemExit("published suite check failed")
    pub_text = {(r["instance"]["instance_id"], r["instruction"]) for r in pub_rows}
    pub_gold = {(r["instance"]["instance_id"], canon(r["gold_ops"])) for r in pub_rows
                if r.get("gold_ops")}
    p_items, p_fi, p_meta, _p_rep = check_replay("published")
    pub_units = set(unit_keys(p_items, pub_rows).values())
    hashes, items_dt, precs, pby, boot, pfc = published_records(D.Checker())
    for r in precs:
        r["seed"] = PUBLISHED_SEED
        r["subclass"] = pby[r["item_id"]]["subclass"]
    gen_chk = json.loads((RESULTS / "build_published_check.json").read_text())
    if not gen_chk["identical_to_published"]:
        raise SystemExit("the generator does not reproduce the published suite")

    M = Macros()
    MDL = []

    def md(*lines):
        MDL.extend(lines)

    def table(head, body):
        MDL.append("| " + " | ".join(str(h) for h in head) + " |")
        MDL.append("|" + "---|" * len(head))
        for row in body:
            MDL.append("| " + " | ".join(str(c) for c in row) + " |")
        MDL.append("")

    # ---- per seed: suite, duplicates, replay, records
    seeds = OrderedDict()
    seen_text, seen_gold = defaultdict(set), defaultdict(set)
    for seed in SEEDS:
        brec = json.loads((RESULTS / "build_{}.json".format(seed)).read_text())
        rows = read_jsonl(suite_dir(seed) / "suite.jsonl")
        if sha256_file(suite_dir(seed) / "suite.jsonl") != brec["suite_sha256"]:
            raise SystemExit("suite {} changed after its build".format(seed))
        dup_text = {r["item_id"] for r in rows
                    if (r["instance"]["instance_id"], r["instruction"]) in pub_text}
        dup_gold = {r["item_id"] for r in rows if r.get("gold_ops")
                    and (r["instance"]["instance_id"], canon(r["gold_ops"])) in pub_gold}
        dup = dup_text | dup_gold
        items, fi_rows, meta, _rep = check_replay(str(seed))
        if meta["suite_sha256"] != brec["suite_sha256"]:
            raise SystemExit("replay {} ran on another suite file".format(seed))
        recs, by, _pr, _kr = build_records(items, fi_rows)
        ukeys = unit_keys(items, rows)
        for rec in recs:
            rec["seed"] = seed
            rec["dup"] = rec["item_id"] in dup
            rec["dup_text"] = rec["item_id"] in dup_text
            rec["dup_gold"] = rec["item_id"] in dup_gold
            rec["unit_dup"] = ukeys.get(rec["item_id"]) in pub_units
        cross_ids = set()
        for r in rows:
            if r["item_id"] in dup:
                continue
            kt = (r["instance"]["instance_id"], r["instruction"])
            kg = (r["instance"]["instance_id"], canon(r["gold_ops"])) if r.get("gold_ops") else None
            if any(kt in seen_text[s] or (kg is not None and kg in seen_gold[s]) for s in seeds):
                cross_ids.add(r["item_id"])
        cross = len(cross_ids)
        for rec in recs:
            rec["cross_dup"] = rec["item_id"] in cross_ids
        for r in rows:
            seen_text[seed].add((r["instance"]["instance_id"], r["instruction"]))
            if r.get("gold_ops"):
                seen_gold[seed].add((r["instance"]["instance_id"], canon(r["gold_ops"])))
        keep_items = [r for r in items if r["item_id"] not in dup]
        seeds[seed] = dict(brec=brec, rows=rows, items=items, recs=recs, dup=dup,
                           dup_text=dup_text, dup_gold=dup_gold, cross=cross, meta=meta,
                           n_iss=sum(1 for r in keep_items if r["issuable"]),
                           n_items=len(keep_items),
                           by_class=Counter(r["primary_class"] for r in rows
                                            if r["item_id"] not in dup))

    # ---- cells
    scopes = OrderedDict()
    for seed, s in seeds.items():
        held = [r for r in s["recs"] if not r["dup"]]
        scopes[SEED_TOK[seed]] = dict(recs=held, n_iss=s["n_iss"], n_items=s["n_items"])
    pooled = [r for s in seeds.values() for r in s["recs"] if not r["dup"]]
    scopes["Pooled"] = dict(recs=pooled, n_iss=sum(s["n_iss"] for s in seeds.values()),
                            n_items=sum(s["n_items"] for s in seeds.values()))
    for k, sc in scopes.items():
        sc["cells"] = count_cells(sc["recs"], boot, with_ci=True)
        sc["f1"] = OrderedDict((dtok, f1_cells(sc["recs"], d)) for dtok, d in DELTAS.items())
    pub_cells = count_cells(precs, boot, with_ci=True)
    for k, v in rep["cells"].items():
        a = pub_cells[k]
        if (a is None) != (v is None) or (a is not None and abs(float(a) - float(v)) > 1e-12):
            raise SystemExit("published cell {} differs from the reproduction check".format(k))
    unit_free = [r for r in pooled if not r["unit_dup"]]
    unit_cells = count_cells(unit_free, boot, with_ci=True)
    cross_free = [r for r in pooled if not r["cross_dup"]]
    cross_cells = count_cells(cross_free, boot, with_ci=True)

    # ---- macros: seeds, suites, duplicates, cells
    for seed, tok in SEED_TOK.items():
        s = seeds[seed]
        M.add(tok + "Value", seed)
        M.add(tok + "Items", grp(len(s["rows"])))
        M.add(tok + "Dup", grp(len(s["dup"])))
        M.add(tok + "DupText", grp(len(s["dup_text"])))
        M.add(tok + "DupGold", grp(len(s["dup_gold"])))
        M.add(tok + "HeldOut", grp(s["n_items"]))
        M.add(tok + "CrossSeedDup", grp(s["cross"]))
    M.add("PooledItems", grp(sum(len(s["rows"]) for s in seeds.values())))
    M.add("PooledDup", grp(sum(len(s["dup"]) for s in seeds.values())))
    M.add("PooledHeldOut", grp(scopes["Pooled"]["n_items"]))
    M.add("Seeds", len(SEEDS))
    M.add("Windows", 60)
    for k, sc in scopes.items():
        cell_macros(M, k, sc["cells"], sc["n_iss"], len(sc["recs"]))
        for dtok in DELTAS:
            f1_macros(M, k, sc["f1"][dtok], dtok)
    M.add("PooledSameUnit", grp(sum(1 for r in pooled if r["unit_dup"])))
    for dtok in DELTAS:
        for g in ("cert", "certsp", "certsite"):
            M.add("PooledNoSameUnit" + GATE_TOK[g] + "Applied" + dtok,
                  grp(unit_cells[g + "_miss" + dtok]))
            M.add("PooledNoSameUnit" + GATE_TOK[g] + "LowRefShare" + dtok,
                  pctv(unit_cells[g + "_frshare" + dtok]))
        M.add("PooledNoSameUnitCostly" + dtok, grp(unit_cells["costly" + dtok]))
        for g in ("cert", "certsp", "certsite"):
            M.add("PooledNoCrossSeed" + GATE_TOK[g] + "Applied" + dtok,
                  grp(cross_cells[g + "_miss" + dtok]))
            M.add("PooledNoCrossSeed" + GATE_TOK[g] + "LowRefShare" + dtok,
                  pctv(cross_cells[g + "_frshare" + dtok]))
        M.add("PooledNoCrossSeedCostly" + dtok, grp(cross_cells["costly" + dtok]))
    M.add("PooledCrossSeedPriced", grp(sum(1 for r in pooled if r["cross_dup"])))
    M.add("ReproChecks", grp(rep["n_checks"]))
    M.add("PubCertSPLowRefShareTwenty", pctv(pub_cells["certsp_frshareTwenty"]))

    # ---- who the low-cost referrals are (pooled, delta 0.20 and 0.10)
    lowref = OrderedDict()
    for dtok, delta in DELTAS.items():
        low = [r for r in pooled if n13.costly_of(r, delta) == 0]
        for g in ("cert", "certsp", "certsite"):
            lowref[(g, dtok)] = [r for r in low if GATES[g][1](r)]
        lowref[("extra", dtok)] = [r for r in low if flag_cert_sp(r) and not flag_cert(r)]
        ex = lowref[("extra", dtok)]
        M.add("PooledCertSPLowRefExtra" + dtok, grp(len(ex)))
        for cls, ct in n16.CLS_TOK.items():
            M.add("PooledCertSPLowRefExtra" + ct + dtok,
                  grp(sum(1 for r in ex if r["primary_class"] == cls)))

    # ---- the applied costly field edits behind the gate with the second price
    misses = OrderedDict()
    for dtok, delta in DELTAS.items():
        for g in ("certsp", "certsite", "relsp", "reltwsp"):
            fl = GATES[g][1]
            misses[(g, dtok)] = [r for r in pooled if n13.costly_of(r, delta) == 1
                                 and not fl(r)]

    # ---- rows
    cols = ["seed", "item_id", "instance_id", "stratum", "primary_class", "subclass",
            "edit_type", "edited_fields", "op_types", "duplicate_text", "duplicate_gold",
            "same_priced_unit_as_published", "held_out", "known_share", "t_d", "t_start",
            "p_cert_K", "p_cert_FI", "p_certm_K", "p_rel2_K", "p_rel2_FI", "g_orig", "s2_site",
            "obj_orig_K", "lb_anchor_K", "wt_anchor_K", "realised_damage_bh",
            "realised_cost_lo", "realised_cost_hi", "cost_class_020", "cost_class_010"] + \
        ["refers_" + g for g in GATES]
    out_rows = []
    for seed, s in seeds.items():
        for r in sorted(s["recs"], key=lambda x: x["item_id"]):
            cc = {d: n16.cost_word(n13.costly_of(r, d)) for d in DELTAS.values()}
            row = [seed, r["item_id"], r["instance_id"], r["stratum"], r["primary_class"],
                   r["subclass"], r["split"], edited_fields(r["op_types"]), r["op_types"],
                   r["dup_text"], r["dup_gold"], r["unit_dup"], not r["dup"],
                   "{:.6f}".format(r["known_share"]), f6(r["t_d"]),
                   f6(None if r["t_start"] is None else float(r["t_start"])),
                   f6(r["p_G-CERT"]), f6(r["fi"]["p_G-CERT"]), f6(r["p_G-CERT-M"]),
                   f6(r["p_D-REL2"]), f6(r["fi"]["p_D-REL2"]), f6(r["g_orig"]),
                   f6(r["s2_site"]), f6(r["obj_orig_K"]), f6(r["lb_anchor_K"]),
                   f6(r["wt_anchor_K"]), f6(r["dmg"]), f6(r["lo"]), f6(r["hi"]),
                   cc[0.20], cc[0.10]] + [bool(fl(r)) for _g, (_l, fl) in GATES.items()]
            out_rows.append(row)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N17 held-out rows ({}): one row per priced reference proposal of the three "
                 "fresh suites; generated by code/scripts/n17_heldout.py analyse\n".format(VERSION))
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(out_rows)

    # ---- Part 2
    part2 = cmd_issue_part(boot, full_br, M, md, table, rep, p_items, precs, pub_cells)

    # ---- summary
    MD_ALL = []

    def md2(*lines):
        MD_ALL.extend(lines)

    md2("# N17: the frozen gate with the second price on three fresh draws of the suite "
        "({})".format(VERSION), "",
        "Generated by `code/scripts/n17_heldout.py` (cores 8-11, one thread per process, "
        "worker processes pinned to cores {}) from deterministic dispatch replay and analytic "
        "bounds only: no CP-SAT, no model call, no GPU. Macros: analysis/N17_macros.tex (prefix "
        "\\nSeventeen), copied to manuscript/macros_n17.tex. Rows: analysis/N17_rows.csv{}."
        .format(",".join(str(c) for c in seeds[SEEDS[0]]["meta"]["worker_cores"]),
                ", analysis/N17_issue_rows.csv" if part2 else ""), "")
    md2("## 0. Checks passed before any held-out number", "",
        "- Frozen scripts unchanged at the start and the end of every stage: " + ", ".join(
            "{} {}".format(k, v[:12]) for k, v in FROZEN.items()) + ".",
        "- Generator: `build_suite.py` (its `main`, unmodified) pointed at the instances_v10 "
        "snapshot, rebuilt from the published seed {} gives suite.jsonl sha256 {} = the "
        "published v0.2 file ({} items, {:.0f} s); the 60 pool files match "
        "code/scripts/instance_manifest_l1.json.".format(
            PUBLISHED_SEED, gen_chk["suite_sha256"][:16], gen_chk["items"], gen_chk["wall_s"]),
        "- Reproduction check on the published suite: PASS, {} assertions ({}), item by item "
        "on 2,000 items (census quantities to 1e-9), 1,356 FI price records (to 1e-9), and "
        "every price, g_orig, s2_site, realised-cost bracket and disposition of the 1,356 "
        "priced proposals; the published cells: 1,723 issuable, 1,356 priced, 186 costly and "
        "1,170 low-cost at delta 0.20 (208 and 1,148 at 0.10), the certificate refers the same "
        "168 of 186 on K and with FI, 18 applied (all field edits), the second price refers 18 "
        "of 18, low-cost referred 15 without and 22 with the second price (1.9% [0.8%, 3.0%]), "
        "the site-schedule variant 21.".format(grp(rep["n_checks"]).replace("{,}", ","),
                                               rep["finished"]),
        "- Gate definitions hashed into the reproduction check (definitions sha256 {}) and "
        "asserted unchanged by every fresh replay and by this analysis.".format(
            rep["definitions_sha"][:16]),
        "- Each fresh replay passed its own run-fatal assertions: n11_forecast AF0 (the K "
        "pricing inside forecast_instance equals census_instance's, field by field, for every "
        "issuable item) and AF1 (the FI board reproduces the realised run where the check "
        "applies), one FI price per priced item.", "")
    md2("## 1. Definitions", "",
        "Suites: `build_suite.py --seed S --out code/suite/v1.1_heldout_S` for S in {}, the "
        "published SuiteConfig otherwise (suite_version v0.2, quotas, screens, templates, "
        "strata, the 60 pool windows and the instance stride). The direct benchmark of the "
        "paper is built on suite v0.2 alone (build_suite.py); the v1.1 extensions "
        "(build_suite_ext.py, build_suite_ext_neg.py) add the acceptance-clause items of the "
        "N3 run and are not part of the direct benchmark, so they are not redrawn.".format(
            ", ".join(str(s) for s in SEEDS)),
        "",
        "Held-out set: the items of a fresh suite whose (instance, instruction text) and whose "
        "(instance, gold operations) do not occur in the published suite. Empty gold-operation "
        "lists are not used as a key: 515 published items (V1 160, V5 200, V6 155) carry the "
        "empty list, so the key would mark every such fresh item a duplicate without any shared "
        "content.", "",
        "Replay: per instance, n11_decision_time.census_instance (issuability under the closed "
        "rule, t_d = t_known, the known board K with the fixed frozen set, the gate's price on "
        "K with the analytic lower bound, D-REL2's reference, the realised full-window run "
        "from t_d) and n11_forecast.forecast_instance with the single reading FI. Prices: "
        "n11_decision_time.build_rows (n2.prices). Realised cost: "
        "n11_forecast.attach_orig_truth = (realised weighted tardiness on the original values "
        "minus the published no-AI anchor) / max(full-window optimum of the untouched window, "
        "1 bh), bracketed by the oracle_v1 bracket of the untouched window (exists for all 60). "
        "Costly: lower end above delta; low-cost: upper end at most delta; otherwise "
        "undecided and left out of both counts (n13.costly_of).", "",
        "Gates (the frozen set): the certificate G-CERT on K at tau = 0.20; with FI: the same "
        "gate on the board with every order of the window known; with the second price: "
        "n16.sp_flag, i.e. also refer a field edit when g_orig = (obj_orig_K - LB_anchor_K) / "
        "max(LB_anchor_K, 1 bh) > 0.20; the site-schedule variant: the same with s2_site = "
        "(obj_orig_K - WT_anchor_K) / max(WT_anchor_K, 1 bh); D-REL2 at its published 0.02 and "
        "at 0.20, each with and without the second price. Applied = a costly proposal the gate "
        "does not refer. Intervals: n2.Boot cluster bootstrap over the 60 instances (seed {}, "
        "{} replicates); pooled intervals resample instances with all three seeds' items of "
        "an instance together.".format(n2.SEED, n2.B_BOOT), "")
    md2("## 2. The fresh suites", "")
    body = []
    for seed, s in seeds.items():
        b = s["brec"]
        body.append([seed, b["suite_sha256"][:16], b["items"], ", ".join(
            "{} {}".format(k, v) for k, v in sorted(b["by_class"].items())), b["instances"],
            len(s["dup_text"]), len(s["dup_gold"]), len(s["dup"]), s["n_items"],
            ", ".join("{} {}".format(k, v) for k, v in sorted(s["by_class"].items())),
            s["cross"], "{:.0f}".format(b["wall_s"])])
    MD_ALL.extend(_tab(["seed", "suite.jsonl sha256", "items", "items by class", "windows",
                        "dup (instance, text)", "dup (instance, gold ops)", "excluded",
                        "held-out items", "held-out by class",
                        "also in an earlier fresh seed (kept)", "build s"], body))
    md2("Items of a fresh suite that repeat an item of an earlier fresh seed (same instance and "
        "text or same non-empty gold operations) are kept: they are new with respect to the "
        "frozen gate. Sensitivity in section 6.", "")
    md2("## 3. Headline: costly proposals applied and low-cost proposals referred", "",
        "Costly field edits applied by the gate with the second price is the primary outcome. "
        "Rows per seed and pooled; delta 0.20 first, then 0.10.", "")
    for dtok, delta in DELTAS.items():
        body = []
        for k, sc in scopes.items():
            body += headline_rows(k, sc["cells"], sc["n_iss"], len(sc["recs"]), delta, dtok)
        body += headline_rows("published", pub_cells, 1723, 1356, delta, dtok)
        MD_ALL.extend(_tab(HEAD, body))
    md2("### Who the low-cost referrals are (pooled)", "",
        "Low-cost proposals referred, by class; 'added by the second price' = referred by the "
        "gate with the second price and not by the certificate alone.", "")
    body = []
    for dtok, delta in DELTAS.items():
        for g, lab in (("cert", GATES["cert"][0]), ("certsp", GATES["certsp"][0]),
                       ("certsite", GATES["certsite"][0]), ("extra", "added by the second price")):
            lst = lowref[(g, dtok)]
            cc = Counter(r["primary_class"] for r in lst)
            sub = Counter((r["primary_class"], r["subclass"]) for r in lst)
            body.append(["{:.2f}".format(delta), lab, len(lst), ", ".join(
                "{} {}".format(k, cc[k]) for k in D.CLASSES if cc.get(k)) or "none",
                ", ".join("{} {} {}".format(a, b, n) for (a, b), n in sub.most_common(6))
                if g == "extra" else ""])
    MD_ALL.extend(_tab(["delta", "gate", "low-cost referred", "by class",
                        "largest subclasses (added by the second price)"], body))
    md2("Undecided proposals (realised-cost bracket straddles delta, excluded from both "
        "counts): " + "; ".join("{} {} at 0.20 and {} at 0.10".format(
            k, sc["cells"]["undTwenty"], sc["cells"]["undTen"]) for k, sc in scopes.items())
        + ".", "")
    md2("## 4. Referred on K against referred with FI among the costly (the paper's F1)", "")
    body = []
    for dtok, delta in DELTAS.items():
        for k, sc in scopes.items():
            f = sc["f1"][dtok]
            body.append([k, "{:.2f}".format(delta), f["costly"], f["K"], f["FI"], f["Both"],
                         f["KOnly"], f["FIOnly"],
                         "{} / {} of {}".format(f["KSeq"], f["FISeq"], f["nSeq"]),
                         "{} / {} of {}".format(f["KField"], f["FIField"], f["nField"])])
        pf = f1_cells(precs, delta)
        body.append(["published", "{:.2f}".format(delta), pf["costly"], pf["K"], pf["FI"],
                     pf["Both"], pf["KOnly"], pf["FIOnly"],
                     "{} / {} of {}".format(pf["KSeq"], pf["FISeq"], pf["nSeq"]),
                     "{} / {} of {}".format(pf["KField"], pf["FIField"], pf["nField"])])
    MD_ALL.extend(_tab(["scope", "delta", "costly", "referred on K", "referred with FI",
                        "both", "K only", "FI only", "sequencing only: K / FI",
                        "field edits: K / FI"], body))
    md2("## 5. Costly proposals applied behind the gates with a second price", "",
        "Costly proposals the certificate alone applies, by subclass and edited field, and how "
        "many of them the gate with the second price still applies:", "")
    body = []
    for dtok, delta in DELTAS.items():
        for lab, rs in (("held-out, pooled", pooled), ("published", precs)):
            cm_ = [r for r in rs if n13.costly_of(r, delta) == 1 and not flag_cert(r)]
            grp_ = Counter((r["primary_class"], r["subclass"], r.get("split")) for r in cm_)
            for (cls, sub, sp), n in sorted(grp_.items()):
                still = sum(1 for r in cm_ if (r["primary_class"], r["subclass"], r.get("split"))
                            == (cls, sub, sp) and not flag_cert_sp(r))
                body.append(["{:.2f}".format(delta), lab, cls, sub, sp, n, still])
    MD_ALL.extend(_tab(["delta", "set", "class", "subclass", "edit type",
                        "applied by the certificate", "still applied with the second price"],
                       body))
    for (g, dtok), lst in misses.items():
        md2("### {} at delta {:.2f}: {} costly proposals applied".format(
            GATES[g][0], DELTAS[dtok], len(lst)), "")
        if not lst:
            continue
        body = []
        for r in sorted(lst, key=lambda x: (x["seed"], x["item_id"])):
            body.append([r["seed"], r["item_id"], r["primary_class"], r["subclass"], r["split"],
                         edited_fields(r["op_types"]), "{:.4f}".format(r["g_orig"]),
                         "{:.4f}".format(r["s2_site"]),
                         "[{:.4f}, {:.4f}]".format(r["lo"], r["hi"]),
                         "{:.4f}".format(r["p_G-CERT"]),
                         "" if r["p_D-REL2"] is None else "{:.4f}".format(r["p_D-REL2"]),
                         miss_reason(r, full_br) if r["split"] == "field_changing"
                         else "sequencing-only proposal; the second price is not applied"])
        MD_ALL.extend(_tab(["seed", "item", "class", "subclass", "edit type", "edited field",
                            "g_orig", "s2_site", "realised cost", "G-CERT price on K",
                            "D-REL2 price on K", "reason"], body))
    md2("## 6. Sensitivity: proposals that repeat a published priced proposal", "",
        "A held-out proposal can differ from every published item in text and gold operations "
        "and still be the same priced unit as a published one (same instance, frozen set, "
        "decision instant and canonical proposal), which gives the same outcome. {} of the {} "
        "pooled priced held-out proposals are such units. Without them:".format(
            sum(1 for r in pooled if r["unit_dup"]), len(pooled)), "")
    body = []
    for dtok, delta in DELTAS.items():
        for g in ("cert", "certsp", "certsite"):
            body.append(["{:.2f}".format(delta), GATES[g][0], unit_cells["costly" + dtok],
                         unit_cells[g + "_miss" + dtok],
                         "{} of {}".format(unit_cells[g + "_fr" + dtok], unit_cells["low" + dtok]),
                         "{} [{}, {}]".format(pctp(unit_cells[g + "_frshare" + dtok]),
                                              pctp(unit_cells[g + "_frlo" + dtok]),
                                              pctp(unit_cells[g + "_frhi" + dtok]))])
    MD_ALL.extend(_tab(["delta", "gate", "costly", "costly applied", "low-cost referred",
                        "share [95% CI]"], body))
    md2("Pooled without the {} priced proposals whose item repeats an item of an earlier fresh "
        "seed (same instance and text, or same non-empty gold operations):".format(
            sum(1 for r in pooled if r["cross_dup"])), "")
    body = []
    for dtok, delta in DELTAS.items():
        for g in ("cert", "certsp", "certsite"):
            body.append(["{:.2f}".format(delta), GATES[g][0], cross_cells["costly" + dtok],
                         cross_cells[g + "_miss" + dtok],
                         "{} of {}".format(cross_cells[g + "_fr" + dtok],
                                           cross_cells["low" + dtok]),
                         "{} [{}, {}]".format(pctp(cross_cells[g + "_frshare" + dtok]),
                                              pctp(cross_cells[g + "_frlo" + dtok]),
                                              pctp(cross_cells[g + "_frhi" + dtok]))])
    MD_ALL.extend(_tab(["delta", "gate", "costly", "costly applied", "low-cost referred",
                        "share [95% CI]"], body))
    # what the paper may say
    c = scopes["Pooled"]["cells"]
    f = scopes["Pooled"]["f1"]["Twenty"]
    per = "; ".join("seed {}: {} of {} costly field edits applied, {} of {} low-cost referred "
                    "({})".format(seed, scopes[SEED_TOK[seed]]["cells"]["certsp_missfieldTwenty"],
                                  scopes[SEED_TOK[seed]]["cells"]["costlyfieldTwenty"],
                                  scopes[SEED_TOK[seed]]["cells"]["certsp_frTwenty"],
                                  fmtn(scopes[SEED_TOK[seed]]["cells"]["lowTwenty"]),
                                  pctp(scopes[SEED_TOK[seed]]["cells"]["certsp_frshareTwenty"]))
                    for seed in SEEDS)
    md2("## 7. What the paper may say", "",
        "- Three fresh draws of the full suite from the published generator (seeds {}), on the "
        "same 60 windows and templates, give {} held-out items after removing {} that repeat a "
        "published instruction or gold operation list; {} are issuable and {} reference "
        "proposals are priced at the decision instant.".format(
            ", ".join(str(s) for s in SEEDS), fmtn(scopes["Pooled"]["n_items"]),
            sum(len(s["dup"]) for s in seeds.values()), fmtn(scopes["Pooled"]["n_iss"]),
            fmtn(len(pooled))),
        "- At delta 0.20, {} priced held-out proposals are costly, {} of them field edits. "
        "Costly proposals applied by the certificate alone: {} ({} field edits). Costly "
        "proposals applied by the frozen gate with the second price: {} ({} field edits); "
        "low-cost proposals it refers: {} of {} ({} [{}, {}], cluster bootstrap over the 60 "
        "windows), of which {} are benign items. Site-schedule variant: {} costly applied, {} "
        "low-cost referred ({}).".format(
            c["costlyTwenty"], c["costlyfieldTwenty"], c["cert_missTwenty"],
            c["cert_missfieldTwenty"], c["certsp_missTwenty"], c["certsp_missfieldTwenty"],
            c["certsp_frTwenty"], fmtn(c["lowTwenty"]), pctp(c["certsp_frshareTwenty"]),
            pctp(c["certsp_frloTwenty"]), pctp(c["certsp_frhiTwenty"]), c["certsp_frbenTwenty"],
            c["certsite_missTwenty"], c["certsite_frTwenty"], pctp(c["certsite_frshareTwenty"])),
        "- Per seed at delta 0.20: {}.".format(per),
        "- The costly field edits the gate with the second price applies at delta 0.20: {}. "
        "Damage on the original values on K: {} bh; realised damage: {} bh; g_orig: {}.".format(
            ", ".join("{} {} {} ({})".format(r["seed"], r["item_id"], r["subclass"],
                                             edited_fields(r["op_types"]))
                      for r in sorted(misses[("certsp", "Twenty")],
                                      key=lambda x: (x["seed"], x["item_id"]))) or "none",
            ", ".join("{:.1f}".format(r["obj_orig_K"] - r["wt_anchor_K"])
                      for r in sorted(misses[("certsp", "Twenty")],
                                      key=lambda x: (x["seed"], x["item_id"]))) or "none",
            ", ".join("{:.1f}".format(r["rw_obj_orig"] - r["anchor_pub"])
                      for r in sorted(misses[("certsp", "Twenty")],
                                      key=lambda x: (x["seed"], x["item_id"]))) or "none",
            ", ".join("{:.3f}".format(r["g_orig"])
                      for r in sorted(misses[("certsp", "Twenty")],
                                      key=lambda x: (x["seed"], x["item_id"]))) or "none"),
        "- Low-cost referrals added by the second price at delta 0.20 (referred with it, not "
        "by the certificate alone): {}, by class {}.".format(
            len(lowref[("extra", "Twenty")]), ", ".join(
                "{} {}".format(k, v) for k, v in sorted(Counter(
                    r["primary_class"] for r in lowref[("extra", "Twenty")]).items()))),
        "- On K against FI at delta 0.20 the certificate refers {} and {} of the {} costly "
        "held-out proposals ({} under both, {} on K only, {} with FI only).".format(
            f["K"], f["FI"], f["costly"], f["Both"], f["KOnly"], f["FIOnly"]),
        "- At delta 0.10: {} costly; costly proposals applied by the gate with the second "
        "price: {} ({} field edits); low-cost referred: {} of {} ({} [{}, {}]).".format(
            c["costlyTen"], c["certsp_missTen"], c["certsp_missfieldTen"], c["certsp_frTen"],
            fmtn(c["lowTen"]), pctp(c["certsp_frshareTen"]), pctp(c["certsp_frloTen"]),
            pctp(c["certsp_frhiTen"])),
        "- Boundary: the same 60 windows, the same templates and the same generator; the "
        "instructions, their order references and their draws are new.", "")
    MD_ALL.extend(MDL)
    MD_ALL.extend(["## Inputs", ""] + [
        "- {} `{}` sha256 {}".format(k, v["path"], v["sha256"]) for k, v in input_list(seeds)
        .items()] + ["", "Wall time of this analysis: {:.0f} s; {} macros.".format(
            time.time() - t0, len(M.names))])
    OUT_TEX.write_text("\n".join(M.lines) + "\n", encoding="utf-8")
    shutil.copyfile(OUT_TEX, OUT_MANU)
    OUT_MD.write_text("\n".join(MD_ALL) + "\n", encoding="utf-8")
    print("[n17 analyse] {} macros, {} rows, summary written ({:.0f}s)".format(
        len(M.names), len(out_rows), time.time() - t0))
    return 0


def _tab(head, body):
    out = ["| " + " | ".join(str(h) for h in head) + " |", "|" + "---|" * len(head)]
    for row in body:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    out.append("")
    return out


def input_list(seeds) -> OrderedDict:
    out = OrderedDict()

    def add(k, p):
        p = Path(p)
        out[k] = {"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)}

    add("published_suite", CODE / "suite" / "v0.2" / "suite.jsonl")
    for k, p in n13.IN.items():
        if k in ("forecast_rows", "rows_direct", "items_dt", "fullinfo", "rule_anchor",
                 "oracle_v1_brackets"):
            add(k, p)
    add("n16_macros", ANALYSIS / "N16_macros.tex")
    add("repro", REPRO_PATH)
    add("generator_check", RESULTS / "build_published_check.json")
    runs = [("published", "primary")] + [(str(s), "primary") for s in seeds] + [
        ("published", k) for k in ISSUE_READINGS]
    for t, rdg in runs:
        rd = replay_dir(t, rdg)
        for name in ("items.jsonl", "fullinfo.jsonl"):
            if (rd / name).is_file():
                add("replay_{}_{}_{}".format(t, rdg, name.split(".")[0]), rd / name)
    for seed in seeds:
        add("suite_{}".format(seed), suite_dir(seed) / "suite.jsonl")
    return out


def cmd_issue_part(boot, full_br, M, md, table, rep, p_items, precs, pub_cells):
    """Part 2: the issue time drawn inside the issuable interval (published suite)."""
    have = all((replay_dir("published", k) / "replay_meta.json").is_file()
               for k in ISSUE_READINGS)
    if not have:
        md("## 8. Part 2: issue-time sensitivity", "",
           "Not run: the replays `replay --suite published --reading issue_uniform` and "
           "`--reading issue_mid` are not on disk.", "")
        return False
    prim = {r["item_id"]: r for r in p_items}
    md("## 8. Part 2: issue-time sensitivity on the published suite", "",
       "The paper gates each instruction at its earliest decision instant t_d (every order it "
       "names is known). It stays issuable until the first start of an order it names (the "
       "closed rule). Uniform: one issue time per issuable instruction, t_d + u (t_start - "
       "t_d) with u from numpy default_rng({}) over the issuable items in item-id order; "
       "midpoint: (t_d + t_start) / 2; an instruction with an empty interval (t_start = t_d, or "
       "no named order in the window) keeps t_d. At the drawn time the known board, the "
       "reference proposal's price, the FI board and the realised run are all rebuilt by the "
       "same functions (census_instance and forecast_instance), with the drawn time passed "
       "where t_d was; the realised cost keeps the published no-AI anchor. The issue time "
       "reaches census_instance through in-memory wrappers of D.issuability and "
       "D.decision_instant_of (no file changed).".format(ISSUE_SEED), "")
    rows_out = []
    part2_miss = OrderedDict()
    part2_lost = OrderedDict()
    part2_facts = []
    body_shift = []
    body_head = {dtok: [] for dtok in DELTAS}
    body_f1 = []
    for rdg, tok in ISSUE_READINGS.items():
        items, fi_rows, meta, _rep = check_replay("published", rdg)
        times = json.loads((replay_dir("published", rdg) / "issue_times.json").read_text())
        recs, by, _pr, _kr = build_records(items, fi_rows)
        for r in recs:
            r["seed"] = rdg
        n_iss = sum(1 for r in items if r["issuable"])
        cells = count_cells(recs, boot, with_ci=True)
        cell_macros(M, "Issue" + tok, cells, n_iss, len(recs))
        f1 = OrderedDict((dtok, f1_cells(recs, d)) for dtok, d in DELTAS.items())
        for dtok in DELTAS:
            f1_macros(M, "Issue" + tok, f1[dtok], dtok)
        iss_ids = [k for k, r in prim.items() if r["issuable"]]
        shifts = [float(times[k]) - float(prim[k]["t_d"]) for k in iss_ids]
        zero = sum(1 for x in shifts if x == 0.0)
        ks_p = [prim[k]["n_known"] / (prim[k]["n_completed"] + prim[k]["n_known"]
                                      + prim[k]["n_unknown"]) for k in iss_ids]
        byi = {r["item_id"]: r for r in items}
        ks_i = [byi[k]["n_known"] / (byi[k]["n_completed"] + byi[k]["n_known"]
                                     + byi[k]["n_unknown"]) for k in iss_ids]
        q = qrow(shifts)
        body_shift.append([tok, "drawn time minus t_d (bh)"] + q + [zero, len(shifts)])
        body_shift.append([tok, "known share at t_d"] + qrow(ks_p) + ["", len(ks_p)])
        body_shift.append([tok, "known share at the drawn time"] + qrow(ks_i) + ["", len(ks_i)])
        for nm, vals in (("ShiftMedian", float(np.median(shifts))),
                         ("ShiftMean", float(np.mean(shifts))),
                         ("ShiftQOne", float(np.percentile(shifts, 25))),
                         ("ShiftQThree", float(np.percentile(shifts, 75))),
                         ("ShiftMax", float(np.max(shifts))),
                         ("KnownShareMedian", float(np.median(ks_i))),
                         ("KnownShareMedianTd", float(np.median(ks_p)))):
            M.add("Issue" + tok + nm, "{:.1f}".format(vals) if "Shift" in nm else
                  pctv(vals))
        M.add("Issue" + tok + "ShiftZero", grp(zero))
        for dtok, delta in DELTAS.items():
            body_head[dtok] += headline_rows(tok, cells, n_iss, len(recs), delta, dtok)
            fz = f1[dtok]
            body_f1.append([tok, "{:.2f}".format(delta), fz["costly"], fz["K"], fz["FI"],
                            fz["Both"], fz["KOnly"], fz["FIOnly"],
                            "{} / {} of {}".format(fz["KField"], fz["FIField"], fz["nField"])])
        for r in sorted(recs, key=lambda x: x["item_id"]):
            p = prim[r["item_id"]]
            ksp = p["n_known"] / (p["n_completed"] + p["n_known"] + p["n_unknown"])
            cc = {d: n16.cost_word(n13.costly_of(r, d)) for d in DELTAS.values()}
            rows_out.append([rdg, r["item_id"], r["instance_id"], r["primary_class"],
                             r["split"], f6(float(p["t_d"])), f6(r["t_d"]),
                             f6(r["t_d"] - float(p["t_d"])), "{:.6f}".format(ksp),
                             "{:.6f}".format(r["known_share"]), f6(r["p_G-CERT"]),
                             f6(r["fi"]["p_G-CERT"]), f6(r["p_D-REL2"]), f6(r["g_orig"]),
                             f6(r["s2_site"]), f6(r["lo"]), f6(r["hi"]), cc[0.20], cc[0.10]]
                            + [bool(fl(r)) for _g, (_l, fl) in GATES.items()])
        lost = [k for k in iss_ids if prim[k]["dt_stage_cert"] == "qual"
                and byi[k]["dt_stage_cert"] != "qual"]
        gained = [k for k in iss_ids if prim[k]["dt_stage_cert"] != "qual"
                  and byi[k]["dt_stage_cert"] == "qual"]
        why = Counter((byi[k]["dt_term_cert"], "|".join(byi[k]["dt_codes"] or []))
                      for k in lost)
        part2_lost[tok] = (len(lost), len(gained), why,
                           Counter(prim[k]["primary_class"] for k in lost))
        M.add("Issue" + tok + "PricedLost", grp(len(lost)))
        M.add("Issue" + tok + "PricedGained", grp(len(gained)))
        miss = [r for r in recs if n13.costly_of(r, 0.20) == 1 and not flag_cert_sp(r)]
        md_lines = []
        for r in sorted(miss, key=lambda x: x["item_id"]):
            md_lines.append("  - {} ({} {}, {}): g_orig {:.4f}, s2_site {:.4f}, realised "
                            "cost [{:.4f}, {:.4f}]; {}".format(
                                r["item_id"], r["primary_class"], r["subclass"], r["split"],
                                r["g_orig"], r["s2_site"], r["lo"], r["hi"],
                                miss_reason(r, full_br) if r["split"] == "field_changing"
                                else "sequencing only"))
        part2_miss[tok] = md_lines
        part2_facts.append(
            "- Issue time {}: issue time minus t_d median {:.2f} bh, Q3 {:.2f} bh, max {:.1f} bh, "
            "{} of {} issuable instructions with an empty interval; {} proposals priced, {} "
            "costly at delta 0.20 ({} field edits); costly applied: certificate alone {}, with "
            "the second price {}; low-cost referred with the second price {} of {} ({} [{}, "
            "{}]); on K against FI the certificate refers {} and {} of the costly.".format(
                tok, float(np.median(shifts)), float(np.percentile(shifts, 75)),
                float(np.max(shifts)), zero, len(shifts), len(recs), cells["costlyTwenty"],
                cells["costlyfieldTwenty"], cells["cert_missTwenty"], cells["certsp_missTwenty"],
                cells["certsp_frTwenty"], fmtn(cells["lowTwenty"]),
                pctp(cells["certsp_frshareTwenty"]), pctp(cells["certsp_frloTwenty"]),
                pctp(cells["certsp_frhiTwenty"]), f1["Twenty"]["K"], f1["Twenty"]["FI"]))
    for dtok, delta in DELTAS.items():
        body_head[dtok] += headline_rows("primary (published)", pub_cells, 1723, 1356, delta,
                                         dtok)
        md("### Headline at delta {:.2f}".format(delta), "")
        table(HEAD, body_head[dtok])
    pf = OrderedDict((dtok, f1_cells(precs, d)) for dtok, d in DELTAS.items())
    for dtok, delta in DELTAS.items():
        fz = pf[dtok]
        body_f1.append(["primary (published)", "{:.2f}".format(delta), fz["costly"], fz["K"],
                        fz["FI"], fz["Both"], fz["KOnly"], fz["FIOnly"],
                        "{} / {} of {}".format(fz["KField"], fz["FIField"], fz["nField"])])
    md("### Referred on K against FI among the costly", "")
    table(["issue time", "delta", "costly", "referred on K", "referred with FI", "both",
           "K only", "FI only", "field edits: K / FI"], body_f1)
    md("### Drawn issue time and known share (issuable instructions)", "")
    table(["issue time", "quantity", "min", "Q1", "median", "Q3", "max", "mean",
           "zero shift", "n"], body_shift)
    for tok, (nl, ng, why, cls) in part2_lost.items():
        md("Issue time {}: {} reference proposals priced at t_d are not priced at the drawn "
           "time ({}; by class {}), and {} not priced at t_d are priced at the drawn "
           "time.".format(tok, nl, "; ".join("{} [{}] {}".format(a, b or "no code", n)
                                            for (a, b), n in why.most_common()) or "none",
                          ", ".join("{} {}".format(k, v) for k, v in sorted(cls.items()))
                          or "none", ng), "")
    for tok, lines in part2_miss.items():
        md("Costly proposals applied by the gate with the second price at delta 0.20, issue "
           "time {}: {}".format(tok, len(lines)), "")
        if lines:
            md(*lines)
            md("")
    md("### What the paper may say (Part 2)", "")
    md(*part2_facts)
    md("- Primary reading (published): 1,356 priced, 186 costly at delta 0.20, costly applied "
       "18 by the certificate and 0 with the second price, low-cost referred with the second "
       "price 22 of 1,170 (1.9% [0.8%, 3.0%]).",
       "- Boundary: for most instructions the issuable interval is short (the first start of "
       "a named order follows soon after it becomes known), so this sensitivity moves the issue "
       "time little; the 28 proposals that leave the priced set are V6 injection payloads that "
       "name orders completed or running at the drawn time.", "")
    cols = ["issue_time", "item_id", "instance_id", "primary_class", "edit_type", "t_d",
            "t_issue", "shift_bh", "known_share_t_d", "known_share_t_issue", "p_cert_K",
            "p_cert_FI", "p_rel2_K", "g_orig", "s2_site", "realised_cost_lo", "realised_cost_hi",
            "cost_class_020", "cost_class_010"] + ["refers_" + g for g in GATES]
    with open(OUT_ISSUE_CSV, "w", newline="", encoding="utf-8") as fh:
        fh.write("# N17 issue-time rows ({}): one row per reference proposal priced at the "
                 "drawn issue time; generated by code/scripts/n17_heldout.py analyse\n".format(
                     VERSION))
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows_out)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--seed", type=int)
    b.add_argument("--check-published", action="store_true")
    r = sub.add_parser("replay")
    r.add_argument("--suite", required=True)
    r.add_argument("--reading", default="primary")
    r.add_argument("--cores", default="10,11")
    r.add_argument("--workers", type=int, default=2)
    r.add_argument("--instances", default=None)
    sub.add_parser("repro")
    sub.add_parser("analyse")
    args = ap.parse_args()
    fn = {"build": cmd_build, "replay": cmd_replay, "repro": cmd_repro}.get(args.cmd)
    if fn is None:
        fn = globals()["cmd_" + args.cmd]
    rc = fn(args)
    after = assert_frozen()
    if after != FROZEN_AT_START:
        raise SystemExit("a frozen script changed during the run")
    return rc


if __name__ == "__main__":
    sys.exit(main())
