#!/usr/bin/env python3
"""Last Continent — SNES final-dungeon epic. Em C G D (i–bVI–bIII–bVII)."""
from paths import track_path
from vgm16 import render_track

EM = ((52, 55, 59), 40)
C_ = ((48, 52, 55), 36)
G_ = ((43, 47, 50), 31)  # G B D
D_ = ((50, 54, 57), 38)  # D F# A — F# only here

# E natural minor. F# only over D.
MEL_A = [
    71, 67, 64, 67, 71, 76, 74, 71,  # B G E G  B E D B
    72, 67, 64, 67, 72, 76, 72, 67,  # C G E G  C E C G
    74, 71, 67, 62, 67, 71, 74, 79,  # D B G D  G B D G
    74, 69, 66, 69, 74, 78, 74, 69,  # D A F# A  D F# D A
]
MEL_B = [
    76, 71, 67, 71, 76, 79, 76, 74,
    79, 76, 72, 67, 72, 76, 79, 81,
    79, 74, 71, 67, 71, 74, 79, 83,
    81, 74, 69, 66, 69, 74, 78, 81,
]


if __name__ == "__main__":
    render_track(
        track_path("16bit", "last_continent_2min.mp3"),
        bpm=144,
        bars=72,
        loop=[EM, C_, G_, D_],
        mel_a=MEL_A,
        mel_b=MEL_B,
    )
