#!/usr/bin/env python3
"""Last Continent — SNES final-dungeon mist. Em C G D. Choir intro, flute, half-time."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, add_at, env_ad, env_adsr, flute, midi_hz, organ, render_crash,
    render_hat, render_kick, render_snare, render_tom, sine, tri, write_wav,
)

BPM = 144
BARS = 72
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

EM = ((52, 55, 59), 40)
C_ = ((48, 52, 55), 36)
G_ = ((43, 47, 50), 31)
D_ = ((50, 54, 57), 38)  # F# only here


def harmony(bar: int):
    return (EM, C_, G_, D_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "mist"
    if bar < 16:
        return "approach"
    if bar < 32:
        return "gate"
    if bar < 40:
        return "collapse"
    if bar < 64:
        return "march"
    return "ashes"


# Lyrical holds. F# (66/78) only over D.
MEL_A = [
    71, 71, 71, 0, 67, 64, 67, 71,
    72, 72, 67, 64, 67, 0, 64, 67,
    74, 71, 67, 67, 62, 67, 71, 74,
    74, 74, 69, 66, 69, 0, 66, 69,
]
MEL_B = [
    76, 76, 71, 0, 67, 71, 76, 79,
    79, 76, 72, 67, 72, 0, 76, 72,
    79, 74, 71, 67, 71, 74, 79, 74,
    81, 74, 69, 66, 69, 74, 78, 81,
]
BASS = [0, 0, 0, 0, 12, 12, 7, 7]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.16, 0.35)
    snare = render_snare(0.14, 170.0)
    hat_c = render_hat(True)
    tom_h = render_tom(180.0)
    tom_l = render_tom(95.0)
    crash = render_crash(2.0)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "mist":
            if b == 0 and bar % 2 == 0:
                add_at(L, start, tom_l, 0.35)
                add_at(R, start, tom_l, 0.3)
            continue
        if sec == "approach":
            if b == 0:
                add_at(L, start, tom_h, 0.4)
                add_at(R, int((t + BEAT) * SR), tom_l, 0.5)
            continue
        if sec == "ashes":
            if b == 0:
                add_at(L, start, kick, 0.45)
                add_at(R, start, kick, 0.45)
            continue
        # half-time: kick 1, snare 3
        if b == 0:
            add_at(L, start, kick, 0.8)
            add_at(R, start, kick, 0.8)
        if b == 2:
            sg = 0.35 if sec == "collapse" else 0.7
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.05)
        if sec == "march" and b in (1, 3):
            add_at(L, start, hat_c, 0.14)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.16)
        if sec == "collapse" and b == 3:
            add_at(L, start, tom_h, 0.4)
            add_at(R, int((t + EIGHTH) * SR), tom_l, 0.5)

    for bar, g in ((16, 0.4), (32, 0.3), (40, 0.6)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    choir_ph = [0.0, 0.0, 0.0]
    organ_ph = [[0.0, 0.0] for _ in range(3)]
    harp_ph = 0.0
    bass_ph = bass2 = 0.0
    lead_ph = 0.0
    delay_n = max(1, int(BEAT * SR))
    delay = [0.0] * delay_n
    di = 0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "ashes":
            fade = max(0.0, 1.0 - (bar - 64 + pos / BAR) / 8.0)

        ch = 0.0
        for vi, nm in enumerate(chord):
            choir_ph[vi] = (choir_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
            ch += sine(choir_ph[vi])
        cg = 0.22 if sec in ("mist", "collapse", "ashes") else 0.1
        L[i] += ch / 3.0 * cg * fade
        R[i] += ch / 3.0 * cg * fade * 1.08

        if sec in ("mist", "approach", "collapse"):
            acc = 0.0
            for vi, nm in enumerate(chord):
                organ_ph[vi][0] = (organ_ph[vi][0] + midi_hz(nm) / SR) % 1.0
                acc += organ(organ_ph[vi][0])
            L[i] += acc / 3.0 * 0.18 * fade
            R[i] += acc / 3.0 * 0.16 * fade

        if sec != "mist":
            hz = midi_hz(root + BASS[ei])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.01, 0.06, 0.7, 0.08)
            bass = tri(bass_ph) * 0.7 + sine(bass2) * 0.55
            L[i] += bass * benv * 0.5 * fade
            R[i] += bass * benv * 0.5 * fade

        if sec in ("mist", "approach", "gate", "march"):
            step = int(pos / SIX) % 4
            nm = chord[step % 3] + 24
            harp_ph = (harp_ph + midi_hz(nm) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            henv = env_ad(st, 0.002, 0.07)
            hp = sine(harp_ph) * henv * 0.11 * fade
            L[i] += hp * (0.4 if step % 2 else 0.85)
            R[i] += hp * (0.85 if step % 2 else 0.4)

        lead = 0.0
        if sec in ("approach", "gate", "march"):
            mel = MEL_B if sec == "march" else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                attack = nmidi != prev
                lenv = env_adsr(eth, EIGHTH * 0.95, 0.02, 0.08, 0.6, 0.1) if attack else 0.6
                lead = flute(lead_ph) * lenv * 0.55 * fade
            else:
                lead_ph = (lead_ph + midi_hz(71) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.75 + dly * 0.35
        R[i] += lead * 0.85 + dly * 0.28

    write_wav(track_path("16bit", "last_continent_2min.mp3"), L, R, crunch=520.0)


if __name__ == "__main__":
    main()
