#!/usr/bin/env python3
"""Genesis boss fight — Koshiro / Thunder Force / Shinobi energy, E minor."""
from __future__ import annotations

from paths import track_path

import math

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_crash, render_hat, render_kick, render_snare, render_tom, saw_bl,
    sine, square_bl, tri, write_wav,
)

BPM = 160
BARS = 80  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# Em | Em | C | B  — i i bVI V (B major = harmonic-minor sting)
EM = ((52, 55, 59), 40, False)
C_ = ((48, 52, 55), 36, True)
B_ = ((47, 51, 54), 35, True)  # B D# F#


def harmony(bar: int):
    return (EM, EM, C_, B_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "alert"
    if bar < 20:
        return "phase1"
    if bar < 36:
        return "phase2"
    if bar < 44:
        return "break"
    if bar < 64:
        return "phase3"
    if bar < 76:
        return "final"
    return "ko"


# 8ths. D# only over B. F# is in E minor.
MEL_1 = [
    64, 67, 71, 76, 74, 71, 67, 64,  # E G B E  D B G E
    67, 69, 71, 72, 71, 67, 66, 64,  # G A B C  B G F# E
    72, 67, 64, 67, 72, 74, 72, 67,  # C G E G  C D C G
    71, 75, 78, 75, 71, 66, 63, 59,  # B D# F# D#  B F# D# B
]
MEL_2 = [
    76, 71, 67, 71, 76, 79, 76, 74,
    76, 72, 71, 67, 66, 64, 66, 67,
    72, 76, 79, 76, 74, 72, 67, 64,
    75, 78, 83, 78, 75, 71, 66, 63,
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.12, 0.7)
    snare = render_snare(0.12, 210.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(240.0)
    tom_l = render_tom(120.0)
    crash = render_crash(1.4)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "alert":
            nsub = 2 if bar < 2 else 4
            for k in range(nsub):
                st = int((t + BEAT * k / nsub) * SR)
                add_at(L, st, snare, 0.25 + 0.5 * (bar / 3.0))
                add_at(R, st, snare, 0.25 + 0.5 * (bar / 3.0))
            if b == 0:
                add_at(L, start, kick, 0.8)
                add_at(R, start, kick, 0.8)
            continue
        if sec == "ko":
            if b == 0:
                add_at(L, start, crash, 0.7)
                add_at(R, start, crash, 0.7)
                add_at(L, start, kick, 0.9)
                add_at(R, start, kick, 0.9)
            continue
        add_at(L, start, kick, 1.0 if b in (0, 2) else 0.45)
        add_at(R, start, kick, 1.0 if b in (0, 2) else 0.45)
        if sec in ("phase2", "phase3", "final") and b in (1, 3):
            add_at(L, int((t + SIX) * SR), kick, 0.4)
            add_at(R, int((t + SIX) * SR), kick, 0.4)
        if b in (1, 3):
            add_at(L, start, snare, 0.9)
            add_at(R, start, snare, 0.95)
        hg = 0.28 if sec != "break" else 0.14
        add_at(L, start, hat_c, hg * 0.8)
        add_at(R, start, hat_c, hg)
        add_at(L, int((t + EIGHTH) * SR), hat_c, hg)
        add_at(R, int((t + EIGHTH) * SR), hat_c, hg * 0.7)
        if sec in ("phase2", "final"):
            for k in (1, 3):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.16)
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.2)
        if b == 3 and sec not in ("break",):
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.3)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.34)
        if bar % 8 == 7 and b == 3:
            add_at(L, start, tom_h, 0.6)
            add_at(R, int((t + EIGHTH) * SR), tom_l, 0.7)

    for bar, g in ((4, 0.7), (20, 0.55), (36, 0.35), (44, 0.75), (64, 0.8)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = 0.0
    bass2 = 0.0
    gtr_r = 0.0
    gtr_f = 0.0
    lead_ph = 0.0
    lead2 = 0.0
    alarm_ph = 0.0
    arp_ph = 0.0
    lead_lp = 0.0
    delay_n = max(1, int(EIGHTH * SR))
    delay = [0.0] * delay_n
    di = 0

    BASS = [0, 0, 12, 0, 0, 7, 12, 0]

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root, _maj = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH
        fade = 1.0
        if sec == "ko":
            fade = max(0.0, 1.0 - (bar - 76 + pos / BAR) / 4.0)

        # FM-ish pumping bass
        if sec not in ("alert",):
            hz = midi_hz(root + BASS[eighth])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + hz * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.002, 0.03, 0.65, 0.03)
            raw = square_bl(bass_ph) * 0.45 + saw_bl(bass_ph) * 0.35 + sine(bass2) * 0.5
            bass = drive(raw, 2.8 if sec in ("phase3", "final") else 2.1)
            g = 0.55 if sec != "break" else 0.28
            L[i] += bass * benv * g * fade
            R[i] += bass * benv * g * fade

        # distorted fifths
        if sec in ("phase1", "phase2", "phase3", "final"):
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            genv = env_ad(eth, 0.002, 0.07)
            gtr = drive(saw_bl(gtr_r) + saw_bl(gtr_f), 3.8)
            gg = 0.5 if sec in ("phase3", "final") else 0.36
            L[i] += gtr * genv * gg * fade * 0.55
            R[i] += gtr * genv * gg * fade * 0.7

        # alarm in alert + break — E4 drifting to G4
        if sec in ("alert", "break"):
            hz = midi_hz(64 + 3.0 * (0.5 + 0.5 * math.sin(2 * math.pi * t / BAR)))
            alarm_ph = (alarm_ph + hz / SR) % 1.0
            al = sine(alarm_ph) * 0.14 * fade
            L[i] += al * 0.7
            R[i] += al

        # lead
        if sec in ("phase1", "phase2", "phase3", "final"):
            mel = MEL_2 if sec in ("phase2", "final") else MEL_1
            nmidi = mel[(bar % 4) * 8 + eighth]
            hz = midi_hz(nmidi + (12 if sec == "final" else 0))
            lead_ph = (lead_ph + hz / SR) % 1.0
            lead2 = (lead2 + hz * 1.0015 / SR) % 1.0
            lenv = env_adsr(eth, EIGHTH * 0.88, 0.003, 0.04, 0.6, 0.05)
            raw = pulse_bl(lead_ph) * 0.65 + square_bl(lead2) * 0.25 + sine(lead_ph) * 0.3
            lead_lp = one_pole(lead_lp, raw, 3800.0)
            lead = lead_lp * lenv * 0.7 * fade
        else:
            lead = 0.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.8 + dly * 0.22
        R[i] += lead * 0.7 + dly * 0.4

        # 16th chord arp in later phases
        if sec in ("phase3", "final"):
            step = int(pos / SIX) % 4
            nmidi = chord[step % 3] + 12
            hz = midi_hz(nmidi)
            arp_ph = (arp_ph + hz / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            aenv = env_ad(st, 0.002, 0.05)
            arp = tri(arp_ph) * aenv * 0.14 * fade
            L[i] += arp * 0.6
            R[i] += arp

    write_wav(track_path("16bit", "red_alert_2min.mp3"), L, R, crunch=640.0)


if __name__ == "__main__":
    main()
