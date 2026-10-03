#!/usr/bin/env python3
"""008 ear-on-artifact: does the RENDERED AUDIO show the recurrence the lanes claim?

The one place the artifact can prove what lane math cannot: chroma is
octave-blind by construction, so the register-shifted answers (B/D, +12 on the
tail) still fold to the same pitch-class sequence. Section pairs that the lane
gates certified as hook statements should correlate in chroma space; sections
gated as divergent (the ornament sites) should NOT correlate fully.

Gates (declared before running):
  GA corroboration: of the lane-gated hook pairs, >= 5/6 audio-correlate
    (chroma cosine >= 0.60) — the artifact carries the identity audibly.
  GB contrast: at most 2 of the 8 sections fail the plain-salad floor
    (section chroma spread < 0.02 = one mass, no colour).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "omainur/generator"))
import omainur_gen as og

RATE = 48_000
RENDER = HERE.parents[1] / "sequencer-fork/target/debug/examples/render"
SAMPLES = HERE.parents[1] / "omainur/instruments/samples"


def audio_of(song: dict, wav: str) -> Path:
    path = Path(f"/tmp/spike008-{wav}.json")
    path.write_text(json.dumps(song, separators=(",", ":")))
    result = subprocess.run([str(RENDER), str(SAMPLES), str(path), f"/tmp/spike008-{wav}.wav", "33"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"render failed: {result.stderr[-200:]}")
    artifact = Path(f"/tmp/spike008-{wav}.wav")
    with wave.open(str(artifact), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return data.reshape(-1, 2).astype(np.float64) / 32768.0


def section_chromas(audio, bpm, count=8, bars=4):
    per = int(RATE * 60.0 / bpm * bars * 4.0)
    out = []
    for i in range(count):
        section = audio[i * per:(i + 1) * per].mean(axis=1)
        # average chroma over the section's 4 bars (1s windows at each onset)
        bars_chroma = []
        for bar in range(bars):
            frame = section[bar * (per // bars):(bar + 1) * (per // bars)]
            if len(frame) > RATE:
                frame = frame[:RATE]
            if len(frame) < 4096:
                continue
            spec = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
            freqs = np.fft.rfftfreq(len(frame), 1.0 / RATE)
            midi = np.full_like(freqs, -1.0)
            audible = (freqs >= 65) & (freqs <= 3000)  # the pack's pitched zone
            midi[audible] = 12.0 * np.log2(freqs[audible] / 440.0) + 69.0
            pc = np.zeros(12)
            ok = midi >= 0
            bins = np.clip(np.round(midi[ok]).astype(int) % 12, 0, 11)
            np.add.at(pc, bins, spec[ok])
            if pc.sum() > 0:
                bars_chroma.append(pc / pc.sum())
        out.append(np.mean(bars_chroma, axis=0) if bars_chroma else np.zeros(12))
    return np.array(out)


def cos(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 1e-12 and nb > 1e-12 else 0.0


def main() -> int:
    genre_name = sys.argv[1] if len(sys.argv) > 1 else "castle"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1986

    spec006 = importlib.util.spec_from_file_location("s006", HERE.parent / "006-answer-cadence/main.py")
    s006 = importlib.util.module_from_spec(spec006)
    spec006.loader.exec_module(s006)
    song, hook, errors, lead_idx = s006.build_006(genre_name, seed)
    if errors:
        print("validator:", errors[:2])
        return 1

    # the lane-gated claim, per section (which pairs SHOULD sound alike)
    genre = og.GENRES[genre_name]
    lanes = song["song"]["tracks"][lead_idx]["lanes"]
    hook_lane = lanes[0]
    s005 = s006.s005
    claims = {}
    for p, name in enumerate("ABCDEFGH"):
        m = s006.match_slice(lanes[p], hook_lane, s006.slice_expectation(name))
        claims[name] = round(m, 3)
    print("lane claims:", claims)

    # GA hear-the-carrier experiment: solo the LEAD track (mute every other
    # track — data-level, engine-honored) so chroma measures the melody
    # itself, not the section's backing harmony (which re-lands the hook on
    # DIFFERENT chords by design and would mask identity at mix level).
    solo = json.loads(json.dumps(song))
    for i, track in enumerate(solo["song"]["tracks"]):
        solo["song"]["tracks"][i]["mute"] = (i != lead_idx)
    audio = audio_of(solo, "lead")
    chromas = section_chromas(audio, genre["bpm"])
    print("lead chroma spreads:", [round(float(c.max() - c.min()), 4) for c in chromas])

    # GA: every section vs the A section (the call), on the soloed carrier
    names = "BCDEFGH"
    audios = {name: round(cos(chromas[ord(name) - 65], chromas[0]), 3) for name in names}
    corroborate = sum(1 for name in names
                      if claims[name] >= 0.75 and audios[name] >= 0.60)
    claimed_total = sum(1 for name in names if claims[name] >= 0.75)
    salad = [chr(65 + i) for i, c in enumerate(chromas) if c.max() - c.min() < 0.02]

    results = {
        "lead_solo_cosine_vs_A": audios,
        "ga_corroborate": {"pass": corroborate >= 5, "count": corroborate,
                           "of": claimed_total},
        "gb_contrast": {"pass": len(salad) <= 2, "flat_sections": salad},
    }
    print(json.dumps(results, indent=1))
    Path("/tmp/spike008.json").write_text(json.dumps(results))
    ok = results["ga_corroborate"]["pass"] and results["gb_contrast"]["pass"]
    print("VERDICT:", "VALIDATED" if ok else "INVALIDATED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())