#!/usr/bin/env python3
"""Clock tower final — Castlevania last phase, D harmonic minor, 168 BPM."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, organ, pulse_bl,
    render_bell, render_crash, render_hat, render_kick, render_snare, saw_bl,
    sine, square_bl, tri, write_wav,
)

BPM = 168
BARS = 84  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
N = int(SR * BAR * BARS)

DM = ((50, 53, 57), 38)
A_ = ((45, 49, 52), 33)  # A C# E
BB = ((46, 50, 53), 34)
C_ = ((48, 52, 55), 36)


def harmony(bar: int):
    # Dm | A | Bb | A — late phase swaps Bb for C
    if 52 <= bar < 64:
        return (DM, A_, C_, A_)[bar % 4]
    return (DM, A_, BB, A_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "gears"
    if bar < 24:
        return "ascent"
    if bar < 40:
        return "scream"
    if bar < 52:
        return "pendulum"
    if bar < 76:
        return "final"
    return "strike"


MEL_A = [
    74, 69, 65, 69, 74, 76, 77, 76,  # D A F A  D E F E
    73, 76, 81, 76, 73, 69, 64, 69,  # C# E A E  C# A E A
    70, 74, 77, 74, 70, 65, 70, 74,  # Bb D F D  Bb F Bb D
    76, 73, 69, 73, 76, 81, 76, 73,  # E C# A C#  E A E C#
]
MEL_B = [
    86, 81, 77, 81, 86, 88, 89, 88,  # scream octave
    85, 88, 93, 88, 85, 81, 76, 81,
    82, 86, 89, 86, 82, 77, 82, 86,
    88, 85, 81, 85, 88, 93, 88, 85,
]
MEL_C = [
    74, 69, 65, 69, 74, 76, 77, 76,  # Dm
    73, 76, 81, 76, 73, 69, 64, 69,  # A
    72, 67, 64, 67, 72, 76, 74, 72,  # C
    73, 76, 81, 76, 73, 69, 64, 61,  # A
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.12, 0.5)
    snare = render_snare(0.12, 180.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(1.5)
    bell_d = render_bell(midi_hz(74), 2.0)
    bell_a = render_bell(midi_hz(81), 2.2)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "gears":
            if b in (0, 2):
                add_at(L, start, kick, 0.55)
                add_at(R, start, kick, 0.55)
            if b == 0 and bar % 2 == 0:
                add_at(L, start, bell_d, 0.4)
                add_at(R, start, bell_a, 0.28)
            continue
        if sec == "pendulum":
            if b == 0:
                add_at(L, start, kick, 0.6)
                add_at(R, start, kick, 0.6)
                add_at(L, start, bell_d if bar % 2 == 0 else bell_a, 0.35)
                add_at(R, start, bell_a if bar % 2 == 0 else bell_d, 0.3)
            continue
        if sec == "strike":
            if b == 0:
                add_at(L, start, crash, 0.55)
                add_at(R, start, crash, 0.55)
                add_at(L, start, kick, 0.8)
                add_at(R, start, kick, 0.8)
            continue
        add_at(L, start, kick, 1.0 if b in (0, 2) else 0.4)
        add_at(R, start, kick, 1.0 if b in (0, 2) else 0.4)
        if b in (1, 3):
            add_at(L, start, snare, 0.82)
            add_at(R, start, snare, 0.88)
        add_at(L, start, hat_c, 0.22)
        add_at(R, start, hat_c, 0.26)
        add_at(L, int((t + EIGHTH) * SR), hat_c, 0.2)
        add_at(R, int((t + EIGHTH) * SR), hat_c, 0.16)
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.3)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.34)

    for bar, g in ((8, 0.5), (24, 0.65), (40, 0.35), (52, 0.8)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    organ_ph = [[0.0, 0.0] for _ in range(3)]
    choir_ph = [0.0, 0.0, 0.0]
    bass_ph = bass2 = 0.0
    lead_ph = lead2 = 0.0
    gtr_r = gtr_f = 0.0
    delay_n = max(1, int(EIGHTH * SR))
    delay = [0.0] * delay_n
    di = 0
    BASS = [0, 0, 12, 0, 0, 7, 12, 0]

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH
        fade = 1.0
        if sec == "strike":
            fade = max(0.0, 1.0 - (bar - 76 + pos / BAR) / 8.0)

        # organ — bigger and more driving than Thorn Chapel
        acc_l = acc_r = 0.0
        for vi, nmidi in enumerate(chord):
            hz = midi_hz(nmidi)
            organ_ph[vi][0] = (organ_ph[vi][0] + hz / SR) % 1.0
            organ_ph[vi][1] = (organ_ph[vi][1] + hz * 2 / SR) % 1.0
            s = organ(organ_ph[vi][0]) + organ(organ_ph[vi][1]) * 0.4
            if vi == 0:
                acc_l += s
            elif vi == 2:
                acc_r += s
            else:
                acc_l += s * 0.7
                acc_r += s * 0.7
        og = 0.48 if sec in ("gears", "pendulum") else 0.3
        L[i] += acc_l / 3.0 * og * fade
        R[i] += acc_r / 3.0 * og * fade

        if sec in ("gears", "pendulum", "final", "strike"):
            ch = 0.0
            for vi, nmidi in enumerate(chord):
                choir_ph[vi] = (choir_ph[vi] + midi_hz(nmidi + 12) / SR) % 1.0
                ch += sine(choir_ph[vi])
            L[i] += ch / 3.0 * 0.16 * fade
            R[i] += ch / 3.0 * 0.18 * fade

        if sec not in ("gears",):
            hz = midi_hz(root + BASS[eighth])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.003, 0.03, 0.7, 0.03)
            bass = tri(bass_ph) * 0.5 + sine(bass2) * 0.5 + square_bl(bass_ph) * 0.22
            bg = 0.25 if sec == "pendulum" else 0.65
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        if sec in ("scream", "final"):
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            genv = env_ad(eth, 0.002, 0.08)
            gtr = drive(saw_bl(gtr_r) + saw_bl(gtr_f), 3.4)
            L[i] += gtr * genv * 0.34 * fade
            R[i] += gtr * genv * 0.42 * fade

        lead = 0.0
        if sec in ("ascent", "scream", "final", "pendulum"):
            if sec == "scream":
                mel = MEL_B
            elif sec == "final":
                mel = MEL_C if bar < 64 else MEL_B
            elif sec == "pendulum":
                mel = MEL_A
            else:
                mel = MEL_A
            nmidi = mel[(bar % 4) * 8 + eighth]
            hz = midi_hz(nmidi)
            lead_ph = (lead_ph + hz / SR) % 1.0
            lead2 = (lead2 + hz * 2 / SR) % 1.0
            lenv = env_adsr(eth, EIGHTH * 0.9, 0.003, 0.04, 0.7, 0.05)
            pluck = square_bl(lead_ph) * env_ad(eth, 0.002, 0.1)
            scream = (pulse_bl(lead_ph) * 0.55 + sine(lead_ph) * 0.4 + sine(lead2) * 0.12) * lenv
            lead = (pluck * 0.35 + scream * 0.8) * fade
            if sec == "scream":
                lead *= 1.15
            elif sec == "pendulum":
                lead *= 0.55

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.85 + dly * 0.28
        R[i] += lead * 0.72 + dly * 0.4

    write_wav(track_path("16bit", "last_bell_2min.mp3"), L, R, crunch=850.0)


if __name__ == "__main__":
    main()
