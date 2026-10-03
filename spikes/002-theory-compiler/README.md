# 002: the theory compiler (deterministic, theory-locked)

## Question

Can the make-16bit-music ontology (its SKILL.md rules + generator code) be
compiled into a pure, seeded rules engine that emits omarchy-sequencer songs
where every pitched note is provably in chord tones or scale?

## Approach

`omainur_gen.py` — stdlib only, no ML, no sampling:

- Theory core: 5 scales (natural/harmonic minor, dorian, mixolydian, major),
  diatonic 7th chords per degree with per-chord scale substitution (the
  harmonic-minor V the skill prescribes), melody generator enforcing chord
  tones / scale tones, stepwise motion preference, holds, rests.
- Genre table: `16bit` (default lane), `house` (club lane), `jungle` +
  `shrine68` (the skill's experiments lanes) — each with BPM, swing, groove,
  progression A/B, section plan, bass figure, ranges/anchors, and engine-FX mix.
- Compiler: fills 8 patterns x 10 tracks from section roles (basic / theme /
  full / tension / break), emits the app's exact file schema (snake_case,
  sample indexes + names array) plus the song-form chain (spike 003).
- Self-validator: re-derives the harmony per bar and checks EVERY pitched note.

## Evidence

```
genre=16bit   sha256=...  validation: all notes in chord tones or scale — PASS
genre=house   sha256=...  validation: all notes in chord tones or scale — PASS
genre=jungle  sha256=...  validation: all notes in chord tones or scale — PASS
genre=shrine68 sha256=... validation: all notes in chord tones or scale — PASS
DETERMINISM: PASS        (same seed -> byte-identical file, cmp)
SEED VARIATION: differs  (different seed -> different melody, same harmony)
```

Determinism modulo the generator: the engine's own noise sources (its LCG) are
not seedable from the song file today — noted for the real build.

Hand-checked: Dm7-Bbmaj7-C7-Dm7 diatonic in D natural minor; pattern E-H use
Gm-Bb-C-A7 with C# coming from harmonic minor on the V. Hold audit: 87 holds,
0 overlapping notes.

## Verdict: VALIDATED

Deterministic, theory-locked, self-validating. This is the "ontology as data"
form: the skill's prose rules became a table + pure functions.

### Recommendation for the real build
- The genre table is the product: new lane = new table entry.
- Promote the validator to CI: a genre that emits one out-of-key note fails.
- Later: extend table with intro-signature recipes (the skill demands
  non-generic intros; currently the "basic" section plays that role).
