"""Private local CSV output with restricted destination and sanitized validation."""
import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

import games

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / 'data' / 'predictions'
DEFAULT_OUTPUT = OUTPUT_ROOT / 't07.csv'


def checked_output(path):
    """Only ignored, untracked regular CSVs in the dedicated local output tree.

    Reject symlink components (including dangling links), traversal and directories.
    Keep prediction output separate from raw assets and the shared feature cache.
    """
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    if '..' in path.parts or path.suffix.lower() != '.csv':
        raise ValueError('unsafe output destination')
    try:
        path.relative_to(OUTPUT_ROOT)
    except ValueError:
        raise ValueError('unsafe output destination') from None
    for component in (path, *path.parents):
        if component == ROOT:
            break
        if component.is_symlink():
            raise ValueError('unsafe output destination')
    if path.exists() and not path.is_file():
        raise ValueError('unsafe output destination')
    relative = str(path.relative_to(ROOT))
    ignored = subprocess.run(['git', 'check-ignore', '-q', '--', relative], cwd=ROOT,
                             capture_output=True, check=False)
    tracked = subprocess.run(['git', 'ls-files', '--', relative], cwd=ROOT,
                             capture_output=True, check=False)
    if ignored.returncode != 0 or tracked.returncode != 0 or tracked.stdout:
        raise ValueError('output must be ignored and untracked')
    return path


def write_csv(path, frames, labels):
    """Atomically write a complete production timeline; no partial file replaces it."""
    path = checked_output(path)
    n = games.GAMES[games.GAME]['n_video_frames']
    if (np.shape(frames) != (n,) or np.shape(labels) != (n,)
            or not np.array_equal(frames, np.arange(n))
            or not np.isin(labels, ['H', 'A', 'D', 'X']).all()):
        raise ValueError('invalid submission timeline')
    path.parent.mkdir(parents=True, exist_ok=True)
    checked_output(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=path.parent, prefix='.t07-', suffix='.tmp',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream, lineterminator='\n')
            writer.writerow(('frame', 'label'))
            writer.writerows(zip(frames, labels))
            stream.flush()
            os.fsync(stream.fileno())
        checked_output(path)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def official_valid(path):
    """Run the unchanged organizer validator; never relay its derived diagnostics."""
    path = checked_output(path)
    result = subprocess.run([sys.executable, str(ROOT / 'evaluation/validate_submission.py'),
                             str(path)], cwd=ROOT, capture_output=True, check=False)
    return result.returncode == 0
