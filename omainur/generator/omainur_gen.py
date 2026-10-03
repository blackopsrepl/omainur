#!/usr/bin/env python3
"""omainur spike: make-16bit-music ontology compiled into omarchy-sequencer songs.

Deterministic: same seed + genre -> byte-identical song JSON. Rules, not ML.
"""
from __future__ import annotations

import json

# ---------------------------------------------------------------- theory core

PC = {"c": 0, "c#": 1, "db": 1, "d": 2, "d#": 3, "eb": 4, "e": 4, "f": 5,
      "f#": 6, "gb": 6, "g": 7, "g#": 8, "ab": 8, "a": 9, "bb": 10, "b": 11}

SCALES = {
    "natural_min": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_min": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
}

# Scale degrees (0-indexed) of each chord tone for a given chord quality.
CHORD_DEGREES = {
    "min7": (0, 2, 4, 6),
    "maj7": (0, 2, 4, 6),
    "dom7": (0, 2, 4, 6),
    "min": (0, 2, 4),
    "maj": (0, 2, 4),
}

# Third/seventh alteration per quality relative to the scale degrees they sit on.
# We compute chord tones from the scale itself; only dominant and harmonic-minor
# chords need explicit alteration, handled in chord_tones() via PROGRESSION data.


class LCG:
    """The same LCG make-16bit-music uses for noise; here it drives choice only."""

    def __init__(self, seed: int) -> None:
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s >> 8

    def pick(self, n: int) -> int:
        return self.next() % n

    def chance(self, pct: int) -> bool:
        return self.next() % 100 < pct


def scale_range(root_midi: int, scale: list[int], lo: int, hi: int) -> list[int]:
    """All midi notes in [lo, hi] that belong to the scale, ascending."""
    out = []
    for m in range(lo, hi + 1):
        deg = (m - root_midi) % 12
        if deg in scale:
            out.append(m)
    return out


def chord_tones(root_midi: int, scale: list[int], degree: int, seventh: bool) -> list[int]:
    """Pitch classes of the diatonic 7th (or triad) on `degree` of the scale."""
    steps = [scale[(degree + i) % 7] for i in (0, 2, 4, 6)][:4 if seventh else 3]
    return sorted({(root_midi + s) % 12 for s in steps})


def gen_melody(rng: LCG, root_midi: int, scale: list[int], chord: list[int],
               length: int, lo: int, hi: int) -> list[int]:
    """One 4-bar motive over one chord per bar: midi note, or 0 = rest.

    Rules from the make-music skill: chord tones or scale tones only, stepwise
    motion preferred, real holds and rests (never a static arpeggio), phrase
    ends on a long chord tone. Fully deterministic from `rng`.
    """
    pool = scale_range(root_midi, scale, lo, hi)
    if not pool:
        return [0] * length
    tones = [m for m in pool if m % 12 in chord]
    cur = rng.pick(len(tones))
    cur = tones[cur]
    out = []
    i = 0
    while i < length:
        r = rng.next() % 100
        if r < 14:
            out.append(0)          # rest
            i += 1
            continue
        if r < 26 and out and out[-1] != 0:
            out.append(out[-1])    # hold (repeat = longer note)
            i += 1
            continue
        step = 1 if rng.chance(50) else -1
        cand = [m for m in pool if abs(m - cur) <= 4 and m != cur]
        if not cand:
            i += 1
            continue
        idx = cand.index(min(cand, key=lambda m: abs(m - cur)))
        j = min(max(idx + (1 if step > 0 else -1), 0), len(cand) - 1)
        cur = cand[j]
        out.append(cur)
        i += 1
    return out


# ---------------------------------------------------------------- genre table

# Progression entry: (degree 0-6, seventh?, scale_for_these_chord_tones).
# harmonic_min for the V is exactly what the make-music skill prescribes.
def P(degree: int, seventh: bool = False, scale: str = ""):
    return (degree, seventh, scale)


