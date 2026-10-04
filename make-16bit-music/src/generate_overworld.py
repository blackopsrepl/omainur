#!/usr/bin/env python3
"""SNES RPG overworld — Uematsu walking-the-map energy, C major."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, env_ad, env_adsr, flute, midi_hz, one_pole, organ,
    render_crash, render_hat, render_kick, render_snare, sine, tri, write_wav,
)

BPM = 120
BARS = 64  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
N = int(SR * BAR * BARS)

# C | Am | F | G  — the overworld loop
PROG = [
    ((60, 64, 67), 36),  # C
    ((57, 60, 64), 33),  # Am
    ((53, 57, 60), 29),  # F
    ((55, 59, 62), 31),  # G
]

# 8ths, chord tones / pentatonic-safe
MEL_A = [
    64, 67, 72, 74, 76, 74, 72, 67,  # E G C D E D C G
    69, 72, 76, 74, 72, 71, 69, 64,  # A C E D C B A E  (B = 9th of Am)
    65, 69, 72, 74, 72, 69, 65, 69,  # F A C D C A F A
    67, 71, 74, 76, 74, 71, 67, 62,  # G B D E D B G D
]
# B is 2nd/9th of Am — fine. G chord B is 3rd.

MEL_B = [
    76, 74, 72, 71, 69, 67, 69, 71,  # over C: E D C B A G A B
    72, 76, 79, 76, 74, 72, 69, 67,  # Am: C E G E D C A G
    65, 67, 69, 72, 74, 72, 69, 65,  # F
    67, 71, 74, 79, 76, 74, 71, 67,  # G
]


def section_of(bar: int) -> str:
    if bar < 4:
        return "intro"
    if bar < 20:
        return "a"
    if bar < 36:
        return "b"
    if bar < 52:
        return "a2"
    return "coda"


def harmony(bar: int):
    return PROG[bar % 4]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.14, 0.25)
    snare = render_snare(0.14, 220.0)
    hat = render_hat(True)
    crash = render_crash(2.2)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec != "intro":
            kg = 0.55 if b in (0, 2) else 0.0
            if kg:
                add_at(L, start, kick, kg)
                add_at(R, start, kick, kg)
            if b in (1, 3):
                add_at(L, start, snare, 0.38)
                add_at(R, start, snare, 0.42)
            add_at(L, start, hat, 0.16)
            add_at(R, start, hat, 0.2)
            add_at(L, int((t + EIGHTH) * SR), hat, 0.12)
            add_at(R, int((t + EIGHTH) * SR), hat, 0.1)

    for bar, g in ((0, 0.25), (4, 0.35), (20, 0.3), (36, 0.4), (52, 0.28)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    pad_ph = [[0.0, 0.0] for _ in range(3)]
    pad_lp_l = 0.0
    pad_lp_r = 0.0
    harp_ph = 0.0
    bass_ph = 0.0
    lead_ph = 0.0
    harm_ph = 0.0
    bell_ph = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH
        fade = 1.0
        if sec == "coda":
            fade = max(0.15, 1.0 - (bar - 52 + pos / BAR) / 12.0)

        # warm string pad
        pad_l = pad_r = 0.0
        for vi, nmidi in enumerate(chord):
            hz = midi_hz(nmidi)
            pad_ph[vi][0] = (pad_ph[vi][0] + hz / SR) % 1.0
            pad_ph[vi][1] = (pad_ph[vi][1] + hz * 1.002 / SR) % 1.0
            s = organ(pad_ph[vi][0]) * 0.5 + sine(pad_ph[vi][1]) * 0.5
            if vi == 0:
                pad_l += s
            elif vi == 2:
                pad_r += s
            else:
                pad_l += s * 0.7
                pad_r += s * 0.7
        pad_l /= 2.4
        pad_r /= 2.4
        pad_cut = 900.0 if sec == "intro" else 1400.0
        pad_lp_l = one_pole(pad_lp_l, pad_l, pad_cut)
        pad_lp_r = one_pole(pad_lp_r, pad_r, pad_cut)
        pg = 0.28 * fade
        L[i] += pad_lp_l * pg
        R[i] += pad_lp_r * pg

        # harp arp 16ths: 1 3 5 8
        if sec != "intro" or bar >= 2:
            step = int(pos / (EIGHTH * 0.5)) % 4
            arp_notes = (chord[0], chord[1], chord[2], chord[0] + 12)
            hz = midi_hz(arp_notes[step] + 12)
            harp_ph = (harp_ph + hz / SR) % 1.0
            st = pos - int(pos / (EIGHTH * 0.5)) * (EIGHTH * 0.5)
            aenv = env_ad(st, 0.003, 0.12)
            harp = sine(harp_ph) * aenv * 0.16 * fade
            L[i] += harp * (0.7 if step % 2 == 0 else 1.0)
            R[i] += harp * (1.0 if step % 2 == 0 else 0.65)

        # pizz bass
        if sec != "intro":
            hz = midi_hz(root)
            bass_ph = (bass_ph + hz / SR) % 1.0
            if eighth % 2 == 0:
                benv = env_ad(eth, 0.004, 0.28)
            else:
                benv = env_ad(eth, 0.004, 0.14) * 0.45
            bass = tri(bass_ph) * benv * 0.42 * fade
            L[i] += bass
            R[i] += bass

        # flute lead
        if sec in ("a", "a2", "b", "coda"):
            mel = MEL_B if sec == "b" else MEL_A
            nmidi = mel[(bar % 4) * 8 + eighth]
            hz = midi_hz(nmidi)
            lead_ph = (lead_ph + hz / SR) % 1.0
            lenv = env_adsr(eth, EIGHTH * 0.98, 0.012, 0.05, 0.7, 0.08)
            lead = flute(lead_ph) * lenv * 0.55 * fade
            L[i] += lead * 0.75
            R[i] += lead * 0.95

        # third-above harmony on reprise
        if sec == "a2":
            nmidi = chord[1] + 12
            hz = midi_hz(nmidi)
            harm_ph = (harm_ph + hz / SR) % 1.0
            henv = env_adsr(eth, EIGHTH * 0.9, 0.02, 0.06, 0.5, 0.1)
            h = sine(harm_ph) * henv * 0.18 * fade
            L[i] += h * 0.9
            R[i] += h * 0.5

        # sparkle bells on phrase starts
        if eighth == 0 and sec in ("a", "a2", "coda"):
            hz = midi_hz(chord[2] + 24)
            bell_ph = (bell_ph + hz / SR) % 1.0
            benv = env_ad(pos, 0.002, 0.6)
            bell = sine(bell_ph) * benv * 0.08 * fade
            L[i] += bell * 0.6
            R[i] += bell

    write_wav(track_path("16bit", "emerald_trail_2min.mp3"), L, R, crunch=0.0)


if __name__ == "__main__":
    main()
