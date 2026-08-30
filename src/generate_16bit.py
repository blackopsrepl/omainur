#!/usr/bin/env python3
"""2-minute 16-bit action theme. Konami / Kukeiha Club energy, Western setting."""
from __future__ import annotations

from paths import track_path

import math
import os
import tempfile
import wave
from array import array

from game_synth import wav_to_mp3

SR = 44100
BPM = 150
BARS = 75  # 2:00 exactly at 150 BPM
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
N = int(SR * BAR * BARS)

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
    # 25% pulse ≈ square minus octave
    return square_bl(phase) - 0.5 * square_bl(phase * 2.0)


def tri(phase: float) -> float:
    a = 0.0
    s = 1.0
    for h in (1, 3, 5, 7):
        a += s * sine(phase * h) / (h * h)
        s = -s
    return a * 0.95


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


def midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


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


def render_kick() -> list[float]:
    m = int(SR * 0.16)
    out = [0.0] * m
    ph = 0.0
    rng = Noise(3)
    for i in range(m):
        t = i / SR
        freq = 70.0 + 90.0 * math.exp(-t * 40.0)
        ph = (ph + freq / SR) % 1.0
        click = rng.next() * math.exp(-t * 220.0) * 0.5
        out[i] = sine(ph) * math.exp(-t * 18.0) + click
    return out


def render_snare() -> list[float]:
    m = int(SR * 0.18)
    out = [0.0] * m
    rng = Noise(21)
    hp = 0.0
    ph = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.78 * hp + 0.22 * n
        air = n - hp
        ph = (ph + 190.0 / SR) % 1.0
        env = math.exp(-t * 22.0)
        out[i] = air * env * 1.3 + sine(ph) * math.exp(-t * 28.0) * 0.45
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_hat(closed: bool) -> list[float]:
    m = int(SR * (0.045 if closed else 0.16))
    out = [0.0] * m
    rng = Noise(80 if closed else 81)
    hp = 0.0
    k = 70.0 if closed else 18.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.55 * hp + 0.45 * n
        out[i] = (n - hp) * math.exp(-t * k)
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


def render_tom(hz: float) -> list[float]:
    m = int(SR * 0.22)
    out = [0.0] * m
    ph = 0.0
    for i in range(m):
        t = i / SR
        freq = hz * (1.0 + 0.7 * math.exp(-t * 18.0))
        ph = (ph + freq / SR) % 1.0
        out[i] = sine(ph) * math.exp(-t * 10.0)
    return out


def render_crash() -> list[float]:
    m = int(SR * 1.8)
    out = [0.0] * m
    rng = Noise(424)
    hp = 0.0
    for i in range(m):
        t = i / SR
        n = rng.next()
        hp = 0.8 * hp + 0.2 * n
        out[i] = (n - hp) * math.exp(-t * 2.2)
    peak = max(1e-9, max(abs(x) for x in out))
    return [x / peak for x in out]


# D minor — Konami "American stage" key
# (chord midi, bass midi, is_major)
DM = ((50, 53, 57), 38, False)
BB = ((46, 50, 53), 34, True)
C_ = ((48, 52, 55), 36, True)
GM = ((43, 46, 50), 31, False)
A_ = ((45, 49, 52), 33, True)  # A major, V of Dm — harmonic minor sting


def section_of(bar: int) -> str:
    if bar < 4:
        return "intro"
    if bar < 12:
        return "vamp"
    if bar < 28:
        return "theme_a"
    if bar < 44:
        return "theme_b"
    if bar < 52:
        return "tension"
    if bar < 68:
        return "theme_a2"
    return "outro"


def harmony(bar: int) -> tuple[tuple[int, int, int], int, bool]:
    sec = section_of(bar)
    if sec == "intro":
        return (DM, DM, A_, A_)[bar % 4]
    if sec == "tension":
        return (DM, C_, BB, A_)[bar % 4]
    if sec == "theme_b":
        return (GM, BB, C_, A_)[bar % 4]
    # vamp, theme_a, theme_a2, outro
    return (DM, BB, C_, DM)[bar % 4]


