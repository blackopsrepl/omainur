#!/usr/bin/env python3
"""Dust Canyon — spaghetti-western 16-bit gallop. D dorian, whistle, tremolo."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, flute, midi_hz, render_crash,
    render_hat, render_kick, render_snare, render_tom, saw_bl, sine, write_wav,
)

BPM = 132
BARS = 66  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
TRIP = BEAT / 3.0  # gallop
N = int(SR * BAR * BARS)

# D dorian: D E F G A B C — IV is G major (the dorian tell)
DM = ((50, 53, 57), 38)
G_ = ((43, 47, 50), 31)  # G B D
C_ = ((48, 52, 55), 36)
EM = ((52, 55, 59), 40)


def harmony(bar: int):
    return (DM, G_, C_, G_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "horizon"
    if bar < 24:
        return "ride"
    if bar < 40:
        return "showdown"
    if bar < 48:
        return "wind"
    if bar < 62:
        return "ride2"
    return "dusk"


# 8ths. B natural only over G (and as 6th of D dorian on weak notes).
MEL = [
    69, 70, 69, 65, 62, 65, 69, 72,  # A Bb? NO Bb in dorian. Use 69 67 69 65
    67, 71, 74, 71, 67, 62, 67, 71,  # G B D B  G D G B  over G
    72, 67, 64, 67, 72, 74, 72, 67,  # C
    67, 71, 74, 79, 74, 71, 67, 62,  # G
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.14, 0.35)
    snare = render_snare(0.12, 170.0)
    hat = render_hat(True)
    tom_h = render_tom(180.0)
    tom_l = render_tom(95.0)
    crash = render_crash(2.0)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "horizon":
            if b == 0:
                add_at(L, start, tom_l, 0.5)
                add_at(R, start, tom_l, 0.5)
            continue
        if sec == "wind":
            if b in (0, 2):
                add_at(L, start, kick, 0.4)
                add_at(R, start, kick, 0.4)
            continue
        if sec == "dusk":
            if b == 0:
                add_at(L, start, kick, 0.45)
                add_at(R, start, kick, 0.45)
            continue
        # gallop: kick on the beat, tom on the last triplet
        add_at(L, start, kick, 0.85 if b % 2 == 0 else 0.55)
        add_at(R, start, kick, 0.85 if b % 2 == 0 else 0.55)
        add_at(L, int((t + 2 * TRIP) * SR), tom_h, 0.4)
        add_at(R, int((t + 2 * TRIP) * SR), tom_l, 0.35)
        if b in (1, 3):
            add_at(L, start, snare, 0.55)
            add_at(R, start, snare, 0.6)
        add_at(L, start, hat, 0.14)
        add_at(R, int((t + EIGHTH) * SR), hat, 0.1)

    add_at(L, int(8 * BAR * SR), crash, 0.4)
    add_at(R, int(8 * BAR * SR), crash, 0.4)
    add_at(L, int(40 * BAR * SR), crash, 0.3)
    add_at(R, int(40 * BAR * SR), crash, 0.3)

    whistle_ph = 0.0
    trem_r = trem_f = 0.0
    bass_ph = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    harm_ph = 0.0

    # Fix MEL bar 0 — D dorian, no Bb
    mel_a = [
        69, 67, 69, 65, 62, 65, 69, 72,  # A G A F  D F A C
        67, 71, 74, 71, 67, 62, 67, 71,
        72, 67, 64, 67, 72, 74, 72, 67,
        67, 71, 74, 79, 74, 71, 67, 62,
    ]

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH
        fade = 1.0
        if sec == "dusk":
            fade = max(0.0, 1.0 - (bar - 62 + pos / BAR) / 4.0)

        # dry bass on roots
        hz = midi_hz(root)
        bass_ph = (bass_ph + hz / SR) % 1.0
        if sec not in ("horizon",):
            ben = env_adsr(eth if eighth % 2 == 0 else eth, EIGHTH, 0.004, 0.06, 0.5, 0.05)
            if eighth % 2:
                ben *= 0.4
            L[i] += sine(bass_ph) * ben * 0.42 * fade
            R[i] += sine(bass_ph) * ben * 0.42 * fade

        # tremolo fifths (fast AM)
        if sec in ("ride", "showdown", "ride2"):
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            trem_r = (trem_r + rh / SR) % 1.0
            trem_f = (trem_f + fh / SR) % 1.0
            trem = 0.5 + 0.5 * sine(t * 12.0)  # ~12 Hz pick
            gtr = (saw_bl(trem_r) + saw_bl(trem_f)) * trem
            L[i] += drive(gtr, 2.2) * 0.22 * fade
            R[i] += drive(gtr, 2.2) * 0.28 * fade

        # desert pad
        if sec in ("horizon", "wind", "dusk"):
            acc = 0.0
            for vi, nmidi in enumerate(chord):
                pad_ph[vi] = (pad_ph[vi] + midi_hz(nmidi) / SR) % 1.0
                acc += sine(pad_ph[vi])
            L[i] += acc / 3.0 * 0.2 * fade
            R[i] += acc / 3.0 * 0.22 * fade

        # whistle
        if sec in ("ride", "showdown", "ride2", "horizon"):
            nmidi = mel_a[(bar % 4) * 8 + eighth]
            if sec == "showdown":
                nmidi += 12
            hz = midi_hz(nmidi)
            whistle_ph = (whistle_ph + hz / SR) % 1.0
            lenv = env_adsr(eth, EIGHTH * 0.98, 0.03, 0.05, 0.65, 0.1)
            air = 1.0 + 0.05 * sine(t * 6.0)
            wh = flute(whistle_ph) * lenv * air
            wg = 0.35 if sec == "horizon" else 0.55
            L[i] += wh * wg * fade * 0.7
            R[i] += wh * wg * fade

        # harmonica-ish fifth over whistle in showdown
        if sec == "showdown":
            nmidi = chord[2] + 12
            hz = midi_hz(nmidi)
            harm_ph = (harm_ph + hz / SR) % 1.0
            hen = env_adsr(eth, EIGHTH, 0.02, 0.08, 0.4, 0.08)
            L[i] += sine(harm_ph) * hen * 0.16 * fade
            R[i] += sine(harm_ph) * hen * 0.12 * fade

    write_wav(track_path("experiments", "dust_canyon_2min.mp3"), L, R, crunch=700.0)


if __name__ == "__main__":
    main()
