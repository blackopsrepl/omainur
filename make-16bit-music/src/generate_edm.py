#!/usr/bin/env python3
"""2-minute festival-style EDM track. Pure stdlib synthesizer."""
from __future__ import annotations

from paths import track_path

import math
import os
import tempfile
import wave
from array import array

from game_synth import wav_to_mp3

SR = 44100
BPM = 128
BARS = 64  # 2:00 exactly at 128 BPM
BEAT = 60.0 / BPM
BAR = BEAT * 4
DURATION = BAR * BARS
N = int(SR * DURATION)

LUT = 8192
SINE = [math.sin(2.0 * math.pi * i / LUT) for i in range(LUT)]
TWO_PI = 2.0 * math.pi


def sine(phase: float) -> float:
    p = phase % 1.0
    x = p * LUT
    i = int(x) & (LUT - 1)
    f = x - int(x)
    j = (i + 1) & (LUT - 1)
    return SINE[i] + (SINE[j] - SINE[i]) * f


def saw_bl(phase: float) -> float:
    a = 0.0
    p = phase
    for h in range(1, 8):
        a += sine(p * h) / h
    return a * 0.55


def square_bl(phase: float) -> float:
    a = 0.0
    for h in (1, 3, 5, 7, 9):
        a += sine(phase * h) / h
    return a * 0.7


def env_exp(t: float, dur: float, tau: float) -> float:
    if t < 0.0 or t >= dur:
        return 0.0
    return math.exp(-t / tau)


def env_ad(t: float, a: float, d: float) -> float:
    if t < 0.0 or t >= a + d:
        return 0.0
    if t < a:
        return t / a if a > 0 else 1.0
    return 1.0 - (t - a) / d


def env_adsr(t: float, dur: float, a: float, d: float, s: float, r: float) -> float:
    if t < 0.0 or t >= dur:
        return 0.0
    if t < a:
        return (t / a) if a > 0 else 1.0
    if t < a + d:
        return 1.0 + (s - 1.0) * ((t - a) / d)
    if t < dur - r:
        return s
    if r <= 0:
        return s
    return s * max(0.0, 1.0 - (t - (dur - r)) / r)


def midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def clip_soft(x: float) -> float:
    ax = abs(x)
    return x * (27.0 + ax * ax) / (27.0 + 9.0 * ax * ax) if ax < 3.0 else math.copysign(1.0, x)


def one_pole(prev: float, x: float, cutoff: float) -> float:
    alpha = 1.0 - math.exp(-TWO_PI * max(20.0, cutoff) / SR)
    return prev + alpha * (x - prev)


class Noise:
    __slots__ = ("s",)

    def __init__(self, seed: int) -> None:
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return (self.s / 2147483648.0) - 1.0


def add_at(buf: list[float], start: int, src: list[float], gain: float = 1.0) -> None:
    n = len(buf)
    for i, v in enumerate(src):
        j = start + i
        if 0 <= j < n:
            buf[j] += v * gain


def render_kick(length: float = 0.42) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    click_n = int(0.004 * SR)
    rng = Noise(7)
    hp = 0.0
    rest_hz = midi_hz(33)  # A1
    body_ph = 0.0
    sub_ph = 0.0
    for i in range(m):
        t = i / SR
        p_env = math.exp(-t * 22.0)
        freq = rest_hz + 125.0 * p_env
        body_ph = (body_ph + freq / SR) % 1.0
        sub_ph = (sub_ph + rest_hz / SR) % 1.0
        body = sine(body_ph) * math.exp(-t * 7.5)
        sub = sine(sub_ph) * math.exp(-t * 5.5)
        click = 0.0
        if i < click_n:
            n = rng.next()
            hp = 0.96 * hp + 0.04 * n
            click = (n - hp) * (1.0 - i / click_n) * 0.9
        out[i] = body * 1.15 + sub * 0.85 + click
    return out


def render_clap(length: float = 0.28) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(99)
    hp = 0.0
    bp = 0.0
    bursts = (0.0, 0.012, 0.024, 0.041)
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.88 * hp + 0.12 * n
        air = n - hp
        env = 0.0
        for b in bursts:
            dt = t - b
            if dt >= 0:
                env += math.exp(-dt * 55.0) * (1.2 if b == bursts[-1] else 0.7)
        bp = bp + 0.35 * (air * env - bp)
        out[i] = (air * 0.55 + bp * 1.4) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_hat(length: float, bright: float) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(1234 + int(bright * 100))
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = (0.55 + 0.2 * bright) * hp + (0.45 - 0.2 * bright) * n
        air = n - hp
        env = math.exp(-t * (28.0 + (1.0 - bright) * 90.0))
        metallic = sine(8700 * t) * sine(5400 * t) * env * 0.12
        out[i] = air * env * 1.6 + metallic
    peak = max(1e-9, max(abs(x) for x in out))
    g = 0.7 + 0.3 * bright
    return [x / peak * g for x in out]


