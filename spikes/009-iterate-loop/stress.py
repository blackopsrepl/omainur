#!/usr/bin/env python3
"""stress: red drafts 1980-2003, and whether M1-M4 repairs them red->green."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "omainur" / "generator"))
spec009 = importlib.util.spec_from_file_location(
    "s009", Path(__file__).with_name("main.py")
)
s009 = importlib.util.module_from_spec(spec009)
spec009.loader.exec_module(s009)
import omainur_gen as og

genre = og.GENRES["castle"]
lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")
red_seeds = []
for seed in range(1980, 2004):
    song = s009.build_variant("castle", seed)
    score = s009.evaluate(song, "castle", genre, lead_idx, 1)
    red = [g for g, ok in score["gates"].items() if not ok]
    if not score["validator_pass"] or red:
        red_seeds.append((seed, red or [str(score["errors"])[:40]], score["gate_count"]))
print("red drafts in seeds 1980-2003:", red_seeds if red_seeds else "none")
repairs = []
for seed, red, _ in red_seeds:
    params = {"interval": 3, "ornament": 50, "e_op": "fragment", "tag_len": 1}
    song = s009.build_variant("castle", seed, **params)
    current = s009.evaluate(song, "castle", genre, lead_idx, 1)
    path = [f"draft gate_count={current['gate_count']} red={red}"]
    for step in range(1, 8):
        best = None
        for label, cp in s009.mutations(params):
            cs = s009.build_variant("castle", seed, **cp)
            sc = s009.evaluate(cs, "castle", genre, lead_idx, cp["tag_len"])
            if not sc["validator_pass"]:
                continue
            if (sc["gate_count"], sc["distinct"]) > (current["gate_count"], current["distinct"]):
                if best is None or (sc["gate_count"], sc["distinct"]) > (best[1]["gate_count"], best[1]["distinct"]):
                    best = (label, sc, cp, cs)
        if best is None:
            break
        label, current, params, song = best[0], best[1], best[2], best[3]
        path.append(f"{label} -> {current['gate_count']}/4")
    fixed = current["gate_count"] == 4
    repairs.append((seed, fixed, path, current["gates"]))
for seed, fixed, path, gates in repairs:
    print("seed", seed, "REPAIRED" if fixed else "UNREPAIRED", path,
          "still-red:", [g for g, ok in gates.items() if not ok])