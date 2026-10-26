"""Dead/alive projections and independently authored uncertainty/noise contracts."""
import unittest
from dataclasses import replace

import numpy as np

from evaluation.behavioral_cases import Inputs, Observation, Phase, Player, synthetic_cases
from evaluation.behavioral_harness import expected_labels
from possession.features import features_from_inputs
from possession.dead_ball import Config, Evidence, State, infer, infer_inputs


def inputs(points, halves=None, phases=(), fps=10):
    return Inputs(tuple(Observation(i, 1 if halves is None else halves[i], point,
                                   (Player('H', (10, 20)), Player('A', (70, 40))), phases)
                        for i, point in enumerate(points)), fps=fps)


class DeadBallTests(unittest.TestCase):
    def test_t04_dead_alive_projection_only(self):
        # Full H/A ownership behavior remains T07; expected states never reach infer.
        for case in synthetic_cases():
            with self.subTest(case=case.name):
                projection = {'H': State.ALIVE, 'A': State.ALIVE,
                              'D': State.DEAD, 'X': State.UNKNOWN}
                expected = [projection[x] for x in expected_labels(case)]
                np.testing.assert_array_equal(infer_inputs(case.inputs).state, expected)

    def test_team_permutation_does_not_change_result(self):
        for case in synthetic_cases():
            swapped = replace(case.inputs, observations=tuple(
                replace(row, players=tuple(replace(p, team={'H':'A', 'A':'H'}.get(p.team))
                                           for p in row.players),
                        phases=tuple(replace(p, team={'H':'A', 'A':'H'}.get(p.team))
                                     for p in row.phases))
                for row in case.inputs.observations))
            np.testing.assert_array_equal(infer_inputs(swapped).state,
                                          infer_inputs(case.inputs).state)

    def test_stationary_inside_and_setpiece_are_insufficient(self):
        tags = (Phase('SET PIECES', None), Phase('progression', 'H'), Phase('progression', 'A'))
        result = infer_inputs(inputs([(30, 20)] * 50, phases=tags))
        self.assertTrue(np.all(result.state == State.UNKNOWN))
        self.assertTrue(np.all(result.evidence & Evidence.STATIONARY_IN_PITCH))
        self.assertTrue(np.all(result.evidence & Evidence.NOISY_TAG_CONTEXT))

    def test_tags_alone_and_missing_ball_cannot_create_dead(self):
        result = infer_inputs(inputs([None] * 100, phases=(Phase('SET PIECES', 'A'),)))
        self.assertTrue(np.all(result.state == State.UNKNOWN))

    def test_live_missing_retention_expires_and_recovers(self):
        points = [(20 + i * .1, 20) for i in range(20)] + [None] * 80
        points += [(30 + i * .1, 20) for i in range(20)]
        result = infer_inputs(inputs(points))
        self.assertTrue(np.all(result.state[:50] == State.ALIVE))
        self.assertTrue(np.all(result.state[50:100] == State.UNKNOWN))
        self.assertTrue(np.all(result.state[100:] == State.ALIVE))
        self.assertTrue(result.evidence[30] & Evidence.RETAINED)

    def test_dead_missing_retention_expires(self):
        result = infer_inputs(inputs([(30, -2)] * 20 + [None] * 80))
        self.assertTrue(np.all(result.state[:50] == State.DEAD))
        self.assertTrue(np.all(result.state[50:] == State.UNKNOWN))

    def test_half_change_resets_dead_and_live_without_observations(self):
        for point in ((30, -2), (30, 20)):
            points = [point] * 20 if point[1] < 0 else [(30+i*.1, 20) for i in range(20)]
            result = infer_inputs(inputs(points + [None] * 10, [1] * 20 + [2] * 10))
            self.assertTrue(np.all(result.state[20:] == State.UNKNOWN))

    def test_ungraded_does_not_bridge_and_graded_half_start_is_not_dropped(self):
        f = features_from_inputs(inputs([(20+i*.1, 20) for i in range(70)]))
        f.arrays['graded'][20:30] = False
        f.arrays['ball_observed'][30:40] = False
        result = infer(f)
        self.assertTrue(np.all(result.state[:20] == State.ALIVE))
        self.assertTrue(np.all(result.state[20:40] == State.UNKNOWN))
        self.assertTrue(np.all(result.state[40:] == State.ALIVE))
        self.assertFalse(result.assessed[25])
        # Published half membership is sufficient; no inferred kickoff exclusion.
        self.assertEqual(result.state[0], State.ALIVE)

    def test_one_frame_outside_and_boundary_jitter_do_not_stop_live_play(self):
        points = [(20+i*.1, .1 if i % 2 else -.1) for i in range(60)]
        # Begin with clean supported live motion, then uncertain boundary observations.
        points[:20] = [(20+i*.1, 1) for i in range(20)]
        points[25] = (22.5, -3)
        result = infer_inputs(inputs(points))
        self.assertFalse(np.any(result.state == State.DEAD))
        self.assertEqual(result.state[25], State.ALIVE)

    def test_noisy_outside_stop_and_noisy_restart_backdate(self):
        points = [(20+i*.1, 20) for i in range(20)]
        points += [(22 + (.06 if i % 2 else -.06), -2 + (.04 if i % 3 else -.04))
                   for i in range(30)]
        points += [(30+i*.15, 20 + (.02 if i % 2 else -.02)) for i in range(30)]
        result = infer_inputs(inputs(points))
        self.assertTrue(np.all(result.state[20:50] == State.DEAD))
        self.assertTrue(np.all(result.state[50:] == State.ALIVE))

    def test_isolated_motion_outlier_and_jitter_do_not_establish_live(self):
        points = [(30+(.04 if i%2 else -.04), 20) for i in range(60)]
        points[25] = (90, 50)
        self.assertTrue(np.all(infer_inputs(inputs(points)).state == State.UNKNOWN))

    def test_fps_units_and_short_unconfirmed_evidence(self):
        for fps in (5, 25):
            pts = [(20+i/fps, 20) for i in range(fps*2)]
            self.assertTrue(np.all(infer_inputs(inputs(pts, fps=fps)).state == State.ALIVE))
        self.assertEqual(infer_inputs(inputs([(30, -2)])).state[0], State.UNKNOWN)

    def test_short_outside_run_and_stale_setpiece_do_not_split_live(self):
        points = [(20+i*.1, 20) for i in range(80)]
        points[25:28] = [(22.5, -2)] * 3
        result = infer_inputs(inputs(points, phases=(Phase('SET PIECES', 'A'),)))
        self.assertTrue(np.all(result.state == State.ALIVE))

    def test_low_confidence_outside_jitter_and_sparse_observations_abstain(self):
        # Sustained outside but not stationary enough to support D.
        points = [(30, -2 if i % 2 else -3) for i in range(80)]
        self.assertTrue(np.all(infer_inputs(inputs(points)).state == State.UNKNOWN))
        sparse = [(30, -2) if i % 3 == 0 else None for i in range(80)]
        self.assertTrue(np.all(infer_inputs(inputs(sparse)).state == State.UNKNOWN))

    def test_invalid_config(self):
        for kwargs in ({'retain_seconds':0}, {'motion_seconds':float('nan')},
                       {'motion_coherence':1.1}):
            with self.assertRaises(ValueError):
                Config(**kwargs)

    def test_determinism(self):
        fixture = synthetic_cases()[5].inputs
        a, b = infer_inputs(fixture), infer_inputs(fixture)
        np.testing.assert_array_equal(a.state, b.state)
        np.testing.assert_array_equal(a.evidence, b.evidence)
