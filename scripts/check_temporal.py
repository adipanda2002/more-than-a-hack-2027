#!/usr/bin/env python3
"""Sanitized full-match invariants, two independent decodes and CSV byte equality."""
import argparse
import contextlib
import io
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from possession.features import build_features
from possession.temporal import infer
from possession.dead_ball import State
from possession.submission import DEFAULT_OUTPUT, OUTPUT_ROOT, checked_output, official_valid, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', help='local asset root; defaults to MTAH_DATA_DIR or ./data')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            destination = checked_output(args.output)
            features, _ = build_features(data_dir=args.data_dir)
            first = infer(features)
            expected = features['graded'] & (features['half'] > 0)
            n = len(features['frame'])
            assert first.labels.shape == first.control.shape == first.assessed.shape == (n,)
            assert np.isin(first.labels, ['H', 'A', 'D', 'X']).all()
            assert np.isin(first.control, [-1, 0, 1]).all()
            assert np.array_equal(first.assessed, expected)
            assert np.all(first.labels[~expected] == 'X')
            assert np.array_equal(first.labels == 'D', first.dead_state == State.DEAD)
            write_csv(destination, features['frame'], first.labels)
            assert official_valid(destination)
            # Temporary second output is also checked ignored/untracked and removed on exit.
            OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='t07-smoke-', dir=OUTPUT_ROOT) as directory:
                second = infer(features)
                for field in ('labels', 'control', 'assessed', 'dead_state'):
                    assert np.array_equal(getattr(first, field), getattr(second, field))
                second_path = write_csv(Path(directory) / 'repeat.csv', features['frame'], second.labels)
                assert official_valid(second_path)
                assert destination.read_bytes() == second_path.read_bytes()
    except Exception:
        print('FAIL temporal full-match smoke (local details suppressed)')
        return 1
    print('PASS temporal invariants, deterministic CSV bytes and official format validation (no quality scoring)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
