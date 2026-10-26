"""Test the synthetic harness with stubs and deliberate behavioral failures.

No possession model is implemented or validated by this test module.
"""

import unittest
from dataclasses import fields, replace

from evaluation.behavioral_cases import Inputs, Interval, Observation, synthetic_cases
from evaluation.behavioral_harness import check_prediction, expected_labels, run_cases


class BehavioralHarnessTests(unittest.TestCase):
    def setUp(self):
        self.cases = {case.name: case for case in synthetic_cases()}

    def test_contracts_are_complete_and_deterministic(self):
        self.assertEqual(synthetic_cases(), synthetic_cases())
        self.assertEqual(len(self.cases), 8)
        for case in self.cases.values():
            self.assertEqual(len(expected_labels(case)), len(case.inputs.observations))

    def test_constant_test_stub_passes_sustained_case(self):
        # Stub has no access to expectations, and is not a candidate algorithm.
        def home_stub(inputs):
            self.assertIsInstance(inputs, Inputs)
            return ["H"] * len(inputs.observations)

        result, = run_cases(home_stub, [self.cases["sustained_control"]])
        self.assertTrue(result.passed)
        self.assertEqual(result.mismatches, 0)

    def test_constant_stub_fails_turnover_and_dead_ball(self):
        results = run_cases(lambda inputs: ["H"] * len(inputs.observations), [
            self.cases["controlled_turnover_after_gap"],
            self.cases["visible_dead_ball_then_restart"],
        ])
        self.assertEqual([r.mismatches for r in results], [50, 70])
        self.assertTrue(all(not r.passed for r in results))

    def test_missing_ball_as_dead_fails(self):
        case = self.cases["missing_ball_inside_possession"]
        wrong = ["D" if ob.ball_xy is None else "H" for ob in case.inputs.observations]
        self.assertEqual(check_prediction(case, wrong).mismatches, 20)

    def test_one_frame_contact_is_not_a_turnover(self):
        case = self.cases["transient_opponent_deflection"]
        contact = case.inputs.observations[35]
        self.assertEqual(contact.ball_xy, contact.players[1].xy)
        wrong = ["H"] * 80
        wrong[35] = "A"
        self.assertFalse(check_prediction(case, wrong).passed)

    def test_each_side_of_turnover_boundary_is_checked(self):
        case = self.cases["controlled_turnover_after_gap"]
        # Independently written stub timeline, then early and late variants.
        self.assertTrue(check_prediction(case, ["H"] * 50 + ["A"] * 50).passed)
        for boundary in (49, 51):
            result = check_prediction(case, ["H"] * boundary + ["A"] * (100 - boundary))
            self.assertEqual(result.mismatches, 1)

    def test_restart_and_half_reset_boundaries(self):
        restart = self.cases["visible_dead_ball_then_restart"]
        self.assertTrue(check_prediction(restart, ["H"] * 30 + ["D"] * 30 + ["A"] * 40).passed)
        # Copying the phase tag's team produces a false possession during D.
        self.assertFalse(check_prediction(restart, ["H"] * 30 + ["A"] * 70).passed)
        halves = self.cases["half_boundary_resets_state"]
        self.assertTrue(check_prediction(halves, ["H"] * 40 + ["A"] * 50).passed)
        self.assertEqual(check_prediction(halves, ["H"] * 50 + ["A"] * 40).mismatches, 10)

    def test_noisy_phases_do_not_supply_answer(self):
        case = self.cases["noisy_phase_is_not_possession"]
        wrong = [ob.phases[0].team for ob in case.inputs.observations]
        self.assertEqual(check_prediction(case, wrong).mismatches, 80)

    def test_wrong_length_and_unknown_labels_raise(self):
        case = self.cases["sustained_control"]
        for prediction in (["H"] * 79, ["H"] * 81, ["?"] * 80, [None] * 80):
            with self.assertRaises(ValueError):
                check_prediction(case, prediction)

    def test_invalid_expectations_are_rejected(self):
        case = self.cases["sustained_control"]
        for intervals in (
            (Interval(1, 80, "H"),), (Interval(0, 81, "H"),),
            (Interval(0, 40, "H"), Interval(39, 80, "A")),
            (Interval(0, 80, "?"),),
        ):
            with self.assertRaises(ValueError):
                expected_labels(replace(case, expected=intervals))

    def test_invalid_fixture_prevents_any_predictor_invocation(self):
        case = self.cases["sustained_control"]
        invalid = replace(case, expected=(Interval(1, 80, "H"),))
        calls = []

        def spy(inputs):
            calls.append(inputs)
            return ["H"] * len(inputs.observations)

        with self.assertRaises(ValueError):
            run_cases(spy, [case, invalid])
        self.assertEqual(calls, [])

    def test_fps_must_be_finite_and_positive(self):
        case = self.cases["sustained_control"]
        for fps in (float("nan"), float("inf"), -float("inf"), 0, -1):
            with self.assertRaises(ValueError):
                expected_labels(replace(case, inputs=replace(case.inputs, fps=fps)))

    def test_predictor_input_has_no_intent_fields(self):
        self.assertEqual({f.name for f in fields(Inputs)}, {"observations", "fps", "pitch_m"})
        self.assertEqual({f.name for f in fields(Observation)},
                         {"frame", "half", "ball_xy", "players", "phases"})


if __name__ == "__main__":
    unittest.main()
