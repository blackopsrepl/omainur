#!/usr/bin/env python3
"""Render the make-16bit-music synth voices as anchor WAVs for the omainur pack.

Each voice is the game_synth oscillator code, rendered at exact MIDI notes
(the anchor per track role) and 16-bit quantized, so track pitch + per-note
offsets land every note on its intended scale degree.
"""
from __future__ import annotations

import math
import struct
import wave

SR = 44100
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


def square_bl(phase: float) -> float:
    a = 0.0
    for h in (1, 3, 5, 7):
        a += sine(phase * h) / h
    return a * 0.72


def tri(phase: float) -> float:
    a = 0.0
    s = 1.0
    for h in (1, 3, 5, 7):
        a += s * sine(phase * h) / (h * h)
        s = -s
    return a * 0.95


def midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def env_adsr(t: float, dur: float, a: float, d: float, s: float, r: float) -> float:
    if t < 0.0 or t >= dur:
        return 0.0
    if t < a:
        return t / a if a else 1.0
    if t < a + d:
        return 1.0 + (s - 1.0) * ((t - a) / d)
    if t < dur - r:
        return s
    if r <= 0:
        return s
    return s * max(0.0, 1.0 - (t - (dur - r)) / r)


def quantize(x: float, q: float = 768.0) -> float:
    return round(x * q) / q


def one_pole(prev: float, x: float, cutoff: float) -> float:
    alpha = 1.0 - math.exp(-TWO_PI * max(20.0, cutoff) / SR)
    return prev + alpha * (x - prev)


def write_wav(path, data, rate=SR):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for x in data:
            frames += struct.pack("<h", int(max(-1.0, min(1.0, x)) * 31000))
        w.writeframes(bytes(frames))


def render_pulse(midi: int, dur: float) -> list[float]:
    """The Gator lead: pulse + square chorus + sine, lowpassed, ~3 cent detune."""
    hz = midi_hz(midi)
    ph = ph2 = lp = 0.0
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        ph = (ph + hz / SR) % 1.0
        ph2 = (ph2 + hz * 1.002 / SR) % 1.0
        lenv = env_adsr(t, dur, 0.006, 0.04, 0.75, 0.06)
        raw = (square_bl(ph) - 0.5 * square_bl(ph * 2.0)) * 0.7 + square_bl(ph2) * 0.25 + sine(ph) * 0.35
        lp = one_pole(lp, raw, 3200.0)
        out.append(quantize(lp * lenv * 0.72))
    return out


def render_tri_bass(midi: int, dur: float) -> list[float]:
    """The Gator bass: triangle + sub sine + a bit of square."""
    hz = midi_hz(midi)
    ph = ph2 = 0.0
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        ph = (ph + hz / SR) % 1.0
        ph2 = (ph2 + hz * 0.5 / SR) % 1.0
        benv = env_adsr(t, dur, 0.004, 0.03, 0.7, 0.04)
        b = tri(ph) * 0.7 + sine(ph2) * 0.5 + square_bl(ph) * 0.15
        out.append(quantize(b * benv * 0.85))
    return out


def render_rhodes(midi: int, dur: float) -> list[float]:
    """Rhodes-ish bell voice for stabs and pads."""
    hz = midi_hz(midi)
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 1.6)
        v = sine(hz * t) * 0.55 + sine(2.0 * hz * t) * 0.2 + sine(3.01 * hz * t) * 0.1
        out.append(quantize(v * env * 0.6))
    return out


def render_pluck(midi: int, dur: float) -> list[float]:
    """Short sine pluck for arps and sparkle."""
    hz = midi_hz(midi)
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 9.0)
        out.append(quantize(sine(hz * t) * env * 0.6))
    return out


class Noise:
    """The LCG noise from game_synth."""

    def __init__(self, seed: int) -> None:
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return (self.s / 2147483648.0) - 1.0


def render_kick() -> list[float]:
    m = int(SR * 0.16)
    out = [0.0] * m
    ph = 0.0
    rng = Noise(3)
    for i in range(m):
        t = i / SR
        freq = 68.0 + 95.0 * math.exp(-t * 38.0)
        ph = (ph + freq / SR) % 1.0
        ck = rng.next() * math.exp(-t * 220.0) * 0.5
        out.append(sine(ph) * math.exp(-t * 16.0) + ck)
    return out


def render_snare() -> list[float]:
    m = int(SR * 0.16)
    out = [0.0] * m
    rng = Noise(21)
    hp = 0.0
    ph = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.78 * hp + 0.22 * n
        ph = (ph + 190.0 / SR) % 1.0
        env = math.exp(-t * 24.0)
        out.append((n - hp) * env * 1.25 + sine(ph) * math.exp(-t * 30.0) * 0.4)
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_hat(closed: bool) -> list[float]:
    m = int(SR * (0.04 if closed else 0.15))
    out = [0.0] * m
    rng = Noise(80 if closed else 81)
    hp = 0.0
    k = 75.0 if closed else 16.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.55 * hp + 0.45 * n
        out.append((n - hp) * math.exp(-t * k))
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_clap() -> list[float]:
    m = int(SR * 0.12)
    out = [0.0] * m
    rng = Noise(7)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.7 * hp + 0.3 * n
        burst = math.exp(-((t % 0.01) * 300.0))
        env = math.exp(-t * 28.0)
        out.append((n - hp) * burst * env)
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def main() -> None:
    import os
    import sys

    outdir = sys.argv[1] if len(sys.argv) > 1 else "anchors"
    os.makedirs(outdir, exist_ok=True)

    for name, data in {
        "omainur_kick": render_kick(),
        "omainur_snare": render_snare(),
        "omainur_hat_closed": render_hat(True),
        "omainur_hat_open": render_hat(False),
        "omainur_clap": render_clap(),
    }.items():
        write_wav(os.path.join(outdir, f"{name}.wav"), data)

    # Anchors: the exact MIDI note each role's sample is rendered at.
    # File names MUST equal the generator's sample names. The "omainur_" prefix
    # is the namespace: the app keys user samples on the FILE STEM (directories
    # are stripped), so only a unique file name keeps these from being shadowed
    # by the built-in sounds, which the app resolves FIRST. Anchors:
    # lead 60, bass 36, stab/pad 48, arp 72.
    for base, (render, arg) in {
        "rhodes_tone": (render_pulse, 60),
        "bass_hit": (render_tri_bass, 36),
        "rhodes_chord": (render_rhodes, 48),
        "neon_pad": (render_rhodes, 48),
        "plucks": (render_pluck, 72),
    }.items():
        wav = render(arg, {"rhodes_tone": 0.4, "bass_hit": 0.6, "rhodes_chord": 1.2, "neon_pad": 2.0, "plucks": 0.3}[base])
        write_wav(os.path.join(outdir, f"omainur_{base}.wav"), wav)
    print(f"anchors written to {outdir}/")


if __name__ == "__main__":
    main()
