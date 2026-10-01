#!/usr/bin/env python3
"""Spike 001 verdict: does track_pitch + per-note offset land in tune through the engine?

Renders single bass notes at +0/+4/+7/+12 semitones via the real engine
(render harness), then measures each rendered f0 with a Goertzel scan and
checks the semitone ratios. Usage: python3 verify_pitch.py <wav_dir> <render_bin>
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave

SR = 48000
ANCHOR = 36  # bass_c1 is rendered at midi 36


def one_note_song(note_offset: int) -> dict:
    lane = {"cells": ["Off"] * 64, "lens": [1] * 64, "notes": [0] * 64}
    lane["cells"][0] = "Accent"
    lane["lens"][0] = 8
    lane["notes"][0] = note_offset
    return {
        "names": ["bass_hit"],
        "song": {
            "bpm": 120.0, "swing": 0.0, "master": 0.8,
            "steps": [16] * 8, "current": 0, "queued": None,
            "tracks": [{
                "sample": 0, "lanes": [lane] + [{"cells": ["Off"] * 64, "lens": [1] * 64, "notes": [0] * 64} for _ in range(7)],
                "note_len": 1, "volume": 0.8, "pitch": 0.0, "pan": 0.0, "send": 0.0,
                "fx": {}, "mute": False, "solo": False,
            }],
        },
    }


def read_wav(path: str) -> list[float]:
    with wave.open(path) as w:
        assert w.getnchannels() == 2 and w.getsampwidth() == 2
        raw = w.readframes(w.getnframes())
    n = len(raw) // 4
    import struct
    vals = struct.unpack(f"<{2 * n}h", raw)
    return [(vals[2 * i] + vals[2 * i + 1]) / 65534.0 for i in range(n)]


def goertzel_peak(x: list[float], rate: int, lo: float, hi: float) -> tuple[float, float]:
    """(freq, power) of the strongest sinusoid in [lo, hi], 0.2 Hz grid."""
    best = (0.0, -1.0)
    n = len(x)
    f = lo
    while f <= hi:
        w = 2.0 * math.pi * f / rate
        cw = math.cos(w)
        coeff = 2.0 * cw
        s0 = s1 = s2 = 0.0
        for v in x:
            s0 = v + coeff * s1 - s2
            s2 = s1
            s1 = s0
        power = s1 * s1 + s2 * s2 - coeff * s1 * s2
        if power > best[1]:
            best = (f, power)
        f += 0.1
    return best


def main() -> None:
    wav_dir, render_bin = sys.argv[1], sys.argv[2]
    found = {}
    for semi in (0, 4, 7, 12):
        song = f"/tmp/on_{semi}.json"
        out = f"/tmp/on_{semi}.wav"
        with open(song, "w") as fh:
            json.dump(one_note_song(semi), fh)
        subprocess.run([render_bin, wav_dir, song, out, "1"], check=True,
                       capture_output=True, text=True)
        x = read_wav(out)
        # Window fully inside the sounding note at every transposition.
        seg = x[SR // 20: SR // 20 + SR // 5]
        f0, power = goertzel_peak(seg, SR, 40.0, 400.0)
        found[semi] = f0
        print(f"note +{semi:>2}: f0 = {f0:7.2f} Hz  (power {power:.1f})")
    ok = True
    for semi, ref in ((4, 0), (7, 0), (12, 0)):
        expected = found[ref] * (2.0 ** (semi / 12.0))
        cents = 1200.0 * math.log2(found[semi] / expected)
        status = "PASS" if abs(cents) < 15 else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"+{semi:>2} vs +0: expected {expected:7.2f}, got {found[semi]:7.2f} -> {cents:+7.2f} cents {status}")
    print("PITCH CHAIN VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
