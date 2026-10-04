#!/usr/bin/env python3
"""Infiltration — Metal Gear 2 night raid. Sparse, tense, A harmonic minor."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, Noise, add_at, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_crash, render_hat, render_kick, render_snare, saw_bl, sine,
    square_bl, tri, write_wav,
)

BPM = 112
BARS = 56  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# Am | Em | F | E  — i v bVI V, sneaking toward the sting
AM = ((57, 60, 64), 33)
EM = ((52, 55, 59), 28)
F_ = ((53, 57, 60), 29)
E_ = ((52, 56, 59), 28)


def harmony(bar: int):
    return (AM, EM, F_, E_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "codec"
    if bar < 24:
        return "yard"
    if bar < 32:
        return "alert"
    if bar < 48:
        return "depths"
    return "extract"


# Sparse 8ths: 0 = rest. G# only on E.
MEL = [
    69, 0, 64, 0, 67, 64, 69, 0,   # A  E  G E A     (G = b7 of Am, bluesy stealth)
    67, 0, 64, 0, 59, 64, 67, 0,   # G  E  B E G
    65, 0, 60, 65, 69, 65, 60, 0,  # F  C F A F C
    64, 0, 68, 64, 71, 68, 64, 0,  # E  G# E B G# E
]
MEL_2 = [
    76, 0, 72, 69, 72, 0, 69, 64,
    71, 0, 67, 64, 67, 0, 64, 59,
    72, 69, 65, 0, 69, 65, 60, 0,
    76, 71, 68, 64, 68, 71, 76, 0,
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.18, 0.3)
    snare = render_snare(0.1, 240.0)
    hat_c = render_hat(True)
    crash = render_crash(1.8)
    rng = Noise(5)

    # dry rim-ish from snare at low gain
    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "codec":
            if b == 0:
                add_at(L, start, kick, 0.45)
                add_at(R, start, kick, 0.45)
            continue
        if sec == "extract":
            if b in (0, 2):
                add_at(L, start, kick, 0.4)
                add_at(R, start, kick, 0.4)
            continue
        # heartbeat kick on 1, sometimes 3
        if b == 0 or (b == 2 and sec in ("yard", "depths")):
            add_at(L, start, kick, 0.7 if b == 0 else 0.45)
            add_at(R, start, kick, 0.7 if b == 0 else 0.45)
        if sec == "alert" and b in (1, 3):
            add_at(L, start, snare, 0.55)
            add_at(R, start, snare, 0.6)
        elif b in (1, 3) and sec == "depths":
            add_at(L, start, snare, 0.28)
            add_at(R, start, snare, 0.3)
        # closed hats, very dry 8ths
        if sec != "codec":
            hg = 0.2 if sec == "alert" else 0.12
            add_at(L, start, hat_c, hg * 0.7)
            add_at(R, start, hat_c, hg)
            add_at(L, int((t + EIGHTH) * SR), hat_c, hg * 0.6)
            add_at(R, int((t + EIGHTH) * SR), hat_c, hg * 0.5)

    add_at(L, int(8 * BAR * SR), crash, 0.25)
    add_at(R, int(8 * BAR * SR), crash, 0.25)
    add_at(L, int(32 * BAR * SR), crash, 0.4)
    add_at(R, int(32 * BAR * SR), crash, 0.4)

    bass_ph = 0.0
    gtr_r = gtr_f = 0.0
    gtr_hp = 0.0
    lead_ph = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    tick_ph = 0.0
    delay_n = max(1, int(BEAT * SR))  # quarter-note echo, spy-like
    delay = [0.0] * delay_n
    di = 0
    air = Noise(4242)
    air_lp = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH
        fade = 1.0
        if sec == "extract":
            fade = max(0.0, 1.0 - (bar - 48 + pos / BAR) / 8.0)

        # triangle bass — slow, on beat
        if sec != "codec" or bar >= 4:
            if eighth % 2 == 0:
                hz = midi_hz(root)
                bass_ph = (bass_ph + hz / SR) % 1.0
                benv = env_adsr(eth, EIGHTH * 2, 0.01, 0.08, 0.55, 0.12)
                bass = tri(bass_ph) * 0.75 + sine(bass_ph) * 0.4
                bg = 0.55 if sec != "codec" else 0.3
                L[i] += bass * benv * bg * fade
                R[i] += bass * benv * bg * fade
            else:
                bass_ph = (bass_ph + midi_hz(root) / SR) % 1.0

        # muted 16th "guitar" chug — the Metal Gear tick
        if sec in ("yard", "alert", "depths"):
            step = int(pos / SIX) % 16
            st = pos - int(pos / SIX) * SIX
            # ghost notes on off 16ths
            genv = env_ad(st, 0.0015, 0.035)
            if step % 2 == 1:
                genv *= 0.4
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            raw = saw_bl(gtr_r) * 0.55 + saw_bl(gtr_f) * 0.45
            gtr_hp = one_pole(gtr_hp, raw, 900.0)
            # highpassed mute
            mute = raw - gtr_hp
            gg = 0.38 if sec == "alert" else 0.26
            L[i] += mute * genv * gg * fade * 0.8
            R[i] += mute * genv * gg * fade

        # low pad
        acc = 0.0
        for vi, nmidi in enumerate(chord):
            pad_ph[vi] = (pad_ph[vi] + midi_hz(nmidi) / SR) % 1.0
            acc += sine(pad_ph[vi])
        pg = 0.22 if sec in ("codec", "extract") else 0.12
        L[i] += acc / 3.0 * pg * fade
        R[i] += acc / 3.0 * pg * fade * 1.05

        # sonar / codec blip
        if sec in ("codec", "extract") and eighth == 0:
            hz = midi_hz(81)
            tick_ph = (tick_ph + hz / SR) % 1.0
            tenv = env_ad(pos, 0.002, 0.18)
            blip = sine(tick_ph) * tenv * 0.12 * fade
            L[i] += blip * 0.5
            R[i] += blip

        lead = 0.0
        if sec in ("yard", "alert", "depths"):
            mel = MEL_2 if sec in ("alert", "depths") and bar % 8 >= 4 else MEL
            nmidi = mel[(bar % 4) * 8 + eighth]
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                lenv = env_adsr(eth, EIGHTH * 0.85, 0.01, 0.06, 0.55, 0.1)
                lead = (pulse_bl(lead_ph) * 0.35 + sine(lead_ph) * 0.7) * lenv * 0.5 * fade
            else:
                lead_ph = (lead_ph + midi_hz(69) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.7 + dly * 0.4
        R[i] += lead * 0.85 + dly * 0.28

        n = air.next()
        air_lp = one_pole(air_lp, n, 400.0)
        hiss = air_lp * (0.025 if sec == "codec" else 0.015)
        L[i] += hiss
        R[i] += hiss * 0.85

    write_wav(track_path("16bit", "night_raid_2min.mp3"), L, R, crunch=0.0)


if __name__ == "__main__":
    main()
