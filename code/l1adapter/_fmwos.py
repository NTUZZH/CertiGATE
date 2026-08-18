"""Read-only bridge to the Paper Y1 environment package (``fmwos``).

The Y1 repository is reused, never modified.  Its package root is the repo's
``src/`` directory, so the only integration is a ``sys.path`` insertion.  Two
precautions keep the Y1 tree byte-untouched:

* nothing in ``l1adapter`` ever opens a Y1 file for writing;
* bytecode writing is disabled for the duration of the ``fmwos`` import, so no
  new ``__pycache__`` entry is created inside the Y1 tree.

Set the ``L1_Y1_ROOT`` environment variable to the checkout of that repository.
The default is a sibling directory named ``PaperY-FMScheduling`` next to this
repository.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_Y1_ROOT = Path(__file__).resolve().parents[2].parent / "PaperY-FMScheduling"
Y1_ROOT = Path(os.environ.get("L1_Y1_ROOT", str(DEFAULT_Y1_ROOT)))
Y1_SRC = Y1_ROOT / "src"


def _import_fmwos():
    if not Y1_SRC.is_dir():
        raise ImportError(
            "Y1 package root {} not found; set L1_Y1_ROOT to the "
            "PaperY-FMScheduling checkout".format(Y1_SRC)
        )
    if str(Y1_SRC) not in sys.path:
        sys.path.insert(0, str(Y1_SRC))
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # never write .pyc into the read-only Y1 tree
    try:
        import fmwos  # noqa: F401
        from fmwos import pdrs, timeaxis, validator
    finally:
        sys.dont_write_bytecode = prev
    return fmwos, pdrs, timeaxis, validator


fmwos, pdrs, timeaxis, validator = _import_fmwos()

# The environment's own constants, reused rather than restated (fmwos/timeaxis.py).
SLA_BH: dict[int, float] = dict(timeaxis.SLA_BH)      # {1: 8.0, 2: 24.0, 3: 80.0, 4: 171.4}
WEIGHT: dict[int, float] = dict(timeaxis.WEIGHT)      # {1: 8.0, 2: 4.0, 3: 2.0, 4: 1.0}

# The storage convention of the environment's own instance builder
# (fmwos/instances.py rounds release_bh and due_bh to 4 decimals).
ROUND_BH = 4

__all__ = [
    "Y1_ROOT",
    "Y1_SRC",
    "fmwos",
    "pdrs",
    "timeaxis",
    "validator",
    "SLA_BH",
    "WEIGHT",
    "ROUND_BH",
]
