"""Focused feature-contract tests over independently authored synthetic geometry."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import xml.etree.ElementTree as ET
import json

import numpy as np

from evaluation.behavioral_cases import Inputs, Observation, Phase, Player
import games
from possession.features import (Features, _empty, _load_cache, _save_cache,
                                 _normalized_to_pitch_m, _set_timeline, _team_index,
                                 _cache_path, features_from_inputs)


class FeatureTests(unittest.TestCase):
    def test_metadata_membership_uses_team_ids_not_slot_order(self):
        from possession.features import _team_metadata
        xml = """<root>
          <Team id="h"><Name>Home</Name></Team><Team id="a"><Name>Away</Name></Team>
          <Player teamId="a"/><Player teamId="h"/><Player teamId="a"/>
          <Player teamId="unassigned"/>
        </root>"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "metadata.xml"
            path.write_text(xml)
            membership, names = _team_metadata(path)
        self.assertEqual(names, ("Home", "Away"))
        self.assertEqual(membership.tolist(), [1, 0, 1, -1])

    def test_metric_geometry_missingness_and_unknown_team(self):
        self.assertEqual(_normalized_to_pitch_m(0.5, 0.25, (105.3, 68)),
                         (52.65, 17.0))
        rows = (Observation(0, 1, (10.0, 10.0),
                            (Player("H", (10.0, 10.0)), Player("A", (20.0, 10.0)),
                             Player(None, (11.0, 10.0)))),
                Observation(1, 1, None, ()),)
        f = features_from_inputs(Inputs(rows, fps=2, pitch_m=(100, 60)))
        self.assertAlmostEqual(f["team_nearest_ball_distance_m"][0, 0], 0)
        self.assertAlmostEqual(f["team_nearest_ball_distance_m"][0, 1], 10)
        self.assertEqual(f["team_observed_count"][0].tolist(), [1, 1])
        self.assertEqual(f["player_team"][0].tolist(), [0, 1, -1])
        self.assertTrue(np.isnan(f["ball_xy_m"][1]).all())
        self.assertFalse(f["ball_observed"][1])
        self.assertTrue(np.isnan(f["team_nearest_ball_distance_m"][1]).all())
        self.assertFalse(f["ball_out_of_pitch"][1])

    def test_motion_requires_consecutive_observation_and_same_half(self):
        rows = tuple(Observation(i, 1 if i < 3 else 2,
                                 None if i == 2 else (float(i), 0.0),
                                 () if i == 2 else (Player("H", (float(i), 0.0)),))
                     for i in range(4))
        f = features_from_inputs(Inputs(rows, fps=5, pitch_m=(100, 60)))
        self.assertTrue(np.isnan(f["ball_speed_mps"][0]))
        self.assertAlmostEqual(f["ball_speed_mps"][1], 5)
        self.assertTrue(np.isnan(f["ball_speed_mps"][2]))
        self.assertTrue(np.isnan(f["ball_speed_mps"][3]))
        self.assertTrue(np.isnan(f["player_speed_mps"][2, 0]))
        self.assertTrue(np.isnan(f["player_speed_mps"][3, 0]))

    def test_motion_does_not_cross_track_slot_team_change(self):
        rows = (Observation(0, 1, (0, 0), (Player("H", (0, 0)),)),
                Observation(1, 1, (1, 0), (Player("A", (1, 0)),)))
        f = features_from_inputs(Inputs(rows))
        self.assertTrue(np.isnan(f["player_speed_mps"][1, 0]))

    def test_all_missing_geometry_has_no_fabricated_zero(self):
        rows = tuple(Observation(i, 1, None, ()) for i in range(3))
        f = features_from_inputs(Inputs(rows))
        self.assertFalse(f["ball_observed"].any())
        self.assertFalse(f["player_observed"].any())
        self.assertTrue(np.isnan(f["team_nearest_ball_distance_m"]).all())
        self.assertTrue(np.isnan(f["team_centroid_separation_m"]).all())

    def test_smart_tag_semantics_keep_defending_side_as_opponent_support(self):
        rows = (Observation(0, 1, None,
                            (Player("H", (1, 1)),),
                            (Phase("BUILD UP", "H"), Phase("DEFENDING IN MIDDLE THIRD", "A"),
                             Phase("SET PIECES", None), Phase("UNKNOWN", None))),)
        f = features_from_inputs(Inputs(rows))
        self.assertTrue(f["tag_team_offensive"][0, 0])
        self.assertTrue(f["tag_team_defensive"][0, 1])
        self.assertTrue(f["tag_team_defending_opponent_support"][0, 0])
        self.assertTrue(f["tag_set_piece"][0])
        self.assertTrue(f["tag_unknown_team"][0])
        self.assertFalse(f["tag_conflict"][0])

    def test_tag_support_conflict_and_unknown_set_piece_team(self):
        rows = (Observation(0, 1, None, (),
                            (Phase("BUILD UP", "H"), Phase("DEFENDING IN MIDDLE THIRD", "H"),
                             Phase("SET PIECES", None), Phase("NOT IN TAXONOMY", "A"))),)
        f = features_from_inputs(Inputs(rows))
        self.assertTrue(f["tag_conflict"][0])
        self.assertTrue(f["tag_unknown_team"][0])
        self.assertTrue(f["tag_unknown_code"][0])
        self.assertTrue(f["tag_set_piece"][0])
        self.assertFalse(f["tag_team_set_piece"][0].any())

    def test_tag_projection_is_half_open_and_handles_conflicting_intervals(self):
        from possession.features import _project_tags
        xml = """<root>
          <instance><start>0.1</start><end>0.3</end><code>BUILD UP</code>
            <label><group>Team</group><text>Barcelona</text></label></instance>
          <instance><start>0.2</start><end>0.4</end><code>DEFENDING IN MIDDLE THIRD</code>
            <label><group>Team</group><text>Barcelona</text></label></instance>
          <instance><start>0.3</start><end>0.5</end><code>SET PIECES</code>
            <label><group>Team</group><text>N/A</text></label></instance>
        </root>"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tags.xml"
            path.write_text(xml)
            a = _empty(8, 1, (100, 60), 10, ("FC Barcelona", "Athletic Club"))
            _project_tags(path, a, ("FC Barcelona", "Athletic Club"), 10)
        self.assertTrue(a["tag_team_offensive"][1, 0])
        self.assertFalse(a["tag_team_offensive"][3, 0])
        self.assertTrue(a["tag_team_defending_opponent_support"][2, 1])
        self.assertFalse(a["tag_team_defending_opponent_support"][4, 1])
        self.assertTrue(a["tag_set_piece"][3])
        self.assertFalse(a["tag_set_piece"][5])
        self.assertTrue(a["tag_unknown_team"][3])
        self.assertTrue(a["tag_conflict"][2])

    def test_half_boundary_resets_speed_without_removing_timeline_semantics(self):
        rows = (Observation(0, 1, (1, 1), (Player("H", (1, 1)),)),
                Observation(1, 2, (2, 1), (Player("H", (2, 1)),)))
        f = features_from_inputs(Inputs(rows))
        self.assertTrue(np.isnan(f["ball_speed_mps"][1]))

    def test_published_timeline_alignment_and_graded_mask_are_independent(self):
        n = 199319
        a = _empty(n, 1, (105.3, 68), 25, ("FC Barcelona", "Athletic Club"))
        _set_timeline(a, "BAR-ATH")
        self.assertEqual(a["half"][11184], 0)
        self.assertEqual(a["half"][11185], 1)
        self.assertEqual(a["half"][90651], 1)
        self.assertEqual(a["half"][90652], 0)
        self.assertEqual(a["half"][110808], 2)
        self.assertTrue(a["graded"][110808])  # graded pre-kickoff remains separate
        self.assertEqual(a["half"][190197], 2)
        self.assertFalse(a["graded"][190198])
        self.assertEqual(_team_index("Barcelona", ("FC Barcelona", "Athletic Club")), 0)
        self.assertEqual(_team_index("Atletic Club", ("FC Barcelona", "Athletic Club")), 1)
        self.assertEqual(_team_index("N/A", ("FC Barcelona", "Athletic Club")), -1)

    def test_cache_rejects_fingerprint_mismatch_and_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "features.npz"
            features = Features(_empty(2, 1, (100, 60), 25, ("Home", "Away")),
                                25, (100, 60), ("Home", "Away"))
            _save_cache(path, features, "fingerprint-a")
            self.assertIsNotNone(_load_cache(path, "fingerprint-a", 2, 1))
            self.assertIsNone(_load_cache(path, "fingerprint-b", 2, 1))
            with np.load(path, allow_pickle=False) as cached:
                arrays = {key: cached[key] for key in cached.files if key != "__metadata__"}
                metadata = json.loads(str(cached["__metadata__"].item()))
            metadata["pitch_m"] = [0, 60]
            np.savez_compressed(path, __metadata__=np.asarray(json.dumps(metadata)), **arrays)
            self.assertIsNone(_load_cache(path, "fingerprint-a", 2, 1))
            _save_cache(path, features, "fingerprint-a")
            features.arrays["ball_observed"] = features.arrays["ball_observed"].astype(np.int8)
            _save_cache(path, features, "fingerprint-a")
            self.assertIsNone(_load_cache(path, "fingerprint-a", 2, 1))
            path.write_bytes(b"broken")
            self.assertIsNone(_load_cache(path, "fingerprint-a", 2, 1))

    def test_cache_destination_is_always_verified_private_data_path(self):
        path = _cache_path("/tmp/not-the-data-root", "BAR-ATH")
        self.assertIn("/data/cache/features/", str(path))
        self.assertTrue(path.parent.is_relative_to(Path(__file__).resolve().parents[1] / "data"))

    def test_unsafe_cache_destination_is_rejected_before_write(self):
        with mock.patch("possession.features.subprocess.run",
                        side_effect=[SimpleNamespace(returncode=1),
                                     SimpleNamespace(returncode=1)]):
            with self.assertRaises(ValueError):
                _cache_path("/tmp", "BAR-ATH")

    def test_production_loader_parses_synthetic_assets_and_checks_alignment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            meta = root / "meta.xml"
            raw = root / "tracking.txt"
            tags = root / "tags.xml"
            meta.write_text("""<root>
              <Team id="h"><Name>FC Barcelona</Name></Team>
              <Team id="a"><Name>Athletic Club</Name></Team>
              <Player teamId="h"/><Player teamId="a"/><Player teamId="unknown"/>
            </root>""")
            source_rows = [
                "1:0.2,0.5,0;0.8,0.5,0;N:0.2,0.5,0\n",
                "2:0.201,0.5,0;0.8,0.5,0;N:0.201,0.5,0\n",
                "3:0.202,0.5,0;0.8,0.5,0;N:N\n",
                "4:0.203,0.5,0;0.8,0.5,0;N:0.203,0.5,0\n",
            ]
            raw.write_text("".join(source_rows))
            tags.write_text("""<root>
              <instance><start>0.04</start><end>0.12</end><code>BUILD UP</code>
                <label><group>Team</group><text>Barcelona</text></label></instance>
              <instance><start>0.12</start><end>0.16</end><code>SET PIECES</code>
                <label><group>Team</group><text>N/A</text></label></instance>
            </root>""")
            with mock.patch("possession.features.games.require",
                            return_value=[str(meta), str(raw), str(tags)]), \
                    mock.patch("possession.features.games.source_frames", return_value=4), \
                    mock.patch("possession.features.games.half_video_blocks",
                               return_value=[(1, 0, 2), (2, 3, 3)]), \
                    mock.patch("possession.features._cache_path",
                               side_effect=AssertionError("no-cache must not resolve cache path")):
                from possession.features import build_features
                f, hit = build_features(data_dir=folder, use_cache=False)
                self.assertFalse(hit)
                self.assertEqual(f.team_names, ("FC Barcelona", "Athletic Club"))
                self.assertAlmostEqual(f["player_xy_m"][0, 0, 0], 21.06)
                self.assertAlmostEqual(f["player_xy_m"][0, 0, 1], 34.0)
                self.assertEqual(f["team_observed_count"][0].tolist(), [1, 1])
                self.assertEqual(f["player_team"][0].tolist(), [0, 1, -1])
                self.assertAlmostEqual(f["team_nearest_ball_distance_m"][1, 0], 0.0)
                self.assertAlmostEqual(f["team_mean_speed_mps"][1, 0], 2.6325, places=3)
                self.assertTrue(np.isnan(f["player_speed_mps"][3, 0]))
                self.assertTrue(f["tag_team_offensive"][1, 0])
                self.assertFalse(f["tag_team_offensive"][3, 0])
                self.assertTrue(f["tag_set_piece"][3])
                self.assertTrue(f["tag_unknown_team"][3])
                self.assertTrue(np.isnan(f["team_nearest_ball_distance_m"][2]).all())

                # A duplicated middle frame ID fails even though endpoints/count could match.
                raw.write_text(source_rows[0] + source_rows[2] + source_rows[2] + source_rows[3])
                with self.assertRaises(ValueError):
                    build_features(data_dir=folder, use_cache=False)


if __name__ == "__main__":
    unittest.main()
