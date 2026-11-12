"""N12 (environment sensitivity): derived instances, the scaled clock, the crew convention.

Run pinned::

    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 taskset -c 8-9 python -m pytest code/tests/test_n12.py -q
"""

from __future__ import annotations

import copy
import json
import multiprocessing as mp
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "code" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("L1_INSTANCE_ROOT",
                      ((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))

import n12_env_sensitivity as N  # noqa: E402
import n11_decision_time as D  # noqa: E402


def _paths():
    import suite_gate as sg
    pub = {r["item_id"]: r for r in sg.load_suite()}
    return N.instance_paths(pub)


PATHS = _paths()
ONE = {st: next(p for iid, p in PATHS.items() if iid.startswith(st)) for st in D.STRATA}


def test_identity_reproduces_every_manifest_hash():
    man = N.manifest_files()
    assert len(PATHS) == 60
    for iid, p in PATHS.items():
        src = N._ORIG_LOAD(p)
        der = N.derive(src, N.ENVS["cal"])
        assert N.file_sha(der) == man[N.source_rel(p)], iid
        assert der == src


@pytest.mark.parametrize("fw", [0.5, 1.5])
def test_window_transform(fw):
    env = dict(N.ENVS["cal"], window=fw)
    sla = {1: 8.0, 2: 24.0, 3: 80.0, 4: 171.4}
    for p in ONE.values():
        src = N._ORIG_LOAD(p)
        keep = copy.deepcopy(src)
        der = N.derive(src, env)
        assert src == keep                                   # the input is never mutated
        so = {w["id"]: w for w in src["work_orders"]}
        for w in der["work_orders"]:
            assert w["due_bh"] == round(w["release_bh"] + fw * sla[w["priority"]], 4)
            s = so[w["id"]]
            assert {k: v for k, v in w.items() if k != "due_bh"} == \
                {k: v for k, v in s.items() if k != "due_bh"}
        assert der["technicians"] == src["technicians"]
        assert der["meta"] == src["meta"] and der["trades"] == src["trades"]


def test_crew_convention_matches_y1_rounding():
    # Python's round is half to even, as Y1's generator uses it (generator.py:_technicians)
    assert N.crew_target(2, 0.75) == 2          # 1.5 -> 2
    assert N.crew_target(1, 0.75) == 1          # 0.75 -> 1
    assert N.crew_target(3, 0.75) == 2          # 2.25 -> 2
    assert N.crew_target(2, 1.25) == 2          # 2.5 -> 2
    assert N.crew_target(6, 1.25) == 8          # 7.5 -> 8
    assert N.crew_target(49, 0.75) == 37        # 36.75 -> 37
    assert N.crew_target(1, 0.1) == 1           # never below one technician


@pytest.mark.parametrize("fc", [0.75, 1.25])
def test_crew_transform(fc):
    env = dict(N.ENVS["cal"], crew=fc)
    for p in ONE.values():
        src = N._ORIG_LOAD(p)
        der = N.derive(src, env)
        n_src = Counter(t["trade"] for t in src["technicians"])
        n_der = Counter(t["trade"] for t in der["technicians"])
        assert set(n_der) == set(n_src)
        for tr, n in n_src.items():
            assert n_der[tr] == max(1, int(round(n * fc)))
        assert [t["id"] for t in der["technicians"]] == \
            ["T{}".format(i) for i in range(len(der["technicians"]))]
        trades = [t["trade"] for t in der["technicians"]]
        assert trades == sorted(trades)
        assert der["work_orders"] == src["work_orders"]


def test_loader_needs_an_environment_and_never_writes_the_snapshot():
    p = ONE["c10_replay_400"]
    before = D.sha256_file(p), os.stat(p).st_mtime_ns
    N._STATE["env"] = None
    with pytest.raises(SystemExit):
        N.env_load_instance(p)
    N.activate("win050")
    inst = N.env_load_instance(p)
    assert inst["work_orders"][0]["due_bh"] == round(
        inst["work_orders"][0]["release_bh"] + 0.5 * N.base_sla()[inst["work_orders"][0]["priority"]], 4)
    assert (D.sha256_file(p), os.stat(p).st_mtime_ns) == before
    N.activate("cal")


def _probe_in_worker(path):
    inst = D.load_instance(path)
    return N.sla_probe(inst, N._STATE["env"]), inst["work_orders"][0]["due_bh"]


@pytest.mark.parametrize("name,fw", [("win050", 0.5), ("win150", 1.5), ("cal", 1.0)])
def test_scaled_clock_reaches_forked_workers(name, fw):
    from l1adapter import _fmwos
    from l1adapter import apply as apply_mod

    N.activate(name)
    assert apply_mod.SLA_BH == {p: fw * v for p, v in N.base_sla().items()}
    assert dict(_fmwos.timeaxis.SLA_BH) == apply_mod.SLA_BH
    p = ONE["c09_storm2_w80"]
    with mp.get_context("fork").Pool(1) as pool:
        probe, due = pool.apply(_probe_in_worker, (p,))
    assert probe["ok"], probe
    w0 = N._ORIG_LOAD(p)["work_orders"][0]
    assert due == round(w0["release_bh"] + fw * N.base_sla()[w0["priority"]], 4)
    N.activate("cal")


def test_identity_environment_leaves_the_published_constants():
    from l1adapter import _fmwos
    from l1adapter import apply as apply_mod

    N.activate("cal")
    assert apply_mod.SLA_BH == {1: 8.0, 2: 24.0, 3: 80.0, 4: 171.4}
    assert dict(_fmwos.timeaxis.SLA_BH) == {1: 8.0, 2: 24.0, 3: 80.0, 4: 171.4}
    assert N.base_sla() == {1: 8.0, 2: 24.0, 3: 80.0, 4: 171.4}
