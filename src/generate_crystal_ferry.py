#!/usr/bin/env python3
"""Crystal Ferry — lyrical SNES RPG ferry/town. Bb major I–vi–IV–V.
Uematsu methods: singable flute lead, warm pads, clear A/B; original cue."""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, Noise, add_at, env_ad, env_adsr, flute, midi_hz, one_pole, organ,
    render_bell, render_crash, render_hat, render_kick, render_snare, saw_bl,
    sine, square_bl, tri, write_wav,
)

BPM = 112
BARS = 56  # 2:00 exactly
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# Bb major. A (57/69/81) only over F. E natural avoided (not in Bb major).
BB = ((58, 62, 65), 34)   # Bb D F
GM = ((55, 58, 62), 31)   # G Bb D
EB = ((51, 55, 58), 27)   # Eb G Bb
F_ = ((53, 57, 60), 29)   # F A C — A only here
CM = ((48, 51, 55), 36)   # C Eb G  (ii)


def section_of(bar: int) -> str:
    if bar < 8:
        return "dock"
    if bar < 24:
        return "embark"
    if bar < 40:
        return "crossing"
    if bar < 48:
        return "mist"
    return "shore"  # 48–55, fade in last bars


def harmony(bar: int):
    sec = section_of(bar)
    if sec == "dock":
        return (BB, BB, EB, F_)[bar % 4]
    if sec == "crossing":
        return (EB, CM, BB, F_)[bar % 4]
    if sec == "mist":
        return (BB, F_, GM, EB)[bar % 4]
    # embark, shore — I vi IV V
    return (BB, GM, EB, F_)[bar % 4]


# Theme A over Bb | Gm | Eb | F — holds + rests, singable ferry call
MEL_A = [
    70, 70, 0, 65, 67, 65, 62, 0,   # Bb Bb  F  G F D
    67, 0, 70, 67, 65, 62, 58, 0,   # G  Bb G F D Bb
    75, 75, 0, 70, 67, 0, 70, 72,   # Eb Eb  Bb G  Bb C
    69, 0, 72, 69, 65, 0, 67, 65,   # A  C A F  G F  (A only over F)
]

# Theme B over Eb | Cm | Bb | F — higher, more open water
MEL_B = [
    75, 0, 77, 75, 70, 0, 67, 70,   # Eb  F Eb Bb  G Bb
    72, 0, 75, 72, 67, 0, 70, 67,   # C  Eb C G  Bb G
    74, 74, 0, 70, 65, 70, 74, 0,   # D D  Bb F Bb D
    77, 0, 72, 69, 72, 77, 81, 0,   # F  C A C F A  (A over F)
]

# Soft countermelody under shore reprise (lower 3rds/5ths, scale-safe)
MEL_C = [
    65, 65, 0, 58, 62, 58, 55, 0,
    58, 0, 62, 58, 55, 50, 55, 0,
    63, 63, 0, 58, 55, 0, 58, 60,
    60, 0, 65, 60, 57, 0, 58, 53,   # A=57 only in F bar (index 24–31)
]

