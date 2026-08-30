#!/usr/bin/env python3
"""2-minute dark house / cyberpunk track. Pure stdlib synthesizer."""
from __future__ import annotations

from paths import track_path

import math
import os
import tempfile
import wave
from array import array

from game_synth import wav_to_mp3

SR = 44100
BPM = 124
BARS = 62  # 2:00 exactly at 124 BPM
BEAT = 60.0 / BPM
BAR = BEAT * 4
DURATION = BAR * BARS
N = int(SR * DURATION)
SIXTEENTH = BEAT * 0.25
SWING = 0.16  # delay odd 16ths a little (dirty house shuffle)

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
    for h in range(1, 7):
        a += sine(phase * h) / h
    return a * 0.58


def square_bl(phase: float) -> float:
    a = 0.0
    for h in (1, 3, 5, 7):
        a += sine(phase * h) / h
    return a * 0.72


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


def midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def clip_soft(x: float) -> float:
    ax = abs(x)
    return x * (27.0 + ax * ax) / (27.0 + 9.0 * ax * ax) if ax < 3.0 else math.copysign(1.0, x)


def drive(x: float, amt: float) -> float:
    a = max(0.5, amt)
    return math.tanh(x * a) / math.tanh(a)


def growl(x: float, amt: float) -> float:
    y = drive(x, amt)
    return clip_soft(y + 0.25 * math.sin(y * 2.4))


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


def swing_t(step16: int) -> float:
    t = step16 * SIXTEENTH
    if step16 % 2 == 1:
        t += SIXTEENTH * SWING
    return t


def render_kick() -> list[float]:
    # Short dirty house thud — not a pitched 808, so it won't fight the bass
    m = int(SR * 0.28)
    out = [0.0] * m
    rng = Noise(11)
    hp = 0.0
    ph = 0.0
    click_n = int(0.0035 * SR)
    for i in range(m):
        t = i / SR
        p_env = math.exp(-t * 24.0)
        freq = 50.0 + 95.0 * p_env
        ph = (ph + freq / SR) % 1.0
        body = sine(ph) * math.exp(-t * 11.0)
        grit = 0.0
        if i < click_n:
            n = rng.next()
            hp = 0.94 * hp + 0.06 * n
            grit = (n - hp) * (1.0 - i / click_n)
        sample = body * 1.5 + grit * 0.7
        out[i] = growl(sample, 3.0)
    return out


def render_clap() -> list[float]:
    m = int(SR * 0.22)
    out = [0.0] * m
    rng = Noise(201)
    hp = 0.0
    bursts = (0.0, 0.011, 0.023)
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.86 * hp + 0.14 * n
        air = n - hp
        env = 0.0
        for b in bursts:
            dt = t - b
            if dt >= 0:
                env += math.exp(-dt * 70.0) * (1.3 if b == bursts[-1] else 0.55)
        out[i] = air * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [drive(x / peak, 1.8) for x in out]


def render_hat(length: float, bright: float) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(900 + int(bright * 50))
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = (0.50 + 0.25 * bright) * hp + (0.50 - 0.25 * bright) * n
        air = n - hp
        env = math.exp(-t * (40.0 + (1.0 - bright) * 110.0))
        out[i] = air * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak * (0.65 + 0.25 * bright) for x in out]


def render_rim() -> list[float]:
    m = int(SR * 0.09)
    out = [0.0] * m
    rng = Noise(44)
    ph = 0.0
    hp = 0.0
    for i in range(m):
        t = i / SR
        env = math.exp(-t * 55.0)
        ph = (ph + 1850.0 / SR) % 1.0
        n = rng.next()
        hp = 0.7 * hp + 0.3 * n
        out[i] = (sine(ph) * 0.45 + (n - hp) * 0.7) * env
    return out


def render_tick() -> list[float]:
    # Cyber metallic tick
    m = int(SR * 0.06)
    out = [0.0] * m
    for i in range(m):
        t = i / SR
        env = math.exp(-t * 90.0)
        out[i] = sine(4200 * t) * sine(2700 * t) * env
    return out


