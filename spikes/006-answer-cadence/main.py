#!/usr/bin/env python3
"""006 answer-cadence: the answer sites are designed, not accidental.

One placement contract for every section: each event carries absolute midi,
placement is total (never dropped, never re-folded by a later heuristic — a
fold applied after an octave rule silently undoes it; the total function is
the contract), pitch classes stay in-key so og.validate() referees.

Form grammar (declared before running):
  B/D answer A: start a designed interval away (the third/sixth family),
  state the tail an octave up, cadence down to the root an octave low.
  C/F diverge with a per-site ornament. H tags the tail and returns home.

Gates:
  G3 answer:  pc(B.start) - pc(A.start) in {3,4,8,9} AND B ends on the root
  G4 return:  H's last onset is the root
  G5 identity: >= 7 of 8 section lane hashes distinct
  G1/G2 carried from 005
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec005 = importlib.util.spec_from_file_location("s005", HERE.parent / "005-hook-carrier/main.py")
s005 = importlib.util.module_from_spec(spec005)
spec005.loader.exec_module(s005)

og = s005.og
OPS = list(s005.OPS)

ANSWER_INTERVALS = (3, 4, 8, 9)  # minor/major thirds and sixths: the answer family


def reland_full(events, genre, pat):
    """Hook re-fit to this pattern's chords as absolute midi in the lead range.

    Total: every event lands. Octave folds happen once, here, in order:
    nearest octave, range, then the silence rule (offset 0 is rest — in a
    root-anchored genre the root's pitch class folds onto the anchor, so it
    lifts an octave).
    """
    anchor = genre["lead"]["anchor"]
    lo, hi = genre["lead"]["lo"], genre["lead"]["hi"]
    out = []
    for ev in sorted(events, key=lambda e: e["slot"]):
        bar = ev["slot"] // 8
        chord, chord_root, scale, root = og.pattern_harmony(genre, pat, bar)
        chord_pcs = sorted(chord)
        target_pc = (root + scale[ev["deg"] % 7]) % 12
        snapped = min(chord_pcs, key=lambda pc: (pc - target_pc) % 12)
        midi = anchor + (snapped - anchor) % 12
        if midi < lo:
            midi += 12
        if midi - anchor == 0:  # offset 0 is silence in the lane format
            midi += 12
        if midi > hi:
            midi -= 12
        out.append({"slot": ev["slot"], "midi": midi, "pc": snapped})
    return out


def answer_events(events, genre, pat, site_rng, a_start_pc):
    """Landed hook with the call-site designed: interval start, octave tail, low cadence.

    The interval is measured from the CALL's actual first onset (A's start),
    not from the genre root: a call that begins on its chord's third must be
    answered a third-family interval away from THAT tone, or the answer is a
    unison. 1987 proved the distinction (interval 0 against a third-start).
    """
    landed = reland_full(events, genre, pat)
    chord0, _, _, root = og.pattern_harmony(genre, pat, 0)
    chord_pcs = sorted(chord0)
    candidates = [pc for pc in chord_pcs if (pc - a_start_pc) % 12 in ANSWER_INTERVALS]
    start_pc = candidates[site_rng.pick(len(candidates))] if candidates else chord_pcs[0]
    last_slot = max(e["slot"] for e in landed) if landed else 15
    out = []
    for ev in landed:
        new = dict(ev)
        if ev["slot"] // 8 == 1 and new["midi"] + 12 <= genre["lead"]["hi"]:
            new["midi"] += 12  # the tail states an octave up
        if ev["slot"] == 0:  # the answer starts a designed interval away from the CALL
            candidate = genre["lead"]["anchor"] - 12 + (start_pc - genre["lead"]["anchor"]) % 12
            if candidate < genre["lead"]["lo"]:
                candidate += 12
            if candidate - genre["lead"]["anchor"] == 0:
                candidate += 12
            new["midi"] = candidate
        if ev["slot"] == last_slot:  # the cadence: resolve down, one octave low
            new["midi"] = genre["lead"]["anchor"] - 12 + (root - genre["lead"]["anchor"]) % 12
        out.append(new)
    return out


def ornament_events(events, genre, pat, site_rng):
    """Full statement; a per-site approach tone may precede it."""
    landed = reland_full(events, genre, pat)
    if not site_rng.chance(50):
        return landed
    chord, chord_root, scale, root = og.pattern_harmony(genre, pat, 0)
    approach_pc = sorted(chord)[site_rng.pick(len(chord))]
    approach = genre["lead"]["anchor"] + (approach_pc - genre["lead"]["anchor"]) % 12
    if approach < genre["lead"]["lo"]:
        approach += 12
    return [{"slot": -1, "midi": approach, "pc": approach_pc}] + landed


def fragment_events(events, genre, pat):
    return [e for e in reland_full(events, genre, pat) if e["slot"] < 8]


def truncate_events(events, genre, pat):
    return [e for e in reland_full(events, genre, pat) if e["slot"] % 8 in (0, 4)]


def tag_events(events, genre, pat):
    landed = reland_full(events, genre, pat)
    tail = [e for e in landed if e["slot"] >= 12]
    out = [{"slot": e["slot"] - 12, "midi": e["midi"], "pc": e["pc"]} for e in tail]
    if out:
        root_pc = og.PC[genre["root"]]
        out[-1]["midi"] = genre["lead"]["anchor"] - 12 + (root_pc - genre["lead"]["anchor"]) % 12
    return out


def build_006(genre_name: str, seed: int):
    genre = og.GENRES[genre_name]
    song = og.generate(genre_name, seed)
    hook = s005.design_hook(genre, og.LCG(seed ^ 0x5EED))
    lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")
    # The call comes first: A is built before anything answers it, and the
    # answers measure their interval from A's ACTUAL first onset.
    a_landed = reland_full(hook, genre, 0)
    a_start_pc = a_landed[0]["pc"] if a_landed else og.PC[genre["root"]]
    for pat, name in enumerate("ABCDEFGH"):
        lane = song["song"]["tracks"][lead_idx]["lanes"][pat]
        for step in range(64):
            lane["cells"][step] = "Off"
            lane["notes"][step] = 0
            lane["lens"][step] = 1
        site_rng = og.LCG(seed * 1000 + pat)
        if name in ("B", "D"):
            events = answer_events(hook, genre, pat, site_rng, a_start_pc)
        elif name in ("A", "C", "F"):
            events = ornament_events(hook, genre, pat, site_rng)
        elif name == "E":
            events = fragment_events(hook, genre, pat)
        elif name == "G":
            events = truncate_events(hook, genre, pat)
        else:
            events = tag_events(hook, genre, pat)
        for ev in sorted(events, key=lambda e: e["slot"]):
            step = (ev["slot"] // 8) * 16 + (ev["slot"] % 8) * 2 if ev["slot"] >= 0 else 62
            if step < 0 or step > 63 or lane["cells"][step] != "Off":
                continue
            lane["cells"][step] = "On"
            lane["notes"][step] = ev["midi"] - genre["lead"]["anchor"]
            lane["lens"][step] = 2
    errors = og.validate(song, genre_name)
    return song, hook, errors, lead_idx


def contour_steps(lane):
    """Onsets as (step, note) so slices can select by hook slot."""
    return [(s, lane["notes"][s]) for s in range(64)
            if lane["cells"][s] != "Off" and lane["notes"][s] != 0]


def slice_expectation(name):
    """Which hook slots each op must visibly restate (the call's own grain)."""
    return {"A": None, "B": (8, 15), "C": None, "D": (8, 15),
            "E": (0, 7), "F": None, "G": (0, 15, (0, 4, 8, 12)), "H": (12, 15)}[name]


def slot_of(step):
    return (step // 16) * 8 + (step % 16) // 2


def match_slice(lane, hook_lane, expectation):
    """Correlation against the expected slice; exact deltas for tiny ones."""
    if expectation is None:  # full statement: the 005 full-profile rule
        return s005.contour_match(lane, hook_lane)
    if len(expectation) == 3:
        lo, hi, slots = expectation
    else:
        lo, hi = expectation
        slots = None
    hook = [(slot_of(s), n) for s, n in contour_steps(hook_lane)]
    want = [n for slot, n in hook if lo <= slot <= hi and (slots is None or slot in slots)]
    got = [n for _, n in contour_steps(lane)]
    if not want:
        return 0.0
    if len(want) < 3:  # too few deltas for correlation: require exact contour
        want_d = [b - a for a, b in zip(want, want[1:])]
        best = 0.0
        for i in range(len(got) - len(want) + 1):
            window = got[i:i + len(want)]
            if [b - a for a, b in zip(window, window[1:])] == want_d:
                best = 1.0
        return best
    profile = [b - a for a, b in zip(want, want[1:])]
    best = 0.0
    import numpy as _np
    for i in range(len(got) - len(want) + 1):
        window = _np.array(got[i:i + len(want)], dtype=float)
        deltas = _np.diff(window)
        if _np.std(deltas) < 1e-9 or _np.std(profile) < 1e-9:
            continue
        best = max(best, abs(float(_np.corrcoef(_np.array(profile, dtype=float), deltas)[0, 1])))
    return best


def gates_006(song, genre, hook, lead_idx):
    lanes = song["song"]["tracks"][lead_idx]["lanes"]
    anchor = genre["lead"]["anchor"]
    root_pc = og.PC[genre["root"]]
    start_a = (anchor + s005.contour_of_lane(lanes[0])[0]) % 12
    start_b = (anchor + s005.contour_of_lane(lanes[1])[0]) % 12
    end_b = (anchor + s005.contour_of_lane(lanes[1])[-1]) % 12
    end_h = (anchor + s005.contour_of_lane(lanes[7])[-1]) % 12
    interval_b = (start_b - start_a) % 12
    hashes = {s005.lane_hash(lanes[p]) for p in range(8)}
    per_op = {}
    recurrence = 0
    for p, name in enumerate("ABCDEFGH"):
        m = match_slice(lanes[p], lanes[0], slice_expectation(name))
        per_op[name] = round(m, 3)
        if m >= 0.75:
            recurrence += 1
    return {
        "g3_answer": {"interval_b": interval_b, "end_pc_b": end_b,
                      "pass": interval_b in ANSWER_INTERVALS and end_b == root_pc},
        "g4_return": {"end_pc_h": end_h, "pass": end_h == root_pc},
        "g5_identity": {"distinct": len(hashes), "pass": len(hashes) >= 7},
        "g1_recurrence": {"count": recurrence, "match_per_op": per_op,
                          "pass": recurrence >= 4},
    }


if __name__ == "__main__":
    genre_name = sys.argv[1] if len(sys.argv) > 1 else "castle"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1986
    song, hook, errors, lead_idx = build_006(genre_name, seed)
    print("validator:", errors if errors else "PASS")
    result = gates_006(song, og.GENRES[genre_name], hook, lead_idx)
    print(json.dumps(result, indent=1))
    Path("/tmp/spike006.json").write_text(json.dumps(song, separators=(",", ":")))
    ok = (not errors) and all(v["pass"] for v in result.values())
    print("VERDICT:", "VALIDATED" if ok else "INVALIDATED")