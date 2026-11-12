#!/usr/bin/env python
"""Write ``code/scripts/instance_manifest_l1.json``: the content this paper's
logs were computed on.

WHY THIS FILE EXISTS

The Y1 instance tree the E1 logs name,
``${L1_Y1_ROOT}/data/processed/instances``, was regenerated
on 2026-08-19, after this study's evaluation. 46 of the 60 instances the paper
replays now carry different content, and a no-op dispatch of a regenerated file
reproduces neither the suite's stored episode baseline nor the published ladder
anchor. An untouched snapshot of the original content sits beside it, in
``instances_v10``, and that snapshot reproduces all 116 published ladder
anchors exactly.

A tree that has drifted is not a loud failure. It loads, it dispatches, and it
returns a plausible number from data the run never saw. The manifest turns that
into a loud failure: it records the sha256 of each of the 60 files as the
snapshot holds them, and ``code/scripts/suite_gate.py`` refuses to load an
instance whose content does not match.

THE FOUR LAUNCH QUESTIONS (the project's experiment rules)

1. PURPOSE. Produce the integrity manifest the suite gate checks every instance
   against. It answers "is the file I am about to dispatch the file the
   published numbers were computed on?", and it lands in the repository as
   ``code/scripts/instance_manifest_l1.json`` and in the public release beside
   the code that reads it. No number in the manuscript comes from this run.
2. EXPECTED RESULT. Exactly 60 relative paths, one per instance the E1
   proposal logs name, each with the sha256 of the snapshot copy. If the count
   is not 60, or a path the logs name is missing from the snapshot, or the
   snapshot copy is byte-identical to the drifted tree on all 60 files (which
   would mean the drift is elsewhere and this guard is aimed at the wrong
   thing), the script exits non-zero and writes nothing.
3. CONTAMINATION. Nothing is trained, no device is held, no checkpoint is
   touched. Every input is read-only: the eight ``proposals.jsonl`` logs and
   the snapshot's instance files. The one real risk is hashing the WRONG tree,
   so the snapshot root is asserted to be the anchor-verified one by name and
   the drifted root is hashed too, only to record how far the two differ.
4. DATA ACCURACY. The path list is collected from the logs themselves rather
   than from a directory walk, so it is exactly the set the paper replays. The
   anchor-verification basis is not re-derived here: it is cited from the
   provenance header of ``analysis/DG17_e2e_delta.csv``, whose generator
   resolves the instance root by dispatching every published anchor and
   refusing to run unless all 116 reproduce. That header's sha256 is recorded
   in the manifest, so a later reader can tell whether the basis moved.

Usage::

    python code/scripts/instance_manifest_l1.py            # write the manifest
    python code/scripts/instance_manifest_l1.py --check    # exit 1 if stale

Version: l1-instance-manifest-1.
"""

from __future__ import annotations
import os  # the path literals below read L1_Y1_ROOT

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

VERSION = "l1-instance-manifest-1"

ROOT = Path(__file__).resolve().parent.parent.parent      # <project>
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"
OUT = Path(__file__).resolve().parent / "instance_manifest_l1.json"

#: The root every logged ``instance_path`` is written against.  It is the
#: tree that drifted, and it is never trusted.
LOGGED_ROOT = Path("${L1_Y1_ROOT}/data/processed/instances")

