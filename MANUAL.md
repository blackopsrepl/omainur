# omainur — user manual

How to operate the whole thing: build the app, install the instrument pack,
generate songs, play and edit them. Nothing here is optional context — every
step is what you actually run.

The system has three pieces:

| Piece | Where | What it is |
|---|---|---|
| the app | `sequencer-fork/` | omarchy-sequencer 1.2.1 plus per-note pitch and a song-form chain |
| the generator | `omainur/generator/` | turns `genre + seed` into a song file; refuses out-of-key notes |
| the pack | `omainur/instruments/` | the 16-bit instrument sounds the songs play |

The generator writes the app's own file format. A generated song is a normal
sequencer song: every note is editable, every sound is swappable, undo works.

---

## 1. Build the app

Needs Rust (stable) and, to actually run it, a graphical session with audio
(it is a Hyprland/Omarchy desktop app). On a headless box you can build and
render, not run the window.

```bash
cd sequencer-fork
cargo build --release
```

The binary is `sequencer-fork/target/release/omarchy-sequencer`. Run it from a
terminal or install it wherever you keep binaries:

```bash
cp target/release/omarchy-sequencer ~/.local/bin/
```

For everything the app itself can do (themes, sharing, recording, packs), read
the app's own README: `sequencer-fork/README.md` in this repo. This manual
covers operating it with omainur.

## 2. Install the instrument pack

The songs reference sounds named `omainur_*`. Those are not built in — install
them once, into the app's user-sample folder:

```bash
cd omainur/instruments
python3 make_anchors.py ~/.local/share/omarchy-sequencer/samples/
```

