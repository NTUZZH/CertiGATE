# Practitioner audit: recorded ratings

`cases.csv` is the de-identified record of a small human audit of the suite's
own dispositions. Five practitioners each read the same 30 cases and rated
every one of them; nothing else about the reviewers is recorded here, and no
reviewer-level file exists in this repository.

**What a row is.** One audited case. `case` is its identifier, `class` the
suite class it was drawn from (benign, V3, V4, V5, V6), `register` the surface
form of the instruction (formal, terse, conversational), `stratum` the instance
stratum it was drawn from, and `disposition` the disposition the suite assigns
it (Apply, Reject, Refer).

**What a cell is.** `apply`, `reject` and `refer` are the number of reviewers
who chose each disposition, so the three sum to five on every row. `realism`,
`fidelity`, `clarity` and `action` are counts of POSITIVE ratings out of the
five reviewers, not mean scores: each reviewer answered on a four-point scale
and a rating of 3 or 4 counts as positive.

**Scope.** Case-level only, de-identified, 30 cases and 150 judgements per
measure. The analysis that reads this file is
`code/scripts/practitioner_audit.py`, which writes
`analysis/DG13_practitioner_audit.csv` and asserts every headline it prints.
