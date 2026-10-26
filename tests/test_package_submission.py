"""Asset-free safety and CLI tests for the final release packager."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import package_submission as package


class PackageSubmissionTests(unittest.TestCase):
    def test_all_destinations_checked_before_loading(self):
        for failed_index in range(3):
            calls = []
            def destination(path):
                calls.append(path)
                if len(calls) == failed_index + 1:
                    raise ValueError('private detail')
                return path
            with self.subTest(failed_index=failed_index), \
                    patch.object(package, '_safe_destination', side_effect=destination), \
                    patch.object(package, 'build_features') as build, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(package.main(['--team', 'polyamal']), 1)
            build.assert_not_called()
            self.assertEqual(len(calls), failed_index + 1)
            self.assertEqual(output.getvalue(), 'FAIL release packaging (local details suppressed)\n')

    def test_destination_traversal_parent_links_and_git_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            release = root / 'data/predictions/release'
            release.mkdir(parents=True)
            with patch.object(package, 'ROOT', root), \
                    patch.object(package.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=b'')):
                with self.assertRaises(ValueError):
                    package._safe_destination(release / '..' / 'escape.csv')
                release.rmdir()
                release.symlink_to(root / 'missing', target_is_directory=True)
                with self.assertRaises(ValueError):
                    package._safe_destination(release / 'team.csv')
                release.unlink()
                release.mkdir()
                for result in (SimpleNamespace(returncode=1, stdout=b''),
                               SimpleNamespace(returncode=0, stdout=b'tracked')):
                    with patch.object(package.subprocess, 'run', return_value=result):
                        with self.assertRaises(ValueError):
                            package._safe_destination(release / 'team.csv')

    def test_atomic_text_failure_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.md'
            path.write_text('previous')
            with patch.object(package, '_safe_destination', side_effect=lambda value: value), \
                    patch.object(package.os, 'replace', side_effect=OSError('private details')):
                with self.assertRaises(OSError):
                    package._atomic_text(path, 'replacement')
            self.assertEqual(path.read_text(), 'previous')
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_validator_failure_suppresses_details_and_does_not_write_sidecars(self):
        def noisy_rejection(path):
            print('private derived details')
            return False
        with patch.object(package, '_safe_destination', side_effect=lambda value: value), \
                patch.object(package, 'build_features', return_value=({'frame': np.arange(1)}, False)), \
                patch.object(package, 'infer', return_value=SimpleNamespace(labels=np.array(['X']))), \
                patch.object(package, 'write_csv'), \
                patch.object(package, 'official_valid', side_effect=noisy_rejection), \
                patch.object(package, '_atomic_text') as atomic, \
                contextlib.redirect_stdout(io.StringIO()) as output, \
                contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(package.main(['--team', 'polyamal']), 1)
        atomic.assert_not_called()
        self.assertEqual(error.getvalue(), '')
        self.assertEqual(output.getvalue(), 'FAIL release packaging (local details suppressed)\n')

    def test_basename_validation_rejects_paths_and_non_ascii(self):
        for value in ('', '../team', 'team/name', 'a.b', 'équipe', 'x' * 65):
            with self.subTest(value=value):
                self.assertIsNone(package.SAFE_TEAM.fullmatch(value))
        self.assertIsNotNone(package.SAFE_TEAM.fullmatch('polyamal-2027_1'))

    def test_destination_rejects_wrong_location_symlink_and_directory(self):
        with self.assertRaises(ValueError):
            package._safe_destination(package.ROOT / 'data/cache/escape.csv')
        package.RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
        link = package.RELEASE_ROOT / 'synthetic-link.csv'
        target = package.RELEASE_ROOT / 'absent.csv'
        try:
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                package._safe_destination(link)
        finally:
            link.unlink(missing_ok=True)
        directory = package.RELEASE_ROOT / 'synthetic-directory.csv'
        directory.mkdir(exist_ok=True)
        with self.assertRaises(ValueError):
            package._safe_destination(directory)
        directory.rmdir()

    def test_invalid_team_fails_sanitized_before_asset_loading(self):
        output = io.StringIO()
        with patch('scripts.package_submission.build_features') as build, contextlib.redirect_stdout(output):
            code = package.main(['--team', '../unsafe'])
        self.assertEqual(code, 1)
        build.assert_not_called()
        self.assertEqual(output.getvalue(), 'FAIL release packaging (local details suppressed)\n')

    def test_synthetic_generation_uses_exact_team_paths_and_schema(self):
        team = 'CodexSyntheticTest'
        paths = [package.RELEASE_ROOT / f'{team}{suffix}'
                 for suffix in ('.csv', '.md', '.manifest.json')]
        for path in paths:
            path.unlink(missing_ok=True)
        features = {'frame': np.arange(4)}
        result = SimpleNamespace(labels=np.array(list('HADX')))
        output = io.StringIO()
        try:
            with patch('scripts.package_submission.build_features', return_value=(features, False)) as build, \
                    patch('scripts.package_submission.infer', return_value=result), \
                    patch('scripts.package_submission.official_valid', return_value=True), \
                    patch('possession.submission.games.GAME', 'synthetic'), \
                    patch('possession.submission.games.GAMES', {'synthetic': {'n_video_frames': 4}}), \
                    contextlib.redirect_stdout(output):
                code = package.main(['--team', team, '--no-cache'])
            self.assertEqual(code, 0)
            self.assertEqual(build.call_args.kwargs['use_cache'], False)
            self.assertEqual(paths[0].name, team + '.csv')
            self.assertEqual(paths[0].read_bytes(), b'frame,label\n0,H\n1,A\n2,D\n3,X\n')
            self.assertEqual(paths[1].read_text(), package.REPORT.read_text())
            self.assertTrue(paths[2].is_file())
            manifest = json.loads(paths[2].read_text())
            self.assertEqual(manifest['dead_ball_config'], package.DeadConfig().__dict__)
            self.assertEqual(set(manifest['dependencies']), {'numpy', 'pandas', 'python-dateutil', 'six'})
            self.assertIn('TECHNICAL_REPORT.md', manifest['source_sha256'])
            self.assertIn('evaluation/validate_submission.py', manifest['source_sha256'])
            self.assertEqual(output.getvalue(),
                             'PASS release packaging and official format validation (no quality scoring)\n')
        finally:
            for path in paths:
                path.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
