#!/usr/bin/env python3
"""Hex Breach — 16-bit terminal exploit. G#m E C#m F#, modem handshake, seek groove."""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR, Noise, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_bell, render_crash, render_hat, render_kick, render_snare, sine,
    square_bl, tri, write_wav,
)

BPM = 134
BARS = 67  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)
TWO_PI = 2.0 * math.pi

# G# natural minor. A# (46/70) sits on F# as its 3rd.
GSM = ((44, 47, 51), 32)  # G# B D#
E_ = ((40, 44, 47), 28)   # E G# B
CSM = ((37, 40, 44), 25)  # C# E G#
FS = ((42, 46, 49), 30)   # F# A# C#


def harmony(bar: int):
    return (GSM, E_, CSM, FS)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "handshake"
    if bar < 12:
        return "prompt"
    if bar < 28:
        return "breach"
    if bar < 36:
        return "firewall"
    if bar < 52:
        return "root"
    if bar < 60:
        return "dump"
    if bar < 64:
        return "root2"
    return "logout"


# Teletype: holds + lots of rest. A# (70) only over F#.
MEL_A = [
    68, 0, 0, 63, 66, 0, 59, 0,   # G#    D# F#  B
    64, 64, 0, 59, 56, 0, 59, 64,  # E E   B G#  B E
    61, 0, 64, 68, 0, 64, 61, 0,   # C#  E G#  E C#
    66, 70, 66, 0, 61, 66, 70, 0,  # F# A# F#  C# F# A#
]
MEL_B = [
    80, 0, 68, 63, 0, 66, 68, 0,   # G#6  G# D#  F# G#
    76, 71, 0, 64, 71, 76, 0, 71,  # E B  E B E  B
    73, 0, 68, 64, 68, 0, 73, 76,  # C#  G# E G#  C# E
    70, 66, 61, 0, 66, 70, 73, 70,  # A# F# C#  F# A# C# A#
]

BASS = {
    32: [12, 0, 12, 0, 7, 0, 10, 12],  # G#: offbeat oct, 5, b7
    28: [0, 12, 4, 7, 12, 0, 7, 4],    # E: G# is 4
    25: [12, 0, 3, 7, 0, 12, 7, 3],    # C#m: E is 3
    30: [0, 0, 4, 7, 12, 10, 7, 4],    # F#: A# is 4, E is 10
}

# Disk-seek 16ths (1 = click). Not a hat grid.
SEEK = [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1]


