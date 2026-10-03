# 009 iterate loop: mutate form parameters, keep only measured improvements

## Verdict: VALIDATED

### Evidence (castle, seeds 1986 / 1987 / 1988)
- **Seed 1986**: draft green (4/4 gates, recurrence 6, distinct 7) → loop
  declines all six mutations → converged. MONOTONE.
- **Seed 1987**: draft red on g3_answer — the loop was HANDED a red gate and
  the vocabulary could NOT repair it, and the probe showed why: the root
  cause was mine, not the grammar's. The answer interval was measured from
  the genre root while the call itself started on the chord's third →
  interval 0 (a unison "answer", a design failure 1986 masked by luck).
  Fix moved into the compiler (006): the call is built FIRST and answers
  measure from its actual first onset. After the contract fix, 1987's draft
  is green (4/4, distinct 8).
- **Seed 1988**: draft green, converged, MONOTONE.

### The honest line on the repair step — updated after the 24-seed stress
The stress run (seeds 1980–2003, `stress.py`) settled it: **5/24 drafts are
born RED** on g5_identity (1983, 1985, 1994, 1996, 2003 — all distinctness 6/8),
and the loop repairs **5/5 red→green** in a single M2 step (ornament 50→100,
per-site approach tones diverge the hashes). The repair path is not theoretical:
natural red drafts occur ~1 in 5, and the vocabulary fixes every one observed,
monotonically, in one step.

### What the loop rejects (measured)
- Any mutation whose song fails the validator is skipped, not shipped.
- M1 to an interval the answering chord cannot supply stands down (designed
  answer preserved rather than traded for an out-of-key start).

### What the loop proved about the form grammar
- Recurrence 6/8 and distinctness 7–8/8 across all three seeds: the grammar
  does not need luck. The draft IS the converged form.