# omainur — feasibility study → implementation

*The Ainur sing reality into existence; this layer sings sequencer songs into
files.* A port of [make-16bit-music](https://github.com/timsonner/make-16bit-music)'s
ontology — music theory rules, genre lanes, full arrangements — into
[omarchy-sequencer](https://github.com/jankeesvw/omarchy-sequencer) as a
**deterministic, theory-locked generator layer**.

**Status: implemented.** The feasibility spikes (commit `49b4b02`) validated
the design on the real engine; the implementation is this repository's current
tree. No ML anywhere: the same seed + genre always produces the same song, and
every pitched note is provably a chord tone or scale tone.

The two development series are preserved for provenance on the `dev-history`
tag: the `main` spike snapshot (`49b4b02`) and the implementation commit
series.

| # | Spike | Validates | Verdict |
|---|-------|-----------|---------|
| 001 | [per-note pitch](spikes/001-pitch-notation/README.md) | a `Lane` can carry a melody through one sample, in tune | **VALIDATED** (+4/+7/+12 = 0.02/1.58/0.00 cents) |
| 002 | [theory compiler](spikes/002-theory-compiler/README.md) | ontology as pure rules: deterministic, in-key, genre-distinct | **VALIDATED** (4 genres, byte-identical per seed, validator PASS) |
| 003 | [arrangement chain](spikes/003-arrangement-chain/README.md) | a song plays its full A–H form, not one loop | **VALIDATED** (switches on bar boundaries, 8-bar render) |
| 004 | [instrument pack](spikes/004-instrument-pack/README.md) | the make-16bit-music voices land as a data-only pack | **VALIDATED** (ear test pending) |

## Layout

| Path | What |
|---|---|
| `omainur/generator/` | the ontology as code: `omainur_gen.py` (theory core, genre table, compiler, self-validator) + reference songs |
| `omainur/instruments/` | `make_anchors.py` — the synth voices as anchor WAVs (run it to fill `samples/`) |
| `sequencer-fork/` | the fork *is* the app: omarchy-sequencer 1.2.1 + per-note pitch + song-form chain, with `install.sh`, packaging and upstream docs. The pristine upstream clones used while studying it (`omarchy-sequencer/`, `make-16bit-music/`) are not tracked |
| `spikes/` | the four feasibility studies; `main` and the implementation series stay reachable on the `dev-history` tag |

## The two kernel changes

1. `Lane.notes: Vec<i8>` — per-step semitone offset (serde-default **filled to
   64 zeros**, clamped ±24), applied by the engine through its existing
   per-voice resampler. Old files load unchanged; verified in tune to <2 cents.
2. `Song.queued_chain: Option<Vec<ChainLink>>` — the song form; the engine
   follows it at pattern wrap unless the UI queues a jump. Old files loop as
   before; sanitize clamps untrusted chains.

Both compile against the untouched UI (`cargo check` with default features).

## Try it

```bash
cd omainur/instruments && python3 make_anchors.py samples
cd ../generator && python3 omainur_gen.py 16bit 1 my_song.json  # house jungle shrine68
../sequencer-fork/target/debug/examples/render \
  ../instruments/samples my_song.json /tmp/out.wav 8            # after cargo build --example render
# or open my_song.json in the app (drop instruments/samples/*.wav into
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

Design alternatives kept for future approaches: see the vault note
`projects/omainur.md` in `/srv/org`.
