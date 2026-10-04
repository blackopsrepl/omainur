#!/usr/bin/env python3
"""Cobalt Apex — 16-bit GT touring race. F# mixolydian, start lights, half-time cruise."""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR, Noise, add_at, drive, env_ad, env_adsr, midi_hz, one_pole,
    render_crash, render_hat, render_kick, render_snare, saw_bl, sine,
    square_bl, tri, write_wav,
)

BPM = 148
BARS = 74  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)
TWO_PI = 2.0 * math.pi

# F# mixolydian: F# G# A# B C# D# E
# I bVII IV v  — overtake flips v to V (C# major, F only there)
FS = ((54, 58, 61), 42)   # F# A# C# — A# only as this 3rd
Emaj = ((52, 56, 59), 40)  # E G# B
Bmaj = ((47, 51, 54), 35)  # B D# F# — D# only as this 3rd
CSM = ((49, 52, 56), 37)   # C# E G#
CS = ((49, 53, 56), 37)    # C# F G# — F/E# only here


def section_of(bar: int) -> str:
    if bar < 4:
        return "lights"
    if bar < 12:
        return "formation"
    if bar < 28:
        return "lap"
    if bar < 36:
        return "tunnel"
    if bar < 52:
        return "overtake"
    if bar < 60:
        return "pit"
    if bar < 72:
        return "final"
    return "flag"


def harmony(bar: int):
    loop = (FS, Emaj, Bmaj, CS if section_of(bar) in ("overtake", "final", "flag") else CSM)
    return loop[bar % 4]


# Holds + rests. A# (70/82) over F#. D# (75) over B. F (77) only over C# major.
MEL_A = [
    78, 78, 0, 76, 73, 0, 70, 73,  # F#  rest E C#  rest A# C#
    76, 76, 71, 0, 68, 71, 76, 0,  # E E B  rest G# B E
    75, 71, 66, 0, 71, 75, 78, 75,  # D# B F# rest B D# F# D#
    73, 73, 0, 68, 73, 76, 73, 68,  # C#  rest G# C# E C# G#  (E over C#m)
]
MEL_B = [
    82, 78, 73, 0, 70, 73, 78, 82,  # A# F# C# rest A# C# F# A#
    80, 76, 71, 76, 80, 0, 76, 71,  # G# E B E G# rest E B
    78, 75, 71, 0, 75, 78, 83, 78,  # F# D# B rest D# F# B F#
    77, 73, 68, 73, 77, 80, 77, 0,  # F C# G# C# F G# F rest  (F over C#)
]

BASS = {
    42: [0, 0, 7, 12, 0, 10, 7, 5],   # F#: C# oct  E C# B
    40: [0, 12, 7, 0, 4, 7, 12, 2],   # E:  oct B  G# B oct F#
    35: [0, 0, 4, 7, 12, 7, 4, 0],    # B:  D# F# oct
    37: [0, 12, 3, 7, 0, 10, 7, 3],   # C#m default: E G#  B E
}
BASS_CS = [0, 12, 4, 7, 0, 4, 7, 12]  # C# major: F is 4


def render_light(midi: float) -> list[float]:
    m = int(SR * 0.22)
    out = [0.0] * m
    ph = 0.0
    for i in range(m):
        t = i / SR
        ph = (ph + midi_hz(midi) / SR) % 1.0
        env = min(1.0, t / 0.008) * math.exp(-t * 9.0)
        out[i] = (sine(ph) * 0.7 + tri(ph) * 0.3) * env
    return out


