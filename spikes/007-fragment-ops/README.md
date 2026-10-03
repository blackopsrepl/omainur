# 007 fragment ops: partial statements stay key-locked and traceable

## Verdict: VALIDATED (absorbed into 006's slice matcher)

The fragment vocabulary shipped inside 006: `fragment` (E, hook slots 0–7),
`truncate` (G, onsets on beat heads), `tag` (H, tail slots 12–15) — each
compiled through `reland_full`, each **measured against its expected slice**
rather than the full hook profile (`slice_expectation` + `match_slice`).

### Evidence (castle, seed 1986)
- validator PASS: fragments are key-locked (all onsets re-snapped to the
  section's own chords by the reland).
- Traceability measured: E 1.00, G 0.99, H 1.00 against their expected slices
  — the partial statements demonstrably ARE the hook's material, not new
  streams. Zero out-of-key or untraceable fragments in 8 sections.

### The idea 007 contributed to the design
Partial ops must be gated against the slice they claim to restate. The full
hook profile under-gates them (structurally 0.0); the slice matcher is what
makes E/G/H first-class form statements. That gate logic lives in
`spikes/006-answer-cadence/main.py`.