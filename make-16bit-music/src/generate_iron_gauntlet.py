#!/usr/bin/env python3
"""Iron Gauntlet — 16-bit arcade BATTLE cue. Fm Db Ab C, brass fanfare, punch motif.

Shimomura / Capcom METHODS only (sharp motifs, rhythmic punches, character-theme
clarity). Original cue — not an SF2 clone.
"""
from __future__ import annotations

import math

from paths import track_path
from game_synth import (
    SR, add_at, drive, env_ad, env_adsr, midi_hz, one_pole, pulse_bl,
    render_crash, render_hat, render_kick, render_snare, render_tom,
    saw_bl, sine, square_bl, tri, write_wav,
)

BPM = 150
BARS = 75  # 2:00 exact
BEAT = 60.0 / BPM
BAR = BEAT * 4
EIGHTH = BEAT * 0.5
SIX = BEAT * 0.25
N = int(SR * BAR * BARS)
TWO_PI = 2.0 * math.pi

# F natural minor loop; E lives only on C (harmonic-minor V).
FM = ((53, 56, 60), 41)   # F Ab C
DB = ((49, 53, 56), 37)   # Db F Ab
AB = ((56, 60, 63), 44)   # Ab C Eb
C_ = ((48, 52, 55), 36)   # C E G


def harmony(bar: int):
    return (FM, DB, AB, C_)[bar % 4]


def section_of(bar: int) -> str:
    if bar < 4:
        return "fanfare"
    if bar < 12:
        return "stance"
    if bar < 28:
        return "motif"
    if bar < 36:
        return "pressure"
    if bar < 52:
        return "motif2"
    if bar < 60:
        return "clinch"
    if bar < 72:
        return "finish"
    return "ko"


# Character theme A — short punches + rests. E (64/76) only over C.
MEL_A = [
    72, 0, 72, 0, 70, 68, 0, 65,  # C  C  Bb Ab  F
    68, 0, 65, 60, 0, 65, 68, 73,  # Ab  F C  F Ab Db
    75, 0, 72, 68, 0, 72, 75, 77,  # Eb  C Ab  C Eb F
    76, 72, 0, 67, 64, 0, 67, 72,  # E C  G E  G C
]
# Elevated answer — same clarity, higher register.
MEL_B = [
    77, 0, 72, 75, 0, 72, 70, 68,  # F  C Eb  C Bb Ab
    73, 73, 0, 68, 65, 68, 73, 0,  # Db Db  Ab F Ab Db
    80, 0, 75, 72, 75, 0, 80, 84,  # Ab  Eb C Eb  Ab C
    79, 76, 72, 0, 76, 72, 67, 64,  # G E C  E C G E
]

# Syncopated punch bass — not the Gator octave pump.
BASS = {
    41: [12, 0, 0, 7, 12, 10, 0, 7],  # F: oct .. 5 oct b7 .. 5
    37: [0, 12, 0, 4, 7, 0, 12, 4],   # Db: . oct . 3 5 . oct 3
    44: [0, 7, 12, 0, 7, 0, 4, 12],   # Ab: . 5 oct . 5 . 3 oct
    36: [0, 0, 4, 7, 12, 0, 7, 4],    # C: . . E G oct . G E
}

# Intro / clinch brass-stab gate (8ths). 1 = hit.
STAB = [1, 0, 1, 0, 0, 1, 0, 1]


def render_fanfare_hit(midi: float, length: float) -> list[float]:
    m = int(SR * length)
    out = [0.0] * m
    ph = ph2 = 0.0
    for i in range(m):
        t = i / SR
        hz = midi_hz(midi)
        ph = (ph + hz / SR) % 1.0
        ph2 = (ph2 + hz * 1.004 / SR) % 1.0
        env = min(1.0, t / 0.006) * math.exp(-t * 6.5)
        raw = square_bl(ph) * 0.55 + saw_bl(ph2) * 0.4 + sine(ph) * 0.25
        out[i] = drive(raw, 2.6) * env
    return out


