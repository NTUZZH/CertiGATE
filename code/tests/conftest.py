"""Test bootstrap: put the L1 code directory (and this directory) on sys.path.

Tests are always run from the L1 side (``pytest /home/ziheng/PaperL1/code/tests``)
so that nothing is ever written inside the read-only Y1 repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
CODE_DIR = TESTS_DIR.parent

for p in (str(CODE_DIR), str(TESTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
