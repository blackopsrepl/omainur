#!/usr/bin/env python3
"""Black Satellite — jungle / DnB, 174 BPM, F#m pedal. Breaks, not four-on-the-floor."""
from __future__ import annotations

from paths import track_path

from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, render_crash,
    render_hat, render_kick, render_snare, saw_bl, sine, square_bl, write_wav,
)

BPM = 174
BARS = 87  # 2:00
BEAT = 60.0 / BPM
BAR = BEAT * 4
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

FS = 42  # F#2


def section_of(bar: int) -> str:
    if bar < 8:
        return "dropin"
    if bar < 24:
        return "a"
    if bar < 32:
        return "cut"
    if bar < 56:
        return "b"
    if bar < 64:
        return "amen"
    if bar < 80:
        return "c"
    return "out"


# Amen-ish 16th grids (K=kick S=snare h=hat). Two bars alternating.
BRK_A = "K---S-K---S-S-KS"
BRK_B = "K-K-S---K--S--S-"
BRK_C = "K--S-KS---S-K-S-"


def grid_for(bar: int) -> str:
    sec = section_of(bar)
    if sec in ("cut", "out"):
        return "K-------K-------"
    if sec == "amen":
        return BRK_C
    if bar % 2:
        return BRK_B
    return BRK_A


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.11, 0.85)
    snare = render_snare(0.09, 230.0)
    hat_c = render_hat(True)
    crash = render_crash(1.2)

    for bar in range(BARS):
        g = grid_for(bar)
        t0 = bar * BAR
        sec = section_of(bar)
        for s, ch in enumerate(g):
            st = int((t0 + s * SIX) * SR)
            if ch == "K":
                add_at(L, st, kick, 1.05)
                add_at(R, st, kick, 1.05)
            elif ch == "S":
                add_at(L, st, snare, 0.9)
                add_at(R, st, snare, 0.95)
            if sec not in ("cut", "out") and s % 2 == 0:
                add_at(L, st, hat_c, 0.16)
                add_at(R, st, hat_c, 0.2)
            elif sec not in ("cut", "out") and s % 2 == 1:
                add_at(L, st, hat_c, 0.08)
                add_at(R, st, hat_c, 0.1)

    for bar, g in ((8, 0.45), (24, 0.3), (32, 0.55), (64, 0.5)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    reese_a = reese_b = 0.0
    reese_lp = 0.0
    stab_ph = 0.0
    pad_ph = [0.0, 0.0, 0.0]
    sub_ph = 0.0
    # F#m7: F# A C# E
    pad_notes = (54, 57, 61, 64)

    bass_pat = [0, 0, 10, 12, 0, 7, 10, 0]  # F# E(rel +10 is E? F#=0, 10=E, 12=oct, 7=C#)
    # 0=F#, 7=C#, 10=E, 12=F# oct — all in F#m7

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        sec = section_of(bar)
        step = int(pos / SIX) % 16
        st = pos - int(pos / SIX) * SIX
        fade = 1.0
        if sec == "out":
            fade = max(0.0, 1.0 - (bar - 80 + pos / BAR) / 7.0)

        # reese on F# (and a 5th)
        hz = midi_hz(FS)
        reese_a = (reese_a + hz * (2.0 ** (-5.0 / 1200.0)) / SR) % 1.0
        reese_b = (reese_b + hz * (2.0 ** (5.0 / 1200.0)) / SR) % 1.0
        raw = saw_bl(reese_a) + saw_bl(reese_b)
        reese_lp = one_pole(reese_lp, raw, 280.0 if sec in ("b", "c", "amen") else 180.0)
        rg = 0.15 if sec in ("cut", "dropin") else 0.55
        L[i] += drive(reese_lp, 3.2) * rg * fade
        R[i] += drive(reese_lp, 3.2) * rg * fade

        # sub 8ths
        eighth = int(pos / (BEAT * 0.5)) % 8
        eth = pos - eighth * (BEAT * 0.5)
        if sec not in ("cut",):
            bhz = midi_hz(FS + bass_pat[eighth])
            sub_ph = (sub_ph + bhz / SR) % 1.0
            ben = env_adsr(eth, BEAT * 0.5, 0.003, 0.04, 0.6, 0.04)
            L[i] += sine(sub_ph) * ben * 0.45 * fade
            R[i] += sine(sub_ph) * ben * 0.45 * fade

        # ragga stabs on the snare hits of the grid — F#m7 voicing
        if sec in ("a", "b", "c", "amen") and grid_for(bar)[step] == "S":
            shz = midi_hz(66 + (7 if step > 8 else 0))  # F#4 / C#5
            stab_ph = (stab_ph + shz / SR) % 1.0
            sen = env_ad(st, 0.002, 0.07)
            stab = drive(square_bl(stab_ph) * 0.5 + sine(stab_ph) * 0.4, 2.4) * sen
            L[i] += stab * 0.22 * fade
            R[i] += stab * 0.3 * fade

        if sec in ("dropin", "cut", "out"):
            acc = 0.0
            for vi, nmidi in enumerate(pad_notes[:3]):
                pad_ph[vi] = (pad_ph[vi] + midi_hz(nmidi) / SR) % 1.0
                acc += sine(pad_ph[vi])
            L[i] += acc / 3.0 * 0.18 * fade
            R[i] += acc / 3.0 * 0.2 * fade

    write_wav(track_path("experiments", "black_satellite_2min.mp3"), L, R, crunch=0.0)


if __name__ == "__main__":
    main()
