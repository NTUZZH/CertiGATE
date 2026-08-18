"""Explicit loader for the git-ignored project ``.env`` (decisions.md, v3.6 entry).

The three provider keys live in ``/home/ziheng/PaperL1/.env`` (chmod 600) and are
loaded by each experiment runner at start-up, into ``os.environ`` of that process
only.  They are never exported from a shell profile: an exported
``ANTHROPIC_API_KEY`` would hijack this machine's Claude Code authentication.

A key already present in the environment wins over the file, so a one-off
override (``DEEPSEEK_API_KEY=... python ...``) still works.
"""

from __future__ import annotations

import os

ENV_PATH = "/home/ziheng/PaperL1/.env"


def load_env(path: str = ENV_PATH) -> list:
    """Load KEY=value lines from ``path`` into ``os.environ``; return loaded names."""
    loaded = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return loaded
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
