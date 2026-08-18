#!/usr/bin/env python
"""Build the L1 violation suite (deliverable D2).

    python scripts/build_suite.py                # full suite -> code/suite/v0.1/
    python scripts/build_suite.py --smoke        # 5% config, for a quick check
    python scripts/build_suite.py --out /tmp/x   # elsewhere
    python scripts/build_suite.py --twice        # build twice, compare hashes

Every artifact is a pure function of the config: the same config rebuilds a
byte-identical ``suite.jsonl``.  Nothing is written inside the Y1 repository.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from l1suite import SuiteConfig, build_suite, smoke_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="5%% of every quota")
    ap.add_argument("--scale", type=float, default=None, help="scale every quota")
    ap.add_argument("--seed", type=int, default=None, help="global seed")
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--twice", action="store_true", help="rebuild and compare hashes")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    config = smoke_config() if args.smoke else SuiteConfig()
    if args.scale is not None:
        config.quota_scale = args.scale
    if args.seed is not None:
        config.global_seed = args.seed

    t0 = time.time()
    summary = build_suite(config, out_dir=args.out, verbose=not args.quiet)
    elapsed = time.time() - t0
    print("items      : {}".format(summary["items"]))
    print("out        : {}".format(summary["out_dir"]))
    print("sha256     : {}".format(summary["suite_sha256"]))
    print("by set     : {}".format(summary["counts"]["by_set"]))
    print("by class   : {}".format(summary["counts"]["by_class"]))
    print("build time : {:.1f} s".format(elapsed))

    if args.twice:
        out2 = Path(summary["out_dir"]).parent / (Path(summary["out_dir"]).name + "_rebuild")
        again = build_suite(config, out_dir=out2, verbose=False)
        same = again["suite_sha256"] == summary["suite_sha256"]
        print("rebuild    : {} ({})".format(again["suite_sha256"], "identical" if same else "DIFFERENT"))
        if not same:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
