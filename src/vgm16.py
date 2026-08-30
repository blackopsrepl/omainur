#!/usr/bin/env python3
"""Shared 16-bit SNES/Genesis arrangement: drums, fifths, pulse lead, delay."""
from __future__ import annotations

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_crash, render_hat, render_kick, render_snare, render_tom, saw_bl,
    sine, square_bl, tri, write_wav,
)

BASS_PAT = [0, 0, 12, 0, 0, 7, 12, 0]


def render_track(
    path: str,
    bpm: int,
    bars: int,
    loop: list[tuple],
    mel_a: list[int],
    mel_b: list[int],
    *,
    crunch: float = 700.0,
) -> None:
    beat = 60.0 / bpm
    bar_s = beat * 4
    eighth = beat * 0.5
    six = beat * 0.25
    n = int(SR * bar_s * bars)

    def section_of(bar: int) -> str:
        if bar < 4:
            return "intro"
        if bar < 8:
            return "vamp"
        if bar < 24:
            return "a"
        if bar < 40:
            return "b"
        if bar < 48:
            return "break"
        if bar < 64:
            return "a2"
        if bar < bars - 4:
            return "b2"
        return "end"

    def harmony(bar: int):
        return loop[bar % 4]

    L = [0.0] * n
    R = [0.0] * n
    kick = render_kick(0.13, 0.55)
    snare = render_snare(0.13, 200.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(220.0)
    tom_l = render_tom(110.0)
    crash = render_crash(1.6)

    for bi in range(bars * 4):
        t = bi * beat
        bar = bi // 4
        b = bi % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "intro":
            if b in (0, 2):
                add_at(L, start, kick, 0.7)
                add_at(R, start, kick, 0.7)
            if b in (1, 3) and bar >= 2:
                add_at(L, start, snare, 0.45)
                add_at(R, start, snare, 0.5)
            continue
        if sec == "end":
            if b == 0:
                add_at(L, start, kick, 0.6)
                add_at(R, start, kick, 0.6)
            if b in (1, 3) and bar < bars - 2:
                add_at(L, start, snare, 0.4)
                add_at(R, start, snare, 0.42)
            continue
        kg = 1.0 if b in (0, 2) else 0.45
        add_at(L, start, kick, kg)
        add_at(R, start, kick, kg)
        if sec in ("a", "b", "a2", "b2") and b in (1, 3):
            add_at(L, int((t + six) * SR), kick, 0.3)
            add_at(R, int((t + six) * SR), kick, 0.3)
        if b in (1, 3):
            sg = 0.55 if sec == "break" else 0.88
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.05)
        hg = 0.16 if sec in ("vamp", "break") else 0.28
        add_at(L, start, hat_c, hg * 0.8)
        add_at(R, start, hat_c, hg)
        add_at(L, int((t + eighth) * SR), hat_c, hg)
        add_at(R, int((t + eighth) * SR), hat_c, hg * 0.75)
        if b == 3 and sec not in ("break", "vamp"):
            add_at(L, int((t + eighth) * SR), hat_o, 0.28)
            add_at(R, int((t + eighth) * SR), hat_o, 0.32)
        if bar % 8 == 7 and b == 3 and sec not in ("intro", "end"):
            add_at(L, start, tom_h, 0.55)
            add_at(R, int((t + eighth) * SR), tom_l, 0.65)

    for bar, g in ((4, 0.45), (8, 0.55), (24, 0.5), (48, 0.35), (64, 0.6)):
        if bar < bars:
            add_at(L, int(bar * bar_s * SR), crash, g)
            add_at(R, int(bar * bar_s * SR), crash, g)

    bass_ph = bass2 = 0.0
    gtr_r = gtr_f = 0.0
    lead_ph = lead2 = 0.0
    lead_lp = 0.0
    ctr_ph = 0.0
    brass_ph = [0.0, 0.0, 0.0]
    delay_n = max(1, int(eighth * 1.5 * SR))
    delay = [0.0] * delay_n
    di = 0

    for i in range(n):
        t = i / SR
        bar = min(bars - 1, int(t / bar_s))
        pos = t - bar * bar_s
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / eighth) % 8
        eth = pos - ei * eighth
        fade = 1.0
        if sec == "end":
            fade = max(0.0, 1.0 - (bar - (bars - 4) + pos / bar_s) / 4.0)

        if sec != "intro" or bar >= 2:
            hz = midi_hz(root + BASS_PAT[ei])
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, eighth, 0.004, 0.03, 0.7, 0.04)
            bass = tri(bass_ph) * 0.65 + sine(bass2) * 0.45 + square_bl(bass_ph) * 0.12
            L[i] += bass * benv * 0.62 * fade
            R[i] += bass * benv * 0.62 * fade

        if sec in ("vamp", "a", "b", "a2", "b2"):
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            genv = env_ad(eth, 0.003, 0.09)
            gtr = drive(saw_bl(gtr_r) + saw_bl(gtr_f), 3.3)
            L[i] += gtr * genv * 0.34 * fade * 0.55
            R[i] += gtr * genv * 0.34 * fade * 0.7

        if sec in ("intro", "a2") and ei == 0:
            acc = 0.0
            for vi, nm in enumerate(chord):
                hz = midi_hz(nm + 12)
                brass_ph[vi] = (brass_ph[vi] + hz / SR) % 1.0
                acc += saw_bl(brass_ph[vi]) * 0.5 + sine(brass_ph[vi]) * 0.5
            benv = env_adsr(eth, eighth * 2, 0.02, 0.08, 0.45, 0.1)
            val = acc / 3.0 * benv * 0.28 * fade
            L[i] += val * 0.85
            R[i] += val * 0.7

        lead = 0.0
        if sec in ("a", "b", "a2", "b2"):
            mel = mel_b if sec in ("b", "b2") else mel_a
            nmidi = mel[(bar % 4) * 8 + ei]
            hz = midi_hz(nmidi)
            lead_ph = (lead_ph + hz / SR) % 1.0
            lead2 = (lead2 + hz * 1.0018 / SR) % 1.0
            lenv = env_adsr(eth, eighth * 0.92, 0.005, 0.04, 0.7, 0.06)
            raw = pulse_bl(lead_ph) * 0.65 + square_bl(lead2) * 0.22 + sine(lead_ph) * 0.35
            lead_lp = one_pole(lead_lp, raw, 3200.0)
            lead = lead_lp * lenv * 0.7 * fade
            if sec in ("a2", "b2"):
                lead *= 1.08

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.82 + dly * 0.34
        R[i] += lead * 0.7 + dly * 0.45

        if sec in ("a2", "b2"):
            nm = chord[1] + 12
            hz = midi_hz(nm)
            ctr_ph = (ctr_ph + hz / SR) % 1.0
            cenv = env_adsr(eth, eighth * 0.9, 0.01, 0.05, 0.5, 0.08)
            ctr = tri(ctr_ph) * cenv * 0.22 * fade
            L[i] += ctr * 0.9
            R[i] += ctr * 0.5

    write_wav(path, L, R, crunch=crunch)
