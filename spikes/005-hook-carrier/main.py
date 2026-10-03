#!/usr/bin/env python3
"""005 hook-carrier: carry a designed hook through the A-H chain.

Lane-level spike. Builds a 2-bar hook from the genre's own harmony, applies one
deterministic section op per pattern, writes lanes through the SAME data shape
the compiler uses, validates with og.validate(), and gates:
  G1 recurrence: hook contour present in >= 4/8 sections
  G2 distinctness: >= 6/8 section lane-hashes differ (recurrence != repetition)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "omainur/generator"))
import omainur_gen as og


# ---------------------------------------------------------------- hook design

def design_hook(genre: dict, rng: og.LCG) -> list[dict]:
    """A 2-bar hook over the progression's first two chords.

    8 eighth-note slots per bar. Rhythm: a deterministic mask (never a static
    arpeggio; at least one rest, at least one hold). Contour: chord-tone
    anchored, stepwise preferred, one leap allowed, ends on a long chord tone.
    Returns events: {slot, deg} where deg = scale-degree index (0 = root),
    resolved against each bar's chord later by the ops.
    """
    mask = [1, 1, 0, 1, 1, 1, 0, 1]  # slots that carry an onset (rests are real)
    scale = og.SCALES[genre["scale"]]
    # contour over scale degrees: rise, one leap, stepwise resolve down
    contour = [0, 2, 4, 2, 4, 6, 5, 4]
    leap = rng.pick(3)  # where the one designed leap sits
    contour[leap] = contour[leap - 1] + 4 if contour[leap - 1] + 4 <= 7 else contour[leap - 1] - 3
    hook = []
    for slot in range(16):
        bar, pos = slot // 8, slot % 8
        if mask[pos]:
            deg = contour[pos] if bar == 0 else max(contour[pos] - 1, 0)
            hook.append({"slot": slot, "deg": deg})
    return hook


# ------------------------------------------------------------------- section ops

def reland(events: list[dict], genre: dict, pat: int) -> list[dict]:
    """Re-fit the hook to each bar's chord. The identity survives the harmony."""
    out = []
    drop = 0
    for ev in events:
        bar = ev["slot"] // 8
        chord, chord_root, scale, root = og.pattern_harmony(genre, pat, bar)
        chord_tones = sorted(chord)
        # snap the degree to the nearest chord tone by pitch class
        target_pc = (root + scale[ev["deg"] % len(scale)]) % 12
        snapped = min(chord_tones, key=lambda pc: (pc - target_pc) % 12)
        deg = (snapped - root) % 12
        out.append({"slot": ev["slot"], "pc": (root + deg) % 12, "chord_root": chord_root})
        drop += 1
    return out


