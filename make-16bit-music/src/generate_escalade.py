#!/usr/bin/env python3
"""Escalade — procedural castle-cue on the overdub model.

The session: seven fixed layers tracked in order — kick, snare, hats (three
drum takes), then bass, comp, lead, counter over them — each take cut ONCE
against the takes below it, never revisited. The arrangement is a matrix of
six fixed blocks by seven layers, each cell a named role backed by a pattern.
The lead's two-bar rhythm varies locally before notes are assigned. Strong
claimed beats get chord tones; weak get stepwise scale motion; rests are real;
cadences resolve.
Procedural, deterministic, and deliberately mediocre-but-plausible: legality
comes from the grammar, not from dice.
"""
from __future__ import annotations

import random
import sys

from paths import track_path
from event_variation import swap_event_onsets, variation_metrics, vary_phrase_mask

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, organ,
    render_bell, render_crash, render_hat, render_kick, render_snare,
    render_tom, saw_bl, sine, square_bl, pulse_bl, tri, write_wav,
)

BPM = 132
BARS = 66  # 2:00 exactly at 132 BPM
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# A harmonic minor; the V is the dagger (A major triad over the minor sea).
AM = ((57, 60, 64), 45, False)   # A C E, root A2
GM = ((55, 59, 62), 43, False)   # G B D
F_ = ((53, 57, 60), 41, True)    # F A C (major IV in minor — Aeolian color)
EM = ((52, 56, 59), 40, False)   # E G B  (natural v, for the bridge)
ED = ((52, 56, 61), 40, True)    # E G# B — the dagger, dominant of Am
DM = ((50, 53, 57), 38, False)   # D F A
C_ = ((48, 52, 55), 36, True)    # C E G


def block_of(bar: int) -> str:
    """The arrangement walk: which block owns this bar."""
    bounds = BLOCK_BOUNDS
    for name, a, b in bounds:
        if a <= bar < b:
            return name
    return "finale"


BLOCK_BOUNDS = [
    ("procession", 0, 4),
    ("theme", 4, 20),
    ("tower", 20, 28),
    ("theme2", 28, 44),
    ("crypt", 44, 54),
    ("finale", 54, 66),
]

# The matrix: block x layer -> named role. Drums read grids; pitched layers
# read rhythm masks; "none" means the take is silent there.
MATRIX = {
    # block:    [kick, snare, hats, bass, comp, lead, counter]
    "procession": ["heart", "none", "none", "none", "pedal_organ", "foreshadow", "none"],
    "theme": ["stomp", "backbeat", "eighths", "gallop", "triads", "theme", "rests"],
    "tower": ["half", "half", "eighths", "walk", "sevenths", "sequence", "rests"],
    "theme2": ["stomp", "backbeat", "drive", "gallop", "triads", "theme_oct", "thirds"],
    "crypt": ["heart", "none", "sparse", "pedal", "bells", "none", "none"],
    "finale": ["drive", "drive", "drive", "gallop_hi", "triads", "theme_oct", "octaves"],
}

# Harmony per block: [bar-in-block positions of chord changes], chords cyclic.
PROGS = {
    "theme": (4, [AM, GM, F_, ED]),      # i VII VI V — the descent, dagger on top
    "theme2": (4, [AM, GM, F_, ED]),
    "tower": (2, [AM, ED]),              # i V alternation, tension
    "crypt": (4, [AM, AM, EM, EM]),      # pedal sea with iv sigh
    "finale": (2, [AM, GM]),             # i VII loop, cadence at the last bar
    "procession": (4, [AM, AM, EM, EM]),
}