GENRES = {
    # The default lane of make-16bit-music: dark SNES/Genesis action cue.
    "16bit": {
        "bpm": 150.0, "swing": 0.0, "steps": 16,
        "root": "d", "scale": "natural_min",
        "prog": [P(0, True), P(5, True), P(6, True), P(0, True)],          # Dm Bb C Dm
        "prog_b": [P(3, True), P(5, True), P(6, True), P(4, True, "harmonic_min")],  # Gm Bb C A7
        "sections": {"A": "basic", "B": "theme", "C": "full", "D": "tension"},
        "groove": {"kick": [0, 4, 8, 12], "snare": [4, 12],
                   "hat": [0, 2, 4, 6, 8, 10, 12, 14]},
        "bass_fig": [(0, 0), (2, 0), (4, 12), (6, 0), (8, 0), (10, 7), (12, 12), (14, 0)],
        "lead": {"lo": 62, "hi": 81, "anchor": 60},
        "bass_range": (33, 48), "bass_anchor": 36,
        "stab": [(0, 2), (6, 2), (10, 4)],
        "mix": {"lead": {"crush": 0.22, "filter": "Low", "cutoff": 0.78, "delay_steps": 3, "feedback": 0.38, "send": 0.35},
                "bass": {"drive": 0.15},
                "hat": {"filter": "High", "cutoff": 0.45}},
    },
    # castle lane: Castlevania-style gothic chase — harmonic-minor modal rock
    # (i–VI–VII / i–iv–VI–V with a true V7), octave-gallop bass, organ stabs.
    "castle": {
        "bpm": 140.0, "swing": 0.0, "steps": 16,
        "root": "e", "scale": "harmonic_min",
        "prog": [P(0, True), P(5, True), P(6, True), P(0, True)],          # Em C D Em
        "prog_b": [P(0, True), P(3, True), P(5, True), P(4, True, "harmonic_min")],  # Em Am C B7
        "sections": {"A": "basic", "B": "theme", "C": "full", "D": "tension"},
        "groove": {"kick": [0, 8], "snare": [4, 12],
                   "hat": [0, 2, 4, 6, 8, 10, 12, 14]},
        "bass_fig": [(0, 0), (2, 12), (4, 0), (6, 12), (8, 0), (10, 12), (12, 0), (14, 12)],
        "lead": {"lo": 59, "hi": 80, "anchor": 64},
        "bass_range": (28, 43), "bass_anchor": 33,
        "stab": [(0, 4), (6, 2), (8, 4), (14, 2)],
        "mix": {"lead": {"crush": 0.45, "reverb": 0.4, "delay_steps": 3, "feedback": 0.35, "send": 0.4},
                "bass": {"filter": "Low", "cutoff": 0.5},
                "stab": {"reverb": 0.55}, "arp": {"reverb": 0.35, "send": 0.3}},
    },
    # club lane: 4-on-the-floor dark house.
    "house": {
        "bpm": 124.0, "swing": 0.06, "steps": 16,
        "root": "a", "scale": "natural_min",
        "prog": [P(0, True), P(5, True), P(3, True), P(4, True)],          # Am F Dm Em
        "prog_b": [P(0, True), P(5, True), P(3, True), P(6, True, "dorian")],
        "sections": {"A": "basic", "B": "full", "C": "break", "D": "theme"},
        "groove": {"kick": [0, 4, 8, 12], "clap": [4, 12],
                   "hat": [2, 6, 10, 14]},
        "bass_fig": [(0, 0), (2, 12), (4, 0), (6, 0), (8, 0), (10, 12), (12, 7), (14, 0)],
        "lead": {"lo": 60, "hi": 79, "anchor": 60},
        "bass_range": (33, 45), "bass_anchor": 36,
        "stab": [(2, 2), (10, 2)],
        "mix": {"lead": {"delay_steps": 6, "feedback": 0.45, "send": 0.45, "reverb": 0.3},
                "bass": {"filter": "Low", "cutoff": 0.55},
                "stab": {"chop": 0.6, "chop_steps": 2}},
    },
    # experiments lane: breakbeat / jungle-adjacent, chopped breaks.
    "jungle": {
        "bpm": 168.0, "swing": 0.0, "steps": 16,
        "root": "e", "scale": "harmonic_min",
        "prog": [P(0, True), P(0, True), P(4, True), P(5, True)],          # Em Em C Am
        "prog_b": [P(0, True), P(3, True), P(4, True), P(5, True)],
        "sections": {"A": "basic", "B": "theme", "C": "full", "D": "tension"},
        "groove": {"kick": [0, 10], "snare": [4, 12, 14],
                   "hat": [0, 2, 4, 6, 8, 10, 12, 14]},
        "bass_fig": [(0, 0), (3, 0), (6, 12), (8, 0), (11, 7), (14, 0)],
        "lead": {"lo": 64, "hi": 83, "anchor": 64},
        "bass_range": (28, 43), "bass_anchor": 33,
        "stab": [(0, 4), (8, 2)],
        "mix": {"lead": {"crush": 0.35, "delay_steps": 3, "feedback": 0.3, "send": 0.3},
                "bass": {"drive": 0.3, "filter": "Low", "cutoff": 0.5},
                "snare": {"reverb": 0.35}},
    },
    # experiments lane: 6/8 shrine ritual over a 4/4 grid.
    "shrine68": {
        "bpm": 96.0, "swing": 0.0, "steps": 16,
        "root": "f", "scale": "harmonic_min",
        "prog": [P(0, True), P(0, True), P(5, True), P(4, True, "harmonic_min")],
        "prog_b": [P(0, True), P(5, True), P(4, True, "harmonic_min"), P(0, True)],
        "sections": {"A": "basic", "B": "theme", "C": "full", "D": "tension"},
        "groove": {"kick": [0, 6], "snare": [6, 14],
                   "hat": [0, 2, 4, 6, 8, 10, 12, 14]},
        "bass_fig": [(0, 0), (4, 0), (6, 7), (8, 0), (12, 12), (14, 0)],
        "lead": {"lo": 60, "hi": 81, "anchor": 60},
        "bass_range": (29, 41), "bass_anchor": 34,
        "stab": [(0, 6)],
        "mix": {"lead": {"reverb": 0.5, "delay_steps": 6, "feedback": 0.5, "send": 0.5},
                "bass": {"filter": "Low", "cutoff": 0.45},
                "stab": {"reverb": 0.6}},
    },
}


