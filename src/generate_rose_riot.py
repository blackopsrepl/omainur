#!/usr/bin/env python3
"""Rose Riot — 16-bit Sunset Strip stage. C#m A E B, guitar-squeal intro, Adler swagger."""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR, Noise, add_at, drive, env_ad, env_adsr, midi_hz, one_pole,
    pulse_bl, render_crash, render_hat, render_kick, render_snare,
    render_tom, saw_bl, sine, square_bl, tri, write_wav,
)

BPM = 124
BARS = 62  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)
TWO_PI = 2.0 * math.pi

# C# natural minor. D# lives on B (its 3rd) in the hook; F# is scale-4 / B's 5th.
CSM = ((49, 52, 56), 37)  # C# E G#
A_ = ((45, 49, 52), 33)   # A C# E
E_ = ((52, 56, 59), 40)   # E G# B
B_ = ((47, 51, 54), 35)   # B D# F#


def harmony(bar: int):
    return (CSM, A_, E_, B_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "squeal"
    if bar < 12:
        return "riff"
    if bar < 28:
        return "verse"
    if bar < 36:
        return "chorus"
    if bar < 44:
        return "solo"
    if bar < 52:
        return "riff2"
    if bar < 60:
        return "chorus2"
    return "lastcall"


# Holds + rests. Slash pentatonic C# E F# G# B; D# (75/63) only over B.
MEL_A = [
    73, 73, 0, 71, 68, 0, 64, 68,  # C#  rest B G#  rest E G#
    69, 69, 64, 0, 61, 64, 69, 73,  # A A E  rest C# E A C#
    71, 71, 0, 68, 64, 68, 71, 76,  # B  rest G# E G# B E
    75, 71, 66, 0, 71, 66, 63, 66,  # D# B F# rest B F# D# F#
]
MEL_B = [
    76, 76, 73, 71, 73, 0, 68, 71,  # E E C# B C# rest G# B
    73, 69, 64, 69, 73, 76, 0, 73,  # C# A E A C# E rest C#
    76, 71, 68, 0, 71, 76, 80, 76,  # E B G# rest B E G# E
    78, 75, 71, 66, 71, 75, 78, 0,  # F# D# B F# B D# F# rest
]
MEL_C = [
    85, 80, 76, 80, 0, 76, 73, 71,  # C# G# E G# rest E C# B
    73, 76, 81, 81, 76, 0, 73, 69,  # C# E A A E rest C# A
    80, 80, 76, 71, 68, 71, 76, 80,  # G# G# E B G# B E G#
    83, 78, 75, 78, 83, 78, 75, 71,  # B F# D# F# B F# D# B
]

# Per-root swagger. Not the Gator octave pump.
BASS = {
    37: [0, 0, 7, 12, 0, 10, 7, 12],  # C#: G# oct  b7 G# oct
    33: [0, 0, 4, 7, 12, 7, 4, 0],    # A:  C# E  oct E C#
    40: [0, 12, 7, 0, 4, 7, 12, 4],   # E:  oct G# G# B oct G#
    35: [0, 0, 4, 7, 12, 10, 7, 4],   # B:  D# F# oct A F# D#
}

# Mute-chug gate. 1 = hit, 0 = rest (riff timekeeper).
CHUG = [1, 1, 0, 1, 1, 0, 1, 0]


def render_squeal() -> list[float]:
    length = BAR * 2.0
    m = int(SR * length)
    out = [0.0] * m
    ph = 0.0
    ph2 = 0.0
    for i in range(m):
        t = i / SR
        u = t / length
        midi = 64.0 + 22.0 * math.sin(math.pi * u)
        hz = midi_hz(midi)
        ph = (ph + hz / SR) % 1.0
        ph2 = (ph2 + hz * 1.0035 / SR) % 1.0
        env = min(1.0, t / 0.05) * math.sin(math.pi * u)
        trem = 0.82 + 0.18 * math.sin(TWO_PI * 7.0 * t)
        raw = saw_bl(ph) * 0.7 + sine(ph2) * 0.35 + pulse_bl(ph) * 0.2
        out[i] = drive(raw, 3.4) * env * trem
    return out


def render_scratch() -> list[float]:
    m = int(SR * 0.055)
    out = [0.0] * m
    rng = Noise(909)
    ph = 0.0
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.6 * hp + 0.4 * n
        ph = (ph + midi_hz(80) / SR) % 1.0
        env = math.exp(-t * 48.0)
        out[i] = ((n - hp) * 0.7 + saw_bl(ph) * 0.35) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.14, 0.58)
    snare = render_snare(0.15, 185.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(235.0)
    tom_m = render_tom(160.0)
    tom_l = render_tom(108.0)
    crash = render_crash(1.7)
    squeal = render_squeal()
    scratch = render_scratch()

    add_at(L, 0, squeal, 0.62)
    add_at(R, 0, squeal, 0.7)
    add_at(L, int((BARS - 2) * BAR * SR), squeal, 0.5)
    add_at(R, int((BARS - 2) * BAR * SR), squeal, 0.55)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "squeal":
            for k in range(4):
                st = int((t + SIX * k) * SR)
                g = 0.18 + 0.08 * (k % 2)
                add_at(L, st, scratch, g * 0.85)
                add_at(R, st, scratch, g)
            if bar == 3:
                nsub = 4 if b < 2 else 8
                for k in range(nsub):
                    st = int((t + BEAT * k / nsub) * SR)
                    g = 0.2 + 0.55 * (b / 3.0) * (k / max(1, nsub - 1))
                    add_at(L, st, snare, g)
                    add_at(R, st, snare, g)
                if b == 3:
                    add_at(L, start, tom_h, 0.45)
                    add_at(R, int((t + SIX) * SR), tom_m, 0.5)
                    add_at(L, int((t + SIX * 2) * SR), tom_l, 0.6)
            continue

        if sec == "lastcall":
            if b == 0:
                add_at(L, start, crash, 0.7)
                add_at(R, start, crash, 0.7)
                add_at(L, start, kick, 0.85)
                add_at(R, start, kick, 0.85)
            continue

        # Kick: 1, 1-and, 3-and (forward swagger). Chorus adds 4-and.
        if b == 0:
            add_at(L, start, kick, 0.95)
            add_at(R, start, kick, 0.95)
            add_at(L, int((t + EIGHTH) * SR), kick, 0.55)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.55)
        if b == 2:
            add_at(L, int((t + EIGHTH) * SR), kick, 0.72)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.72)
        if sec in ("chorus", "chorus2") and b == 3:
            add_at(L, int((t + EIGHTH) * SR), kick, 0.4)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.4)

        if b in (1, 3):
            sg = 0.92 if sec in ("chorus", "chorus2") else 0.78
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.06)
            if sec == "verse" and b == 3:
                add_at(L, int((t + EIGHTH) * SR), snare, 0.22)
                add_at(R, int((t + EIGHTH) * SR), snare, 0.18)

        if sec in ("verse",):
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.22)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.26)
        elif sec in ("chorus", "chorus2"):
            add_at(L, start, hat_c, 0.2)
            add_at(R, start, hat_c, 0.24)
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.32)
            if b == 3:
                add_at(L, int((t + EIGHTH) * SR), hat_o, 0.34)
                add_at(R, int((t + EIGHTH) * SR), hat_o, 0.38)
        elif sec == "riff2" and b == 0:
            add_at(L, start, hat_c, 0.16)
            add_at(R, start, hat_c, 0.2)
        elif sec == "solo":
            add_at(L, start, hat_o, 0.12)
            add_at(R, start, hat_o, 0.16)

        if sec == "solo" and bar % 2 == 1 and b == 3:
            add_at(L, start, tom_h, 0.5)
            add_at(R, int((t + SIX) * SR), tom_m, 0.55)
            add_at(L, int((t + SIX * 2) * SR), tom_l, 0.62)
            add_at(R, int((t + SIX * 3) * SR), snare, 0.4)

        if bar in (11, 27, 43, 51) and b == 3:
            add_at(L, start, tom_h, 0.55)
            add_at(R, int((t + SIX) * SR), tom_m, 0.6)
            add_at(L, int((t + SIX * 2) * SR), tom_l, 0.7)
            add_at(R, int((t + SIX * 3) * SR), snare, 0.5)

    for bar, g in ((4, 0.7), (12, 0.5), (28, 0.75), (36, 0.4), (44, 0.45), (52, 0.8)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    gtr_r = gtr_f = 0.0
    gtr_lp = 0.0
    ring_r = ring_f = 0.0
    lead_ph = lead2 = 0.0
    lead_lp = 0.0
    harm_ph = 0.0
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
        if sec == "lastcall":
            fade = max(0.0, 1.0 - (bar - 60 + pos / BAR) / 2.0)

        # Bass — pick attack, stays out of the intro squeal
        if sec not in ("squeal",):
            rel = BASS[root][ei]
            hz = midi_hz(root + rel)
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH * 0.92, 0.002, 0.025, 0.55, 0.04)
            raw = square_bl(bass_ph) * 0.42 + tri(bass_ph) * 0.3 + sine(bass2) * 0.5
            bass = drive(raw, 2.4 if sec in ("chorus", "chorus2") else 1.9)
            bg = 0.62 if sec not in ("riff2",) else 0.7
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        # Mute-chug fifths — the riff's clock
        if sec in ("riff", "verse", "riff2") and CHUG[ei]:
            genv = env_ad(eth, 0.002, 0.07)
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            graw = saw_bl(gtr_r) + saw_bl(gtr_f) * 0.85
            gtr_lp = one_pole(gtr_lp, graw, 1600.0)
            gtr = drive(gtr_lp, 3.5)
            gg = 0.34 if sec == "riff2" else 0.28
            L[i] += gtr * genv * gg * fade * 0.7
            R[i] += gtr * genv * gg * fade
        elif sec in ("chorus", "chorus2"):
            # ringing open fifths, half-note
            half = pos % (BEAT * 2)
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            ring_r = (ring_r + rh / SR) % 1.0
            ring_f = (ring_f + fh / SR) % 1.0
            renv = env_adsr(half, BEAT * 2, 0.01, 0.08, 0.55, 0.18)
            graw = saw_bl(ring_r) * 0.6 + saw_bl(ring_f) * 0.5 + sine(ring_r) * 0.2
            gtr = drive(graw, 2.8)
            L[i] += gtr * renv * 0.3 * fade
            R[i] += gtr * renv * 0.38 * fade

        lead = 0.0
        if sec in ("verse", "chorus", "solo", "chorus2"):
            if sec == "solo":
                mel = MEL_C
            elif sec in ("chorus", "chorus2"):
                mel = MEL_B
            else:
                mel = MEL_A
            idx = (bar % 4) * 8 + ei
            nmidi = mel[idx]
            prev = mel[idx - 1] if ei else mel[7 if (bar % 4) == 0 else idx - 1]
            if nmidi:
                target = midi_hz(nmidi)
                if prev and abs(nmidi - prev) >= 3:
                    frac = min(1.0, eth / (EIGHTH * 0.32))
                    hz = midi_hz(prev) + (target - midi_hz(prev)) * frac
                else:
                    hz = target
                if nmidi == prev:
                    hz *= 1.0 + 0.0038 * math.sin(TWO_PI * 5.2 * t)
                lead_ph = (lead_ph + hz / SR) % 1.0
                lead2 = (lead2 + hz * 1.0032 / SR) % 1.0
                hold = nmidi == prev
                if hold:
                    lenv = env_adsr(eth, EIGHTH * 0.98, 0.0, 0.02, 0.7, 0.06)
                else:
                    lenv = env_adsr(eth, EIGHTH * 0.9, 0.004, 0.05, 0.55, 0.07)
                raw = saw_bl(lead_ph) * 0.5 + pulse_bl(lead2) * 0.35 + sine(lead_ph) * 0.3
                lead_lp = one_pole(lead_lp, drive(raw, 2.6), 4200.0)
                lg = 0.78 if sec == "solo" else 0.68
                lead = lead_lp * lenv * lg * fade
                if sec == "chorus2":
                    harm_ph = (harm_ph + midi_hz(nmidi + 7) / SR) % 1.0
                    lead += tri(harm_ph) * lenv * 0.16 * fade
            else:
                lead_ph = (lead_ph + midi_hz(73) / SR) % 1.0
                lead_lp = one_pole(lead_lp, 0.0, 4200.0)

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.86 + dly * 0.2
        R[i] += lead * 0.72 + dly * 0.38

    write_wav(track_path("16bit", "rose_riot_2min.mp3"), L, R, crunch=700.0)


if __name__ == "__main__":
    main()
