# 001: per-note pitch (the gating question)

## Question

The sequencer's `Lane` stores only On/Off/Accent — no pitch. Can a lane carry a
melody through ONE sample per track, in tune, through the real engine?

## Approach

1. `Lane` gains `notes: Vec<i8>` (semitone offset per step, `#[serde(default)]`),
   sanitized to ±24 like the existing FX `fine` field. Zeroed = old behaviour;
   old files load unchanged; unknown-field tolerance both directions.
2. `Engine::step()` passes `track.pitch + lane.notes[step]` (clamped ±24) into the
   existing `trigger()` resampler — the per-voice pitch plumbing already existed;
   it just had no per-note input.
3. Instruments are anchor WAVs rendered by the make-16bit-music synth code at the
   exact anchor note each role folds to (lead C3=60, bass C1=36, stab/pad C2=48,
   arp C4=72). `notes[]` then indexes scale degrees relative to that anchor.

## Evidence

```
note + 0: f0 =   65.40 Hz      (+0 semitones)
note + 4: f0 =   82.40 Hz   +0.02 cents vs expected  PASS
note + 7: f0 =   97.90 Hz   -1.58 cents vs expected  PASS
note +12: f0 =  130.80 Hz   -0.00 cents vs expected  PASS
PITCH CHAIN VERDICT: PASS
```

Rendered by the real `Engine` (headless `render` example, cpal not involved),
measured by Goertzel scan on the rendered WAV. An earlier FAIL on +12 was the
probe's analysis window outrunning a 0.25 s sample at 2x resample rate — fixed
in the probe (0.6 s anchor), not in the engine.

The app-side UI (writing/painting `notes[]`) is NOT built in this spike; the
JSON path (generator → file → engine) is complete and verified.

## Verdict: VALIDATED

Melody works through one sample per track. The generator already writes melodies
this way; every note validated in chord tones or scale by spike 002.

### Recommendation for the real build
- Ship the `notes` field exactly as spiked (serde-default, ±24 clamp).
- UI work is additive: a per-note pitch mode (scroll = transpose note) touching
  only `ui.rs` paint + input paths that already read `lens[]`.
- Watch: ±24 clamp fights wide-range leads; real build may want ±36.
