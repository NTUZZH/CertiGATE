"""Test bootstrap: put the L1 code directory (and this directory) on sys.path.

Tests are always run from the repository root (``python -m pytest code/tests``),
so that nothing is ever written inside the read-only scheduling repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
CODE_DIR = TESTS_DIR.parent

for p in (str(CODE_DIR), str(TESTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


# The larger logs ship as release assets (see results/README.md). Each test module
# below reads one of them, and it is skipped, with the asset named, until that
# asset is unpacked at the repository root.
_ASSET_NEEDS = {
    'test_n10.py': [
        ('results/e1_eval_deepseek/proposals.jsonl', 'e1_eval_deepseek.tar.gz'),
        ('results/e1_eval_glm9b/proposals.jsonl', 'e1_eval_glm9b.tar.gz'),
        ('results/e1_eval_gpt54mini/proposals.jsonl', 'e1_eval_gpt54mini.tar.gz'),
        ('results/e1_eval_opus5/proposals.jsonl', 'e1_eval_opus5.tar.gz'),
        ('results/e1_eval_qwen14b/proposals.jsonl', 'e1_eval_qwen14b.tar.gz'),
        ('results/e1_eval_qwen27b/proposals.jsonl', 'e1_eval_qwen27b.tar.gz'),
        ('results/e1_eval_sol/proposals.jsonl', 'e1_eval_sol.tar.gz'),
        ('results/e1_eval_sonnet5/proposals.jsonl', 'e1_eval_sonnet5.tar.gz'),
    ],
    'test_n11_forecast.py': [
        ('results/n11_decision_time/items.jsonl', 'n11_decision_time.tar.gz'),
        ('results/n11_decision_time/late/items.jsonl', 'n11_decision_time.tar.gz'),
    ],
    'test_n14.py': [
        ('results/n11_decision_time/items.jsonl', 'n11_decision_time.tar.gz'),
        ('results/n11_decision_time/boards.jsonl', 'n11_decision_time.tar.gz'),
    ],
}


def pytest_collection_modifyitems(config, items):
    import pytest

    root = CODE_DIR.parent
    for item in items:
        needs = _ASSET_NEEDS.get(Path(str(item.fspath)).name, ())
        missing = sorted({asset for rel, asset in needs if not (root / rel).exists()})
        if missing:
            item.add_marker(pytest.mark.skip(reason="needs the release asset(s) " + ", ".join(missing)))