That writes ten WAVs (`omainur_kick.wav`, `omainur_bass_hit.wav`,
`omainur_rhodes_tone.wav`, …). Restart the app; the sounds appear in the sound
browser (click a track's sound name) under your user samples.

**Do not skip this.** A song that references a missing sample falls back to
the first sample in the list (the kick) — the song will play, but wrong.

Why the sounds are "anchors": each WAV is rendered at one exact note (the
bass at C1, the lead at C3, keys at C2, plucks at C4). A note's pitch number
in the grid is semitones away from that anchor. You never need to think about
it when playing generated songs; it matters only when you tune sounds yourself.

## 3. Generate a song

```bash
cd omainur/generator
python3 omainur_gen.py <genre> <seed> <file>.json
```

| Genre | Feel | BPM | Key |
|---|---|---|---|
| `16bit` | dark SNES/Genesis action (the make-16bit-music default lane) | 150 | D minor |
| `house` | 4-on-the-floor club | 124 | A minor |
| `jungle` | chopped breakbeat | 168 | E harmonic minor |
| `shrine68` | 6/8-feel ritual over a 4/4 grid | 96 | F harmonic minor |

The seed is any integer. The same genre + seed always produces the exact same
file; a different seed gives a new melody over the same progression and form.
Each run self-validates: it prints `validation: … PASS` and refuses to write a
song containing a single note outside the chord tones or scale.

The output is one JSON file containing the full arrangement — 8 patterns (A to
H: intro, themes, tension, break, reprise) chained into a form, with harmony
that modulates between the two progressions.

Reference renders from the study (16-bit voices, real engine) are in
`/tmp/omainur_*.wav` if you still have them from the session that built this;
regenerate any time with the render command in section 7.

## 4. Open a generated song in the app

The app keeps songs in `~/Music/Sequencer/`. Copy yours there:

```bash
cp my_song.json ~/Music/Sequencer/
```

Then: launch the app → **Songs** (or `Ctrl+O`) → pick it → `Space` plays. On
play the app follows the form by itself: A → B → … → H → B → …, switching on
bar boundaries. Pressing a pattern letter (or `F1`–`F8`) takes over manually
until you stop and restart.

---

## 5. Edit a generated song

All the normal sequencer gestures apply (full key list below). The one new
surface is **per-note pitch** — what makes a melody editable.

### Pitch mode (`P`)

Press `P`. The app confirms in the status line. While it is on:

| Gesture | Effect |
|---|---|
| scroll over a note | transpose that one note by 1 semitone per notch |
| shift + scroll over a note | transpose that note by octaves |
| `↑` / `↓` | transpose every note in the current pattern by 1 semitone |
| `ctrl + ↑` / `ctrl + ↓` | transpose the pattern by octaves |

Every note shows its offset from the track's base pitch as `+n` / `−n` in its
corner while pitch mode is on. Offsets are clamped to ±24 semitones. Press `P`
again to leave; scroll and `↑`/`↓` go back to resize/tempo.

This composes with everything else: undo (`Ctrl+Z`) reverts transpositions,
`Shift`+pattern-letter copies a pattern (with its pitches) to another slot, and
`C` clears the pattern including pitch offsets.

### The song form (the arrows)

Between the pattern letters A–H, a small `→` marks where the form plays on.
It is read-only: the chain lives in the file, the engine follows it, and
clicking letters still selects/copies patterns as usual. To change the form,
edit the `queued_chain` array in the JSON (`next` = the index of the following
pattern, 0 = A; `null` ends the form there) — the app preserves the field
across edits and saves.

### Everyday gestures (unchanged from the sequencer)

| Key | What it does |
|---|---|
| `Space` | play or stop |
| `←` / `→` | fewer or more steps |
| `↑` / `↓`, `T` | tempo down or up, tap tempo (outside pitch mode) |
| `F1`–`F8` | pattern A–H; `Shift` copies the current pattern there |
| `1`–`9` | mute track 1–9 |
| `Tab` | select next track |
| `V` | record into the selected track |
| `R` / `C` / `N` | random pattern, clear pattern, add track |
| `Ctrl+Z` / `Ctrl+Shift+Z` | undo, redo |
| `Ctrl+N` / `Ctrl+O` | new song, songs window |
| `Ctrl+E` | export the current pattern to WAV |
| draw / right-click | draw notes / accent |
| scroll over a note | lengthen or shorten it (outside pitch mode) |

## 6. Play it out loud

`Space`. Meters run per track; the pattern letter of what is actually playing
blinks while a queued switch is pending. `Ctrl+E` bounces the current pattern
four times to a WAV in `~/Music`. For full arrangements use the headless
render below — it plays the whole chain.

## 7. Render a song to WAV without the app

The render harness plays a song's full form through the real engine — the same
code the app plays with — and writes a WAV:

```bash
cd sequencer-fork
cargo build --example render
./target/debug/examples/render <wav-dir> <song.json> <out.wav> <patterns>
```

- `<wav-dir>` — a directory of WAVs; use the pack (`../omainur/instruments/samples`)
  or your own `~/.local/share/omarchy-sequencer/samples/`.
- `<patterns>` — how many patterns (bars) to play; 8 for a full form.

It prints every pattern switch with its bar position and writes 16-bit stereo
at 48 kHz, plus two seconds of effect tail:

```bash
./target/debug/examples/render ../omainur/instruments/samples \
  ../omainur/generator/16bit_r1.json /tmp/my_render.wav 8
```

## 8. How the pieces fit together

- **Song file** = JSON in the app's own format (`~/Music/Sequencer/*.json`).
  Fields added by omainur: `notes` (per-step pitch offsets, inside each lane)
  and `queued_chain` (the form, inside the song). Both are ignored by the
  upstream app — a song stays loadable there, it just plays everything at one
  pitch and loops one pattern.
- **The generator** never touches the app; it writes files.
- **The pack** is ten WAVs; the app loads them because they sit in its
  user-sample folder. Their names (`omainur_*`) are the contract with the
  generator — if you rename them, generated songs fall back to the kick.
- **The engine** applies `track pitch + note offset` per voice and follows the
  chain at pattern end. Everything else (FX, swing, per-track mix) is stock
  sequencer behavior the generator presets per genre.

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A track plays a kick even though the grid shows notes | its sample id did not resolve — the pack is not installed, or a sound was renamed | run section 2, restart the app; ids must be exactly `omainur_*` |
| Song plays everything at one pitch | you opened it in the stock sequencer (no `notes` support) | run the fork's binary |
| Song loops one pattern instead of playing the form | same reason (no `queued_chain` support), or the file's chain was hand-edited to `null` | run the fork's binary; check `queued_chain` in the JSON |
| `↑`/`↓` change tempo instead of pitch | pitch mode is off | press `P` |
| Notes at the top of a melody refuse to go higher | ±24 semitone clamp on note offsets | raise the track's base `Pitch` control instead, then fine-tune per note |
| `python3 omainur_gen.py` fails validation | it refuses to write out-of-key songs — this is a guard, not a crash | report it; the validator's message names the track, pattern, bar and step |
| Render WAV is silent | wav-dir path wrong, or the song's names do not match any WAV stems | check the harness's `SAMPLE name=…` lines — every track's id must appear |

## 10. Housekeeping

- Songs you edit in the app autosave to `~/Music/Sequencer/` — the generated
  file is the starting point, not a live template. Keep generators' outputs
  under version control if you want to regenerate.
- The pack WAVs are ~500 KB total; they are yours to keep or re-render
  (`make_anchors.py` regenerates them deterministically).
- To share a generated song with another omainur user: send the JSON plus a
  pointer to this repo. The app's own Share button works too, but the community
  site runs the stock engine — pitch and form will not play there yet.

