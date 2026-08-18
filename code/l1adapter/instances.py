"""Locating and loading Y1 instance files (read-only).

Layout of the Y1 instance store::

    data/processed/instances/c{01,02,05,09,10,12}/<track>/<size>/<id>.json

with ``<track>`` in {replay, generator, pmmix, storm, storm2} and ``<size>`` the
size class directory.  The size directory is a work-order count for every track
except ``storm2``, whose single size directory is ``w80`` (an 80-bh window with a
campus-dependent order count: 2,269 on C9, 9,350 on C10 for instance 0000).

There is no public instance loader in ``fmwos`` (``fmwos.train._load_instance``
is a private, caching helper), so :func:`load_instance` is a plain
``json.load``: the file is parsed exactly as written, no coercion, no defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._fmwos import Y1_ROOT

INSTANCE_ROOT = Y1_ROOT / "data" / "processed" / "instances"
INDEX_CSV = INSTANCE_ROOT / "index.csv"


def campus_dir(campus) -> str:
    """Normalise a campus reference to its directory name (``9`` -> ``'c09'``)."""
    s = str(campus)
    if s.startswith("c") and s[1:].isdigit():
        return "c{:02d}".format(int(s[1:]))
    if s.isdigit():
        return "c{:02d}".format(int(s))
    raise ValueError("cannot read {!r} as a campus (expected 9, '9' or 'c09')".format(campus))


def list_instances(campus, track: str, size=None) -> list[Path]:
    """Return the sorted instance paths for one (campus, track[, size]) cell.

    Parameters
    ----------
    campus : int | str   ``9``, ``'9'`` or ``'c09'``
    track  : str         ``replay`` | ``storm2`` | ``storm`` | ``pmmix`` | ``generator``
    size   : int | str | None
        Size-class directory (``150``, ``'150'``, ``'w80'``).  ``None`` returns
        every size directory of that track, concatenated in sorted directory
        order.

    Returns an empty list when the cell does not exist (no exception: the caller
    decides whether an empty cell is an error).
    """
    base = INSTANCE_ROOT / campus_dir(campus) / str(track)
    if not base.is_dir():
        return []
    if size is not None:
        sizes = [base / str(size)]
    else:
        sizes = sorted(p for p in base.iterdir() if p.is_dir())
    out: list[Path] = []
    for d in sizes:
        if d.is_dir():
            out.extend(sorted(d.glob("*.json")))
    # A track directory may also hold instance files directly (none do today).
    out.extend(sorted(base.glob("*.json")))
    return out


def load_instance(path) -> dict:
    """Load one instance JSON exactly as stored (no coercion, no defaults)."""
    with open(path, "r") as f:
        return json.load(f)


def instance_id(path) -> str:
    """The instance id, taken from the file name (equals ``meta.id`` in Y1)."""
    return Path(path).stem


__all__ = [
    "INSTANCE_ROOT",
    "INDEX_CSV",
    "campus_dir",
    "list_instances",
    "load_instance",
    "instance_id",
]
