import random
import unittest

from event_variation import (
    swap_event_onsets, variation_metrics, vary_phrase_mask,
)


class PhraseRhythmTests(unittest.TestCase):
    def test_changes_onset_pattern_while_preserving_entry_and_cadence_anchors(self):
        base = "x.x..x..x.x.x..."

        variant = vary_phrase_mask(base, random.Random(4))

        base_slots = [i for i, symbol in enumerate(base) if symbol == "x"]
        new_slots = [i for i, symbol in enumerate(variant) if symbol == "x"]
        self.assertNotEqual(new_slots, base_slots)
        self.assertEqual(new_slots[0], base_slots[0])
        self.assertEqual(new_slots[-1], base_slots[-1])
        self.assertGreaterEqual(len(new_slots), 3)
        self.assertLessEqual(len(new_slots), 8)

    def test_is_seeded_and_avoids_repeating_the_previous_phrase(self):
        base = "x.x..x..x.x.x..."
        previous = vary_phrase_mask(base, random.Random(1))

        first = vary_phrase_mask(base, random.Random(2), previous)
        again = vary_phrase_mask(base, random.Random(2), previous)

        self.assertNotEqual(first, previous)
        self.assertEqual(first, again)

    def test_silent_role_remains_silent(self):
        base = "." * 16
        self.assertEqual(vary_phrase_mask(base, random.Random(7)), base)


class VariationMetricsTests(unittest.TestCase):
    def test_reports_note_onset_and_contour_variation(self):
        first = [
            {"bar": 0, "slot": 0, "note": 60},
            {"bar": 0, "slot": 2, "note": 62},
            {"bar": 0, "slot": 4, "note": 64},
        ]
        second = [
            {"bar": 0, "slot": 0, "note": 61},
            {"bar": 0, "slot": 2, "note": 63},
            {"bar": 0, "slot": 4, "note": 65},
        ]

        result = variation_metrics(first, second)

        self.assertEqual(result, {"note": 1.0, "onset": 0.0, "contour": 1.0})

    def test_identical_or_too_short_takes_have_zero_measured_variation(self):
        one_note = [{"bar": 0, "slot": 0, "note": 60}]

        self.assertEqual(variation_metrics(one_note, one_note),
                         {"note": 0.0, "onset": 0.0, "contour": 0.0})
        self.assertEqual(variation_metrics([], []),
                         {"note": 0.0, "onset": 0.0, "contour": 0.0})


class SwapEventOnsetsTests(unittest.TestCase):
    def test_swaps_individual_note_slots_and_recomputes_sample_starts(self):
        events = [
            {"bar": 2, "slot": 1, "note": 64, "start": 100},
            {"bar": 2, "slot": 8, "note": 67, "start": 200},
        ]
        before_notes = [event["note"] for event in events]

        moved = swap_event_onsets(events, random.Random(4),
                                  bar_seconds=1.0, sixteenth_seconds=0.1,
                                  sample_rate=100)

        self.assertEqual(moved, 2)
        self.assertEqual([event["note"] for event in events], before_notes)
        self.assertEqual([event["slot"] for event in events], [8, 1])
        self.assertEqual([event["start"] for event in events], [280, 210])

    def test_never_moves_events_across_bars_or_collides_slots(self):
        events = [
            {"bar": 0, "slot": 0, "note": 60, "start": 0},
            {"bar": 0, "slot": 4, "note": 62, "start": 40},
            {"bar": 1, "slot": 3, "note": 65, "start": 130},
            {"bar": 1, "slot": 9, "note": 67, "start": 190},
        ]

        moved = swap_event_onsets(events, random.Random(9),
                                  bar_seconds=1.0, sixteenth_seconds=0.1,
                                  sample_rate=100)

        self.assertEqual(moved, 4)
        for bar in (0, 1):
            slots = [event["slot"] for event in events if event["bar"] == bar]
            self.assertEqual(len(slots), len(set(slots)))
        self.assertEqual({event["bar"] for event in events}, {0, 1})

    def test_leaves_single_event_bar_unchanged(self):
        events = [{"bar": 3, "slot": 6, "note": 69, "start": 360}]
        original = [event.copy() for event in events]

        moved = swap_event_onsets(events, random.Random(1),
                                  bar_seconds=1.0, sixteenth_seconds=0.1,
                                  sample_rate=100)

        self.assertEqual(moved, 0)
        self.assertEqual(events, original)


if __name__ == "__main__":
    unittest.main()
