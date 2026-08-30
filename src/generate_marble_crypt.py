#!/usr/bin/env python3
"""Marble Crypt — falling-fifths dungeon. Dm Gm C F (i–iv–bVII–bIII)."""
from paths import track_path
from vgm16 import render_track

DM = ((50, 53, 57), 38)
GM = ((43, 46, 50), 31)  # G Bb D
C_ = ((48, 52, 55), 36)
F_ = ((41, 45, 48), 29)

# D natural minor. Bb only over Gm. E only over C.
MEL_A = [
    69, 65, 62, 65, 69, 74, 72, 69,  # A F D F  A D C A
    70, 67, 62, 67, 70, 74, 70, 67,  # Bb G D G  Bb D Bb G
    72, 67, 64, 67, 72, 76, 74, 72,  # C G E G  C E D C
    72, 69, 65, 60, 65, 69, 72, 74,  # C A F C  F A C D
]
MEL_B = [
    74, 69, 65, 69, 74, 77, 76, 74,
    77, 70, 67, 70, 74, 77, 74, 70,
    76, 72, 67, 64, 67, 72, 76, 79,
    77, 72, 69, 65, 69, 72, 77, 81,
]


if __name__ == "__main__":
    render_track(
        track_path("16bit", "marble_crypt_2min.mp3"),
        bpm=128,
        bars=64,
        loop=[DM, GM, C_, F_],
        mel_a=MEL_A,
        mel_b=MEL_B,
        crunch=780.0,
    )