def render_crash(length: float = 2.4) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(4242)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.82 * hp + 0.18 * n
        air = n - hp
        env = math.exp(-t * 1.7) * (0.4 + 0.6 * math.exp(-t * 8.0))
        shimmer = sine(9000 * t + 0.5 * sine(13 * t)) * env * 0.08
        out[i] = air * env + shimmer
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_riser(length: float, seed: int = 777) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(seed)
    hp = 0.0
    lp = 0.0
    for i in range(m):
        t = i / SR
        p = t / length
        n = rng.next()
        hp = 0.90 * hp + 0.10 * n
        air = n - hp
        cut = 400.0 + 9000.0 * (p ** 2)
        lp = one_pole(lp, air, cut)
        sweep = sine((180.0 + 2400.0 * (p ** 2.2)) * t) * (0.15 + 0.5 * p)
        env = (p ** 1.4) * (0.3 + 0.7 * (0.5 - 0.5 * math.cos(min(1.0, p) * math.pi)))
        out[i] = (lp * 0.9 + sweep) * env
    return out


# Chord loop in midi: Am F C G
CHORDS = [
    (57, 60, 64),  # A3 C4 E4
    (53, 57, 60),  # F3 A3 C4
    (48, 52, 55),  # C3 E3 G3
    (55, 59, 62),  # G3 B3 D4
]
ROOTS = [45, 41, 36, 43]  # A2 F2 C2 G2


def chord_arp_notes(chord: tuple[int, int, int]) -> list[int]:
    r, third, fifth = chord
    return [
        r + 12,
        third + 12,
        fifth + 12,
        r + 24,
        fifth + 12,
        third + 12,
        fifth + 12,
        third + 12,
    ]


def chord_lead_notes(chord: tuple[int, int, int], variation: bool) -> list[int]:
    r, third, fifth = chord
    if not variation:
        return [
            fifth + 12,
            r + 12,
            third + 12,
            r + 12,
            fifth + 12,
            third + 12,
            r + 24,
            fifth + 12,
        ]
    return [
        r + 24,
        fifth + 12,
        third + 24,
        fifth + 12,
        r + 24,
        third + 12,
        fifth + 24,
        fifth + 12,
    ]


def section_of(bar: int) -> str:
    if bar < 8:
        return "intro"
    if bar < 16:
        return "groove"
    if bar < 24:
        return "build1"
    if bar < 40:
        return "drop1"
    if bar < 48:
        return "break"
    if bar < 56:
        return "build2"
    if bar < 62:
        return "drop2"
    return "outro"


