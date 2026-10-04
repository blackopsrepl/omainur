#!/usr/bin/env python3
"""Crystal Siege — SNES fight fanfare. Am F G Am. Snare-roll intro, 16th arp, 8th delay."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, add_at, env_ad, env_adsr, flute, midi_hz,
    render_crash, render_hat, render_kick, render_snare, saw_bl, sine,
    square_bl, tri, write_wav,
)

BPM = 152
BARS = 76
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

AM = ((57, 60, 64), 33)
F_ = ((53, 57, 60), 29)
G_ = ((55, 59, 62), 31)


def harmony(bar: int):
    return (AM, F_, G_, AM)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "fanfare"
    if bar < 12:
        return "clash"
    if bar < 28:
        return "theme"
    if bar < 44:
        return "chorus"
    if bar < 52:
        return "break"
    if bar < 72:
        return "final"
    return "win"


# Holds + rests. B only over G.
MEL_A = [
    76, 76, 0, 72, 69, 0, 72, 74,
    77, 0, 72, 69, 72, 72, 69, 65,
    74, 74, 71, 0, 67, 71, 74, 79,
    76, 0, 72, 69, 64, 67, 69, 72,
]
MEL_B = [
    81, 81, 76, 0, 72, 76, 79, 76,
    77, 72, 69, 72, 77, 0, 76, 72,
    79, 74, 71, 0, 74, 79, 81, 79,
    76, 76, 72, 69, 67, 64, 69, 72,
]
BASS = [0, 12, 0, 7, 12, 7, 5, 12]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.11, 0.65)
    snare = render_snare(0.09, 230.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(1.3)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "fanfare":
            if b == 0:
                add_at(L, start, kick, 0.85)
                add_at(R, start, kick, 0.85)
            nsub = 2 if bar < 2 else 4
            for k in range(nsub):
                st = int((t + BEAT * k / nsub) * SR)
                g = 0.2 + 0.18 * bar + 0.08 * k
                add_at(L, st, snare, g)
                add_at(R, st, snare, g * 1.05)
            continue
        if sec == "win":
            if b == 0:
                add_at(L, start, crash, 0.55)
                add_at(R, start, crash, 0.55)
                add_at(L, start, kick, 0.7)
                add_at(R, start, kick, 0.7)
            continue
        if sec == "break":
            if b == 0:
                add_at(L, start, kick, 0.7)
                add_at(R, start, kick, 0.7)
            if b == 2:
                add_at(L, start, snare, 0.4)
                add_at(R, start, snare, 0.42)
            add_at(L, int((t + SIX) * SR), hat_c, 0.12)
            add_at(R, int((t + SIX * 3) * SR), hat_c, 0.14)
            continue
        # battle: kick 1 + AND of 2, snare 2+4
        add_at(L, start, kick, 0.95 if b == 0 else 0.0)
        add_at(R, start, kick, 0.95 if b == 0 else 0.0)
        if b in (0, 2):
            add_at(L, int((t + SIX * 2) * SR), kick, 0.35)
            add_at(R, int((t + SIX * 2) * SR), kick, 0.35)
        if b in (1, 3):
            add_at(L, start, snare, 0.82)
            add_at(R, start, snare, 0.88)
        add_at(L, start, hat_c, 0.2)
        add_at(R, int((t + EIGHTH) * SR), hat_c, 0.24)
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.3)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.34)

    for bar, g in ((4, 0.7), (12, 0.45), (28, 0.55), (52, 0.4), (64, 0.65)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    lead_ph = lead2 = 0.0
    arp_ph = 0.0
    brass_ph = [0.0, 0.0, 0.0]
    delay_n = max(1, int(EIGHTH * SR))
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
        if sec == "win":
            fade = max(0.0, 1.0 - (bar - 72 + pos / BAR) / 4.0)

        if sec != "fanfare":
            hz = midi_hz(root + BASS[ei])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.003, 0.025, 0.62, 0.03)
            bass = square_bl(bass_ph) * 0.4 + tri(bass_ph) * 0.4 + sine(bass2) * 0.45
            bg = 0.32 if sec == "break" else 0.58
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        if sec in ("fanfare", "chorus", "final") and ei == 0:
            acc = 0.0
            for vi, nm in enumerate(chord):
                brass_ph[vi] = (brass_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                acc += saw_bl(brass_ph[vi]) * 0.55 + sine(brass_ph[vi]) * 0.5
            benv = env_adsr(eth, EIGHTH * 2, 0.01, 0.07, 0.4, 0.08)
            val = acc / 3.0 * benv * (0.42 if sec == "fanfare" else 0.2) * fade
            L[i] += val * 0.9
            R[i] += val * 0.7

        if sec in ("clash", "theme", "chorus", "break", "final"):
            step = int(pos / SIX) % 4
            nm = chord[step % 3] + (12 if step < 3 else 24)
            arp_ph = (arp_ph + midi_hz(nm) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            aenv = env_ad(st, 0.001, 0.045)
            arp = tri(arp_ph) * aenv * 0.16 * fade
            L[i] += arp * (0.45 if step % 2 == 0 else 0.9)
            R[i] += arp * (0.9 if step % 2 == 0 else 0.45)

        lead = 0.0
        if sec in ("theme", "chorus", "final"):
            mel = MEL_B if sec in ("chorus", "final") and bar % 8 >= 4 else MEL_A
            if sec == "chorus":
                mel = MEL_B
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                lead2 = (lead2 + hz * 2 / SR) % 1.0
                attack = nmidi != prev
                lenv = env_adsr(eth, EIGHTH * 0.9, 0.004, 0.04, 0.65, 0.05) if attack else 0.65
                raw = square_bl(lead_ph) * 0.5 + sine(lead2) * 0.35 + flute(lead_ph) * 0.25
                lead = raw * lenv * 0.62 * fade
            else:
                lead_ph = (lead_ph + midi_hz(69) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.8 + dly * 0.28
        R[i] += lead * 0.7 + dly * 0.4

    write_wav(track_path("16bit", "crystal_siege_2min.mp3"), L, R, crunch=640.0)


if __name__ == "__main__":
    main()