def render_crash(length: float = 2.6) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(7777)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.84 * hp + 0.16 * n
        env = math.exp(-t * 1.5) * (0.35 + 0.65 * math.exp(-t * 7.0))
        out[i] = (n - hp) * env
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_riser(length: float, seed: int) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(seed)
    hp = 0.0
    lp = 0.0
    for i in range(m):
        t = i / SR
        p = t / length
        n = rng.next()
        hp = 0.91 * hp + 0.09 * n
        air = n - hp
        cut = 250.0 + 7000.0 * (p ** 2.1)
        lp = one_pole(lp, air, cut)
        siren_hz = 180.0 + 1400.0 * (p ** 1.8)
        siren = sine(siren_hz * t) * (0.12 + 0.35 * p)
        env = p ** 1.35
        out[i] = (lp * 0.85 + siren) * env
    return out


# 8-bar loop: Am | Am | G | G | F | F | E | E
# Andalusian cadence — dark, but every move sits for human ears
PROGRESSION = [
    ((57, 60, 64), 45, False),  # Am / A2
    ((57, 60, 64), 45, False),
    ((55, 59, 62), 43, True),   # G / G2
    ((55, 59, 62), 43, True),
    ((53, 57, 60), 41, True),   # F / F2
    ((53, 57, 60), 41, True),
    ((52, 56, 59), 40, True),   # E / E2
    ((52, 56, 59), 40, True),
]


def harmony(bar: int) -> tuple[tuple[int, int, int], int, bool]:
    return PROGRESSION[bar % 8]


def section_of(bar: int) -> str:
    if bar < 8:
        return "intro"
    if bar < 16:
        return "groove"
    if bar < 24:
        return "build1"
    if bar < 40:
        return "peak1"
    if bar < 48:
        return "break"
    if bar < 54:
        return "build2"
    if bar < 60:
        return "peak2"
    return "outro"


def mix_for(bar: int, pos_in_bar: float) -> tuple[float, float, float, float, float, float, bool]:
    """pad_cut, pad_g, acid_g, stab_g, drone_g, siren_g, peak."""
    sec = section_of(bar)
    pbar = pos_in_bar / BAR
    if sec == "intro":
        return 280.0, 0.18, 0.0, 0.0, 0.22, 0.04, False
    if sec == "groove":
        return 420.0, 0.20, 0.72, 0.18, 0.22, 0.03, False
    if sec == "build1":
        p = (bar - 16 + pbar) / 8.0
        return 500.0 + 900.0 * p, 0.22, 0.8 + 0.15 * p, 0.22 + 0.1 * p, 0.2, 0.06 + 0.1 * p, False
    if sec == "peak1":
        hot = bar >= 32
        return 700.0, 0.18, 1.05 if hot else 0.92, 0.34 if hot else 0.28, 0.16, 0.05, True
    if sec == "break":
        return 900.0, 0.34, 0.12, 0.08, 0.28, 0.16, False
    if sec == "build2":
        p = (bar - 48 + pbar) / 6.0
        return 550.0 + 1100.0 * p, 0.24, 0.85 + 0.2 * p, 0.2 + 0.12 * p, 0.18, 0.1 + 0.12 * p, False
    if sec == "peak2":
        return 780.0, 0.16, 1.12, 0.38, 0.14, 0.06, True
    fade = max(0.0, 1.0 - (bar - 60 + pbar) / 2.0)
    return 350.0, 0.16 * fade, 0.35 * fade, 0.08 * fade, 0.2 * fade, 0.08 * fade, False


