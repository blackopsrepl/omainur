#!/usr/bin/env python3
"""Wind Millstone — Mitsuda-method travel: D Dorian folk pulse, pipe+pluck, hope-with-edge.

Original cue. Not Chrono Trigger or any pool track.
Form: millwake / trail / cairn / eddy / ridge / settle.
"""
from __future__ import annotations

from paths import track_path
from game_synth import (
    SR, Noise, add_at, env_ad, env_adsr, flute, midi_hz, one_pole, organ,
    render_crash, render_hat, render_kick, render_snare, render_tom, sine,
    square_bl, tri, write_wav,
)

BPM = 128
BARS = 64  # 2:00 exactly
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)

# D Dorian: D E F G A B C — hope-with-edge (bright IV/VII against dark i)
# Dm | G | C | Am   (i – IV – VII – v)
DM = ((50, 53, 57), 38)  # D3 F A, root D2
G_ = ((55, 59, 62), 31)  # G B D
C_ = ((48, 52, 55), 36)  # C E G
AM = ((45, 48, 52), 33)  # A C E


def harmony(bar: int):
    return (DM, G_, C_, AM)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 8:
        return "millwake"
    if bar < 24:
        return "trail"
    if bar < 36:
        return "cairn"
    if bar < 44:
        return "eddy"
    if bar < 56:
        return "ridge"
    return "settle"


# Pipe lead — motives with holds/rests. Chord tones / Dorian scale.
# Over Dm G C Am. 0 = rest.
MEL_TRAIL = [
    # Dm: rising hope, held D
    69, 69, 0, 72, 74, 72, 69, 0,   # A A _ C D C A _
    # G: bright IV turn
    71, 0, 74, 76, 74, 71, 67, 0,   # B _ D E D B G _
    # C: open sky
    72, 72, 76, 0, 79, 76, 72, 69,  # C C E _ G E C A
    # Am: edge settle
    72, 0, 69, 67, 69, 65, 0, 0,    # C _ A G A F _ _
]

MEL_CAIRN = [
    # higher pipe phrase — still Dorian
    81, 81, 0, 79, 76, 0, 74, 76,   # A A _ G E _ D E
    79, 0, 74, 71, 74, 79, 0, 76,   # G _ D B D G _ E
    84, 81, 79, 0, 76, 79, 81, 0,   # C A G _ E G A _
    81, 76, 72, 0, 69, 72, 76, 0,   # A E C _ A C E _
]

MEL_RIDGE = [
    # reprise with wider leaps + held tops
    74, 74, 74, 0, 76, 79, 81, 0,   # D D D _ E G A _
    79, 79, 0, 76, 74, 71, 74, 0,   # G G _ E D B D _
    76, 0, 79, 84, 81, 79, 76, 72,  # E _ G C A G E C
    69, 72, 76, 0, 74, 69, 0, 0,    # A C E _ D A _ _
]