# ---------------------------------------------------------------- compiler

# (name, role). role decides groove/notes/mix. The "omainur_" prefix is the
# instrument-pack namespace: the anchors ship as files of the same stem (see
# instruments/make_anchors.py) and the app resolves sample ids by name, so the
# prefixed ids bind generated songs to the tuned pack instead of the built-ins.
TRACKS = [
    ("omainur_kick", "kick"), ("omainur_snare", "snare"), ("omainur_clap", "clap"),
    ("omainur_hat_closed", "hat"), ("omainur_hat_open", "hat_open"),
    ("omainur_bass_hit", "bass"), ("omainur_rhodes_chord", "stab"),
    ("omainur_rhodes_tone", "lead"), ("omainur_plucks", "arp"), ("omainur_neon_pad", "pad"),
]

# Pattern chain A..H: content type per slot, and which progression it uses.
ARRANGEMENT = [
    ("basic", "a"), ("theme", "a"), ("full", "a"), ("theme", "a"),
    ("tension", "b"), ("full", "b"), ("break", "b"), ("theme", "b"),
]

ROLE_VOL = {"kick": 0.9, "snare": 0.6, "clap": 0.55, "hat": 0.32, "hat_open": 0.3,
            "bass": 0.75, "stab": 0.42, "lead": 0.5, "arp": 0.28, "pad": 0.33}
ROLE_PAN = {"hat": 0.2, "hat_open": 0.25, "arp": 0.35, "pad": -0.25, "stab": -0.1}


def nearest_in_range(target: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, target))


