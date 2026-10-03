# 005–009 hook form: verdicts

## Series result: VALIDATED (5/5 spikes landed; 4 with real findings)

| Spike | Question | Verdict | The finding |
|---|---|---|---|
| 005 hook-carrier | does a designed hook recur without collapsing diversity? | VALIDATED | 5/8 recurrence, 6/8 distinct; partial ops invisible to a full-profile gate (gate flaw, not carrier flaw) |
| 006 answer-cadence | can the answer be designed, measured, and key-locked? | VALIDATED | answer interval must be measured from the CALL's first onset, not the genre root (seed 1987 proved it — a root-relative answer is a unison); lane offset 0 = silence erases the root identity in root-anchored genres (root now lives at +12) |
| 007 fragment-ops | do partial statements stay key-locked and traceable? | VALIDATED | absorbed into 006's slice matcher: E/G/H measure 1.00/0.99/1.00 against their expected slices |
| 008 ear-on-artifact | does the RENDER carry the recurrence audibly? | VALIDATED | 5/5 lane-claimed statements audible on the soloed carrier (octave-blind chroma); mix-level vs carrier-level are named lenses — F's 0.50-at-mix is reharmonization doing its job |
| 009 iterate-loop | do measured-gate mutations converge monotonically? | VALIDATED | monotone-or-plateau across three seeds; **24-seed stress: 5/24 drafts born red, 5/5 repaired red→green in one M2 step**; M1 stands down rather than shipping an out-of-key answer |

## What shipped into the generator
`omainur/generator/hook_form.py` + `generate()` integration: the hook carrier
now owns the lead lane for every genre (fallback to the legacy per-section
draw if the module is absent). castle/16bit/house/jungle/shrine68 all
validate PASS; castle lane hashes 8/8 distinct; the promoted artifact renders
the full A–H chain through the real engine.

## The not-salad contract, as built
1. One designed hook per genre (contour + rhythm + in-key snap).
2. Sections are OPERATIONS on the hook (state/answer/ornament/fragment/
   truncate/tag) — the form grammar is data, per genre.
3. The call comes first; answers measure from the call's actual start.
4. Gates before ship: recurrence ≥ 4/8 at op grain, distinctness ≥ 6/8,
   answer + return cadences to the root, validator PASS.
5. Mutation keeps only gate-measured improvements; the loop stops when
   nothing helps.