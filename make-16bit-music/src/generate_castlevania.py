#!/usr/bin/env python3
"""Castlevania church banger — Yamane baroque-rock, D harmonic minor."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, organ, pulse_bl,
    render_bell, render_crash, render_hat, render_kick, render_snare,
    saw_bl, sine, square_bl, tri, write_wav,
)

BPM = 144
BARS = 72  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
N = int(SR * BAR * BARS)

# i iv bVI V  — church cadence, A major is the harmonic-minor dagger
DM = ((50, 53, 57), 38, False)
GM = ((43, 46, 50), 31, False)
BB = ((46, 50, 53), 34, True)
A_ = ((45, 49, 52), 33, True)
F_ = ((41, 45, 48), 29, True)
C_ = ((48, 52, 55), 36, True)


def section_of(bar: int) -> str:
    if bar < 8:
        return "nave"      # organ intro
    if bar < 24:
        return "rite"      # theme A
    if bar < 40:
        return "hunt"      # rock B
    if bar < 48:
        return "crypt"     # break, bells
    if bar < 64:
        return "rite2"     # theme A big
    return "amen"


def harmony(bar: int):
    sec = section_of(bar)
    if sec == "hunt":
        return (F_, C_, BB, A_)[bar % 4]
    if sec == "crypt":
        return (DM, A_, DM, A_)[bar % 4]
    return (DM, GM, BB, A_)[bar % 4]


# Theme A over Dm Gm Bb A
MEL_A = [
    74, 69, 65, 69, 74, 76, 77, 76,  # D A F A  D E F E
    74, 70, 67, 70, 74, 72, 70, 69,  # D Bb G Bb  D C Bb A
    70, 74, 77, 74, 72, 70, 69, 65,  # Bb D F D  C Bb A F
    69, 73, 76, 73, 69, 64, 61, 57,  # A C# E C#  A E C# A
]
# Hunt over F C Bb A
MEL_B = [
    72, 69, 65, 69, 72, 77, 76, 72,  # C A F A  C F E C
    72, 67, 64, 67, 72, 76, 74, 72,  # C G E G  C E D C
    70, 65, 62, 65, 70, 74, 72, 70,  # Bb F D F  Bb D C Bb
    73, 76, 81, 76, 73, 69, 64, 61,  # C# E A E  C# A E C#
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.15, 0.45)
    snare = render_snare(0.15, 185.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(2.0)
    bell_d = render_bell(midi_hz(74), 2.6)  # D5
    bell_a = render_bell(midi_hz(69), 2.8)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "nave":
            if b == 0:
                add_at(L, start, kick, 0.4)
                add_at(R, start, kick, 0.4)
            continue
        if sec == "crypt":
            if b == 0:
                add_at(L, start, kick, 0.5)
                add_at(R, start, kick, 0.5)
            if b == 0 and bar % 2 == 0:
                add_at(L, start, bell_d, 0.45)
                add_at(R, start, bell_a, 0.35)
            continue
        kg = 1.0 if b in (0, 2) else 0.4
        add_at(L, start, kick, kg)
        add_at(R, start, kick, kg)
        if b in (1, 3):
            add_at(L, start, snare, 0.8)
            add_at(R, start, snare, 0.86)
        add_at(L, start, hat_c, 0.22)
        add_at(R, start, hat_c, 0.26)
        add_at(L, int((t + EIGHTH) * SR), hat_c, 0.2)
        add_at(R, int((t + EIGHTH) * SR), hat_c, 0.16)
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.32)

    for bar, g in ((8, 0.45), (24, 0.6), (40, 0.35), (48, 0.7), (64, 0.4)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)
    add_at(L, 0, bell_d, 0.5)
    add_at(R, 0, bell_a, 0.4)

    organ_ph = [[0.0, 0.0] for _ in range(3)]
    organ_lp = 0.0
    bass_ph = 0.0
    bass2 = 0.0
    lead_ph = 0.0
    lead2 = 0.0
    hc_ph = 0.0
    choir_ph = [0.0, 0.0, 0.0]
    gtr_r = 0.0
    gtr_f = 0.0
    delay_n = max(1, int(EIGHTH * 1.5 * SR))
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
        if sec == "amen":
            fade = max(0.0, 1.0 - (bar - 64 + pos / BAR) / 8.0)

        # pipe organ chords
        acc_l = acc_r = 0.0
        for vi, nmidi in enumerate(chord):
            hz = midi_hz(nmidi)
            organ_ph[vi][0] = (organ_ph[vi][0] + hz / SR) % 1.0
            organ_ph[vi][1] = (organ_ph[vi][1] + (hz * 2) / SR) % 1.0
            s = organ(organ_ph[vi][0]) + organ(organ_ph[vi][1]) * 0.35
            if vi == 0:
                acc_l += s
            elif vi == 2:
                acc_r += s
            else:
                acc_l += s * 0.7
                acc_r += s * 0.7
        acc_l /= 3.0
        acc_r /= 3.0
        organ_lp = one_pole(organ_lp, (acc_l + acc_r) * 0.5, 1800.0)
        og = 0.42 if sec in ("nave", "crypt") else 0.28
        L[i] += acc_l * og * fade * 0.7 + organ_lp * 0.15 * fade
        R[i] += acc_r * og * fade * 0.7 + organ_lp * 0.15 * fade

        # choir aahs (sines on chord)
        if sec in ("nave", "crypt", "rite2", "amen"):
            ch = 0.0
            for vi, nmidi in enumerate(chord):
                hz = midi_hz(nmidi + 12)
                choir_ph[vi] = (choir_ph[vi] + hz / SR) % 1.0
                ch += sine(choir_ph[vi])
            ch /= 3.0
            cg = 0.2 if sec in ("nave", "crypt") else 0.12
            L[i] += ch * cg * fade
            R[i] += ch * cg * fade * 1.05

        # bass
        if sec not in ("nave",):
            hz = midi_hz(root + BASS[eighth])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + hz * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.004, 0.04, 0.7, 0.04)
            bass = tri(bass_ph) * 0.55 + sine(bass2) * 0.5 + square_bl(bass_ph) * 0.2
            bg = 0.22 if sec == "crypt" else 0.62
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        # gothic guitar fifths on the hunt / reprise
        if sec in ("hunt", "rite2"):
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            genv = env_ad(eth, 0.003, 0.1)
            gtr = drive(saw_bl(gtr_r) + saw_bl(gtr_f), 3.2)
            L[i] += gtr * genv * 0.32 * fade
            R[i] += gtr * genv * 0.4 * fade

        # harpsichord / violin lead
        lead = 0.0
        if sec in ("rite", "hunt", "rite2", "amen"):
            mel = MEL_B if sec == "hunt" else MEL_A
            nmidi = mel[(bar % 4) * 8 + eighth]
            hz = midi_hz(nmidi)
            lead_ph = (lead_ph + hz / SR) % 1.0
            lead2 = (lead2 + hz * 2 / SR) % 1.0
            lenv = env_adsr(eth, EIGHTH * 0.95, 0.004, 0.05, 0.7, 0.07)
            # harpsichord pluck + sustained string
            pluck = (square_bl(lead_ph) * 0.45 + sine(lead2) * 0.2) * env_ad(eth, 0.002, 0.14)
            bowed = (sine(lead_ph) * 0.5 + pulse_bl(lead_ph) * 0.25) * lenv
            lead = (pluck * 0.55 + bowed * 0.7) * fade * (1.1 if sec == "rite2" else 1.0)

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.82 + dly * 0.3
        R[i] += lead * 0.7 + dly * 0.42

        # harpsichord 16th run in hunt
        if sec == "hunt":
            step = int(pos / (EIGHTH * 0.5)) % 4
            nmidi = chord[step % 3] + 24
            hz = midi_hz(nmidi)
            hc_ph = (hc_ph + hz / SR) % 1.0
            st = pos - int(pos / (EIGHTH * 0.5)) * (EIGHTH * 0.5)
            henv = env_ad(st, 0.001, 0.06)
            hc = square_bl(hc_ph) * henv * 0.1 * fade
            L[i] += hc * 0.5
            R[i] += hc * 0.9

    write_wav(track_path("16bit", "thorn_chapel_2min.mp3"), L, R, crunch=900.0)


if __name__ == "__main__":
    main()
