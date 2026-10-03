# 006 answer-cadence: the sites answer and the form returns home

## Verdict: VALIDATED

### Result (castle, seed 1986)
- validator PASS — every answer, ornament and cadence tone is in-key.
- **G3 answer**: B starts a minor third above A (interval 3, from the designed
  family {3,4,8,9}) and its last onset lands on the root → PASS.
- **G4 return**: H's tag resolves to the root → PASS.
- **G5 identity**: 7/8 lane hashes distinct (per-site parameters, ornament
  chance) → PASS.
- **G1 recurrence**: 6/8 sections ≥0.75 against their expected slice:
  A 1.00, C 0.96, E 1.00, F 0.94, G 0.99, H 1.00. B/D 0.53 by contour but
  certified by G3 — the octave-up tail reads as answer, the matcher alone
  cannot certify register-shifted identity (carried to 008: hear it).

### What changed from 005
- One total placement contract (`reland_full`): absolute midi, folds applied
  once in order, no later heuristic undoing an earlier rule.
- The silence rule found a real defect: offset 0 is rest, and a root-anchored
  genre folds the root ONTO silence. The root identity now lives at +12.
- Per-site answer grammar: start-tone chosen from the designed interval
  family relative to A's start (a semitone "answer" is a design failure);
  cadence to the root an octave low (a real 8ve descent, visible in-lane).

### Carried to 008
- Register-shifted recurrence (B/D oct tails) is invisible to interval deltas:
  the audio correlate must fold chroma by pitch CLASS, which is octave-blind
  by construction — the one place the artifact can prove what the lane math
  cannot.