def op_lane(events: list[dict], op: str, genre: dict, pat: int, rng: og.LCG) -> list[dict]:
    """Compile one section: hook events -> lane events for op semantics."""
    relanded = reland(events, genre, pat)
    if op in ("state", "harmonize_full"):
        return relanded
    if op == "reland":
        # the answer keeps every onset but answers one octave up (pc preserved:
        # key membership is exact, the validator must still pass)
        return [{**e, "oct": 1} if (e["slot"] // 8) == 1 else e for e in relanded]
    if op == "fragment":
        return [e for e in relanded if e["slot"] < 8]  # first half only, over the pedal
    if op == "truncate":
        return [e for e in relanded if e["slot"] % 8 in (0, 4)]  # head notes, long
    if op == "tag":
        tail = [e for e in relanded if e["slot"] >= 12]
        return [{"slot": e["slot"] - 12, "pc": e["pc"], "chord_root": e["chord_root"]} for e in tail]
    raise ValueError(op)


OPS = ["state", "reland", "harmonize_full", "reland", "fragment", "harmonize_full", "truncate", "tag"]


# ------------------------------------------------------------------- assembly

def empty_lane() -> dict:
    return {"cells": ["Off"] * 64, "lens": [1] * 64, "notes": [0] * 64}


def lane_hash(lane: dict) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(lane, sort_keys=True).encode()).hexdigest()[:12]


def build(genre_name: str, seed: int) -> dict:
    genre = og.GENRES[genre_name]
    song = og.generate(genre_name, seed)  # real compiler: drums, bass, fx, chain
    rng = og.LCG(seed ^ 0x5EED)
    hook = design_hook(genre, rng)
    lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")
    per_bar = []
    for pat in range(8):
        lane = song["song"]["tracks"][lead_idx]["lanes"][pat]
        # clear what fill_harmony drew in this lane: the hook owns it now
        for step in range(64):
            lane["cells"][step] = "Off"
            lane["notes"][step] = 0
            lane["lens"][step] = 1
        events = op_lane(hook, OPS[pat], genre, pat, rng)
        anchor = genre["lead"]["anchor"]
        for ev in events:
            slot, pos = ev["slot"] // 8, ev["slot"] % 8
            step = slot * 16 + pos * 2
            if lane["cells"][step] != "Off":
                continue
            # pitch: fold the pitch class into the lead octave near the anchor
            midi = anchor + ((ev["pc"] - anchor) % 12)
            if ev.get("oct"):
                midi += 12
            if midi > genre["lead"]["hi"]:
                midi -= 12
            lane["cells"][step] = "On"
            lane["notes"][step] = midi - anchor
            lane["lens"][step] = 2
            per_bar.append((pat, slot, step, midi))
    errors = og.validate(song, genre_name)
    return song, hook, per_bar, errors


# -------------------------------------------------------------------- gates

def contour_of_lane(lane: dict) -> list[int]:
    onsets = [(s, lane["notes"][s]) for s in range(64)
              if lane["cells"][s] != "Off" and lane["notes"][s] != 0]
    return [n for _, n in onsets]


def contour_match(lane: dict, hook_lane: dict) -> float:
    """Best normalized alignment of the hook's delta profile against the lane's."""
    hook_notes = contour_of_lane(hook_lane)
    lane_notes = contour_of_lane(lane)
    if len(hook_notes) < 3 or len(lane_notes) < len(hook_notes):
        return 0.0
    profile = np.diff(np.array(hook_notes, dtype=float))
    best = 0.0
    for i in range(len(lane_notes) - len(hook_notes) + 1):
        window = np.diff(np.array(lane_notes[i:i + len(hook_notes)], dtype=float))
        if np.std(profile) < 1e-9 or np.std(window) < 1e-9:
            continue
        score = abs(float(np.corrcoef(profile, window)[0, 1]))
        best = max(best, score)
    return best


GATE_GRAIN = {
    # how much of the hook each op must visibly restate, per the op's semantics
    "A": ("state", 1.0), "B": ("reland", 0.7), "C": ("harmonize_full", 1.0),
    "D": ("reland", 0.7), "E": ("fragment", 0.5), "F": ("harmonize_full", 1.0),
    "G": ("truncate", 0.35), "H": ("tag", 0.35),
}


def gates(song: dict, hook_lane: dict) -> dict:
    """Recurrence at each op's own grain + distinctness across all lanes."""
    lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")
    lanes = song["song"]["tracks"][lead_idx]["lanes"]
    matches = [contour_match(lanes[p], hook_lane) for p in range(8)]
    recurrence = 0
    per_section = []
    pattern_names = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for p, name in enumerate(pattern_names):
        op, grain = GATE_GRAIN[name]
        threshold = 0.7 * grain + 0.05
        hit = matches[p] >= threshold
        recurrence += hit
        per_section.append({"pattern": name, "op": op, "match": round(matches[p], 3),
                            "grain": grain, "hit": hit})
    hashes = {lane_hash(lanes[p]) for p in range(8)}
    return {"recurrence": recurrence, "distinct": len(hashes),
            "per_section": per_section,
            "g1_pass": recurrence >= 4, "g2_pass": len(hashes) >= 6}


if __name__ == "__main__":
    genre_name = sys.argv[1] if len(sys.argv) > 1 else "castle"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1986
    import hashlib
    song, hook, placed, errors = build(genre_name, seed)
    print("validator:", errors if errors else "PASS")
    lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")
    result = gates(song, song["song"]["tracks"][lead_idx]["lanes"][0])
    print(json.dumps(result, indent=1))
    Path("/tmp/spike005.json").write_text(json.dumps(song, separators=(",", ":")))
    verdict = "VALIDATED" if (not errors and result["g1_pass"] and result["g2_pass"]) else "INVALIDATED"
    print("VERDICT:", verdict)