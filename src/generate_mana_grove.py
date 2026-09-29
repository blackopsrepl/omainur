#!/usr/bin/env python3
"""Mana Grove — Kikuta-method lush SNES atmosphere (methods only, not a SoM clone).

Bb major wonder: Bb Gm Eb F. Soft/hall space, dreamy flute lead, leaf-tick
percussion. Form: whisper → grove → mist → clear → grove.
"""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR,
    Noise,
    add_at,
    env_ad,
    env_adsr,
    flute,
    midi_hz,
    one_pole,
    organ,
    render_bell,
    render_crash,
    render_hat,
    render_kick,
    render_tom,
    sine,
    tri,
    write_wav,
)

BPM = 96
BARS = 48  # 120 * 96 / 240 = 48 → 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# Bb | Gm | Eb | F  — warm pastoral I–vi–IV–V (Bb major)
BB = ((46, 50, 53), 34)  # Bb D F
GM = ((43, 46, 50), 31)  # G Bb D
EB = ((39, 43, 46), 27)  # Eb G Bb
F_ = ((41, 45, 48), 29)  # F A C  — A only here


def harmony(bar: int):
    return (BB, GM, EB, F_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "whisper"
    if bar < 20:
        return "grove"
    if bar < 30:
        return "mist"
    if bar < 40:
        return "clear"
    return "grove2"


# Sparse dreamy motives with holds/rests. A (69) only over F.
MEL_A = [
    70, 70, 0, 65, 62, 0, 65, 70,  # Bb
    70, 0, 67, 62, 65, 0, 70, 74,  # Gm: Bb · G D F · Bb D
    75, 70, 67, 0, 63, 67, 70, 75,  # Eb: Eb Bb G · Eb G Bb Eb
    72, 0, 69, 65, 69, 0, 72, 77,  # F: C · A F A · C F
]

MEL_B = [
    77, 77, 72, 0, 70, 65, 70, 72,  # Bb: F F C · Bb F Bb C
    74, 70, 67, 0, 62, 67, 70, 74,  # Gm
    75, 0, 70, 67, 63, 67, 70, 75,  # Eb
    77, 72, 69, 65, 69, 72, 77, 0,  # F: F C A F A C F ·
]

# Sparse bass: root holds with gentle lift — not the common [0,0,12,...]
BASS = [0, 0, 0, 0, 0, 7, 0, 12]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.22, 0.22)  # soft, rounded
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(210.0)
    tom_l = render_tom(110.0)
    crash = render_crash(2.4)
    bell_bb = render_bell(midi_hz(70), 3.2)
    bell_f = render_bell(midi_hz(65), 2.8)
    bell_hi = render_bell(midi_hz(77), 2.2)

    # Soft leaf-tick percussion (Kikuta field: space > groove)
    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "whisper":
            if b == 0 and bar % 2 == 0:
                add_at(L, start, bell_bb, 0.22)
                add_at(R, start, bell_f, 0.18)
            if b == 2 and bar % 4 == 1:
                add_at(R, start, bell_hi, 0.12)
                add_at(L, int((t + EIGHTH) * SR), bell_f, 0.08)
            continue

        if sec == "mist":
            # almost no kick — soft hat mist + rare low tom
            if b == 0 and bar % 2 == 0:
                add_at(L, start, tom_l, 0.22)
                add_at(R, start, tom_l, 0.18)
            if b in (1, 3):
                add_at(L, int((t + EIGHTH) * SR), hat_c, 0.08)
                add_at(R, start, hat_c, 0.07)
            continue

        if sec == "grove2":
            if b == 0:
                add_at(L, start, kick, 0.28)
                add_at(R, start, kick, 0.28)
            if b == 0 and bar % 2 == 0:
                add_at(L, start, bell_f, 0.14)
                add_at(R, start, bell_bb, 0.12)
            continue

        # grove / clear: soft heartbeat kick on 1, leaf ticks, no hard snare
        if b == 0:
            kg = 0.55 if sec == "clear" else 0.42
            add_at(L, start, kick, kg)
            add_at(R, start, kick, kg)
        if b == 2:
            add_at(L, start, tom_h, 0.18 if sec == "grove" else 0.26)
            add_at(R, int((t + EIGHTH) * SR), tom_l, 0.2)
        # irregular leaf hats (not every 8th)
        if b in (0, 2):
            add_at(L, int((t + SIX) * SR), hat_c, 0.1)
            add_at(R, int((t + SIX * 3) * SR), hat_c, 0.09)
        if b == 3 and sec == "clear":
            add_at(L, start, hat_o, 0.14)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.11)

    for bar, g in ((8, 0.22), (20, 0.18), (30, 0.28), (40, 0.2)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g * 0.95)

    # Soft hall: irregular early reflections + slower wet (not on-grid)
    hall_taps = [
        max(1, int(0.037 * SR)),
        max(1, int(0.089 * SR)),
        max(1, int(0.143 * SR)),
        max(1, int(0.271 * SR)),
    ]
    hall_bufs = [[0.0] * t for t in hall_taps]
    hall_i = [0, 0, 0, 0]
    hall_g = [0.28, 0.2, 0.14, 0.1]

    pad_ph = [0.0, 0.0, 0.0]
    pad2_ph = [0.0, 0.0, 0.0]
    choir_ph = [0.0, 0.0, 0.0]
    bass_ph = bass2 = 0.0
    lead_ph = lead2 = 0.0
    harp_ph = 0.0
    spark_ph = 0.0
    wind = Noise(41)
    wind_lp = 0.0
    # gentle quarter-ish delay for lead glue (on tempo, not drifting)
    delay_n = max(1, int(BEAT * 0.75 * SR))
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
        if sec == "grove2":
            fade = max(0.0, 1.0 - (bar - 40 + pos / BAR) / 8.0)
        elif sec == "whisper":
            fade = min(1.0, (bar + pos / BAR) / 4.0)

        # lush sine/organ pads (Kikuta space)
        acc_l = acc_r = 0.0
        for vi, nm in enumerate(chord):
            pad_ph[vi] = (pad_ph[vi] + midi_hz(nm) / SR) % 1.0
            pad2_ph[vi] = (pad2_ph[vi] + midi_hz(nm) * 1.0035 / SR) % 1.0  # ~6 cents
            s = (
                organ(pad_ph[vi]) * 0.55
                + sine(pad_ph[vi]) * 0.35
                + sine(pad2_ph[vi]) * 0.25
            )
            if vi == 0:
                acc_l += s
            elif vi == 2:
                acc_r += s
            else:
                acc_l += s * 0.75
                acc_r += s * 0.75
        pg = {
            "whisper": 0.28,
            "grove": 0.2,
            "mist": 0.3,
            "clear": 0.16,
            "grove2": 0.24,
        }[sec]
        L[i] += acc_l / 3.0 * pg * fade
        R[i] += acc_r / 3.0 * pg * fade

        # choir veil in mist / whisper / return
        if sec in ("whisper", "mist", "grove2"):
            ch = 0.0
            for vi, nm in enumerate(chord):
                choir_ph[vi] = (choir_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                ch += sine(choir_ph[vi])
            cg = 0.2 if sec == "mist" else 0.12
            L[i] += ch / 3.0 * cg * fade
            R[i] += ch / 3.0 * cg * 1.1 * fade

        # wind / canopy air
        wn = wind.next()
        wind_lp = one_pole(wind_lp, wn, 420.0)
        wg = 0.045 if sec == "whisper" else (0.028 if sec == "mist" else 0.014)
        L[i] += wind_lp * wg * fade
        R[i] += wind_lp * wg * 0.75 * fade

        # sparse warm bass
        if sec not in ("whisper",) or bar >= 4:
            if ei in (0, 5, 7):
                hz = midi_hz(root + BASS[ei])
                bass_ph = (bass_ph + hz / SR) % 1.0
                bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
                dur = EIGHTH * (2.4 if ei == 0 else 1.2)
                benv = env_adsr(eth, dur, 0.02, 0.12, 0.55, 0.14)
                bass = tri(bass_ph) * 0.55 + sine(bass2) * 0.7 + sine(bass_ph) * 0.2
                bg = 0.38 if sec != "mist" else 0.22
                L[i] += bass * benv * bg * fade
                R[i] += bass * benv * bg * fade
            else:
                bass_ph = (bass_ph + midi_hz(root) / SR) % 1.0

        # soft harp sparkle (16ths, light) — Kikuta color
        if sec in ("grove", "clear", "mist"):
            step = int(pos / SIX) % 8
            # only on select steps so it breathes
            if step in (0, 3, 5, 7) or (sec == "clear" and step in (1, 4)):
                nm = chord[step % 3] + 24
                harp_ph = (harp_ph + midi_hz(nm) / SR) % 1.0
                st = pos - int(pos / SIX) * SIX
                henv = env_ad(st, 0.002, 0.09)
                hg = 0.07 if sec == "mist" else (0.12 if sec == "clear" else 0.09)
                hp = sine(harp_ph) * henv * hg * fade
                L[i] += hp * (0.35 if step % 2 else 0.9)
                R[i] += hp * (0.9 if step % 2 else 0.35)
            else:
                harp_ph = (harp_ph + midi_hz(chord[0] + 24) / SR) % 1.0

        # clear-section high sparkle ticks
        if sec == "clear" and ei in (2, 6):
            spark_ph = (spark_ph + midi_hz(chord[2] + 36) / SR) % 1.0
            senv = env_ad(eth, 0.001, 0.06)
            sp = flute(spark_ph) * senv * 0.08 * fade
            L[i] += sp * 0.5
            R[i] += sp

        # dreamy flute lead (slight unison detune ≤7 cents)
        lead = 0.0
        if sec in ("grove", "mist", "clear", "grove2"):
            mel = MEL_B if sec == "clear" else MEL_A
            # mist: thinner — play only even eighths / held tones
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if sec == "mist" and ei % 2 == 1 and nmidi == prev:
                nmidi = nmidi  # keep holds
            if sec == "mist" and ei in (1, 3, 5) and mel[(bar % 4) * 8 + ei] and not prev:
                nmidi = 0  # more air in mist
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                lead2 = (lead2 + hz * 1.0038 / SR) % 1.0  # ~6.5 cents
                attack = nmidi != prev
                if attack:
                    lenv = env_adsr(eth, EIGHTH * 1.05, 0.025, 0.1, 0.58, 0.12)
                else:
                    lenv = 0.58
                lg = 0.52 if sec != "mist" else 0.32
                if sec == "clear":
                    lg = 0.58
                lead = (
                    flute(lead_ph) * 0.72
                    + flute(lead2) * 0.28
                    + sine(lead_ph) * 0.15
                ) * lenv * lg * fade
            else:
                lead_ph = (lead_ph + midi_hz(70) / SR) % 1.0
                lead2 = (lead2 + midi_hz(70) * 1.0038 / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        wet = lead * 0.72 + dly * 0.38
        L[i] += wet * 0.85
        R[i] += wet * 0.95 + dly * 0.08

        # soft hall on mix send (pads+lead+air already in L/R — send dry-ish)
        send = (L[i] + R[i]) * 0.5 * 0.22
        hall = 0.0
        for ti, tap in enumerate(hall_taps):
            buf = hall_bufs[ti]
            idx = hall_i[ti]
            hall += buf[idx] * hall_g[ti]
            buf[idx] = send
            hall_i[ti] = (idx + 1) % tap
        # gentle stereo smear
        L[i] += hall * 0.9
        R[i] += hall * 1.05

    write_wav(track_path("16bit", "mana_grove_2min.mp3"), L, R, crunch=480.0)


if __name__ == "__main__":
    main()
