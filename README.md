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
| 005 | [hook-carrier](spikes/005-hook-carrier/README.md) | a designed hook recurs through the form without collapsing diversity | **VALIDATED** (5/8 recurrence at op grain, 6/8 distinct) |
| 006 | [answer-cadence](spikes/006-answer-cadence/README.md) | the answer is designed, measured, key-locked; the form returns home | **VALIDATED** (interval measured from the CALL's onset, not the root — seed 1987) |
| 007 | [fragment-ops](spikes/007-fragment-ops/README.md) | partial statements stay key-locked and traceable to the hook | **VALIDATED** (E/G/H = 1.00/0.99/1.00 against expected slices) |
| 008 | [ear-on-artifact](spikes/008-ear-on-artifact/README.md) | the render carries the recurrence audibly | **VALIDATED** (5/5 claims audible, octave-blind chroma on the soloed carrier) |
| 009 | [iterate-loop](spikes/009-iterate-loop/README.md) | form-grammar mutations converge monotonically under the gates | **VALIDATED** (24-seed stress: 5/24 drafts born red, 5/5 repaired in one step) |

## Layout

| Path | What |
|---|---|
| `omainur/generator/` | the ontology as code: `omainur_gen.py` (theory core, genre table, compiler, self-validator) + `hook_form.py` (the hook carrier: sections are operations on a designed motif) + reference songs |
| `omainur/instruments/` | `make_anchors.py` — the synth voices as anchor WAVs (run it to fill `samples/`) |
| `sequencer-fork/` | the fork *is* the app: omarchy-sequencer 1.2.1 + per-note pitch + song-form chain, with `install.sh`, packaging and upstream docs. The pristine upstream clones used while studying it (`omarchy-sequencer/`, `make-16bit-music/`) are not tracked |
| `spikes/` | the nine feasibility studies; earlier series stay reachable on the `dev-history` tag |

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

## The not-salad contract (spikes 005–009)

The lead is no longer a per-section stream. One hook is **designed** per genre
(contour + rhythm over the genre's own harmony); every section is an explicit
**operation** on it — state, answer, ornament, fragment, truncate, tag — and
the compiler must pass gates before a song ships:

1. recurrence: the hook restated in ≥ 4/8 sections, measured at each op's own grain
2. distinctness: ≥ 6/8 lead lanes differ (recurrence is not repetition)
3. answer: B starts a third/sixth-family interval from the **call's actual
   first onset** and cadences to the root
4. return: H's tag resolves home
5. every pitched note a chord or scale tone (the existing validator)

The iterate loop mutates the form grammar (answer interval, ornament rate,
section ops, tag length) and keeps only gate-measured improvements, so a
draft that is merely "salad" cannot survive: 5/24 seeds are born red and the
loop repairs them red→green in one step.

## What is still open

1. **Pack packaging** — anchor WAVs as a proper pack + CATALOG entry, so
   generated songs share correctly instead of depending on the user-sample
   folder.
2. **Genre table growth** — intro-signature recipes (the make-music skill's most
   opinionated rule), more lanes, second lead/bass voices.
3. **Determinism hardening** — engine noise (accents are data; hat humanization
   if ever added should become seeded data too).
4. **Validator in CI** — a genre that emits one out-of-key note fails the build.

## Design alternatives not taken

- **Zero-kernel generator** — emit songs inside the stock schema only: drums
  and one pitch per track, harmony carried by chord roots. Runs on the
  unmodified app and shares as-is; gives up melodies.
- **External render pipeline** — keep make-16bit-music as the renderer and use
  the sequencer only as an editing surface. Gives up in-app editability of
  generated songs.
- **Upstream-first** — PR the two additive fields to the app and keep the
  generator and pack local. Best endgame if the app picks them up; the fork
  exists until then.