#: The untouched snapshot that reproduces every published ladder anchor.  The
#: manifest's digests are taken from here and from nowhere else.
SNAPSHOT_ROOT = Path(((os.environ.get("L1_Y1_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "PaperY-FMScheduling")) + "/data/processed/instances_v10"))

#: The record of the anchor verification.  Its generator resolves the instance
#: root by dispatching all 116 published anchors and refuses to run unless one
#: candidate reproduces every one of them; the verdict for each candidate is
#: written into the provenance header of this file.
ANCHOR_RECORD = ANALYSIS / "DG17_e2e_delta.csv"
ANCHOR_GENERATOR = "code/scripts/e1_delta_guard_replay.py::resolve_instance_root"
N_PUBLISHED_ANCHORS = 116

#: The eight evaluation directories whose proposal logs name the instances.
EVAL_DIRS = ("e1_eval_qwen14b", "e1_eval_qwen27b", "e1_eval_glm9b",
             "e1_eval_gpt54mini", "e1_eval_deepseek", "e1_eval_sonnet5",
             "e1_eval_opus5", "e1_eval_sol")

N_EXPECTED = 60


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def logged_relpaths() -> list:
    """The instance files the E1 proposal logs name, relative to the root.

    Read from the logs rather than from a directory walk: the manifest must
    cover exactly the instances this paper replays, and the instance tree
    holds many more.
    """
    rels, seen_dirs = set(), []
    for name in EVAL_DIRS:
        log = RESULTS / name / "proposals.jsonl"
        if not log.is_file():
            raise SystemExit("missing proposal log: {}".format(log))
        seen_dirs.append(name)
        with log.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                path = json.loads(line).get("instance_path")
                if not path:
                    raise SystemExit(
                        "a proposal in {} carries no instance_path".format(log))
                p = Path(path)
                try:
                    rels.add(str(p.relative_to(LOGGED_ROOT)))
                except ValueError:
                    raise SystemExit(
                        "proposal log {} names an instance outside the logged "
                        "root {}: {}".format(log, LOGGED_ROOT, path))
    if len(seen_dirs) != len(EVAL_DIRS):
        raise SystemExit("not every evaluation directory was read")
    return sorted(rels)


def anchor_basis() -> dict:
    """What is known about the two candidate roots, and where it is recorded."""
    if not ANCHOR_RECORD.is_file():
        raise SystemExit("missing anchor record: {}".format(ANCHOR_RECORD))
    verdicts = {}
    for line in ANCHOR_RECORD.open():
        if not line.startswith("#"):
            break
        if "instance root candidate" in line:
            body = line.split("instance root candidate", 1)[1].strip()
            parts = body.split(None, 1)
            verdicts[parts[0]] = parts[1].strip() if len(parts) > 1 else ""
    for root in (str(LOGGED_ROOT), str(SNAPSHOT_ROOT)):
        if root not in verdicts:
            raise SystemExit(
                "the anchor record does not report on candidate root {}; it "
                "cannot be the basis for this manifest".format(root))
    if "reproduces all {} anchors".format(N_PUBLISHED_ANCHORS) \
            not in verdicts[str(SNAPSHOT_ROOT)]:
        raise SystemExit(
            "the anchor record does not say the snapshot reproduces all {} "
            "anchors: {!r}".format(N_PUBLISHED_ANCHORS,
                                   verdicts[str(SNAPSHOT_ROOT)]))
    if "differ" not in verdicts[str(LOGGED_ROOT)]:
        raise SystemExit(
            "the anchor record no longer reports the logged root as drifted: "
            "{!r}. Re-derive the basis before writing a manifest."
            .format(verdicts[str(LOGGED_ROOT)]))
    return {
        "published_anchors": N_PUBLISHED_ANCHORS,
        "verified_by": ANCHOR_GENERATOR,
        "recorded_in": str(ANCHOR_RECORD.relative_to(ROOT)),
        "recorded_in_sha256": sha256_of(ANCHOR_RECORD),
        "candidate_verdicts": verdicts,
    }


def build() -> dict:
    rels = logged_relpaths()
    if len(rels) != N_EXPECTED:
        raise SystemExit(
            "expected {} distinct instances in the E1 logs, found {}"
            .format(N_EXPECTED, len(rels)))

    digests, drifted = {}, []
    for rel in rels:
        snap = SNAPSHOT_ROOT / rel
        if not snap.is_file():
            raise SystemExit(
                "the snapshot does not carry an instance the logs name: {}"
                .format(snap))
        digests[rel] = sha256_of(snap)
        live = LOGGED_ROOT / rel
        if live.is_file() and sha256_of(live) != digests[rel]:
            drifted.append(rel)
    if not drifted:
        raise SystemExit(
            "the logged root matches the snapshot on all {} files, so either "
            "the drift has been repaired or this manifest is aimed at the "
            "wrong tree; refusing to write a guard nobody needs"
            .format(len(rels)))

    body_sha = hashlib.sha256(
        json.dumps(digests, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")).hexdigest()
    return {
        "schema": VERSION,
        "generated": _dt.datetime.now().astimezone()
                        .strftime("%Y-%m-%d %H:%M:%S %z"),
        "generator": "code/scripts/instance_manifest_l1.py ({})".format(VERSION),
        "purpose": (
            "The content of the Y1 scheduling instances this paper's logs "
            "were computed on. code/scripts/suite_gate.py verifies every "
            "instance it loads against this manifest and refuses to dispatch "
            "a file whose content has changed."),
        "snapshot": {
            "name": SNAPSHOT_ROOT.name,
            "root": str(SNAPSHOT_ROOT),
            "note": (
                "An untouched copy of the instance content as it stood when "
                "the E1 evaluation ran on 2026-08-16."),
        },
        "drifted_root": {
            "root": str(LOGGED_ROOT),
            "note": (
                "The root every logged instance_path names. It was "
                "regenerated on 2026-08-19, after the evaluation, and must "
                "not be dispatched."),
            "files_differing_from_snapshot": len(drifted),
            "files_total": len(rels),
        },
        "anchor_verification": anchor_basis(),
        "override": {
            "env": ["L1_Y1_ROOT", "L1_INSTANCE_ROOT"],
            "note": (
                "L1_Y1_ROOT relocates the whole Y1 checkout and keeps the "
                "data/processed/instances layout; L1_INSTANCE_ROOT points "
                "straight at an instance tree, which is how a checkout "
                "reaches the snapshot without moving files. Neither override "
                "disables the content check: a file present in this manifest "
                "is verified wherever it is read from."),
        },
        "n_files": len(rels),
        "files_sha256": body_sha,
        "files": digests,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the manifest would change; write nothing")
    args = ap.parse_args(argv)

    manifest = build()
    text = json.dumps(manifest, indent=2, sort_keys=False) + "\n"

    if OUT.is_file():
        try:
            old = json.loads(OUT.read_text())
        except ValueError:
            old = None
        if old is not None and old.get("files") == manifest["files"] \
                and old.get("anchor_verification", {}).get("recorded_in_sha256") \
                == manifest["anchor_verification"]["recorded_in_sha256"]:
            # Idempotent: an unchanged manifest keeps its recorded time.
            manifest["generated"] = old.get("generated", manifest["generated"])
            text = json.dumps(manifest, indent=2, sort_keys=False) + "\n"

    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print("instance_manifest_l1.json is {}".format(
            "up to date" if same else "STALE"))
        return 0 if same else 1

    OUT.write_text(text)
    print("wrote {} ({} instances, files_sha256 {})".format(
        OUT, manifest["n_files"], manifest["files_sha256"][:16]))
    print("  snapshot        {}".format(manifest["snapshot"]["root"]))
    print("  drifted root    {} ({} of {} files differ)".format(
        manifest["drifted_root"]["root"],
        manifest["drifted_root"]["files_differing_from_snapshot"],
        manifest["drifted_root"]["files_total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
