# omainur — feasibility study

*The Ainur sing reality into existence; this layer sings sequencer songs into
files.* A spike: can [make-16bit-music](https://github.com/timsonner/make-16bit-music)'s
ontology — music theory rules, genre lanes, full arrangements — be ported into
[omarchy-sequencer](https://github.com/jankeesvw/omarchy-sequencer) as a
**deterministic, theory-locked generator layer**?

**Answer: yes.** Four spikes, all validated on the real engine (this checkout's
`sequencer-fork/` = omarchy-sequencer + two additive fields). No ML anywhere:
the same seed + genre always produces the same song, and every pitched note is
provably a chord tone or scale tone.

| # | Spike | Validates | Verdict |
|---|-------|-----------|---------|
| 001 | [per-note pitch](001-pitch-notation/README.md) | a `Lane` can carry a melody through one sample, in tune | **VALIDATED** (+4/+7/+12 = 0.02/1.58/0.00 cents) |
| 002 | [theory compiler](002-theory-compiler/README.md) | ontology as pure rules: deterministic, in-key, genre-distinct | **VALIDATED** (4 genres, byte-identical per seed, validator PASS) |
| 003 | [arrangement chain](003-arrangement-chain/README.md) | a song plays its full A–H form, not one loop | **VALIDATED** (switches on bar boundaries, 8-bar render) |
| 004 | [instrument pack](004-instrument-pack/README.md) | the make-16bit-music voices land as a data-only pack | **VALIDATED** (ear test pending — renders in /tmp) |

## What changed in the sequencer (the whole diff)

1. `Lane.notes: Vec<i8>` — per-step semitone offset, serde-default, ±24 clamp.
2. `Song.queued_chain: Option<Vec<ChainLink>>` — the song form; UI `queued`
   still overrides; missing field = today's behaviour.
3. Engine: pass `track.pitch + note` to the existing per-voice resampler;
   follow the chain at pattern wrap when the UI hasn't queued anything.

Everything else is **data**: the generator (`spikes/002-theory-compiler/omainur_gen.py`)
writes the app's own file format, and the sounds are WAVs.

## Try it

```bash
cd sequencer-fork && cargo build --example render
cd ../spikes/002-theory-compiler
python3 omainur_gen.py 16bit 1 my_song.json      # also: house jungle shrine68
../../sequencer-fork/target/debug/examples/render \
  ../001-pitch-notation/anchors my_song.json /tmp/out.wav 8
# or open my_song.json in the app (drop the anchors into
# ~/.local/share/omarchy-sequencer/samples/ first)
```

## What the real build still needs (none of it spikes-risky)

1. **UI for `notes[]`** — paint + a transpose gesture; `lens[]` already shows
   the pattern to copy (scroll-over-note = transpose).
2. **Chain UI (optional)** — a form row over the pattern letters; the engine
   already plays it, and the site player gets it for free.
3. **Pack packaging** — anchor WAVs as a proper pack + CATALOG entry.
4. **Genre table growth** — intro-signature recipes (the skill's most
   opinionated rule), more lanes, second lead/bass voices.
5. **Determinism hardening** — engine noise (accents are data; hat humanization
   if ever added should become seeded data too).
6. **Validator in CI** — a genre that emits one out-of-key note fails the build.
