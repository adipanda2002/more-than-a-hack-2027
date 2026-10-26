"""Focused T08 fixture and accounting checks; never loads match assets."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from evaluation.behavioral_harness import expected_labels
from evaluation.robustness_cases import limitation_witnesses, robustness_cases
from evaluation.behavioral_cases import synthetic_cases
from scripts import run_robustness as runner


class RobustnessFixtureTests(unittest.TestCase):
    def test_frozen_fixtures_are_complete_and_have_expected_lengths(self):
        cases = robustness_cases()
        self.assertEqual(len(cases), 15)
        for case in cases:
            self.assertEqual(len(expected_labels(case)), len(case.inputs.observations))
        for family in ("R01_", "R03_", "R05_", "R06_"):
            self.assertEqual(sum(c.name.startswith(family) for c in cases), 3)

    def test_two_frame_contact_and_half_gap_are_encoded_as_preregistered(self):
        cases = {case.name: case for case in robustness_cases()}
        r02 = cases["R02_deflection"]
        contact_rows = [i for i, row in enumerate(r02.inputs.observations)
                        if row.players[0].xy[0] == 40]
        self.assertEqual(contact_rows, [30, 31])
        for i in contact_rows:
            t = i / 10
            self.assertEqual(r02.inputs.observations[i].players[1].xy, (19.7 + t, 25))
        r06 = cases["R06_half_reset_10fps"]
        self.assertEqual(r06.inputs.observations[39].half, 1)
        self.assertEqual(r06.inputs.observations[40].half, 2)
        self.assertIsNone(r06.inputs.observations[40].ball_xy)

    def test_limit_witnesses_share_unidentifiable_inputs(self):
        witnesses = dict(limitation_witnesses())
        live = witnesses["L01_live_H"].inputs.observations
        dead = witnesses["L01_stoppage_D"].inputs.observations
        self.assertEqual(live, dead)
        self.assertEqual(len(expected_labels(witnesses["L02_missing_stoppage"])), 80)

    def test_source_digest_is_stable(self):
        self.assertEqual(runner.source_digest(), runner.source_digest())

    def _valid_report(self):
        names = {case.name for case in tuple(synthetic_cases()) + robustness_cases()}
        witness_names = {name for name, _ in limitation_witnesses()}
        return {
            "schema": runner.CACHE_SCHEMA,
            "digest": runner.source_digest(),
            "python": runner.platform.python_version(),
            "numpy": runner.np.__version__,
            "platform": runner.platform.platform(),
            "config_ids": list(runner.CONFIGS),
            "fixtures": {cid: {name: {"passed": True, "mismatches": 0} for name in names}
                         for cid in runner.CONFIGS},
            "invariances": {cid: {name: True for name in runner._expected_invariance_names(
                tuple(synthetic_cases()) + robustness_cases())} for cid in runner.CONFIGS},
            "limitations": {cid: {name: {"passed": name == "L01_live_H", "mismatches": 0 if name == "L01_live_H" else 60,
                                         **({"x_expiry_present": True, "dead_established": False}
                                            if name == "L02_missing_stoppage" else {})}
                                  for name in witness_names} for cid in runner.CONFIGS},
            "resources": {cid: {"passed": True, "labels_valid": True,
                                "peak_rss_bytes": 1, "feature_seconds": .1,
                                "decode_seconds": .1} for cid in runner.CONFIGS},
        }

    def test_missing_or_truncated_resource_never_passes_cache_or_gate(self):
        report = self._valid_report()
        del report["resources"]["C2"]
        self.assertFalse(runner._report_valid(report))
        report = self._valid_report()
        report["resources"]["C1"] = {"passed": True}
        self.assertFalse(runner._report_valid(report))

    def test_ablation_semantic_failure_rejects_candidate_but_c0_remains_eligible(self):
        report = self._valid_report()
        report["fixtures"]["C1"][next(iter(report["fixtures"]["C1"]))] = {
            "passed": False, "mismatches": 2}
        gates = runner._eligible(report)
        self.assertTrue(gates["C0"]["eligible"])
        self.assertFalse(gates["C1"]["eligible"])

    def test_c0_semantic_or_resource_failure_blocks_full_match(self):
        for key in ("semantic", "resource"):
            report = self._valid_report()
            if key == "semantic":
                first = next(iter(report["fixtures"]["C0"]))
                report["fixtures"]["C0"][first] = {"passed": False, "mismatches": 1}
            else:
                report["resources"]["C0"] = {"passed": False, "reason": "limit"}
            with patch.object(runner, "_load_cache", return_value=report), \
                    patch.object(runner, "resource_check", side_effect=AssertionError("rerun")), \
                    patch.object(runner, "_run_full_match") as full:
                _, _, status = runner._execute(full_match=True)
            self.assertNotEqual(status, "ok")
            full.assert_not_called()

    def test_any_config_invariance_failure_is_command_gate(self):
        report = self._valid_report()
        report["invariances"]["C2"][next(iter(report["invariances"]["C2"]))] = False
        with patch.object(runner, "_load_cache", return_value=report), \
                patch.object(runner, "_run_full_match") as full:
            _, _, status = runner._execute(full_match=True)
        self.assertEqual(status, "invariance_failure")
        full.assert_not_called()

    def test_full_match_reuses_complete_cache_without_resource_reruns(self):
        report = self._valid_report()
        with patch.object(runner, "_load_cache", return_value=report), \
                patch.object(runner, "resource_check", side_effect=AssertionError("rerun")), \
                patch.object(runner, "_run_full_match", return_value=True), \
                patch.object(runner, "_save_cache"):
            result, gates, status = runner._execute(full_match=True)
        self.assertEqual(status, "ok")
        self.assertEqual(result["production_c0"], "PASS")
        self.assertTrue(gates["C0"]["eligible"])

    def test_default_execution_never_calls_full_match(self):
        report = self._valid_report()
        with patch.object(runner, "_load_cache", return_value=report), \
                patch.object(runner, "_run_full_match") as full:
            _, _, status = runner._execute(full_match=False)
        self.assertEqual(status, "ok")
        full.assert_not_called()

    def test_cache_path_rejects_symlink_components_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data" / "experiments").symlink_to(root / "missing", target_is_directory=True)
            with patch.object(runner, "ROOT", root):
                self.assertFalse(runner._path_is_safe(root / "data/experiments/t08-synthetic.json"))
                self.assertFalse(runner._path_is_safe(root / "data/experiments/other.json"))

    def test_cache_requires_exact_invariance_keys_and_consistent_counts(self):
        self.assertTrue(runner._report_valid(self._valid_report()))
        for mutation in ("truncated", "arbitrary", "positive_pass", "negative", "bool_count", "false_zero"):
            with self.subTest(mutation=mutation):
                report = self._valid_report()
                name = next(iter(report["fixtures"]["C0"]))
                if mutation == "truncated":
                    report["invariances"]["C0"].pop(next(iter(report["invariances"]["C0"])))
                elif mutation == "arbitrary":
                    report["invariances"]["C0"] = {"metamorphic": True}
                else:
                    report["fixtures"]["C0"][name] = {
                        "passed": mutation != "false_zero",
                        "mismatches": {"positive_pass": 2, "negative": -1,
                                       "bool_count": True, "false_zero": 0}[mutation]}
                self.assertFalse(runner._report_valid(report))

    def test_missing_cache_runs_matrix_once_and_saves_complete_results(self):
        report = self._valid_report()
        resources = report["resources"]
        report["resources"] = {}
        with patch.object(runner, "_load_cache", return_value=None), \
                patch.object(runner, "synthetic_results", return_value=report), \
                patch.object(runner, "resource_check", side_effect=lambda cid: resources[cid]) as run, \
                patch.object(runner, "_save_cache") as save, \
                patch.object(runner, "_run_full_match") as full:
            _, _, status = runner._execute()
        self.assertEqual(status, "ok")
        self.assertEqual([call.args[0] for call in run.call_args_list], list(runner.CONFIGS))
        self.assertTrue(runner._report_valid(save.call_args.args[0]))
        full.assert_not_called()

    def test_any_resource_failure_stops_command_and_production(self):
        for cid in runner.CONFIGS:
            report = self._valid_report()
            report["resources"][cid] = {"passed": False, "reason": "limit"}
            with patch.object(runner, "_load_cache", return_value=report), \
                    patch.object(runner, "_run_full_match") as full:
                _, _, status = runner._execute(full_match=True)
            self.assertEqual(status, "resource_failure")
            full.assert_not_called()

    def test_cache_rejects_traversal_nested_alias_and_directory_before_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "data/experiments/t08-synthetic.json"
            canonical.mkdir(parents=True)
            with patch.object(runner, "ROOT", root), \
                    patch.object(runner.subprocess, "run", side_effect=AssertionError("git reached")):
                for path in (canonical, root / "data/experiments/../t08-synthetic.json",
                             root / "data/experiments/nested/t08-synthetic.json"):
                    self.assertFalse(runner._path_is_safe(path))

    def test_production_timeline_mask_bytes_and_validator_gates_capture_output(self):
        for defect in (None, "timeline", "mask", "bytes", "validator"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                frames = runner.np.arange(199319)
                if defect == "timeline":
                    frames[1] = 0
                features = {"frame": frames, "graded": runner.np.ones(199319, dtype=bool),
                            "half": runner.np.ones(199319, dtype=int)}
                result = SimpleNamespace(labels=runner.np.full(199319, "H"),
                    control=runner.np.zeros(199319, dtype=int),
                    assessed=runner.np.full(199319, defect != "mask", dtype=bool),
                    dead_state=runner.np.zeros(199319, dtype=int))
                def write(path, *_):
                    print("private writer diagnostic")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("different" if defect == "bytes" and "second" in path.name else "same")
                captured = io.StringIO()
                with patch("possession.features.build_features", return_value=(features, True)), \
                        patch("possession.submission.OUTPUT_ROOT", Path(directory)), \
                        patch("possession.submission.checked_output", side_effect=lambda p: p), \
                        patch("possession.submission.write_csv", side_effect=write), \
                        patch.object(runner, "infer", return_value=result), \
                        patch.object(runner.subprocess, "run", return_value=SimpleNamespace(
                            returncode=1 if defect == "validator" else 0,
                            stdout=b"private validator diagnostic", stderr=b"private")) as validator, \
                        contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                    outcome = runner._run_full_match()
                self.assertIs(outcome, defect is None)
                self.assertEqual(captured.getvalue(), "")
                for call in validator.call_args_list:
                    self.assertTrue(call.kwargs["capture_output"])

    def test_full_match_failure_and_library_output_are_sanitized(self):
        noisy = lambda **kwargs: (print("restricted detail"), (_ for _ in ()).throw(RuntimeError()))[1]
        output = io.StringIO()
        with patch("possession.features.build_features", side_effect=noisy), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = runner._run_full_match()
        self.assertIs(result, False)
        self.assertNotIn("restricted", output.getvalue())


if __name__ == "__main__":
    unittest.main()
