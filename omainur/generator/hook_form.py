#!/usr/bin/env python3
"""Hook-form compiler: a designed hook carries the whole lead across the form.

Spike 005-009 promoted into the generator. The old fill_harmony drew every
section's melody as an independent stream (the root cause of "salad": nothing
recurred, nothing developed). This module replaces it:

- design_hook(): one 2-bar motif per genre, deterministic from the seed,
  contour + rhythm as designed data over the genre's own harmony.
- reland(): the hook re-fit to each section's chords (identity survives
  reharmonization).
- section ops: state / answer / ornament / fragment / truncate / tag — the
  section's relationship to the call, as data in GENRES[section_ops].
- The call comes first: A is built before anything answers it, and every
  answer measures its interval from A's actual first onset (a call that
  begins on its chord's third must be answered away from that tone,
  not from the genre root — seed 1987 proved the distinction).

Gates a compiler run must pass (the not-salad contract):
  G1 recurrence: hook restated in >= 4/8 sections at the op's own grain
  G2 distinctness: >= 6/8 lead lane hashes differ (recurrence != repetition)
  G3 answer: B starts a third/sixth-family interval from the call and
     cadences to the root
  G4 return: H's tag ends on the root
  plus og.validate(): every pitched note a chord or scale tone.

All findings trace to spikes/005..009 in this repository.
"""
from __future__ import annotations

import hashlib
import json


def design_hook(genre: dict, rng) -> list[dict]:
    """A 2-bar hook over the progression's first two chords (8 slots/bar)."""
    mask = [1, 1, 0, 1, 1, 1, 0, 1]
    contour = [0, 2, 4, 2, 4, 6, 5, 4]
    leap = rng.pick(3)
    contour[leap] = contour[leap - 1] + 4 if contour[leap - 1] + 4 <= 7 else contour[leap - 1] - 3
    hook = []
    for slot in range(16):
        bar, pos = slot // 8, slot % 8
        if mask[pos]:
            deg = contour[pos] if bar == 0 else max(contour[pos] - 1, 0)
            hook.append({"slot": slot, "deg": deg})
    return hook


def reland(events: list[dict], genre: dict, pat: int) -> list[dict]:
    """A section's hook: degree -> nearest in-chord tone for that bar."""
    from omainur_gen import SCALES, pattern_harmony

    out = []
    for ev in sorted(events, key=lambda e: e["slot"]):
        bar = ev["slot"] // 8
        chord, chord_root, scale, root = pattern_harmony(genre, pat, bar)
        target_pc = (root + scale[ev["deg"] % 7]) % 12
        snapped = min(sorted(chord), key=lambda pc: (pc - target_pc) % 12)
        out.append({"slot": ev["slot"], "pc": snapped, "root": root % 12})
    return out


def _range_fold(midi: int, genre: dict) -> int:
    """One fold pass through the lead range; the silence rule lives in placement."""
    lo, hi = genre["lead"]["lo"], genre["lead"]["hi"]
    while midi > hi:
        midi -= 12
    while midi < lo:
        midi += 12
    return midi


def section_events(hook: list[dict], genre: dict, pat: int, site_rng,
                   a_start_pc: int, tag_len: int = 1) -> list[dict]:
    """Event list (absolute midi) for one section, by its op. Total: no drop."""
    name = "ABCDEFGH"[pat]
    anchor = genre["lead"]["anchor"]
    ops = genre.get("section_ops") or {
        "A": "state", "B": "answer", "C": "ornament", "D": "answer",
        "E": "fragment", "F": "ornament", "G": "truncate", "H": "tag",
    }
    op = ops[name]
    landed = reland(hook, genre, pat)
    last_slot = max(e["slot"] for e in landed) if landed else 15

    def midi_of(ev) -> int:
        return _range_fold(anchor + (ev["pc"] - anchor) % 12, genre)

    if op == "state":
        out = [("slot", e) for e in landed]
        return [{"slot": e["slot"], "midi": midi_of(e)} for e in landed]

    if op == "answer":
        chord0 = landed[0]
        chord_pcs = sorted({e["pc"] for e in landed})  # this section's chord tones
        cands = [pc for pc in chord_pcs if (pc - a_start_pc) % 12 in (3, 4, 8, 9)]
        start_pc = cands[site_rng.pick(len(cands))] if cands else chord_pcs[0]
        out = []
        for e in landed:
            midi = midi_of(e)
            if e["slot"] // 8 == 1 and midi + 12 <= genre["lead"]["hi"]:
                midi += 12
            if e["slot"] == 0:
                cand = anchor - 12 + (start_pc - anchor) % 12
                if cand < genre["lead"]["lo"]:
                    cand += 12
                if cand - anchor == 0:
                    cand += 12
                midi = cand
            if e["slot"] == last_slot:
                midi = anchor - 12 + (e["root"] - anchor) % 12
            out.append({"slot": e["slot"], "midi": midi})
        return out

    if op == "ornament":
        out = []
        approach = None
        if site_rng.chance(50):  # M2's contract: one draw per site
            first = landed[0]
            from omainur_gen import pattern_harmony
            chord, _, _, _ = pattern_harmony(genre, pat, 0)
            pc = sorted(chord)[site_rng.pick(len(chord))]
            approach = {"slot": -1, "midi": _range_fold(anchor + (pc - anchor) % 12, genre)}
        body = [{"slot": e["slot"], "midi": midi_of(e)} for e in landed]
        return ([approach] if approach else []) + body

    if op == "fragment":
        return [{"slot": e["slot"], "midi": midi_of(e)} for e in landed if e["slot"] < 8]

    if op == "truncate":
        return [{"slot": e["slot"], "midi": midi_of(e)} for e in landed if e["slot"] % 8 in (0, 4)]

    if op == "tag":
        horizon = 16 - tag_len * 8
        tail = [e for e in landed if e["slot"] >= horizon]
        out = [{"slot": e["slot"] - horizon, "midi": midi_of(e)} for e in tail]
        if out:
            out[-1]["midi"] = anchor - 12 + (landed[-1]["root"] - anchor) % 12
        return out

    raise ValueError(f"unknown section op: {op}")


def carry_hook(song: dict, genre_name: str, seed: int) -> dict:
    """Replace fill_harmony's per-section draws with the hook carrier."""
    from omainur_gen import GENRES, LCG, TRACKS

    genre = GENRES[genre_name]
    hook = design_hook(genre, LCG(seed ^ 0x5EED))
    lead_idx = next(i for i, (name, role) in enumerate(TRACKS) if role == "lead")
    a_start = reland(hook, genre, 0)
    a_start_pc = a_start[0]["pc"] if a_start else 0
    for pat, name in enumerate("ABCDEFGH"):
        lane = song["song"]["tracks"][lead_idx]["lanes"][pat]
        for step in range(64):
            lane["cells"][step] = "Off"
            lane["notes"][step] = 0
            lane["lens"][step] = 1
        events = section_events(hook, genre, pat, LCG(seed * 1000 + pat), a_start_pc)
        for ev in sorted(events, key=lambda e: e["slot"]):
            step = (ev["slot"] // 8) * 16 + (ev["slot"] % 8) * 2 if ev["slot"] >= 0 else 62
            if step < 0 or step > 63 or lane["cells"][step] != "Off":
                continue
            offset = ev["midi"] - genre["lead"]["anchor"]
            if offset == 0:  # offset 0 is silence; the root's identity lives at +12
                offset = 12
            lane["cells"][step] = "On"
            lane["notes"][step] = offset
            lane["lens"][step] = 2
    return song