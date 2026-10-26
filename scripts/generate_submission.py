#!/usr/bin/env python3
"""Generate the frozen initial T07 CSV locally, without scoring or raw diagnostics."""
import argparse
import contextlib
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from possession.features import build_features
from possession.temporal import infer
from possession.submission import DEFAULT_OUTPUT, checked_output, official_valid, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', help='local asset root; defaults to MTAH_DATA_DIR or ./data')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT),
                        help='ignored untracked CSV beneath this repository data/predictions/')
    args = parser.parse_args()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            destination = checked_output(args.output)
            features, _ = build_features(data_dir=args.data_dir)
            result = infer(features)
            write_csv(destination, features['frame'], result.labels)
            if not official_valid(destination):
                raise ValueError('submission validation failed')
    except Exception:
        print('FAIL temporal submission generation (local details suppressed)')
        return 1
    print('PASS temporal submission generation and official format validation (no quality scoring)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
