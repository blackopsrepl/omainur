#!/usr/bin/env python3
"""Night city beat-'em-up — Koshiro / Final Fight after-hours, A minor."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_crash, render_hat, render_kick, render_snare, saw_bl, sine,
    square_bl, tri, write_wav,
)

BPM = 130
BARS = 65  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# Am | F | G | E  — Andalusian city loop (E = harmonic-minor sting)
AM = ((57, 60, 64), 33)
F_ = ((53, 57, 60), 29)
G_ = ((55, 59, 62), 31)
E_ = ((52, 56, 59), 28)


def harmony(bar: int):
    return (AM, F_, G_, E_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "streets"
    if bar < 24:
        return "theme"
    if bar < 40:
        return "chase"
    if bar < 48:
        return "alley"
    if bar < 61:
        return "theme2"
    return "fade"


# G# (56/68) only on E. B only on G/E.
MEL_A = [
    69, 72, 76, 72, 74, 72, 69, 64,  # A C E C  D C A E
    65, 69, 72, 69, 65, 60, 65, 69,  # F A C A  F C F A
    67, 71, 74, 71, 67, 62, 67, 71,  # G B D B  G D G B
    64, 68, 71, 68, 64, 59, 64, 68,  # E G# B G#  E B E G#
]
MEL_B = [
    76, 72, 69, 72, 76, 79, 76, 74,
    72, 69, 65, 69, 72, 77, 76, 72,
    74, 71, 67, 71, 74, 79, 76, 74,
    76, 71, 68, 64, 68, 71, 76, 80,
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.14, 0.55)
    snare = render_snare(0.13, 200.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(1.6)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        kg = 0.0
        if sec == "streets":
            kg = 0.75
        elif sec == "alley":
            kg = 0.7 if b in (0, 2) else 0.0
        elif sec == "fade":
            kg = 0.5 if b == 0 else 0.25
        else:
            kg = 1.0  # 4-on-the-floor Koshiro
        if kg:
            add_at(L, start, kick, kg)
            add_at(R, start, kick, kg)
        if b in (1, 3) and sec not in ("streets",):
            sg = 0.45 if sec == "alley" else 0.78
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.05)
        if sec == "streets" and bar >= 4 and b in (1, 3):
            add_at(L, start, snare, 0.35)
            add_at(R, start, snare, 0.38)
        hg = 0.12 if sec in ("streets", "alley") else 0.26
        if sec != "fade":
            add_at(L, start, hat_c, hg * 0.8)
            add_at(R, start, hat_c, hg)
            add_at(L, int((t + EIGHTH) * SR), hat_c, hg)
            add_at(R, int((t + EIGHTH) * SR), hat_c, hg * 0.75)
        if sec in ("theme", "chase", "theme2") and b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.32)
        if sec in ("chase", "theme2"):
            for k in (1, 3):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.14)
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.18)

    for bar, g in ((8, 0.5), (24, 0.45), (40, 0.3), (48, 0.55)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    stab_ph = [0.0, 0.0, 0.0]
    stab_lp = 0.0
    lead_ph = lead2 = 0.0
    lead_lp = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    delay_n = max(1, int(EIGHTH * 1.5 * SR))
    delay = [0.0] * delay_n
    di = 0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH
        fade = 1.0
        if sec == "fade":
            fade = max(0.0, 1.0 - (bar - 61 + pos / BAR) / 4.0)

        # offbeat FM bass
        if sec != "streets" or bar >= 4:
            off = eighth % 2 == 1
            hz = midi_hz(root + (12 if off else 0))
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.003, 0.05, 0.55, 0.06)
            if not off:
                benv *= 0.35
            raw = square_bl(bass_ph) * 0.5 + saw_bl(bass_ph) * 0.3 + sine(bass2) * 0.45
            bass = drive(raw, 2.4)
            bg = 0.35 if sec == "alley" else 0.7
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        # dark pad
        if sec in ("streets", "alley", "fade"):
            acc = 0.0
            for vi, nmidi in enumerate(chord):
                pad_ph[vi] = (pad_ph[vi] + midi_hz(nmidi) / SR) % 1.0
                acc += sine(pad_ph[vi])
            L[i] += acc / 3.0 * 0.16 * fade
            R[i] += acc / 3.0 * 0.18 * fade

        # chord stabs
        if sec in ("theme", "chase", "theme2"):
            hit = eighth % 2 == 0
            stenv = env_ad(eth, 0.004, 0.12) if hit else 0.0
            acc = 0.0
            for vi, nmidi in enumerate(chord):
                stab_ph[vi] = (stab_ph[vi] + midi_hz(nmidi + 12) / SR) % 1.0
                acc += saw_bl(stab_ph[vi]) * 0.5 + sine(stab_ph[vi]) * 0.4
            stab_lp = one_pole(stab_lp, acc / 3.0, 1600.0)
            val = drive(stab_lp, 2.2) * stenv * 0.32 * fade
            L[i] += val * 0.7
            R[i] += val * 0.85

        lead = 0.0
        if sec in ("theme", "chase", "theme2"):
            mel = MEL_B if sec == "chase" else MEL_A
            nmidi = mel[(bar % 4) * 8 + eighth]
            hz = midi_hz(nmidi)
            lead_ph = (lead_ph + hz / SR) % 1.0
            lead2 = (lead2 + hz * 1.0018 / SR) % 1.0
            lenv = env_adsr(eth, EIGHTH * 0.92, 0.005, 0.04, 0.68, 0.06)
            raw = pulse_bl(lead_ph) * 0.6 + square_bl(lead2) * 0.25 + sine(lead_ph) * 0.35
            lead_lp = one_pole(lead_lp, raw, 3000.0)
            lead = lead_lp * lenv * 0.68 * fade

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.82 + dly * 0.32
        R[i] += lead * 0.7 + dly * 0.45

    write_wav(track_path("16bit", "neon_riot_2min.mp3"), L, R, crunch=720.0)


if __name__ == "__main__":
    main()
