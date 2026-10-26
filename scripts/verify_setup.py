#!/usr/bin/env python3
"""Run the local, public-safe setup and reproducibility checks for this project."""

import csv
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXPECTED_SCORES = {
    "baseline_raw": (0.5972, 0.0378),
    "baseline_smooth25": (0.6200, 0.2868),
    "baseline_smooth50": (0.6207, 0.3256),
    "baseline_smooth125": (0.5812, 0.4242),
}


class CheckFailure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


def valid_atd_frame_ids(lines, expected):
    """Check every sequential ATD frame ID, including internal rows."""
    count = 0
    for count, line in enumerate(lines, 1):
        try:
            frame_id = int(line.split(":", 1)[0])
        except (ValueError, IndexError):
            return False
        if frame_id != count:
            return False
    return count == expected


def run_quietly(command):
    """Capture child output so restricted asset-derived output never reaches the terminal."""
    result = subprocess.run(command, cwd=str(ROOT), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode:
        # Child exceptions can contain paths or asset excerpts; report only the command class.
        raise CheckFailure("{} failed (exit {})".format(Path(command[1]).name,
                                                         result.returncode))
    return result


def check_assets():
    import games
    import numpy as np
    from starter import load_homography, load_smart_tagging

    required = games.require(["video", "atd_meta", "atd_raw", "homography",
                              "smart_tagging"])
    require(all(os.path.getsize(path) > 0 for path in required),
            "tactical required asset missing or empty")

    metadata = ET.parse(games.require(["atd_meta"])[0]).getroot()
    require(len(list(metadata.iter("Team"))) == 2 and
            len(list(metadata.iter("Player"))) > 0,
            "tactical metadata structure check failed")
    expected = games.source_frames("tactical")
    with open(games.require(["atd_raw"])[0]) as handle:
        require(valid_atd_frame_ids(handle, expected), "tactical ATD frame IDs are not sequential")

    require(load_homography.check_alignment()["agrees"],
            "tactical homography frame sequence check failed")
    matrices, reprojection_error, valid = load_homography.load()
    require(len(matrices) == expected and len(valid) == expected and
            matrices.shape == (expected, 3, 3), "tactical homography row count check failed")
    require(bool(valid.any()) and bool(np.isfinite(matrices[valid]).all()) and
            bool(np.isfinite(reprojection_error[valid]).all()) and
            bool(np.isnan(matrices[~valid]).all()),
            "tactical homography values do not match validity flags")

    events = load_smart_tagging.load()
    require(bool(events) and all(math.isfinite(event["start_s"]) and
                                 math.isfinite(event["end_s"]) and
                                 0 <= event["start_frame"] <= event["end_frame"] <= expected
                                 for event in events),
            "Smart Tagging intervals are malformed")
    require(load_smart_tagging.check_time_base(events)["agrees"],
            "Smart Tagging structure or time-base check failed")

    # Assets inside the checkout must remain ignored and untracked. A deliberate external
    # MTAH_DATA_DIR is supported and has no Git-exclusion requirement.
    repo_root = str(ROOT.resolve())
    paths_inside_repo = []
    for path in required:
        absolute = str(Path(path).resolve())
        if Path(absolute).is_relative_to(Path(repo_root)):
            paths_inside_repo.append(absolute)
    for path in paths_inside_repo:
        ignored = subprocess.run(["git", "check-ignore", "--quiet", "--", path], cwd=repo_root,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", path],
                                 cwd=repo_root, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).returncode == 0
        require(ignored and not tracked, "in-repository tactical assets must be ignored and untracked")

    # Broadcast is optional. Presence alone is useful; decoding and alignment are outside T03.
    broadcast = games.asset_paths(source="broadcast")
    present = all(os.path.isfile(path) and os.path.getsize(path) > 0
                  for path in broadcast.values())
    print("PASS assets tactical required files, structure, and alignment")
    print("PASS assets broadcast optional bundle {}".format("present" if present else "not present"))
    print("INFO videos are checked for presence only; no decoder is installed or run")


def check_reproducibility():
    import hashlib

    def sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    with tempfile.TemporaryDirectory(prefix="mtah-verify-", dir=str(ROOT / "data")) as temp:
        temp = Path(temp)
        outputs = temp / "generated"
        reports = temp / "reports"
        outputs.mkdir()
        reports.mkdir()
        run_quietly([sys.executable, "starter/baseline.py", "--out", str(outputs)])

        for name in EXPECTED_SCORES:
            generated = outputs / (name + ".csv")
            original = ROOT / "evaluation" / "results" / generated.name
            require(generated.is_file() and sha256(generated) == sha256(original),
                    "reference baseline hash check failed: " + name)
        print("PASS reference generation matches all four supplied baseline hashes")

        run_quietly([sys.executable, "evaluation/validate_submission.py",
                     str(outputs / "baseline_smooth50.csv")])
        print("PASS unchanged official validator accepts regenerated full-length baseline")

        run_quietly([sys.executable, "evaluation/run_evaluation.py", "--results",
                     str(outputs), "--out", str(reports), "--no-detail"])
        with open(reports / "scoreboard.csv", newline="") as handle:
            rows = {row["submission"].removesuffix(".csv"): row
                    for row in csv.DictReader(handle)}
        for name, (macro, spell) in EXPECTED_SCORES.items():
            require(name in rows and rows[name]["status"] == "scored" and
                    abs(float(rows[name]["macro_f1"]) - macro) < 0.00005 and
                    abs(float(rows[name]["spell_f1_mean"]) - spell) < 0.00005,
                    "public score check failed: " + name)
        print("PASS unchanged public scorer matches all four published public scores")


def main():
    try:
        require(sys.version_info[:2] == (3, 12), "Python must be 3.12 (see SETUP.md)")
        import numpy
        import pandas
        require(numpy.__version__ == "2.4.4" and pandas.__version__ == "3.0.2",
                "pinned NumPy/pandas versions are not installed")
        print("PASS runtime Python {}.{}.{}, NumPy 2.4.4, pandas 3.0.2".format(
            *sys.version_info[:3]))
        check_assets()
        check_reproducibility()
        print("PASS setup verification complete")
        return 0
    except CheckFailure as error:
        print("FAIL " + str(error))
    except Exception:
        # Never print exception strings from parsing or processing gated inputs.
        print("FAIL setup verification encountered an unexpected local error")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
