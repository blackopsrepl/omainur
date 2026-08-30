# make-music

Python synth + Grok skill for original 16-bit / club tracks. Generated MP3s live in `~/Music/ost` (local library, not this repo).

## Layout

```
src/                 synth, 16-bit engine, per-track generators
bin/play-ost         shuffle / loop / refresh playlists
skills/make-music/   Grok skill (symlink into ~/.grok/skills/)
```

## Install the skill

```bash
ln -sfn "$(pwd)/skills/make-music" ~/.grok/skills/make-music
```

## Generate

```bash
python3 src/generate_crystal_siege.py
./bin/play-ost refresh
```

Output pools: `16bit/`, `club/`, `bright/`, `experiments/` under `~/Music/ost`. Override with `OST_DIR`.

## Play (video background)

```bash
./bin/play-ost 16bit          # favorites
./bin/play-ost                # 16bit + club
OST_VOLUME=35 ./bin/play-ost 16bit
```

`~/play-ost` is a symlink to `bin/play-ost`.