# Acid 16th intervals relative to current root. Stays chord-safe:
# minor: 0, m3, 5, b7, oct   major: 0, M3, 5, oct
ACID_MIN = [0, 0, 12, 0, 0, 7, 12, 3, 0, 12, 10, 0, 7, 0, 12, 3]
ACID_MAJ = [0, 0, 12, 0, 0, 7, 12, 4, 0, 12, 7, 0, 4, 0, 12, 7]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N

    kick = render_kick()
    clap = render_clap()
    hat_c = render_hat(0.055, 0.25)
    hat_o = render_hat(0.18, 0.7)
    rim = render_rim()
    tick = render_tick()
    crash = render_crash()
    crash_rev = list(reversed(crash))

    sc = [1.0] * N

    def duck_at(start: int) -> None:
        length = int(0.22 * SR)
        for i in range(length):
            j = start + i
            if j >= N:
                break
            sc[j] = min(sc[j], 1.0 - 0.72 * math.exp(-(i / SR) * 16.0))

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        start = int(t * SR)
        sec = section_of(bar)

        kg = 0.0
        if sec == "intro":
            kg = 0.9
        elif sec in ("groove", "build1", "build2", "peak1", "peak2"):
            kg = 1.0
        elif sec == "break":
            kg = 0.7 if (bar >= 44 and b == 0) or (bar >= 46) else (0.55 if b == 0 else 0.0)
        elif sec == "outro":
            kg = 0.55 if bar == 60 else 0.28
        if kg:
            add_at(L, start, kick, 1.05 * kg)
            add_at(R, start, kick, 1.05 * kg)
            duck_at(start)

        # dry clap on 2 and 4
        cg = 0.0
        if b % 2 == 1:
            if sec == "groove":
                cg = 0.42
            elif sec in ("build1", "build2"):
                cg = 0.55
            elif sec in ("peak1", "peak2"):
                cg = 0.72
            elif sec == "outro" and bar == 60:
                cg = 0.3
        if cg:
            add_at(L, start, clap, 0.62 * cg)
            add_at(R, start, clap, 0.7 * cg)

        # hats with swing
        hg = 0.0
        busy = False
        if sec == "intro" and bar >= 4:
            hg = 0.16
        elif sec == "groove":
            hg = 0.24
        elif sec in ("build1", "build2"):
            hg = 0.28
            busy = True
        elif sec in ("peak1", "peak2"):
            hg = 0.32
            busy = True
        elif sec == "break" and bar >= 44:
            hg = 0.12
        elif sec == "outro":
            hg = 0.1
        if hg:
            for k in range(4):
                if k % 2 == 1 and not busy:
                    continue
                delay = swing_t(k)
                hs = int((t + delay) * SR)
                g = hg * (0.55 if k % 2 else 1.0)
                add_at(L, hs, hat_c, g * (0.8 if k % 2 == 0 else 1.0))
                add_at(R, hs, hat_c, g * (1.0 if k % 2 == 0 else 0.75))

        if b == 3 and sec in ("groove", "build1", "build2", "peak1", "peak2"):
            add_at(L, int((t + BEAT * 0.5) * SR), hat_o, 0.22)
            add_at(R, int((t + BEAT * 0.5) * SR), hat_o, 0.28)

        # industrial rim on the last 16th of the beat during peaks
        if sec in ("peak1", "peak2", "groove", "build1") and b in (1, 3):
            rs = int((t + swing_t(2)) * SR)
            add_at(L, rs, rim, 0.22)
            add_at(R, rs, rim, 0.18)

        # cyber ticks
        if sec in ("peak1", "peak2", "build2") and b == 2:
            ts = int((t + swing_t(1)) * SR)
            add_at(L, ts, tick, 0.16)
            add_at(R, ts, tick, 0.28)

        # snare rolls into peaks
        roll = 0
        if sec == "build1" and bar == 23:
            roll = 8 if b < 2 else 16
        elif sec == "build2" and bar == 53:
            roll = 16 if b < 2 else 32
        if roll:
            for k in range(roll):
                st = int((t + BEAT * k / roll) * SR)
                g = 0.2 + 0.7 * (k / max(1, roll - 1))
                add_at(L, st, clap, g * 0.5)
                add_at(R, st, clap, g * 0.55)

    def crash_at(bar: int, gain: float) -> None:
        s = int(bar * BAR * SR)
        add_at(L, s, crash, gain)
        add_at(R, s, crash, gain)

    crash_at(0, 0.28)
    crash_at(16, 0.22)
    crash_at(24, 0.7)
    crash_at(32, 0.4)
    crash_at(40, 0.35)
    crash_at(54, 0.8)
    crash_at(60, 0.3)

    for bar, gain in ((24, 0.35), (54, 0.45)):
        start = int(bar * BAR * SR) - len(crash_rev)
        add_at(L, start, crash_rev, gain)
        add_at(R, start, crash_rev, gain)

    riser1 = render_riser(BAR * 4, 303)
    riser2 = render_riser(BAR * 4, 808)
    add_at(L, int(20 * BAR * SR), riser1, 0.48)
    add_at(R, int(20 * BAR * SR), riser1, 0.48)
    add_at(L, int(50 * BAR * SR), riser2, 0.62)
    add_at(R, int(50 * BAR * SR), riser2, 0.62)

    # --- tonal / acid / atmosphere ---
    pad_lp_l = 0.0
    pad_lp_r = 0.0
    drone_ph = 0.0
    pad_ph = [[0.0, 0.0] for _ in range(3)]
    pad_center = [0.0, 0.0, 0.0]
    acid_ph = 0.0
    acid_sq = 0.0
    acid_low = 0.0
    acid_band = 0.0
    stab_ph = [0.0, 0.0, 0.0]
    stab_lp = 0.0
    siren_ph = 0.0
    sub_ph = 0.0
    reese_ph_a = 0.0
    reese_ph_b = 0.0
    reese_lp = 0.0
    air_lp = 0.0
    air_rng = Noise(9991)

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos_in_bar = t - bar * BAR
        chord, root, is_maj = harmony(bar)
        pad_cut, pad_g, acid_g, stab_g, drone_g, siren_g, peak = mix_for(bar, pos_in_bar)
        duck = sc[i]
        sec = section_of(bar)

        # dark pad (low, sine-heavy)
        pad_l = 0.0
        pad_r = 0.0
        for vi, note in enumerate(chord):
            # drop an octave for gloom
            base = midi_hz(note - 12)
            pad_center[vi] = (pad_center[vi] + base / SR) % 1.0
            c = sine(pad_center[vi])
            pad_l += c * 0.7
            pad_r += c * 0.7
            for di, cents in enumerate((-4.0, 4.0)):
                freq = base * (2.0 ** (cents / 1200.0))
                pad_ph[vi][di] = (pad_ph[vi][di] + freq / SR) % 1.0
                s = saw_bl(pad_ph[vi][di]) * 0.35 + sine(pad_ph[vi][di]) * 0.65
                if di == 0:
                    pad_l += s
                else:
                    pad_r += s
        pad_l /= 5.0
        pad_r /= 5.0
        pad_lp_l = one_pole(pad_lp_l, pad_l, pad_cut)
        pad_lp_r = one_pole(pad_lp_r, pad_r, pad_cut)
        L[i] += pad_lp_l * pad_g * duck
        R[i] += pad_lp_r * pad_g * duck

        # sub drone on root
        if drone_g > 0.01:
            sub_hz = midi_hz(root)
            drone_ph = (drone_ph + sub_hz / SR) % 1.0
            sub_ph = (sub_ph + (sub_hz * 0.5) / SR) % 1.0
            drone = sine(drone_ph) * 0.7 + sine(sub_ph) * 0.35
            L[i] += drone * drone_g * duck * 0.55
            R[i] += drone * drone_g * duck * 0.55

        # acid bass — 16ths, low and driven so it growls instead of screaming
        if acid_g > 0.01:
            step = int(pos_in_bar / SIXTEENTH) % 16
            local = pos_in_bar - step * SIXTEENTH
            if step % 2 == 1:
                step_t = local - SIXTEENTH * SWING
            else:
                step_t = local
            if step_t < 0:
                aenv = 0.0
                cutoff = 140.0
            else:
                aenv = math.exp(-step_t * 8.0) if step_t < SIXTEENTH else 0.0
                accent = 1.3 if step in (0, 4, 10, 14) else 1.0
                aenv *= accent
                cutoff = 110.0 + (950.0 if peak else 620.0) * aenv
            pat = ACID_MAJ if is_maj else ACID_MIN
            hz = midi_hz(root + pat[step])
            acid_ph = (acid_ph + hz / SR) % 1.0
            acid_sq = (acid_sq + hz / SR) % 1.0
            raw = square_bl(acid_ph) * 0.55 + saw_bl(acid_sq) * 0.55
            f = 2.0 * math.sin(math.pi * min(cutoff, 5000.0) / SR)
            f = min(f, 0.9)
            res = 0.76 if peak else 0.64
            q = 0.28 + (1.0 - res) * 0.5
            acid_low += f * acid_band
            high = raw - acid_low - q * acid_band
            acid_band += f * high
            filthy = growl(acid_low * 1.55, 4.2 if peak else 3.2)
            L[i] += filthy * aenv * acid_g * duck * 0.9
            R[i] += filthy * aenv * acid_g * duck * 0.9

            # reese under the acid — two low saws a few cents apart = the growl
            rh = midi_hz(root)
            reese_ph_a = (reese_ph_a + rh * (2.0 ** (-5.0 / 1200.0)) / SR) % 1.0
            reese_ph_b = (reese_ph_b + rh * (2.0 ** (5.0 / 1200.0)) / SR) % 1.0
            reese_raw = saw_bl(reese_ph_a) + saw_bl(reese_ph_b) + sine(reese_ph_a) * 0.8
            reese_lp = one_pole(reese_lp, reese_raw, 240.0 if peak else 170.0)
            reese = growl(reese_lp * 0.7, 3.6)
            rg = 0.55 if peak else 0.4
            L[i] += reese * rg * acid_g * duck
            R[i] += reese * rg * acid_g * duck

        # chord stabs — short, dirty, on 1 and 3 in peaks, offbeats in groove
        if stab_g > 0.01:
            eighth = int(pos_in_bar / (BEAT * 0.5))
            eighth_t = pos_in_bar - eighth * (BEAT * 0.5)
            hit = False
            if peak:
                hit = True  # offbeat house stabs every 8th, gated
            elif sec in ("groove", "build1", "build2"):
                hit = eighth % 2 == 0 and (bar % 2 == 0 or sec != "groove")
            elif sec == "break":
                hit = eighth == 0
            if hit:
                stenv = env_ad(eighth_t, 0.004, 0.14 if peak else 0.22)
            else:
                stenv = 0.0
            acc = 0.0
            for vi, note in enumerate(chord):
                hz = midi_hz(note + (12 if peak else 0))
                stab_ph[vi] = (stab_ph[vi] + hz / SR) % 1.0
                acc += saw_bl(stab_ph[vi]) + sine(stab_ph[vi]) * 0.4
            acc /= 3.0
            stab_lp = one_pole(stab_lp, acc, 900.0 + 700.0 * stenv)
            val = growl(stab_lp, 2.6) * stenv * stab_g * duck
            L[i] += val * 0.7
            R[i] += val * 0.85

        # cyber siren — A3 drifting toward G3 (whole step, in the cadence)
        if siren_g > 0.01:
            lfo = 0.5 + 0.5 * math.sin(TWO_PI * t / (BAR * 4))
            hz = midi_hz(57 - 2.0 * lfo)
            siren_ph = (siren_ph + hz / SR) % 1.0
            tone = sine(siren_ph) * (0.6 + 0.4 * sine(t * 0.25))
            L[i] += tone * siren_g * 0.12
            R[i] += tone * siren_g * 0.18

        # room grit / analog hiss, filtered
        n = air_rng.next()
        air_lp = one_pole(air_lp, n, 900.0 if peak else 500.0)
        hiss = air_lp * (0.03 if peak else 0.02)
        L[i] += hiss
        R[i] += hiss * 0.9

    peak_v = 1e-9
    for i in range(N):
        peak_v = max(peak_v, abs(L[i]), abs(R[i]))
    norm = 0.86 / peak_v
    out = array("h")
    for i in range(N):
        l = drive(L[i] * norm * 1.08, 1.6)
        r = drive(R[i] * norm * 1.08, 1.6)
        mid = (l + r) * 0.5
        side = (l - r) * 0.48  # a bit more mono / club
        l = clip_soft(mid + side)
        r = clip_soft(mid - side)
        out.append(int(max(-1.0, min(1.0, l)) * 31800))
        out.append(int(max(-1.0, min(1.0, r)) * 31800))

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    mp3_path = track_path("club", "chrome_cellar_2min.mp3")
    wav_to_mp3(wav_path, mp3_path)
    print(f"wrote {mp3_path}  duration={N/SR:.2f}s  peak={peak_v:.3f}")


if __name__ == "__main__":
    main()
