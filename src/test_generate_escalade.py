import ast
import io
import unittest
from contextlib import redirect_stdout

from generate_escalade import (
    A_HARM_MIN, AM, C_, DM, ED, EM, F_, GM, LEAD_ROLES, _Lcg,
    nearby_chord_tone, check_rules, chord_tone_pcs, deal_arrangement,
    deal_lead_rhythms, main, note_for_slot,
)


class SeedReportingTests(unittest.TestCase):
    def test_reports_every_layer_seed_needed_for_exact_replay(self):
        output = io.StringIO()
        with redirect_stdout(output):
            main(render_audio=False, verify_variation=False, argv=["73"])

        seed_line = next(
            line for line in output.getvalue().splitlines()
            if line.startswith("layer seeds:")
        )
        seeds = ast.literal_eval(seed_line.partition(": ")[2])

        self.assertEqual(
            set(seeds),
            {"arrangement", "kick", "snare", "hats", "bass", "comp", "lead"},
        )


class LeadFlowTests(unittest.TestCase):
    def test_block_entries_keep_melodic_steps_within_a_seventh(self):
        for seed in (0, 2, 7):
            events = main(render_audio=False, verify_variation=False,
                          argv=[str(seed)])
            largest_step = max(
                (abs(second["note"] - first["note"])
                 for first, second in zip(events, events[1:])),
                default=0,
            )

            self.assertLessEqual(largest_step, 7, f"seed {seed}")
            self.assertEqual(check_rules(events), [], f"seed {seed}")


class ChordToneSelectionTests(unittest.TestCase):
    def test_entries_and_cadences_stay_on_nearby_chord_tones(self):
        for seed, chord in enumerate((AM, GM, F_, EM, ED, DM, C_)):
            note = nearby_chord_tone(
                chord, A_HARM_MIN, previous=72, chooser=_Lcg(seed),
            )

            self.assertIn(note % 12, chord_tone_pcs(chord))
            self.assertLessEqual(abs(note - 72), 7)
            self.assertGreaterEqual(note, 64)
            self.assertLessEqual(note, 83)


class RuleCheckerTests(unittest.TestCase):
    def test_rejects_cadence_outside_current_chord(self):
        events = [{"bar": 3, "slot": 15, "func": "cadence",
                   "pc": 0, "pcs": {1, 4, 8}}]

        self.assertEqual(
            check_rules(events),
            ["bar3 slot15: cadence note is outside the current chord"],
        )


class LeadRhythmDealTests(unittest.TestCase):
    def test_two_bar_phrases_repeat_and_adjacent_phrases_change(self):
        bounds = [("theme", 0, 8)]
        matrix = {"theme": ["stomp", "backbeat", "eighths", "gallop",
                             "triads", "theme", "thirds"]}

        first = deal_lead_rhythms(bounds, matrix, 73)
        again = deal_lead_rhythms(bounds, matrix, 73)

        self.assertEqual(first, again)
        for phrase_start in (0, 2, 4, 6):
            self.assertEqual(first[("theme", phrase_start)],
                             first[("theme", phrase_start + 1)])
        phrase_masks = [first[("theme", start)] for start in (0, 2, 4, 6)]
        self.assertTrue(all(a != b for a, b in zip(phrase_masks, phrase_masks[1:])))
        base_slots = [i for i, value in enumerate(LEAD_ROLES["theme"]) if value == "x"]
        for mask in phrase_masks:
            slots = [i for i, value in enumerate(mask) if value == "x"]
            self.assertEqual((slots[0], slots[-1]), (base_slots[0], base_slots[-1]))

    def test_silent_lead_role_remains_empty(self):
        bounds = [("crypt", 0, 2)]
        matrix = {"crypt": ["heart", "none", "sparse", "pedal",
                             "bells", "none", "none"]}

        masks = deal_lead_rhythms(bounds, matrix, 73)

        self.assertEqual(masks, {("crypt", 0): "." * 16,
                                 ("crypt", 1): "." * 16})


class MusicRuleVariationTests(unittest.TestCase):
    def test_strong_slots_vary_only_among_nearby_chord_tones(self):
        scale = [69, 71, 72, 74, 76, 77, 80, 81]
        seeds = [0, 123456789, 234567890, 345678901, 456789012,
                 567890123, 678901234, 789012345, 890123456, 901234567,
                 101010101, 121212121]
        notes = {
            note_for_slot(AM, scale, 4, 1.0, None, 71, chooser=_Lcg(seed))
            for seed in seeds
        }

        self.assertGreater(len(notes), 1)
        self.assertTrue(all(note % 12 in chord_tone_pcs(AM) for note in notes))
        self.assertTrue(all(abs(note - 71) <= 7 for note in notes))

    def test_weak_slots_vary_by_one_scale_step(self):
        scale = [69, 71, 72, 74, 76, 77, 80, 81]
        seeds = [0, 123456789, 234567890, 345678901, 456789012,
                 567890123, 678901234, 789012345, 890123456, 901234567,
                 101010101, 121212121]
        notes = {
            note_for_slot(AM, scale, 4, 0.0, None, 72, chooser=_Lcg(seed))
            for seed in seeds
        }

        self.assertGreater(len(notes), 1)
        self.assertTrue(all(note in scale for note in notes))
        self.assertTrue(all(0 < abs(note - 72) <= 2 for note in notes))


class ArrangementVariationTests(unittest.TestCase):
    def test_deals_vary_body_order_but_keep_opening_and_finale_anchors(self):
        deals = [deal_arrangement(_Lcg(seed)) for seed in range(16)]
        orders = [tuple(deal["order"]) for deal in deals]

        self.assertGreater(len(set(orders)), 1)
        for order in orders:
            self.assertEqual(order[0], "procession")
            self.assertEqual(order[-1], "finale")
            self.assertNotEqual(order[1], "crypt")
            self.assertEqual(set(order[1:-1]), {"theme", "tower", "theme2", "crypt"})

    def test_same_arrangement_seed_reproduces_order_and_bounds(self):
        first = deal_arrangement(_Lcg(73))
        second = deal_arrangement(_Lcg(73))

        self.assertEqual(first["order"], second["order"])
        self.assertEqual(first["bounds"], second["bounds"])


if __name__ == "__main__":
    unittest.main()