def fold_to_anchor(midi: int, anchor: int, lo: int, hi: int) -> int:
    """Fold a pitch class onto the octave nearest `anchor` inside [lo, hi]."""
    best = None
    for k in range(-5, 6):
        m = midi + 12 * k
        if lo <= m <= hi:
            d = abs(m - anchor)
            if best is None or d < best[0]:
                best = (d, m)
    return best[1] if best else nearest_in_range(anchor, lo, hi)


def pattern_harmony(genre: dict, pat: int, bar: int):
    """Chord tones + scale + root for `bar` (0-3) of pattern `pat`."""
    root = PC[genre["root"]]
    prog = genre["prog_b"] if ARRANGEMENT[pat][1] == "b" else genre["prog"]
    degree, seventh, alt = prog[bar % len(prog)]
    scale_name = alt or genre["scale"]
    scale = SCALES[scale_name]
    chord = chord_tones(root, scale, degree, seventh)
    chord_root = root + scale[degree]
    return chord, chord_root, scale, root


def empty_lane() -> dict:
    return {"cells": ["Off"] * 64, "lens": [1] * 64, "notes": [0] * 64}


def put(lane: dict, step: int, note: int, accent: bool, length: int = 1) -> None:
    if step < 0 or step > 63 or lane["cells"][step] != "Off":
        return
    room = 1
    for s in range(step + 1, 64):
        if lane["cells"][s] != "Off":
            break
        room += 1
    lane["cells"][step] = "Accent" if accent else "On"
    lane["notes"][step] = max(-24, min(24, note))
    lane["lens"][step] = max(1, min(length, room, 16))


def fill_drums(genre: dict, lanes: list[dict], pat: int) -> None:
    kind = ARRANGEMENT[pat][0]
    g = genre["groove"]
    for bar in range(4):
        off = bar * 16
        last = bar == 3
        if kind == "break":
            for s in g.get("hat", []):
                put(lanes[3], off + s, 0, s % 4 == 2)
            continue
        if kind == "tension":
            put(lanes[0], off, 0, True)
            for s in (8, 12, 14):
                put(lanes[1], off + s, 0, s == 8)
            for s in g.get("hat", []):
                put(lanes[3], off + s, 0, False)
            continue
        for s in g.get("kick", []):
            if kind == "break":
                continue
            put(lanes[0], off + s, 0, s == 0)
        for s in g.get("snare", []):
            put(lanes[1], off + s, 0, pat % 2 == 1 and s == 12)
        for s in g.get("clap", []):
            put(lanes[2], off + s, 0, False)
        for s in g.get("hat", []):
            put(lanes[3], off + s, 0, s % 4 == 2)
        if last and kind in ("theme", "full"):
            put(lanes[1], off + 14, 0, False)
            put(lanes[1], off + 15, 0, True)          # pick-up into the next pattern


def fill_bass(genre: dict, lanes: list[dict], pat: int) -> None:
    kind = ARRANGEMENT[pat][0]
    if kind == "break":
        return
    lo, hi = genre["bass_range"]
    anchor = genre["bass_anchor"]
    for bar in range(4):
        off = bar * 16
        chord, chord_root, _, _ = pattern_harmony(genre, pat, bar)
        if kind == "tension":
            m = fold_to_anchor(chord_root, anchor, lo, hi)
            put(lanes[5], off, m - anchor, bar == 0, length=8)
            continue
        for s, iv in genre["bass_fig"]:
            m = fold_to_anchor(chord_root + iv, anchor + iv, lo, hi)
            put(lanes[5], off + s, m - anchor, s == 0 and bar == 0)


