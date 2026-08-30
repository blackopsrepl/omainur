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
2. Default lane is **16-bit SNES/Genesis** (the cues Tim keeps: Gator, Red Alert, Thorn Chapel, Neon Riot, Last Bell, Night Raid). Variety = a *different 90s/early-2000s VGM progression*, key, and tempo — not a new genre.

Palette: 4/4; pulse lead + dotted-8th delay; triangle/sub bass; power fifths (no third); rock/military drums (kick on 1+3, snare 2+4, 8th hats, tom fill every 8 bars). Optional brass stabs and a triangle counter-line on the reprise.

Taste: dark, in-tune, slightly gritty. Cute major-key overworld is a miss (Emerald Trail). Chord tones + chosen scale only. No `i → bII`. G# / C# / D# only on the chord that contains them. Unison detune ≤7 cents.

Progressions to rotate (do not reuse one that is already the hook of a pool track):
- `i–VI–VII–i` (Am F G Am) — 90s battle loop
- `i–VI–III–VII` (Am F C G) — used (Neon Drop)
- `i–bVII–bVI–V` Andalusian — used (Neon Riot / Chrome Cellar)
- `i–iv–bVI–V` — used (Thorn Chapel)
- `i–bVI–V` / `i–i–bVI–V` — used (Red Alert)
- `i–iv–bVII–bIII` (Dm Gm C F) — falling fifths / dungeon
- `i–bVI–bIII–bVII` (Em C G D) — SNES final-dungeon epic
- `IV–V–iii–vi` (F G Em Am) — 90s royal road / J-RPG
- `i–III–VII–iv` (Am C G Dm)

Keep jungle, 6/8 shrine, yo-scale, western gallop, breakbeat, and acid-house in `experiments/` unless Tim asks for that lane.

Default length: **2:00**. In 4/4, `bars = 120 * BPM / 240`. Bounce with `game_synth.write_wav(mp3_path, L, R)` or `wav_to_mp3` — never leave a `.wav` in `~` or the OST dirs.

## Layout

Repo is `~/make-music` (this skill lives at `skills/make-music/` inside it). MP3 library is `~/Music/ost` (not in git).

| Path | Role |
|---|---|
| `~/make-music/src/` | `game_synth.py`, `vgm16.py`, `paths.py`, `generate_*.py` |
| `~/make-music/bin/play-ost` | Shuffle player + playlist refresh (`~/play-ost` is a symlink) |
| `~/Music/ost/16bit/` | Canonical 16-bit / game cues |
| `~/Music/ost/club/` | EDM / house |
| `~/Music/ost/bright/` | Cheery / other-people tracks |
| `~/Music/ost/experiments/` | Misses / off-lane (not in the video shuffle) |

`pool` is 16bit+club (no bright, no experiments). Video default is `~/play-ost` or `~/play-ost 16bit`.

## Compose

New file `~/make-music/src/generate_<slug>.py`. Import `game_synth` / `vgm16` / `paths` from the same folder. Bounce with `track_path("16bit", "name_2min.mp3")` (or `club` / `bright` / `experiments`). Keep pitch locked (`midi_hz`, phase accumulators). Pre-render drums; synthesize tonal layers per sample.

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

Stay in the 16-bit palette. Change **at least two** of: VGM progression (from the list above), tonic, tempo band (112 / 128 / 140 / 150 / 160).

## Out of scope

Do not call paid music APIs. Do not keep WAV masters. Do not add Emerald Trail or `experiments/` to the video pool.