# Oar-dip bass: root hold, fifth lift, octave flick — NOT the stock [0,0,12,0,0,7,12,0]
BASS = [0, 0, 0, 7, 0, 0, 12, 5]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.15, 0.28)
    snare = render_snare(0.13, 205.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    crash = render_crash(2.1)
    # Crystal dock bells (Bb5, F5, D5, Bb4)
    bell_bb = render_bell(midi_hz(82), 2.8)
    bell_f = render_bell(midi_hz(77), 2.5)
    bell_d = render_bell(midi_hz(74), 2.4)
    bell_low = render_bell(midi_hz(70), 3.0)

    # --- drums: paddle groove (kick 1 + &-of-2, soft snare on 3) ---
    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)
        if sec == "dock":
            continue
        if sec == "mist":
            if b == 0:
                add_at(L, start, kick, 0.35)
                add_at(R, start, kick, 0.35)
            if b == 2:
                add_at(L, start, snare, 0.22)
                add_at(R, start, snare, 0.25)
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.08)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.1)
            continue
        # paddle: kick on 1, ghost on &-of-2, soft snare on 3
        if b == 0:
            add_at(L, start, kick, 0.72)
            add_at(R, start, kick, 0.72)
        if b == 1:
            add_at(L, int((t + EIGHTH) * SR), kick, 0.32)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.32)
        if b == 2:
            sg = 0.42 if sec != "shore" else 0.32
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.08)
        # offbeat splash hats (water)
        add_at(L, int((t + EIGHTH) * SR), hat_c, 0.14)
        add_at(R, int((t + EIGHTH) * SR), hat_c, 0.18)
        if b == 3 and sec in ("embark", "crossing", "shore"):
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.16)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.2)

    for bar, g in ((0, 0.22), (8, 0.38), (24, 0.45), (40, 0.28), (48, 0.4)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    # dock crystal cascade
    add_at(L, 0, bell_bb, 0.42)
    add_at(R, int(0.18 * SR), bell_f, 0.38)
    add_at(L, int(0.36 * SR), bell_d, 0.34)
    add_at(R, int(0.55 * SR), bell_low, 0.4)
    add_at(L, int(4 * BAR * SR), bell_f, 0.3)
    add_at(R, int(4 * BAR * SR + 0.2 * SR), bell_bb, 0.28)
    # mist return bells
    add_at(L, int(40 * BAR * SR), bell_d, 0.35)
    add_at(R, int(40 * BAR * SR + 0.25 * SR), bell_low, 0.32)

    pad_ph = [[0.0, 0.0] for _ in range(3)]
    pad_lp_l = pad_lp_r = 0.0
    brass_ph = [0.0, 0.0, 0.0]
    brass_lp = 0.0
    bass_ph = bass2 = 0.0
    lead_ph = lead2 = 0.0
    ctr_ph = 0.0
    harp_ph = 0.0
    water = Noise(41)
    water_lp = 0.0
    # irregular short hall taps (ms), not on the beat
    tap1 = max(1, int(0.037 * SR))
    tap2 = max(1, int(0.061 * SR))
    tap3 = max(1, int(0.097 * SR))
    hall = [0.0] * max(tap1, tap2, tap3)
    hi = 0
    # rhythmic 8th delay as mix glue
    delay_n = max(1, int(EIGHTH * SR))
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
        if sec == "shore" and bar >= 52:
            fade = max(0.0, 1.0 - (bar - 52 + pos / BAR) / 4.0)

        # soft water hush on dock / mist
        wn = water.next()
        water_lp = one_pole(water_lp, wn, 480.0)
        if sec in ("dock", "mist"):
            wg = 0.028 if sec == "dock" else 0.018
            L[i] += water_lp * wg * fade
            R[i] += water_lp * wg * 0.85 * fade

        # warm string/organ pad
        pad_l = pad_r = 0.0
        for vi, nm in enumerate(chord):
            hz = midi_hz(nm)
            pad_ph[vi][0] = (pad_ph[vi][0] + hz / SR) % 1.0
            pad_ph[vi][1] = (pad_ph[vi][1] + hz * 1.003 / SR) % 1.0  # ~5 cents
            s = organ(pad_ph[vi][0]) * 0.48 + sine(pad_ph[vi][1]) * 0.52
            if vi == 0:
                pad_l += s
            elif vi == 2:
                pad_r += s
            else:
                pad_l += s * 0.7
                pad_r += s * 0.7
        pad_l /= 2.4
        pad_r /= 2.4
        cut = 750.0 if sec == "dock" else (1100.0 if sec == "mist" else 1450.0)
        pad_lp_l = one_pole(pad_lp_l, pad_l, cut)
        pad_lp_r = one_pole(pad_lp_r, pad_r, cut)
        pg = 0.34 if sec in ("dock", "mist") else 0.24
        L[i] += pad_lp_l * pg * fade
        R[i] += pad_lp_r * pg * fade

        # soft brass swell on crossing / shore phrase tops
        if sec in ("crossing", "shore") and ei == 0:
            acc = 0.0
            for vi, nm in enumerate(chord):
                brass_ph[vi] = (brass_ph[vi] + midi_hz(nm + 12) / SR) % 1.0
                acc += saw_bl(brass_ph[vi]) * 0.35 + sine(brass_ph[vi]) * 0.55
            benv = env_adsr(eth, EIGHTH * 3.2, 0.04, 0.12, 0.45, 0.18)
            brass_lp = one_pole(brass_lp, acc / 3.0, 1600.0)
            val = brass_lp * benv * 0.2 * fade
            L[i] += val * 0.9
            R[i] += val * 0.7
        else:
            for vi, nm in enumerate(chord):
                brass_ph[vi] = (brass_ph[vi] + midi_hz(nm + 12) / SR) % 1.0

        # oar-dip bass (pizz triangle + sine sub)
        if sec != "dock" or bar >= 4:
            rel = BASS[ei]
            # +5 is Eb: only safe as scale tone; keep it on Bb/Eb bars mostly
            if rel == 5 and root not in (34, 27):
                rel = 7
            hz = midi_hz(root + rel)
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + hz * 0.5 / SR) % 1.0
            if ei in (0, 3, 4, 6, 7):
                benv = env_adsr(eth, EIGHTH * 0.95, 0.006, 0.05, 0.55, 0.07)
            else:
                benv = env_ad(eth, 0.004, 0.08) * 0.25
            bg = 0.2 if sec == "mist" else (0.15 if sec == "dock" else 0.48)
            bass = tri(bass_ph) * 0.55 + sine(bass2) * 0.5 + square_bl(bass_ph) * 0.08
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        # harp 16th sparkle on embark phrase ends / crossing
        if sec in ("embark", "crossing", "shore") and (bar % 4) >= 2:
            step = int(pos / SIX) % 4
            arp = (chord[0], chord[1], chord[2], chord[0] + 12)
            harp_ph = (harp_ph + midi_hz(arp[step] + 12) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            henv = env_ad(st, 0.002, 0.09)
            harp = sine(harp_ph) * henv * 0.11 * fade
            L[i] += harp * (0.55 if step % 2 == 0 else 0.95)
            R[i] += harp * (0.95 if step % 2 == 0 else 0.55)

        # flute lead (tiny chorus ≤7 cents)
        lead = 0.0
        if sec in ("embark", "crossing", "shore"):
            mel = MEL_B if sec == "crossing" else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            prev = mel[(bar % 4) * 8 + (ei - 1)] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                lead2 = (lead2 + hz * 1.0035 / SR) % 1.0  # ~6 cents
                attack = nmidi != prev
                if attack:
                    lenv = env_adsr(eth, EIGHTH * 0.98, 0.018, 0.06, 0.68, 0.09)
                else:
                    lenv = 0.68
                raw = flute(lead_ph) * 0.72 + flute(lead2) * 0.28
                lead = raw * lenv * 0.58 * fade
                if sec == "shore":
                    lead *= 1.08
            else:
                lead_ph = (lead_ph + midi_hz(70) / SR) % 1.0
                lead2 = (lead2 + midi_hz(70) * 1.0035 / SR) % 1.0

        # 8th delay glue
        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n

        # short irregular hall on lead
        h1 = hall[(hi - tap1) % len(hall)]
        h2 = hall[(hi - tap2) % len(hall)]
        h3 = hall[(hi - tap3) % len(hall)]
        hall[hi] = lead
        hi = (hi + 1) % len(hall)
        wet = h1 * 0.22 + h2 * 0.14 + h3 * 0.09

        L[i] += lead * 0.78 + dly * 0.28 + wet * 0.7
        R[i] += lead * 0.9 + dly * 0.34 + wet * 0.85

        # shore counter flute (lower)
        if sec == "shore":
            cnote = MEL_C[(bar % 4) * 8 + ei]
            if cnote:
                ctr_ph = (ctr_ph + midi_hz(cnote) / SR) % 1.0
                cenv = env_adsr(eth, EIGHTH * 0.9, 0.02, 0.06, 0.5, 0.1)
                ctr = flute(ctr_ph) * cenv * 0.22 * fade
                L[i] += ctr * 0.95
                R[i] += ctr * 0.55
            else:
                ctr_ph = (ctr_ph + midi_hz(58) / SR) % 1.0

    write_wav(track_path("16bit", "crystal_ferry_2min.mp3"), L, R, crunch=0.0)


if __name__ == "__main__":
    main()