# Bass figure — dotted travel walk (NOT the banned pattern)
# offsets from root per 8th: root, rest, +5, root, +12, rest, +7, +5
BASS_TRAIL = [0, None, 7, 0, 12, None, 7, 5]
BASS_CAIRN = [0, 0, None, 12, 7, None, 5, 7]
BASS_RIDGE = [0, None, 12, 7, 0, 5, None, 12]


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.13, 0.32)
    snare = render_snare(0.11, 205.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_m = render_tom(140.0)
    tom_l = render_tom(88.0)
    crash = render_crash(1.9)

    # --- Drums: bodhrán-ish travel pulse (not 1+3 / 2+4 default) ---
    # Kick on 1 and the & of 2; soft snare on 3; ghost tom on 4&; swingy hats.
    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "millwake":
            # wind + millstone: low tom on bar starts only
            if b == 0 and bar % 2 == 0:
                add_at(L, start, tom_l, 0.28)
                add_at(R, start, tom_l, 0.24)
            if b == 2 and bar >= 4:
                add_at(L, start, tom_m, 0.18)
                add_at(R, int((t + EIGHTH) * SR), hat_o, 0.1)
            continue

        if sec == "eddy":
            # thinned: kick 1, open hat on &s, soft snare 3
            if b == 0:
                add_at(L, start, kick, 0.45)
                add_at(R, start, kick, 0.45)
            if b == 2:
                add_at(L, start, snare, 0.28)
                add_at(R, start, snare, 0.3)
            add_at(L, int((t + EIGHTH) * SR), hat_o if b % 2 == 0 else hat_c, 0.12)
            continue

        if sec == "settle":
            if b == 0:
                add_at(L, start, kick, 0.35)
                add_at(R, start, kick, 0.35)
            if b == 2 and bar < 60:
                add_at(L, start, tom_m, 0.22)
                add_at(R, start, tom_m, 0.2)
            continue

        # trail / cairn / ridge — travel pulse
        kg = 0.78 if sec == "ridge" else 0.68
        if b == 0:
            add_at(L, start, kick, kg)
            add_at(R, start, kick, kg)
        # & of 2 — the travel hitch
        if b == 1:
            add_at(L, int((t + EIGHTH) * SR), kick, 0.32)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.32)
        if b == 2:
            sg = 0.55 if sec != "cairn" else 0.48
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.06)
        # 4& ghost tom
        if b == 3:
            add_at(L, int((t + EIGHTH) * SR), tom_m, 0.22)
            add_at(R, int((t + EIGHTH) * SR), tom_l, 0.26)
        # hats: closed on beats, open on & of odd beats
        add_at(L, start, hat_c, 0.14)
        add_at(R, start, hat_c, 0.11)
        if b % 2 == 0:
            add_at(L, int((t + EIGHTH) * SR), hat_o, 0.16)
            add_at(R, int((t + EIGHTH) * SR), hat_o, 0.14)
        else:
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.1)

    for bar, g in ((8, 0.32), (24, 0.4), (36, 0.22), (44, 0.45), (56, 0.28)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    # --- Tonal layers ---
    pad_ph = [[0.0, 0.0] for _ in range(3)]
    pad_lp_l = pad_lp_r = 0.0
    bass_ph = bass2 = 0.0
    lead_ph = pipe2 = 0.0
    pluck_ph = 0.0
    harp_ph = 0.0
    drone_ph = drone2 = 0.0
    wind = Noise(47)
    wind_lp = 0.0
    # 8th-note delay — mix glue, on-grid
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
        if sec == "settle":
            fade = max(0.0, 1.0 - (bar - 56 + pos / BAR) / 8.0)
        if sec == "millwake" and bar < 2:
            fade = 0.35 + 0.65 * ((bar + pos / BAR) / 2.0)

        # wind bed (millwake signature + soft under trail)
        wn = wind.next()
        wind_lp = one_pole(wind_lp, wn, 480.0)
        wg = 0.055 if sec == "millwake" else (0.018 if sec in ("trail", "eddy", "settle") else 0.01)
        L[i] += wind_lp * wg * fade
        R[i] += wind_lp * wg * 0.72 * fade

        # soft Dorian drone on root fifth (millstone hum)
        if sec in ("millwake", "eddy", "settle"):
            dh = midi_hz(root)
            drone_ph = (drone_ph + dh / SR) % 1.0
            drone2 = (drone2 + midi_hz(root + 7) / SR) % 1.0
            dr = sine(drone_ph) * 0.55 + sine(drone2) * 0.35
            dg = 0.16 if sec == "millwake" else 0.1
            L[i] += dr * dg * fade
            R[i] += dr * dg * 0.9 * fade

        # warm organ pad — stereo spread
        pad_l = pad_r = 0.0
        for vi, nm in enumerate(chord):
            hz = midi_hz(nm)
            pad_ph[vi][0] = (pad_ph[vi][0] + hz / SR) % 1.0
            pad_ph[vi][1] = (pad_ph[vi][1] + hz * 1.003 / SR) % 1.0
            s = organ(pad_ph[vi][0]) * 0.55 + sine(pad_ph[vi][1]) * 0.45
            if vi == 0:
                pad_l += s
            elif vi == 2:
                pad_r += s
            else:
                pad_l += s * 0.65
                pad_r += s * 0.65
        pad_l /= 2.3
        pad_r /= 2.3
        cut = 700.0 if sec in ("millwake", "eddy", "settle") else 1300.0
        pad_lp_l = one_pole(pad_lp_l, pad_l, cut)
        pad_lp_r = one_pole(pad_lp_r, pad_r, cut)
        pg = {
            "millwake": 0.2,
            "trail": 0.22,
            "cairn": 0.28,
            "eddy": 0.18,
            "ridge": 0.26,
            "settle": 0.2,
        }[sec] * fade
        L[i] += pad_lp_l * pg
        R[i] += pad_lp_r * pg

        # plucked millstone ostinato — 16th root-5-8-5 harp plucks
        if sec in ("millwake", "trail", "cairn", "eddy", "ridge"):
            step = int(pos / SIX) % 4
            offs = (0, 7, 12, 7)[step]
            oct = 24 if sec != "millwake" else 12
            pluck_ph = (pluck_ph + midi_hz(root + oct + offs) / SR) % 1.0
            st = pos - int(pos / SIX) * SIX
            penv = env_ad(st, 0.0015, 0.055)
            # square-ish pluck with sine body
            pl = (square_bl(pluck_ph) * 0.35 + sine(pluck_ph) * 0.65) * penv
            pgain = 0.11 if sec == "millwake" else (0.09 if sec == "eddy" else 0.07)
            L[i] += pl * pgain * fade * (0.55 if step % 2 else 0.95)
            R[i] += pl * pgain * fade * (0.95 if step % 2 else 0.55)

        # harp fill on cairn / ridge phrase tops (chord tone sparkle)
        if sec in ("cairn", "ridge") and ei in (0, 4):
            nm = chord[2] + 24
            harp_ph = (harp_ph + midi_hz(nm) / SR) % 1.0
            henv = env_ad(eth, 0.002, 0.35)
            hp = sine(harp_ph) * henv * 0.1 * fade
            L[i] += hp * 0.5
            R[i] += hp

        # bass — dotted travel walk
        if sec not in ("millwake",):
            fig = BASS_TRAIL
            if sec == "cairn":
                fig = BASS_CAIRN
            elif sec in ("ridge", "settle"):
                fig = BASS_RIDGE
            elif sec == "eddy":
                fig = [0, None, None, 0, 7, None, None, 5]
            off = fig[ei]
            if off is not None:
                hz = midi_hz(root + off)
                bass_ph = (bass_ph + hz / SR) % 1.0
                bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
                benv = env_adsr(eth, EIGHTH * 0.95, 0.006, 0.05, 0.65, 0.07)
                bass = tri(bass_ph) * 0.72 + sine(bass2) * 0.5
                bg = 0.48 * fade
                L[i] += bass * benv * bg
                R[i] += bass * benv * bg
            else:
                bass_ph = (bass_ph + midi_hz(root) / SR) % 1.0

        # pipe lead — flute + soft square edge (pipe-ish)
        lead = 0.0
        if sec in ("trail", "cairn", "ridge"):
            if sec == "cairn":
                mel = MEL_CAIRN
            elif sec == "ridge":
                mel = MEL_RIDGE
            else:
                mel = MEL_TRAIL
            idx = (bar % 4) * 8 + ei
            nmidi = mel[idx]
            prev = mel[idx - 1] if ei else 0
            if nmidi:
                hz = midi_hz(nmidi)
                lead_ph = (lead_ph + hz / SR) % 1.0
                pipe2 = (pipe2 + hz * 1.0025 / SR) % 1.0  # ≤7 cents
                attack = nmidi != prev
                lenv = (
                    env_adsr(eth, EIGHTH * 0.96, 0.014, 0.06, 0.62, 0.09)
                    if attack
                    else 0.62
                )
                pipe = flute(lead_ph) * 0.78 + square_bl(pipe2) * 0.18 + sine(pipe2) * 0.1
                lead = pipe * lenv * 0.58 * fade
            else:
                lead_ph = (lead_ph + midi_hz(69) / SR) % 1.0
                pipe2 = (pipe2 + midi_hz(69) * 1.0025 / SR) % 1.0
        elif sec == "eddy":
            # sparse echoes of trail motive (every other bar phrase starts)
            if bar % 2 == 0:
                nmidi = MEL_TRAIL[(bar % 4) * 8 + ei]
                if nmidi and ei in (0, 1, 4, 5):
                    hz = midi_hz(nmidi)
                    lead_ph = (lead_ph + hz / SR) % 1.0
                    lenv = env_adsr(eth, EIGHTH * 0.9, 0.02, 0.08, 0.5, 0.12)
                    lead = flute(lead_ph) * lenv * 0.35 * fade
                else:
                    lead_ph = (lead_ph + midi_hz(69) / SR) % 1.0
            else:
                lead_ph = (lead_ph + midi_hz(69) / SR) % 1.0

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.72 + dly * 0.28
        R[i] += lead * 0.88 + dly * 0.22

    out = track_path("16bit", "wind_millstone_2min.mp3")
    write_wav(out, L, R, crunch=480.0)


if __name__ == "__main__":
    main()
