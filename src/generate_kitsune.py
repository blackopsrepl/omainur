#!/usr/bin/env python3
"""Kitsune Gate — 6/8 shrine raid, D yo-scale (D E G A B). No Western cadences."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, env_ad, env_adsr, midi_hz, pulse_bl, render_crash, render_hat,
    render_kick, render_tom, sine, tri, write_wav,
)

# 6/8, dotted-quarter = 96 → 96 bars = 2:00
BPM_DQ = 96
BARS = 96
BEAT = 60.0 / BPM_DQ  # dotted quarter
BAR = BEAT * 2
EIGHTH = BAR / 6.0
N = int(SR * BAR * BARS)

# Yo-scale pitch set (no F, no C)
YO = [50, 52, 55, 57, 59, 62, 64, 67, 69, 71, 74, 76, 79, 81, 83]

# Two-note "chords": scale fifths
FIFTHS = [
    (62, 69),  # D A
    (62, 69),
    (67, 74),  # G D
    (69, 76),  # A E
]


def harmony(bar: int):
    return FIFTHS[bar % 4]


def section_of(bar: int) -> str:
    if bar < 16:
        return "torii"
    if bar < 40:
        return "path"
    if bar < 56:
        return "mask"
    if bar < 72:
        return "gate"
    if bar < 88:
        return "path2"
    return "bow"


# 6 eighths per bar, yo only
MEL = [
    74, 76, 79, 76, 74, 71,  # D E G E D B
    69, 71, 74, 71, 69, 67,
    79, 74, 71, 74, 76, 79,
    81, 79, 76, 74, 71, 69,
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    taiko = render_kick(0.22, 0.15)
    tom = render_tom(98.0)
    hat = render_hat(True)
    crash = render_crash(2.0)

    for bar in range(BARS):
        sec = section_of(bar)
        t0 = bar * BAR
        # taiko on 1 and 4 of 6/8
        g1 = 0.55 if sec == "torii" else 0.9
        add_at(L, int(t0 * SR), taiko, g1)
        add_at(R, int(t0 * SR), taiko, g1)
        if sec not in ("torii", "bow"):
            add_at(L, int((t0 + 3 * EIGHTH) * SR), taiko, 0.7)
            add_at(R, int((t0 + 3 * EIGHTH) * SR), taiko, 0.7)
        if sec in ("mask", "gate", "path2"):
            add_at(L, int((t0 + 2 * EIGHTH) * SR), tom, 0.35)
            add_at(R, int((t0 + 5 * EIGHTH) * SR), tom, 0.4)
        if sec not in ("bow",):
            for k in range(6):
                add_at(L, int((t0 + k * EIGHTH) * SR), hat, 0.08 if k % 3 else 0.14)
                add_at(R, int((t0 + k * EIGHTH) * SR), hat, 0.1 if k % 3 else 0.12)

    add_at(L, int(16 * BAR * SR), crash, 0.35)
    add_at(R, int(16 * BAR * SR), crash, 0.35)
    add_at(L, int(56 * BAR * SR), crash, 0.4)
    add_at(R, int(56 * BAR * SR), crash, 0.4)

    koto_ph = [0.0, 0.0]
    flute_ph = 0.0
    drone_ph = 0.0
    bell_ph = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        low, high = harmony(bar)
        sec = section_of(bar)
        step = int(pos / EIGHTH) % 6
        st = pos - step * EIGHTH
        fade = 1.0
        if sec == "bow":
            fade = max(0.0, 1.0 - (bar - 88 + pos / BAR) / 8.0)

        # drone on D
        drone_ph = (drone_ph + midi_hz(38) / SR) % 1.0
        dg = 0.22 if sec in ("torii", "bow") else 0.12
        L[i] += sine(drone_ph) * dg * fade
        R[i] += sine(drone_ph) * dg * fade

        # koto: two open strings, sharp pluck each eighth
        for vi, nmidi in enumerate((low, high)):
            hz = midi_hz(nmidi)
            koto_ph[vi] = (koto_ph[vi] + hz / SR) % 1.0
        ken = env_ad(st, 0.002, 0.16)
        koto = (
            sine(koto_ph[0]) * 0.55
            + sine(koto_ph[1]) * 0.4
            + pulse_bl(koto_ph[0]) * 0.12
        ) * ken
        kg = 0.28 if sec == "torii" else 0.4
        L[i] += koto * kg * fade * 0.75
        R[i] += koto * kg * fade

        # yokobue / flute lead
        if sec in ("path", "mask", "gate", "path2"):
            nmidi = MEL[(bar % 4) * 6 + step]
            if sec == "gate":
                nmidi += 12
            hz = midi_hz(nmidi)
            flute_ph = (flute_ph + hz / SR) % 1.0
            # light vibrato in cents via FM of phase? use amplitude vibrato only
            lenv = env_adsr(st, EIGHTH * 0.95, 0.02, 0.05, 0.7, 0.08)
            vib = 1.0 + 0.04 * sine(t * 5.0)
            fl = (sine(flute_ph) * 0.7 + sine(flute_ph * 2) * 0.12) * lenv * vib
            L[i] += fl * 0.55 * fade
            R[i] += fl * 0.7 * fade

        if step == 0 and sec in ("mask", "gate"):
            hz = midi_hz(high + 12)
            bell_ph = (bell_ph + hz / SR) % 1.0
            ben = env_ad(pos, 0.002, 0.8)
            L[i] += sine(bell_ph) * ben * 0.08 * fade
            R[i] += sine(bell_ph) * ben * 0.1 * fade

    write_wav(track_path("experiments", "kitsune_gate_2min.mp3"), L, R, crunch=0.0)


if __name__ == "__main__":
    main()
