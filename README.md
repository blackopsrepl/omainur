# omainur — 8-bit cues, python end to end

*Generate a track similar to Castlevania. That's the whole product.*

The model is Tim's make-music skill: a shared python synth (`game_synth.py`),
one full-arrangement `generate_<slug>.py` per cue composed by the agent, MP3
bounced into the OST library. Theory discipline lives in the skill's rules,
not in an engine layer. Determinism where it matters: pitch is derived from
data (midi numbers → hz, phase accumulators), never from dice.

## Layout

| Path | What |
|---|---|
| `make-16bit-music/src/game_synth.py` | oscillators, drums, envelopes, bounce |
| `make-16bit-music/src/generate_*.py` | one file per cue — the compositions |
| `make-16bit-music/skills/make-music/` | the composition rules (Tim's skill) |
| `OST_DIR` | optional environment variable to choose where MP3s land |

The omarchy-sequencer app (clone `omarchy-sequencer/`, fork `sequencer-fork/`)
stays on disk untracked; it plays nothing here.

## Generate

```bash
cd make-16bit-music && python3 src/generate_castlevania.py   # the existing cue
```

A new cue is a new file: read the skill before writing a note
(`make-16bit-music/skills/make-music/SKILL.md`). Steal methods, not mixes.