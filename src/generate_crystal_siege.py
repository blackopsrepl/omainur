#!/usr/bin/env python3
"""Crystal Siege — 90s SNES battle loop. Am F G Am (i–VI–VII–i)."""
from paths import track_path
from vgm16 import render_track

AM = ((57, 60, 64), 33)
F_ = ((53, 57, 60), 29)
G_ = ((55, 59, 62), 31)

# 8ths, A natural minor. B only over G.
MEL_A = [
    69, 72, 76, 72, 74, 72, 69, 64,  # A C E C  D C A E
    72, 69, 65, 69, 72, 74, 72, 69,  # C A F A  C D C A
    74, 71, 67, 71, 74, 79, 76, 74,  # D B G B  D G E D
    76, 72, 69, 64, 67, 64, 69, 72,  # E C A E  G E A C
]
MEL_B = [
    81, 76, 72, 76, 79, 76, 72, 69,
    77, 72, 69, 65, 69, 72, 77, 76,
    79, 74, 71, 67, 71, 74, 79, 81,
    76, 72, 69, 72, 76, 79, 76, 72,
]


if __name__ == "__main__":
    render_track(
        track_path("16bit", "crystal_siege_2min.mp3"),
        bpm=152,
        bars=76,
        loop=[AM, F_, G_, AM],
        mel_a=MEL_A,
        mel_b=MEL_B,
    )
