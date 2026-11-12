"""Exact-model brackets that honour an instruction's dispatch constraints.

``l1oracle.cpsat_prec`` is a CP-SAT model of an adjusted instance with the
instruction's precedence edges, pins, frozen slots and batch chains imposed.
Its lower end is a valid lower bound on the continuous constrained optimum
(rounded-down grid), and its upper end is a feasible continuous schedule.
"""

from . import cpsat_prec  # noqa: F401

__all__ = ["cpsat_prec"]
