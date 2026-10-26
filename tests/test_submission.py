"""Synthetic output safety and atomic CSV checks; no restricted match inputs."""
from pathlib import Path
import tempfile
import contextlib
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from possession.submission import OUTPUT_ROOT, ROOT, checked_output, official_valid, write_csv


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='synthetic-test-', dir=OUTPUT_ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_reject_external_asset_cache_traversal_and_non_csv(self):
        for path in ('/tmp/submission.csv', ROOT/'data/source.csv',
                     ROOT/'data/cache/test.csv', ROOT/'evaluation/results/new.csv',
                     self.directory/'../escape.csv', self.directory/'other.txt', OUTPUT_ROOT):
            with self.subTest(path=path), self.assertRaises(ValueError):
                checked_output(path)

    def test_reject_symlink_file_parent_and_dangling_link(self):
        target = self.directory/'real.csv'
        target.write_text('synthetic')
        link = self.directory/'link.csv'
        link.symlink_to(target)
        directory_link = self.directory/'linked'
        directory_link.symlink_to(self.directory, target_is_directory=True)
        dangling = self.directory/'dangling.csv'
        dangling.symlink_to(self.directory/'absent.csv')
        for path in (link, directory_link/'out.csv', dangling):
            with self.assertRaises(ValueError):
                checked_output(path)

    def test_explicit_ignored_untracked_destination_and_directory_rejection(self):
        target = self.directory/'valid.csv'
        self.assertEqual(checked_output(target), target)
        directory = self.directory/'directory.csv'
        directory.mkdir()
        with self.assertRaises(ValueError):
            checked_output(directory)

    def test_writer_schema_bytes_replacement_and_invalid_input_preserves_old_file(self):
        target = self.directory/'synthetic.csv'
        game = {'test': {'n_video_frames': 4}}
        with patch('possession.submission.games.GAME', 'test'), patch(
                'possession.submission.games.GAMES', game):
            write_csv(target, np.arange(4), np.array(list('HADX')))
            self.assertEqual(target.read_bytes(), b'frame,label\n0,H\n1,A\n2,D\n3,X\n')
            original = target.read_bytes()
            for frames, labels in ((np.arange(3), list('HAD')),
                                   (np.array([0,1,1,3]), list('HADX')),
                                   (np.arange(4), list('HAD?'))):
                with self.assertRaises(ValueError):
                    write_csv(target, frames, labels)
                self.assertEqual(target.read_bytes(), original)
            write_csv(target, np.arange(4), np.array(list('XXXX')))
            self.assertNotEqual(target.read_bytes(), original)
        self.assertFalse(list(self.directory.glob('.t07-*')))

    def test_atomic_write_failure_preserves_old_and_cleans_temporary(self):
        target = self.directory/'synthetic.csv'
        target.write_text('old')
        with patch('possession.submission.games.GAME', 'test'), patch(
                'possession.submission.games.GAMES', {'test': {'n_video_frames': 1}}), patch(
                'possession.submission.os.replace', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                write_csv(target, np.arange(1), np.array(['H']))
        self.assertEqual(target.read_text(), 'old')
        self.assertFalse(list(self.directory.glob('.t07-*')))

    def test_validator_subprocess_always_captures_diagnostics(self):
        target = self.directory/'synthetic.csv'
        with patch('possession.submission.subprocess.run') as run, patch(
                'possession.submission.checked_output', return_value=target):
            run.return_value.returncode = 0
            self.assertTrue(official_valid(target))
            self.assertTrue(run.call_args.kwargs['capture_output'])
            run.return_value.returncode = 1
            self.assertFalse(official_valid(target))

    def test_ignore_and_tracking_checks_are_both_required(self):
        target = self.directory/'synthetic.csv'
        for ignored_code, tracked_output in ((1, b''), (0, b'tracked-path')):
            results = [SimpleNamespace(returncode=ignored_code, stdout=b''),
                       SimpleNamespace(returncode=0, stdout=tracked_output)]
            with patch('possession.submission.subprocess.run', side_effect=results):
                with self.assertRaises(ValueError):
                    checked_output(target)

    def test_generator_rejects_destination_before_loading_assets(self):
        from scripts.generate_submission import main
        output = io.StringIO()
        with patch('sys.argv', ['generate_submission.py', '--output', '/tmp/unsafe.csv']), patch(
                'scripts.generate_submission.build_features') as build, contextlib.redirect_stdout(output):
            self.assertEqual(main(), 1)
        build.assert_not_called()
        self.assertEqual(output.getvalue(),
                         'FAIL temporal submission generation (local details suppressed)\n')

    def test_generator_sanitizes_exception_and_library_diagnostics(self):
        from scripts.generate_submission import main
        output = io.StringIO()
        def failure(**kwargs):
            print('synthetic-private-diagnostic')
            raise ValueError('synthetic-private-exception')
        with patch('sys.argv', ['generate_submission.py', '--output',
                               str(self.directory/'synthetic.csv')]), patch(
                'scripts.generate_submission.build_features', side_effect=failure), contextlib.redirect_stdout(output):
            self.assertEqual(main(), 1)
        self.assertEqual(output.getvalue(),
                         'FAIL temporal submission generation (local details suppressed)\n')
