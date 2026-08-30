#!/usr/bin/env python3
"""Shared 16-bit-style synth helpers."""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
import wave
from array import array

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


def saw_bl(phase: float) -> float:
    a = 0.0
    for h in range(1, 6):
        a += sine(phase * h) / h
    return a * 0.62


def square_bl(phase: float) -> float:
    a = 0.0
    for h in (1, 3, 5, 7):
        a += sine(phase * h) / h
    return a * 0.72


def pulse_bl(phase: float) -> float:
    return square_bl(phase) - 0.5 * square_bl(phase * 2.0)


def tri(phase: float) -> float:
    a = 0.0
    s = 1.0
    for h in (1, 3, 5, 7):
        a += s * sine(phase * h) / (h * h)
        s = -s
    return a * 0.95


def organ(phase: float) -> float:
    # Hammond-ish: 8' 4' 2 2/3' 2'
    return (
        sine(phase) * 0.55
        + sine(phase * 2) * 0.28
        + sine(phase * 3) * 0.18
        + sine(phase * 4) * 0.12
    )


def flute(phase: float) -> float:
    return sine(phase) * 0.75 + sine(phase * 2) * 0.18 + sine(phase * 3) * 0.07


def midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def env_ad(t: float, a: float, d: float) -> float:
    if t < 0.0 or t >= a + d:
        return 0.0
    if t < a:
        return t / a if a else 1.0
    return 1.0 - (t - a) / d


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


def clip_soft(x: float) -> float:
    ax = abs(x)
    return x * (27.0 + ax * ax) / (27.0 + 9.0 * ax * ax) if ax < 3.0 else math.copysign(1.0, x)


def drive(x: float, amt: float) -> float:
    a = max(0.5, amt)
    return math.tanh(x * a) / math.tanh(a)


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


def render_kick(length: float = 0.16, click: float = 0.5) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    ph = 0.0
    rng = Noise(3)
    for i in range(m):
        t = i / SR
        freq = 68.0 + 95.0 * math.exp(-t * 38.0)
        ph = (ph + freq / SR) % 1.0
        ck = rng.next() * math.exp(-t * 220.0) * click
        out[i] = sine(ph) * math.exp(-t * 16.0) + ck
    return out


def render_snare(length: float = 0.16, tone: float = 190.0) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(21)
    hp = 0.0
    ph = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.78 * hp + 0.22 * n
        ph = (ph + tone / SR) % 1.0
        env = math.exp(-t * 24.0)
        out[i] = (n - hp) * env * 1.25 + sine(ph) * math.exp(-t * 30.0) * 0.4
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_hat(closed: bool = True) -> list[float]:
    m = int(SR * (0.04 if closed else 0.15))
    out = [0.0] * m
    rng = Noise(80 if closed else 81)
    hp = 0.0
    k = 75.0 if closed else 16.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.55 * hp + 0.45 * n
        out[i] = (n - hp) * math.exp(-t * k)
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_tom(hz: float) -> list[float]:
    m = int(SR * 0.2)
    out = [0.0] * m
    ph = 0.0
    for i in range(m):
        t = i / SR
        freq = hz * (1.0 + 0.65 * math.exp(-t * 16.0))
        ph = (ph + freq / SR) % 1.0
        out[i] = sine(ph) * math.exp(-t * 11.0)
    return out


def render_crash(length: float = 1.8) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    rng = Noise(424)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.8 * hp + 0.2 * n
        out[i] = (n - hp) * math.exp(-t * 2.1)
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_bell(hz: float, length: float = 2.4) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    for i in range(m):
        t = i / SR
        env = math.exp(-t * 1.6)
        out[i] = (
            sine(hz * t) * 0.55
            + sine(hz * 2.0 * t) * 0.22
            + sine(hz * 3.01 * t) * 0.12
            + sine(hz * 4.2 * t) * 0.06
        ) * env
    return out


def wav_to_mp3(wav_path: str, mp3_path: str, delete_wav: bool = True) -> None:
    os.makedirs(os.path.dirname(mp3_path) or ".", exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            wav_path,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            mp3_path,
        ],
        check=True,
    )
    if delete_wav:
        os.remove(wav_path)


def write_wav(path: str, L: list[float], R: list[float], crunch: float = 0.0) -> None:
    """Bounce a stereo mix to mp3. A temp wav is used and deleted."""
    n = len(L)
    peak = 1e-9
    for i in range(n):
        peak = max(peak, abs(L[i]), abs(R[i]))
    norm = 0.88 / peak
    out = array("h")
    q = 1024.0 if crunch <= 0 else crunch
    for i in range(n):
        l = clip_soft(L[i] * norm * 1.04)
        r = clip_soft(R[i] * norm * 1.04)
        mid = (l + r) * 0.5
        side = (l - r) * 0.52
        l = clip_soft(mid + side)
        r = clip_soft(mid - side)
        if crunch > 0:
            l = round(l * q) / q
            r = round(r * q) / q
        out.append(int(max(-1.0, min(1.0, l)) * 31200))
        out.append(int(max(-1.0, min(1.0, r)) * 31200))
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    mp3_path = path if path.endswith(".mp3") else path.rsplit(".", 1)[0] + ".mp3"
    wav_to_mp3(wav_path, mp3_path, delete_wav=True)
    print(f"wrote {mp3_path}  duration={n / SR:.2f}s  peak={peak:.3f}")
