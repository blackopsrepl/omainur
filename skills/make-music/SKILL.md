---
name: make-music
description: >
  Compose original tracks with the local Python synth, bounce MP3 into the OST
  folders, and refresh shuffle playlists. Use when the user wants a new song,
  EDM, 16-bit, chiptune, house, OST, playlist, shuffle, /make-music, "another
  track", or video background music.
---

# Make music

Original tracks for Tim's video-background OST. Synthesize in Python, bounce MP3 only, drop into a pool, shuffle with mpv.

## Before writing a note

1. `ls ~/Music/ost/16bit ~/Music/ost/club ~/Music/ost/bright ~/Music/ost/experiments` — do not clone a pool track.
2. Open two existing generators and steal *methods*, not the mix. Keepers: `generate_16bit.py` (Gator), `generate_boss.py` (Red Alert), `generate_castlevania.py` (Thorn Chapel), `generate_clock_tower.py` (Last Bell), `generate_night_city.py` (Neon Riot), `generate_infiltration.py` (Night Raid). Later full cues in `src/` are fair too.
3. Default lane is **16-bit SNES/Genesis**. Stay in that era. Variety is a new cue with its own intro, groove, lead, and form — not a new progression dropped into the same engine.

Taste: in-tune, slightly gritty. Default lane is dark. Raw major-key overworld is in the pool (Emerald Trail) — that color is allowed; do not clone the cue. Unison detune ≤7 cents.

**Harmony:** Any Western progression that belongs in 80s–early-2000s VGM is fair game — diatonic major/minor, modal (dorian, mixolydian, …), harmonic-minor V / vii°, circle-of-fifths, royal road, Andalusian, rock bVII, and other loops those scores actually used. Pick a tonic and a scale for the cue; melody and bass are chord tones or tones of that scale. Accidentals (G# / C# / D# and enharmonics) only on a chord that contains them. No `i → bII` as the hook. Do not copy another pool track’s loop as this cue’s hook — read existing `generate_*.py` files to see what is already taken. The pool is not a menu of allowed progressions.

Keep jungle, 6/8 shrine, yo-scale, western gallop, breakbeat, and acid-house in `experiments/` unless Tim asks for that lane.

Default length: **2:00**. In 4/4, `bars = 120 * BPM / 240`. Bounce with `game_synth.write_wav(mp3_path, L, R)` or `wav_to_mp3` — never leave a `.wav` in `~` or the OST dirs.

## Layout

Repo is `~/make-music` (this skill lives at `skills/make-music/` inside it). MP3 library is `~/Music/ost` (not in git).

| Path | Role |
|---|---|
| `~/make-music/src/` | `game_synth.py`, `paths.py`, per-track `generate_*.py` |
| `~/make-music/bin/play-ost` | Shuffle player + playlist refresh (`~/play-ost` is a symlink) |
| `~/Music/ost/16bit/` | Canonical 16-bit / game cues |
| `~/Music/ost/club/` | EDM / house |
| `~/Music/ost/bright/` | Cheery / other-people tracks |
| `~/Music/ost/experiments/` | Misses / off-lane (not in the video shuffle) |

`pool` is 16bit+club (no bright, no experiments). Video default is `~/play-ost` or `~/play-ost 16bit`.

## Compose

New file `~/make-music/src/generate_<slug>.py` is a **full arrangement**, on the order of the keepers (not a 40-line melody list). Import `game_synth` and `paths` only. Bounce with `track_path("16bit", "name_2min.mp3")` (or `club` / `bright` / `experiments`). Keep pitch locked (`midi_hz`, phase accumulators). Pre-render drums; synthesize tonal layers per sample.

Each cue must invent all of:

- **Intro** — a signature that is not "4 bars of kick on 1+3". Bells, snare roll, codec blip, organ nave, alarm, wind, toms-only ritual, brass fanfare, clave+bass, horn cry, etc.
- **Drum feel** — invent one (funk, 4-on-the-floor, half-time, heartbeat, wing-beat toms, clave, …). Do not default to kick 1+3 / snare 2+4 / 8th hats / tom fill every 8 bars.
- **Lead** — one identity per song (pulse, flute, organ, mallet, brass horn, FM electric piano, …). Not the same pulse+dotted-8th stack as Gator unless that *is* the cue.
- **Bass figure** — write a new 8th/quarter/half pattern. Do not reuse `[0, 0, 12, 0, 0, 7, 12, 0]`.
- **Space** — dry, a short hall / multi-tap (irregular milliseconds, not on the beat), or a rhythmic delay that is clearly mix glue (16th / 8th / quarter / half). A long off-grid delay reads as a second melody drifting out of sync — don't.
- **Form** — named sections with different instrumentation, not intro/vamp/a/b/break/a2/b2/end.
- **Melody** — motives with holds and rests (`0` = rest). Not an 8th-note chord arpeggio for 32 slots.

Power fifths, brass, and triangle counters are optional colors, not the template.

```bash
python3 ~/make-music/src/generate_<slug>.py
```

After a successful bounce:

```bash
~/play-ost refresh
```

That rebuilds `~/Music/ost/pool/` symlinks and `~/Music/ost/playlists/*.m3u`.

Play: `~/play-ost 16bit`  (or `club`, `pool`, `bright`). `OST_VOLUME=35` to duck it.

## Variety checklist (use it)

Stay 16-bit. A new progression + tonic + tempo is **not enough** if the intro and mix match an existing cue. Change the intro and at least three of: drum groove, lead waveform, bass rhythm, space (dry / delay / reverb), unique FX (bells, alarm, codec, organ, flute, harp, choir, wind, clave).

## Out of scope

Do not call paid music APIs. Do not keep WAV masters. Do not add `experiments/` to the video pool.
