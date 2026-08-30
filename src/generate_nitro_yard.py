#!/usr/bin/env python3
"""Nitro Yard — Capcom 16-bit stage. Em D C D (i–bVII–VI–bVII). Dry staccato pulse."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_crash, render_hat, render_kick, render_snare, render_tom, saw_bl,
    sine, square_bl, tri, write_wav,
)

BPM = 156
BARS = 78  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

EM = ((52, 55, 59), 40)
D_ = ((50, 54, 57), 38)  # F# only here
C_ = ((48, 52, 55), 36)


def harmony(bar: int):
    return (EM, D_, C_, D_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "wire"
    if bar < 20:
        return "stage"
    if bar < 36:
        return "boost"
    if bar < 44:
        return "refill"
    if bar < 60:
        return "stage2"
    if bar < 74:
        return "fortress"
    return "clear"


# Staccato jumps + rests. F# (66/78) only over D.
MEL_A = [
    64, 0, 67, 71, 76, 0, 71, 67,
    74, 0, 69, 66, 69, 74, 0, 69,
    72, 0, 67, 64, 67, 72, 76, 0,
    74, 71, 69, 0, 66, 69, 74, 76,
]
MEL_B = [
    76, 0, 79, 76, 71, 0, 67, 71,
    81, 74, 78, 0, 74, 69, 66, 69,
    79, 76, 72, 0, 67, 72, 76, 79,
    81, 0, 74, 78, 74, 69, 74, 76,
]

# Busy octave/5th. Per-root extras stay in E natural minor; F# only on D.
BASS_EM = [0, 12, 7, 12, 0, 10, 7, 12]
BASS_D = [0, 12, 7, 12, 0, 4, 7, 12]
BASS_C = [0, 12, 7, 12, 0, 4, 7, 12]


def bass_pat(root: int) -> list[int]:
    if root == 40:
        return BASS_EM
    if root == 38:
        return BASS_D
    return BASS_C


def render_charge() -> list[float]:
    length = 0.2
    m = int(SR * length)
    out = [0.0] * m
    ph = 0.0
    for i in range(m):
        t = i / SR
        hz = midi_hz(64.0 + 7.0 * (t / length))
        ph = (ph + hz / SR) % 1.0
        env = min(1.0, t / 0.015) * max(0.0, 1.0 - t / length)
        out[i] = sine(ph) * env
    return out


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.11, 0.72)
    snare = render_snare(0.1, 225.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(230.0)
    tom_l = render_tom(115.0)
    crash = render_crash(1.2)
    charge = render_charge()

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "wire":
            # hats on the ands only — the bass is the intro
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.16)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.2)
            if bar == 3 and b == 3:
                add_at(L, start, tom_h, 0.5)
                add_at(R, int((t + SIX) * SR), tom_l, 0.55)
                add_at(L, int((t + SIX * 2) * SR), snare, 0.45)
            continue
        if sec == "refill":
            if b == 0:
                add_at(L, start, kick, 0.8)
                add_at(R, start, kick, 0.8)
            if b == 3:
                add_at(L, start, snare, 0.7)
                add_at(R, start, snare, 0.75)
            for k in range(4):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.1)
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.12)
            continue
        if sec == "clear":
            if b == 0:
                add_at(L, start, crash, 0.45)
                add_at(R, start, crash, 0.45)
                add_at(L, start, kick, 0.6)
                add_at(R, start, kick, 0.6)
            continue
        # Capcom rock: kick 1 + 2-and, snare 2+4, 16th hats
        if b == 0:
            add_at(L, start, kick, 0.95)
            add_at(R, start, kick, 0.95)
        if b == 1:
            add_at(L, int((t + SIX * 2) * SR), kick, 0.42)
            add_at(R, int((t + SIX * 2) * SR), kick, 0.42)
        if b in (1, 3):
            add_at(L, start, snare, 0.84)
            add_at(R, start, snare, 0.9)
        for k in range(4):
            hg = 0.22 if k % 2 == 0 else 0.12
            add_at(L, int((t + SIX * k) * SR), hat_c, hg * 0.75)
            add_at(R, int((t + SIX * k) * SR), hat_c, hg)
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.26)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.3)
        if sec == "fortress" and bar % 4 == 3 and b == 3:
            add_at(L, start, tom_h, 0.45)
            add_at(R, int((t + SIX * 2) * SR), tom_l, 0.55)

    for bar, g in ((4, 0.65), (20, 0.45), (36, 0.3), (44, 0.5), (60, 0.7)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)
        add_at(L, int(bar * BAR * SR), charge, 0.55)
        add_at(R, int(bar * BAR * SR), charge, 0.45)

    bass_ph = bass2 = 0.0
    lead_ph = 0.0
    lead_lp = 0.0
    gtr_r = gtr_f = 0.0
    gtr_hp = 0.0
    ctr_ph = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "clear":
            fade = max(0.0, 1.0 - (bar - 74 + pos / BAR) / 4.0)

        rel = bass_pat(root)[ei]
        hz = midi_hz(root + rel)
        bass_ph = (bass_ph + hz / SR) % 1.0
        bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
        benv = env_adsr(eth, EIGHTH, 0.002, 0.02, 0.45, 0.025)
        raw = square_bl(bass_ph) * 0.5 + tri(bass_ph) * 0.35 + sine(bass2) * 0.4
        bass = drive(raw, 2.6 if sec in ("boost", "fortress") else 2.0)
        bg = 0.72 if sec == "wire" else 0.58
        if sec == "refill":
            bg = 0.65
        L[i] += bass * benv * bg * fade
        R[i] += bass * benv * bg * fade

        if sec in ("boost", "stage2", "fortress"):
            step = int(pos / SIX) % 2
            st = pos - int(pos / SIX) * SIX
            genv = env_ad(st, 0.0015, 0.04)
            if step == 1:
                genv *= 0.45
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            graw = saw_bl(gtr_r) * 0.55 + saw_bl(gtr_f) * 0.45
            gtr_hp = one_pole(gtr_hp, graw, 1100.0)
            mute = graw - gtr_hp
            gg = 0.32 if sec == "fortress" else 0.22
            L[i] += mute * genv * gg * fade * 0.75
            R[i] += mute * genv * gg * fade

        lead = 0.0
        if sec in ("stage", "boost", "stage2", "fortress"):
            mel = MEL_B if sec in ("boost", "fortress") else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                attack = nmidi != prev
                if attack:
                    lenv = env_ad(eth, 0.002, 0.085)
                else:
                    lenv = env_adsr(eth, EIGHTH * 0.7, 0.0, 0.03, 0.35, 0.04)
                raw = pulse_bl(lead_ph) * 0.75 + sine(lead_ph) * 0.28
                lead_lp = one_pole(lead_lp, raw, 3600.0)
                lead = lead_lp * lenv * 0.7 * fade
            else:
                lead_ph = (lead_ph + midi_hz(64) / SR) % 1.0
                lead_lp = one_pole(lead_lp, 0.0, 3600.0)

        L[i] += lead * 0.88
        R[i] += lead * 0.72

        if sec == "fortress" and lead:
            nm = chord[0] + 24
            ctr_ph = (ctr_ph + midi_hz(nm) / SR) % 1.0
            cenv = env_ad(eth, 0.002, 0.06)
            ctr = tri(ctr_ph) * cenv * 0.14 * fade
            L[i] += ctr * 0.5
            R[i] += ctr * 0.9

    write_wav(track_path("16bit", "nitro_yard_2min.mp3"), L, R, crunch=680.0)


if __name__ == "__main__":
    main()