def mix_for(bar: int, pos_in_bar: float) -> tuple[str, float, float, float, float, float, bool, bool]:
    """Returns section, pad_cut, pad_g, bass_g, arp_g, lead_g, drop_sec, lead_var."""
    sec = section_of(bar)
    pbar = pos_in_bar / BAR
    if sec == "intro":
        pad_cut = 380.0 + 220.0 * math.sin(TWO_PI * (bar + pbar) / 8.0)
        return sec, pad_cut, 0.22, 0.0, 0.0, 0.0, False, False
    if sec == "groove":
        return sec, 900.0, 0.26, 0.55, 0.12, 0.0, False, False
    if sec == "build1":
        p = (bar - 16 + pbar) / 8.0
        return sec, 700.0 + 2000.0 * p, 0.28 + 0.08 * p, 0.6 + 0.25 * p, 0.14 + 0.12 * p, 0.14 * p, False, False
    if sec == "drop1":
        var = bar >= 32
        wobble = 2800.0 + 900.0 * math.sin(TWO_PI * pos_in_bar / BEAT * 0.5)
        return sec, wobble, 0.33, 0.95, 0.22 + (0.08 if var else 0.0), 0.72 + (0.08 if var else 0.0), True, var
    if sec == "break":
        pad_cut = 1100.0 + 400.0 * math.sin(TWO_PI * (bar + pbar) / 8.0)
        bass = 0.18 if bar < 44 else 0.32
        return sec, pad_cut, 0.42, bass, 0.08, 0.16, False, False
    if sec == "build2":
        p = (bar - 48 + pbar) / 8.0
        return sec, 800.0 + 2400.0 * p, 0.32 + 0.06 * p, 0.65 + 0.28 * p, 0.16 + 0.14 * p, 0.18 * p, False, True
    if sec == "drop2":
        wobble = 3000.0 + 1000.0 * math.sin(TWO_PI * pos_in_bar / BEAT * 0.5)
        return sec, wobble, 0.34, 1.0, 0.3, 0.85, True, True
    fade = 1.0 - (bar - 62 + pbar) / 2.0
    fade = max(0.0, fade)
    return sec, 400.0 + 700.0 * fade, 0.22 * fade, 0.45 * fade, 0.08 * fade, 0.28 * fade, False, True


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N

    kick = render_kick()
    clap = render_clap()
    hat_c = render_hat(0.07, 0.35)
    hat_o = render_hat(0.22, 0.85)
    crash = render_crash()
    crash_rev = list(reversed(crash))

    sc = [1.0] * N
    kick_on = [False] * (BARS * 4)

    def place_kick(beat: int, gain: float) -> None:
        if gain <= 0.01:
            return
        start = int(beat * BEAT * SR)
        add_at(L, start, kick, 0.95 * gain)
        add_at(R, start, kick, 0.95 * gain)
        kick_on[beat] = True
        length = int(0.28 * SR)
        for i in range(length):
            j = start + i
            if j >= N:
                break
            duck = 1.0 - 0.78 * math.exp(-(i / SR) * 14.0)
            sc[j] = min(sc[j], duck)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        start = int(t * SR)
        sec = section_of(bar)

        # --- kick ---
        kg = 0.0
        if sec == "intro":
            kg = 0.85
        elif sec == "groove":
            kg = 0.95
        elif sec == "build1":
            kg = 1.0
        elif sec == "drop1" or sec == "drop2":
            kg = 1.0
        elif sec == "break":
            if bar < 44:
                kg = 0.75 if b == 0 else 0.0
            else:
                kg = 0.85
        elif sec == "build2":
            kg = 1.0
        elif sec == "outro":
            kg = 0.7 if bar == 62 else 0.35
        place_kick(beat, kg)

        # --- clap on 2 and 4 ---
        cg = 0.0
        if b % 2 == 1:
            if sec == "groove":
                cg = 0.55
            elif sec in ("build1", "build2"):
                cg = 0.7
            elif sec in ("drop1", "drop2"):
                cg = 0.9
            elif sec == "outro" and bar == 62:
                cg = 0.4
        if cg:
            add_at(L, start, clap, 0.72 * cg)
            add_at(R, start, clap, 0.78 * cg)

        # --- hats ---
        hg = 0.0
        sixteenths = False
        if sec == "intro" and bar >= 4:
            hg = 0.18
        elif sec == "groove":
            hg = 0.28
        elif sec in ("build1", "build2"):
            hg = 0.32
            sixteenths = bar % 8 >= 6
        elif sec in ("drop1", "drop2"):
            hg = 0.38
            sixteenths = True
        elif sec == "break" and bar >= 44:
            hg = 0.16
        elif sec == "outro":
            hg = 0.14
        if hg:
            add_at(L, start, hat_c, hg * 0.85)
            add_at(R, start, hat_c, hg)
            off = int((t + BEAT * 0.5) * SR)
            add_at(L, off, hat_c, hg)
            add_at(R, off, hat_c, hg * 0.8)
            if sixteenths:
                for k in (0.25, 0.75):
                    h16 = int((t + BEAT * k) * SR)
                    add_at(L, h16, hat_c, 0.18)
                    add_at(R, h16, hat_c, 0.22)

        if b == 3 and sec in ("groove", "build1", "build2", "drop1", "drop2"):
            og = 0.28 if sec in ("groove", "build1") else 0.4
            add_at(L, start + int(0.5 * BEAT * SR), hat_o, og * 0.9)
            add_at(R, start + int(0.5 * BEAT * SR), hat_o, og)

        # --- snare rolls into drops ---
        roll = 0
        if sec == "build1" and bar == 22 and b == 3:
            roll = 8
        elif sec == "build1" and bar == 23:
            roll = 16 if b >= 2 else 8
        elif sec == "build2" and bar == 54 and b == 3:
            roll = 8
        elif sec == "build2" and bar == 55:
            roll = 16 if b < 2 else 32
        if roll:
            for k in range(roll):
                st = int((t + BEAT * k / roll) * SR)
                g = 0.22 + 0.7 * (k / max(1, roll - 1))
                add_at(L, st, clap, g * 0.55)
                add_at(R, st, clap, g * 0.6)

    # crashes + reverse hits
    def crash_at(bar: int, gain: float) -> None:
        s = int(bar * BAR * SR)
        add_at(L, s, crash, gain)
        add_at(R, s, crash, gain)

    crash_at(0, 0.32)
    crash_at(24, 0.9)
    crash_at(32, 0.5)
    crash_at(40, 0.45)
    crash_at(56, 0.95)
    crash_at(62, 0.4)

    # reverse crash just before each drop
    rev_len = len(crash_rev)
    for bar, gain in ((24, 0.4), (56, 0.5)):
        start = int(bar * BAR * SR) - rev_len
        add_at(L, start, crash_rev, gain)
        add_at(R, start, crash_rev, gain)

    # risers: 4 bars into each drop
    riser1 = render_riser(BAR * 4, 777)
    riser2 = render_riser(BAR * 4, 1337)
    add_at(L, int(20 * BAR * SR), riser1, 0.5)
    add_at(R, int(20 * BAR * SR), riser1, 0.5)
    add_at(L, int(52 * BAR * SR), riser2, 0.7)
    add_at(R, int(52 * BAR * SR), riser2, 0.7)
    # short lift into drop1 second half
    riser_s = render_riser(BAR * 2, 2024)
    add_at(L, int(30 * BAR * SR), riser_s, 0.35)
    add_at(R, int(30 * BAR * SR), riser_s, 0.35)

    pad_lp_l = 0.0
    pad_lp_r = 0.0
    bass_lp = 0.0
    lead_lp_l = 0.0
    lead_lp_r = 0.0
    pluck_lp = 0.0

    pad_ph = [[0.0, 0.0, 0.0] for _ in range(3)]
    bass_ph = 0.0
    sub_ph = 0.0
    lead_ph = [0.0] * 5
    lead_center_ph = 0.0
    arp_ph = 0.0
    pluck_ph = 0.0
    pad_center_ph = [0.0, 0.0, 0.0]
    spark_ph = 0.0

    detune_cents = (-6.0, 0.0, 6.0)
    lead_cents = (-7.0, -3.0, 0.0, 3.0, 7.0)

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos_in_bar = t - bar * BAR
        chord = CHORDS[bar % 4]
        root = ROOTS[bar % 4]

        sec, pad_cut, pad_g, bass_g, arp_g, lead_g, drop_sec, lead_var = mix_for(bar, pos_in_bar)
        duck = sc[i]

        pad_l = 0.0
        pad_r = 0.0
        for vi, note in enumerate(chord):
            base = midi_hz(note)
            pad_center_ph[vi] = (pad_center_ph[vi] + base / SR) % 1.0
            center = sine(pad_center_ph[vi])
            pad_l += center * 0.45
            pad_r += center * 0.45
            for di, cents in enumerate(detune_cents):
                freq = base * (2.0 ** (cents / 1200.0))
                pad_ph[vi][di] = (pad_ph[vi][di] + freq / SR) % 1.0
                s = saw_bl(pad_ph[vi][di])
                if di == 0:
                    pad_l += s
                elif di == 2:
                    pad_r += s
                else:
                    pad_l += s * 0.7
                    pad_r += s * 0.7
        pad_l /= 7.2
        pad_r /= 7.2
        pad_lp_l = one_pole(pad_lp_l, pad_l, pad_cut)
        pad_lp_r = one_pole(pad_lp_r, pad_r, pad_cut)
        L[i] += pad_lp_l * pad_g * duck
        R[i] += pad_lp_r * pad_g * duck

        if bass_g > 0.01:
            eighth = int(pos_in_bar / (BEAT * 0.5))
            eighth_t = pos_in_bar - eighth * (BEAT * 0.5)
            offbeat = eighth % 2 == 1
            bass_env = env_exp(eighth_t, BEAT * 0.5, 0.12) if offbeat else env_exp(eighth_t, BEAT * 0.45, 0.18) * 0.35
            if drop_sec:
                bass_env = (
                    env_adsr(eighth_t, BEAT * 0.5, 0.004, 0.05, 0.55, 0.08)
                    if offbeat
                    else env_exp(eighth_t, 0.12, 0.06) * 0.25
                )
            elif sec == "break":
                bass_env = env_exp(eighth_t, BEAT * 0.9, 0.28)

            sub_hz = midi_hz(root)
            mid_hz = midi_hz(root + 12)
            sub_ph = (sub_ph + sub_hz / SR) % 1.0
            bass_ph = (bass_ph + mid_hz / SR) % 1.0
            sub = sine(sub_ph) * 0.95
            mid = saw_bl(bass_ph) * 0.55 + square_bl(bass_ph) * 0.45
            bass_lp = one_pole(bass_lp, mid, 280.0 + (900.0 if drop_sec else 350.0))
            bass = (sub * 0.9 + bass_lp * 0.7) * bass_env * bass_g * duck
            L[i] += bass
            R[i] += bass

        if arp_g > 0.01:
            step = int(pos_in_bar / (BEAT * 0.25)) % 8
            step_t = pos_in_bar - int(pos_in_bar / (BEAT * 0.25)) * (BEAT * 0.25)
            note = chord_arp_notes(chord)[step]
            if lead_var and step in (0, 4):
                note += 12
            hz = midi_hz(note)
            arp_ph = (arp_ph + hz / SR) % 1.0
            pluck_ph = (pluck_ph + hz / SR) % 1.0
            aenv = env_ad(step_t, 0.004, 0.16)
            pl = saw_bl(arp_ph) * 0.45 + sine(pluck_ph) * 0.7
            pluck_lp = one_pole(pluck_lp, pl, 1800.0 + 1400.0 * aenv)
            val = pluck_lp * aenv * arp_g * duck
            if step % 2 == 0:
                L[i] += val * 0.85
                R[i] += val * 0.45
            else:
                L[i] += val * 0.45
                R[i] += val * 0.85

        if lead_g > 0.01:
            if drop_sec:
                st = int(pos_in_bar / (BEAT * 0.5))
                st_t = pos_in_bar - st * (BEAT * 0.5)
                seq = chord_lead_notes(chord, variation=lead_var)
                nhz = midi_hz(seq[st % 8])
                gate = env_adsr(st_t, BEAT * 0.5 * 0.92, 0.006, 0.07, 0.65, 0.08)
            else:
                nhz = midi_hz(chord[2] + 12)
                gate = 0.55 + 0.45 * math.sin(TWO_PI * t / BAR)

            acc_l = 0.0
            acc_r = 0.0
            for li, cents in enumerate(lead_cents):
                freq = nhz * (2.0 ** (cents / 1200.0))
                lead_ph[li] = (lead_ph[li] + freq / SR) % 1.0
                s = saw_bl(lead_ph[li])
                if li < 2:
                    acc_l += s
                elif li > 2:
                    acc_r += s
                else:
                    acc_l += s * 0.6
                    acc_r += s * 0.6
            lead_center_ph = (lead_center_ph + nhz / SR) % 1.0
            center = sine(lead_center_ph)
            acc_l = acc_l / 3.0 + center * 0.55
            acc_r = acc_r / 3.0 + center * 0.55
            lead_cut = 1200.0 + (3800.0 if drop_sec else 900.0) * (0.6 + 0.4 * gate)
            lead_lp_l = one_pole(lead_lp_l, acc_l, lead_cut)
            lead_lp_r = one_pole(lead_lp_r, acc_r, lead_cut)
            L[i] += lead_lp_l * lead_g * gate * duck * 0.85
            R[i] += lead_lp_r * lead_g * gate * duck * 0.85

        if drop_sec:
            spark_hz = midi_hz(chord[2] + 24)
            spark_ph = (spark_ph + spark_hz / SR) % 1.0
            spark = sine(spark_ph)
            sh = env_exp((pos_in_bar % (BEAT * 0.25)), 0.08, 0.03) * 0.04
            L[i] += spark * sh * 0.7
            R[i] += spark * sh

    peak = 1e-9
    for i in range(N):
        peak = max(peak, abs(L[i]), abs(R[i]))
    norm = 0.89 / peak
    out = array("h")
    for i in range(N):
        l = clip_soft(L[i] * norm * 1.05)
        r = clip_soft(R[i] * norm * 1.05)
        mid = (l + r) * 0.5
        side = (l - r) * 0.55
        l = clip_soft(mid + side)
        r = clip_soft(mid - side)
        out.append(int(max(-1.0, min(1.0, l)) * 32000))
        out.append(int(max(-1.0, min(1.0, r)) * 32000))

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    mp3_path = track_path("club", "neon_drop_2min.mp3")
    wav_to_mp3(wav_path, mp3_path)
    print(f"wrote {mp3_path}  duration={N/SR:.2f}s  peak={peak:.3f}")


if __name__ == "__main__":
    main()
