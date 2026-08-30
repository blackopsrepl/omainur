#!/usr/bin/env python3
"""Sky Citadel — airship royal road. F G Em Am. Wind intro, flute, propeller 16ths."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, Noise, add_at, env_ad, env_adsr, flute, midi_hz, one_pole,
    render_crash, render_hat, render_kick, render_snare, saw_bl, sine,
    square_bl, write_wav,
)

BPM = 140
BARS = 70
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

F_ = ((53, 57, 60), 29)
G_ = ((55, 59, 62), 31)
EM = ((52, 55, 59), 40)
AM = ((57, 60, 64), 33)


def harmony(bar: int):
    return (F_, G_, EM, AM)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "launch"
    if bar < 20:
        return "clouds"
    if bar < 36:
        return "crest"
    if bar < 44:
        return "stall"
    if bar < 64:
        return "dive"
    return "land"


MEL_A = [
    72, 0, 77, 72, 69, 0, 65, 69,
    71, 0, 74, 79, 74, 71, 67, 0,
    76, 76, 71, 67, 64, 0, 67, 71,
    69, 72, 76, 0, 81, 76, 72, 69,
]
MEL_B = [
    77, 72, 69, 72, 77, 81, 79, 77,
    79, 74, 71, 0, 74, 79, 83, 79,
    76, 71, 67, 71, 76, 0, 79, 76,
    81, 76, 72, 69, 72, 76, 81, 0,
]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.14, 0.4)
    snare = render_snare(0.12, 190.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(1.8)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "launch":
            if b == 0:
                add_at(L, start, kick, 0.35)
                add_at(R, start, kick, 0.35)
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.12)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.1)
            continue
        if sec == "stall":
            if b == 0:
                add_at(L, start, kick, 0.5)
                add_at(R, start, kick, 0.5)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.18)
            continue
        if sec == "land":
            if b == 0:
                add_at(L, start, kick, 0.4)
                add_at(R, start, kick, 0.4)
            continue
        # airship lilt: kick 1, ghost 3, snare 4
        if b == 0:
            add_at(L, start, kick, 0.85)
            add_at(R, start, kick, 0.85)
        if b == 2:
            add_at(L, start, kick, 0.28)
            add_at(R, start, kick, 0.28)
        if b == 3:
            add_at(L, start, snare, 0.7)
            add_at(R, start, snare, 0.76)
        add_at(L, int((t + EIGHTH) * SR), hat_o if b % 2 == 0 else hat_c, 0.22)
        add_at(R, start, hat_c, 0.12)

    for bar, g in ((8, 0.35), (20, 0.5), (44, 0.45), (56, 0.55)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    rumble_ph = rumble2 = 0.0
    bass_ph = 0.0
    lead_ph = 0.0
    prop_ph = 0.0
    brass_ph = [0.0, 0.0, 0.0]
    wind = Noise(19)
    wind_lp = 0.0
    delay_n = max(1, int(BEAT * 1.5 * SR))
    delay = [0.0] * delay_n
    di = 0

    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        pos = t - bar * BAR
        chord, root = harmony(bar)
        sec = section_of(bar)
        ei = int(pos / EIGHTH) % 8
        eth = pos - ei * EIGHTH
        fade = 1.0
        if sec == "land":
            fade = max(0.0, 1.0 - (bar - 64 + pos / BAR) / 6.0)

        # engine rumble — two subs, 5 cents
        rh = midi_hz(root)
        rumble_ph = (rumble_ph + rh * 0.5 / SR) % 1.0
        rumble2 = (rumble2 + rh * 0.5 * 1.0029 / SR) % 1.0
        rg = 0.22 if sec in ("launch", "stall", "land") else 0.1
        rum = (sine(rumble_ph) + sine(rumble2)) * 0.5 * rg * fade
        L[i] += rum
        R[i] += rum

        wn = wind.next()
        wind_lp = one_pole(wind_lp, wn, 600.0)
        wg = 0.04 if sec == "launch" else 0.016
        L[i] += wind_lp * wg * fade
        R[i] += wind_lp * wg * 0.7 * fade

        if sec not in ("launch",) or bar >= 4:
            if ei % 2 == 0:
                bass_ph = (bass_ph + midi_hz(root) / SR) % 1.0
                benv = env_adsr(eth, EIGHTH * 2, 0.008, 0.05, 0.6, 0.08)
                bass = sine(bass_ph) * 0.7 + flute(bass_ph) * 0.2
                L[i] += bass * benv * 0.48 * fade
                R[i] += bass * benv * 0.48 * fade
            else:
                bass_ph = (bass_ph + midi_hz(root) / SR) % 1.0

        # propeller: 16th 1-5-8-5 square ticks
        if sec in ("launch", "clouds", "crest", "dive"):
            step = int(pos / SIX) % 4
            offs = (0, 7, 12, 7)[step]
            prop_ph = (prop_ph + midi_hz(root + 24 + offs) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            penv = env_ad(st, 0.001, 0.04)
            prop = square_bl(prop_ph) * penv * 0.09 * fade
            L[i] += prop * (0.5 if step % 2 else 0.9)
            R[i] += prop * (0.9 if step % 2 else 0.5)

        if sec in ("crest", "dive") and ei == 0:
            acc = 0.0
            for vi, nm in enumerate(chord):
                brass_ph[vi] = (brass_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                acc += saw_bl(brass_ph[vi]) * 0.4 + sine(brass_ph[vi]) * 0.6
            benv = env_adsr(eth, EIGHTH * 2, 0.02, 0.08, 0.4, 0.1)
            val = acc / 3.0 * benv * 0.22 * fade
            L[i] += val * 0.85
            R[i] += val * 0.7

        lead = 0.0
        if sec in ("clouds", "crest", "dive"):
            mel = MEL_B if sec in ("crest", "dive") and bar % 8 >= 4 else MEL_A
            if sec == "crest":
                mel = MEL_B
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + ei - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                attack = nmidi != prev
                lenv = env_adsr(eth, EIGHTH * 0.95, 0.015, 0.06, 0.62, 0.08) if attack else 0.62
                lead = flute(lead_ph) * lenv * 0.6 * fade
            else:
                lead_ph = (lead_ph + midi_hz(72) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.78 + dly * 0.32
        R[i] += lead * 0.88 + dly * 0.26

    write_wav(track_path("16bit", "sky_citadel_2min.mp3"), L, R, crunch=0.0)


if __name__ == "__main__":
    main()