def main() -> None:
    L = [0.0] * N
    R = [0.0] * N
    kick = render_kick(0.13, 0.68)
    snare = render_snare(0.11, 230.0)
    hat_c = render_hat(True)
    hat_o = render_hat(False)
    tom_h = render_tom(250.0)
    tom_m = render_tom(170.0)
    tom_l = render_tom(115.0)
    crash = render_crash(1.5)

    # Pre-baked fanfare hits (F / Ab / C / Bb)
    hits = {
        65: render_fanfare_hit(65, 0.28),
        68: render_fanfare_hit(68, 0.28),
        70: render_fanfare_hit(70, 0.22),
        72: render_fanfare_hit(72, 0.32),
        77: render_fanfare_hit(77, 0.35),
        60: render_fanfare_hit(60, 0.25),
    }
    # Fanfare contour across bars 0–3 (unique intro, not kick vamp)
    FANFARE_NOTES = [
        # bar0
        (0.0, 72), (0.5, 68), (1.0, 72), (1.5, 65),
        (2.0, 70), (2.5, 68), (3.0, 65), (3.5, 60),
        # bar1
        (4.0, 77), (4.5, 72), (5.0, 68), (5.5, 72),
        (6.0, 70), (6.5, 65), (7.0, 68), (7.5, 72),
        # bar2 — denser punches
        (8.0, 72), (8.25, 70), (8.5, 68), (9.0, 65),
        (9.5, 72), (10.0, 77), (10.5, 72), (11.0, 68),
        (11.5, 65),
        # bar3 — climb into stance
        (12.0, 68), (12.5, 70), (13.0, 72), (13.5, 77),
        (14.0, 72), (14.5, 77), (15.0, 72), (15.5, 77),
    ]
    for beat_pos, nm in FANFARE_NOTES:
        st = int(beat_pos * BEAT * SR)
        g = 0.55 + 0.15 * (beat_pos / 16.0)
        add_at(L, st, hits[nm], g * 0.9)
        add_at(R, st, hits[nm], g)

    for beat in range(BARS * 4):
        t = beat * BEAT
        bar = beat // 4
        b = beat % 4
        sec = section_of(bar)
        start = int(t * SR)

        if sec == "fanfare":
            # Snare roll builds under brass; toms land bar 3 beat 4
            if bar >= 2:
                nsub = 4 if bar == 2 else (4 if b < 2 else 8)
                for k in range(nsub):
                    st = int((t + BEAT * k / nsub) * SR)
                    g = 0.15 + 0.55 * ((bar - 2) * 4 + b) / 8.0 * (k + 1) / nsub
                    add_at(L, st, snare, g * 0.85)
                    add_at(R, st, snare, g)
            if bar == 3 and b == 3:
                add_at(L, start, tom_h, 0.55)
                add_at(R, int((t + SIX) * SR), tom_m, 0.6)
                add_at(L, int((t + SIX * 2) * SR), tom_l, 0.7)
                add_at(R, int((t + SIX * 3) * SR), snare, 0.55)
            if b == 0 and bar == 0:
                add_at(L, start, crash, 0.35)
                add_at(R, start, crash, 0.35)
            continue

        if sec == "ko":
            if b == 0:
                add_at(L, start, crash, 0.75)
                add_at(R, start, crash, 0.75)
                add_at(L, start, kick, 0.9)
                add_at(R, start, kick, 0.9)
            continue

        # Capcom punch groove: kick 1 + 2-e + 3-and; snare 2 + 4; ghost 4-e
        if b == 0:
            add_at(L, start, kick, 0.95)
            add_at(R, start, kick, 0.95)
        if b == 1:
            add_at(L, int((t + SIX) * SR), kick, 0.48)
            add_at(R, int((t + SIX) * SR), kick, 0.48)
        if b == 2:
            add_at(L, int((t + EIGHTH) * SR), kick, 0.7)
            add_at(R, int((t + EIGHTH) * SR), kick, 0.7)
        if sec in ("pressure", "finish", "motif2") and b == 3:
            add_at(L, int((t + SIX * 3) * SR), kick, 0.35)
            add_at(R, int((t + SIX * 3) * SR), kick, 0.35)

        if b in (1, 3):
            sg = 0.95 if sec in ("motif2", "finish") else 0.78
            if sec == "stance":
                sg = 0.65
            add_at(L, start, snare, sg)
            add_at(R, start, snare, sg * 1.05)
        if sec in ("motif", "pressure", "finish") and b == 3:
            add_at(L, int((t + SIX) * SR), snare, 0.22)
            add_at(R, int((t + SIX) * SR), snare, 0.18)

        # Hats: offbeat 8ths + open on 4-and (musical, not grid spray)
        if sec == "stance":
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.22)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.26)
        elif sec in ("motif", "motif2", "pressure", "finish", "clinch"):
            add_at(L, start, hat_c, 0.14)
            add_at(R, start, hat_c, 0.18)
            add_at(L, int((t + EIGHTH) * SR), hat_c, 0.28)
            add_at(R, int((t + EIGHTH) * SR), hat_c, 0.32)
            if b == 3:
                add_at(L, int((t + EIGHTH) * SR), hat_o, 0.36)
                add_at(R, int((t + EIGHTH) * SR), hat_o, 0.4)
            if sec in ("pressure", "finish") and b in (0, 2):
                add_at(L, int((t + SIX) * SR), hat_c, 0.14)
                add_at(R, int((t + SIX * 3) * SR), hat_c, 0.16)

        if sec == "clinch" and b == 3 and bar % 2 == 1:
            add_at(L, start, tom_h, 0.5)
            add_at(R, int((t + SIX) * SR), tom_m, 0.55)
            add_at(L, int((t + SIX * 2) * SR), tom_l, 0.65)
            add_at(R, int((t + SIX * 3) * SR), snare, 0.45)

        if bar in (11, 27, 35, 51, 59) and b == 3:
            add_at(L, start, tom_h, 0.55)
            add_at(R, int((t + SIX) * SR), tom_m, 0.6)
            add_at(L, int((t + SIX * 2) * SR), tom_l, 0.7)
            add_at(R, int((t + SIX * 3) * SR), snare, 0.5)

    for bar, g in ((4, 0.7), (12, 0.55), (28, 0.65), (36, 0.5), (52, 0.4), (60, 0.8)):
        add_at(L, int(bar * BAR * SR), crash, g)
        add_at(R, int(bar * BAR * SR), crash, g)

    bass_ph = bass2 = 0.0
    gtr_r = gtr_f = 0.0
    gtr_lp = 0.0
    lead_ph = lead2 = 0.0
    lead_lp = 0.0
    stab_ph = stab2 = 0.0
    cnt_ph = 0.0
    # 16th rhythmic delay — Capcom mix glue
    delay_n = max(1, int(SIX * SR))
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
        if sec == "ko":
            fade = max(0.0, 1.0 - (bar - 72 + pos / BAR) / 3.0)

        # Bass — punch figure from stance onward
        if sec not in ("fanfare",):
            rel = BASS[root][ei]
            hz = midi_hz(root + rel)
            bass_ph = (bass_ph + hz / SR) % 1.0
            bass2 = (bass2 + midi_hz(root) * 0.5 / SR) % 1.0
            benv = env_adsr(eth, EIGHTH * 0.78, 0.002, 0.025, 0.4, 0.035)
            raw = square_bl(bass_ph) * 0.48 + sine(bass2) * 0.5 + tri(bass_ph) * 0.18
            bass = drive(raw, 2.5 if sec in ("pressure", "finish") else 2.0)
            bg = 0.58 if sec != "stance" else 0.68
            if sec == "clinch":
                bg = 0.5
            L[i] += bass * benv * bg * fade
            R[i] += bass * benv * bg * fade

        # Power fifths — pressure / finish color only
        if sec in ("pressure", "finish"):
            rh = midi_hz(root + 12)
            fh = midi_hz(root + 19)
            gtr_r = (gtr_r + rh / SR) % 1.0
            gtr_f = (gtr_f + fh / SR) % 1.0
            genv = env_ad(eth, 0.002, 0.065)
            graw = saw_bl(gtr_r) + saw_bl(gtr_f) * 0.8
            gtr_lp = one_pole(gtr_lp, graw, 1800.0)
            gtr = drive(gtr_lp, 3.2)
            gg = 0.3 if sec == "finish" else 0.24
            L[i] += gtr * genv * gg * fade * 0.65
            R[i] += gtr * genv * gg * fade

        # Clinch: rhythmic brass stabs (call punches, not melody)
        if sec == "clinch" and STAB[ei]:
            nm = chord[ei % 3] + 12
            hz = midi_hz(nm)
            stab_ph = (stab_ph + hz / SR) % 1.0
            stab2 = (stab2 + hz * 1.003 / SR) % 1.0
            senv = env_ad(eth, 0.003, 0.09)
            sraw = square_bl(stab_ph) * 0.6 + saw_bl(stab2) * 0.4
            stab = drive(sraw, 2.8) * senv * 0.38 * fade
            L[i] += stab * 0.85
            R[i] += stab

        # Triangle counter in motif2 / finish (under the lead, not competing)
        if sec in ("motif2", "finish") and ei in (2, 5, 7):
            nm = chord[0] + (24 if sec == "finish" else 12)
            hz = midi_hz(nm)
            cnt_ph = (cnt_ph + hz / SR) % 1.0
            cenv = env_ad(eth, 0.002, 0.08)
            cnt = tri(cnt_ph) * cenv * 0.12 * fade
            L[i] += cnt
            R[i] += cnt * 0.7

        # LEAD — one brass identity: square+saw, sharp attack, clear motif
        lead = 0.0
        if sec in ("motif", "pressure", "motif2", "finish"):
            mel = MEL_B if sec in ("motif2", "finish") else MEL_A
            nmidi = mel[(bar % 4) * 8 + ei]
            if nmidi:
                hz = midi_hz(nmidi + (12 if sec == "finish" and bar >= 68 else 0))
                lead_ph = (lead_ph + hz / SR) % 1.0
                lead2 = (lead2 + hz * 1.0028 / SR) % 1.0
                # Punch envelope: snappy attack, short hold — Capcom clarity
                lenv = env_adsr(eth, EIGHTH * 0.7, 0.002, 0.035, 0.35, 0.05)
                raw = (
                    square_bl(lead_ph) * 0.5
                    + saw_bl(lead2) * 0.35
                    + pulse_bl(lead_ph) * 0.2
                    + sine(lead_ph) * 0.2
                )
                lead_lp = one_pole(lead_lp, drive(raw, 2.4), 4500.0)
                lg = 0.72 if sec in ("motif2", "finish") else 0.64
                if sec == "pressure":
                    lg = 0.58
                lead = lead_lp * lenv * lg * fade
            else:
                lead_ph = (lead_ph + midi_hz(72) / SR) % 1.0
                lead_lp = one_pole(lead_lp, 0.0, 4500.0)

        dly = delay[di]
        delay[di] = lead
        di = (di + 1) % delay_n
        L[i] += lead * 0.88 + dly * 0.18
        R[i] += lead * 0.74 + dly * 0.32

    out = track_path("16bit", "iron_gauntlet_2min.mp3")
    write_wav(out, L, R, crunch=640.0)


if __name__ == "__main__":
    main()
