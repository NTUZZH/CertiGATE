# N27b addendum (choices made after the variant design was frozen)

Entries are appended in order; each says whether it was written before or after any pricing of the variant.

1. (Before any pricing of the variant.) Implementation choices. The script is a copy of N27's
   with the candidate rule, the seed prefix, the outputs and the tables of the variant design
   changed; N27's script and outputs are untouched. Each thinned board is keyed by a digest of
   its sorted withheld ids (H2 can hold thousands of orders), and every draw records how many
   of its withheld orders are planned. Population tokens in macro names are Priced (all 1,356
   priced proposals) and Costly. Besides the descriptives 5b and 6b that the variant design
   names, the descriptive 5c of N27 is carried over: the share of the window's corrective
   orders not seen, now (n_unknown + withheld corrective orders) / corrective orders of the
   window. The item 1 table also counts costly proposals refused in some draw.
2. (Before any pricing of the variant.) Test runs as in N27: a smoke self-test on two small
   windows that prints only |K|, |H2| and the number of distinct boards, then a full self-test
   that keeps the replay in a copy outside the project for testing the analysis code. The
   reported outputs come from a separate fresh replay.
3. (After the results.) Nine macros added on request, on the costly proposals whose disposition
   changes at delta 0.20: for the certificate, the number of distinct instances they lie on,
   their realised cost (smallest lower end and largest upper end of the realised-cost
   interval), their certificate price at f = 0 and at f = 1 (smallest and largest), and how many
   only re-sequence work; for the certificate with the second price, how many are field edits.
   No new replay was run. The script gained a --from-stored mode that rebuilds every output
   from replay_n27b.jsonl, the stored replay of the official fresh run (558 s on cores 8 and 9),
   and asserts that it rewrites that file byte for byte. The trajectory digest check, which the
   official run passed when it wrote the file, is not repeated. Every earlier macro keeps its
   value (the old and new macro files differ only by the 18 added lines), and the row file, the
   figure data and the raw replay are byte-identical to those of the official run.
