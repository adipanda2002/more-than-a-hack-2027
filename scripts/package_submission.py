#!/usr/bin/env python3
"""Create a locally validated, team-named release bundle without scoring."""
import argparse
import contextlib
import hashlib
import io
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from possession.features import build_features
from possession.temporal import Config, infer
from possession.dead_ball import Config as DeadConfig
from possession.submission import OUTPUT_ROOT, official_valid, write_csv

RELEASE_ROOT = OUTPUT_ROOT / 'release'
REPORT = ROOT / 'TECHNICAL_REPORT.md'
SAFE_TEAM = re.compile(r'[A-Za-z0-9_-]{1,64}\Z', re.ASCII)
CODE_FILES = ('possession/features.py', 'possession/dead_ball.py',
              'possession/temporal.py', 'possession/submission.py',
              'scripts/package_submission.py', 'requirements-local.txt', 'games.py',
              'evaluation/validate_submission.py', 'evaluation/possession_metrics.py',
              'TECHNICAL_REPORT.md', 'LICENSE')


def _safe_destination(path):
    path = Path(path)
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        raise ValueError('unsafe release destination') from None
    if '..' in path.parts or rel.parent != Path('data/predictions/release'):
        raise ValueError('unsafe release destination')
    for component in (path, *path.parents):
        if component == ROOT:
            break
        if component.is_symlink():
            raise ValueError('unsafe release destination')
    if path.exists() and not path.is_file():
        raise ValueError('unsafe release destination')
    ignored = subprocess.run(['git', 'check-ignore', '-q', '--', str(rel)], cwd=ROOT,
                             capture_output=True, check=False)
    tracked = subprocess.run(['git', 'ls-files', '--', str(rel)], cwd=ROOT,
                             capture_output=True, check=False)
    if ignored.returncode or tracked.returncode or tracked.stdout:
        raise ValueError('release files must be ignored and untracked')
    return path


def _atomic_text(path, content):
    path = _safe_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_destination(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=path.parent, prefix='.release-', suffix='.tmp',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        _safe_destination(path)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _manifest(team, output):
    sources = {}
    for name in CODE_FILES:
        sources[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    return {
        'schema': 1,
        'team': team,
        'method': 'unchanged C0 temporal.Config defaults',
        'config': Config().__dict__,
        'dead_ball_config': DeadConfig().__dict__,
        'python': platform.python_version(),
        'platform': platform.platform(),
        'dependencies': {name: version(name) for name in
                         ('numpy', 'pandas', 'python-dateutil', 'six')},
        'source_sha256': sources,
        'csv_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--team', required=True)
    parser.add_argument('--data-dir')
    parser.add_argument('--no-cache', action='store_true',
                        help='rebuild aligned tactical features without reading/writing the feature cache')
    args = parser.parse_args(argv)
    try:
        if not SAFE_TEAM.fullmatch(args.team):
            raise ValueError('invalid team basename')
        csv_path = _safe_destination(RELEASE_ROOT / (args.team + '.csv'))
        md_path = _safe_destination(RELEASE_ROOT / (args.team + '.md'))
        manifest_path = _safe_destination(RELEASE_ROOT / (args.team + '.manifest.json'))
        if not REPORT.is_file():
            raise ValueError('technical report missing')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            features, _ = build_features(data_dir=args.data_dir,
                                          use_cache=not args.no_cache)
            result = infer(features)
            write_csv(csv_path, features['frame'], result.labels)
            if not official_valid(csv_path):
                raise ValueError('submission validator rejected output')
            _atomic_text(md_path, REPORT.read_text(encoding='utf-8'))
            manifest = _manifest(args.team, csv_path)
            _atomic_text(manifest_path, json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    except Exception:
        print('FAIL release packaging (local details suppressed)')
        return 1
    print('PASS release packaging and official format validation (no quality scoring)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
