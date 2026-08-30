#!/usr/bin/env python3
"""Syndicate Row — Koshiro beat-'em-up. Cm F Bb G (i–IV–bVII–V). Funk groove, DX piano."""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, organ,
    render_crash, render_hat, render_kick, render_snare, saw_bl, sine,
    square_bl, tri, write_wav,
)

BPM = 126
BARS = 63  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

CM = ((48, 51, 55), 36)  # C Eb G
F_ = ((53, 57, 60), 41)  # F A C — A only here
BB = ((46, 50, 53), 34)  # Bb D F
G_ = ((43, 47, 50), 31)  # G B D — B only here


def harmony(bar: int):
    return (CM, F_, BB, G_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "lot"
    if bar < 24:
        return "stroll"
    if bar < 40:
        return "scrap"
    if bar < 48:
        return "refill"
    if bar < 60:
        return "stroll2"
    return "out"


# Syncopated. A (57/69) only over F. B (59/71) only over G. No Ab.
MEL_A = [
    0, 63, 67, 0, 70, 67, 63, 0,
    69, 0, 72, 69, 65, 0, 60, 65,
    70, 0, 0, 65, 62, 65, 70, 0,
    67, 71, 74, 0, 71, 67, 62, 59,
]
MEL_B = [
    75, 0, 70, 67, 70, 0, 75, 79,
    81, 72, 69, 0, 72, 77, 72, 69,
    77, 70, 65, 0, 70, 74, 77, 0,
    79, 74, 71, 67, 71, 74, 79, 83,
]

BASS = {
    36: [0, 12, 0, 10, 0, 7, 10, 12],  # C: Bb is b7
    41: [0, 12, 0, 4, 7, 4, 12, 7],    # F: A is 3rd
    34: [0, 12, 7, 0, 4, 7, 12, 4],    # Bb: D is 3rd
    31: [0, 12, 4, 0, 7, 4, 12, 7],    # G: B is 3rd
}


def render_clave() -> list[float]:
    m = int(SR * 0.035)
    out = [0.0] * m
    ph = 0.0
    for i in range(m):
        t = i / SR
        ph = (ph + 2450.0 / SR) % 1.0
        out[i] = sine(ph) * math.exp(-t * 90.0)
    return out


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.13, 0.58)
    snare = render_snare(0.11, 215.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(1.4)
    clave = render_clave()

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "lot":
            add_at(L, int((t + SIX * 2) * SR), clave, 0.35 if b in (1, 3) else 0.12)
            add_at(R, int((t + SIX * 2) * SR), clave, 0.4 if b in (1, 3) else 0.1)
            if bar >= 4 and b == 0:
                add_at(L, start, kick, 0.55)
                add_at(R, start, kick, 0.55)
            continue
        if sec == "out":
            if b == 0:
                add_at(L, start, kick, 0.5)
                add_at(R, start, kick, 0.5)
            if b in (1, 3):
                add_at(L, int((t + SIX * 2) * SR), clave, 0.2)
                add_at(R, int((t + SIX * 2) * SR), clave, 0.22)
            continue
        if sec == "refill":
            if b == 0:
                add_at(L, start, kick, 0.85)
                add_at(R, start, kick, 0.85)
            if b == 3:
                add_at(L, start, snare, 0.7)
                add_at(R, start, snare, 0.75)
            for k in range(4):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.1)
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.12)
            add_at(L, int((t + SIX * 2) * SR), clave, 0.22)
            add_at(R, int((t + SIX * 2) * SR), clave, 0.26)
            continue
        # funk: kick 1 + 2-and + 3-and, snare 2+4, 16th hats
        if b == 0:
            add_at(L, start, kick, 0.95)
            add_at(R, start, kick, 0.95)
        if b == 1:
            add_at(L, start, snare, 0.8)
            add_at(R, start, snare, 0.86)
            add_at(L, int((t + SIX * 2) * SR), kick, 0.4)
            add_at(R, int((t + SIX * 2) * SR), kick, 0.4)
        if b == 2:
            add_at(L, int((t + SIX * 2) * SR), kick, 0.5)
            add_at(R, int((t + SIX * 2) * SR), kick, 0.5)
        if b == 3:
            add_at(L, start, snare, 0.84)
            add_at(R, start, snare, 0.9)
        for k in range(4):
            hg = 0.2 if k % 2 == 0 else 0.1
            add_at(L, int((t + SIX * k) * SR), hat_c, hg * 0.7)
            add_at(R, int((t + SIX * k) * SR), hat_c, hg)
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.32)
        add_at(L, int((t + SIX * 2) * SR), clave, 0.16 if b in (1, 3) else 0.06)
        add_at(R, int((t + SIX * 2) * SR), clave, 0.2 if b in (1, 3) else 0.05)

    for bar, g in ((8, 0.5), (24, 0.4), (48, 0.55)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    ep_ph = ep2 = 0.0
    ep_lp = 0.0
    stab_ph = [0.0, 0.0, 0.0]
    stab_lp = 0.0
    gtr_r = gtr_f = 0.0
    gtr_hp = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "out":
            fade = max(0.0, 1.0 - (bar - 60 + pos / BAR) / 3.0)

        rel = BASS[root][ei]
        hz = midi_hz(root + rel)
        bass_ph = (bass_ph + hz / SR) % 1.0
        bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
        benv = env_adsr(eth, EIGHTH, 0.002, 0.018, 0.35, 0.03)
        raw = square_bl(bass_ph) * 0.45 + tri(bass_ph) * 0.3 + sine(bass2) * 0.4
        bass = drive(raw, 2.3)
        bg = 0.7 if sec == "lot" else 0.56
        L[i] += bass * benv * bg * fade
        R[i] += bass * benv * bg * fade

        if sec in ("scrap", "stroll2"):
            step = int(pos / SIX) % 2
            st = pos - int(pos / SIX) * SIX
            genv = env_ad(st, 0.0015, 0.035)
            if step == 1:
                genv *= 0.4
            gtr_r = (gtr_r + midi_hz(root + 12) / SR) % 1.0
            gtr_f = (gtr_f + midi_hz(root + 19) / SR) % 1.0
            graw = saw_bl(gtr_r) * 0.5 + saw_bl(gtr_f) * 0.45
            gtr_hp = one_pole(gtr_hp, graw, 1200.0)
            mute = graw - gtr_hp
            L[i] += mute * genv * 0.22 * fade * 0.8
            R[i] += mute * genv * 0.22 * fade

        if sec in ("scrap", "stroll2") and ei == 0:
            acc = 0.0
            for vi, nm in enumerate(chord):
                stab_ph[vi] = (stab_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                acc += saw_bl(stab_ph[vi]) * 0.45 + sine(stab_ph[vi]) * 0.55
            stenv = env_ad(eth, 0.006, 0.14)
            stab_lp = one_pole(stab_lp, acc / 3.0, 1500.0)
            val = drive(stab_lp, 2.0) * stenv * 0.24 * fade
            L[i] += val * 0.75
            R[i] += val * 0.9

        lead = 0.0
        if sec in ("stroll", "scrap", "stroll2"):
            mel = MEL_B if sec in ("scrap", "stroll2") and bar % 8 >= 4 else MEL_A
            if sec == "scrap":
                mel = MEL_B
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                ep_ph = (ep_ph + hz / SR) % 1.0
                ep2 = (ep2 + hz * 2 / SR) % 1.0
                attack = nmidi != prev
                if attack:
                    lenv = env_adsr(eth, EIGHTH * 0.85, 0.004, 0.06, 0.45, 0.08)
                else:
                    lenv = 0.45
                raw = organ(ep_ph) * 0.5 + sine(ep_ph) * 0.35 + sine(ep2) * 0.12
                ep_lp = one_pole(ep_lp, raw, 2800.0)
                lead = ep_lp * lenv * 0.62 * fade
            else:
                ep_ph = (ep_ph + midi_hz(63) / SR) % 1.0
                ep_lp = one_pole(ep_lp, 0.0, 2800.0)

        L[i] += lead * 0.82
        R[i] += lead * 0.78

    write_wav(track_path("16bit", "syndicate_row_2min.mp3"), L, R, crunch=640.0)


if __name__ == "__main__":
    main()