def harmony_at(bar: int):
    blk = block_of(bar)
    start = next(a for n, a, _b in BLOCK_BOUNDS if n == blk)
    span, prog = PROGS[blk]
    chord = prog[((bar - start) // span) % len(prog)]
    return chord, blk


# --------------------------------------------------------------- take 1-3: drums
# 16-step grids (jungle's notation): K kick, S snare, k soft kick, h hat accent,
# o open hat, . rest. Drums are committed FIRST; everything below conditions on
# where these grids put their weight.

DRUM_GRIDS = {
    "heart":   "K.......K.......",          # processional heartbeat, half-note
    "stomp":   "K...k...K...k...",          # march stomp, kick on 1 and 3
    "backbeat": "....S.......S...",        # snare on 2 and 4 only
    "half":    "K.......S.......",          # half-time
    "drive":   "K...k...K.k.k...",         # the engines-on pattern
    "eighths": "h.h.h.h.h.hoh.h.",        # straight 8ths, open on the 'and' of 4
    "drive_h": "hhhhhhhhhhhohhhh",        # 16ths, pedal to the floor
    "sparse":  "h.......h.......",
}

# weight profile: which grid slots are STRONG claims (pitched layers yield to these)
def grid_weights(grid: str) -> list[float]:
    out = []
    for s, ch in enumerate(grid):
        if ch in "KSo":
            out.append(1.0)
        elif ch in "kh":
            out.append(0.55)
        else:
            out.append(0.0)
    return out


# --------------------------------------------------------------- take 4: bass
# Bass rhythms claim their own weight; the LEAD has to leave them alone on
# joint strong beats (the punch rule). Each pattern is (grid, register).
# 0 = root, 7 = fifth, 12 = octave: the root-position grammar of castle bass.
BASS_ROLES = {
    "gallop":   ("K.K.K.K.K.K.K.K.", 0),      # 16th gallop like the ride out
    "gallop_hi": ("K.K.K.K.K.K.K.K.", 12),
    "walk":     ("K...K...K...K...", 0),      # quarter walk for the tower
    "pedal":    ("K...............", 0),
}


# --------------------------------------------------------------- take 5: comp
# rhythm instrument. Triads = chord on strong beats; sevenths add the 7th;
# bells = the crypt's two bell voices; pedal_organ = a held root+fifth.
COMP_ROLES = {"triads", "sevenths", "bells", "pedal_organ"}


# --------------------------------------------------------------- takes 6-7: leads
# Lead roles are rhythm masks over the harmony. Notes are CHOSEN per onset by
# metric function: strong claimed beat -> chord tone; off-beat -> stepwise
# scale tone between the neighbors; the LAST onset of a block -> cadence
# (leading tone up to the tonic, or root). Rests are real (mask keeps them).
LEAD_ROLES = {
    "theme":     "x.x..x..x.x.x...",       # the call: syncopated, breathes at 4
    "theme_oct": "x.x..x..x.x.x...",
    "sequence":  "x..xx..xx..xx..x",       # fragmentation for the tower
    "foreshadow": "x.....x.........",      # three bare calls in the dark
    "none":      "................",
}
COUNTER_ROLES = {
    "rests":    "................",
    "thirds":   "x...x...x...x...",   # long thirds below the call
    "octaves":  "x..x..x.x..x..x.",   # unison punches in the finale
}

# A harmonic minor, ascending from the tonic A4 (the lead's center of gravity).
A_HARM_MIN = [69, 71, 72, 74, 76, 77, 80, 81]   # A B C D E F G# A
CHORD_TONE_PCS = {
    0: None,  # filled per chord below
}


def chord_tone_pcs(chord) -> set[int]:
    return {n % 12 for n in chord[0]}


def note_for_slot(chord, scale: list[int], slot: int, claim: float,
                  bass_note: int | None, prev: int, chooser=None) -> int:
    """Choose a note for a non-entry, non-cadence lead onset.

    Strong claims use nearby chord tones; weak claims move by one scale step.
    """
    pcs = chord_tone_pcs(chord)
    root_pc = chord[1] % 12
    if claim >= 0.55:  # the beat is claimed by a committed take
        cands = [n for n in scale if n % 12 in pcs and abs(n - prev) <= 7]
        if not cands:
            cands = [n for n in scale if abs(n - prev) <= 5]
        ranked = sorted(cands, key=lambda n: (abs(n - prev), n))[:3]
        return chooser.pick(ranked) if chooser and len(ranked) > 1 else min(
            ranked, key=lambda n: (abs(n - prev), n))
    # Unclaimed slots move by one scale step; the seed chooses direction.
    neighbors = [n for n in scale if 0 < abs(n - prev) <= 2]
    if not neighbors:
        return prev
    return chooser.pick(neighbors) if chooser else min(
        neighbors, key=lambda n: (abs(n - prev), n))


def nearby_chord_tone(chord, scale: list[int], previous: int, chooser=None) -> int:
    """Choose a nearby chord tone for a phrase entry or cadence."""
    pcs = chord_tone_pcs(chord)
    candidates = sorted({note for note in scale
                         if note % 12 in pcs and 64 <= note <= 83})
    if not candidates:
        candidates = sorted({note + 12 * octave for note in chord[0]
                             for octave in range(-3, 5)
                             if 64 <= note + 12 * octave <= 83})
    if not candidates:
        raise ValueError("chord has no note in the lead register")

    nearby = [note for note in candidates if abs(note - previous) <= 7]
    ranked = sorted(nearby or candidates,
                    key=lambda note: (abs(note - previous), note))[:3]
    return chooser.pick(ranked) if chooser and len(ranked) > 1 else ranked[0]


def check_rules(events: list[dict]) -> list[str]:
    """The static checks: legality of every placed note, printed at build."""
    problems = []
    for ev in events:
        if ev["func"] == "none":
            continue
        if ev["func"] == "chord" and ev["pc"] not in ev["pcs"]:
            problems.append(f"bar{ev['bar']} slot{ev['slot']}: strong beat, non-chord tone")
        if ev["func"] == "step":
            if ev["pc"] not in ev["scale_pcs"]:
                problems.append(f"bar{ev['bar']} slot{ev['slot']}: off-scale passing note")
        if ev["func"] == "cadence" and ev["pc"] not in ev["pcs"]:
            problems.append(f"bar{ev['bar']} slot{ev['slot']}: cadence note is outside the current chord")
    return problems


# --------------------------------------------------------------- the session

class _Lcg:
    """The seed's ONLY power: choosing among already-legal options."""
    __slots__ = ("s",)

    def __init__(self, seed: int) -> None:
        self.s = (seed * 2654435761) & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s >> 8

    def pick(self, options):
        """pick(n) = index choice; pick([...]) = element choice. Both legal-only."""
        if isinstance(options, int):
            return self.next() % max(1, options)
        seq = list(options)
        return seq[self.next() % len(seq)] if seq else 0


# The legal-choice libraries the seed re-deals from. Nothing here is optional:
# every entry is a role/pattern the grammar knows how to voice.
KICK_LIB = ["stomp", "drive", "half", "heart"]
SNARE_LIB = ["backbeat", "drive", "half", "none"]
HAT_LIB = ["eighths", "drive_h", "sparse"]
BASS_LIB = ["gallop", "walk", "pedal"]
COMP_LIB = ["triads", "sevenths", "pedal_organ", "bells"]
LEAD_LIB = ["theme", "sequence", "foreshadow", "none"]
COUNTER_LIB = ["rests", "thirds", "octaves"]
PROG_LIB = {
    "minor_descent": [AM, GM, F_, ED],       # i VII VI V
    "pedal_iv": [AM, AM, F_, F_],            # i i IV IV (sighing loop)
    "dagger": [AM, ED, AM, ED],              # i V i V (tension)
    "aeolian": [AM, F_, GM, AM],             # i VI VII i
    "subdominant_walk": [F_, GM, ED, AM],    # VI VII V i (the climb home)
}
BLOCK_LENS = {"theme": 16, "tower": 8, "theme2": 16, "crypt": 10, "finale": 12, "procession": 4}


def deal_arrangement(rng: _Lcg) -> dict:
    """The seed's real job: re-deal the arrangement matrix, legally.

    Rules the deal must obey (legality of FORM, not just notes):
    - the walk is bounded to 66 bars total and the canonical block set
    - crypt never first among the body blocks; finale is always last
    - the lead must state the theme somewhere before the crypt reprise
    - every layer cell comes from its library, so every combo is playable
    Returns {bounds, matrix, progs} in exactly the shapes main() consumes.
    """
    body_names = ["theme", "tower", "theme2", "crypt"]
    order = ["procession"]
    rng_order = list(body_names)
    # Fisher-Yates re-deals the body sequence while keeping the opening and
    # finale fixed. Crypt stays out of the first body position.
    for i in range(len(rng_order) - 1, 0, -1):
        j = rng.pick(i + 1)
        rng_order[i], rng_order[j] = rng_order[j], rng_order[i]
    if rng_order[0] == "crypt":
        rng_order[0], rng_order[1] = rng_order[1], rng_order[0]
    order += rng_order
    order.append("finale")

    # bar allocation: canonical lens, theme2 shortened to 12 if the walk runs long
    total = sum(BLOCK_LENS[n] for n in order)
    if total > 66:
        over = total - 66
        if "theme2" in order:
            BLOCK_LENS_ADJ = BLOCK_LENS.copy()
            BLOCK_LENS_ADJ["theme2"] = max(8, 16 - over)
            lens = {n: BLOCK_LENS_ADJ[n] for n in order}
        else:
            lens = {n: BLOCK_LENS[n] for n in order}
    else:
        lens = {n: BLOCK_LENS[n] for n in order}
        # give the surplus to the finale (bigger ending)
        lens[order[-1]] += 66 - sum(lens.values())

    bounds = []
    t = 0
    for name in order:
        bounds.append((name, t, t + lens[name]))
        t += lens[name]

    matrix = {}
    progs = {}
    body = [n for n in order if n not in ("procession", "crypt", "finale")]
    # the theme must be stated in at least 2 body blocks: pin the lead there,
    # then deal the rest of the lead cells freely
    if len(body) > 2:
        first = rng.pick(body)
        second = rng.pick([b for b in body if b != first])
        pinned = [first, second]
    else:
        pinned = list(body)
    for name, _a, _b in bounds:
        crypt = name == "crypt"
        proc = name == "procession"
        fin = name == "finale" and name == order[-1]
        matrix[name] = [
            rng.pick([r for r in KICK_LIB if r != "heart"] if not crypt else ["heart"]),
            "none" if crypt else ("half" if proc else rng.pick(SNARE_LIB)),
            "sparse" if crypt else rng.pick(HAT_LIB),
            "pedal" if crypt else ("gallop" if fin else rng.pick(BASS_LIB)),
            "bells" if crypt else ("pedal_organ" if proc else rng.pick(COMP_LIB)),
            "theme" if (not crypt and not proc and name in pinned) else (
                "none" if crypt else ("foreshadow" if proc else rng.pick(LEAD_LIB))),
            "none" if crypt or proc else rng.pick(COUNTER_LIB),
        ]
        # harmony: a legal rotation of one of the progressions (start point only)
        prog_name = rng.pick(list(PROG_LIB))
        base = PROG_LIB[prog_name]
        rot = rng.pick(len(base))
        progs[name] = (4 if len(base) > 2 else 2, base[rot:] + base[:rot])
    return {"bounds": bounds, "matrix": matrix, "progs": progs,
            "order": order}


def deal_lead_rhythms(
    bounds: list[tuple[str, int, int]],
    matrix: dict[str, list[str]],
    seed: int,
) -> dict[tuple[str, int], str]:
    """Deal two-bar lead rhythms with local variation and anchored phrase ends."""
    masks: dict[tuple[str, int], str] = {}
    previous: dict[str, str] = {}
    for name, start, end in bounds:
        base = LEAD_ROLES[matrix[name][5]]
        for phrase_start in range(start, end, 2):
            phrase_index = (phrase_start - start) // 2
            phrase_seed = seed ^ (phrase_start * 7919) ^ (phrase_index * 104729)
            phrase_rng = random.Random(phrase_seed)
            mask = vary_phrase_mask(base, phrase_rng, previous.get(name))
            previous[name] = mask
            for bar in range(phrase_start, min(phrase_start + 2, end)):
                masks[(name, bar)] = mask
    return masks


def main(render_audio: bool = True, verify_variation: bool = True,
         argv: list[str] | None = None) -> list[dict]:
    # No user seed: every layer rolls its own entropy. The console logs the
    # seven layer seeds so any individual take can be reproduced on purpose.
    import os as _os
    args = sys.argv[1:] if argv is None else list(argv)
    if args and args[0] != "--repro":
        layer_seed_input = int(args[0])
        rng_master = _Lcg(layer_seed_input)
        layer_seeds = [rng_master.pick(1 << 30) for _ in range(7)]
    elif "--repro" in args:
        # --repro <comma list>: exact layer seeds, for reproducing one take
        raw = next(a for a in args if a.startswith("--repro"))
        if len(args) > args.index(raw) + 1 and "," in args[args.index(raw) + 1]:
            layer_seeds = [int(x) for x in args[args.index(raw) + 1].split(",")]
        else:
            layer_seeds = [int(x) for x in raw.split("=", 1)[1].split(",")] if "=" in raw else [0]
        while len(layer_seeds) < 7:
            layer_seeds.append(0)
    else:
        layer_seeds = [int.from_bytes(_os.urandom(4), "little") for _ in range(7)]
    names = ["arrangement", "kick", "snare", "hats", "bass", "comp", "lead"]
    rng = {
        "arrangement": _Lcg(layer_seeds[0]),  # the walk + matrix + progs
        "kick": _Lcg(layer_seeds[1]), "snare": _Lcg(layer_seeds[2]),
        "hats": _Lcg(layer_seeds[3]), "bass": _Lcg(layer_seeds[4]),
        "comp": _Lcg(layer_seeds[5]), "lead": _Lcg(layer_seeds[6]),
    }
    print("layer seeds:", {n: layer_seeds[i] for i, n in enumerate(names)})
    global_deal = deal_arrangement(rng["arrangement"])
    BLOCK_BOUNDS = global_deal["bounds"]
    MATRIX = global_deal["matrix"]
    lead_rhythms = deal_lead_rhythms(BLOCK_BOUNDS, MATRIX, layer_seeds[6])
    phrase_starts = [(name, bar) for name, start, end in BLOCK_BOUNDS
                     for bar in range(start, end, 2)]
    active_phrases = [
        (name, bar) for name, bar in phrase_starts
        if "x" in LEAD_ROLES[MATRIX[name][5]]
    ]
    changed_phrases = sum(
        lead_rhythms[(name, bar)] != LEAD_ROLES[MATRIX[name][5]]
        for name, bar in active_phrases
    )
    print(f"lead rhythm: {changed_phrases}/{len(active_phrases)} active two-bar phrases varied")
    if active_phrases and changed_phrases != len(active_phrases):
        raise RuntimeError("an active lead phrase did not receive a rhythm variation")

    def block_of(bar: int) -> str:
        for name, a, b in BLOCK_BOUNDS:
            if a <= bar < b:
                return name
        return "finale"

    def harmony_at(bar: int):
        blk = block_of(bar)
        start = next(a for n, a, _b in BLOCK_BOUNDS if n == blk)
        span, prog = global_deal["progs"][blk]
        # allow 2-bar spans when the prog is 2 chords; 4-bar otherwise
        chord = prog[((bar - start) // span) % len(prog)]
        return chord, blk

    L = [0.0] * N if render_audio else []
    R = [0.0] * N if render_audio else []
    mix_at = add_at if render_audio else (lambda *_args, **_kwargs: None)
    kick = render_kick(0.14, 0.5)
    kick_soft = render_kick(0.10, 0.2)
    snare = render_snare(0.14, 188.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_l = render_tom(103.0)
    crash = render_crash(1.8)
    bell_hi = render_bell(midi_hz(76), 2.8)   # E5
    bell_lo = render_bell(midi_hz(69), 3.0)   # A4

    # ---- takes 1-3: the drum bed, committed first ------------------------
    # claims[bar][slot] = the strongest weight any drum grid put on that 16th.
    claims = [[0.0] * 16 for _ in range(BARS)]
    for bar in range(BARS):
        blk = block_of(bar)
        roles = MATRIX[blk]
        t0 = bar * BAR
        for layer, role_idx, lrng in ((0, 0, rng["kick"]), (1, 1, rng["snare"]), (2, 2, rng["hats"])):
            role = roles[role_idx]
            if role == "none":
                continue
            grid = DRUM_GRIDS[role]
            w = grid_weights(grid)
            for s, ch in enumerate(grid):
                st = int((t0 + s * SIX) * SR)
                if ch == "K":
                    g = 0.95 if role != "drive" else 0.85
                    mix_at(L, st, kick, g); mix_at(R, st, kick, g)
                elif ch == "k":
                    mix_at(L, st, kick_soft, 0.55); mix_at(R, st, kick_soft, 0.55)
                elif ch == "S":
                    mix_at(L, st, snare, 0.85); mix_at(R, st, snare, 0.9)
                elif ch == "h":
                    pass  # hat grid handled below by layer 3 gains
                claims[bar][s] = max(claims[bar][s], w[s])
        # hats layer with its own pattern + fills
        hat_role = roles[2]
        if hat_role != "none":
            hgrid = DRUM_GRIDS[hat_role]
            for s, ch in enumerate(hgrid):
                st = int((t0 + s * SIX) * SR)
                if ch == "h":
                    mix_at(L, st, hat_c, 0.2); mix_at(R, st, hat_c, 0.24)
                elif ch == "o":
                    mix_at(L, st, hat_o, 0.26); mix_at(R, st, hat_o, 0.3)
        # tom pick-up into every block boundary (the player's fill)
        nxt = bar + 1
        if nxt < BARS and block_of(nxt) != blk:
            mix_at(L, int((t0 + 14 * SIX) * SR), tom_l, 0.55)
            mix_at(R, int((t0 + 14 * SIX) * SR), tom_l, 0.55)
            mix_at(L, int((t0 + 15 * SIX) * SR), snare, 0.6)
            mix_at(R, int((t0 + 15 * SIX) * SR), snare, 0.6)

    for blk, _a, _b in BLOCK_BOUNDS:
        start = next(a for n, a, _b in BLOCK_BOUNDS if n == blk)
        mix_at(L, int(start * BAR * SR), crash, 0.5)
        mix_at(R, int(start * BAR * SR), crash, 0.5)
    mix_at(L, 0, bell_hi, 0.4)
    mix_at(R, 0, bell_lo, 0.35)

    # ---- take 4: bass, conditioned on the drum claims --------------------
    # Bass commits to roots on the drum's claimed beats; its onsets avoid the
    # kick's exact slots EXCEPT the downbeat (punch), and its register sits
    # under the harmony. Its own onsets then join the claims for the lead.
    bass_events: list[dict] = []
    bass_ph = 0.0
    bass_sub = 0.0
    bass_claims = [[0.0] * 16 for _ in range(BARS)]
    for bar in range(BARS):
        blk = block_of(bar)
        role = MATRIX[blk][3]
        if role == "none":
            continue
        grid, reg = BASS_ROLES[role]
        _chord, _ = harmony_at(bar)
        root = _chord[1]
        t0 = bar * BAR
        for s, ch in enumerate(grid):
            if ch != "K":
                continue
            # punch rule: skip a slot that a KICK also owns, except the downbeat
            if s != 0 and claims[bar][s] >= 1.0:
                continue
            st = int((t0 + s * SIX) * SR)
            note = root + reg + (12 if s % 4 == 2 else 0)
            bass_events.append({"bar": bar, "slot": s, "note": note, "func": "root",
                                "start": st})
            bass_claims[bar][s] = 1.0

    # Bass events are held until every note layer is composed, then swapped
    # and rendered together in the final accompaniment pass.

    # ---- take 5: comp (the rhythm instrument), reads drums+bass ----------
    comp_events: list[dict] = []
    for bar in range(BARS):
        blk = block_of(bar)
        role = MATRIX[blk][4]
        if role == "none":
            continue
        chord, _ = harmony_at(bar)
        t0 = bar * BAR
        if role == "bells":
            # Preserve the alternating crypt bell pattern as movable events.
            slot = 0 if bar % 2 == 0 else 8
            left_sample, right_sample = ((bell_hi, bell_lo) if bar % 2 == 0
                                         else (bell_lo, bell_hi))
            left_gain, right_gain = ((0.4, 0.3) if bar % 2 == 0
                                     else (0.35, 0.28))
            comp_events.append({"bar": bar, "slot": slot,
                                "start": int((t0 + slot * SIX) * SR),
                                "kind": "bells", "left_sample": left_sample,
                                "right_sample": right_sample,
                                "left_gain": left_gain, "right_gain": right_gain,
                                "swap_class": "bells"})
            continue
        # triads / sevenths / pedal_organ: stabs where the BACKBEAT owns the slot
        # (drum role "none" = the comp articulates on quarters instead)
        snare_role = MATRIX[blk][1]
        if snare_role == "none":
            stab_slots = [0, 8]
        else:
            stab_slots = [s for s in range(16) if DRUM_GRIDS[snare_role][s] == "S"]
        if role == "pedal_organ":
            stab_slots = [0]
        if role == "sevenths":
            # add the 7th above the root (A->G over Am: the tower's color)
            chord = (chord[0] + ((chord[1] - 2) % 12,), chord[1], chord[2])
        for slot in stab_slots:
            notes = chord[0] + (((chord[1] - 2) % 12 + 60,) if role == "sevenths" else ())
            comp_events.append({"bar": bar, "slot": slot,
                                "start": int((t0 + slot * SIX) * SR),
                                "kind": "organ", "notes": notes,
                                "dur_six": SIX * 2 if role == "pedal_organ" else SIX,
                                "swap_class": role})


    # ---- take 6: THE LEAD, reads everything committed so far -------------
    # Choose each two-bar onset mask first, then assign notes against current
    # drum/bass claims. Strong slots get chord tones; weak slots get steps.
    # Phrase entry/ending hits remain anchored; the block finale resolves home.
    lead_events: list[dict] = []
    prev = 69  # the voice's initial center
    for bar in range(BARS):
        blk = block_of(bar)
        role = MATRIX[blk][5]
        mask = lead_rhythms[(blk, bar)]
        chord, _ = harmony_at(bar)
        block_last_bar = next(b for n, _a, b in BLOCK_BOUNDS if n == blk) - 1
        scale = [n + (12 if n < 67 else 0) for n in A_HARM_MIN]  # center the window
        block_first_bar = next(a for n, a, _b in BLOCK_BOUNDS if n == blk)
        first_slot = next((i for i, symbol in enumerate(mask) if symbol == "x"), None)
        for s, ch in enumerate(mask):
            if ch != "x":
                continue
            is_last_of_block = bar == block_last_bar and s == max(
                i for i, c in enumerate(mask) if c == "x")
            claim = max(claims[bar][s], bass_claims[bar][s])
            is_block_entry = bar == block_first_bar and s == first_slot
            if is_last_of_block:
                # CADENCE: close on a current chord tone, near the voice when possible.
                note = nearby_chord_tone(chord, scale, prev, rng["lead"])
                func = "cadence"
            elif is_block_entry:
                # Make the entry itself chord-legal and connected to the prior phrase.
                note = nearby_chord_tone(chord, scale, prev, rng["lead"])
                func = "chord"
            else:
                note = note_for_slot(chord, scale, s, claim, None, prev, rng["lead"])
                func = "chord" if claim >= 0.55 else "step"
            lead_events.append({"bar": bar, "slot": s, "note": note, "func": func,
                                "pcs": chord_tone_pcs(chord),
                                "pc": note % 12,
                                "scale_pcs": {n % 12 for n in scale},
                                "swap_class": func,
                                "start": int((bar * BAR + s * SIX) * SR)})
            prev = note
    # register fold, then render through the pulse voice with the dotted echo
    for ev in lead_events:
        while ev["note"] > 83:
            ev["note"] -= 12
        while ev["note"] < 64:
            ev["note"] += 12
    # Lead events are fully composed; render after the counter has been derived.


    # ---- take 7: the counter voice, reads the lead take ------------------
    # thirds track the call a third below (legal: chord tones of the same
    # chord); octaves punch WITH the lead (unison weight in the finale).
    ctr_events: list[dict] = []
    for bar in range(BARS):
        blk = block_of(bar)
        role = MATRIX[blk][6]
        if role == "none":
            continue
        cgrid = COUNTER_ROLES[role]
        call = [ev for ev in lead_events if ev["bar"] == bar]
        for ev in call:
            s = ev["slot"]
            if s >= 16 or cgrid[s] != "x":
                continue
            if role == "thirds":
                # a diatonic third below the call note
                lower = [n for n in A_HARM_MIN if 0 < ev["note"] - 12 - n <= 7]
                note = (lower[-1] if lower else ev["note"] - 5) - 12
            else:  # octaves: with the lead, down two octaves for weight
                note = ev["note"] - 24
            ctr_events.append({"bar": bar, "slot": s, "note": max(33, note),
                               "swap_class": role,
                               "start": ev["start"]})
    # Counter events remain tied to the selected lead onsets and pitches.


    # ---- final event pass: exchange only accompaniment notes -------------
    # The lead rhythm is already chosen phrase-by-phrase before notes are
    # composed; the counter is derived from those pitches and onsets. Keep
    # both intact here so their harmonic and rhythmic relationship survives.
    timing_rng = random.Random(layer_seeds[3] ^ 0x5E5A7)
    moved = {
        "bass": swap_event_onsets(
            bass_events, timing_rng, bar_seconds=BAR,
            sixteenth_seconds=SIX, sample_rate=SR),
        "comp": swap_event_onsets(
            comp_events, timing_rng, bar_seconds=BAR,
            sixteenth_seconds=SIX, sample_rate=SR),
    }
    print("accompaniment time-swap pass:", moved)

    problems = check_rules(lead_events)
    total = len(lead_events)
    funcs = {}
    for ev in lead_events:
        funcs[ev["func"]] = funcs.get(ev["func"], 0) + 1
    print(f"lead notes: {total}  functions: {funcs}")
    if problems:
        print("RULE VIOLATIONS:")
        for p in problems[:10]:
            print(" ", p)
    else:
        print("rule checks: chord/step/cadence legality — PASS")

    if verify_variation:
        if not args:
            peer_args = []
        elif args[0] != "--repro":
            peer_args = [str(int(args[0]) + 1)]
        else:
            peer_seeds = [seed ^ 0x5E5A7 for seed in layer_seeds[:7]]
            peer_args = ["--repro", ",".join(map(str, peer_seeds))]
        peer_events = main(render_audio=False, verify_variation=False,
                           argv=peer_args)
        metrics = variation_metrics(lead_events, peer_events)
        print("two-take variation:",
              ", ".join(f"{name}={value:.1%}" for name, value in metrics.items()))
        if metrics["contour"] < 0.90:
            raise SystemExit(
                f"variation gate FAIL: contour variation {metrics['contour']:.1%} < 90%")
        print("variation gate PASS: contour variation >= 90%")

    if not render_audio:
        return lead_events

    # Bass render
    for ev in sorted(bass_events, key=lambda event: event["start"]):
        dur_six = SIX
        for i_off in range(int(dur_six * SR)):
            idx = ev["start"] + i_off
            if idx >= N:
                break
            hz = midi_hz(ev["note"])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass_sub = (bass_sub + hz * 0.5 / SR) % 1.0
            eth = i_off / SR
            benv = env_adsr(eth, dur_six, 0.004, 0.03, 0.7, 0.03)
            tone = tri(bass_ph) * 0.6 + sine(bass_sub) * 0.5 + square_bl(bass_ph) * 0.18
            L[idx] += tone * benv * 0.6
            R[idx] += tone * benv * 0.6

    # Comp render
    comp_voice_count = max((len(event.get("notes", ())) for event in comp_events),
                           default=0)
    comp_ph = [[0.0, 0.0] for _ in range(comp_voice_count)]
    for ev in sorted(comp_events, key=lambda event: event["start"]):
        st = ev["start"]
        if ev["kind"] == "bells":
            mix_at(L, st, ev["left_sample"], ev["left_gain"])
            mix_at(R, st, ev["right_sample"], ev["right_gain"])
            continue
        dur_six = ev["dur_six"]
        notes = ev["notes"]
        for vi, nmidi in enumerate(notes):
            hz = midi_hz(nmidi + 12)
            for i_off in range(int(dur_six * SR)):
                idx = st + i_off
                if idx >= N:
                    break
                organ_ph = comp_ph[vi]
                organ_ph[0] = (organ_ph[0] + hz / SR) % 1.0
                organ_ph[1] = (organ_ph[1] + hz * 2 / SR) % 1.0
                eth = i_off / SR
                cenv = env_adsr(eth, dur_six, 0.006, 0.05, 0.7, 0.06)
                tone = (organ(organ_ph[0]) + organ(organ_ph[1]) * 0.3) / 3.0
                pan = 0.85 if vi == 0 else (0.6 if vi == len(notes) - 1 else 1.0)
                L[idx] += tone * cenv * 0.3 * pan
                R[idx] += tone * cenv * 0.3 * (1.9 - pan)

    # Lead render, including its dotted echo
    lead_ph = 0.0
    lead_lp = 0.0
    delay_n = max(1, int(EIGHTH * 1.5 * SR))
    delay_buf = [0.0] * delay_n
    di = 0
    for ev in sorted(lead_events, key=lambda event: event["start"]):
        dur_six = SIX * 0.95
        for i_off in range(int(dur_six * SR)):
            idx = ev["start"] + i_off
            if idx >= N:
                break
            hz = midi_hz(ev["note"])
            lead_ph = (lead_ph + hz / SR) % 1.0
            eth = i_off / SR
            lenv = env_adsr(eth, dur_six, 0.006, 0.04, 0.75, 0.06)
            raw = pulse_bl(lead_ph) * 0.6 + square_bl(lead_ph) * 0.2 + sine(lead_ph) * 0.3
            lead_lp = one_pole(lead_lp, raw, 3400.0)
            lead = lead_lp * lenv * 0.62
            dly = delay_buf[di]
            delay_buf[di] = lead
            di = (di + 1) % delay_n
            L[idx] += lead * 0.8 + dly * 0.5
            R[idx] += lead * 0.66 + dly * 0.75

    # Counter render
    ctr_ph = 0.0
    for ev in sorted(ctr_events, key=lambda event: event["start"]):
        dur_six = SIX * 1.8
        for i_off in range(int(dur_six * SR)):
            idx = ev["start"] + i_off
            if idx >= N:
                break
            hz = midi_hz(ev["note"])
            ctr_ph = (ctr_ph + hz / SR) % 1.0
            eth = i_off / SR
            cenv = env_adsr(eth, dur_six, 0.01, 0.06, 0.6, 0.1)
            tone = (tri(ctr_ph) * 0.7 + sine(ctr_ph) * 0.4) * cenv * 0.3
            L[idx] += tone * 0.9
            R[idx] += tone * 0.55

    # ---- the bounce -------------------------------------------------------
    write_wav(track_path("16bit", "escalade_2min.mp3"), L, R, crunch=900.0)
    return lead_events


if __name__ == "__main__":
    main()