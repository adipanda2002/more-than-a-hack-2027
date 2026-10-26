"""Asset-free full possession contracts and independently authored adversarial checks."""
from dataclasses import replace
import unittest

import numpy as np

from evaluation.behavioral_cases import Inputs, Observation, Phase, Player, synthetic_cases
from evaluation.behavioral_harness import run_cases
from possession.dead_ball import State
from possession.features import features_from_inputs
from possession.temporal import Config, infer, predict


def sequence(teams, missing=(), halves=None, phases=()):
    rows = []
    for i, team in enumerate(teams):
        x = 15 + i * .1
        if team is None:
            players = (Player('H', (x, 10)), Player('A', (x, 40)))
        elif team == 'tie':
            players = (Player('H', (x, 24)), Player('A', (x, 26)))
        else:
            players = (Player(team, (x, 25)), Player('A' if team == 'H' else 'H', (x, 45)))
        rows.append(Observation(i, 1 if halves is None else halves[i],
                                None if i in missing else (x+.25, 25), players, phases))
    return Inputs(tuple(rows))


class TemporalTests(unittest.TestCase):
    def test_all_eight_unchanged_full_contracts(self):
        results = run_cases(predict)
        self.assertEqual(len(results), 8)
        self.assertTrue(all(item.passed for item in results), results)

    def test_single_opponent_contact_retains_both_directions(self):
        for owner, opponent in (('H', 'A'), ('A', 'H')):
            labels = predict(sequence([owner]*20+[opponent]+[owner]*20))
            self.assertTrue(np.all(labels == owner))

    def test_control_confirmation_and_backdating_at_fps(self):
        for fps in (5, 10, 25):
            steps = int(np.ceil(.4*fps))
            short = replace(sequence(['H'] * steps), fps=fps)
            long = replace(sequence(['H'] * (steps+1)), fps=fps)
            self.assertTrue(np.all(predict(short) == 'X'))
            self.assertTrue(np.all(predict(long) == 'H'))

    def test_supported_turnover_backdates_first_control_in_both_directions(self):
        for owner, opponent in (('H', 'A'), ('A', 'H')):
            labels = predict(sequence([owner]*20+[None]*10+[opponent]*20))
            self.assertTrue(np.all(labels[:30] == owner))
            self.assertTrue(np.all(labels[30:] == opponent))

    def test_missing_expires_and_reacquires(self):
        result = predict(sequence(['H']*100, missing=range(20, 80)))
        self.assertTrue(np.all(result[:50] == 'H'))
        self.assertTrue(np.all(result[50:80] == 'X'))
        self.assertTrue(np.all(result[80:] == 'H'))
        self.assertFalse(np.any(result == 'D'))

    def test_loose_ball_expiry_is_finite(self):
        labels = predict(sequence(['H']*20+[None]*60))
        self.assertTrue(np.all(labels[:50] == 'H'))
        self.assertTrue(np.all(labels[50:] == 'X'))

    def test_ties_and_no_players_do_not_establish_ownership(self):
        self.assertTrue(np.all(predict(sequence(['tie']*40)) == 'X'))
        fixture = sequence(['H']*40)
        empty = replace(fixture, observations=tuple(replace(row, players=())
                                                  for row in fixture.observations))
        features = features_from_inputs(empty)
        self.assertEqual(features['player_xy_m'].shape, (40, 0, 2))
        self.assertTrue(np.all(features['team_observed_count'] == 0))
        self.assertTrue(np.isnan(features['team_nearest_ball_distance_m']).all())
        self.assertTrue(np.all(infer(features).labels == 'X'))

    def test_sustained_tie_retains_then_expires_without_flipping(self):
        labels = predict(sequence(['A']*20+['tie']*60))
        self.assertTrue(np.all(labels[:50] == 'A'))
        self.assertTrue(np.all(labels[50:] == 'X'))

    def test_missing_opponent_is_not_evidence_for_visible_team(self):
        fixture = sequence(['H']*40)
        partial = replace(fixture, observations=tuple(replace(row, players=(row.players[0],))
                                                    for row in fixture.observations))
        self.assertTrue(np.all(predict(partial) == 'X'))

    def test_half_change_and_ungraded_gap_reset_without_fresh_evidence(self):
        fixture = sequence(['H']*50, missing=range(20, 40), halves=[1]*20+[2]*30)
        labels = predict(fixture)
        self.assertTrue(np.all(labels[:20] == 'H'))
        self.assertTrue(np.all(labels[20:40] == 'X'))
        self.assertTrue(np.all(labels[40:] == 'H'))
        features = features_from_inputs(sequence(['H']*70, missing=range(30, 50)))
        features.arrays['graded'][20:30] = False
        labels = infer(features).labels
        self.assertTrue(np.all(labels[20:50] == 'X'))

    def test_dead_clears_owner_before_unsupported_restart(self):
        fixture = sequence(['H']*20+[None]*60)
        rows = list(fixture.observations)
        for i in range(20, 50):
            rows[i] = replace(rows[i], ball_xy=(20, -2))
        result = infer(features_from_inputs(replace(fixture, observations=tuple(rows))))
        self.assertTrue(np.all(result.labels[20:50] == 'D'))
        self.assertTrue(np.all(result.labels[50:] == 'X'))
        self.assertTrue(np.all(result.dead_state[50:] == State.ALIVE))

    def test_outside_restart_discontinuity_is_not_live_control_velocity(self):
        for owner in ('H', 'A'):
            fixture = sequence([None]*15+[owner]*25)
            rows = list(fixture.observations)
            for i in range(15):
                rows[i] = replace(rows[i], ball_xy=(15, -3))
            features = features_from_inputs(replace(fixture, observations=tuple(rows)))
            self.assertGreater(features['ball_speed_mps'][15], Config().max_control_ball_mps)
            labels = infer(features).labels
            self.assertTrue(np.all(labels[:15] == 'D'))
            self.assertTrue(np.all(labels[15:] == owner))

    def test_stationary_close_control_does_not_claim_referee_alive_state(self):
        fixture = sequence(['H']*30, phases=(Phase('SET PIECES', 'A'),))
        first = fixture.observations[0]
        rows = tuple(replace(first, frame=i) for i in range(30))
        result = infer(features_from_inputs(replace(fixture, observations=rows)))
        self.assertTrue(np.all(result.dead_state == State.UNKNOWN))
        self.assertTrue(np.all(result.labels == 'H'))
        # Ownership is a proxy here. It must never silently convert uncertainty to D.

    def test_noisy_geometry_and_tags_preserve_control(self):
        fixture = sequence(['A']*60, phases=(Phase('progression', 'H'),
                                            Phase('SET PIECES', 'H'), Phase('unknown')))
        noisy = replace(fixture, observations=tuple(replace(row,
                            ball_xy=(row.ball_xy[0]+(.03 if i%2 else -.03),
                                     row.ball_xy[1]+(.02 if i%3 else -.02)))
                          for i, row in enumerate(fixture.observations)))
        self.assertTrue(np.all(predict(noisy) == 'A'))

    def test_fast_ball_proximity_and_outside_ball_cannot_establish_owner(self):
        fixture = sequence(['H']*40)
        features = features_from_inputs(fixture)
        features.arrays['ball_speed_mps'][:] = 20
        self.assertTrue(np.all(infer(features).labels == 'X'))
        outside = replace(fixture, observations=tuple(replace(row, ball_xy=(20,-.1))
                                                    for row in fixture.observations))
        self.assertTrue(np.all(predict(outside) == 'X'))

    def test_team_swap_symmetry_and_determinism(self):
        for case in synthetic_cases():
            fixture = case.inputs
            swapped = replace(fixture, observations=tuple(replace(row,
                      players=tuple(replace(p, team={'H':'A', 'A':'H'}.get(p.team))
                                    for p in row.players)) for row in fixture.observations))
            original = predict(fixture)
            expected = np.array([{'H':'A', 'A':'H', 'D':'D', 'X':'X'}[x] for x in original])
            np.testing.assert_array_equal(predict(swapped), expected)
            np.testing.assert_array_equal(predict(fixture), original)

    def test_invalid_configs(self):
        for kwargs in ({'control_seconds': 0}, {'opponent_margin_m': -1},
                       {'retain_seconds': float('nan')}, {'control_radius_m': float('inf')}):
            with self.assertRaises(ValueError):
                Config(**kwargs)
