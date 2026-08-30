#!/usr/bin/env python3
"""Wyrm Keel — SNES dragon-airship. Fm Db Eb Bb (i–bVI–bVII–IV). Horn cry, hall reverb."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, Noise, add_at, env_ad, env_adsr, midi_hz, one_pole, organ,
    render_crash, render_kick, render_snare, render_tom, saw_bl, sine,
    tri, write_wav,
)

BPM = 132
BARS = 66  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

FM = ((53, 56, 60), 41)  # F Ab C
DB = ((49, 53, 56), 37)  # Db F Ab — Db/C# only as this chord
EB = ((51, 55, 58), 39)  # Eb G Bb
BB = ((46, 50, 53), 34)  # Bb D F — D only here


def harmony(bar: int):
    return (FM, DB, EB, BB)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "cry"
    if bar < 16:
        return "lift"
    if bar < 32:
        return "soar"
    if bar < 40:
        return "dive"
    if bar < 56:
        return "roar"
    return "horizon"


# Long calls, 5th leaps. D (62/74/86) only over Bb.
MEL_A = [
    65, 65, 65, 0, 60, 56, 60, 65,  # F — C Ab C F
    68, 68, 61, 65, 68, 0, 65, 61,  # Ab Ab Db F Ab
    70, 67, 63, 67, 70, 70, 67, 0,  # Bb G Eb G Bb
    70, 65, 62, 0, 65, 70, 74, 70,  # Bb F D — D only here
]
MEL_B = [
    77, 72, 68, 0, 72, 77, 80, 77,
    80, 73, 68, 73, 80, 0, 77, 73,
    82, 79, 75, 70, 75, 79, 82, 0,
    82, 77, 74, 70, 74, 77, 82, 86,
]
BASS = [0, 0, 0, 0, 7, 7, 12, 12]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.18, 0.32)
    snare = render_snare(0.14, 160.0)
    tom_h = render_tom(175.0)
    tom_l = render_tom(88.0)
    crash = render_crash(2.1)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "cry":
            if b == 0 and bar % 2 == 0:
                add_at(L, start, tom_l, 0.55)
                add_at(R, start, tom_l, 0.5)
            if b == 2 and bar % 2 == 1:
                add_at(L, start, tom_h, 0.35)
                add_at(R, start, tom_h, 0.4)
            continue
        if sec == "horizon":
            if b == 0:
                add_at(L, start, tom_l, 0.4)
                add_at(R, start, kick, 0.3)
            continue
        if sec == "dive":
            # faster wing-beats: toms every beat, snare on 4
            add_at(L, start, tom_h if b % 2 == 0 else tom_l, 0.5)
            add_at(R, start, tom_l if b % 2 == 0 else tom_h, 0.45)
            if b == 3:
                add_at(L, start, snare, 0.55)
                add_at(R, start, snare, 0.6)
            continue
        # wing-beat march: kick 1, tom on 3, snare on 4
        if b == 0:
            add_at(L, start, kick, 0.78)
            add_at(R, start, kick, 0.78)
            add_at(L, start, tom_l, 0.28)
        if b == 2:
            add_at(L, start, tom_h, 0.42)
            add_at(R, start, tom_h, 0.38)
        if b == 3 and sec in ("soar", "roar"):
            add_at(L, start, snare, 0.48)
            add_at(R, start, snare, 0.52)

    for bar, g in ((8, 0.3), (16, 0.45), (32, 0.35), (40, 0.6)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    organ_ph = [0.0, 0.0, 0.0]
    choir_ph = [0.0, 0.0, 0.0]
    harp_ph = 0.0
    bass_ph = bass2 = 0.0
    horn_ph = horn2 = 0.0
    wind = Noise(31)
    wind_lp = 0.0
    # short hall: irregular early taps + light comb. not a rhythmic delay.
    rv_n = max(64, int(0.14 * SR))
    rv = [0.0] * rv_n
    ri = 0
    taps_l = (
        (int(0.011 * SR), 0.36),
        (int(0.023 * SR), 0.26),
        (int(0.041 * SR), 0.18),
        (int(0.067 * SR), 0.12),
    )
    taps_r = (
        (int(0.013 * SR), 0.34),
        (int(0.029 * SR), 0.24),
        (int(0.053 * SR), 0.16),
        (int(0.079 * SR), 0.11),
    )
    fb_off = int(0.097 * SR)

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "horizon":
            fade = max(0.0, 1.0 - (bar - 56 + pos / BAR) / 10.0)

        acc = 0.0
        for vi, nm in enumerate(chord):
            organ_ph[vi] = (organ_ph[vi] + midi_hz(nm) / SR) % 1.0
            acc += organ(organ_ph[vi])
        og = 0.24 if sec in ("cry", "horizon") else 0.1
        L[i] += acc / 3.0 * og * fade
        R[i] += acc / 3.0 * og * fade * 0.92

        if sec in ("cry", "lift", "horizon", "roar"):
            ch = 0.0
            for vi, nm in enumerate(chord):
                choir_ph[vi] = (choir_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                ch += sine(choir_ph[vi])
            cg = 0.18 if sec in ("cry", "horizon") else 0.08
            L[i] += ch / 3.0 * cg * fade
            R[i] += ch / 3.0 * cg * fade * 1.1

        wn = wind.next()
        wind_lp = one_pole(wind_lp, wn, 480.0)
        # wing whoosh on even-bar downbeats
        whoosh = 0.0
        if bar % 2 == 0 and pos < 0.35:
            whoosh = env_ad(pos, 0.03, 0.28)
        wg = 0.055 if sec in ("cry", "dive") else 0.028
        air = wind_lp * (wg + whoosh * 0.08) * fade
        L[i] += air
        R[i] += air * 0.75

        if sec != "cry" or bar >= 4:
            hz = midi_hz(root + BASS[ei])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.012, 0.08, 0.72, 0.1)
            bass = tri(bass_ph) * 0.65 + sine(bass2) * 0.5
            L[i] += bass * benv * 0.5 * fade
            R[i] += bass * benv * 0.5 * fade

        if sec in ("lift", "soar", "roar"):
            # 1–5–8–5, two cycles per bar — locks to the 4/4, not 3-against-4
            step = ei % 4
            nm = chord[0 if step % 2 == 0 else 2] + (24 if step != 2 else 36)
            harp_ph = (harp_ph + midi_hz(nm) / SR) % 1.0
            henv = env_ad(eth, 0.003, 0.09)
            hp = sine(harp_ph) * henv * 0.1 * fade
            L[i] += hp * (0.85 if step % 2 == 0 else 0.4)
            R[i] += hp * (0.4 if step % 2 == 0 else 0.85)

        lead = 0.0
        if sec in ("cry", "soar", "roar", "horizon"):
            mel = MEL_B if sec == "roar" else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                horn_ph = (horn_ph + hz / SR) % 1.0
                horn2 = (horn2 + hz * 0.5 / SR) % 1.0
                attack = nmidi != prev
                if attack:
                    lenv = env_adsr(eth, EIGHTH * 0.95, 0.03, 0.08, 0.7, 0.12)
                else:
                    lenv = 0.7
                horn = (
                    saw_bl(horn_ph) * 0.32
                    + sine(horn_ph) * 0.5
                    + sine(horn2) * 0.22
                )
                g = 0.5 if sec == "cry" else 0.58
                if sec == "horizon":
                    g = 0.4
                lead = horn * lenv * g * fade
            else:
                horn_ph = (horn_ph + midi_hz(65) / SR) % 1.0

        fb = rv[(ri - fb_off) % rv_n]
        rv[ri] = lead + fb * 0.28
        wet_l = 0.0
        wet_r = 0.0
        for off, g in taps_l:
            wet_l += rv[(ri - off) % rv_n] * g
        for off, g in taps_r:
            wet_r += rv[(ri - off) % rv_n] * g
        ri = (ri + 1) % rv_n
        L[i] += lead * 0.8 + wet_l * 0.72
        R[i] += lead * 0.8 + wet_r * 0.72

    write_wav(track_path("16bit", "wyrm_keel_2min.mp3"), L, R, crunch=620.0)


if __name__ == "__main__":
    main()
