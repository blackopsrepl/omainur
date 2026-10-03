# omainur

*The Ainur sing reality into existence; this layer sings sequencer songs into
files.* A deterministic, theory-locked song generator for
[omarchy-sequencer](https://github.com/jankeesvw/omarchy-sequencer), porting
the ontology of [make-16bit-music](https://github.com/timsonner/make-16bit-music):
same seed + genre → same song file, and every pitched note is provably a chord
tone or a scale tone. No ML — rules and tables.

**Start with the [user manual](../MANUAL.md)** — build, install, generate, play, edit.

Layout:

```
generator/     omainur_gen.py   the ontology as code (theory core + genre table + compiler + validator)
instruments/   make_anchors.py  the make-16bit-music synth voices as anchor WAVs
sequencer-fork/                 omarchy-sequencer 1.2.1 + per-note pitch + song-form chain
spikes/                         the feasibility studies that proved the design
```

## Generate a song

```bash
cd generator
python3 omainur_gen.py 16bit 1 my_song.json   # genres: 16bit house jungle shrine68
```

Emits the sequencer's own file format (drop it in `~/Music/Sequencer/` or open
it via the render harness). The validator inside refuses to write a song with a
single out-of-key note: every pitched note is a chord tone or scale tone of the
bar's chord, the melody moves stepwise with real holds and rests, and the
B-section harmony carries the harmonic-minor V the make-music skill demands.

## Instruments

```bash
cd instruments
python3 make_anchors.py ~/.local/share/omarchy-sequencer/samples/
```

Renders the 16-bit voices (pulse lead, triangle+sub bass, Rhodes-ish keys,
sine pluck, synthesized drums) at exact MIDI anchors; file names equal the
app's built-in sample names, so the engine loads them with zero code. The
contract: a sample named X is rendered at the anchor the generator's table
folds X to (lead 60, bass 36, stab/pad 48, arp 72).

## The sequencer changes (sequencer-fork/)

Exactly two additive fields, both backward compatible:

1. `Lane.notes: Vec<i8>` — per-step semitone offset, clamped ±24, applied by
   the engine through its existing per-voice resampler.
2. `Song.queued_chain: Option<Vec<ChainLink>>` — the song form; the engine
   follows it at pattern wrap unless the UI queues a jump.

Everything else is data.

## Verify

```bash
cd sequencer-fork && cargo test --lib
cargo build --example render
./target/debug/examples/render ../instruments/samples my_song.json /tmp/out.wav 8
```
