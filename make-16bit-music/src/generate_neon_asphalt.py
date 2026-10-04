#!/usr/bin/env python3
"""Neon Asphalt — night-city chase. Gm Eb F D (i–bVI–bVII–V). Sliding bass, FM grit lead."""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR, Noise, add_at, drive, env_ad, env_adsr, midi_hz, one_pole,
    pulse_bl, render_crash, render_hat, render_kick, render_snare,
    render_tom, saw_bl, sine, square_bl, tri, write_wav,
)

BPM = 142
BARS = 71  # ~2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)
TWO_PI = 2.0 * math.pi

# G natural minor. A lives on F (3rd) / D (5th). F# only on D (V).
GM = ((55, 58, 62), 31)  # G Bb D
EB = ((51, 55, 58), 27)  # Eb G Bb
F_ = ((53, 57, 60), 29)  # F A C
D_ = ((50, 54, 57), 26)  # D F# A


def harmony(bar: int):
    return (GM, EB, F_, D_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "ignition"
    if bar < 12:
        return "cruise"
    if bar < 28:
        return "chase"
    if bar < 36:
        return "overpass"
    if bar < 52:
        return "nitro"
    if bar < 56:
        return "refill"
    if bar < 68:
        return "chase2"
    return "skid"


# Motivic: holds + rests. A (69/57) over F/D. F# (66/78) only over D.
MEL_A = [
    67, 0, 70, 67, 62, 0, 58, 0,   # G  Bb G D  Bb
    70, 67, 63, 0, 58, 63, 67, 70,  # Bb G Eb  Bb Eb G Bb
    72, 0, 69, 65, 0, 60, 65, 69,   # C  A F  C F A
    74, 70, 66, 0, 62, 66, 69, 66,  # D Bb F#  D F# A F#
]
MEL_B = [
    79, 0, 74, 70, 74, 0, 79, 82,   # G  D Bb D  G Bb
    79, 75, 70, 0, 67, 70, 75, 79,  # G Eb Bb  G Bb Eb G
    81, 72, 69, 0, 72, 77, 72, 69,  # A C A  C F C A
    78, 74, 69, 66, 69, 74, 78, 0,  # F# D A F# A D F#
]

# Sliding urban bass — not the Gator octave pump.
BASS = {
    31: [0, 7, 0, 12, 10, 0, 7, 12],   # G: 5 rest oct b7 rest 5 oct
    27: [0, 0, 4, 7, 12, 7, 4, 12],    # Eb: 3 5 oct 5 3 oct
    29: [0, 12, 0, 4, 7, 0, 12, 4],    # F: oct rest 3 5 rest oct 3
    26: [0, 0, 4, 7, 12, 4, 7, 12],    # D: 3 5 oct 3 5 oct (F#=4)
}

# Asphalt knock: kick mask per 16th of a bar (1=hit). Unique vs funk / 4otf.
KICK_16 = [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0]
# Rim ghosts on selected 16ths
RIM_16 = [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0]


def render_rim() -> list[float]:
    m = int(SR * 0.028)
    out = [0.0] * m
    rng = Noise(505)
    ph = 0.0
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.58 * hp + 0.42 * n
        ph = (ph + 2850.0 / SR) % 1.0
        env = math.exp(-t * 110.0)
        out[i] = ((n - hp) * 0.55 + sine(ph) * 0.5) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_squeal() -> list[float]:
    """Tire-squeal pitch dive — ignition signature."""
    length = BAR * 1.5
    m = int(SR * length)
    out = [0.0] * m
    ph = ph2 = 0.0
    for i in range(m):
        t = i / SR
        u = t / length
        midi = 76.0 - 18.0 * (u ** 0.7)
        hz = midi_hz(midi)
        ph = (ph + hz / SR) % 1.0
        ph2 = (ph2 + hz * 1.004 / SR) % 1.0
        env = min(1.0, t / 0.04) * (1.0 - u) ** 0.6
        trem = 0.85 + 0.15 * math.sin(TWO_PI * 9.0 * t)
        raw = saw_bl(ph) * 0.55 + pulse_bl(ph2) * 0.35 + sine(ph) * 0.2
        out[i] = drive(raw, 2.8) * env * trem
    return out


def render_engine() -> list[float]:
    """Sub pulse throb under the squeal."""
    length = BAR * 2.0
    m = int(SR * length)
    out = [0.0] * m
    ph = 0.0
    for i in range(m):
        t = i / SR
        u = t / length
        hz = midi_hz(31.0 + 0.5 * math.sin(TWO_PI * 2.0 * t))
        ph = (ph + hz / SR) % 1.0
        env = min(1.0, t / 0.08) * (0.55 + 0.45 * abs(math.sin(TWO_PI * 4.0 * t / BEAT)))
        env *= 1.0 - 0.35 * u
        out[i] = sine(ph) * env
    return out


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.12, 0.68)
    snare = render_snare(0.11, 210.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(220.0)
    tom_m = render_tom(155.0)
    tom_l = render_tom(100.0)
    crash = render_crash(1.5)
    rim = render_rim()
    squeal = render_squeal()
    engine = render_engine()

    # --- intro FX ---
    add_at(L, 0, squeal, 0.55)
    add_at(R, 0, squeal, 0.48)
    add_at(L, 0, engine, 0.7)
    add_at(R, 0, engine, 0.7)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "ignition":
            # rim clicks + soft kick on 1 from bar 2
            for k in range(4):
                si = b * 4 + k
                if RIM_16[si]:
                    add_at(L, int((t + SIX * k) * SR), rim, 0.22)
                    add_at(R, int((t + SIX * k) * SR), rim, 0.28)
            if bar >= 2 and b == 0:
                add_at(L, start, kick, 0.55)
                add_at(R, start, kick, 0.55)
            if bar == 3 and b == 3:
                add_at(L, start, tom_h, 0.45)
                add_at(R, int((t + SIX) * SR), tom_m, 0.5)
                add_at(L, int((t + SIX * 2) * SR), tom_l, 0.55)
                add_at(R, int((t + SIX * 3) * SR), snare, 0.4)
            continue

        if sec == "skid":
            if b == 0:
                add_at(L, start, kick, 0.55)
                add_at(R, start, kick, 0.55)
                if bar == 68:
                    add_at(L, start, crash, 0.4)
                    add_at(R, start, crash, 0.4)
            if b in (1, 3):
                add_at(L, int((t + SIX * 2) * SR), rim, 0.18)
                add_at(R, int((t + SIX * 2) * SR), rim, 0.22)
            continue

        if sec == "refill":
            if b == 0:
                add_at(L, start, kick, 0.8)
                add_at(R, start, kick, 0.8)
            if b == 3:
                add_at(L, start, snare, 0.7)
                add_at(R, start, snare, 0.75)
            for k in range(4):
                add_at(L, int((t + SIX * k) * SR), hat_c, 0.09)
                add_at(R, int((t + SIX * k) * SR), hat_c, 0.11)
            if RIM_16[b * 4 + 2]:
                add_at(L, int((t + SIX * 2) * SR), rim, 0.2)
                add_at(R, int((t + SIX * 2) * SR), rim, 0.24)
            continue

        if sec == "overpass":
            # half-time knock: kick 1, snare 3, sparse hats, tom answers
            if b == 0:
                add_at(L, start, kick, 0.9)
                add_at(R, start, kick, 0.9)
            if b == 2:
                add_at(L, start, snare, 0.72)
                add_at(R, start, snare, 0.78)
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.12)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.14)
            if bar % 4 == 3 and b == 3:
                add_at(L, start, tom_h, 0.4)
                add_at(R, int((t + SIX * 2) * SR), tom_l, 0.5)
            continue

        # asphalt knock: patterned kick 16ths, snare 2+4, 8th hats, rim ghosts
        for k in range(4):
            si = b * 4 + k
            if KICK_16[si]:
                kg = 0.95 if k == 0 and b == 0 else 0.55
                if sec == "cruise":
                    kg *= 0.85
                add_at(L, int((t + SIX * k) * SR), kick, kg)
                add_at(R, int((t + SIX * k) * SR), kick, kg)
            if RIM_16[si] and sec in ("chase", "nitro", "chase2"):
                add_at(L, int((t + SIX * k) * SR), rim, 0.16)
                add_at(R, int((t + SIX * k) * SR), rim, 0.2)
        if b in (1, 3):
            sg = 0.7 if sec == "cruise" else 0.86
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.06)
            # ghost after snare
            if sec in ("nitro", "chase2"):
                add_at(L, int((t + SIX * 3) * SR), snare, 0.22)
                add_at(R, int((t + SIX * 3) * SR), snare, 0.24)
        for k in (0, 2):
            hg = 0.18 if sec == "cruise" else 0.24
            add_at(L, int((t + SIX * k) * SR), hat_c, hg * 0.7)
            add_at(R, int((t + SIX * k) * SR), hat_c, hg)
        add_at(L, int((t + SIX) * SR), hat_c, 0.1)
        add_at(R, int((t + SIX * 3) * SR), hat_c, 0.12)
        if b == 3 and sec in ("nitro", "chase2"):
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.32)

    for bar, g in ((4, 0.55), (12, 0.45), (28, 0.35), (36, 0.5), (56, 0.55)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    bass_lp = 0.0
    slide_hz = midi_hz(31)
    lead_ph = lead_mod = 0.0
    lead_lp = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    pad_lp = 0.0
    fifth_r = fifth_f = 0.0
    fifth_hp = 0.0
    delay_L = [0.0] * int(SR * SIX)  # 16th delay glue
    delay_R = [0.0] * int(SR * SIX)
    dlen = len(delay_L)
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
        if sec == "skid":
            fade = max(0.0, 1.0 - (bar - 68 + pos / BAR) / 3.0)

        # --- sliding synth bass ---
        rel = BASS[root][ei]
        target = midi_hz(root + rel)
        # portamento: fast glide within the eighth
        slide_hz += (target - slide_hz) * min(1.0, 480.0 / SR + eth * 18.0)
        bass_ph = (bass_ph + slide_hz / SR) % 1.0
        bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
        benv = env_adsr(eth, EIGHTH, 0.002, 0.022, 0.42, 0.028)
        # FM-ish grit: square+tri carrier, mild mod
        mod = sine((bass_ph * 2.0) % 1.0) * 0.15
        raw = (
            square_bl((bass_ph + mod) % 1.0) * 0.48
            + tri(bass_ph) * 0.32
            + sine(bass2) * 0.38
        )
        bass_lp = one_pole(bass_lp, raw, 900.0 if sec == "overpass" else 1600.0)
        bass = drive(bass_lp, 2.5 if sec in ("nitro", "chase2") else 2.1)
        bg = 0.78 if sec == "ignition" else 0.58
        if sec == "refill":
            bg = 0.68
        if sec == "overpass":
            bg = 0.62
        L[i] += bass * benv * bg * fade
        R[i] += bass * benv * bg * fade

        # --- soft chord pad (cruise+) ---
        if sec not in ("ignition", "skid"):
            acc = 0.0
            for vi, nm in enumerate(chord):
                pad_ph[vi] = (pad_ph[vi] + midi_hz(nm) / SR) % 1.0
                acc += sine(pad_ph[vi]) * 0.55 + tri(pad_ph[vi]) * 0.25
            pad_lp = one_pole(pad_lp, acc / 3.0, 700.0)
            pg = 0.12 if sec in ("cruise", "refill", "overpass") else 0.08
            L[i] += pad_lp * pg * fade * 0.85
            R[i] += pad_lp * pg * fade

        # --- power-fifth mute chug (nitro / chase2) ---
        if sec in ("nitro", "chase2"):
            step = int(pos / SIX) % 2
            st = pos - int(pos / SIX) * SIX
            genv = env_ad(st, 0.0015, 0.038)
            if step == 1:
                genv *= 0.4
            fifth_r = (fifth_r + midi_hz(root + 12) / SR) % 1.0
            fifth_f = (fifth_f + midi_hz(root + 19) / SR) % 1.0
            graw = saw_bl(fifth_r) * 0.5 + saw_bl(fifth_f) * 0.45
            fifth_hp = one_pole(fifth_hp, graw, 1250.0)
            mute = graw - fifth_hp
            L[i] += mute * genv * 0.2 * fade * 0.75
            R[i] += mute * genv * 0.2 * fade

        # --- FM-ish cool synth lead ---
        lead = 0.0
        if sec in ("chase", "nitro", "chase2"):
            mel = MEL_B if sec in ("nitro",) else MEL_A
            if sec == "chase2" and bar % 8 >= 4:
                mel = MEL_B
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_mod = (lead_mod + hz * 2.01 / SR) % 1.0
                mod_idx = 0.55 + 0.25 * math.sin(TWO_PI * 0.5 * t)
                lead_ph = (lead_ph + (hz / SR) * (1.0 + mod_idx * sine(lead_mod) * 0.35)) % 1.0
                attack = nmidi != prev
                if attack:
                    lenv = env_adsr(eth, EIGHTH * 0.9, 0.004, 0.05, 0.5, 0.07)
                else:
                    lenv = 0.5
                # carrier stack: pulse + sine + mild saw grit
                raw = (
                    pulse_bl(lead_ph) * 0.55
                    + sine(lead_ph) * 0.35
                    + saw_bl(lead_ph) * 0.18
                )
                lead_lp = one_pole(lead_lp, raw, 3200.0)
                lead = drive(lead_lp, 1.8) * lenv * 0.62 * fade
            else:
                lead_ph = (lead_ph + midi_hz(67) / SR) % 1.0
                lead_lp = one_pole(lead_lp, 0.0, 3200.0)

        # 16th delay glue on lead (mix, not second melody)
        delayed = delay_L[di]
        delay_L[di] = lead * 0.28
        delay_R[di] = lead * 0.22
        di = (di + 1) % dlen
        L[i] += lead * 0.9 + delayed * 0.55
        R[i] += lead * 0.78 + delayed * 0.7

        # overpass: sparse echo of lead motif as soft bell tones on downbeats
        if sec == "overpass" and ei in (0, 4):
            nm = chord[0] + 12
            # reuse pad path lightly
            bell_ph = (pad_ph[0] + midi_hz(nm) / SR) % 1.0
            pad_ph[0] = bell_ph
            benv2 = env_ad(eth, 0.005, 0.2)
            bv = (sine(bell_ph) * 0.6 + sine((bell_ph * 2) % 1.0) * 0.25) * benv2 * 0.2 * fade
            L[i] += bv * 0.7
            R[i] += bv

    out = track_path("16bit", "neon_asphalt_2min.mp3")
    write_wav(out, L, R, crunch=620.0)
    print(f"Neon Asphalt  BPM={BPM}  key=Gm  bars={BARS}")


if __name__ == "__main__":
    main()