# 8th-note hooks, rests as 0. All chord/scale-safe.
# Theme A over Dm | Bb | C | Dm
MEL_A = [
    69, 74, 72, 69, 70, 69, 67, 65,  # A D C A  Bb A G F
    70, 72, 70, 65, 62, 65, 70, 72,  # Bb C Bb F  D F Bb C
    72, 67, 64, 67, 72, 74, 72, 67,  # C G E G  C D C G
    74, 72, 69, 65, 67, 62, 64, 62,  # D C A F  G D E D
]

# Theme B over Gm | Bb | C | A
MEL_B = [
    70, 67, 62, 67, 70, 74, 72, 70,  # Bb G D G  Bb D C Bb
    70, 65, 62, 65, 70, 72, 70, 65,  # Bb F D F  Bb C Bb F
    72, 67, 64, 67, 72, 76, 74, 72,  # C G E G  C E D C
    73, 76, 73, 69, 64, 61, 64, 69,  # C# E C# A  E C# E A
]

# Counter-line for the reprise (lower 5ths/3rds)
MEL_C = [
    62, 65, 69, 65, 65, 65, 62, 60,
    58, 62, 65, 62, 58, 62, 65, 67,
    64, 60, 55, 60, 64, 67, 64, 60,
    62, 65, 69, 65, 62, 57, 58, 57,
]


