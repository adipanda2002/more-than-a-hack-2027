#!/usr/bin/env python3
"""Sanitized local feature-consumer/invariant/determinism smoke, without quality scoring."""
import argparse
import contextlib
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from possession.features import build_features
from possession.dead_ball import Evidence, State, infer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', help='local asset root; defaults to MTAH_DATA_DIR or ./data')
    args = parser.parse_args()
    try:
        # Suppress library diagnostics too: only the fixed final pass/fail leaves this process.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            features, _ = build_features(data_dir=args.data_dir)
            first, second = infer(features), infer(features)
            n = len(features['frame'])
            assert all(array.shape == (n,) for array in
                       (first.state, first.evidence, first.assessed))
            assert np.isin(first.state, [int(x) for x in State]).all()
            assert np.all(first.state[~first.assessed] == State.UNKNOWN)
            assert np.array_equal(first.assessed, features['graded'] & (features['half'] > 0))
            direct_live = (first.evidence & int(Evidence.MOTION)) != 0
            direct_dead = (first.evidence & int(Evidence.OUTSIDE_STATIONARY)) != 0
            retained = (first.evidence & int(Evidence.RETAINED)) != 0
            assert np.all(first.state[direct_live] == State.ALIVE)
            assert np.all(first.state[direct_dead] == State.DEAD)
            assert np.all((first.state == State.UNKNOWN) | direct_live | direct_dead | retained)
            for key in ('state', 'evidence', 'assessed'):
                assert np.array_equal(getattr(first, key), getattr(second, key))
    except Exception:
        print('FAIL dead-ball feature-consumer smoke (local details suppressed)')
        return 1
    print('PASS dead-ball feature-consumer invariants and determinism (no quality scoring)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
