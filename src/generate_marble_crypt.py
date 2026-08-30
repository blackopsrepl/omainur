#!/usr/bin/env python3
"""Marble Crypt — dripping dungeon. Dm Gm C F. Mallet lead, drip intro, half-time."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, Noise, add_at, env_ad, env_adsr, midi_hz, one_pole, organ,
    render_bell, render_crash, render_kick, render_snare, sine, square_bl,
    tri, write_wav,
)

BPM = 128
BARS = 64
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
N = int(SR * BAR * BARS)

DM = ((50, 53, 57), 38)
GM = ((43, 46, 50), 31)  # Bb
C_ = ((48, 52, 55), 36)
F_ = ((41, 45, 48), 29)


def harmony(bar: int):
    return (DM, GM, C_, F_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "torch"
    if bar < 20:
        return "descent"
    if bar < 36:
        return "chamber"
    if bar < 44:
        return "collapse"
    if bar < 60:
        return "ascent"
    return "seal"


# Sparse. Bb (70) only over Gm. E (64) only over C.
MEL_A = [
    69, 0, 0, 65, 62, 0, 65, 0,
    70, 0, 67, 0, 62, 67, 70, 0,
    72, 0, 0, 67, 64, 0, 67, 72,
    72, 69, 65, 0, 65, 69, 72, 0,
]
MEL_B = [
    74, 0, 69, 65, 69, 0, 0, 65,
    77, 70, 0, 67, 70, 0, 74, 70,
    76, 0, 72, 67, 64, 67, 72, 0,
    77, 72, 69, 65, 60, 0, 65, 69,
]
BASS = [0, 0, 0, 0, 0, 0, 12, 0]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.2, 0.28)
    snare = render_snare(0.16, 155.0)
    crash = render_crash(2.2)
    bell_d = render_bell(midi_hz(62), 2.4)
    bell_a = render_bell(midi_hz(69), 2.8)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "torch":
            if b == 0 and bar % 2 == 0:
                add_at(L, start, bell_d, 0.28)
                add_at(R, start, bell_a, 0.22)
            continue
        if sec == "seal":
            if b == 0:
                add_at(L, start, kick, 0.35)
                add_at(R, start, kick, 0.35)
            continue
        if sec == "collapse":
            if b in (0, 2):
                add_at(L, start, kick, 0.7)
                add_at(R, start, kick, 0.7)
            if b in (1, 3):
                add_at(L, start, snare, 0.5)
                add_at(R, start, snare, 0.55)
            continue
        # half-time crawl
        if b == 0:
            add_at(L, start, kick, 0.72)
            add_at(R, start, kick, 0.72)
        if b == 2 and sec in ("chamber", "ascent"):
            add_at(L, start, snare, 0.38)
            add_at(R, start, snare, 0.4)
        if b == 0 and bar % 4 == 0 and sec != "descent":
            add_at(L, start, bell_a, 0.18)
            add_at(R, start, bell_d, 0.14)

    add_at(L, int(20 * BAR * SR), crash, 0.28)
    add_at(R, int(20 * BAR * SR), crash, 0.28)
    add_at(L, int(44 * BAR * SR), crash, 0.4)
    add_at(R, int(44 * BAR * SR), crash, 0.4)

    organ_ph = [0.0, 0.0, 0.0]
    bass_ph = bass2 = 0.0
    lead_ph = 0.0
    drip_ph = 0.0
    air = Noise(77)
    air_lp = 0.0
    delay_n = max(1, int(BEAT * 2 * SR))
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
        if sec == "seal":
            fade = max(0.0, 1.0 - (bar - 60 + pos / BAR) / 4.0)

        acc = 0.0
        for vi, nm in enumerate(chord):
            organ_ph[vi] = (organ_ph[vi] + midi_hz(nm) / SR) % 1.0
            acc += organ(organ_ph[vi])
        og = 0.26 if sec in ("torch", "seal") else 0.12
        L[i] += acc / 3.0 * og * fade
        R[i] += acc / 3.0 * og * fade * 0.9

        if sec != "torch" or bar >= 4:
            hz = midi_hz(root + BASS[ei])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            if ei in (0, 4, 6):
                benv = env_adsr(eth, EIGHTH * 2, 0.01, 0.1, 0.55, 0.12)
                bass = tri(bass_ph) * 0.8 + sine(bass2) * 0.5
                L[i] += bass * benv * 0.52 * fade
                R[i] += bass * benv * 0.52 * fade

        # drip: high mallet on the last eighth of odd bars
        if bar % 2 == 1 and ei == 7:
            drip_ph = (drip_ph + midi_hz(81 if bar % 4 == 1 else 74) / SR) % 1.0
            denv = env_ad(eth, 0.002, 0.22)
            drip = sine(drip_ph) * denv * 0.1 * fade
            L[i] += drip * 0.4
            R[i] += drip

        lead = 0.0
        if sec in ("chamber", "ascent", "collapse"):
            mel = MEL_B if sec in ("ascent", "collapse") else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                attack = nmidi != prev
                lenv = env_ad(eth, 0.003, 0.22) if attack else env_adsr(eth, EIGHTH, 0.0, 0.05, 0.35, 0.08)
                mallet = (sine(lead_ph) * 0.65 + tri(lead_ph) * 0.25 + square_bl(lead_ph) * 0.08)
                lead = mallet * lenv * 0.58 * fade
            else:
                lead_ph = (lead_ph + midi_hz(69) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.7 + dly * 0.4
        R[i] += lead * 0.82 + dly * 0.3

        n = air.next()
        air_lp = one_pole(air_lp, n, 280.0)
        hiss = air_lp * (0.03 if sec == "torch" else 0.012)
        L[i] += hiss
        R[i] += hiss * 0.8

    write_wav(track_path("16bit", "marble_crypt_2min.mp3"), L, R, crunch=900.0)


if __name__ == "__main__":
    main()
