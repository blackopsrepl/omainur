# 005 hook-carrier: a tune that recurs is a design object, not a stream

## Question

Can the compiler carry a **hook** — one designed 2-bar motif — through the
A–H chain so that recurrence is real in the lane data, while sections stay
distinct? The current `fill_harmony` draws every section independently, which
is the root cause of salad; this spike replaces it.

## Given / When / Then

- **Given** a 2-bar hook as designed data (contour, rhythm, anchored to chord
  tones) and a set of deterministic section operations,
- **when** the eight patterns are compiled and the song validates,
- **then**: (1) the hook's relative contour appears in ≥4 of 8 sections,
  quantified by contour matching on lane notes; (2) ≥6 section lane-hashes
  differ from each other — recurrence must never become repetition.

## Method

- Lane level only (no render needed to kill the question): hook → per-section
  op → lanes → `og.validate()` → gates.
- Hook: built from the genre's own scale/progression, deterministic from seed.
- Ops (minimal set, spelled exactly):
  - `state`: hook as composed (A)
  - `reland`: hook re-fit to each bar's chord (B, D)
  - `harmonize_full`: reland + stab/arp support (C, F)
  - `fragment`: first half of the hook over a V pedal (E)
  - `truncate`: head of the hook, long notes (G)
  - `tag`: last 1 bar re-lands the hook tail over the chain seam (H)

## Verdict: VALIDATED (lane-level)

### What worked
- Hook as designed data + one deterministic op per section compiles through the
  real data shape; `og.validate()` PASS on the merged song.
- G1 recurrence: **5/8** sections restate the hook at their own grain
  (A 1.00, C 1.00, F 0.90 across the b-progression, B/D 0.69 as octave-up answers).
- G2 distinctness: **6/8** lane hashes differ — recurrence is not repetition.

### What didn't
- E/G/H score 0.0 against the **full** hook profile: fragment, truncate and tag
  are partial statements (≤7 onsets vs 13), and the correlator needs a
  full-length window. Partial ops are structurally ungated by this matcher.

### Carried to 007
- Per-op expected profiles: the gate must match *the fragment of the hook the
  op is supposed to produce*, not the whole hook. Until then partial ops
  contribute to G1 only by construction, not by measurement.

### Carried to 006
- B and D (same op, same progression) produce identical lanes. The answer-op
  needs per-site variation: B starts the answer away from A's start; D varies
  the resolution. Measured, not asserted.