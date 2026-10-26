#!/usr/bin/env python3
"""Build private tactical feature cache; output contains no asset-derived values."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from possession.features import build_features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="data root (defaults to MTAH_DATA_DIR or ./data)")
    parser.add_argument("--no-cache", action="store_true", help="build without reading/writing cache")
    args = parser.parse_args()
    try:
        _, hit = build_features(data_dir=args.data_dir, use_cache=not args.no_cache)
    except Exception:
        print("FAIL tactical feature build (local details suppressed)")
        return 1
    result = "cache-hit" if hit else "built-no-cache" if args.no_cache else "built-and-cached"
    print("PASS tactical features {}".format(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
