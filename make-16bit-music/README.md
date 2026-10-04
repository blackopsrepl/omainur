# make-music

Python synth + Grok skill for original 16-bit / club cues. MP3s live in `~/Music/ost` (local library, not this repo).

Each song is its own `src/generate_<slug>.py` — a full arrangement, not a melody dropped into a shared engine. Steal methods from existing generators; do not clone their mix.

Composition rules: `skills/make-music/SKILL.md` (symlinked into `~/.grok/skills/`).

## Layout

```
src/game_synth.py     oscillators, drums, bounce-to-mp3
src/paths.py          OST_DIR / track_path()
src/generate_*.py     one file per cue
bin/play-ost          shuffle / loop / refresh playlists
skills/make-music/    Grok skill
```

## Install the skill

```bash
ln -sfn "$(pwd)/skills/make-music" ~/.grok/skills/make-music
```

`~/play-ost` is a symlink to `bin/play-ost`.

## Generate

```bash
python3 src/generate_<slug>.py
./bin/play-ost refresh
```

Bounces a 2:00 MP3 into `~/Music/ost/<pool>/`. Override the library root with `OST_DIR`. Never leave a `.wav` in `~` or the OST dirs.

| Pool | Role |
|---|---|
| `16bit/` | Canonical 16-bit / game cues (video shuffle) |
| `club/` | EDM / house (video shuffle) |
| `bright/` | Cheery / other-people tracks (not in the default video pool) |
| `experiments/` | Off-lane (not shuffled by `play-ost`) |

`pool` is 16bit + club. `play-ost refresh` rebuilds `~/Music/ost/pool/` symlinks and `~/Music/ost/playlists/*.m3u`.

## Play (video background)

```bash
~/play-ost 16bit              # 16-bit cues
~/play-ost                    # 16bit + club
~/play-ost club
OST_VOLUME=35 ~/play-ost 16bit
```

## Cues

List the folders — the disk is the catalog.

| Generator | MP3 | Pool |
|---|---|---|
| `generate_16bit.py` | `codename_gator_2min.mp3` | 16bit |
| `generate_boss.py` | `red_alert_2min.mp3` | 16bit |
| `generate_castlevania.py` | `thorn_chapel_2min.mp3` | 16bit |
| `generate_clock_tower.py` | `last_bell_2min.mp3` | 16bit |
| `generate_night_city.py` | `neon_riot_2min.mp3` | 16bit |
| `generate_infiltration.py` | `night_raid_2min.mp3` | 16bit |
| `generate_crystal_siege.py` | `crystal_siege_2min.mp3` | 16bit |
| `generate_last_continent.py` | `last_continent_2min.mp3` | 16bit |
| `generate_marble_crypt.py` | `marble_crypt_2min.mp3` | 16bit |
| `generate_sky_citadel.py` | `sky_citadel_2min.mp3` | 16bit |
| `generate_eidolon_gate.py` | `eidolon_gate_2min.mp3` | 16bit |
| `generate_nitro_yard.py` | `nitro_yard_2min.mp3` | 16bit |
| `generate_wyrm_keel.py` | `wyrm_keel_2min.mp3` | 16bit |
| `generate_syndicate_row.py` | `syndicate_row_2min.mp3` | 16bit |
| `generate_western.py` | `dust_canyon_2min.mp3` | 16bit |
| `generate_overworld.py` | `emerald_trail_2min.mp3` | 16bit |
| `generate_edm.py` | `neon_drop_2min.mp3` | club |
| `generate_dark_house.py` | `chrome_cellar_2min.mp3` | club |
| `generate_jungle.py` | `black_satellite_2min.mp3` | experiments |
| `generate_kitsune.py` | `kitsune_gate_2min.mp3` | experiments |
| `generate_escalade.py` | `escalade_2min.mp3` | 16bit |

## Escalade

`src/generate_escalade.py` renders a 2:00, 132 BPM castle cue to
`~/Music/ost/16bit/escalade_2min.mp3` (or under `OST_DIR`). It deals a fixed
seven-layer arrangement—kick, snare, hats, bass, comp, lead, counter—from
bounded pattern and harmony choices.

```bash
python3 src/generate_escalade.py          # entropy-backed take; prints its seeds
python3 src/generate_escalade.py 73       # deterministic take from one seed
python3 src/generate_escalade.py --repro 1,2,3,4,5,6,7
```

For exact replay, pass all seven logged seeds to `--repro` in this order:
`arrangement,kick,snare,hats,bass,comp,lead`. The lead's one-bar onset mask is
repeated within each two-bar phrase; active phrases get bounded local rhythm
changes while keeping their first and last hits anchored. Strong drum/bass
claims favor nearby chord tones; weak slots move by one scale step. The output
file is replaced on each render.

Run the generator tests from the repository root with
`cd src && python3 -m unittest discover -v`.