def render_whoosh() -> list[float]:
    m = int(SR * 0.55)
    out = [0.0] * m
    rng = Noise(404)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.72 * hp + 0.28 * n
        env = math.sin(math.pi * t / 0.55)
        out[i] = (n - hp) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.12, 0.45)
    snare = render_snare(0.11, 205.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(1.5)
    whoosh = render_whoosh()
    lights = [render_light(m) for m in (66.0, 70.0, 73.0, 78.0)]

    for k, tone in enumerate(lights):
        add_at(L, int(k * BAR * SR), tone, 0.7)
        add_at(R, int(k * BAR * SR), tone, 0.62)
    add_at(L, int(36 * BAR * SR), whoosh, 0.28)
    add_at(R, int(36 * BAR * SR + 0.04 * SR), whoosh, 0.4)
    add_at(L, int(60 * BAR * SR), whoosh, 0.22)
    add_at(R, int(60 * BAR * SR + 0.03 * SR), whoosh, 0.32)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "lights":
            if bar == 3 and b == 3:
                nsub = 8
                for k in range(nsub):
                    st = int((t + BEAT * k / nsub) * SR)
                    add_at(L, st, snare, 0.15 + 0.5 * (k / nsub))
                    add_at(R, st, snare, 0.15 + 0.5 * (k / nsub))
            continue

        if sec == "flag":
            if b == 0:
                add_at(L, start, crash, 0.65)
                add_at(R, start, crash, 0.65)
                add_at(L, start, kick, 0.7)
                add_at(R, start, kick, 0.7)
            continue

        if sec == "formation":
            for k in range(4):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.1 if k % 2 else 0.16)
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.14 if k % 2 else 0.1)
            if bar >= 8 and b == 0:
                add_at(L, start, kick, 0.55)
                add_at(R, start, kick, 0.55)
            continue

        if sec == "pit":
            if b == 0:
                add_at(L, start, kick, 0.45)
                add_at(R, start, kick, 0.45)
            if b in (1, 3):
                add_at(L, int((t + SIX * 2) * SR), hat_o, 0.2)
                add_at(R, int((t + SIX * 2) * SR), hat_o, 0.24)
            continue

        if sec == "tunnel":
            if b == 0:
                add_at(L, start, kick, 0.6)
                add_at(R, start, kick, 0.6)
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.14)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.18)
            continue

        # lap: touring half-time (snare on 3). overtake/final: push backbeat.
        if sec == "lap":
            if b == 0:
                add_at(L, start, kick, 0.88)
                add_at(R, start, kick, 0.88)
            if b == 2:
                add_at(L, start, snare, 0.8)
                add_at(R, start, snare, 0.86)
            for k in range(4):
                hg = 0.18 if k % 2 == 0 else 0.08
                add_at(L, int((t + SIX * k) * SR), hat_c, hg * 0.75)
                add_at(R, int((t + SIX * k) * SR), hat_c, hg)
            if b == 3:
                add_at(L, int((t + EIGHTH) * SR), hat_o, 0.22)
                add_at(R, int((t + EIGHTH) * SR), hat_o, 0.26)
        else:
            if b == 0:
                add_at(L, start, kick, 0.92)
                add_at(R, start, kick, 0.92)
            if b == 2:
                add_at(L, int((t + SIX * 3) * SR), kick, 0.38)
                add_at(R, int((t + SIX * 3) * SR), kick, 0.38)
            if b in (1, 3):
                add_at(L, start, snare, 0.82)
                add_at(R, start, snare, 0.88)
            for k in range(4):
                hg = 0.22 if k % 2 == 0 else 0.11
                add_at(L, int((t + SIX * k) * SR), hat_c, hg * 0.7)
                add_at(R, int((t + SIX * k) * SR), hat_c, hg)
            if b == 3:
                add_at(L, int((t + EIGHTH) * SR), hat_o, 0.3)
                add_at(R, int((t + EIGHTH) * SR), hat_o, 0.34)

    for bar, g in ((4, 0.75), (12, 0.4), (28, 0.3), (36, 0.55), (52, 0.25), (60, 0.7)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    rumble_ph = rumble2 = 0.0
    bass_ph = bass2 = 0.0
    lead_ph = lead2 = 0.0
    lead_lp = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    tach_ph = 0.0
    delay_n = max(1, int(SIX * SR))
    delay = [0.0] * delay_n
    di = 0
    wind = Noise(77)
    wind_lp = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "flag":
            fade = max(0.0, 1.0 - (bar - 72 + pos / BAR) / 2.0)

        # cabin rumble
        rh = midi_hz(root)
        rumble_ph = (rumble_ph + rh * 0.5 / SR) % 1.0
        rumble2 = (rumble2 + rh * 0.5 * 1.003 / SR) % 1.0
        rg = 0.2 if sec in ("lights", "formation", "tunnel", "pit") else 0.08
        rum = (sine(rumble_ph) + sine(rumble2)) * 0.5 * rg * fade
        L[i] += rum
        R[i] += rum

        wn = wind.next()
        wind_lp = one_pole(wind_lp, wn, 700.0)
        wg = 0.035 if sec in ("lights", "tunnel") else 0.012
        L[i] += wind_lp * wg * fade
        R[i] += wind_lp * wg * 0.75 * fade

        # tach ticks — 16th 1-5-b7-5, formation + overtake
        if sec in ("formation", "overtake", "final"):
            step = int(pos / SIX) % 4
            offs = (0, 7, 12, 7)[step]
            tach_ph = (tach_ph + midi_hz(root + 24 + offs) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            tenv = env_ad(st, 0.001, 0.035)
            tach = square_bl(tach_ph) * tenv * 0.08 * fade
            L[i] += tach * (0.55 if step % 2 else 0.95)
            R[i] += tach * (0.95 if step % 2 else 0.55)

        if sec not in ("lights",):
            if sec in ("overtake", "final", "flag") and root == 37:
                rel = BASS_CS[ei]
            else:
                rel = BASS[root][ei]
            hz = midi_hz(root + rel)
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH * 0.9, 0.003, 0.03, 0.5, 0.04)
            raw = sine(bass_ph) * 0.5 + square_bl(bass_ph) * 0.28 + tri(bass2) * 0.28
            bass = drive(raw, 2.0)
            bg = 0.68 if sec == "formation" else 0.52
            if sec == "pit":
                bg = 0.6
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        if sec in ("tunnel", "pit", "lights"):
            acc = 0.0
            for vi, nm in enumerate(chord):
                pad_ph[vi] = (pad_ph[vi] + midi_hz(nm) / SR) % 1.0
                acc += sine(pad_ph[vi])
            pg = 0.2 if sec == "tunnel" else 0.12
            L[i] += acc / 3.0 * pg * fade
            R[i] += acc / 3.0 * pg * 1.1 * fade

        lead = 0.0
        if sec in ("lap", "overtake", "final"):
            mel = MEL_B if sec in ("overtake", "final") else MEL_A
            idx = (bar % 4) * 8 + ei
            nmidi = mel[idx]
            prev = mel[idx - 1] if ei else (mel[7] if (bar % 4) == 0 else mel[idx - 1])
            if nmidi:
                target = midi_hz(nmidi)
                if prev and abs(nmidi - prev) >= 3:
                    frac = min(1.0, eth / (EIGHTH * 0.28))
                    hz = midi_hz(prev) + (target - midi_hz(prev)) * frac
                else:
                    hz = target
                lead_ph = (lead_ph + hz / SR) % 1.0
                lead2 = (lead2 + hz * 1.003 / SR) % 1.0
                hold = nmidi == prev
                if hold:
                    lenv = env_adsr(eth, EIGHTH * 0.98, 0.0, 0.03, 0.72, 0.08)
                else:
                    lenv = env_adsr(eth, EIGHTH * 0.92, 0.012, 0.06, 0.55, 0.1)
                raw = saw_bl(lead_ph) * 0.38 + sine(lead_ph) * 0.45 + sine(lead2) * 0.22
                cut = 2600.0 if sec == "final" else 2200.0
                lead_lp = one_pole(lead_lp, raw, cut)
                lg = 0.72 if sec == "final" else 0.64
                lead = lead_lp * lenv * lg * fade
            else:
                lead_ph = (lead_ph + midi_hz(73) / SR) % 1.0
                lead_lp = one_pole(lead_lp, 0.0, 2200.0)

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.84 + dly * 0.18
        R[i] += lead * 0.74 + dly * 0.34

    write_wav(track_path("16bit", "cobalt_apex_2min.mp3"), L, R, crunch=880.0)


if __name__ == "__main__":
    main()
