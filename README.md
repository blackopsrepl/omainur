# omainur — 8-bit cues, Python end to end

*Generate a track similar to Castlevania. That's the whole product.*

The model is Tim's make-music skill: a shared Python synth (`game_synth.py`),
one full-arrangement `generate_<slug>.py` per cue composed by the agent, and
MP3 output to a configurable music library. Theory discipline lives in the
skill's rules, not in an engine layer. Pitch rendering maps MIDI note values
to frequencies and phase increments; composition choices remain in the cue.

## Layout

| Path | What |
|---|---|
| `make-16bit-music/src/game_synth.py` | oscillators, drums, envelopes, bounce |
| `make-16bit-music/src/generate_*.py` | one file per cue — the compositions |
| `make-16bit-music/skills/make-music/` | the composition rules (Tim's skill) |
| `OST_DIR` | optional environment variable to choose where MP3s land |

## Setup

The music-generation source is not vendored here. Clone Tim's upstream
repository into the ignored `make-16bit-music/` directory:

```bash
git clone https://github.com/timsonner/make-16bit-music.git make-16bit-music
```

## Generate

```bash
cd make-16bit-music && python3 src/generate_castlevania.py
```

A new cue is a new file: read the skill before writing a note
(`make-16bit-music/skills/make-music/SKILL.md`). Steal methods, not mixes.