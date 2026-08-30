#!/usr/bin/env python3
"""Eidolon Gate — summoning rite. Bm D A Em. Tom circle intro, organ hymn, 16th slap."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, add_at, env_ad, env_adsr, midi_hz, organ, render_crash, render_hat,
    render_kick, render_snare, render_tom, sine, square_bl, tri, write_wav,
)

BPM = 160
BARS = 80
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

BM = ((47, 50, 54), 35)
D_ = ((50, 54, 57), 38)
A_ = ((45, 49, 52), 33)  # C# only here
EM = ((52, 55, 59), 40)


def harmony(bar: int):
    return (BM, D_, A_, EM)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "circle"
    if bar < 20:
        return "invoke"
    if bar < 36:
        return "appear"
    if bar < 52:
        return "rage"
    if bar < 64:
        return "bind"
    if bar < 76:
        return "appear2"
    return "vanish"


# C# (61/73) only over A.
MEL_A = [
    71, 71, 66, 62, 66, 0, 71, 74,
    74, 69, 66, 0, 69, 74, 78, 76,
    73, 73, 69, 64, 69, 0, 73, 76,
    76, 71, 67, 0, 64, 67, 71, 76,
]
MEL_B = [
    83, 78, 74, 78, 83, 0, 81, 78,
    81, 74, 69, 74, 78, 81, 78, 74,
    76, 73, 69, 64, 69, 73, 76, 81,
    79, 76, 71, 67, 71, 76, 79, 0,
]
BASS = [0, 0, 0, 12, 0, 7, 0, 12]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.13, 0.6)
    snare = render_snare(0.11, 205.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(250.0)
    tom_m = render_tom(165.0)
    tom_l = render_tom(100.0)
    crash = render_crash(1.5)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec in ("circle", "invoke"):
            # ritual toms walking down the bar
            if b == 0:
                add_at(L, start, tom_h, 0.55)
                add_at(R, start, tom_h, 0.4)
            if b == 1:
                add_at(L, start, tom_m, 0.45)
                add_at(R, start, tom_m, 0.5)
            if b == 2:
                add_at(L, start, tom_l, 0.6)
                add_at(R, start, tom_l, 0.55)
            if sec == "invoke" and b == 3:
                add_at(L, int((t + EIGHTH) * SR), tom_h, 0.3)
            continue
        if sec == "bind":
            if b == 0:
                add_at(L, start, kick, 0.75)
                add_at(R, start, kick, 0.75)
            if b == 2:
                add_at(L, start, snare, 0.55)
                add_at(R, start, snare, 0.6)
            add_at(L, start, tom_l if b % 2 == 0 else tom_m, 0.25)
            continue
        if sec == "vanish":
            if b == 0:
                add_at(L, start, crash, 0.5)
                add_at(R, start, crash, 0.5)
            continue
        kg = 1.0 if b in (0, 2) else 0.0
        add_at(L, start, kick, kg)
        add_at(R, start, kick, kg)
        if b in (1, 3):
            add_at(L, start, snare, 0.8)
            add_at(R, start, snare, 0.86)
        if sec == "rage":
            for k in range(4):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.12 + 0.04 * (k % 2))
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.1 + 0.05 * (k % 2))
        else:
            add_at(L, start, hat_c, 0.18)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.2)
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.28)

    for bar, g in ((8, 0.3), (20, 0.7), (36, 0.55), (52, 0.35), (64, 0.6)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    organ_ph = [[0.0, 0.0] for _ in range(3)]
    choir_ph = [0.0, 0.0, 0.0]
    bass_ph = bass2 = 0.0
    lead_ph = 0.0
    run_ph = 0.0
    delay_n = max(1, int(SIX * SR))
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
        if sec == "vanish":
            fade = max(0.0, 1.0 - (bar - 76 + pos / BAR) / 4.0)

        acc_l = acc_r = 0.0
        for vi, nm in enumerate(chord):
            organ_ph[vi][0] = (organ_ph[vi][0] + midi_hz(nm) / SR) % 1.0
            organ_ph[vi][1] = (organ_ph[vi][1] + midi_hz(nm) * 2 / SR) % 1.0
            s = organ(organ_ph[vi][0]) + organ(organ_ph[vi][1]) * 0.35
            if vi == 0:
                acc_l += s
            elif vi == 2:
                acc_r += s
            else:
                acc_l += s * 0.7
                acc_r += s * 0.7
        og = 0.4 if sec in ("circle", "invoke", "bind", "vanish") else 0.18
        L[i] += acc_l / 3.0 * og * fade
        R[i] += acc_r / 3.0 * og * fade

        if sec in ("circle", "bind", "vanish"):
            ch = 0.0
            for vi, nm in enumerate(chord):
                choir_ph[vi] = (choir_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                ch += sine(choir_ph[vi])
            L[i] += ch / 3.0 * 0.16 * fade
            R[i] += ch / 3.0 * 0.18 * fade

        if sec not in ("circle",):
            hz = midi_hz(root + BASS[ei])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.004, 0.03, 0.65, 0.04)
            bass = tri(bass_ph) * 0.55 + sine(bass2) * 0.5 + square_bl(bass_ph) * 0.18
            L[i] += bass * benv * 0.56 * fade
            R[i] += bass * benv * 0.56 * fade

        if sec == "rage":
            step = int(pos / SIX) % 4
            nm = chord[step % 3] + 24
            run_ph = (run_ph + midi_hz(nm) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            renv = env_ad(st, 0.001, 0.05)
            run = square_bl(run_ph) * renv * 0.12 * fade
            L[i] += run * 0.5
            R[i] += run * 0.9

        lead = 0.0
        if sec in ("invoke", "appear", "rage", "appear2"):
            mel = MEL_B if sec in ("rage", "appear2") else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                attack = nmidi != prev
                lenv = env_adsr(eth, EIGHTH * 0.92, 0.008, 0.05, 0.62, 0.07) if attack else 0.62
                lead = organ(lead_ph) * lenv * 0.55 * fade
                if sec == "rage":
                    lead *= 1.1
            else:
                lead_ph = (lead_ph + midi_hz(71) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.82 + dly * 0.22
        R[i] += lead * 0.7 + dly * 0.34

    write_wav(track_path("16bit", "eidolon_gate_2min.mp3"), L, R, crunch=700.0)


if __name__ == "__main__":
    main()