def fill_harmony(genre: dict, lanes: list[dict], pat: int, rng: LCG) -> None:
    kind = ARRANGEMENT[pat][0]
    lo, hi = genre["lead"]["lo"], genre["lead"]["hi"]
    anchor = genre["lead"]["anchor"]

    # Stabs: chord root hits (long in slow genres).
    if kind in ("full", "theme") and kind != "break":
        for bar in range(4):
            off = bar * 16
            chord, chord_root, _, _ = pattern_harmony(genre, pat, bar)
            for s, ln in genre["stab"]:
                put(lanes[6], off + s, fold_to_anchor(chord_root, 48, 41, 60) - 48, s == 0, length=ln)

    # Pad: one long root where the section breathes.
    if kind in ("full", "break", "tension"):
        chord, chord_root, _, _ = pattern_harmony(genre, pat, 0)
        put(lanes[9], 0, fold_to_anchor(chord_root, 48, 41, 60) - 48, False, length=16)

    # Arp: 8th-note chord-tone sparkle, full sections only.
    if kind == "full":
        for bar in range(4):
            off = bar * 16
            chord, _, _, _ = pattern_harmony(genre, pat, bar)
            tones = sorted(chord)
            for i, s in enumerate(range(0, 16, 2)):
                pc = tones[i % len(tones)]
                m = fold_to_anchor(60 + pc, 72, 60, 84)
                put(lanes[8], off + s, m - 72, False, length=1)

    # Lead: the generated motive. Holds extend the previous note's length.
    if kind in ("theme", "full"):
        flat: list[int] = []
        for bar in range(4):
            chord, _, scale, root = pattern_harmony(genre, pat, bar)
            flat += gen_melody(rng, root, scale, chord, 16, lo, hi)
        placed: list[tuple[int, int]] = []
        for i, v in enumerate(flat):
            if v == 0:
                continue
            if placed and flat[i - 1] == v:
                # hold: extend the still-sounding note instead of retriggering
                for j in range(len(placed) - 1, -1, -1):
                    st, ln = placed[j]
                    if st + ln == i and i - st < 16:
                        placed[j] = (st, ln + 1)
                        break
                continue
            if len(placed) >= 40:
                continue
            placed.append((i, 1))
        for i, (st, ln) in enumerate(placed):
            bar = st // 16
            chord, _, _, _ = pattern_harmony(genre, pat, bar)
            accent = st % 16 == 0
            put(lanes[7], st, flat[st] - anchor, accent, length=ln)


FX_KEYS = {"filter", "cutoff", "resonance", "drive", "crush", "downsample", "distort",
           "reverb", "delay_steps", "feedback", "chop", "chop_steps", "ring", "ring_freq",
           "eq_low", "eq_mid", "eq_high", "reverse", "fine"}


def apply_fx(genre: dict, roles: list[str], tracks: list[dict]) -> None:
    for i, role in enumerate(roles):
        fx = genre["mix"].get(role, {})
        track = tracks[i]
        for k, v in fx.items():
            if k in FX_KEYS:
                track["fx"][k] = v
        if role == "lead":
            track["send"] = fx.get("send", 0.0)
        if role == "stab":
            track["send"] = fx.get("send", 0.15)