def render_seek() -> list[float]:
    m = int(SR * 0.028)
    out = [0.0] * m
    rng = Noise(313)
    ph = 0.0
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.5 * hp + 0.5 * n
        ph = (ph + 3100.0 / SR) % 1.0
        env = math.exp(-t * 120.0)
        out[i] = ((n - hp) * 0.65 + sine(ph) * 0.4) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_connect() -> list[float]:
    m = int(SR * 0.35)
    out = [0.0] * m
    rng = Noise(1200)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.62 * hp + 0.38 * n
        env = math.exp(-t * 8.0) * min(1.0, t / 0.01)
        out[i] = (n - hp) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_modem(hi: float, lo: float, length: float) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    ph = 0.0
    bit = int(SR * 0.04)
    for i in range(m):
        hz = midi_hz(hi if (i // bit) % 2 == 0 else lo)
        ph = (ph + hz / SR) % 1.0
        env = 0.7 if i < m - int(0.04 * SR) else max(0.0, 1.0 - (i - (m - int(0.04 * SR))) / (0.04 * SR))
        out[i] = square_bl(ph) * env * 0.55
    return out


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.11, 0.62)
    snare = render_snare(0.08, 260.0)
    hat_c = render_hat(True)
    crash = render_crash(1.1)
    seek = render_seek()
    connect = render_connect()
    modem = render_modem(68.0, 63.0, BAR * 2)
    chime = render_bell(midi_hz(68), 1.8)

    add_at(L, 0, modem, 0.55)
    add_at(R, 0, modem, 0.48)
    add_at(L, int(2 * BAR * SR), modem, 0.35)
    add_at(R, int(2 * BAR * SR + 0.02 * SR), modem, 0.42)
    add_at(L, int(int(3.5 * BAR * SR)), connect, 0.55)
    add_at(R, int(int(3.5 * BAR * SR)), connect, 0.6)
    add_at(L, int(36 * BAR * SR), chime, 0.4)
    add_at(R, int(36 * BAR * SR), chime, 0.35)
    add_at(L, int(64 * BAR * SR), modem, 0.28)
    add_at(R, int(64 * BAR * SR), modem, 0.32)
    add_at(L, int(64 * BAR * SR), connect, 0.25)
    add_at(R, int(64 * BAR * SR), connect, 0.22)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "handshake":
            if bar == 3 and b == 3:
                for k in range(4):
                    add_at(L, int((t + SIX * k) * SR), seek, 0.25 + 0.15 * k)
                    add_at(R, int((t + SIX * k) * SR), seek, 0.2 + 0.15 * k)
            continue

        if sec == "logout":
            if b == 0:
                add_at(L, start, kick, 0.4)
                add_at(R, start, kick, 0.4)
            continue

        if sec == "dump":
            if b == 0:
                add_at(L, start, kick, 0.5)
                add_at(R, start, kick, 0.5)
            for k in range(4):
                if SEEK[(b * 4 + k) % 16]:
                    add_at(L, int((t + SIX * k) * SR), seek, 0.22)
                    add_at(R, int((t + SIX * k) * SR), seek, 0.18)
            continue

        if sec == "prompt":
            if b == 0:
                add_at(L, start, kick, 0.7)
                add_at(R, start, kick, 0.7)
            if b == 1:
                add_at(L, int((t + SIX) * SR), kick, 0.35)
                add_at(R, int((t + SIX) * SR), kick, 0.35)
            if b == 3:
                add_at(L, start, snare, 0.45)
                add_at(R, start, snare, 0.5)
            for k in range(4):
                if SEEK[b * 4 + k]:
                    g = 0.28
                    add_at(L, int((t + SIX * k) * SR), seek, g * 0.85)
                    add_at(R, int((t + SIX * k) * SR), seek, g)
            continue

        # exploit groove: kick 1 + 2-e, snare on 4 (enter key), seek mask
        if b == 0:
            add_at(L, start, kick, 0.9)
            add_at(R, start, kick, 0.9)
        if b == 1:
            add_at(L, int((t + SIX) * SR), kick, 0.42)
            add_at(R, int((t + SIX) * SR), kick, 0.42)
        if sec == "firewall" and b == 2:
            add_at(L, int((t + EIGHTH) * SR), kick, 0.38)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.38)
        if b == 3:
            sg = 0.7 if sec in ("firewall", "root2") else 0.55
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.05)
        if sec == "firewall" and b == 1:
            add_at(L, start, snare, 0.35)
            add_at(R, start, snare, 0.32)
        for k in range(4):
            if SEEK[b * 4 + k]:
                g = 0.32 if sec == "firewall" else 0.24
                add_at(L, int((t + SIX * k) * SR), seek, g * 0.8)
                add_at(R, int((t + SIX * k) * SR), seek, g)
        if sec in ("root", "root2") and b == 3:
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.16)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.2)

    for bar, g in ((4, 0.2), (12, 0.35), (28, 0.45), (36, 0.3), (52, 0.25)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    lead_ph = 0.0
    lead_lp = 0.0
    alarm_ph = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    data_ph = 0.0
    tap1_n = max(1, int(0.037 * SR))
    tap2_n = max(1, int(0.061 * SR))
    tap1 = [0.0] * tap1_n
    tap2 = [0.0] * tap2_n
    t1 = t2 = 0
    air = Noise(9090)
    air_lp = 0.0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "logout":
            fade = max(0.0, 1.0 - (bar - 64 + pos / BAR) / 3.0)

        # CRT hiss
        wn = air.next()
        air_lp = one_pole(air_lp, wn, 900.0)
        hg = 0.03 if sec in ("handshake", "dump", "logout") else 0.012
        L[i] += air_lp * hg * fade
        R[i] += air_lp * hg * 0.8 * fade

        if sec not in ("handshake",):
            rel = BASS[root][ei]
            hz = midi_hz(root + rel)
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH * 0.72, 0.002, 0.02, 0.28, 0.04)
            raw = square_bl(bass_ph) * 0.5 + sine(bass2) * 0.45 + tri(bass_ph) * 0.15
            bass = drive(raw, 2.2)
            bg = 0.7 if sec == "prompt" else 0.54
            if sec == "dump":
                bg = 0.62
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        if sec in ("handshake", "firewall", "logout"):
            acc = 0.0
            for vi, nm in enumerate(chord):
                pad_ph[vi] = (pad_ph[vi] + midi_hz(nm) / SR) % 1.0
                acc += sine(pad_ph[vi])
            pg = 0.18 if sec == "firewall" else 0.12
            L[i] += acc / 3.0 * pg * fade
            R[i] += acc / 3.0 * pg * fade

        # firewall: G# / D# square trill (not the boss E–G siren)
        if sec == "firewall":
            hz = midi_hz(56.0 if math.sin(TWO_PI * t * 6.0) > 0 else 63.0)
            alarm_ph = (alarm_ph + hz / SR) % 1.0
            al = square_bl(alarm_ph) * 0.07 * fade
            L[i] += al
            R[i] += al * 0.7

        # dump: 16th hex stream (texture, not the hook)
        if sec == "dump":
            step = int(pos / SIX) % 4
            nm = chord[step % 3] + 12
            data_ph = (data_ph + midi_hz(nm) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            denv = env_ad(st, 0.001, 0.04)
            data = pulse_bl(data_ph) * denv * 0.16 * fade
            L[i] += data * (0.5 if step % 2 else 0.9)
            R[i] += data * (0.9 if step % 2 else 0.5)

        lead = 0.0
        if sec in ("breach", "root", "root2"):
            mel = MEL_B if sec in ("root", "root2") else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                lenv = env_adsr(eth, EIGHTH * 0.55, 0.001, 0.03, 0.2, 0.04)
                raw = pulse_bl(lead_ph) * 0.7 + square_bl(lead_ph) * 0.25
                lead_lp = one_pole(lead_lp, raw, 3800.0)
                lg = 0.7 if sec == "root2" else 0.62
                lead = lead_lp * lenv * lg * fade
            else:
                lead_ph = (lead_ph + midi_hz(68) / SR) % 1.0
                lead_lp = one_pole(lead_lp, 0.0, 3800.0)

        s1 = tap1[t1]
        s2 = tap2[t2]
        tap1[t1] = lead
        tap2[t2] = lead
        t1 = (t1 + 1) % tap1_n
        t2 = (t2 + 1) % tap2_n
        L[i] += lead * 0.9 + s1 * 0.16
        R[i] += lead * 0.75 + s2 * 0.22

    write_wav(track_path("16bit", "hex_breach_2min.mp3"), L, R, crunch=640.0)


if __name__ == "__main__":
    main()
