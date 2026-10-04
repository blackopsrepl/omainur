from __future__ import annotations

import random
from collections import defaultdict
from typing import MutableMapping, Sequence


def swap_event_onsets(
    events: Sequence[MutableMapping],
    rng: random.Random,
    *,
    bar_seconds: float,
    sixteenth_seconds: float,
    sample_rate: int,
) -> int:
    """Swap note onsets between non-adjacent 16th slots within each bar.

    Events keep their pitches and all other attributes; only the onset slots
    exchange. ``start`` is rebuilt from the bar and destination slot so the
    returned event data is directly usable by a renderer. Returns the number
    of individual events moved.
    """
    by_bar_class: dict[tuple[int, object], list[MutableMapping]] = defaultdict(list)
    for event in events:
        by_bar_class[(int(event["bar"]), event.get("swap_class"))].append(event)

    moved = 0
    for (bar, _swap_class), bar_events in sorted(
        by_bar_class.items(), key=lambda item: (item[0][0], str(item[0][1]))
    ):
        available = list(bar_events)
        rng.shuffle(available)
        while len(available) >= 2:
            first = available.pop()
            partner_index = next(
                (i for i, candidate in enumerate(available)
                 if abs(int(first["slot"]) - int(candidate["slot"])) >= 2),
                None,
            )
            if partner_index is None:
                continue
            second = available.pop(partner_index)
            first_slot = int(first["slot"])
            second_slot = int(second["slot"])
            first["slot"], second["slot"] = second_slot, first_slot
            first["start"] = int((bar * bar_seconds
                                   + second_slot * sixteenth_seconds) * sample_rate)
            second["start"] = int((bar * bar_seconds
                                    + first_slot * sixteenth_seconds) * sample_rate)
            moved += 2
    return moved


def vary_phrase_mask(
    mask: str,
    rng: random.Random,
    previous: str | None = None,
    *,
    max_events: int = 8,
) -> str:
    """Make a bounded local variation while retaining phrase entry/cadence hits.

    The first and last occupied 16th slots are anchors. Variants move one
    interior onset, add a passing onset inside a wide gap, or remove an
    interior onset when density allows. ``previous`` prevents adjacent
    two-bar phrases from repeating the same mask.
    """
    if len(mask) != 16 or set(mask) - {"x", "."}:
        raise ValueError("rhythm masks must be 16 characters of 'x' and '.'")
    slots = [i for i, symbol in enumerate(mask) if symbol == "x"]
    if len(slots) < 2:
        return mask

    variants = {tuple(slots)}
    for source in slots[1:-1]:
        for target in (source - 1, source + 1):
            if 0 < target < 15 and target not in slots:
                variants.add(tuple(sorted((set(slots) - {source}) | {target})))

    if len(slots) < max_events:
        for left, right in zip(slots, slots[1:]):
            if right - left >= 3:
                for target in range(left + 1, right):
                    variants.add(tuple(sorted(slots + [target])))

    if len(slots) > 3:
        for source in slots[1:-1]:
            variants.add(tuple(slot for slot in slots if slot != source))

    def render(variant: tuple[int, ...]) -> str:
        occupied = set(variant)
        return "".join("x" if slot in occupied else "." for slot in range(16))

    alternatives = sorted(render(variant) for variant in variants if variant != tuple(slots))
    alternatives = [candidate for candidate in alternatives if candidate != previous]
    return rng.choice(alternatives) if alternatives else mask


def variation_metrics(first: Sequence[MutableMapping],
                      second: Sequence[MutableMapping]) -> dict[str, float]:
    """Compare aligned note-event sequences; return variation fractions."""
    count = min(len(first), len(second))
    if count == 0:
        return {"note": 0.0, "onset": 0.0, "contour": 0.0}

    same_notes = sum(
        (first[i]["bar"], first[i]["slot"], first[i]["note"])
        == (second[i]["bar"], second[i]["slot"], second[i]["note"])
        for i in range(count)
    )
    same_onsets = sum(
        (first[i]["bar"], first[i]["slot"])
        == (second[i]["bar"], second[i]["slot"])
        for i in range(count)
    )

    first_contour = [
        (first[i]["note"] % 12, first[i + 1]["note"] % 12)
        for i in range(len(first) - 1)
    ]
    second_contour = [
        (second[i]["note"] % 12, second[i + 1]["note"] % 12)
        for i in range(len(second) - 1)
    ]
    contour_count = min(len(first_contour), len(second_contour))
    same_contour = sum(
        first_contour[i] == second_contour[i] for i in range(contour_count)
    )

    return {
        "note": 1.0 - same_notes / count,
        "onset": 1.0 - same_onsets / count,
        "contour": 1.0 - same_contour / contour_count if contour_count else 0.0,
    }
