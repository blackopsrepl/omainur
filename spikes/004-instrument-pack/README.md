# 004: the 16-bit sound (instrument pack)

## Question

Can the make-16bit-music synth voices (pulse lead, tri+sub bass, Rhodes-ish
keys, sine pluck, its drum synthesis) become a sequencer sound pack so the
result sounds like the lane it claims — with zero engine code?

## Approach

- `make_anchors.py` renders the game_synth oscillator code (verbatim math:
  same LUT sine, LCG noise, band-limited square, 16-bit quantization q=768)
  into WAVs whose file names equal the app's built-in sample names
  (`rhodes_tone`, `bass_hit`, `rhodes_chord`, `neon_pad`, `plucks`, `kick`,
  `snare`, `hat_closed`, `hat_open`, `clap`), each at its exact anchor note.
- The engine's user-sample dir (`~/.local/share/omarchy-sequencer/samples/`)
  or a pack dir loads them with no code changes (spiked via the render
  harness's equivalent loader).
- The generator's track pitch + per-note offsets do all intonation work
  (spike 001); the genre table's FX (crush/drive/chop/delay/filter) does the
  per-lane mix work through the engine's existing per-track FX chain.

## Evidence

- Anchor tuning verified through the engine's own decoder + resampler:
  lead 60.02, arp 72.01, stab/pad 48.01 (estimated midi, exact within cents).
- Four genres rendered end-to-end through the real engine: 16bit (150 BPM),
  house (124), jungle (168), shrine68 (96) — distinct files (md5), correct
  durations (8 bars each), objectively distinct spectra:
  zcr B-section 0.0079 / 0.0027 / 0.0021 / 0.0010, and per-genre FX
  (16bit: crush 0.22 + dotted-8th delay; house: reverb + 6-step delay;
  jungle: crush 0.35; shrine68: long reverb 0.5).

## Verdict: VALIDATED (with a scope note)

The pipeline works and the engine-side is a pure data drop. The scope note:
"does it SOUND 16-bit" is an ear judgment — the synthesis code is the
make-16bit-music code verbatim and the crunch/FX chain is engaged, but a
human listen (Vittorio) is the real acceptance test for the default lane's
feel. Renders: `/tmp/omainur_{16bit,house,jungle,shrine68}.wav`.

### Recommendation for the real build
- Ship as a proper pack (pack dir + CATALOG entry), not user samples, so
  songs share correctly.
- The anchor-note convention (file name = app sample name, rendered at the
  role's anchor) is the contract between generator and pack; write it down
  in the pack README.
- Per-role anchor fold ranges currently assume these 10 sounds; a second
  lead/bass voice = one more table column.