def melody_note(bar: int, eighth: int) -> int:
    sec = section_of(bar)
    idx = (bar % 4) * 8 + eighth
    if sec in ("theme_a", "theme_a2", "outro"):
        return MEL_A[idx]
    if sec == "theme_b":
        return MEL_B[idx]
    return 0


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N

    kick = render_kick()
    snare = render_snare()
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(220.0)
    tom_m = render_tom(165.0)
    tom_l = render_tom(110.0)
    crash = render_crash()

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        start = int(t * SR)
        sec = section_of(bar)

        kg = 0.0
        if sec == "intro":
            kg = 0.7 if b in (0, 2) else 0.0
        elif sec == "outro":
            kg = 0.55 if bar < 73 else (0.4 if b == 0 else 0.0)
        else:
            kg = 1.0 if b in (0, 2) else 0.55
            if b == 2:
                kg = 1.0
            # extra rock kick on the 'a' of 2 and 4 in peaks
            if sec in ("theme_a", "theme_b", "theme_a2") and b in (1, 3):
                add_at(L, int((t + EIGHTH) * SR), kick, 0.35)
                add_at(R, int((t + EIGHTH) * SR), kick, 0.35)
        if kg:
            add_at(L, start, kick, kg)
            add_at(R, start, kick, kg)

        if b in (1, 3) and sec != "intro":
            sg = 0.85 if sec != "outro" else 0.5
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.05)
        if sec == "intro":
            # militaristic snare build
            nsub = 2 if bar < 2 else (4 if bar < 3 else 8)
            for k in range(nsub):
                st = int((t + BEAT * k / nsub) * SR)
                g = 0.25 + 0.55 * (bar / 3.0) * (k / max(1, nsub - 1))
                add_at(L, st, snare, g)
                add_at(R, st, snare, g)

        hg = 0.0
        if sec in ("vamp", "theme_a", "theme_b", "theme_a2", "tension"):
            hg = 0.22 if sec == "tension" else 0.3
        if hg:
            add_at(L, start, hat_c, hg * 0.8)
            add_at(R, start, hat_c, hg)
            add_at(L, int((t + EIGHTH) * SR), hat_c, hg)
            add_at(R, int((t + EIGHTH) * SR), hat_c, hg * 0.75)
        if b == 3 and sec in ("theme_a", "theme_b", "theme_a2"):
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.32)

        # tom fill last 2 beats of every 8 bars
        if bar % 8 == 7 and b == 2 and sec not in ("intro",):
            add_at(L, start, tom_h, 0.7)
            add_at(R, start, tom_h, 0.55)
            add_at(L, int((t + EIGHTH) * SR), tom_m, 0.75)
            add_at(R, int((t + EIGHTH) * SR), tom_m, 0.7)
        if bar % 8 == 7 and b == 3 and sec not in ("intro",):
            add_at(L, start, tom_l, 0.8)
            add_at(R, start, tom_l, 0.8)
            add_at(L, int((t + EIGHTH) * SR), snare, 0.7)
            add_at(R, int((t + EIGHTH) * SR), snare, 0.7)

    def crash_at(bar: int, g: float) -> None:
        s = int(bar * BAR * SR)
        add_at(L, s, crash, g)
        add_at(R, s, crash, g)

    crash_at(0, 0.4)
    crash_at(4, 0.55)
    crash_at(12, 0.7)
    crash_at(28, 0.65)
    crash_at(44, 0.45)
    crash_at(52, 0.8)
    crash_at(68, 0.4)

    # synth state
    bass_ph = 0.0
    bass_ph2 = 0.0
    lead_ph = 0.0
    lead_ph2 = 0.0
    ctr_ph = 0.0
    gtr_r = 0.0
    gtr_f = 0.0
    brass_ph = [0.0, 0.0, 0.0]
    brass_lp = 0.0
    arp_ph = 0.0
    delay_n = max(1, int(EIGHTH * 1.5 * SR))  # dotted-8th Konami echo
    delay = [0.0] * delay_n
    di = 0
    lead_lp = 0.0

    BASS_PAT = [0, 0, 12, 0, 0, 7, 12, 0]

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root, is_maj = harmony(bar)
        sec = section_of(bar)
        eighth = int(pos / EIGHTH) % 8
        eth = pos - eighth * EIGHTH

        fade = 1.0
        if sec == "outro":
            fade = max(0.0, 1.0 - (bar - 68 + pos / BAR) / 7.0)

        # --- triangle / FM bass ---
        bass_g = 0.0 if sec == "intro" and bar < 2 else 0.85 * fade
        if bass_g:
            bnote = root + BASS_PAT[eighth]
            if sec == "tension":
                bnote = root  # pedal / walking roots already in harmony
            hz = midi_hz(bnote)
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass_ph2 = (bass_ph2 + hz * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH, 0.004, 0.03, 0.7, 0.04)
            bass = tri(bass_ph) * 0.7 + sine(bass_ph2) * 0.5 + square_bl(bass_ph) * 0.15
            L[i] += bass * benv * bass_g * 0.7
            R[i] += bass * benv * bass_g * 0.7

        # --- gritty power-fifth "guitar" (no third = never fights the key) ---
        gtr_g = 0.0
        if sec in ("vamp", "theme_a", "theme_b", "theme_a2"):
            gtr_g = 0.42 * fade
        elif sec == "tension":
            gtr_g = 0.28 * fade
        if gtr_g:
            # muted 8th chug
            genv = env_ad(eth, 0.003, 0.09)
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)  # fifth
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            gtr = saw_bl(gtr_r) + saw_bl(gtr_f)
            gtr = drive(gtr * 1.8, 3.6)
            L[i] += gtr * genv * gtr_g * 0.55
            R[i] += gtr * genv * gtr_g * 0.7

        # --- brass / FM stabs on downbeats (intro + hits) ---
        brass_g = 0.0
        if sec == "intro":
            brass_g = 0.55
        elif eighth == 0 and sec in ("theme_a2", "vamp"):
            brass_g = 0.22
        if brass_g:
            bdur = BAR if sec == "intro" else EIGHTH * 2
            bt = pos if sec == "intro" else eth
            benv = env_adsr(bt, bdur, 0.02, 0.08, 0.55, 0.12)
            acc = 0.0
            for vi, nmidi in enumerate(chord):
                hz = midi_hz(nmidi + 12)
                brass_ph[vi] = (brass_ph[vi] + hz / SR) % 1.0
                acc += saw_bl(brass_ph[vi]) * 0.55 + sine(brass_ph[vi]) * 0.5
            acc /= 3.0
            brass_lp = one_pole(brass_lp, acc, 1400.0)
            val = brass_lp * benv * brass_g * fade
            L[i] += val * 0.85
            R[i] += val * 0.7

        # --- lead pulse (the hook) ---
        nmidi = melody_note(bar, eighth)
        lead = 0.0
        if nmidi and sec in ("theme_a", "theme_b", "theme_a2", "outro"):
            hz = midi_hz(nmidi)
            lead_ph = (lead_ph + hz / SR) % 1.0
            lead_ph2 = (lead_ph2 + hz * 1.002 / SR) % 1.0  # tiny chorus, ~3 cents
            lenv = env_adsr(eth, EIGHTH * 0.95, 0.006, 0.04, 0.75, 0.06)
            raw = pulse_bl(lead_ph) * 0.7 + square_bl(lead_ph2) * 0.25 + sine(lead_ph) * 0.35
            lead_lp = one_pole(lead_lp, raw, 3200.0)
            lead = lead_lp * lenv * 0.72 * fade
            if sec == "theme_a2":
                lead *= 1.12

        # dotted-8th echo
        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        echo = dly * 0.38
        L[i] += lead * 0.85 + echo * 0.55
        R[i] += lead * 0.7 + echo * 0.85

        # --- counter melody on reprise ---
        if sec == "theme_a2":
            cnote = MEL_C[(bar % 4) * 8 + eighth]
            chz = midi_hz(cnote)
            ctr_ph = (ctr_ph + chz / SR) % 1.0
            cenv = env_adsr(eth, EIGHTH * 0.9, 0.008, 0.05, 0.6, 0.08)
            ctr = tri(ctr_ph) * cenv * 0.28 * fade
            L[i] += ctr * 0.9
            R[i] += ctr * 0.55

        # --- 16th arp sparkle in B and A2 (chord tones only) ---
        if sec in ("theme_b", "theme_a2"):
            step = int(pos / (EIGHTH * 0.5)) % 4
            arn = chord[step % 3] + (12 if step < 3 else 24)
            ahz = midi_hz(arn)
            arp_ph = (arp_ph + ahz / SR) % 1.0
            st = pos - int(pos / (EIGHTH * 0.5)) * (EIGHTH * 0.5)
            aenv = env_ad(st, 0.002, 0.07)
            arp = sine(arp_ph) * aenv * 0.12 * fade
            L[i] += arp * (0.5 if step % 2 == 0 else 0.9)
            R[i] += arp * (0.9 if step % 2 == 0 else 0.5)

    # 16-bit crunch + limiter
    peak = 1e-9
    for i in range(N):
        peak = max(peak, abs(L[i]), abs(R[i]))
    norm = 0.88 / peak
    out = array("h")
    q = 768.0  # ~9.5-bit crunch, SNES-adjacent
    for i in range(N):
        l = clip_soft(L[i] * norm * 1.05)
        r = clip_soft(R[i] * norm * 1.05)
        mid = (l + r) * 0.5
        side = (l - r) * 0.5
        l = clip_soft(mid + side)
        r = clip_soft(mid - side)
        l = round(l * q) / q
        r = round(r * q) / q
        out.append(int(max(-1.0, min(1.0, l)) * 31000))
        out.append(int(max(-1.0, min(1.0, r)) * 31000))

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    mp3_path = track_path("16bit", "codename_gator_2min.mp3")
    wav_to_mp3(wav_path, mp3_path)
    print(f"wrote {mp3_path}  duration={N/SR:.2f}s  peak={peak:.3f}")


if __name__ == "__main__":
    main()