def generate(genre_name: str, seed: int) -> dict:
    genre = GENRES[genre_name]
    rng = LCG(seed)
    names = [n for n, _ in TRACKS]
    roles = [r for _, r in TRACKS]
    tracks = []
    for i, (name, role) in enumerate(TRACKS):
        tracks.append({
            "sample": i, "lanes": [empty_lane() for _ in range(8)],
            "note_len": 1, "volume": ROLE_VOL[role], "pitch": 0.0,
            "pan": ROLE_PAN.get(role, 0.0), "send": 0.0,
            "fx": {"filter": "Off", "cutoff": 0.6, "resonance": 0.2, "drive": 0.0,
                   "crush": 0.0, "downsample": 0.0, "distort": 0.0, "fine": 0.0,
                   "reverse": False, "ring": 0.0, "ring_freq": 0.4, "chop": 0.0,
                   "chop_steps": 1, "reverb": 0.0, "delay_steps": 3, "feedback": 0.35,
                   "eq_low": 0.0, "eq_mid": 0.0, "eq_high": 0.0},
            "mute": False, "solo": False,
        })
    lanes = [t["lanes"] for t in tracks]

    for pat in range(8):
        fill_drums(genre, lanes[0], pat)
        fill_bass(genre, lanes[5], pat)
        fill_harmony(genre, [tl[pat] for tl in lanes], pat, rng)

    apply_fx(genre, roles, tracks)

    # The hook carrier owns the lead: one designed motif carried across the
    # form (recurrence + answer + return; spikes 005-009). fill_harmony's
    # lead lane is overwritten; its stabs/arps/pads remain as support.
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _here = _Path(__file__).resolve().parent
        if str(_here) not in _sys.path:
            _sys.path.insert(0, str(_here))
        import hook_form
        hook_form.carry_hook({"song": {"tracks": tracks}, "names": names}, genre_name, seed)
    except ImportError:
        pass  # hook_form absent: the legacy per-section lead stands

    # The song form: A(intro) B C D | E(tension) F G(break) H, then loop back to B.
    chain = []
    for i in range(8):
        nxt = (i + 1) % 8 if i < 7 else 1
        chain.append({"next": nxt})
    # A pattern holds its own 4-bar progression; the chain advances at the
    # 4-bar wrap. genre["steps"] is the per-bar 4/4 grid.
    steps = [genre["steps"] * 4] * 8

    return {
        "format": "omarchy-sequencer-song", "version": 1, "genre": genre_name,
        "seed": seed,
        "names": names,
        "packs": [],
        "song": {
            "bpm": genre["bpm"], "swing": genre["swing"], "master": 0.8,
            "steps": steps, "current": 0, "queued": None,
            "queued_chain": chain, "tracks": tracks,
        },
    }


# ---------------------------------------------------------------- validation

# Where the compiler folds each pitched track's octave; must match fill_* code.
def track_anchor(base: str, genre: dict) -> int:
    if base == "rhodes_tone":
        return genre["lead"]["anchor"]
    if base == "plucks":
        return 72
    if base in ("rhodes_chord", "neon_pad"):
        return 48
    return genre["bass_anchor"]


def validate(s: dict, genre_name: str) -> list[str]:
    errors = []
    genre = GENRES[genre_name]
    root = PC[genre["root"]]
    song = s["song"]
    names = s["names"]
    for pat in range(8):
        prog = genre["prog_b"] if ARRANGEMENT[pat][1] == "b" else genre["prog"]
        for bar in range(4):
            degree, seventh, alt = prog[bar]
            scale_name = alt or genre["scale"]
            scale = SCALES[scale_name]
            chord = chord_tones(root, scale, degree, seventh)
            scale_pcs = {(root + x) % 12 for x in scale}
            for tr in song["tracks"]:
                lane = tr["lanes"][pat]
                for step in range(bar * 16, (bar + 1) * 16):
                    if lane["cells"][step] == "Off" or lane["notes"][step] == 0:
                        continue
                    name = names[tr["sample"]] if isinstance(tr["sample"], int) else tr["sample"]
                    base = name.removeprefix("omainur_")
                    if base in ("kick", "snare", "clap", "hat_closed", "hat_open"):
                        continue
                    m = track_anchor(base, genre) + lane["notes"][step]
                    if m % 12 not in chord and m % 12 not in scale_pcs:
                        errors.append(f"out-of-key {name} pat{pat} bar{bar} step{step}: midi {m}")
        if len(errors) > 30:
            errors.append("...truncated")
            break
    return errors


if __name__ == "__main__":
    import hashlib
    import sys

    genre = sys.argv[1] if len(sys.argv) > 1 else "16bit"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out = sys.argv[3] if len(sys.argv) > 3 else f"{genre}_{seed}.json"
    data = generate(genre, seed)
    text = json.dumps(data, separators=(",", ":"))
    with open(out, "w") as f:
        f.write(text)
    errors = validate(data, genre)
    print(f"genre={genre} seed={seed} sha256={hashlib.sha256(text.encode()).hexdigest()[:16]}")
    print(f"bpm={data['song']['bpm']} tracks={len(data['song']['tracks'])} bytes={len(text)}")
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" ", e)
        sys.exit(1)
    print("validation: all notes in chord tones or scale — PASS")
