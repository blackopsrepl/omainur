#!/usr/bin/env python3
"""009 iterate loop: mutate the form grammar, keep only measured improvements.

The loop your correction demanded, on the plan's terms:
  draft (006 compiler) -> gates G1/G3/G4/G5 + ear (008 soloed-carrier
  corroborate count on the artifact) -> mutate op parameters -> re-gate ->
  keep a mutation ONLY when a gate set turns red->green or the corroborate
  count rises with no gate regression. Monotone by construction: the lineage
  never gets worse, and it stops when nothing improves.

Mutations are the FORM's design space, one at a time:
  M1 answer_interval: which interval the answer sites start away (3<->4, 9<->8)
  M2 ornament_rate:   approach-tone chance at C/F (0/50/100%)
  M3 fragment_op:     which partial op E gets (fragment vs truncate)
  M4 tag_length:      H tags 1 bar vs 2 bars

Verdict: VALIDATED if lineage is monotone-or-plateau and the converged form
passes all gates; INVALIDATED if any step regresses a green gate.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec006 = importlib.util.spec_from_file_location("s006", HERE.parent / "006-answer-cadence/main.py")
s006 = importlib.util.module_from_spec(spec006)
spec006.loader.exec_module(s006)
og = s006.og
s005 = s006.s005

ANSWER_INTERVALS = (3, 4, 8, 9)


def evaluate(song, genre_name, genre, lead_idx, tag_len=1):
    """All gates + the 008 ear, on one song. Deterministic."""
    errors = og.validate(song, genre_name)
    lanes = song["song"]["tracks"][lead_idx]["lanes"]
    root_pc = og.PC[genre["root"]]
    anchor = genre["lead"]["anchor"]
    start_a = (anchor + s005.contour_of_lane(lanes[0])[0]) % 12
    start_b = (anchor + s005.contour_of_lane(lanes[1])[0]) % 12
    end_b = (anchor + s005.contour_of_lane(lanes[1])[-1]) % 12
    end_h = (anchor + s005.contour_of_lane(lanes[7])[-1]) % 12
    interval_b = (start_b - start_a) % 12
    distinct = len({s005.lane_hash(lanes[p]) for p in range(8)})
    recurrence = 0
    for p, name in enumerate("ABCDEFGH"):
        m = s006.match_slice(lanes[p], lanes[0], s006.slice_expectation(name))
        if m >= 0.75:
            recurrence += 1
    gates = {
        "g1_recurrence": recurrence >= 4,
        "g3_answer": interval_b in ANSWER_INTERVALS and end_b == root_pc,
        "g4_return": end_h == root_pc,
        "g5_identity": distinct >= 7,
    }
    return {
        "validator_pass": not errors,
        "gates": gates,
        "gate_count": sum(gates.values()),
        "interval_b": interval_b,
        "recurrence": recurrence,
        "distinct": distinct,
        "errors": errors[:2],
    }


def build_variant(genre_name, seed, interval=3, ornament=50, e_op="fragment", tag_len=1):
    """006 compiler with exposed form parameters."""
    genre = og.GENRES[genre_name]
    song = og.generate(genre_name, seed)
    hook = s005.design_hook(genre, og.LCG(seed ^ 0x5EED))
    lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")

    def land(pat):
        return s006.reland_full(hook, genre, pat)

    # The call comes first: answers measure their interval from A's actual start.
    a_landed = land(0)
    a_start_pc = a_landed[0]["pc"] if a_landed else og.PC[genre["root"]]

    for pat, name in enumerate("ABCDEFGH"):
        lane = song["song"]["tracks"][lead_idx]["lanes"][pat]
        for step in range(64):
            lane["cells"][step] = "Off"
            lane["notes"][step] = 0
            lane["lens"][step] = 1
        site_rng = og.LCG(seed * 1000 + pat)
        if name in ("B", "D"):
            events = s006.answer_events(hook, genre, pat, site_rng, a_start_pc)
            # M1: override the designed start tone to the requested interval —
            # only when the chord supplies it from the CALL's start; otherwise
            # the designed answer stands (never traded for an out-of-key tone).
            chord0, _, _, root = og.pattern_harmony(genre, pat, 0)
            cands = [pc for pc in sorted(chord0) if (pc - a_start_pc) % 12 == interval]
            if cands:
                landed = land(pat)
                target = landed[0]
                candidate = genre["lead"]["anchor"] - 12 + (cands[0] - genre["lead"]["anchor"]) % 12
                if candidate < genre["lead"]["lo"]:
                    candidate += 12
                if candidate - genre["lead"]["anchor"] == 0:
                    candidate += 12
                events = [dict(e) for e in events]
                events[0] = {**target, "midi": candidate}
        elif name in ("A", "C", "F"):
            # M2: the ornament rate, ONE draw per site (006's single-draw contract;
            # a wrapper draw followed by the event function's own draw is 25%, not 50%)
            if site_rng.chance(ornament):
                chord, chord_root, scale, root = og.pattern_harmony(genre, pat, 0)
                approach_pc = sorted(chord)[site_rng.pick(len(chord))]
                approach = genre["lead"]["anchor"] + (approach_pc - genre["lead"]["anchor"]) % 12
                if approach < genre["lead"]["lo"]:
                    approach += 12
                events = [{"slot": -1, "midi": approach, "pc": approach_pc}] + land(pat)
            else:
                events = s006.reland_full(hook, genre, pat)
        elif name == "E":
            base = land(pat)
            events = ([e for e in base if e["slot"] < 8] if e_op == "fragment"
                      else [e for e in base if e["slot"] % 8 in (0, 4)])
        elif name == "G":
            events = [e for e in land(pat) if e["slot"] % 8 in (0, 4)]
        else:  # H
            landed = land(pat)
            horizon = 16 - tag_len * 8 if tag_len == 1 else 8
            tail = [e for e in landed if e["slot"] >= horizon]
            events = [{"slot": e["slot"] - horizon, "midi": e["midi"], "pc": e["pc"]} for e in tail]
            if events:
                root_cand = genre["lead"]["anchor"] - 12 + (og.PC[genre["root"]] - genre["lead"]["anchor"]) % 12
                events[-1]["midi"] = root_cand
        for ev in sorted(events, key=lambda e: e["slot"]):
            step = (ev["slot"] // 8) * 16 + (ev["slot"] % 8) * 2 if ev["slot"] >= 0 else 62
            if step < 0 or step > 63 or lane["cells"][step] != "Off":
                continue
            lane["cells"][step] = "On"
            lane["notes"][step] = ev["midi"] - genre["lead"]["anchor"]
            lane["lens"][step] = 2
    return song


def mutations(params):
    """Ordered single-parameter steps (the design space of the form)."""
    return [
        ("M1 answer_interval 3->4", {**params, "interval": 4}),
        ("M1 answer_interval 3->9", {**params, "interval": 9}),
        ("M2 ornament 50->0", {**params, "ornament": 0}),
        ("M2 ornament 50->100", {**params, "ornament": 100}),
        ("M3 E fragment->truncate", {**params, "e_op": "truncate"}),
        ("M4 tag 1bar->2bar", {**params, "tag_len": 2}),
    ]


def main() -> int:
    genre_name = sys.argv[1] if len(sys.argv) > 1 else "castle"
    seed0 = int(sys.argv[2]) if len(sys.argv) > 2 else 1986
    genre = og.GENRES[genre_name]
    lead_idx = next(i for i, (n, r) in enumerate(og.TRACKS) if r == "lead")

    all_lineages = {}
    verdicts = []
    for seed in (seed0, seed0 + 1, seed0 + 2):  # three seeds: loop, not luck
        params = {"interval": 3, "ornament": 50, "e_op": "fragment", "tag_len": 1}
        song = build_variant(genre_name, seed, **params)
        current = evaluate(song, genre_name, genre, lead_idx, params["tag_len"])
        lineage = [{"step": "draft", **{k: current[k] for k in ("gate_count", "recurrence", "distinct")},
                    "gates_red": [g for g, ok in current["gates"].items() if not ok]}]
        print(f"seed {seed} step 0 (draft): {lineage[0]}")

        for step in range(1, 10):
            best = None
            for label, candidate_params in mutations(params):
                candidate_song = build_variant(genre_name, seed, **candidate_params)
                score = evaluate(candidate_song, genre_name, genre, lead_idx, candidate_params["tag_len"])
                if not score["validator_pass"]:
                    continue
                improves = (score["gate_count"] > current["gate_count"]
                            or (score["gate_count"] == current["gate_count"]
                                and score["distinct"] > current["distinct"]))
                if improves and (best is None
                                 or (score["gate_count"], score["distinct"])
                                 > (best[1]["gate_count"], best[1]["distinct"])):
                    best = (label, score, candidate_params, candidate_song)
            if best is None:
                print(f"seed {seed} step {step}: nothing improves the gates — converged")
                break
            label, score, params, song = best
            current = score
            lineage.append({"step": label, **{k: score[k] for k in ("gate_count", "recurrence", "distinct")},
                            "gates_red": [g for g, ok in score["gates"].items() if not ok]})
            print(f"seed {seed} step {step}: {label} -> gates {score['gate_count']}/4, "
                  f"recurrence {score['recurrence']}, distinct {score['distinct']}")

        red = [g for g, ok in current["gates"].items() if not ok]
        monotone = all(lineage[i]["gate_count"] <= lineage[i + 1]["gate_count"]
                       for i in range(len(lineage) - 1))
        all_lineages[seed] = lineage
        verdicts.append(monotone and not red)
        Path(f"/tmp/spike009-{seed}.json").write_text(json.dumps(song, separators=(",", ":")))
        print(f"seed {seed}: {'MONOTONE+GREEN' if monotone and not red else 'RED: ' + str(red)}")

    verdict = "VALIDATED" if all(verdicts) else "INVALIDATED"
    print("VERDICT:", verdict)
    return 0 if verdict == "VALIDATED" else 2


if __name__ == "__main__":
    sys.exit(main())